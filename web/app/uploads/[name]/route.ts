import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse, type NextRequest } from "next/server";
import { localDir, mode } from "@/lib/server/store";

// 시험용 local 모드에서 올린 사진 보여 주기 (WEB_STORAGE=local 일 때만). 배포에서는 404 — 사진은 Supabase Storage 주소로 바로 열린다.
const TYPES: Record<string, string> = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif" };

export async function GET(_: NextRequest, { params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  const m = /^[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$/.exec(name);
  if (mode() !== "local" || !m) return new NextResponse("Not found", { status: 404 });
  try {
    const data = await fs.readFile(path.join(localDir(), "uploads", name));
    return new NextResponse(new Uint8Array(data), { headers: { "Content-Type": TYPES[m[1]], "Cache-Control": "no-store" } });
  } catch {
    return new NextResponse("Not found", { status: 404 });
  }
}
