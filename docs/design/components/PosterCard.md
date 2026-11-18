# PosterCard

팝업 하나를 포스터로 보여 주는 리스트 카드. 누르면 상세가 열린다.

- 포스터가 카드를 꽉 채우고(3:4), 아래 그림자 위에 작품 이름(`card-title`, Jua) · 장소 · 기간.
- 왼쪽 위 상태 Badge, 오른쪽 위 지역 Badge, 오른쪽 아래 북마크 버튼.
- 테두리는 `mint-line` 2.5px, 모서리 `radius-md`. 마우스를 올리면 살짝 작아지며 특전·주소가 펼쳐진다.
- 포스터가 없으면 기본 포스터(`Images/default_poster.png`).
- 쓰는 쪽이 정하는 것: 포스터, 작품 이름, 장소, 기간, 상태, 지역, 북마크 여부.

손으로 옮김: `app_cafemap.py` 의 `_poster_card`, `.pcard`.
