# ReviewCard

홈 '꿀팁 가득! 실시간 후기 모음' 의 후기 카드. 3칸 열(좁으면 2칸)에 왼쪽부터 놓이고, 글 길이만큼 높이가 달라진다.

- 테두리 `line` 1.5px · 모서리 `radius-card`(16px) · 안쪽 여백 14px.
- 위에서부터: 종류 칩 → 프로필 사진(26px) · 닉네임 · 랭크 칩(RankStamp 20px + `Lv.n`) · 시간 → 별(다녀온 후기만, `star-ink`) → 본문(14px, 8줄까지) → 어떤 팝업인지 한 줄(작은 포스터 · 작품 이름 · 상태 Badge).
- 종류 칩 색: `다녀온 후기` = `accent-ink` on `accent-soft` · `기대평` = `blue` on `blue-soft` · `기타` = `star-ink` on `rank-5-fill`.
- 사진이 있는 후기는 카드 맨 위에 사진을 꽉 채워 싣는다.
- 칸 제목 오른쪽의 칩(`전체 · 다녀온 후기 · 기대평 · 기타`)으로 종류를 골라 본다.
- 예시의 닉네임 · 글은 시험용이다. 화면 그림 · 문서에 실제 회원의 글을 옮기지 않는다.

손으로 옮김: `app_cafemap.py` 의 `_home_reviews`(`ah_wall`) · 웹 `a-home.css` 의 `.ah-wall`, `.ah-rv*`.
