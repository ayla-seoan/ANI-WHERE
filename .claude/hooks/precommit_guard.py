"""커밋 전 검사 훅. CLAUDE.md 의 '민감정보' · '프롬프트' 규칙을 사람이 아니라 기계가 지키게 한다.

두 가지로 돈다.
  1. Claude Code 훅 (PreToolUse · Bash): Claude 가 `git commit` 을 하려 하면 먼저 검사하고, 걸리면 막는다 (exit 2).
  2. git pre-commit 훅: `git config core.hooksPath .githooks` 한 번이면 사람이 직접 커밋할 때도 같은 검사가 돈다.

검사하는 것 (스테이징된 변경만 본다):
  - 올리면 안 되는 파일: .env, service_account.json, *.pem
  - 새로 더한 줄의 비밀 키: OpenAI(sk-...), Supabase/JWT(eyJ...), 긴 토큰 = 값
  - 새로 더한 줄의 민감정보: common/guard.py 의 PATTERNS (전화번호·이메일·주민번호·카드·계좌)
  - 코드 안 프롬프트: .py 에 '너는 ... 추출기/안내원' 같은 시스템 프롬프트 문장 → common/prompts/ 로 옮길 것
막은 기록은 logs/hooks.jsonl 에 남긴다 (훅이 실제로 몇 번 막았는지가 발표 지표).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BLOCK_FILES = re.compile(r"(^|/)(\.env|service_account\.json|[^/]+\.pem)$")
SECRETS = {
    "OpenAI 키": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "JWT/Supabase 키": re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),
    "토큰 값": re.compile(r"(?i)(?:token|secret|api_key|apikey|password)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{24,}"),
}
PROMPT_IN_CODE = re.compile(r"너는 .{0,40}(?:추출기|안내원|분석가|도우미|역할)")
# 민감정보 검사에서 빼는 것: 예시·문서용 주소, 이미 가린 값
ALLOW = re.compile(r"noreply@|example\.(?:com|org)|@anthropic\.com|●")
URL = re.compile(r"https?://\S+")
SKIP_PATHS = re.compile(r"^(?:common/guard\.py|\.claude/hooks/|supabase/migrations/|scripts/check_supabase_rls\.py|tests/)")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def check() -> list[str]:
    problems: list[str] = []
    for name in _git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines():
        if BLOCK_FILES.search(name):
            problems.append(f"{name}: 비밀 파일은 올리지 않습니다 (.gitignore 확인)")

    try:
        from common.guard import PATTERNS
    except Exception:            # guard 를 못 읽어도 키 검사는 계속한다
        PATTERNS = {}

    current = ""
    for line in _git("diff", "--cached", "-U0", "--no-color").splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else ""
            continue
        if not line.startswith("+") or line.startswith("+++") or not current:
            continue
        added = line[1:]
        for kind, pat in SECRETS.items():
            if pat.search(added):
                problems.append(f"{current}: {kind} 로 보이는 값이 있습니다 → .env / Streamlit Secrets 로 옮기세요")
        if SKIP_PATHS.match(current):
            continue
        if current.endswith(".py") and PROMPT_IN_CODE.search(added):
            problems.append(f"{current}: 코드 안에 프롬프트 문장이 있습니다 → common/prompts/<이름>.<버전>.txt 로 옮기세요")
        if ALLOW.search(added):
            continue
        added = URL.sub(" ", added)      # 주소 속 긴 숫자(트윗·기사 번호)는 개인정보가 아니다
        for kind, pat in PATTERNS.items():
            if pat.search(added):
                problems.append(f"{current}: {kind} 로 보이는 값이 있습니다 → guard.mask() 로 가리거나 지우세요")
                break
    # 같은 문제가 여러 줄에서 나오면 한 번만
    return list(dict.fromkeys(problems))


def _log(problems: list[str], via: str) -> None:
    path = ROOT / "logs" / "hooks.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "hook": "precommit_guard",
                            "via": via, "blocked": True, "problems": problems}, ensure_ascii=False) + "\n")


def main() -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):    # Windows 콘솔(cp949)에서도 한글이 깨지지 않게
        stream.reconfigure(encoding="utf-8")
    if "--git" in sys.argv:          # git pre-commit 훅으로 불렸을 때
        via = "git"
    else:                            # Claude Code PreToolUse 훅: stdin 의 명령이 git commit 일 때만 검사
        try:
            event = json.load(sys.stdin)
        except Exception:
            return 0
        command = str(event.get("tool_input", {}).get("command", ""))
        if not re.search(r"\bgit\b[^|;&]*\bcommit\b", command):
            return 0
        via = "claude"
    problems = check()
    if not problems:
        return 0
    _log(problems, via)
    sys.stderr.write("[커밋 전 검사] 다음 문제 때문에 커밋을 막았습니다:\n- " + "\n- ".join(problems) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
