# ANI:WHERE

애니 팝업 · 콜라보 카페 · 굿즈 행사를 **찾고, 북마크하고, 놓치지 않게** 돕는 지도 서비스의 디자인 시스템.
흰 바탕 위에 포인트만 우유빛 민트, 둥근 글꼴, 포스터가 주인공인 카드. 저장소 `ayla-seoan/ANI-WHERE` 의 실제 화면 코드(`app_cafemap.py`)에서 값을 그대로 옮겼다.

## 말투 (콘텐츠 기본)

- **친절한 존댓말, 짧게.** "~해요 / ~예요". 초등학생도 알아듣는 말로. 예: "북마크한 팝업은 오픈·종료 3일 전부터 알려 드려요."
- **사용자 쪽 말로 이름 짓기.** 기능 이름이 아니라 하는 일: `최애 추가하기`, `N건 더보기`, `팝업 N곳 표시`.
- **안 될 때는 이유와 다음 할 일.** "이 조건엔 행사가 없어요" + `검색어 지우기 (12곳)` 버튼. 빈 표를 보여 주지 않는다.
- **이모지 대신 아이콘.** 버튼·안내에는 Material Symbols Rounded (`:material/…:`, HTML 안에서는 `<span class="mi">이름</span>`).
- **숫자는 규칙으로 센 것만.** 물어보기 답의 건수·날짜는 `accent-deep` 굵게. AI 가 만든 글이면 'AI 산출', 규칙이면 '규칙 기반 대체' 를 기록에 남긴다.
- 버튼·링크에 마우스를 올리면 뜨는 설명(`title`)은 쓰지 않는다. 설명은 제목·입력칸 옆 `?` 로만.

## 색

| 역할 | 토큰 | 쓰는 곳 |
| --- | --- | --- |
| 바탕 | `surface`, `surface-soft`, `gray-soft` | 페이지는 흰색. 칸·상자는 `surface-soft` |
| 글자 | `ink`, `muted`, `subtle` | 본문 `ink`, 장소·기간 `muted`, 바닥글 `subtle` |
| 포인트 | `accent`, `accent-deep`, `accent-soft` | 주 버튼·아이콘 `accent`, 포인트 글자 `accent-deep`, 고른 줄·오늘 칸 `accent-soft` |
| 브랜드 민트 | `mint`, `mint-deep`, `mint-soft`, `mint-line` | 포스터 카드 테두리 `mint-line`, 카드 작품 이름 `mint-deep` |
| 메뉴바 | `gnb` | 맨 위 메뉴바 바탕 하나에만 |
| 강조 하나 | `coral` | 등록하기 + 떠 있는 버튼, 새 알림 점. 한 화면에 한 곳 |
| 상태 | `blue`/`blue-soft` 오픈 예정 · `red`/`red-soft` 마감임박 · `purple` 사전예약 · `orange` 종료 D-n | 상태에만 쓴다. 장식으로 쓰지 않는다 |
| 지역 | `city-*` | 지역 배지. 시마다 다른 색, 포스터 위에서는 진하게 채우고 흰 테두리 |

명암: `ink` 는 흰 바탕 위 13:1. `accent` · `mint` · `orange` 위의 흰 글자와 `muted` · `subtle` 글자는 4.5:1 이 안 된다(원본 값 그대로 둠) — 굵은 짧은 배지 글자나 큰 글자에만 쓰고, 읽어야 하는 문장은 `ink` 로.

## 글꼴

- **제목 `display` (Jua)**: 화면 제목, 칸 제목, 포스터 카드 작품 이름. 둥글고 귀여운 애니 느낌을 맡는다.
- **본문 `body` (NanumSquareRound → Pretendard)**: 나머지 전부. 메뉴바 탭, 버튼, 배지까지.
- **아이콘 `icon` (Material Symbols Rounded)**: 글자와 같은 색·크기를 따른다.
- 홈 칸 제목은 `home-heading`(본문 글꼴 800) + 앞에 `accent` 아이콘.

## 모양 · 간격

- 둥글게: 카드 `radius-md`, 배너·큰 칸 `radius-lg`, 배지·칩·탭 알약·스토리 동그라미 `radius-pill`.
- 포스터가 주인공: 카드는 포스터를 꽉 채우고(3:4 또는 4:3), 글자는 아래에 한두 줄. 배지는 포스터 위 모서리에 — 왼쪽 위 상태, 오른쪽 위 지역.
- 그림자는 떠 있는 것에만: `shadow-float`(등록 + · 물어보기 버튼), `shadow-card`(후기 카드). 평평한 카드에는 테두리(`mint-line` 또는 `line`).
- 간격은 `space-*` 단계로. 홈 칸 사이 `space-5`, 카드 사이 `space-3`.

## 배지 뜻 (어디서나 같게)

| 글자 | 색 | 뜻 |
| --- | --- | --- |
| `진행 중` | `accent-deep` on `accent-soft` | 지금 열려 있음 |
| `D-n` | `blue` on `blue-soft` | n일 뒤에 열림 |
| `마감임박` | `red` on `red-soft` | 3일 안에 끝남 |
| `사전예약 D-n` | 흰 글자 on `purple` | 예약해야 들어감, n일 뒤 열림 |
| `종료 D-n` · `오늘 종료` | 흰 글자 on `orange` | 이번 주에 끝남 (홈) |

## 아이콘 (Iconography)

Material Symbols Rounded 만 쓴다. 자주 쓰는 것: `bookmark_add` / `bookmark_added`(북마크), `map`, `format_list_bulleted`, `calendar_month`, `search`, `notifications`, `location_on`, `local_fire_department`(랭킹), `fiber_new`(신규), `hourglass_bottom`(이번 주), `event_available`(사전예약), `rate_review`(후기), `auto_awesome`(비슷한 팝업), `add`(등록·최애 추가). 아이콘은 혼자 뜻을 나르지 않는다 — 늘 글자와 함께.

## 로고 · 그림

`Logos` 묶음: 기본 로고(`logo.png`), 민트 로고(`logo_mint.png`), 보조 로고(`logo2.png`). 메뉴바 왼쪽에 두고, 누르면 홈. `Images` 묶음: 물어보기 도우미 얼굴(`ask_avatar.png`), 포스터가 없을 때 대신 보이는 기본 포스터(`default_poster.png`). 로고는 다시 그리지 않고 파일 그대로 쓴다.

## 계절 배경

내 캘린더 화면에서만 3~5월 꽃잎 · 6~8월 잎사귀 · 9~11월 단풍 · 12~2월 눈이 천천히 떨어진다(작은 SVG, 클릭을 막지 않음, '동작 줄이기' 설정이면 끔).

## 옮기지 않은 것 (Not synced)

- 글꼴 파일: Jua 는 Google Fonts, NanumSquareRound · Pretendard 는 jsDelivr 의 CSS 로 불러온다. 파일은 저장소에 없어 `type.fonts` 는 비어 있고 이름만 `type.families` 에 있다.
- 컴포넌트: 앱은 Streamlit(파이썬)이라 React 라이브러리가 없다. 아래 5개 카드(배지 · 버튼 · 포스터 카드 · 북마크 팝업 동그라미 · 칩)는 `app_cafemap.py` 의 CSS 를 보고 **손으로 옮긴 정적 모습**이다.
- 다크 모드: 앱에 없어 테마는 Light 하나.
