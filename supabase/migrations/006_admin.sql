-- 006: 관리자 대시보드 · 삭제 요청 · 알림 · 접속 기록 (11/18). 여러 번 돌려도 안전하다.
-- 모두 append-only: anon 은 읽기·쓰기(INSERT)만, 고치기·지우기 권한 없음 (처리·수정·삭제도 새 행).

create table if not exists public.del_requests (
  row_id        text primary key,
  entry_id      text not null,
  revision      integer not null check (revision >= 1),
  status        text not null default 'active' check (status in ('active', 'deleted')),
  updated_at    timestamptz not null default now(),
  target_type   text not null default '' check (target_type in ('', 'review', 'cafe')),
  target_id     text not null default '',
  target_title  text not null default '',
  reason        text not null default '' check (char_length(reason) <= 300),
  requester     text not null default '',      -- 회원 번호 (해시)
  requester_nick text not null default '',
  decision      text not null default 'pending' check (decision in ('pending', 'approved', 'rejected')),
  admin_reason  text not null default '' check (char_length(admin_reason) <= 300),
  decided_at    text not null default '',
  unique (entry_id, revision),
  constraint del_requests_no_sensitive check (not public.has_sensitive(reason) and not public.has_sensitive(admin_reason))
);
create index if not exists del_requests_entry_idx on public.del_requests (entry_id);

create table if not exists public.notices (
  row_id      text primary key,
  entry_id    text not null,
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  target      text not null default 'all',     -- 'all' = 전체 공지, 아니면 회원 번호
  kind        text not null default '',        -- 공지 / 삭제 승인 / 삭제 거부
  title       text not null default '' check (char_length(title) <= 60),
  body        text not null default '' check (char_length(body) <= 500),
  unique (entry_id, revision),
  constraint notices_no_sensitive check (not public.has_sensitive(title) and not public.has_sensitive(body))
);
create index if not exists notices_target_idx on public.notices (target);

create table if not exists public.visits (
  row_id      text primary key,
  entry_id    text not null,                   -- '<회원 번호>:<날짜>'
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  member      text not null default '',
  day         text not null default '',
  unique (entry_id, revision)
);
create index if not exists visits_day_idx on public.visits (day);

alter table public.del_requests enable row level security;
alter table public.notices      enable row level security;
alter table public.visits       enable row level security;

do $$
declare t text;
begin
  foreach t in array array['del_requests', 'notices', 'visits'] loop
    execute format('drop policy if exists %I on public.%I', t || '_select', t);
    execute format('drop policy if exists %I on public.%I', t || '_insert', t);
    execute format('create policy %I on public.%I for select to anon, authenticated using (true)', t || '_select', t);
    execute format('create policy %I on public.%I for insert to anon, authenticated with check (true)', t || '_insert', t);
  end loop;
end $$;

grant select, insert on public.del_requests, public.notices, public.visits to anon, authenticated;
revoke update, delete, truncate on public.del_requests, public.notices, public.visits from anon, authenticated;
