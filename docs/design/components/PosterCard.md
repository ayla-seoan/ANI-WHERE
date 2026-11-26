# PosterCard

팝업 하나를 포스터로 보여 주는 리스트 카드. 누르면 상세가 열린다.

- 포스터(3:4)는 테두리 `mint-line` 2.5px · 모서리 `radius-md`(12px). 글자는 포스터 **아래**에 두 줄: 작품 이름(`card-title`, Jua 17px, `mint-ink`, 두 줄까지) · 장소와 기간(13px, `ink-soft`, 한 줄).
- 포스터 왼쪽 위 상태 Badge, 오른쪽 위 지역 Badge, 오른쪽 아래 북마크 버튼(34px). 왼쪽 아래에는 특전 · 이벤트 한 줄 칩(있을 때만).
- 마우스를 올리면(세 번째 카드) 테두리가 `accent` 로 바뀌고, 포스터 아래쪽에 어두운 판이 올라와 **캐릭터 · 주소 · 특전**을 보여 준다. 터치 기기에서는 띄우지 않는다.
- 포스터가 없으면 기본 포스터(`default_poster.png`).
- 쓰는 쪽이 정하는 것: 포스터, 작품 이름, 장소, 기간, 상태, 지역, 북마크 여부, 겹침 판에 넣을 글.

손으로 옮김: `app_cafemap.py` 의 `_poster_card`, `.pcard` · 웹 `a-browse.css` 의 `.bc`, `.bc-poster`, `.bc-over`, `.bc-title`.
