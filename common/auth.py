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
           "provider", "nickname", "agreed_at"]

PROVIDERS = {
    "kakao": {
        "label": "카카오",
        "authorize": "https://kauth.kakao.com/oauth/authorize",
        "token": "https://kauth.kakao.com/oauth/token",
        "profile": "https://kapi.kakao.com/v2/user/me",
        "id_env": "KAKAO_LOGIN_CLIENT_ID",          # 카카오 REST API 키
        "secret_env": "KAKAO_LOGIN_CLIENT_SECRET",  # 보안 > Client Secret (켰을 때만)
        "scope": "profile_nickname",
    },
    "naver": {
        "label": "네이버",
        "authorize": "https://nid.naver.com/oauth2.0/authorize",
        "token": "https://nid.naver.com/oauth2.0/token",
        "profile": "https://openapi.naver.com/v1/nid/me",
        "id_env": "NAVER_LOGIN_CLIENT_ID",
        "secret_env": "NAVER_LOGIN_CLIENT_SECRET",
        "scope": "",                                 # 네이버는 개발자센터에서 '별명'만 체크
    },
}


class AuthError(RuntimeError):
    """사용자에게 그대로 보여 줘도 되는 한국어 메시지만 담는다."""


@dataclass
class Identity:
    provider: str
    member_key: str          # 소금 친 해시. 저장소의 entry_id
    nickname: str            # 카카오·네이버가 준 별명 (가입 화면 기본값)


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
        nick = ((prof.get("kakao_account") or {}).get("profile") or {}).get("nickname") \
            or (prof.get("properties") or {}).get("nickname") or ""
    else:
        res = prof.get("response") or {}
        uid, nick = str(res.get("id") or ""), res.get("nickname") or ""
    if not uid:
        raise AuthError(f'{p["label"]} 계정 정보를 받지 못했어요. 동의 화면에서 필수 항목을 확인해 주세요.')
    return Identity(provider=provider, member_key=member_key(provider, uid), nickname=clean_nick(nick))


# ------------------------------------------------------------------ 회원 기록
def clean_nick(nick: str) -> str:
    return mask(" ".join(str(nick or "").split()))[:MAX_NICK]


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
    return errors


def find(store, key: str) -> dict | None:
    """가입한 회원이면 최신 행, 아니면(또는 탈퇴했으면) None."""
    row = next((r for r in store.current_rows() if str(r.get("entry_id")) == key), None)
    return row


def signup(store, ident: Identity, nickname: str) -> dict:
    errors = validate_nick(nickname)
    if errors:
        raise AuthError(errors[0])
    return store.append({"provider": ident.provider, "nickname": " ".join(nickname.split()),
                         "agreed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, entry_id=ident.member_key)


def rename(store, row: dict, nickname: str) -> dict:
    errors = validate_nick(nickname)
    if errors:
        raise AuthError(errors[0])
    return store.append({"provider": row.get("provider", ""), "nickname": " ".join(nickname.split()),
                         "agreed_at": row.get("agreed_at", "")}, entry_id=str(row["entry_id"]))


def withdraw(store, row: dict) -> dict:
    """탈퇴: 지우지 않고 'deleted' 행을 쌓는다. 닉네임은 남기지 않는다."""
    return store.append({"provider": row.get("provider", ""), "nickname": "", "agreed_at": ""},
                        entry_id=str(row["entry_id"]), status="deleted")


def display_name(row: dict) -> str:
    """리뷰·수정 이력에 쓸 이름. 끝의 #네 글자는 회원 번호로 정해져 '내 글' 확인에 쓰인다."""
    # 회원은 '#m' + 4자 — 손님의 IP 표식(16진수 4자)과 절대 겹치지 않는다
    return f'{row.get("nickname", "")}#m{str(row.get("entry_id"))[:4]}'
