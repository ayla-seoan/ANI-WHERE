-- 010: 외부 API 호출 수 (11/18). 블로그 검색(NAVER API HUB)을 한 달 30,000번까지만 부르려고 센다.
-- append-only: 부를 때마다 같은 entry_id('blog:2026-11')의 revision 이 하나씩 늘어난다 (가장 큰 revision = 이번 달 호출 수).
create table if not exists public.api_usage (
  row_id      text primary key,
  entry_id    text not null,
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  api         text not null default '',
  month       text not null default '',
  calls       integer not null default 0,
  unique (entry_id, revision)
);
create index if not exists api_usage_entry_idx on public.api_usage (entry_id);

alter table public.api_usage enable row level security;
drop policy if exists api_usage_select on public.api_usage;
drop policy if exists api_usage_insert on public.api_usage;
create policy api_usage_select on public.api_usage for select to anon, authenticated using (true);
create policy api_usage_insert on public.api_usage for insert to anon, authenticated with check (true);
grant select, insert on public.api_usage to anon, authenticated;
revoke update, delete, truncate on public.api_usage from anon, authenticated;
