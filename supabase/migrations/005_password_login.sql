-- 005: 아이디·비밀번호 회원가입 (간편 로그인과 별개).
-- 받는 것: 아이디 · 비밀번호 · 닉네임 · 약관 동의. 이메일·전화번호·실명은 받지 않는다.
--
-- 보안 설계
--  - 비밀번호는 bcrypt(pgcrypto crypt + gen_salt('bf')) 해시로만 저장한다. 원문은 어디에도 남지 않는다.
--  - member_credentials 표는 RLS 를 켜고 정책을 하나도 두지 않는다 + anon 권한을 모두 뺀다
--    → anon 키로는 읽지도 쓰지도 못한다. 해시가 밖으로 나가지 않는다.
--  - 가입·확인·변경·삭제는 아래 security definer 함수로만. 함수는 맞다/아니다(회원 번호)만 돌려준다.
-- 여러 번 돌려도 안전하다.

create extension if not exists pgcrypto with schema extensions;

-- members.provider 에 'local'(아이디 가입) 허용
alter table public.members drop constraint if exists members_provider_check;
alter table public.members add constraint members_provider_check
  check (provider in ('', 'kakao', 'naver', 'local'));

create table if not exists public.member_credentials (
  login_id    text primary key check (login_id ~ '^[a-z0-9_]{4,20}$'),
  member_key  text not null unique,
  pw_hash     text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
alter table public.member_credentials enable row level security;
revoke all on public.member_credentials from anon, authenticated;

-- 아이디가 이미 있는가 (가입 화면의 중복 확인)
create or replace function public.login_exists(p_login_id text)
returns boolean language sql stable security definer set search_path = public, extensions as $$
  select exists (select 1 from public.member_credentials where login_id = lower(p_login_id));
$$;

-- 가입: 아이디·비밀번호를 저장하고 true. 아이디가 이미 있으면 false
create or replace function public.register_login(p_login_id text, p_password text, p_member_key text)
returns boolean language plpgsql security definer set search_path = public, extensions as $$
begin
  if char_length(coalesce(p_password, '')) < 8 or char_length(p_password) > 72 then
    raise exception '비밀번호는 8~72자';
  end if;
  insert into public.member_credentials (login_id, member_key, pw_hash)
  values (lower(p_login_id), p_member_key, crypt(p_password, gen_salt('bf', 10)));
  return true;
exception when unique_violation then
  return false;
end;
$$;

-- 로그인: 맞으면 회원 번호, 틀리면 null (아이디가 없는지 비밀번호가 틀렸는지 구분하지 않는다)
create or replace function public.check_login(p_login_id text, p_password text)
returns text language sql stable security definer set search_path = public, extensions as $$
  select member_key from public.member_credentials
  where login_id = lower(p_login_id) and pw_hash = crypt(p_password, pw_hash);
$$;

-- 비밀번호 변경: 지금 비밀번호가 맞을 때만
create or replace function public.change_password(p_login_id text, p_old text, p_new text)
returns boolean language plpgsql security definer set search_path = public, extensions as $$
begin
  if char_length(coalesce(p_new, '')) < 8 or char_length(p_new) > 72 then
    raise exception '비밀번호는 8~72자';
  end if;
  update public.member_credentials
     set pw_hash = crypt(p_new, gen_salt('bf', 10)), updated_at = now()
   where login_id = lower(p_login_id) and pw_hash = crypt(p_old, pw_hash);
  return found;
end;
$$;

-- 탈퇴: 비밀번호가 맞을 때만 아이디·해시를 지운다 (개인정보라 남기지 않음. 회원 기록은 members 에 deleted 행으로)
create or replace function public.drop_login(p_login_id text, p_password text)
returns boolean language plpgsql security definer set search_path = public, extensions as $$
begin
  delete from public.member_credentials
   where login_id = lower(p_login_id) and pw_hash = crypt(p_password, pw_hash);
  return found;
end;
$$;

revoke all on function public.login_exists(text), public.register_login(text, text, text),
  public.check_login(text, text), public.change_password(text, text, text), public.drop_login(text, text) from public;
grant execute on function public.login_exists(text), public.register_login(text, text, text),
  public.check_login(text, text), public.change_password(text, text, text), public.drop_login(text, text)
  to anon, authenticated;
