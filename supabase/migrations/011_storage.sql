-- 011: 사진 저장소 (Supabase Storage 공개 버킷 'uploads'). 공개 웹(Vercel)에서 올리는 프로필 · 리뷰 · 포스터 사진.
-- 여러 번 돌려도 안전하다.
--
-- 설계 (append-only 와 같은 생각)
--  - 버킷은 공개 읽기(public = true): 저장한 https 주소를 members.avatar · reviews.images · cafes.images 에 그대로 넣고,
--    Streamlit 앱 · 공개 웹 모두 그 주소로 보여 준다.
--  - 올리기는 웹 서버(Next.js 서버 코드)가 anon 키로만 한다. 정책은 '새 파일 넣기' 하나뿐:
--      이 버킷 · 이름 = 무작위 12자 + 그림 확장자 · 파일 종류(mime)·크기는 버킷 설정으로 막는다.
--  - 고치기(update) · 지우기(delete) 정책은 만들지 않는다 → anon 으로는 기존 사진을 바꾸거나 지울 수 없다.
--  - 위치(EXIF) 지우기 · 프로필 256px 줄이기는 서버가 올리기 전에 한다 (web/lib/server/upload.ts).

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('uploads', 'uploads', true, 20971520, array['image/png', 'image/jpeg', 'image/webp', 'image/gif'])
on conflict (id) do update
  set public = true,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists aniwhere_uploads_insert on storage.objects;
create policy aniwhere_uploads_insert on storage.objects
  for insert to anon, authenticated
  with check (
    bucket_id = 'uploads'
    and name ~ '^[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$'
  );
-- (읽기는 공개 버킷 주소 /storage/v1/object/public/uploads/<이름> 로 되므로 select 정책도 두지 않는다)
