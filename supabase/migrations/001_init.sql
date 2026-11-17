-- ANI:WHERE  Supabase 초기 스키마 (001)
-- Supabase 대시보드 > SQL Editor 에 통째로 붙여넣고 Run 한 번.
-- 여러 번 돌려도 같은 결과가 되도록 if not exists / or replace / drop policy if exists 로 썼다.
--
-- 원칙 (CLAUDE.md '저장소'):
--   * append-only. 수정·삭제도 새 행(revision+1)을 쌓는다.
--   * 그래서 anon 키에는 SELECT, INSERT 만 준다. UPDATE·DELETE 정책은 만들지 않는다.
--   * 민감정보(전화번호·이메일·주민번호·카드번호)는 저장하지 않는다 -> DB 에서도 한 번 더 막는다.

-- ------------------------------------------------------------------ 도우미 함수
-- common/guard.py PATTERNS 중 중요한 것을 PostgreSQL 정규식(POSIX)으로 옮긴 것.
-- 앞뒤에 숫자·영문이 붙어 있으면 보지 않는다 (Notion 아이디 같은 긴 16진수 문자열 오탐 방지).
create or replace function public.has_sensitive(t text)
returns boolean
language sql
immutable
as $$
  select coalesce(t, '') ~ '(^|[^0-9A-Za-z])[0-9]{6}[- ]?[1-4][0-9]{6}([^0-9]|$)'            -- 주민등록번호
      or coalesce(t, '') ~ '(^|[^0-9A-Za-z])([0-9]{4}[- ]?){3}[0-9]{4}([^0-9]|$)'           -- 카드번호
      or coalesce(t, '') ~ '(^|[^0-9A-Za-z])01[016-9][-. ]?[0-9]{3,4}[-. ]?[0-9]{4}([^0-9]|$)' -- 휴대전화
      or coalesce(t, '') ~ '(^|[^0-9])0(2|[3-6][1-5]|50[2-8]|70|80)[-. ][0-9]{3,4}[-. ][0-9]{4}([^0-9]|$)' -- 유선·인터넷 전화
      or coalesce(t, '') ~ '[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}'                  -- 이메일
$$;

-- 닉네임 끝 '#네 글자' (IP 해시). '#' 이 없으면 닉네임 전체. common/review.py _tag() 와 같은 규칙.
create or replace function public.nick_tag(nick text)
returns text
language sql
immutable
as $$
  select case when position('#' in coalesce(nick, '')) > 0
              then regexp_replace(nick, '^.*#', '')
              else coalesce(nick, '') end
$$;


-- ------------------------------------------------------------------ cafes
create table if not exists public.cafes (
  row_id      text primary key,
  entry_id    text not null,
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  cafe_name   text not null default '',
  work        text not null default '',
  characters  text not null default '',
  address     text not null default '',
  lat         double precision,              -- 좌표를 못 찾은 행은 null (앱에는 빈칸으로 돌려준다)
  lng         double precision,
  start_date  text not null default '',
  end_date    text not null default '',
  perks       text not null default '',
  goods       text not null default '',
  source      text not null default '',
  note        text not null default '',      -- 끝의 '| notion:<번호>' 는 지우지 않는다
  images      text not null default '',
  tags        text not null default '',
  links       text not null default '',
  editor      text not null default '',
  intro       text not null default '',
  intro_src   text not null default '',
  unique (entry_id, revision),               -- 같은 글에 같은 revision 두 번 = 동시 수정 충돌 -> 거부
  constraint cafes_no_sensitive check (
    not public.has_sensitive(cafe_name) and not public.has_sensitive(note)
    and not public.has_sensitive(intro) and not public.has_sensitive(perks)
    and not public.has_sensitive(goods)
  )
);
create index if not exists cafes_entry_id_idx on public.cafes (entry_id);
create index if not exists cafes_order_idx on public.cafes (updated_at, revision);


-- ------------------------------------------------------------------ reviews
create table if not exists public.reviews (
  row_id      text primary key,
  entry_id    text not null,
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  cafe_id     text not null default '',
  parent_id   text not null default '',      -- 답글이면 원글 entry_id
  kind        text not null default '',
  nickname    text not null default '',      -- '형용사 캐릭터#a3f9'. 끝 4글자가 '내 글' 판단 기준
  body        text not null default '',
  rating      text not null default ''
              check (rating in ('', '1', '2', '3', '4', '5')),
  images      text not null default '',
  unique (entry_id, revision),
  constraint reviews_no_sensitive check (not public.has_sensitive(body))
);
create index if not exists reviews_entry_id_idx on public.reviews (entry_id);
create index if not exists reviews_cafe_id_idx on public.reviews (cafe_id);
create index if not exists reviews_order_idx on public.reviews (updated_at, revision);


-- ------------------------------------------------------------------ favorites
create table if not exists public.favorites (
  row_id      text primary key,
  entry_id    text not null,                 -- '<user 해시>:<cafe_id>'
  revision    integer not null check (revision >= 1),
  status      text not null default 'active' check (status in ('active', 'deleted')),
  updated_at  timestamptz not null default now(),
  cafe_id     text not null default '',
  "user"      text not null default '',      -- IP 를 그대로 두지 않고 해시만 저장
  unique (entry_id, revision)
);
create index if not exists favorites_entry_id_idx on public.favorites (entry_id);
create index if not exists favorites_order_idx on public.favorites (updated_at, revision);


-- ------------------------------------------------------------------ '내 리뷰만 수정·삭제'
-- 이미 있는 리뷰(entry_id)에 새 revision 을 쌓을 때는, 그 글 revision 1 의 닉네임 '#네 글자' 와 같아야 한다.
-- security definer: RLS 를 거치지 않고 원글을 읽는다 (정책 안에서 같은 표를 다시 읽을 때 재귀를 피한다).
create or replace function public.review_owner_ok(p_entry_id text, p_nickname text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    (select public.nick_tag(r.nickname) = public.nick_tag(p_nickname)
       from public.reviews r
      where r.entry_id = p_entry_id
      order by r.revision asc
      limit 1),
    true   -- 처음 쓰는 글(entry_id 가 아직 없음)은 누구나 쓸 수 있다
  )
$$;


-- ------------------------------------------------------------------ RLS
alter table public.cafes     enable row level security;
alter table public.reviews   enable row level security;
alter table public.favorites enable row level security;

-- 정책이 없으면 RLS 는 '전부 거부' 다. UPDATE·DELETE 정책은 일부러 만들지 않는다.
drop policy if exists cafes_select     on public.cafes;
drop policy if exists cafes_insert     on public.cafes;
drop policy if exists reviews_select   on public.reviews;
drop policy if exists reviews_insert   on public.reviews;
drop policy if exists favorites_select on public.favorites;
drop policy if exists favorites_insert on public.favorites;

create policy cafes_select on public.cafes
  for select to anon, authenticated using (true);
create policy cafes_insert on public.cafes
  for insert to anon, authenticated with check (true);

create policy reviews_select on public.reviews
  for select to anon, authenticated using (true);
create policy reviews_insert on public.reviews
  for insert to anon, authenticated
  with check (public.review_owner_ok(entry_id, nickname));

create policy favorites_select on public.favorites
  for select to anon, authenticated using (true);
create policy favorites_insert on public.favorites
  for insert to anon, authenticated with check (true);

-- 이중 잠금: 정책이 없어도 UPDATE/DELETE 는 0행으로 끝나지만, 권한 자체도 빼서 바로 에러가 나게 한다.
revoke update, delete, truncate on public.cafes, public.reviews, public.favorites from anon, authenticated;
grant select, insert on public.cafes, public.reviews, public.favorites to anon, authenticated;
