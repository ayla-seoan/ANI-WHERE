-- 008: 회원 프로필 사진 (11/18). 선택 항목. 여러 번 돌려도 안전하다.
-- 값: https 주소(카카오·네이버 프로필 사진) · 직접 올린 사진 파일 이름 · 'none'(기본 그림을 고름) · ''(아직 안 정함)
alter table public.members add column if not exists avatar text not null default '';
alter table public.members drop constraint if exists members_avatar_check;
alter table public.members add constraint members_avatar_check check (
  char_length(avatar) <= 500
  and (avatar = '' or avatar = 'none'
       or avatar ~ '^https://[A-Za-z0-9._~:/?#\[\]@!$&()*+,;=%-]+$'
       or avatar ~ '^[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$')
);
