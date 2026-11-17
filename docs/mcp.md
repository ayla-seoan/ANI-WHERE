# MCP 활용 기록

ANI:WHERE 에서 MCP(Model Context Protocol)로 Claude 를 외부 도구에 연결해 쓴 곳과, 사람이 정한 것을 적는다.

## 1. Notion MCP — 주간 팝업 수집 (사용 중)

| 항목 | 내용 |
| --- | --- |
| 무엇을 | 매일 08:00 Claude 예약 작업 '애니 팝업·콜라보 매일 수집' (11/17 주 1회 → 매일로 변경) 이 RE:CAL 상세 페이지를 읽고, Notion MCP 로 '🎀 애니 팝업·콜라보 트래커' DB 에 행을 만든다 |
| 규칙 | `docs/notion-import.md` 1부 (행사 × 지점 = 1행, 링크 4칸, 팝업소개 형식, 연도 검증) |
| 이어지는 흐름 | 08:40 GitHub Actions(`scripts/notion_import.py`)가 그 DB 를 읽어 `data/cafes.json` 커밋 → 11:00 Apps Script 주간 브리핑 (`automation/`) |
| 사람이 정한 것 | 포함·제외 기준(게임 업계 행사·버튜버 제외), 3개월 범위, 읽지 않을 사이트 목록, 소개를 요약하지 않고 옮긴다는 원칙 |
| 효과 (지표) | 방문 전 정보 완결률 70.0% → 85.4%, 참고 링크 70% → 86%, 팝업 소개 0% → 14% (`docs/metrics-log.md`, 기준일 10/30) |
| 규칙으로 막는 위험 | RE:CAL 이 대표 지점 좌표만 줘서 다른 지점 기간이 틀릴 수 있음 → 이벤트 칸에 "기간은 <대표지점> 기준 복사" 를 남김. 다른 해 행사를 올해로 넣을 위험 → 상세의 요일을 실제 요일과 대조하는 '연도 검증' (규칙 원문: `docs/notion-import.md` 1-1, 1-2) |

## 2. GitHub MCP — 제출·협업 (2차에서 사용)

| 쓰는 곳 | 방법 |
| --- | --- |
| 2차 작업 올리기 | 브랜치 `feat/2nd-project` → PR 생성 → `po-reviewer` 서브에이전트로 PRD 기준 검토 → 머지 |
| Actions 확인 | Notion 매일 가져오기 실행 결과·실패 로그 확인 |

> 개인 프로젝트라 리뷰어는 서브에이전트(`.claude/agents/po-reviewer.md`)가 맡는다. 리뷰 결과는 PR 본문에 붙인다.

## 3. Supabase MCP — DB 이전 (선택)

`supabase/migrations/001_init.sql` 은 Supabase 대시보드 SQL Editor 에 붙여 넣어도 되고, Supabase MCP 를 연결했다면 Claude 에게
"001_init.sql 을 적용하고 RLS 정책 목록을 보여 줘" 로 적용·확인할 수 있다. 적용 후 `python scripts/check_supabase_rls.py` 로 실제로 막히는지 확인한다 (`db.md`).

## 사람이 결정한 것 vs AI 가 한 것

| 단계 | AI(Claude + MCP) | 사람(PO) |
| --- | --- | --- |
| 수집 | 페이지 읽기, 칸 채우기, Notion 행 만들기 | 무엇을 모을지·뺄지 기준, 링크 우선순위, 소개 원칙 |
| 검수 | 형식 맞추기, 중복 지점 합치기 | 수집 결과 표본 확인, 틀린 사례를 `docs/ai-mistakes.md` 에 기록하고 규칙으로 되돌리기 |
| 배포 | Actions 가 커밋 | 매주 데이터 변화가 지표(`/stats`)에 맞게 나오는지 확인 |

## 4. 직접 만든 MCP 서버 — `mcp_server/aniwhere_server.py` (행사 조회)

Claude(Claude Code · Desktop)가 ANI:WHERE 팝업 데이터를 **도구로 조회**하게 하는 읽기 전용 MCP 서버.
"이번 주말 성수 팝업으로 인스타 문구 3개" 같은 일을 시키면 Claude 가 지어내지 않고 실제 데이터부터 찾는다.

| 도구 | 하는 일 |
| --- | --- |
| `search_popups(question, on_date, limit)` | 자연어 질문 → 작품·캐릭터·지역·날짜 조건을 읽어 찾기 (앱 '물어보기' 와 같은 `common/ask.retrieve`) |
| `list_popups(region, work, status, on_date, limit)` | 조건으로 정확히 거르기 (진행 중 / 예정 / 종료 / 전체) |
| `get_popup(popup_id)` | 한 팝업의 캐릭터·특전·굿즈·참고 링크·소개 |
| `this_weekend(region, on_date)` | 이번 주말(토·일) 열려 있는 팝업 |
| `popup_stats(on_date)` | 진행 현황, 지역·작품 상위 5, 방문 전 정보 완결률 전후 |

설계 판단
- **읽기 전용**: 쓰기 도구를 만들지 않았다. 등록·수정은 사람이 앱에서 하고 기록(editor)이 남아야 한다.
- **앱과 같은 코드**: 저장소(`Storage`, local/supabase)·검색·지표 함수를 그대로 써서 앱 화면과 MCP 답이 어긋나지 않는다.
- **안 내보내는 것**: `note`·`editor`·`source`, 리뷰 본문·닉네임. 문자열은 `guard.mask` 를 한 번 더 거친다.
- **없으면 없다고**: 0건이면 `"지어내지 마세요"` 안내를 결과에 같이 돌려준다.

쓰는 법
- Claude Code: 저장소 루트의 `.mcp.json` 에 등록돼 있다. 이 폴더에서 Claude Code 를 열면 `aniwhere` 서버 사용을 묻는다 (`pip install -r requirements-dev.txt` 필요).
- 확인: `python -X utf8 tests/mcp/check_server.py` → 실제 MCP 프로토콜(stdio)로 도구 5개를 불러 9가지를 확인한다 (11/17: 9/9).
