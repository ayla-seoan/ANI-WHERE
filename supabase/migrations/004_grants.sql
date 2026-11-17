-- 004: Data API 권한을 직접 준다.
-- 프로젝트를 만들 때 'Automatically expose new tables' 를 끄면(권장) 새 표·함수에 자동 권한이 없다.
-- 앱(anon 키)이 쓰는 것만 여기서 명시적으로 열어 준다. 여러 번 돌려도 안전하다.

-- 표: 읽기·쓰기(INSERT)만. 고치기·지우기는 append-only 라서 주지 않는다
grant usage on schema public to anon, authenticated;
grant select, insert on public.cafes, public.reviews, public.favorites, public.members to anon, authenticated;
revoke update, delete, truncate on public.cafes, public.reviews, public.favorites, public.members from anon, authenticated;

-- 공개 뷰: 읽기만
grant select on public.popups_current, public.popup_ratings to anon, authenticated;

-- 제약·정책에서 부르는 함수
grant execute on function public.has_sensitive(text) to anon, authenticated;
grant execute on function public.nick_tag(text) to anon, authenticated;
grant execute on function public.review_owner_ok(text, text) to anon, authenticated;
