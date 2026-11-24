// 물어보기 규칙(lib/ask.ts) 점검: 공개 데이터(GitHub data/cafes.json)로 질문 몇 개를 돌려 답이 말이 되는지 확인한다.
// 실행: npm run test:ask   (tsc 로 임시 폴더에 옮긴 뒤 node 로 돌린다. 질문은 어디에도 저장하지 않는다)
import assert from "node:assert/strict";
import { answer, needsLocation } from "../lib/ask";
import { areaName, cityName, todayKST, toItem, type Item, type Popup } from "../lib/popup";

const CAFES = "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/data/cafes.json";
type Row = Record<string, unknown>;
const s = (v: unknown) => (typeof v === "string" ? v.trim() : typeof v === "number" ? String(v) : "");
const n = (v: unknown) =>
  v === null || v === undefined || s(v) === "" ? null : Number.isFinite(Number(v)) ? Number(v) : null;
const list = (v: unknown) =>
  s(v)
    .split(/[,\n]/)
    .map((x) => x.trim())
    .filter(Boolean);

async function load(): Promise<Item[]> {
  const rows = (await (await fetch(CAFES)).json()) as Row[];
  const latest = new Map<string, Row>();
  for (const r of rows) {
    const id = s(r.entry_id);
    const prev = latest.get(id);
    if (!prev || (n(r.revision) ?? 0) > (n(prev.revision) ?? 0)) latest.set(id, r);
  }
  const out: Item[] = [];
  for (const r of latest.values()) {
    if (s(r.status) !== "active") continue;
    const address = s(r.address);
    const p: Popup = {
      id: s(r.entry_id),
      name: s(r.cafe_name),
      work: s(r.work),
      characters: s(r.characters),
      address,
      region: "",
      area: areaName(address),
      city: cityName(address),
      lat: n(r.lat),
      lng: n(r.lng),
      start: s(r.start_date).slice(0, 10),
      end: s(r.end_date).slice(0, 10),
      perks: list(r.perks),
      goods: list(r.goods),
      tags: list(r.tags),
      images: [],
      links: [],
      intro: "",
      updatedAt: s(r.updated_at),
      createdAt: s(r.updated_at),
      rating: null,
    };
    if (p.start && p.end) out.push(toItem(p));
  }
  return out;
}

function show(q: string, items: Item[], today: string, loc?: { lat: number; lng: number }) {
  const res = answer(q, items, today, { loc });
  console.log(
    `\nQ: ${q}\nA: ${res.text}\n   → ${res.hits.length}건: ${res.hits
      .slice(0, 5)
      .map((h) => `${h.work}(${h.area} ${h.start}~${h.end})`)
      .join(" / ")}`,
  );
  return res;
}

(async () => {
  const items = await load();
  const today = process.argv[2] || todayKST();
  console.log(`팝업 ${items.length}곳 · 오늘 ${today}`);

  let r = show("주술회전 팝업 어디서 해?", items, today);
  assert.ok(r.hits.length > 0 && r.hits.every((h) => h.work.includes("주술회전")), "주술회전: 작품이 맞아야");
  assert.match(r.text, /^네, 주술회전 팝업이 \d+건 있어요\./);

  r = show("부산 팝업 알려줘", items, today);
  assert.ok(
    r.hits.length > 0 && r.hits.every((h) => h.city === "부산" || h.address.includes("부산")),
    "부산: 지역이 맞아야",
  );

  r = show("이번 주말 성수 팝업", items, today);
  assert.equal(r.query.windowLabel, "이번 주말");
  assert.ok(
    r.hits.every((h) => h.area === "성동" || h.address.includes("성수")),
    "성수: 성동구여야",
  );

  r = show("곧 끝나는 팝업", items, today);
  assert.equal(r.query.intent, "ending");
  assert.ok(
    r.hits.every((h, i, a) => h.end >= today && (i === 0 || a[i - 1].end <= h.end)),
    "곧 끝나는: 끝나는 날 순",
  );

  r = show("지금 진행 중인 서울 팝업", items, today);
  assert.ok(
    r.hits.length > 0 &&
      r.hits.every((h) => h.start <= today && h.end >= today && (h.city === "서울" || h.address.includes("서울"))),
    "진행 중 서울",
  );

  r = show("12월 5일 부산에서 하는 팝업", items, today);
  const dec5 = r.query.window?.[0] ?? "";
  assert.ok(
    dec5.endsWith("-12-05") && r.hits.every((h) => h.start <= dec5 && h.end >= dec5 && h.city === "부산"),
    "12/5 부산",
  );

  r = show("팝업 추천해줘", items, today);
  assert.equal(r.query.intent, "recommend");
  assert.ok(r.hits.length > 0 && r.hits.every((h) => h.start <= today && h.end >= today), "추천: 진행 중만");
  assert.ok(r.hits.length <= 5, "추천: 상위 5곳만 (더보기 없음, 11/20)");

  r = show("서울 팝업 추천해줘", items, today);
  assert.equal(r.query.intent, "recommend");
  assert.ok(
    r.hits.length > 0 && r.hits.length <= 5 && r.hits.every((h) => h.city === "서울" || h.address.includes("서울")),
    "서울 추천: 서울 팝업 중 상위 5곳",
  );

  assert.ok(needsLocation("내 주변 가까운 팝업", items, today));
  r = show("내 주변 가까운 팝업", items, today);
  assert.match(r.text, /위치를 알 수 없어요/);
  r = show("내 주변 가까운 팝업", items, today, { lat: 37.5563, lng: 126.9236 }); // 홍대입구역 근처
  assert.ok(r.hits.length > 0 && Object.values(r.distances)[0] < 5, "내 주변: 가까운 순");

  r = show("오늘 날씨 어때?", items, today);
  assert.ok(r.guide, "팝업과 상관없는 질문은 묻는 법 안내");

  r = show("치이카와 화성 팝업 이번 주말", items, today);

  // 11/20: 대한민국 시 · 군 이름 — 팝업이 없는 지역은 '아직 ○○에 팝업이 없어요'
  r = show("태백에 팝업 있어?", items, today);
  assert.deepEqual(r.query.places, ["태백"]);
  assert.match(r.text, /^아직 태백에 팝업이 없어요\./);
  r = show("포항시 팝업 추천해줘", items, today);
  assert.match(r.text, /아직 포항에 팝업이 없어요/);

  // 11/24: 특전 — '특전 · 사은품 있는' 은 특전 칸이 채워진 팝업만, '엽서 주는' 은 특전에 엽서가 적힌 팝업만. 지역과 함께도
  r = show("특전 있는 팝업 찾아줘", items, today);
  assert.ok(r.query.perk && r.hits.length > 0 && r.hits.every((h) => h.perks.trim()), "특전 있는: 특전 칸이 채워져야");
  assert.match(r.text, /^네, 특전 있는 팝업이 \d+건 있어요\./);
  r = show("사은품 있는 팝업 찾아줘", items, today);
  assert.ok(r.query.perk && r.hits.length > 0 && r.hits.every((h) => h.perks.trim()), "사은품: 특전으로 읽어야");
  r = show("엽서 주는 팝업 찾아줘", items, today);
  assert.deepEqual(r.query.perkItems, ["엽서"]);
  assert.ok(r.hits.every((h) => /엽서|포스트카드/.test(h.perks)), "엽서 주는: 특전에 엽서가 있어야");
  r = show("서울 특전 있는 팝업 찾아줘", items, today);
  assert.ok(
    r.hits.length > 0 && r.hits.every((h) => h.perks.trim() && (h.city === "서울" || h.address.includes("서울"))),
    "서울 + 특전",
  );
  r = show("포항 사은품 주는 팝업", items, today);
  assert.match(r.text, /아직 포항에 팝업이 없어요/);
  r = show("특전 있는 팝업 추천해줘", items, today);
  assert.equal(r.query.intent, "recommend");
  assert.ok(r.hits.every((h) => h.perks.trim()), "추천 + 특전");
  r = show("팝업 추천해줘", items, today);
  assert.ok(!r.query.perk, "'추천해줘' 의 '줘' 는 특전 조건이 아니다");
  r = show("고양이 팝업", items, today);
  assert.ok(!r.query.places.includes("고양"), "'고양이' 의 '고양' 은 지역이 아니다");
  r = show("음성 팝업", items, today);
  assert.ok(!r.query.places.includes("음성"), "'음성' 은 '음성군' 으로 써야 지역 (흔한 낱말)");
  r = show("충북 음성군 팝업", items, today);
  assert.ok(r.query.places.includes("음성"), "'음성군' 은 지역");
  r = show("추천해줘", items, today);
  assert.match(r.text, /지금 갈 수 있는 \d건의 팝업을/);
  // 11/20: 민감한 개인정보는 넣을 수 없다고 답한다
  r = show("010-1234-5678 부산 팝업 알려줘", items, today);
  assert.match(r.text, /^전화번호는 민감한 개인정보라 넣을 수 없어요/);
  assert.ok(r.hits.length > 0, "가린 뒤에 부산 팝업은 찾는다");
  r = show("내 전화번호 010-1234-5678 저장해줘", items, today);
  assert.equal(r.query.intent, "pii");
  assert.ok(!r.guide && /넣을 수 없어요/.test(r.text));
  console.log("\n모든 점검 통과");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
