"""안정성 방어: 민감정보 차단 + 이상 입력 차단.

두 앱이 같은 함수를 쓴다. 발표 때 "한 번 만들어 두 곳에서 막았다"로 설명한다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

# ------------------------------------------------------------- 민감정보
# 한국 환경에서 팝업 카페 공지·백로그 설명에 실제로 섞여 들어오는 것들.
# 순서가 중요하다: 겹치면 먼저 잡힌 쪽 이름이 남으므로 긴 형식(주민번호·카드번호)을 앞에 둔다.
PATTERNS: dict[str, re.Pattern] = {
    "주민등록번호": re.compile(r"\d{6}[-\s]?[1-4]\d{6}"),
    "카드번호": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "전화번호": re.compile(r"01[016-9][-.\s]?\d{3,4}[-.\s]?\d{4}"),
    "이메일": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    # 은행마다 자릿수 묶음이 다르다 (110-456-789012, 3333-02-1234567, 1002-123-456789).
    # 숫자가 10~14개일 때만 본다 — 2026-11-01 같은 날짜(8개)는 걸리지 않는다
    "계좌번호": re.compile(r"(?<![\d-])(?=(?:\d-?){10,14}(?![\d-]))\d{2,6}-\d{2,6}-\d{2,7}(?:-\d{1,3})?(?![\d-])"),
}


@dataclass
class Finding:
    kind: str
    text: str


def scan(text: str) -> list[Finding]:
    """민감정보로 의심되는 부분을 모두 찾는다."""
    found: list[Finding] = []
    taken: list[tuple[int, int]] = []
    for kind, pattern in PATTERNS.items():
        for m in pattern.finditer(text or ""):
            # 010-1234-5678 이 전화번호와 계좌번호로 두 번 잡히지 않게, 먼저 잡힌 쪽만 남긴다
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append(m.span())
            found.append(Finding(kind=kind, text=m.group()))
    return found


def mask(text: str) -> str:
    """민감정보를 ●로 가린다. 저장 직전에 한 번 더 돌린다."""
    out = text or ""
    for pattern in PATTERNS.values():
        out = pattern.sub(lambda m: "●" * len(m.group()), out)
    return out


# ------------------------------------------------------------- 이상 입력
@dataclass
class Validation:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)


REQUIRED_BACKLOG_COLUMNS = ["id", "title", "description", "effort_days"]


def validate_backlog(df) -> Validation:
    """주제 1: 업로드된 CSV 가 쓸 수 있는 모양인지."""
    v = Validation(ok=True)
    if df is None or len(df) == 0:
        v.fail("행이 하나도 없습니다. 헤더만 있는 파일은 아닌지 확인해 주세요.")
        return v

    missing = [c for c in REQUIRED_BACKLOG_COLUMNS if c not in df.columns]
    if missing:
        v.fail(f"필수 컬럼이 없습니다: {', '.join(missing)}")

    if "id" in df.columns and df["id"].duplicated().any():
        dup = df.loc[df["id"].duplicated(), "id"].tolist()[:5]
        v.fail(f"id 가 중복됩니다: {dup}")

    if "effort_days" in df.columns:
        bad = df[~df["effort_days"].apply(_is_positive_number)]
        if len(bad):
            v.fail(f"effort_days 가 숫자가 아닌 행이 {len(bad)}개 있습니다.")

    for col in ("title", "description"):
        if col in df.columns:
            hits = sum(len(scan(str(x))) for x in df[col])
            if hits:
                v.warnings.append(
                    f"{col} 에 민감정보로 보이는 값이 {hits}건 있어 가린 뒤 전송합니다."
                )
    return v


def _is_positive_number(x) -> bool:
    try:
        return float(x) > 0
    except (TypeError, ValueError):
        return False


def validate_cafe(entry, today: date | None = None, existing: list | None = None) -> Validation:
    """주제 2: 지도에 올려도 되는 등록 건인지."""
    today = today or date.today()
    v = Validation(ok=True)

    if not entry.cafe_name.strip():
        v.fail("카페명이 비어 있습니다.")
    if not entry.address.strip():
        v.fail("주소가 없으면 지도에 표시할 수 없습니다.")
    if entry.end_date < entry.start_date:
        v.fail("종료일이 시작일보다 빠릅니다.")
    if entry.end_date < today:
        v.fail(f"이미 끝난 일정입니다 (종료 {entry.end_date}).")
    # 팝업은 한두 달 가는 경우가 많다. 석 달을 넘으면 날짜를 잘못 읽었을 가능성이 크다
    if (entry.end_date - entry.start_date).days > 90:
        v.warnings.append("기간이 90일을 넘습니다. 날짜를 잘못 읽었을 수 있습니다.")

    blob = " ".join([entry.cafe_name, entry.work, *entry.characters,
                     entry.address, *entry.perks, *entry.goods])
    for f in scan(blob):
        v.fail(f"{f.kind}로 보이는 값이 들어 있어 저장하지 않습니다.")

    # 같은 매장(애니메이트 카페 등)은 작품을 바꿔 가며 콜라보를 연다.
    # 그래서 카페명·주소에 작품까지 같을 때만 중복으로 본다.
    for row in existing or []:
        if (
            row.get("cafe_name") == entry.cafe_name
            and row.get("address") == entry.address
            and str(row.get("work") or "").strip() == entry.work.strip()
            and row.get("status") != "deleted"
        ):
            v.fail("같은 카페·주소에 같은 작품이 이미 등록되어 있습니다.")
            break

    if entry.confidence == "low":
        v.warnings.append("원문에 정보가 흐릿합니다. 저장 전에 직접 확인해 주세요.")
    return v
