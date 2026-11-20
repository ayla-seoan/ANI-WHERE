import "server-only";

// 공개 데이터 · 예전 사진의 원본 위치 (서버에서만 쓴다 — 브라우저로 내려가는 HTML · JSON 에 넣지 않는다, 11/20 요청).
// 저장소를 옮기거나 비공개로 바꾸면 GITHUB_RAW(원본 주소) · GITHUB_TOKEN(비공개 저장소 읽기용, 선택)만 바꾸면 된다.
export const RAW_ROOT = (process.env.GITHUB_RAW || "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main").replace(/\/+$/, "");

export function rawHeaders(): Record<string, string> {
  const t = (process.env.GITHUB_TOKEN || "").trim();
  return t ? { Authorization: `token ${t}` } : {};
}
