"""파일을 고치기 전·후에 CLAUDE.md 규칙을 기계로 챙기는 훅.

  PreToolUse (Edit|Write|MultiEdit):
    - common/prompts/ 의 '이미 있는' 프롬프트 파일을 고치려 하면 막는다 (exit 2).
      규칙: 프롬프트는 덮어쓰지 말고 새 버전 파일을 만든다 (cafe.v1.txt → cafe.v2.txt).
  PostToolUse (Edit|Write|MultiEdit):
    - common/ 의 .py 를 고쳤으면 "Streamlit 을 껐다 켜야 반영된다" 를 Claude 에게 알려 준다.
      (새로고침만 하면 예전 모듈이 남는다 — 실제로 여러 번 헷갈렸던 문제)
막은 기록은 logs/hooks.jsonl 에 남긴다.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _rel(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return ""


def _log(rec: dict) -> None:
    p = ROOT / "logs" / "hooks.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "hook": "edit_rules", **rec}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):    # Windows 콘솔(cp949)에서도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    phase = event.get("hook_event_name", "")
    path = str(event.get("tool_input", {}).get("file_path", ""))
    rel = _rel(path) if path else ""
    if not rel:
        return 0

    if phase == "PreToolUse" and rel.startswith("common/prompts/") and rel.endswith(".txt") and Path(path).exists():
        _log({"blocked": True, "file": rel, "rule": "프롬프트 새 버전"})
        sys.stderr.write(f"[프롬프트 규칙] {rel} 은 이미 있는 버전입니다. 덮어쓰지 말고 다음 번호의 새 파일을 만드세요 "
                         "(예: cafe.v2.txt → cafe.v3.txt). 바꾼 이유는 prompts/README.md 에 적습니다.\n")
        return 2

    if phase == "PostToolUse" and rel.startswith("common/") and rel.endswith(".py"):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": f"{rel} 를 고쳤습니다. 실행 중인 Streamlit 은 껐다 다시 켜야 반영됩니다 (새로고침만으로는 예전 모듈이 남음).",
        }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
