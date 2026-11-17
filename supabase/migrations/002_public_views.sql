-- 002: 공개 웹(Next.js, web/)과 MCP 서버가 읽는 '지금 상태' 뷰.
-- cafes 는 append-only 라서 같은 팝업의 여러 revision 이 쌓여 있다. 화면은 entry_id 별 최신 행 중 active 만 보면 된다.
-- 여러 번 돌려도 안전하다.

-- security_invoker: 뷰를 읽는 사람의 권한(=cafes 의 RLS)으로 돈다. 뷰가 RLS 를 우회하지 않게.
create or replace view public.popups_current
with (security_invoker = true) as
select row_id, entry_id, revision, updated_at, cafe_name, work, characters, address, lat, lng,
       start_date, end_date, perks, goods, images, tags, links, intro, intro_src
from (
  select distinct on (entry_id) *
  from public.cafes
  order by entry_id, revision desc
) latest
where status = 'active';

comment on view public.popups_current is
  '팝업별 최신 revision 중 active 만. 공개 웹·MCP 가 읽는다. note·editor·source 는 운영용이라 내보내지 않는다.';

-- 읽기만 준다. 뷰에는 INSERT/UPDATE/DELETE 권한이 없다.
revoke all on public.popups_current from anon, authenticated;
grant select on public.popups_current to anon, authenticated;

-- 다녀온 후기 평균 별점 (팝업별). 리뷰 본문·닉네임은 내보내지 않는다.
create or replace view public.popup_ratings
with (security_invoker = true) as
select cafe_id, round(avg(rating::int)::numeric, 1) as avg_rating, count(*) as n
from (
  select distinct on (entry_id) *
  from public.reviews
  order by entry_id, revision desc
) latest
where status = 'active' and parent_id = '' and rating <> ''
group by cafe_id;

revoke all on public.popup_ratings from anon, authenticated;
grant select on public.popup_ratings to anon, authenticated;
