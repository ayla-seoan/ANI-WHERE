# RankStamp

후기 도장. 다녀온 후기를 남긴 팝업 수만큼 도장이 쌓이고, 쌓인 수로 랭크 5단계가 정해진다. 어디서나 같은 도장을 크기만 바꿔 쓴다.

| 랭크 | 다녀온 후기 | 테두리 | 바탕 | 글자 |
| --- | --- | --- | --- | --- |
| Lv.1 새싹 팬 | 1개 | `rank-1-ring` #5fbf9f | `rank-1-fill` #f0faf6 | `rank-1-ink` #0f6b5c |
| Lv.2 단골 팬 | 3개 | `rank-2-ring` #21b287 | `rank-2-fill` #e9f7f2 | `rank-2-ink` #0f6b5c |
| Lv.3 성지순례러 | 10개 | `rank-3-ring` #2c5bc5 | `rank-3-fill` #eaf0fc | `rank-3-ink` #2c5bc5 |
| Lv.4 덕질 마스터 | 25개 | `rank-4-ring` #7656c4 | `rank-4-fill` #f1ecff | `rank-4-ink` #5b3fae |
| Lv.5 전설의 덕후 | 50개 | `rank-5-ring` #c99a00 | `rank-5-fill` #fff6d6 | `rank-5-ink` #7a5a00 |

- **96px** 마이페이지 대표 도장 — 둘레 글자(`ANI:WHERE ✦ LV.n 이름 ✦`) + 오른쪽 아래 단계 숫자. 랭크 안내 팝업에서는 같은 도장을 116px 로.
- **40px** 내 캘린더 '다녀온 팝업' 카드의 포스터 모서리 (테두리 3px).
- **32px** 리뷰 쓰기 칸의 내 닉네임 옆 (테두리 2.5px).
- **20px** 리뷰 · 후기 카드의 닉네임 옆, `Lv.n` 알약 안 (테두리 2px, 바탕 흰색).
- 40px 이하는 색 테두리 + 마스코트(`mascot.png`, 도장 폭의 62%)만. 글자는 넣지 않는다.
- 아직 못 받은 랭크는 회색(grayscale) + 45% 로 흐리게.
- 세는 규칙: 다녀온 후기만(별점만 남겨도 1개), 같은 팝업은 여러 번 써도 1개, 기대평 · 답글 · 지운 후기는 세지 않는다. 탈퇴하면 도장도 지워진다.
- 랭크가 오르면 **도장 색만** 바뀐다. 그 밖의 혜택은 없다 — 없는 혜택을 화면에 쓰지 않는다.
- 도장이 없는 회원(0개)에게는 도장을 그리지 않는다.

손으로 옮김: `common/stamp.py` 의 `TIERS`(값) · `app_cafemap.py` 의 `_ad_stamp` · `_ahome_stamp` · 웹 `components/RankStamp.tsx`, `a-shell.css` 의 `.rk-*`.
