# Button

누르면 일이 일어나는 버튼. 글자는 하는 일 그대로 (`저장하기`, `최애 추가하기`, `92건 더보기`).

- `primary`(accent 바탕): 한 화면에서 가장 중요한 한 가지 (저장하기, 리뷰 등록).
- 기본(흰 바탕 + line 테두리): 그 밖의 선택.
- `more`(gray-soft): 목록 아래 `N건 더보기` — 앞에 `expand_more` 아이콘.
- `tertiary`: 글자만 (취소, 다음에 할게요, 더보기 링크).
- 떠 있는 등록 버튼(FAB)은 `coral` 동그라미 하나, 화면 오른쪽 아래에만.
- 북마크 버튼: 안 한 상태는 흰 바탕 70% 투명, 한 상태는 accent 바탕 + 흰 아이콘.
- 버튼에 마우스를 올리면 뜨는 설명(title)은 쓰지 않는다.

손으로 옮김: `app_cafemap.py` 의 `.st-key-add_btn`, `.st-key-list_more`, `[class*=st-key-fav_]`.
