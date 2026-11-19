-- 013: 블로그 후기 저장 (11/19 요청: "불러온 거 저장해 놓고 보이게, 추가된 것만 새로 불러오면 되잖아"). 여러 번 돌려도 안전하다.
--
-- 예전: 상세를 열 때마다(서버마다 하루 한 번) 네이버 블로그 검색을 다시 불러 하루 한도(429)를 다 썼다.
-- 이제: 찾은 글을 blog_posts 에 쌓아 두고 화면은 여기서 바로 읽는다. 네이버는 팝업마다 하루 한 번만 물어서
--       아직 없는 글(링크 기준)만 더한다. 물어본 날은 blog_checks 에 한 줄 남긴다 (두 사이트 · 서버 재시작 모두 같은 표를 본다).
-- append-only (앱 storage · web store 와 같은 칸). 지우기 · 고치기 없음 — 주간 정리(012)만 내린 팝업의 글을 함께 지운다 (아래).

create table if not exists public.blog_posts (
  row_id      text primary key,
  entry_id    text not null,                 -- '<팝업 id>:<링크 sha1 앞 12자>' (같은 글은 같은 번호)
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  cafe_id     text not null default '',
  link        text not null default '' check (link ~ '^https?://' and length(link) <= 500),
  title       text not null default '' check (length(title) <= 200),
  descr       text not null default '' check (length(descr) <= 300),
  blogger     text not null default '' check (length(blogger) <= 60),
  day         text not null default '' check (day = '' or day ~ '^\d{4}-\d{2}-\d{2}$'),
  thumb       text not null default '' check (thumb = '' or (thumb ~ '^https://' and length(thumb) <= 600)),
  unique (entry_id, revision)
);
create index if not exists blog_posts_cafe_idx on public.blog_posts (cafe_id);

create table if not exists public.blog_checks (
  row_id      text primary key,
  entry_id    text not null,                 -- '<팝업 id>:<YYYY-MM-DD>'
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  cafe_id     text not null default '',
  day         text not null default '' check (day ~ '^\d{4}-\d{2}-\d{2}$'),
  found       text not null default '',      -- 그날 새로 더한 글 수
  unique (entry_id, revision)
);
create index if not exists blog_checks_cafe_idx on public.blog_checks (cafe_id, day);

alter table public.blog_posts  enable row level security;
alter table public.blog_checks enable row level security;
drop policy if exists blog_posts_select on public.blog_posts;
drop policy if exists blog_posts_insert on public.blog_posts;
drop policy if exists blog_checks_select on public.blog_checks;
drop policy if exists blog_checks_insert on public.blog_checks;
create policy blog_posts_select  on public.blog_posts  for select to anon, authenticated using (true);
create policy blog_posts_insert  on public.blog_posts  for insert to anon, authenticated with check (true);
create policy blog_checks_select on public.blog_checks for select to anon, authenticated using (true);
create policy blog_checks_insert on public.blog_checks for insert to anon, authenticated with check (true);
grant select, insert on public.blog_posts, public.blog_checks to anon, authenticated;
revoke update, delete, truncate on public.blog_posts, public.blog_checks from anon, authenticated;

-- 주간 정리(012)가 내린 팝업의 블로그 글 · 확인 기록도 함께 지우게 다시 만든다 (나머지는 012 와 같다)
create or replace function public.purge_ended_popups()
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  monday date := date_trunc('week', now() at time zone 'Asia/Seoul')::date;
  ids  text[];
  rids text[];
  n_rows int; n_rev int; n_fav int; n_req int; n_blog int;
begin
  select coalesce(array_agg(c.entry_id), '{}') into ids
    from public.cafes c
   where c.revision = (select max(x.revision) from public.cafes x where x.entry_id = c.entry_id)
     and (coalesce((case when c.end_date ~ '^\d{4}-\d{2}-\d{2}$' or c.end_date ~ '^\d{4}-\d{2}-\d{2}[T ]' then left(c.end_date, 10)::date end) < monday, false)
          or (c.status = 'deleted' and (c.updated_at at time zone 'Asia/Seoul')::date < monday));

  insert into public.purged_popups (entry_id, notion_ids)
  select c.entry_id, string_agg(distinct m[1], ' ')
    from public.cafes c, regexp_matches(c.note, '(notion:[0-9A-Za-z_-]+)', 'g') as m
   where c.entry_id = any(ids)
     and c.entry_id in (select l.entry_id from public.cafes l
                         where l.entry_id = any(ids)
                           and l.revision = (select max(x.revision) from public.cafes x where x.entry_id = l.entry_id)
                           and not coalesce((case when l.end_date ~ '^\d{4}-\d{2}-\d{2}$' or l.end_date ~ '^\d{4}-\d{2}-\d{2}[T ]' then left(l.end_date, 10)::date end) < monday, false))
   group by c.entry_id
  on conflict (entry_id) do nothing;

  select coalesce(array_agg(distinct r.entry_id), '{}') into rids
    from public.reviews r where r.cafe_id = any(ids);

  delete from public.del_requests
   where (target_type = 'cafe' and target_id = any(ids)) or (target_type = 'review' and target_id = any(rids));
  get diagnostics n_req = row_count;
  delete from public.reviews where cafe_id = any(ids) or parent_id = any(rids);
  get diagnostics n_rev = row_count;
  delete from public.favorites where cafe_id = any(ids);
  get diagnostics n_fav = row_count;
  delete from public.blog_posts where cafe_id = any(ids);
  get diagnostics n_blog = row_count;
  delete from public.blog_checks where cafe_id = any(ids);
  delete from public.cafes where entry_id = any(ids);
  get diagnostics n_rows = row_count;

  return jsonb_build_object('monday', monday, 'popups', cardinality(ids), 'popup_rows', n_rows,
                            'review_rows', n_rev, 'favorite_rows', n_fav, 'del_request_rows', n_req,
                            'blog_rows', n_blog);
end $$;

revoke all on function public.purge_ended_popups() from public, anon, authenticated;
