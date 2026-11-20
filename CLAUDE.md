# 프로젝트 규칙

AI 코딩 도구가 이 저장소에서 작업할 때 지켜야 할 것.

## 구조
- 두 앱(`app_priority.py`, `app_cafemap.py`)이 `common/` 모듈을 **공유**한다. 한쪽에만 필요한 로직도 양쪽에서 쓸 가능성이 있으면 `common/` 에 둔다.
- 주제별 전용 로직은 `common/<주제>.py` 로 분리한다 (`priority.py`, `cafe.py`, `review.py`, `mycal.py`, `locate.py` 처럼).
- 브라우저 쪽 화면 조각은 빌드 없이 `components/<이름>/index.html` 하나로 만들고, `common/<이름>.py` 의 얇은 래퍼로 붙인다.

## ANI:WHERE 화면 작업
- `common/` 파일을 고쳤으면 실행 중인 Streamlit 을 **껐다 다시 켠다**. 새로고침만 하면 예전 모듈이 그대로 남는다.
- 화면 글자는 한국어. 새로 만드는 버튼·안내에는 이모지 대신 `:material/...:` 아이콘을 쓴다.
  - HTML 문자열 안에서는 `_mi("아이콘이름")` 을 쓴다. 짧은 알림은 `st.toast` 대신 `_toast()` (화면 가운데, 최신 것만 보임).
- 포인트 색은 CSS 변수 `--accent`(#14b8a6) · `--accent-soft` · `--accent-deep` 를 쓴다. `@import`(글꼴) 는 `<style>` 맨 앞에 둔다 — 앞에 다른 규칙이 있으면 글꼴이 무시된다.
- 모바일은 폭 640px 이하. PC 와 모바일 화면을 모두 확인한다.
- 참고 웹사이트에서 `recal.kr` 은 다른 사이트 뒤로 보낸다 (`cafe.order_links`).
- Notion 규칙은 `docs/notion-import.md` 가 기준이다 (1부: 예약 작업 '애니 팝업·콜라보 매일 수집' 의 수집 규칙, 2부: 앱 가져오기). 예약 작업 지시문이나 `notion_sync.py` 를 바꾸면 그 문서도 같이 고친다.
  - Notion DB 는 '행사 × 지점 = 1행' 이고 '지점' 칸은 형제 목록이다. 앱에서 행을 다시 나누지 않는다.
  - 매일 08:40 KST(예비 09:40 · 11:40 · 14:40) GitHub Actions(`.github/workflows/notion-sync.yml` → `scripts/notion_import.py`)가 가져와 `data/cafes.json` 을 커밋한다. 로컬에서 `data/cafes.json` 을 올리기 전에 `git pull` 로 그 커밋을 먼저 받는다.
  - 가져온 기록의 `note` 끝 `| notion:<번호>` 는 지우지 않는다 (앱에서 고쳐도 `_keep_notion` 으로 남김).
  - 팝업 소개는 Notion 기준으로 맞추되, 사람이 앱에서 쓴 소개는 덮어쓰지 않는다.
  - 실제 데이터에 넣기 전에 임시 복사본으로 먼저 돌려 본다.
- 북마크(`favorites`)·리뷰(`reviews`)도 카페와 같은 append-only 저장소다.
- 카페 기록을 쌓을 때는 수정한 사람을 `editor=_me()` (리뷰와 같은 IP 닉네임) 로 남긴다. 자동 수집은 `"AI"`.
- 닉네임 규칙(`review.nickname_for`)을 바꿔도 끝의 `#네 글자`(IP 해시) 는 그대로 둔다. 내 글 확인(`can_delete`)이 여기에 걸려 있다.
- 버튼·링크에 마우스를 올리면 뜨는 안내(`help=` · `title`)는 쓰지 않는다. 안내는 입력칸 옆 `?` 로만.

## 프롬프트
- 프롬프트는 **절대 코드 안에 문자열로 두지 않는다.** `common/prompts/<이름>.<버전>.txt` 로 둔다.
- 프롬프트를 고칠 때는 파일을 덮어쓰지 말고 **새 버전 파일을 만든다** (`cafe.v1.txt` → `cafe.v2.txt`).
- 버전은 `.env` 의 `PROMPT_VERSION` 으로 고른다.

## AI 호출
- 모든 OpenAI 호출은 `common/ai.py` 의 `call_structured()` 만 쓴다. 다른 곳에서 직접 `OpenAI()` 를 만들지 않는다.
- 응답은 반드시 Pydantic 스키마를 통과해야 한다. 통과하지 못하면 실패로 처리한다.
- `temperature=0`, `seed=42` 를 바꾸지 않는다. 재현성 지표가 여기에 걸려 있다.

## 예외 처리 원칙
- **AI가 실패해도 앱은 멈추지 않는다.** 모든 AI 호출에 규칙 기반 `fallback` 을 붙인다.
- 결과 화면에는 항상 `AI 산출` 인지 `규칙 기반 대체` 인지 표시한다. (예외: 리스트 옆·모바일 물어보기 대화창은 사용자 요청으로 표시하지 않는다. `/ask` 화면과 로그 `logs/runs.jsonl` 에는 남는다)
- 데이터가 0건일 때 빈 표를 보여주지 않는다. 다음에 할 일을 안내한다.

## 민감정보
- 전화번호·이메일·계좌번호·주민번호·카드번호는 **저장하지 않는다.**
- 외부 API로 보내기 전에 `guard.mask()` 를 거친다.
- 새 패턴을 발견하면 `common/guard.py` 의 `PATTERNS` 에 추가한다.

## 저장소
- `common/storage.py` 는 **append-only** 다. 수정·삭제도 새 행을 쌓는다 (`revision` 증가).
- 기존 행을 덮어쓰거나 지우는 코드를 쓰지 않는다. 되돌리기가 여기에 걸려 있다.
  - **예외 1:** 탈퇴 회원 개인정보 파기 (`auth.purge_withdrawn`, `supabase/migrations/009`). 법적 파기 의무라 예전 행의 닉네임·사진을 지운다.
  - **예외 2 (11/19 사용자 결정):** 내린 팝업 주간 정리 (`supabase/migrations/012`, 매주 월요일 00:10 KST pg_cron). 지난주까지 기간이 끝났거나 삭제 요청 승인으로 내린 팝업의 모든 기록 + 그 리뷰·북마크·삭제 요청을 지운다. 사진 파일은 `scripts/storage_sweep.py` 가 매일 '안 쓰는' 것만 지운다. 이 두 곳 말고는 지우는 코드를 쓰지 않는다.

## 기록
- AI가 틀린 사례를 발견하면 `docs/ai-mistakes.md` 에 한 줄 추가한다.
- 커밋 메시지에 프롬프트 버전을 바꿨으면 그 사실을 적는다.

## 개인정보
- 가입 동의는 필수(만 14세 이상 · 이용약관 · 개인정보 수집·이용)와 선택(프로필 사진)을 나눈다. 새로 받는 정보가 생기면 동의 표(`PRIVACY_TABLE`)와 `docs/privacy-policy.md` 를 같이 고친다.
- 비밀번호는 직접 저장하지 않는다 (Supabase DB 함수의 bcrypt). 선택 동의 없이 사진을 저장하지 않는다.

## 2차에서 더한 것
- 지표 계산은 `common/stats.py` 한곳에서만 한다. `/stats` 화면 · `scripts/metrics_snapshot.py` · MCP 서버가 같은 함수를 써서 숫자가 어긋나지 않게.
- 물어보기(`/ask`)의 검색은 `common/ask.py` 규칙, 답은 `ask` 프롬프트. 검색 규칙을 고치면 `python -X utf8 scripts/eval_ask.py --save` 로 전후를 남긴다.
  - 평가 세트(`samples/ask_eval.jsonl`)는 **추가만** 한다. 점수를 올리려고 기존 문항을 고치지 않는다.
  - 평가 데이터는 `DATA_ASOF` 전 기록으로 고정돼 있다. 새 데이터로 평가하려면 날짜를 바꾸고 그 사실을 기록한다.
- `docs/metrics-log.md` · `docs/ask-eval.md` · `docs/qa-results.md` · `docs/user-test/report.md` 는 날짜별로 **쌓기만** 한다.
- 저장소 모드는 `local | sheets | supabase`. Supabase 쓰기 실패는 `StorageWriteError` 로 올라온다 (조용히 로컬에 쓰지 않음). 표·정책을 바꾸면 `supabase/migrations/` 에 **새 번호 파일**을 만들고 `db.md` 를 고친다.
- 공개 웹(`web/`, Vercel)도 회원 기능(로그인·북마크·리뷰·닉네임)을 쓴다. 회원 데이터 쓰기는 **서버 코드(서버 액션·route handler)에서만**, Supabase **anon 키**로만 한다 (service_role 금지). Streamlit 과 같은 표·같은 규칙(append-only, `common/auth.py` · `review.py` · `guard.py` 를 옮긴 `web/lib/server/`)을 지킨다.
  - 비밀값(`SUPABASE_ANON_KEY` · `AUTH_SECRET` · 카카오/네이버 client secret)은 서버 환경변수에만. `NEXT_PUBLIC_` 은 카카오 지도 JS 키 하나뿐이다.
  - 로그인 쿠키(`aw_session`) 모양을 바꾸면 Streamlit 쪽도 같이 바꾸고 `cd web && npm run test:auth` 로 두 쪽이 서로 읽히는지 확인한다.
  - 회원 기능 시험은 실제 DB 가 아니라 `WEB_STORAGE=local` 로 (`web/scripts/e2e_member.py` · `e2e_extra.py` · `e2e_admin.py` · `e2e_popup.py` · `e2e_pages.py`).
  - 웹은 Streamlit 으로 넘어가는 링크를 두지 않는다 (등록하기 · 수정하기 · 되돌리기 · 삭제 요청 · 관리자 `/data` · `/stats` · 블로그 후기 · 사진 올리기 · `/privacy` `/guide` `/design` `/ask` 모두 웹 안에서). Streamlit 화면을 바꾸면 웹도 같이 바꾼다.
  - 웹에서 올린 사진은 Supabase Storage 공개 버킷 `uploads` (`supabase/migrations/011_storage.sql`) 에 서버가 EXIF 를 지우고 올리고, 저장소 칸에는 https 주소를 넣는다 (`common/images.py` 의 `Remote` 가 그 주소를 Streamlit 에서도 보여 준다).
  - 종 알림 읽음 표시는 앱과 같은 쿠키(`aw_ntf_read_<sha1(회원 번호)[:8]>`, 알림 번호 = `sha1(글)[:8]`)를 쓴다. 앱의 알림 글(`_notices` · `_why_html`)을 바꾸면 `web/lib/server/ntf.ts` 도 같이 바꾼다.
- 블로그 후기는 저장해 둔 글(`blog_posts`, 013)을 보여 준다. 네이버 검색은 `blog.refresh`(웹 `lib/server/blog.ts` 의 `refresh`)로만, 팝업마다 하루 한 번(`blog_checks`) 새 글만 더한다. 상세 · 건수 화면에서 검색을 직접 부르지 않는다 (하루 한도 429).
- 로컬 시험 서버는 `STORAGE_MODE=local`(웹 `WEB_STORAGE=local`) + 임시 데이터 폴더로만 켜고, 끝나면 끈다. 실제 `.env` 로 켠 채 두면 예전 코드가 운영 DB 에 쓴다 (11/19 이미지 사고).
- 공개 화면(웹 HTML · JS · 공유 링크)에 깃허브 주소 · 계정 이름을 넣지 않는다 (11/20, 불특정 다수에게 공유). 예전 사진은 `web/lib/uploads.ts` 의 `imgUrl`(→ `/img/…`), 원본 위치는 서버 전용 `web/lib/server/github.ts` 한곳. Streamlit 공유 링크는 `&embed=true`.
- 로컬 시험 서버를 다 쓰면 끈다 — 지난 세션 서버가 며칠씩 남아 있었다 (11/20 3000 · 3100 · 3110).
- MCP 서버(`mcp_server/`)는 읽기 전용. 쓰기 도구를 만들지 않고, `note`·`editor`·`source`·리뷰 본문·닉네임은 내보내지 않는다. stdout 에 print 하지 않는다.
- 테스트·로컬 실행은 실제 `data/` 를 바꿀 수 있다 (앱을 켜면 Notion 동기화·기간 종료 처리가 돈다). 시험할 때는 `ANIWHERE_DATA_DIR` 로 임시 복사본을 쓴다 (`tests/e2e/conftest.py` 참고).
- `.claude/hooks/` 가 커밋 전 검사(키·민감정보·코드 속 프롬프트)와 프롬프트 덮어쓰기 차단을 한다. 훅에 걸리면 우회하지 말고 원인을 고친다.
