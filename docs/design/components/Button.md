# Button

누르면 일이 일어나는 버튼. 글자는 하는 일 그대로 (`저장하기`, `최애 추가하기`, `97건 더보기`).

- 모양은 알약(`radius-pill`). 높이는 세 가지: 주 버튼 46px(`btn-lg`), 작은 버튼 40px(`btn-sm`), 메뉴바 · 상세의 동그란 버튼 44px(`btn-round`).
- `primary`(accent 바탕): 한 화면에서 가장 중요한 한 가지 (저장하기, 리뷰 등록).
- 기본(흰 바탕 + line 테두리): 그 밖의 선택 (되돌리기, 프로필 수정).
- `more`(gray-soft): 목록 아래 `N건 더보기` — 앞에 `expand_more` 아이콘.
- `tertiary`: 글자만 (취소, 다음에 할게요, 더보기 링크).
- `reserve`(보라 테두리 1.5px + `purple-deep` 글자): 사전예약 타임라인의 `북마크하고 오픈 알림 받기` 에만. 북마크한 뒤에는 `purple` 로 채우고 흰 글자.
- 떠 있는 등록 버튼(FAB)은 `coral` 동그라미 하나, 화면 오른쪽 아래에만.
- 북마크 버튼(카드 위 34px): 안 한 상태는 흰 바탕 75%, 한 상태는 accent 바탕 + 흰 아이콘.
- 메뉴바의 검색 · 알림 · 프로필 · 로그인은 평소 바탕이 투명하고, 커서를 올렸을 때만 흰 바탕이 된다 (알약 탭 참고).
- 버튼에 마우스를 올리면 뜨는 설명(title)은 쓰지 않는다.

손으로 옮김: `app_cafemap.py` 의 `.st-key-add_btn`, `.st-key-list_more`, `[class*=st-key-fav_]`, `.st-key-ade_bar` · 웹 `a-browse.css` 의 `.btn-primary` · `.bm-card`, `a-home.css` 의 `.ah-pre-btn`.
