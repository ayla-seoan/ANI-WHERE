-- 003: 간편 회원가입 (카카오·네이버). 이메일·전화번호·실명·카카오/네이버 고유 번호는 저장하지 않는다.
-- entry_id = 소금 친 해시(member_key). 회원 기록도 append-only: 닉네임 변경·탈퇴는 새 행.
create table if not exists public.members (
  row_id      text primary key,
  entry_id    text not null,                 -- member_key (sha256 앞 16자)
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  provider    text not null default '' check (provider in ('', 'kakao', 'naver')),
  nickname    text not null default '' check (char_length(nickname) <= 16 and position('#' in nickname) = 0),
  agreed_at   text not null default '',
  unique (entry_id, revision),
  constraint members_no_sensitive check (not public.has_sensitive(nickname))
);
create index if not exists members_entry_idx on public.members (entry_id);

alter table public.members enable row level security;
drop policy if exists members_select on public.members;
drop policy if exists members_insert on public.members;
create policy members_select on public.members for select to anon, authenticated using (true);
-- 같은 회원의 다음 기록은 처음 가입한 로그인 수단과 같아야 한다 (다른 수단으로 남의 기록을 잇지 못하게)
create policy members_insert on public.members for insert to anon, authenticated with check (
  not exists (select 1 from public.members m where m.entry_id = members.entry_id
              and m.revision = 1 and m.provider <> members.provider)
);
revoke update, delete, truncate on public.members from anon, authenticated;
