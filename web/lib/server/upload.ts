import "server-only";
import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import sharp from "sharp";
import { localDir, mode, StorageWriteError } from "./store";

// 사진 올리기 (common/images.py 와 같은 규칙) — 저장소는 Supabase Storage 의 공개 버킷 'uploads' (011_storage.sql).
//  - 위치(GPS)·기기 정보(EXIF)는 지우고 픽셀만 다시 저장한다 (sharp 는 메타데이터를 넘기지 않는다, 방향은 먼저 적용)
//  - 프로필 사진은 가운데 정사각형 256px webp (images.save_avatar)
//  - 파일 이름은 원래 이름을 쓰지 않고 무작위 12자 (경로 조작 방지)
//  - 저장한 값은 https 전체 주소 → 같은 칸(images · avatar)에 넣으면 Streamlit 앱도 그대로 보여 준다
//  - 서버에서만 anon 키로 올린다 (버킷 정책: 새 파일 넣기만, 고치기·지우기 없음)
//  - 시험용 local 모드는 WEB_DATA_DIR/uploads 에 두고 /uploads/<이름> 으로 보여 준다

export const TYPES = ["png", "jpg", "jpeg", "webp", "gif"];
export const BUCKET = "uploads";
const MIME: Record<string, string> = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif" };

export const LIMIT_MB = { avatar: 5, review: 10, extra: 10, poster: 20 } as const;
export type Kind = keyof typeof LIMIT_MB;

function extOf(name: string, type: string): string {
  const e = (name.split(".").pop() || "").toLowerCase();
  if (TYPES.includes(e)) return e;
  const byType = Object.entries(MIME).find(([, m]) => m === type)?.[0];
  return byType || "";
}

/** 사진 한 장 → 저장한 주소. 형식·크기가 맞지 않거나 그림으로 읽을 수 없으면 StorageWriteError (화면에 그대로 보여 줄 문구) */
export async function saveImage(file: File, kind: Kind): Promise<string> {
  const ext = extOf(file.name || "", file.type || "");
  if (!ext) throw new StorageWriteError(`지원하지 않는 이미지 형식입니다: ${file.name || "사진"}`);
  if (file.size > LIMIT_MB[kind] * 1024 * 1024) throw new StorageWriteError(`${LIMIT_MB[kind]}MB 를 넘는 사진은 올릴 수 없어요.`);
  const raw = Buffer.from(await file.arrayBuffer());
  let data: Buffer;
  let outExt = ext;
  try {
    if (kind === "avatar") {
      data = await sharp(raw, { animated: false }).rotate().resize(256, 256, { fit: "cover", position: "centre" }).webp({ quality: 85 }).toBuffer();
      outExt = "webp";
    } else if (ext === "gif") {
      data = raw; // 움직이는 GIF 는 그대로 (GIF 는 위치 정보를 담지 않는다)
    } else {
      const img = sharp(raw).rotate(); // 방향 정보를 그림에 먼저 적용, 메타데이터는 넘기지 않는다
      data =
        ext === "png"
          ? await img.png().toBuffer()
          : ext === "webp"
            ? await img.webp({ quality: 90 }).toBuffer()
            : await img.jpeg({ quality: 92 }).toBuffer();
    }
  } catch {
    throw new StorageWriteError("사진을 읽지 못했어요. 다른 사진으로 다시 올려 주세요.");
  }
  const name = `${randomUUID().replace(/-/g, "").slice(0, 12)}.${outExt}`;
  const m = mode();
  if (m === "local") {
    const dir = path.join(localDir(), "uploads");
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(path.join(dir, name), data);
    return `/uploads/${name}`;
  }
  if (m !== "supabase") throw new StorageWriteError("사진 저장소가 아직 설정되지 않았어요.");
  const root = (process.env.SUPABASE_URL || "").trim().replace(/\/+$/, "");
  const key = (process.env.SUPABASE_ANON_KEY || "").trim();
  let res: Response;
  try {
    res = await fetch(`${root}/storage/v1/object/${BUCKET}/${name}`, {
      method: "POST",
      // 새 형식 키(sb_publishable_…)는 apikey 에만, 옛 형식(anon JWT, eyJ…)은 Authorization 에도 (store.ts 와 같게)
      headers: {
        apikey: key,
        ...(key.startsWith("eyJ") ? { Authorization: `Bearer ${key}` } : {}),
        "Content-Type": MIME[outExt],
        "x-upsert": "false",
        "cache-control": "31536000",
      },
      body: new Uint8Array(data),
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    throw new StorageWriteError("사진을 올리지 못했어요 (연결 실패). 잠시 뒤 다시 시도해 주세요.");
  }
  if (!res.ok) {
    console.error(`[upload] 거부 ${res.status}: ${(await res.text()).slice(0, 300)}`);
    throw new StorageWriteError("사진을 올리지 못했어요. 잠시 뒤 다시 시도해 주세요.");
  }
  return `${root}/storage/v1/object/public/${BUCKET}/${name}`;
}

/** 폼에서 받은 사진들 (빈 칸은 빼고) */
export function filesFrom(form: FormData, field: string): File[] {
  return form.getAll(field).filter((f): f is File => typeof f === "object" && f !== null && "arrayBuffer" in f && (f as File).size > 0);
}
