# Claude Code 에 붙여넣을 요청문

> 이 폴더를 저장소의 `docs/design/handoff/` 에 넣은 뒤, Claude Code 에 아래를 그대로 붙여넣으세요.
> 한 번에 다 하지 말고 단계별로 나눠 요청하는 것을 권장합니다.

---

`docs/design/handoff/README.md` 를 먼저 읽어 줘. Claude Design 에서 확정한 A안 디자인 시안이야.

규칙
- `screens/*.dc.html` 은 디자인 시안이라 그대로 복사하지 말고, 색 · 간격 · 글꼴 · 레이아웃 값을 읽어서 지금 코드(Streamlit `app_cafemap.py` 와 공개 웹 `web/`)에 맞게 옮겨 줘.
- 두 서비스는 같은 화면 · 같은 기능 원칙이야. 한쪽을 바꾸면 다른 쪽도 같이 바꿔.
- 시안 속 팝업 이름 · 날짜 · 후기는 예시 데이터야. 실제 데이터에 연결해.
- 기존 기능(로그인, 북마크, 리뷰 개인정보 차단, append-only 저장, 수정 이력)은 깨지지 않게 하고, 끝나면 `python scripts/qa_report.py` 와 `cd web && npm run test:ask` 를 돌려 결과를 알려 줘.
- '후기 도장 랭크'는 새 기능이라 README 4절의 결정이 끝나기 전에는 화면만 만들고 DB 는 건드리지 마.

이번에 할 일 (1단계)
1. 로고를 `assets/aniwhere_logo.png` 로 교체하고, 물어보기 도우미 얼굴 · 파비콘을 `aniwhere_mascot.png` 로 바꿔 줘.
2. 팝업 상세를 `A-Detail` · `A-DetailEdit` 시안대로 바꿔 줘 (위 2단 + 아래 넓은 탭, 리뷰 사진, 수정하기 전체 칸 + 바뀐 내용 미리보기).

작업 전에 바꿀 파일 목록과 계획을 먼저 보여 주고, 내가 확인하면 시작해.

---

## 다음 단계 예시

- 2단계: `A-Home` · `A-Mobile` 홈 섹션 레이아웃 (사전예약 타임라인, 후기 모음 3단)
- 3단계: `A-List` · `A-Cal` · 모바일 탭 화면
- 4단계: 마이페이지 + 후기 도장 랭크 (랭크 기준 확정 후)
