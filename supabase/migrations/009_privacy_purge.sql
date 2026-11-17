-- 009: 탈퇴 회원 개인정보 파기 (11/18, 개인정보 보호법 '파기' 의무). 여러 번 돌려도 안전하다.
--
-- 저장소는 append-only 라 탈퇴해도 예전 기록 행에 닉네임·사진이 남는다. 법적 파기 의무 때문에 이 함수만
-- 예외로 예전 행을 고친다 (닉네임·사진 → 빈 값, 리뷰 작성자 → '탈퇴한 회원', 접속 기록 삭제).
--
-- purge_withdrawn(회원 번호): 앱이 탈퇴 직후 부른다. 그 회원의 마지막 기록이 '탈퇴(deleted)' 일 때만 지운다
--   (탈퇴하지 않은 회원의 정보는 이 함수로 지울 수 없다).
-- purge_expired(): 관리자용 · 매일 자동. 탈퇴 회원 전체 정리 + 1년 지난 접속 기록 삭제. anon 은 부를 수 없다.

create or replace function public.purge_withdrawn(p_member_key text)
returns boolean language plpgsql security definer set search_path = public as $$
declare
  last_status text;
  tag text := '#m' || left(p_member_key, 4);
begin
  select status into last_status from public.members
   where entry_id = p_member_key order by revision desc limit 1;
  if last_status is distinct from 'deleted' then
    return false;                                   -- 탈퇴한 회원만
  end if;
  update public.members set nickname = '', avatar = '' where entry_id = p_member_key;
  update public.reviews set nickname = '탈퇴한 회원' || tag where right(nickname, length(tag)) = tag;
  update public.del_requests set requester_nick = '' where requester = p_member_key;
  delete from public.visits where member = p_member_key;
  delete from public.notices where target = p_member_key;
  delete from public.member_credentials where member_key = p_member_key;
  return true;
end $$;

create or replace function public.purge_expired()
returns integer language plpgsql security definer set search_path = public as $$
declare
  k text;
  n integer := 0;
begin
  for k in
    select m.entry_id from public.members m
     where m.revision = (select max(revision) from public.members x where x.entry_id = m.entry_id)
       and m.status = 'deleted'
  loop
    perform public.purge_withdrawn(k);
    n := n + 1;
  end loop;
  delete from public.visits where day <> '' and day::date < (now() at time zone 'Asia/Seoul')::date - 365;
  return n;
end $$;

revoke all on function public.purge_withdrawn(text) from public;
grant execute on function public.purge_withdrawn(text) to anon, authenticated;
revoke all on function public.purge_expired() from public, anon, authenticated;

-- 매일 새벽 4시(한국 시간 = UTC 19시) 자동 정리. pg_cron 을 켤 수 없는 환경이면 건너뛴다
-- (그때는 SQL Editor 에서 select public.purge_expired(); 를 직접 돌린다)
do $$
begin
  create extension if not exists pg_cron;
  perform cron.unschedule('aniwhere-purge') where exists (select 1 from cron.job where jobname = 'aniwhere-purge');
  perform cron.schedule('aniwhere-purge', '0 19 * * *', 'select public.purge_expired();');
exception when others then
  raise notice 'pg_cron 을 쓸 수 없어 자동 정리는 건너뜀: %', sqlerrm;
end $$;
