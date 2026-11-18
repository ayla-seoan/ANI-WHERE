# Badge

팝업의 지금 상태나 지역을 짧게 알려 주는 알약 모양 표시.

- 상태 배지는 포스터 왼쪽 위, 지역 배지는 오른쪽 위. 한 카드에 상태 하나, 지역 하나.
- 뜻은 어디서나 같게: `진행 중`(accent-deep on accent-soft) · `D-n`(blue on blue-soft) · `마감임박`(red on red-soft, 3일 안에 끝남) · `사전예약 D-n`(흰 글자 on purple) · `종료 D-n`(흰 글자 on orange).
- 지역 배지 바탕은 `city-*` 토큰 (포스터 위에서는 진하게 채우고 흰 테두리).
- 쓰는 쪽이 정하는 것: 글자, 종류(live · soon · closing · reserve · ends · area).

손으로 옮김: `app_cafemap.py` 의 `.cstate`, `.hcbadge`, `_area_badge`.
