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
- 결과 화면에는 항상 `AI 산출` 인지 `규칙 기반 대체` 인지 표시한다.
- 데이터가 0건일 때 빈 표를 보여주지 않는다. 다음에 할 일을 안내한다.

## 민감정보
- 전화번호·이메일·계좌번호·주민번호·카드번호는 **저장하지 않는다.**
- 외부 API로 보내기 전에 `guard.mask()` 를 거친다.
- 새 패턴을 발견하면 `common/guard.py` 의 `PATTERNS` 에 추가한다.

## 저장소
- `common/storage.py` 는 **append-only** 다. 수정·삭제도 새 행을 쌓는다 (`revision` 증가).
- 기존 행을 덮어쓰거나 지우는 코드를 쓰지 않는다. 되돌리기가 여기에 걸려 있다.

## 기록
- AI가 틀린 사례를 발견하면 `docs/ai-mistakes.md` 에 한 줄 추가한다.
- 커밋 메시지에 프롬프트 버전을 바꿨으면 그 사실을 적는다.
