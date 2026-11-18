-- 011: 내 최애 작품 (11/18). 리스트 보기의 '요즘 일정 많은 작품' 스토리 줄 + '최애 추가'.
-- append-only: 고르기/빼기 모두 새 revision 을 쌓는다 (entry_id = '<회원>:<작품 해시>').
create table if not exists public.fav_works (
  row_id      text primary key,
  entry_id    text not null,
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  work        text not null default '',
  "user"      text not null default '',      -- 'm:<회원 번호>'
  unique (entry_id, revision)
);
create index if not exists fav_works_entry_idx on public.fav_works (entry_id);
create index if not exists fav_works_order_idx on public.fav_works (updated_at, revision);

alter table public.fav_works enable row level security;
drop policy if exists fav_works_select on public.fav_works;
drop policy if exists fav_works_insert on public.fav_works;
create policy fav_works_select on public.fav_works for select to anon, authenticated using (true);
create policy fav_works_insert on public.fav_works for insert to anon, authenticated with check (true);
grant select, insert on public.fav_works to anon, authenticated;
revoke update, delete, truncate on public.fav_works from anon, authenticated;
