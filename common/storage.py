"""Google Sheets 또는 Supabase 를 저장소로 쓴다. 키가 없으면 로컬 JSON 으로 자동 전환.

STORAGE_MODE = sheets | supabase | local. 설정이 틀리면 조용히 local 로 내려가고
이유는 self.fallback_reason 에 남긴다. Supabase 는 SELECT·INSERT 만 쓴다 (db.md).

로컬 전환이 있어야 심사자가 README 만 보고 바로 돌려볼 수 있다.
모든 쓰기는 append 로만 하고, 수정·삭제도 새 행을 쌓는다.
=> 마지막 행이 현재 상태, 이전 행이 되돌릴 대상.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = Path(os.getenv("ANIWHERE_DATA_DIR") or ROOT / "data")
# 원격 저장소(Supabase) 읽기를 서버에 기억해 두는 방식 (11/18 요청: 처음에 한 번 불러오고, 매일 아침 수집 뒤 · 저장했을 때만 다시)
#  - 이 서버에서 등록·수정·리뷰·북마크를 저장하면 그 표의 기억을 바로 고친다 (append)
#  - 매일 REFRESH_AT(한국 시간, 08:40 Notion 매일 가져오기가 끝난 뒤) 이후 첫 읽기에서 새로 불러온다
#  - 혹시 다른 곳(Supabase 화면에서 직접 고침 등)에서 바뀐 것은 CACHE_SECONDS 뒤에 보인다. 0 이면 기억하지 않음
CACHE_SECONDS = float(os.getenv("STORAGE_CACHE_SECONDS", "1800"))
REFRESH_AT = os.getenv("STORAGE_REFRESH_AT", "08:45")
_READ_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_LOCK = threading.Lock()
_PROBED: dict[tuple[str, str], float] = {}     # 확인을 마친 Supabase 표 (서버마다 한 번)   # 테스트는 임시 복사본을 가리킨다


def _past_refresh(cached_at: float, now: float) -> bool:
    """기억한 뒤에 오늘(한국 시간) REFRESH_AT 이 지났으면 True → 매일 아침 수집 뒤 한 번 새로 불러온다."""
    kst = timezone(timedelta(hours=9))
    try:
        hh, mm = (int(x) for x in REFRESH_AT.split(":"))
    except ValueError:
        return False
    today = datetime.fromtimestamp(now, kst).replace(hour=hh, minute=mm, second=0, microsecond=0)
    return cached_at < today.timestamp() <= now


def refresh_all() -> None:
    """기억한 것을 모두 버린다 (다음 읽기에서 새로 불러옴). 관리자 화면의 '데이터 새로 불러오기'가 쓴다."""
    with _CACHE_LOCK:
        _READ_CACHE.clear()

HEADERS = [
    "row_id", "entry_id", "revision", "status", "updated_at",
    "cafe_name", "work", "characters", "address", "lat", "lng",
    "start_date", "end_date", "perks", "goods", "source", "note",
    "images", "tags",     # images: static/uploads/ 의 파일 이름들 (첫 번째가 포스터), tags: 이벤트 추가 정보
    "links",              # 참고 웹사이트 주소들 (공백으로 구분)
    "editor",             # 이 기록을 남긴 사람 (리뷰와 같은 IP 닉네임, 자동 수집은 'AI'). 예전 행은 비어 있다
    "intro",              # 팝업 소개 글 (간편등록은 붙여넣은 공지 그대로). 민감정보는 가려서 저장
    "intro_src",          # 팝업 소개를 옮겨 온 원문 주소 (Notion '소개출처'). 상세의 '출처 보기' 버튼
]

# Supabase 표에서 숫자 칸. 나머지는 모두 text 로 주고받는다
_SB_INT = {"revision"}
_SB_FLOAT = {"lat", "lng"}        # 빈칸 <-> null
_SB_PAGE = 1000                   # PostgREST 기본 최대 행 수
_SB_CACHE_SEC = 3.0               # 한 번 화면을 그리는 동안 같은 표를 여러 번 읽지 않게


class StorageWriteError(RuntimeError):
    """Supabase 쓰기 실패. 로컬로 몰래 쓰지 않고 바로 알린다 (재배포 때 사라지는 곳에 쓰면 더 위험)."""


class Storage:
    """append-only 저장소. sheets 모드와 local 모드가 같은 인터페이스를 쓴다."""

    def __init__(self, worksheet: str = "cafes", headers: list[str] | None = None) -> None:
        self.worksheet = worksheet
        self.headers = headers or HEADERS     # 리뷰처럼 칸이 다른 저장소는 따로 넘긴다
        self.mode = os.getenv("STORAGE_MODE", "local").lower()
        self._ws = None
        self._sb: dict | None = None
        self._sb_cache: tuple[float, list[dict]] | None = None
        self.fallback_reason = ""
        if self.mode == "sheets":
            try:
                self._ws = self._open_sheet()
            except Exception as exc:  # 자격증명 문제면 조용히 로컬로
                self.mode = "local"
                self.fallback_reason = str(exc)
        elif self.mode == "supabase":
            try:
                self._sb = self._open_supabase()
            except Exception as exc:  # URL·키가 없거나 표가 없으면 조용히 로컬로
                self.mode = "local"
                self.fallback_reason = str(exc)

    # ------------------------------------------------------------ sheets
    def _open_sheet(self):
        import gspread
        from google.oauth2.service_account import Credentials

        key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        sheet_key = os.getenv("GSHEET_KEY")
        if not key_file or not sheet_key:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE 또는 GSHEET_KEY 가 없습니다.")

        creds = Credentials.from_service_account_file(
            key_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        doc = gspread.authorize(creds).open_by_key(sheet_key)
        try:
            ws = doc.worksheet(self.worksheet)
        except Exception:
            ws = doc.add_worksheet(self.worksheet, rows=1000, cols=len(self.headers))
            ws.append_row(self.headers)
        head = ws.row_values(1)
        if not head:
            ws.append_row(self.headers)
        elif missing := [h for h in self.headers if h not in head]:
            # 나중에 생긴 칸(editor 등)은 제목 줄 오른쪽 끝에만 붙인다. 데이터 줄은 건드리지 않는다
            ws.update([head + missing], "A1")
        return ws

    # ---------------------------------------------------------- supabase
    def _open_supabase(self) -> dict:
        """PostgREST 로 표를 한 번 읽어 보고 연결 정보를 돌려준다. requests 만 쓴다 (새 의존성 없음)."""
        import requests

        url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
        key = (os.getenv("SUPABASE_KEY") or "").strip()
        if not url or not key:
            raise RuntimeError("SUPABASE_URL 또는 SUPABASE_KEY 가 없습니다.")
        conn = {
            "endpoint": f"{url}/rest/v1/{self.worksheet}",
            # 새 형식 키(sb_publishable_…)는 apikey 머리말에만, 옛 형식(anon JWT, eyJ…)은 Authorization 에도 넣는다
            "headers": {"apikey": key, **({"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {})},
        }
        # 표가 있는지 확인하는 요청은 서버(프로세스)마다 표당 한 번만 (11/18 속도 개선: 화면을 다시 그릴 때마다
        # 저장소 13개를 새로 만들며 확인 요청을 13번 보내 클릭마다 2~3초씩 걸렸다)
        probe_key = (url, self.worksheet)
        with _CACHE_LOCK:
            ok = _PROBED.get(probe_key)
        if ok and time.time() - ok < 3600:
            return conn
        res = requests.get(conn["endpoint"], headers=conn["headers"],
                           params={"select": "row_id", "limit": "1"}, timeout=10)
        if res.status_code != 200:
            raise RuntimeError(f"Supabase '{self.worksheet}' 표를 읽지 못했습니다 "
                               f"({res.status_code}): {res.text[:200]}")
        with _CACHE_LOCK:
            _PROBED[probe_key] = time.time()
        return conn

    def _sb_read(self) -> list[dict]:
        import requests

        cached = self._sb_cache
        if cached and time.monotonic() - cached[0] < _SB_CACHE_SEC:
            return [dict(r) for r in cached[1]]
        rows: list[dict] = []
        offset = 0
        while True:   # 1000 행씩 끊어 읽는다
            res = requests.get(
                self._sb["endpoint"], headers=self._sb["headers"], timeout=20,
                params={"select": "*", "order": "updated_at.asc,revision.asc,row_id.asc",
                        "limit": str(_SB_PAGE), "offset": str(offset)},
            )
            res.raise_for_status()
            page = res.json()
            rows.extend(self._from_db(r) for r in page)
            if len(page) < _SB_PAGE:
                break
            offset += _SB_PAGE
        self._sb_cache = (time.monotonic(), rows)
        return [dict(r) for r in rows]

    def _from_db(self, row: dict) -> dict:
        """DB 한 행 -> 로컬 JSON 과 같은 모양 (revision 은 int, 빈 좌표는 '', 별점은 int 또는 '')."""
        out: dict[str, Any] = {}
        for h in self.headers:
            v = row.get(h)
            if h in _SB_INT:
                out[h] = int(v or 0)
            elif h in _SB_FLOAT:
                out[h] = "" if v is None else v
            elif h == "rating":
                out[h] = int(v) if str(v or "").isdigit() else ""
            else:
                out[h] = "" if v is None else str(v)
        return out

    def _to_db(self, record: dict) -> dict:
        """앱의 한 행 -> DB 에 넣을 모양. 표에 없는 칸은 버린다."""
        out: dict[str, Any] = {}
        for h in self.headers:
            v = record.get(h, "")
            if h in _SB_INT:
                out[h] = int(v or 0)
            elif h in _SB_FLOAT:
                out[h] = None if v in ("", None) else float(v)
            else:
                out[h] = "" if v is None else str(v)
        return out

    def _sb_insert(self, records: list[dict]) -> None:
        import requests

        try:
            res = requests.post(
                self._sb["endpoint"], timeout=20,
                headers={**self._sb["headers"], "Content-Type": "application/json",
                         "Prefer": "return=minimal"},
                data=json.dumps([self._to_db(r) for r in records], ensure_ascii=False).encode("utf-8"),
            )
        except requests.RequestException as exc:
            raise StorageWriteError(f"Supabase 에 저장하지 못했습니다 (연결 실패): {exc}") from exc
        finally:
            self._sb_cache = None
        if res.status_code not in (200, 201, 204):
            # RLS(남의 리뷰 수정)·민감정보 검사·revision 충돌이 여기로 온다
            raise StorageWriteError(f"Supabase 가 저장을 거부했습니다 ({res.status_code}): {res.text[:300]}")

    # ------------------------------------------------------------- local
    @property
    def _local_path(self) -> Path:
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        return LOCAL_DIR / f"{self.worksheet}.json"

    def _read_local(self) -> list[dict]:
        if not self._local_path.exists():
            return []
        return json.loads(self._local_path.read_text(encoding="utf-8"))

    def _write_local(self, rows: list[dict]) -> None:
        self._local_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # -------------------------------------------------------------- API
    def _fresh_rows(self) -> list[dict]:
        if self.mode == "sheets" and self._ws is not None:
            return self._ws.get_all_records()
        if self.mode == "supabase" and self._sb is not None:
            return self._sb_read()
        return self._read_local()

    def _cache_key(self) -> str | None:
        """원격 저장소(Supabase·Sheets)만 잠깐 기억한다. 로컬 파일은 빨라서 늘 새로 읽는다."""
        if self.mode == "supabase" and self._sb is not None:
            return f"sb:{self.worksheet}"
        if self.mode == "sheets" and self._ws is not None:
            return f"sh:{self.worksheet}"
        return None

    def all_rows(self) -> list[dict]:
        """모든 기록. 원격 저장소는 CACHE_SECONDS 동안 한 번 읽은 것을 다시 쓴다 (11/18 속도 개선:
        화면 한 번에 같은 표를 수십 번 읽어 몇 초씩 걸렸다). 이 서버에서 쓰면 바로 반영된다."""
        key = self._cache_key()
        if key is None:
            return self._fresh_rows()
        now = time.time()
        with _CACHE_LOCK:
            hit = _READ_CACHE.get(key)
        if hit and now - hit[0] < CACHE_SECONDS and not _past_refresh(hit[0], now):
            return [dict(r) for r in hit[1]]
        rows = self._fresh_rows()
        with _CACHE_LOCK:
            _READ_CACHE[key] = (now, rows)
        return [dict(r) for r in rows]

    def current_rows(self) -> list[dict]:
        """entry_id 별로 가장 최신 revision 만, 삭제된 건 제외."""
        latest: dict[str, dict] = {}
        for row in self.all_rows():
            eid = str(row.get("entry_id"))
            prev = latest.get(eid)
            if prev is None or int(row.get("revision", 0)) >= int(prev.get("revision", 0)):
                latest[eid] = row
        return [r for r in latest.values() if r.get("status") != "deleted"]

    def append(self, payload: dict[str, Any], entry_id: str | None = None,
               status: str = "active") -> dict:
        """새 등록 또는 수정. 항상 새 행이 쌓인다."""
        rows = self._fresh_rows()          # 번호(revision)는 늘 새로 읽어서 매긴다 (기억한 값으로 매기면 겹칠 수 있음)
        entry_id = entry_id or uuid.uuid4().hex[:10]
        revision = max(
            [int(r.get("revision", 0)) for r in rows if str(r.get("entry_id")) == entry_id],
            default=0,
        ) + 1

        record = {k: "" for k in self.headers}
        record.update(payload)
        record.update({
            "row_id": uuid.uuid4().hex[:10],
            "entry_id": entry_id,
            "revision": revision,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        for key in ("perks", "goods"):
            if isinstance(record.get(key), list):
                record[key] = ", ".join(record[key])

        if self.mode == "sheets" and self._ws is not None:
            self._ws.append_row([str(record.get(h, "")) for h in self.headers])
        elif self.mode == "supabase" and self._sb is not None:
            self._sb_insert([record])      # 실패하면 StorageWriteError. 로컬로 대신 쓰지 않는다
        else:
            rows.append(record)
            self._write_local(rows)
        key = self._cache_key()
        if key is not None:                # 방금 읽은 것 + 이번 기록으로 기억을 바로 고친다
            with _CACHE_LOCK:
                _READ_CACHE[key] = (time.time(), rows + [record])
        return record

    def append_many(self, items: list[tuple[dict[str, Any], str]]) -> list[dict]:
        """(payload, entry_id) 여러 개를 한 번에 쌓는다 (11/20 블로그 후기 속도: append 는 한 행마다 표 전체를
        새로 읽어 글 10개면 10번 읽었다). 표는 한 번만 읽어 번호를 매기고 저장도 한 번에 보낸다.
        묶음이 거부되면(한 행의 민감정보 · 번호 충돌 등) 한 행씩 append 로 다시 쌓아 나머지는 살린다. 쌓은 행을 돌려준다."""
        if not items:
            return []
        rows = self._fresh_rows()
        top: dict[str, int] = {}
        for r in rows:
            k = str(r.get("entry_id"))
            top[k] = max(top.get(k, 0), int(r.get("revision", 0) or 0))
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        records = []
        for payload, entry_id in items:
            top[entry_id] = top.get(entry_id, 0) + 1
            record = {k: "" for k in self.headers}
            record.update(payload)
            record.update({"row_id": uuid.uuid4().hex[:10], "entry_id": entry_id, "revision": top[entry_id],
                           "status": "active", "updated_at": now})
            records.append(record)
        try:
            if self.mode == "sheets" and self._ws is not None:
                self._ws.append_rows([[str(r.get(h, "")) for h in self.headers] for r in records])
            elif self.mode == "supabase" and self._sb is not None:
                self._sb_insert(records)
            else:
                self._write_local(rows + records)
        except StorageWriteError:
            out = []
            for payload, entry_id in items:
                try:
                    out.append(self.append(payload, entry_id=entry_id))
                except StorageWriteError:
                    pass
            return out
        key = self._cache_key()
        if key is not None:
            with _CACHE_LOCK:
                _READ_CACHE[key] = (time.time(), rows + records)
        return records

    def revert(self, entry_id: str, extra: dict | None = None) -> dict | None:
        """직전 revision 을 새 행으로 다시 쌓아 되돌린다. 이력은 지우지 않는다."""
        history = sorted(
            [r for r in self.all_rows() if str(r.get("entry_id")) == str(entry_id)],
            key=lambda r: int(r.get("revision", 0)),
        )
        if len(history) < 2:
            return None
        target = history[-2]
        payload = {k: target.get(k, "") for k in self.headers
                   if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
        payload.update(extra or {})      # 되돌린 사람·방법처럼 이번 기록에만 붙는 값
        return self.append(payload, entry_id=str(entry_id), status=target.get("status", "active"))

    def restore(self, entry_id: str, revision: int, extra: dict | None = None) -> dict | None:
        """골라 둔 revision 의 내용을 새 행으로 다시 쌓는다 (수정 이력에서 원하는 버전으로 돌아가기)."""
        target = next((r for r in self.all_rows() if str(r.get("entry_id")) == str(entry_id)
                       and int(r.get("revision", 0)) == int(revision)), None)
        if target is None:
            return None
        payload = {k: target.get(k, "") for k in self.headers
                   if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
        payload.update(extra or {})
        return self.append(payload, entry_id=str(entry_id), status=target.get("status", "active"))

    def soft_delete(self, entry_id: str, extra: dict | None = None) -> dict:
        current = next(
            (r for r in self.current_rows() if str(r.get("entry_id")) == str(entry_id)), {}
        )
        payload = {k: current.get(k, "") for k in self.headers
                   if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
        payload.update(extra or {})
        return self.append(payload, entry_id=str(entry_id), status="deleted")
