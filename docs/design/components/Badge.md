# Badge

팝업의 지금 상태나 지역을 짧게 알려 주는 알약 모양 표시.

- 상태 배지는 포스터 왼쪽 위, 지역 배지는 오른쪽 위. 한 카드에 상태 하나, 지역 하나.
- 뜻과 색은 어디서나 같게 (아래 줄은 '글자 on 바탕').
- `진행 중` — `accent-ink` on `accent-soft`
- `D-n` (n일 뒤 열림) — `blue` on `blue-soft`
- `마감임박` (3일 안에 끝남) · `종료 D-n` (내 캘린더 '곧 있는 팝업') — `red-deep` on `red-soft`
- `종료` — `ink-soft` on `gray-soft`
- `사전예약 D-n` — 흰 글자 on `purple` (사전예약에만)
- 글자 12px · 800, 안쪽 여백 2px 10px, 모서리 `radius-pill`.
- 지역 배지 바탕은 `city-*` 토큰 (포스터 위에서는 진하게 채우고 흰 테두리 1.5px).
- 쓰는 쪽이 정하는 것: 글자, 종류(live · soon · closing · ended · reserve · area).

손으로 옮김: `app_cafemap.py` 의 `.ah-st`, `.cstate`, `_area_badge` · 웹 `a-home.css` 의 `.ah-st`, `a-browse.css` 의 `.bc-state` · `.bc-area`.
