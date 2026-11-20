// 예전에 앱에서 올린 사진(저장소 static/uploads 의 파일 이름)을 화면에 보여 줄 주소.
// 11/20 요청: 불특정 다수에게 공유하니 브라우저에 깃허브 주소(계정 · 저장소 이름)가 보이지 않게 —
// 우리 주소 /img/<파일 이름> 으로 보여 주고, 서버(app/img/[name]/route.ts)가 대신 받아 온다.
// 서버만 아는 원본 위치는 lib/server/github.ts 한곳에만 둔다.
export const IMG_PATH = "/img/";

/** 파일 이름 → 화면 주소. 이름 모양이 이상하면 '' */
export function imgUrl(name: string): string {
  return /^[\w.-]+\.(png|jpe?g|webp|gif|avif)$/i.test(name) ? IMG_PATH + encodeURIComponent(name) : "";
}
