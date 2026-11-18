// 저장소의 문서·그림을 web/ 안으로 옮긴다 (Vercel 배포는 web/ 폴더만 올라가서, web 밖 파일은 빌드 때 읽을 수 없다).
//
//   docs/privacy-policy.md · docs/guide.md · static/guide/guide.css · docs/design/** · static/design/*.css
//     → web/content/docs.gen.ts (문자열로 묶어 빌드에 들어간다. 손으로 고치지 말고 원본을 고친 뒤 이 스크립트를 다시 돌린다)
//   static/guide/*.png → web/public/guide/*.webp (sharp 로 줄인다)
//   static/{logo,logo_mint,logo2,ask_avatar,default_poster}.png → web/public/design/
//   common/prompts/ask.v*.txt · cafe.v*.txt → web/content/prompts/ (서버가 실행 중에 파일로 읽는다 — 코드 안에 넣지 않는다)
//
// 원본이 없으면(= Vercel 처럼 web/ 만 있는 곳) 아무것도 바꾸지 않고 이미 옮겨 둔 것을 그대로 쓴다.
// 사용: cd web && node scripts/sync_docs.mjs   (package.json 의 prebuild 가 부른다)

import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ROOT = path.resolve(WEB, "..");
const DOCS = path.join(ROOT, "docs");
const STATIC = path.join(ROOT, "static");
const PROMPTS = path.join(ROOT, "common", "prompts");
const OUT_TS = path.join(WEB, "content", "docs.gen.ts");

const exists = (p) =>
  fs.access(p).then(
    () => true,
    () => false,
  );
const read = async (p) => (await fs.readFile(p, "utf8")).replace(/\r\n/g, "\n");

async function main() {
  if (!(await exists(path.join(DOCS, "privacy-policy.md")))) {
    console.log("[sync_docs] 원본 문서(../docs)가 없어 건너뛴다 — web/content 에 옮겨 둔 것을 그대로 쓴다.");
    return;
  }
  await fs.mkdir(path.join(WEB, "content", "prompts"), { recursive: true });
  await fs.mkdir(path.join(WEB, "public", "guide"), { recursive: true });
  await fs.mkdir(path.join(WEB, "public", "design"), { recursive: true });

  // ---- 그림: static/guide/*.png → public/guide/*.webp
  let sharp = null;
  try {
    sharp = (await import("sharp")).default;
  } catch {
    sharp = null;
  }
  const guideImgs = (await fs.readdir(path.join(STATIC, "guide"))).filter((f) => f.endsWith(".png"));
  const ext = sharp ? ".webp" : ".png";
  for (const f of guideImgs) {
    const src = path.join(STATIC, "guide", f);
    const dst = path.join(WEB, "public", "guide", f.replace(/\.png$/, ext));
    const [s, d] = await Promise.all([fs.stat(src), fs.stat(dst).catch(() => null)]);
    if (d && d.mtimeMs >= s.mtimeMs) continue; // 이미 최신
    if (sharp) await sharp(src).webp({ quality: 84 }).toFile(dst);
    else await fs.copyFile(src, dst);
  }

  // ---- 로고 · 그림 (디자인 시스템 페이지)
  const logos = ["logo.png", "logo_mint.png", "logo2.png", "ask_avatar.png", "default_poster.png"];
  for (const f of logos) {
    if (await exists(path.join(STATIC, f))) await fs.copyFile(path.join(STATIC, f), path.join(WEB, "public", "design", f));
  }

  // ---- 프롬프트 (물어보기 AI): 파일 그대로
  for (const f of await fs.readdir(PROMPTS)) {
    if (/^(ask|cafe)\.v\d+\.txt$/.test(f)) await fs.copyFile(path.join(PROMPTS, f), path.join(WEB, "content", "prompts", f));
  }

  // ---- 문서: 문자열로 묶기
  const privacy = await read(path.join(DOCS, "privacy-policy.md"));
  // 그림 주소: 앱(Streamlit)의 app/static/guide/x.png → 웹의 /guide/x.webp
  const guide = (await read(path.join(DOCS, "guide.md"))).replace(
    /app\/static\/guide\/([\w-]+)\.png/g,
    (_, n) => `/guide/${n}${ext}`,
  );
  // 꾸밈: Streamlit 칸 이름(.st-key-privacy_wrap)을 웹 칸 이름(.pg-guide)으로
  const guideCss = (await read(path.join(STATIC, "guide", "guide.css"))).replace(/\.st-key-privacy_wrap/g, ".pg-guide");

  const D = path.join(DOCS, "design");
  const comps = {};
  for (const f of (await fs.readdir(path.join(D, "components"))).sort()) {
    comps[f] = await read(path.join(D, "components", f));
  }
  const design = {
    tokens: JSON.parse(await read(path.join(D, "tokens.json"))),
    readme: await read(path.join(D, "README.md")),
    css:
      (await read(path.join(STATIC, "design", "components.css"))) + (await read(path.join(STATIC, "design", "cover.css"))),
    components: comps,
  };

  // 쓰는 아이콘 이름 (Material Symbols Rounded 글꼴을 이 이름들만 받아 가볍게)
  const icons = new Set();
  for (const text of [guide, ...Object.values(comps)])
    for (const m of text.matchAll(/class="mi">([a-z_]+)</g)) icons.add(m[1]);
  ["check_circle", "location_on", "send", "error", "shield"].forEach((n) => icons.add(n));

  const body =
    "// 자동 생성 파일 — 손으로 고치지 말 것. 원본: docs/privacy-policy.md · docs/guide.md · static/guide/guide.css · docs/design/** · static/design/*.css\n" +
    "// 다시 만들기: cd web && node scripts/sync_docs.mjs\n\n" +
    `export const PRIVACY_MD: string = ${JSON.stringify(privacy)};\n\n` +
    `export const GUIDE_HTML: string = ${JSON.stringify(guide)};\n\n` +
    `export const GUIDE_CSS: string = ${JSON.stringify(guideCss)};\n\n` +
    `export const ICON_NAMES: string[] = ${JSON.stringify([...icons].sort())};\n\n` +
    "export type DesignToken = { name: string; value: string | Record<string, string>; usage?: string };\n" +
    "export type DesignStyle = { name: string; fontSize: string; lineHeight: string | number; fontWeight: string | number; sample?: string; usage?: string };\n" +
    "export type DesignTokens = {\n  color: { tokens: DesignToken[] };\n  type: { families: Record<string, string>; groups: { name: string; family: string; styles: DesignStyle[] }[] };\n" +
    "  spacing: { tokens: DesignToken[] };\n  radius: { tokens: DesignToken[] };\n  shadow: { tokens: DesignToken[] };\n};\n\n" +
    `export const DESIGN: { tokens: DesignTokens; readme: string; css: string; components: Record<string, string> } = ${JSON.stringify(design, null, 1)} as never;\n`;
  const prev = await read(OUT_TS).catch(() => "");
  if (prev !== body) await fs.writeFile(OUT_TS, body, "utf8");
  console.log(
    `[sync_docs] 문서 → content/docs.gen.ts, 튜토리얼 그림 ${guideImgs.length}장 → public/guide (${ext}), 로고 → public/design, 프롬프트 → content/prompts`,
  );
}

main().catch((e) => {
  // 문서를 못 옮겨도 빌드는 이미 옮겨 둔 것으로 이어간다
  console.warn("[sync_docs] 실패:", e?.message || e);
});
