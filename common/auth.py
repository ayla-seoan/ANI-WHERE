"""간편 회원가입·로그인: 카카오 · 네이버 (OAuth 2.0).

흐름
  1. /login 에서 '카카오로 시작하기' → 카카오 동의 화면 (authorize_url)
  2. 카카오가 {APP_BASE_URL}/auth?code=…&state=… 로 돌려보냄
     → state 서명 확인(위조·재사용 방지) → code 로 토큰 받기 → 프로필(고유 번호·닉네임)만 읽기 (exchange)
  3. 처음 온 사람이면 /auth 화면에서 닉네임·동의를 받아 회원 기록을 쌓는다 (signup) — 이게 '간편 회원가입'
  4. 로그인 상태는 서명한 쿠키(aw_session, 30일)로 기억한다 (make_session / read_session)

지키는 것
  - 이메일·전화번호·실명은 **요청하지도 저장하지도 않는다** (CLAUDE.md 민감정보). 동의 항목은 닉네임(프로필)만.
  - 카카오·네이버의 고유 번호도 그대로 저장하지 않고 소금 친 해시(member_key)만 남긴다.
  - 회원 기록도 append-only (탈퇴 = status deleted 행을 쌓음).
  - 비밀값(AUTH_SECRET, 각 사의 client secret)은 .env / Streamlit Secrets 에만.

키가 없으면 해당 버튼에 '아직 준비 중' 안내만 띄우고 앱은 손님 모드(IP 닉네임)로 그대로 돈다.
"""
from __future__ import annotations

from . import nickrule

import re

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from .guard import mask, scan

COOKIE = "aw_session"
SESSION_DAYS = 30
STATE_MAX_AGE = 600          # 동의 화면에서 10분 안에 돌아와야 한다
MAX_NICK = 16

HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at",
           "provider", "nickname", "agreed_at", "avatar"]
MAX_AVATAR = 500
PROVIDER_LABEL = {"kakao": "카카오", "naver": "네이버", "local": "아이디"}

PROVIDERS = {
    "kakao": {
        "label": "카카오",
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
        "profile": "https://kapi.kakao.com/v2/user/me",
        "id_env": "KAKAO_LOGIN_CLIENT_ID",          # 카카오 REST API 키
        "secret_env": "KAKAO_LOGIN_CLIENT_SECRET",  # 보안 > Client Secret (켰을 때만)
        # scope 를 콕 집어 요청하지 않는다: 카카오 앱에 '닉네임' 동의항목이 켜져 있지 않으면 로그인 뒤
        # "서비스 관리자에게 문의하세요(KOE205)" 로 막힌다. 비워 두면 켜 둔 동의항목만 묻고, 닉네임은 가입 화면에서 정한다
        "scope": "",
        # 로그아웃한 뒤 다시 누르면 카카오가 브라우저에 남은 카카오 로그인으로 예전 계정을 바로 통과시킨다.
        # 계정 고르는 화면을 늘 보여 줘서 다른 계정으로 가입·로그인할 수 있게 한다 (11/18 요청)
        "extra": {"prompt": "select_account"},
    },
    "naver": {
        "label": "네이버",
        "authorize": "https://nid.naver.com/oauth2.0/authorize",
        "token": "https://nid.naver.com/oauth2.0/token",
        "profile": "https://openapi.naver.com/v1/nid/me",
        "id_env": "NAVER_LOGIN_CLIENT_ID",
        "secret_env": "NAVER_LOGIN_CLIENT_SECRET",
        "scope": "",                                 # 네이버는 개발자센터에서 '별명'만 체크
        "extra": {"auth_type": "reauthenticate"},    # 같은 이유로 네이버 로그인을 다시 확인한다
    },
}


class AuthError(RuntimeError):
    """사용자에게 그대로 보여 줘도 되는 한국어 메시지만 담는다."""


@dataclass
class Identity:
    provider: str
    member_key: str          # 소금 친 해시. 저장소의 entry_id
    nickname: str            # 카카오·네이버가 준 별명 (가입 화면 기본값)
    avatar: str = ""         # 카카오·네이버 프로필 사진 주소 (있으면 가입할 때 그대로 씀, 마이페이지에서 바꿀 수 있음)


# ------------------------------------------------------------------ 설정
def _secret() -> bytes:
    s = os.getenv("AUTH_SECRET", "")
    if len(s) < 16:
        raise AuthError("로그인 설정이 끝나지 않았어요 (AUTH_SECRET). 관리자에게 알려 주세요.")
    return s.encode()


def base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")


def redirect_uri() -> str:
    return f"{base_url()}/auth"


def enabled(provider: str) -> bool:
    p = PROVIDERS.get(provider)
    if not p or not os.getenv(p["id_env"]) or len(os.getenv("AUTH_SECRET", "")) < 16:
        return False
    return provider != "naver" or bool(os.getenv(p["secret_env"]))   # 네이버는 secret 필수


# ------------------------------------------------------------------ 서명
def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode().rstrip("=")


def _unb64(s: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)))


def make_state(provider: str) -> str:
    """동의 화면에 들고 갔다 돌아오는 값. 돌아오면 새 세션이라 서버 메모리 대신 서명으로 확인한다."""
    body = _b64({"p": provider, "n": secrets.token_urlsafe(8), "t": int(time.time())})
    return f"{body}.{_sign(body)}"


def check_state(state: str) -> str:
    try:
        body, sig = state.rsplit(".", 1)
        data = _unb64(body)
    except Exception:
        raise AuthError("로그인 요청이 올바르지 않아요. 처음부터 다시 시도해 주세요.") from None
    if not hmac.compare_digest(sig, _sign(body)):
        raise AuthError("로그인 요청이 위조됐을 수 있어 막았어요. 처음부터 다시 시도해 주세요.")
    if time.time() - int(data.get("t", 0)) > STATE_MAX_AGE:
        raise AuthError("로그인 시간이 지났어요 (10분). 처음부터 다시 시도해 주세요.")
    if data.get("p") not in PROVIDERS:
        raise AuthError("알 수 없는 로그인 방법이에요.")
    return data["p"]


def make_session(member_key: str, provider: str) -> str:
    body = _b64({"k": member_key, "p": provider, "e": int(time.time()) + SESSION_DAYS * 86400})
    return f"{body}.{_sign(body)}"


def read_session(token: str | None) -> dict | None:
    """쿠키 → {'k': member_key, 'p': provider}. 서명이 틀렸거나 만료면 None."""
    if not token or "." not in token:
        return None
    try:
        body, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(sig, _sign(body)):
            return None
        data = _unb64(body)
    except Exception:
        return None
    return data if int(data.get("e", 0)) > time.time() else None


# ------------------------------------------------------------------ OAuth
def authorize_url(provider: str) -> str:
    p = PROVIDERS[provider]
    q = {"response_type": "code", "client_id": os.getenv(p["id_env"], ""),
         "redirect_uri": redirect_uri(), "state": make_state(provider)}
    if p["scope"]:
        q["scope"] = p["scope"]
    q.update(p.get("extra", {}))
    return f'{p["authorize"]}?{urlencode(q)}'


def member_key(provider: str, uid: str) -> str:
    salt = os.getenv("REVIEW_NICK_SALT", "popup-cafe-map")
    return hashlib.sha256(f"{salt}:member:{provider}:{uid}".encode()).hexdigest()[:16]


def exchange(code: str, state: str, timeout: float = 10.0) -> Identity:
    """돌아온 code 로 토큰을 받고 프로필에서 고유 번호·별명만 읽는다."""
    provider = check_state(state)
    p = PROVIDERS[provider]
    data = {"grant_type": "authorization_code", "client_id": os.getenv(p["id_env"], ""),
            "redirect_uri": redirect_uri(), "code": code}
    if os.getenv(p["secret_env"]):
        data["client_secret"] = os.getenv(p["secret_env"])
    if provider == "naver":
        data["state"] = state
    try:
        tok = requests.post(p["token"], data=data, timeout=timeout).json()
        access = tok.get("access_token")
        if not access:
            raise AuthError(f'{p["label"]} 로그인 확인에 실패했어요. 다시 시도해 주세요.')
        prof = requests.get(p["profile"], headers={"Authorization": f"Bearer {access}"}, timeout=timeout).json()
    except requests.RequestException:
        raise AuthError(f'{p["label"]} 서버에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.') from None

    if provider == "kakao":
        uid = str(prof.get("id") or "")
        kp = (prof.get("kakao_account") or {}).get("profile") or {}
        nick = kp.get("nickname") or (prof.get("properties") or {}).get("nickname") or ""
        pic = "" if kp.get("is_default_image") else (kp.get("profile_image_url") or kp.get("thumbnail_image_url")
                                                      or (prof.get("properties") or {}).get("profile_image") or "")
    else:
        res = prof.get("response") or {}
        uid, nick = str(res.get("id") or ""), res.get("nickname") or ""
        pic = res.get("profile_image") or ""
    if not uid:
        raise AuthError(f'{p["label"]} 계정 정보를 받지 못했어요. 동의 화면에서 필수 항목을 확인해 주세요.')
    return Identity(provider=provider, member_key=member_key(provider, uid), nickname=clean_nick(nick),
                    avatar=clean_avatar(pic))


# ------------------------------------------------------------------ 회원 기록
def clean_nick(nick: str) -> str:
    return mask(" ".join(str(nick or "").split()))[:MAX_NICK]


_AVATAR_URL = re.compile(r"https://[A-Za-z0-9._~:/?#\[\]@!$&()*+,;=%-]+")
_AVATAR_FILE = re.compile(r"[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)")


def clean_avatar(value) -> str:
    """프로필 사진 값: https 주소(카카오·네이버) · static/uploads 파일 이름 · 'none'(기본 그림을 고름) · ''(아직 안 정함).
    그 밖의 값은 버린다 (화면 HTML 에 들어가므로 따옴표·공백 같은 글자를 막는다)."""
    v = str(value or "").strip()
    if v == "none":
        return v
    if v.startswith("http://"):
        v = "https://" + v[len("http://"):]
    if len(v) <= MAX_AVATAR and _AVATAR_URL.fullmatch(v):
        return v
    if _AVATAR_FILE.fullmatch(v):
        return v
    return ""


def validate_nick(nick: str) -> list[str]:
    n = " ".join(str(nick or "").split())
    errors = []
    if len(n) < 2:
        errors.append("닉네임은 2자 이상 적어 주세요.")
    if len(n) > MAX_NICK:
        errors.append(f"닉네임은 {MAX_NICK}자까지예요.")
    if "#" in n:
        errors.append("닉네임에 # 은 쓸 수 없어요 (뒤에 자동으로 붙어요).")
    if scan(n):
        errors.append("닉네임에 전화번호·이메일 같은 개인정보는 넣을 수 없어요.")
    bad = nickrule.problem(n)
    if bad == "사칭":
        errors.append("관리자·운영자로 오해할 수 있는 닉네임은 쓸 수 없어요.")
    elif bad:
        errors.append("욕설이나 음란한 말이 든 닉네임은 쓸 수 없어요. 다른 닉네임을 골라 주세요.")
    return errors


def nick_taken(store, nickname: str, except_key: str | None = None) -> bool:
    """다른 회원이 이미 쓰는 닉네임인가 (띄어쓰기·대소문자 차이는 같은 것으로 본다). 탈퇴한 회원은 빼고."""
    return any(nickrule.same(r.get("nickname"), nickname) and str(r.get("entry_id")) != str(except_key or "")
               for r in store.current_rows())


def _check_unique(store, nickname: str, except_key: str | None = None) -> None:
    if nick_taken(store, nickname, except_key):
        raise AuthError("이미 다른 회원이 쓰고 있는 닉네임이에요. 다른 닉네임을 골라 주세요.")


def find(store, key: str) -> dict | None:
    """가입한 회원이면 최신 행, 아니면(또는 탈퇴했으면) None."""
    row = next((r for r in store.current_rows() if str(r.get("entry_id")) == key), None)
    return row


def signup(store, ident: Identity, nickname: str) -> dict:
    errors = validate_nick(nickname)
    if errors:
        raise AuthError(errors[0])
    _check_unique(store, nickname, ident.member_key)
    return store.append({"provider": ident.provider, "nickname": " ".join(nickname.split()),
                         "agreed_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "avatar": clean_avatar(ident.avatar)},
                        entry_id=ident.member_key)


def rename(store, row: dict, nickname: str) -> dict:
    errors = validate_nick(nickname)
    if errors:
        raise AuthError(errors[0])
    _check_unique(store, nickname, str(row["entry_id"]))
    return store.append({"provider": row.get("provider", ""), "nickname": " ".join(nickname.split()),
                         "agreed_at": row.get("agreed_at", ""), "avatar": clean_avatar(row.get("avatar"))},
                        entry_id=str(row["entry_id"]))


def set_avatar(store, row: dict, avatar: str) -> dict:
    """프로필 사진만 바꾼다 ('none' = 기본 그림). 닉네임·동의 시각은 그대로 잇는다."""
    return store.append({"provider": row.get("provider", ""), "nickname": row.get("nickname", ""),
                         "agreed_at": row.get("agreed_at", ""), "avatar": clean_avatar(avatar)},
                        entry_id=str(row["entry_id"]))


def withdraw(store, row: dict) -> dict:
    """탈퇴: 지우지 않고 'deleted' 행을 쌓는다. 닉네임은 남기지 않는다."""
    return store.append({"provider": row.get("provider", ""), "nickname": "", "agreed_at": "", "avatar": ""},
                        entry_id=str(row["entry_id"]), status="deleted")


def display_name(row: dict) -> str:
    """리뷰·수정 이력에 쓸 이름. 끝의 #네 글자는 회원 번호로 정해져 '내 글' 확인에 쓰인다."""
    # 회원은 '#m' + 4자 — 손님의 IP 표식(16진수 4자)과 절대 겹치지 않는다
    return f'{row.get("nickname", "")}#m{str(row.get("entry_id"))[:4]}'


# ================================================================== 아이디·비밀번호 가입 (간편 로그인과 별개)
# 받는 것: 아이디 · 비밀번호 · 닉네임 · 약관 동의. 이메일·전화번호·실명은 받지 않는다.
# 비밀번호 원문은 저장하지 않는다.
#   - supabase 모드: DB 함수(register_login / check_login …)가 bcrypt 로 해시하고 비교한다. 해시는 DB 밖으로 안 나온다 (005)
#   - local 모드: data/credentials.json 에 scrypt 해시 (깃 제외)
import re as _re
from pathlib import Path as _Path

LOGIN_ID_RE = _re.compile(r"^[a-z0-9_]{4,20}$")
PW_MIN, PW_MAX = 8, 72
MAX_FAILS, LOCK_SECONDS = 5, 300          # 같은 화면에서 5번 틀리면 5분 잠금 (무작위 대입 늦추기)
_CRED_FILE = _Path(os.getenv("ANIWHERE_DATA_DIR") or _Path(__file__).resolve().parent.parent / "data") / "credentials.json"


def validate_signup(login_id: str, pw: str, pw2: str, nickname: str) -> list[str]:
    errors = []
    lid = (login_id or "").strip().lower()
    if not LOGIN_ID_RE.match(lid):
        errors.append("아이디는 영어 소문자·숫자·밑줄(_)로 4~20자예요.")
    if scan(lid):
        errors.append("아이디에 전화번호 같은 개인정보는 쓸 수 없어요.")
    if not (PW_MIN <= len(pw or "") <= PW_MAX):
        errors.append(f"비밀번호는 {PW_MIN}~{PW_MAX}자예요.")
    elif not (_re.search(r"[A-Za-z]", pw) and _re.search(r"\d", pw)):
        errors.append("비밀번호에 영문과 숫자를 함께 넣어 주세요.")
    elif lid and lid in pw.lower():
        errors.append("비밀번호에 아이디를 넣지 말아 주세요.")
    if pw != pw2:
        errors.append("비밀번호 확인이 달라요.")
    errors += validate_nick(nickname)
    return errors


def _supabase() -> tuple[str, dict] | None:
    url, key = os.getenv("SUPABASE_URL", "").rstrip("/"), os.getenv("SUPABASE_KEY", "")
    if os.getenv("STORAGE_MODE", "local").lower() != "supabase" or not url or not key:
        return None
    headers = {"apikey": key, "Content-Type": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    return url, headers


def _rpc(name: str, **params):
    url, headers = _supabase()
    try:
        r = requests.post(f"{url}/rest/v1/rpc/{name}", headers=headers, json=params, timeout=10)
    except requests.RequestException:
        raise AuthError("서버에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.") from None
    if r.status_code >= 400:
        raise AuthError("요청을 처리하지 못했어요. 입력을 확인해 주세요.")
    return r.json()


# ---- local 모드 (scrypt) ----
def _scrypt(pw: str, salt: bytes) -> str:
    return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32).hex()


def _cred_load() -> dict:
    try:
        return json.loads(_CRED_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _cred_save(data: dict) -> None:
    _CRED_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CRED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def login_exists(login_id: str) -> bool:
    lid = (login_id or "").strip().lower()
    if _supabase():
        return bool(_rpc("login_exists", p_login_id=lid))
    return lid in _cred_load()


def register_password(store, login_id: str, pw: str, pw2: str, nickname: str) -> dict:
    """아이디 가입: 비밀번호를 해시로 저장하고 회원 기록(members, provider='local')을 쌓는다."""
    errors = validate_signup(login_id, pw, pw2, nickname)
    if errors:
        raise AuthError(errors[0])
    lid = login_id.strip().lower()
    key = member_key("local", lid)
    _check_unique(store, nickname, key)          # 비밀번호를 만들기 전에 막는다 (닉네임 때문에 반쯤 가입되는 일 없게)
    if _supabase():
        if not _rpc("register_login", p_login_id=lid, p_password=pw, p_member_key=key):
            raise AuthError("이미 있는 아이디예요. 다른 아이디를 골라 주세요.")
    else:
        data = _cred_load()
        if lid in data:
            raise AuthError("이미 있는 아이디예요. 다른 아이디를 골라 주세요.")
        salt = secrets.token_bytes(16)
        data[lid] = {"member_key": key, "salt": salt.hex(), "hash": _scrypt(pw, salt)}
        _cred_save(data)
    return signup(store, Identity(provider="local", member_key=key, nickname=nickname), nickname)


def check_password(login_id: str, pw: str) -> str | None:
    """맞으면 회원 번호, 틀리면 None. 아이디가 없는지 비밀번호가 틀렸는지는 알려 주지 않는다."""
    lid = (login_id or "").strip().lower()
    if not lid or not pw:
        return None
    if _supabase():
        return _rpc("check_login", p_login_id=lid, p_password=pw) or None
    rec = _cred_load().get(lid)
    if not rec:
        _scrypt(pw, b"0" * 16)        # 없는 아이디도 같은 시간이 걸리게
        return None
    ok = hmac.compare_digest(rec["hash"], _scrypt(pw, bytes.fromhex(rec["salt"])))
    return rec["member_key"] if ok else None


def change_password(login_id: str, old: str, new: str, new2: str) -> None:
    lid = (login_id or "").strip().lower()
    if new != new2:
        raise AuthError("새 비밀번호 확인이 달라요.")
    errs = [e for e in validate_signup(lid, new, new, "닉네임") if "비밀번호" in e]
    if errs:
        raise AuthError(errs[0])
    if _supabase():
        if not _rpc("change_password", p_login_id=lid, p_old=old, p_new=new):
            raise AuthError("아이디나 지금 비밀번호가 맞지 않아요.")
        return
    if not check_password(lid, old):
        raise AuthError("아이디나 지금 비밀번호가 맞지 않아요.")
    data = _cred_load()
    salt = secrets.token_bytes(16)
    data[lid].update({"salt": salt.hex(), "hash": _scrypt(new, salt)})
    _cred_save(data)


def drop_password(login_id: str, pw: str) -> None:
    """탈퇴할 때 아이디·비밀번호 해시를 지운다 (비밀번호 확인 필요)."""
    lid = (login_id or "").strip().lower()
    if _supabase():
        if not _rpc("drop_login", p_login_id=lid, p_password=pw):
            raise AuthError("아이디나 비밀번호가 맞지 않아요.")
        return
    if not check_password(lid, pw):
        raise AuthError("아이디나 비밀번호가 맞지 않아요.")
    data = _cred_load()
    data.pop(lid, None)
    _cred_save(data)


# ================================================================== 탈퇴 회원 개인정보 파기 (11/18)
WITHDRAWN = "탈퇴한 회원"


def purge_withdrawn(member_key_: str) -> bool:
    """탈퇴 직후 지난 기록까지 지운다 (개인정보 보호법 '파기').
    저장소는 append-only 지만 법적 파기는 예외로 예전 행을 고친다: 닉네임·사진 빈 값, 리뷰 작성자 '탈퇴한 회원',
    접속 기록·받은 알림·아이디/비밀번호 해시 삭제. supabase 는 DB 함수(009), local(개발용)은 파일을 직접 고친다."""
    if _supabase():
        try:
            return bool(_rpc("purge_withdrawn", p_member_key=member_key_))
        except AuthError:
            return False
    import json as _json
    from . import storage as _storage
    base = _storage.LOCAL_DIR
    tag = f"#m{member_key_[:4]}"

    def rewrite(name: str, fn) -> None:
        path = base / f"{name}.json"
        if not path.exists():
            return
        rows = _json.loads(path.read_text(encoding="utf-8") or "[]")
        path.write_text(_json.dumps(fn(rows), ensure_ascii=False, indent=2), encoding="utf-8")

    def members(rows):
        for r in rows:
            if str(r.get("entry_id")) == member_key_:
                r["nickname"], r["avatar"] = "", ""
        return rows

    def reviews(rows):
        for r in rows:
            if str(r.get("nickname") or "").endswith(tag):
                r["nickname"] = WITHDRAWN + tag
        return rows

    def requests_(rows):
        for r in rows:
            if str(r.get("requester")) == member_key_:
                r["requester_nick"] = ""
        return rows

    rewrite("members", members)
    rewrite("reviews", reviews)
    rewrite("del_requests", requests_)
    rewrite("visits", lambda rows: [r for r in rows if str(r.get("member")) != member_key_])
    rewrite("notices", lambda rows: [r for r in rows if str(r.get("target")) != member_key_])
    data = _cred_load()
    for lid in [k for k, v in data.items() if v.get("member_key") == member_key_]:
        data.pop(lid, None)
    _cred_save(data)
    return True
