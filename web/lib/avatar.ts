
// 프로필 사진 값(members.avatar) → 화면 주소 (앱 _avatar_url). 비었거나 'none' 이면 기본 그림.
// 예전에 앱에서 올린 사진 파일 이름은 GitHub 저장소의 static/uploads 에서, 새로 올린 사진은 https 주소(Supabase Storage) 그대로.
const UPLOADS = "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/static/uploads/";

export const DEFAULT_AVATAR =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="32" fill="#DDF3EC"/>' +
      '<circle cx="32" cy="25" r="11" fill="#7CCFB8"/><path d="M12 54c3-11 11-16 20-16s17 5 20 16" fill="#7CCFB8"/></svg>',
  );

export function avatarUrl(v: string | null | undefined): string {
  const s = String(v || "").trim();
  if (!s || s === "none") return DEFAULT_AVATAR;
  if (s.startsWith("https://")) return s;
  if (/^\/uploads\/[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$/.test(s)) return s; // 시험용 local 모드
  if (/^[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$/.test(s)) return `${UPLOADS}${s}`;
  return DEFAULT_AVATAR;
}

/** 리뷰 사진 값 → 주소: https 주소는 그대로(Supabase Storage), 예전 파일 이름은 GitHub 저장소의 static/uploads */
export const uploadUrl = (name: string) =>
  /^https:\/\//.test(name) || name.startsWith("/uploads/") ? name : `${UPLOADS}${encodeURIComponent(name)}`;
