-- 012: 내린 팝업을 매주 월요일에 DB 에서 지우기 (11/19 요청). 여러 번 돌려도 안전하다.
--
-- 규칙 (사용자 결정 11/19)
--  - 월~일을 한 주로 보고, 다음 주 월요일(한국 시간)이 되면 그 전에 내려간 팝업을 지운다:
--      · 기간 종료: 종료일(end_date)이 이번 주 월요일보다 앞인 팝업
--      · 삭제 요청 승인 등으로 내린 팝업: 마지막 기록이 'deleted' 이고 그 기록이 이번 주 월요일보다 앞인 팝업
--  - 팝업의 모든 기록(수정 이력 포함) + 그 팝업의 리뷰(답글 포함) · 북마크 · 삭제 요청 기록을 지운다.
--  - 되돌릴 수 없다. /stats 의 예전 완결률 · 간트 · 내 캘린더 지난 달 · 다녀온 팝업에서도 사라진다 (사용자 확인함).
--  - append-only 저장소의 두 번째 예외다 (첫 번째는 009 탈퇴 회원 파기). CLAUDE.md '저장소' 참고.
--
-- 사진 파일: SQL 로 storage.objects 를 지우면 파일은 버킷에 그대로 남는다 (Supabase 문서 'Delete objects').
--   그래서 파일은 Storage API 로 지운다 — 아래 정책으로 anon 은 '어느 기록도 쓰지 않는 · 하루 지난' 파일만
--   보고 지울 수 있고, 매일 가져오기 작업(scripts/storage_sweep.py)이 그런 파일을 지운다.
--   쓰고 있는 사진(팝업 · 리뷰 · 프로필, 지난 수정 기록 포함)은 anon 이 볼 수도 지울 수도 없다.

-- 기간이 남았는데 내린 팝업(삭제 요청 승인 등)의 Notion 번호만 남긴다 — 지운 뒤에도 Notion 가져오기가
-- 같은 팝업을 다시 넣지 않게 (notion_sync.import_rows 가 읽음). 개인정보 없음. 기간이 끝나 지운 팝업은 남기지 않는다
-- (Notion 에서 기간이 늘어나면 다시 들어오는 게 맞아서).
create table if not exists public.purged_popups (
  entry_id    text primary key,
  notion_ids  text not null default '',      -- 'notion:<번호> notion:<번호>-2' (note 의 표시 그대로)
  purged_at   timestamptz not null default now()
);
alter table public.purged_popups enable row level security;
drop policy if exists purged_popups_read on public.purged_popups;
create policy purged_popups_read on public.purged_popups for select to anon, authenticated using (true);
grant select on public.purged_popups to anon, authenticated;

create or replace function public.purge_ended_popups()
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  monday date := date_trunc('week', now() at time zone 'Asia/Seoul')::date;   -- 이번 주 월요일 (한국 시간)
  ids  text[];
  rids text[];
  n_rows int; n_rev int; n_fav int; n_req int;
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
  delete from public.cafes where entry_id = any(ids);
  get diagnostics n_rows = row_count;

  return jsonb_build_object('monday', monday, 'popups', cardinality(ids), 'popup_rows', n_rows,
                            'review_rows', n_rev, 'favorite_rows', n_fav, 'del_request_rows', n_req);
end $$;

revoke all on function public.purge_ended_popups() from public, anon, authenticated;

-- 사진 파일이 아직 어느 기록에서 쓰이는지 (팝업 포스터 · 리뷰 사진 · 프로필 사진, 지난 수정 기록까지).
-- 정책 안에서 anon 으로 읽을 수 없는 표(members)도 봐야 해서 security definer. 돌려주는 것은 참/거짓 하나뿐이다.
create or replace function public.upload_in_use(p_name text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.cafes   where position(p_name in images) > 0)
      or exists (select 1 from public.reviews where position(p_name in images) > 0)
      or exists (select 1 from public.members where position(p_name in avatar) > 0)
$$;

revoke all on function public.upload_in_use(text) from public;
grant execute on function public.upload_in_use(text) to anon, authenticated;

-- Storage API 로 지우려면 select · delete 정책이 둘 다 필요하다. 둘 다 '안 쓰는 · 하루 지난 파일'만.
-- (하루: 사진을 올린 직후 기록을 쌓기 전 잠깐 동안 지워지지 않게)
drop policy if exists aniwhere_uploads_orphan_select on storage.objects;
create policy aniwhere_uploads_orphan_select on storage.objects
  for select to anon, authenticated
  using (bucket_id = 'uploads' and created_at < now() - interval '1 day' and not public.upload_in_use(name));

drop policy if exists aniwhere_uploads_orphan_delete on storage.objects;
create policy aniwhere_uploads_orphan_delete on storage.objects
  for delete to anon, authenticated
  using (bucket_id = 'uploads' and created_at < now() - interval '1 day' and not public.upload_in_use(name));

-- 매주 월요일 00:10 (한국 시간 = 일요일 15:10 UTC). pg_cron 을 켤 수 없는 환경이면 건너뛴다
-- (그때는 SQL Editor 에서 select public.purge_ended_popups(); 를 월요일마다 직접 돌린다)
do $$
begin
  create extension if not exists pg_cron;
  perform cron.unschedule('aniwhere-purge-popups') where exists (select 1 from cron.job where jobname = 'aniwhere-purge-popups');
  perform cron.schedule('aniwhere-purge-popups', '10 15 * * 0', 'select public.purge_ended_popups();');
exception when others then
  raise notice 'pg_cron 을 쓸 수 없어 월요일 자동 정리는 건너뜀: %', sqlerrm;
end $$;
