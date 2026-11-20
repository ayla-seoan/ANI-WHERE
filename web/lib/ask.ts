// 물어보기 (규칙 기반). 앱의 common/ask.py 규칙을 TypeScript 로 옮긴 것 — AI·API 키 없이 브라우저 안에서만 돈다.
// 질문은 어디에도 저장하거나 서버로 보내지 않는다 (내 위치도 이 계산에만 쓰고 버린다).
//
//   1. intentAnswer() — 자주 묻는 질문(가까운 · 추천 · 곧 끝나는 · 곧 열리는 · 사용법 …)을 먼저 본다 (ask.py INTENTS)
//   2. parse()/search() — 질문에서 작품 · 캐릭터 · 지역 · 날짜 조건을 읽고, 모두 맞는 팝업을 점수 순으로 (ask.py parse/search)
//   3. 답 문장은 앱과 같은 말투: '네, {조건} 팝업이 N건 있어요. 아래에 5건까지 보여 드려요.'
//
// 앱과 다른 점: 북마크 수 · 블로그 글 수는 공개 데이터에 없어서, 그 순서가 필요한 질문은 별점 · 곧 끝나는 순으로 대신하고 그렇게 말한다.

import type { Item } from "./popup";

export const MAX_QUESTION = 200;
export const CARD_MAX = 5;

export type LatLng = { lat: number; lng: number };
export type AskCtx = { loc?: LatLng | null };

export type Query = {
  works: string[];
  characters: string[];
  places: string[];
  window: [string, string] | null;
  windowLabel: string;
  words: string[];
  intent: string;
};

export type AskResult = {
  /** 말풍선 글 */
  text: string;
  /** 찾은 팝업 전부 (카드는 앞 5건, 나머지는 '더보기 · 리스트로 보기') */
  hits: Item[];
  /** 내 주변 질문: 팝업 id → km */
  distances: Record<string, number>;
  /** 못 알아들음 → 예시 상자 */
  guide: boolean;
  /** 답 아래 바로가기 [(글자, 주소)] */
  links: [string, string][];
  query: Query;
};

// ------------------------------------------------------------------ 날짜 (YYYY-MM-DD 문자열, 한국 시간)
function d(y: number, m: number, day: number): string {
  return new Date(Date.UTC(y, m - 1, day)).toISOString().slice(0, 10);
}
function plus(ymd: string, n: number): string {
  const t = new Date(`${ymd}T00:00:00Z`);
  t.setUTCDate(t.getUTCDate() + n);
  return t.toISOString().slice(0, 10);
}
function diff(a: string, b: string): number {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86400000);
}
/** 파이썬 weekday(): 월=0 … 일=6 */
function wd(ymd: string): number {
  return (new Date(`${ymd}T00:00:00Z`).getUTCDay() + 6) % 7;
}
function ymdParts(ymd: string) {
  const [y, m, day] = ymd.split("-").map(Number);
  return { y, m, day };
}
function monthEnd(y: number, m: number): string {
  return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
}
const WEEK_KO = "월화수목금토일";

/** ask.py _window: 질문 속 날짜 낱말 → (시작, 끝), 이름 */
export function windowOf(q: string, today: string): [[string, string] | null, string] {
  const w = wd(today);
  const { y, m } = ymdParts(today);
  if (/오늘|지금|현재/.test(q) || /진행\s*중|진행하는|하고\s*있는|열려\s*있는/.test(q))
    return [[today, today], "오늘(진행 중)"];
  if (q.includes("내일")) return [[plus(today, 1), plus(today, 1)], "내일"];
  if (q.includes("모레")) return [[plus(today, 2), plus(today, 2)], "모레"];
  if (/다음\s*주\s*말/.test(q)) {
    const sat = w <= 5 ? plus(today, ((5 - w + 7) % 7) + 7) : plus(today, 6);
    return [[sat, plus(sat, 1)], "다음 주말"];
  }
  if (q.includes("크리스마스")) {
    const yy = m < 12 || ymdParts(today).day <= 25 ? y : y + 1;
    return [[d(yy, 12, 24), d(yy, 12, 25)], "크리스마스"];
  }
  if (q.includes("이번 주말") || q.includes("이번주말") || (q.includes("주말") && !q.includes("다음"))) {
    const sat = w <= 5 ? plus(today, (5 - w + 7) % 7) : today;
    const sun = wd(sat) === 5 ? plus(sat, 1) : sat;
    return [[sat, sun], "이번 주말"];
  }
  if (q.includes("다음 주") || q.includes("다음주")) {
    const mon = plus(today, 7 - w);
    return [[mon, plus(mon, 6)], "다음 주"];
  }
  if (q.includes("이번 주") || q.includes("이번주")) return [[today, plus(today, 6 - w)], "이번 주"];
  if (q.includes("이번 달") || q.includes("이번달")) return [[today, monthEnd(y, m)], "이번 달"];
  if (/다음\s*달/.test(q)) {
    const ny = m === 12 ? y + 1 : y;
    const nm = m === 12 ? 1 : m + 1;
    return [[d(ny, nm, 1), monthEnd(ny, nm)], "다음 달"];
  }
  if (q.includes("연말")) {
    const dec1 = d(y, 12, 1);
    return [[today > dec1 ? today : dec1, d(y, 12, 31)], "연말"];
  }
  const md = q.match(/(\d{1,2})\s*월\s*(\d{1,2})\s*일/) || q.match(/(?:^|[^\d.])(\d{1,2})\s*[/.]\s*(\d{1,2})(?![\d.])/);
  if (md) {
    const mon = Number(md[1]);
    const day = Number(md[2]);
    if (mon >= 1 && mon <= 12 && day >= 1 && day <= 31) {
      const yy = mon >= m - 6 ? y : y + 1;
      const one = d(yy, mon, day);
      if (ymdParts(one).m === mon) return [[one, one], `${mon}월 ${day}일`];
    }
  }
  const mm = q.match(/(\d{1,2})\s*월/);
  if (mm && Number(mm[1]) >= 1 && Number(mm[1]) <= 12) {
    const mon = Number(mm[1]);
    const yy = mon >= m - 6 ? y : y + 1;
    return [[d(yy, mon, 1), monthEnd(yy, mon)], `${mon}월`];
  }
  return [null, ""];
}

// ------------------------------------------------------------------ 조건 읽기
const norm = (s: string) => (s || "").replace(/\s+/g, "").toLowerCase();

const STOP = new Set(
  (
    "팝업 카페 콜라보 있어 있나요 있니 어디 어디서 알려줘 알려 주세요 근처 에서 하는 해요 해 뭐 뭐야 언제 이번 다음 주말 오늘 내일 지금 이번주 " +
    "다음주 이번달 지난 끝난 종료 추천 추천해줘 가볼 만한 곳 있는 열리는 " +
    "열려 열린 열려있는 시작 시작하는 시작해 끝나는 진행 진행중 진행중인 중인 " +
    "보여줘 보여 보여줘요 알려줄래 나와 나오는 갈만한 가고 싶어 아직 여는 있을까 " +
    "모레 다음달 연말 크리스마스 있어요 있나 있음 하나요 하니 할까 하는거 " +
    "있는지 궁금해 궁금 찾아줘 찾아 검색 좀 혹시 정보 언제까지 언제부터 몇 개 건"
  ).split(" "),
);
const PARTICLE = /(?:에서|에는|에|의|은|는|이|가|을|를|도|로|으로)$/;
const DATE_WORD = /^(?:\d{1,2}월|\d{1,2}일|주말에?|이번주에?|이번달에?|다음주에?)$/;
const WORD_CHAR = /[가-힣A-Za-z0-9]/;

/** name 이 질문 속 낱말의 첫머리에 있는가 (뒤에 조사는 붙어도 된다). 오래된 사파리를 위해 정규식 뒤돌아보기 없이 */
function wordAtStart(name: string, q: string): boolean {
  const n = name.trim();
  if (!n) return false;
  let i = q.indexOf(n);
  while (i >= 0) {
    if (i === 0 || !WORD_CHAR.test(q[i - 1])) return true;
    i = q.indexOf(n, i + 1);
  }
  return false;
}

// 동네·도시 사전 (common/geo.py GAZETTEER 의 이름들) · 동네 → 구 (DISTRICT_OF)
const GAZETTEER = (
  "강남 서초 송파 잠실 마포 홍대 합정 연남 성동 성수 광진 건대 종로 명동 을지로 용산 이태원 영등포 여의도 강서 관악 신촌 이대 동대문 " +
  "노원 은평 구로 금천 강동 중랑 서대문 양천 도봉 강북 성북 동작 수원 성남 분당 판교 용인 고양 일산 부천 안양 송도 의정부 서면 해운대 " +
  "동성로 둔산 창원 전주 천안 청주 광화문 압구정 신사 가로수길 삼성 코엑스 왕십리 신림 목동 상암 망원 하남 스타필드 김포 파주 광명 시흥 " +
  "안산 화성 동탄 평택 오산 군포 의왕 과천 구리 남양주 광주시 이천 여주 양주 포천 동두천 가평 양평 안성 광교 부평 청라 영종 춘천 원주 " +
  "강릉 속초 세종 아산 공주 충주 군산 익산 목포 여수 순천 포항 경주 구미 안동 김해 진주 양산 거제 서귀포 세종대로"
).split(" ");
const DISTRICT_OF: Record<string, string> = {
  홍대: "서울 마포구",
  합정: "서울 마포구",
  연남: "서울 마포구",
  망원: "서울 마포구",
  상암: "서울 마포구",
  신촌: "서울 서대문구",
  이대: "서울 서대문구",
  성수: "서울 성동구",
  왕십리: "서울 성동구",
  건대입구: "서울 광진구",
  건대: "서울 광진구",
  잠실: "서울 송파구",
  용산: "서울 용산구",
  이태원: "서울 용산구",
  강남: "서울 강남구",
  압구정: "서울 강남구",
  삼성: "서울 강남구",
  코엑스: "서울 강남구",
  신사: "서울 강남구",
  가로수길: "서울 강남구",
  여의도: "서울 영등포구",
  명동: "서울 중구",
  을지로: "서울 중구",
  종로: "서울 종로구",
  광화문: "서울 종로구",
  신림: "서울 관악구",
  목동: "서울 양천구",
  서면: "부산 부산진구",
  해운대: "부산 해운대구",
  동성로: "대구 중구",
  둔산: "대전 서구",
  송도: "인천 연수구",
  부평: "인천 부평구",
  일산: "경기 고양시",
  킨텍스: "경기 고양시",
  수원: "경기 수원시",
  광교: "경기 수원시",
  판교: "경기 성남시",
  분당: "경기 성남시",
  동탄: "경기 화성시",
  스타필드: "경기 하남시",
};

function placeMatch(place: string, r: Item): boolean {
  if (r.address.includes(place) || r.name.includes(place)) return true;
  if (place === r.area || place === r.city) return true;
  const district = DISTRICT_OF[place];
  return !!district && norm(r.address).includes(norm(district));
}

export function parse(question: string, items: Item[], today: string): Query {
  const q = question.trim();
  const nq = norm(q);
  const query: Query = { works: [], characters: [], places: [], window: null, windowLabel: "", words: [], intent: "" };

  const works = [...new Set(items.map((r) => r.work.trim()).filter(Boolean))].sort((a, b) => b.length - a.length);
  for (let w of works) {
    let nw = norm(w);
    if (nw.length < 2 || STOP.has(nw)) continue;
    let hit: boolean;
    if (nw.length === 2) hit = wordAtStart(w, q);
    else {
      hit = nq.includes(nw) || (nw.length >= 4 && nq.includes(nw.slice(0, 4)));
      if (!hit) {
        const first = w.trim().split(/[\s·:×x-]+/)[0];
        hit = norm(first).length >= 3 && !STOP.has(norm(first)) && wordAtStart(first, q);
        if (hit) {
          w = first;
          nw = norm(first);
        }
      }
    }
    if (hit && !query.works.some((x) => norm(x).includes(nw) || nw.includes(norm(x)))) query.works.push(w);
  }

  const chars = [
    ...new Set(
      items.flatMap((r) =>
        r.characters
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
      ),
    ),
  ].sort((a, b) => b.length - a.length);
  for (const c of chars) {
    const nc = norm(c);
    if (nc.length < 2 || STOP.has(nc) || [...query.characters, ...query.works].some((x) => norm(x).includes(nc)))
      continue;
    if (nc.length > 2 ? nq.includes(nc) : wordAtStart(c, q)) query.characters.push(c);
  }

  const places = [...new Set([...GAZETTEER, ...items.map((r) => r.city)])]
    .filter((p) => p && p.length >= 2)
    .sort((a, b) => b.length - a.length);
  for (const p of places) if (q.includes(p) && !query.places.some((x) => x.includes(p))) query.places.push(p);

  [query.window, query.windowLabel] = windowOf(q, today);
  const known = [...query.works, ...query.characters, ...query.places].map(norm);
  for (const w of q.match(/[가-힣A-Za-z0-9]{2,}/g) || []) {
    const base = w.replace(PARTICLE, "");
    if (base.length < 2 || STOP.has(w) || STOP.has(base) || DATE_WORD.test(w) || DATE_WORD.test(base)) continue;
    if (known.some((k) => k && (norm(w).includes(k) || k.includes(norm(base))))) continue;
    query.words.push(base);
  }
  return query;
}

// ------------------------------------------------------------------ 검색
const ended = (r: Item, today: string) => !!r.end && r.end < today;
const overlaps = (r: Item, w: [string, string]) => !!(r.start && r.end && r.start <= w[1] && r.end >= w[0]);
const ongoing = (r: Item, today: string) => !!(r.start && r.end && r.start <= today && today <= r.end);
const bigText = (r: Item) => norm([r.work, r.characters, r.name, r.extra].join(" "));

/** 읽어 낸 조건(작품·캐릭터·장소·기간)에 모두 맞는 팝업. 점수 높은 순 (ask.py search) */
export function search(query: Query, items: Item[], today: string): Item[] {
  const scored: [number, Item][] = [];
  for (const r of items) {
    if (ended(r, today)) continue; // 끝난 팝업은 답하지 않는다
    if (query.window && !overlaps(r, query.window)) continue;
    let score = 0;
    const work = norm(r.work);
    if (query.works.length) {
      if (query.works.some((w) => work.includes(norm(w)) || (work && norm(w).includes(work)))) score += 5;
      else continue;
    }
    if (query.characters.length) {
      const ch = norm(r.characters);
      if (query.characters.some((c) => ch.includes(norm(c)) || work.includes(norm(c)))) score += 4;
      else continue;
    }
    if (query.places.length) {
      if (query.places.some((p) => placeMatch(p, r))) score += 3;
      else continue;
    }
    if (query.window) score += 2;
    const text = bigText(r);
    const extra = query.words.filter((w) => text.includes(norm(w))).length;
    if (extra) score += Math.min(extra, 3) * 0.5;
    else if (query.words.length && !(query.works.length || query.characters.length)) continue;
    if (score === 0) continue;
    scored.push([score + (ongoing(r, today) ? 0.3 : 0), r]);
  }
  scored.sort((a, b) => b[0] - a[0] || a[1].start.localeCompare(b[1].start));
  return scored.map((t) => t[1]);
}

// ------------------------------------------------------------------ 답 문장
export const GUIDE_HEAD = "말씀을 못 알아들었어요. 작품 이름 · 장소 · 날짜를 넣어서 물어봐 주세요.";
export const GUIDE_EXAMPLES = [
  "치이카와 이번 달 서울 팝업 있어?",
  "이번 주말 홍대 팝업",
  "12월 5일 부산에서 하는 팝업",
  "주술회전 팝업 언제까지야?",
  "곧 끝나는 팝업",
];
export const DEFAULT_CHIPS = [
  "내 주변 가까운 팝업",
  "팝업 추천해줘",
  "지금 진행 중인 서울 팝업",
  "곧 끝나는 팝업",
  "이번 주말 성수 팝업",
];
const NO_HIT = "조건에 맞는 팝업을 찾지 못했어요. 작품 이름을 줄이거나(예: 주술회전) 날짜·지역 조건을 하나 빼 보세요.";

function describe(q: Query): string {
  const parts: string[] = [];
  if (q.works.length) parts.push("작품 " + q.works.join(", "));
  if (q.characters.length) parts.push("캐릭터 " + q.characters.join(", "));
  if (q.places.length) parts.push("지역 " + q.places.join(", "));
  if (q.windowLabel) parts.push(q.windowLabel);
  return parts.join(" · ");
}

/** 조건을 말로: '이번 달 서울에서 하는 치이카와' (ask.py phrase) */
export function phrase(q: Query): string {
  const when = q.windowLabel === "오늘(진행 중)" ? "지금 진행 중인" : q.windowLabel;
  const where = q.places.length ? `${q.places.join("·")}에서 하는` : "";
  const what = [...q.works, ...q.characters.filter((c) => !q.works.some((w) => norm(w).includes(norm(c))))].join(" ");
  return [when, where, what].filter(Boolean).join(" ").trim();
}

function understood(q: Query, items: Item[]): boolean {
  const text = items.map(bigText).join(" ");
  const unknown = q.words.filter((w) => !text.includes(norm(w)));
  const known = q.words.filter((w) => text.includes(norm(w)));
  if (q.works.length || q.characters.length || q.places.length) return true;
  if (q.window) return !unknown.length || known.length > 0;
  return known.length > 0;
}

/** 0건일 때: 조건 하나를 빼면 몇 건인지 (ask.py relax_hint) */
function relaxHint(q: Query, items: Item[], today: string): string {
  const tips: string[] = [];
  const tries: [boolean, string, Partial<Query>][] = [
    [q.places.length > 0, q.places.join("·"), { places: [] }],
    [!!q.window, q.windowLabel, { window: null, windowLabel: "" }],
    [q.characters.length > 0, q.characters.join(", "), { characters: [] }],
    [q.works.length > 0, q.works.join(", "), { works: [] }],
  ];
  for (const [on, label, patch] of tries) {
    if (!on) continue;
    const q2 = { ...q, ...patch };
    if (!(q2.works.length || q2.characters.length || q2.places.length || q2.window)) continue;
    const n = search(q2, items, today).length;
    if (n) tips.push(`'${label === "오늘(진행 중)" ? "지금" : label}' 조건을 빼면 ${n}건 있어요`);
  }
  return tips.length ? " " + tips.slice(0, 2).join(" · ") + "." : "";
}

function countAnswer(q: Query, n: number, items: Item[], today: string): string {
  const cond = phrase(q) || `'${q.words.join("', '")}' 이(가) 들어간`;
  if (n) return `네, ${cond} 팝업이 ${n}건 있어요.` + (n > CARD_MAX ? ` 아래에 ${CARD_MAX}건까지 보여 드려요.` : "");
  const hint = relaxHint(q, items, today);
  return hint ? `현재 진행하는 팝업이 없어요. (${cond} 조건으로 찾았어요.)${hint}` : NO_HIT;
}

// ------------------------------------------------------------------ 자주 묻는 질문 (ask.py INTENTS)
const INTENTS: [string, RegExp][] = [
  ["me_nick", /(내|제|나의)\s*(닉네임|닉|별명|이름)|나\s*(는\s*)?(누구|이름)/],
  [
    "me_loc",
    /(내|제|나의|지금|현재)\s*(위치|있는\s*곳|동네)\s*(가|는|이|은)?\s*(어디|뭐|알려|확인)|나\s*(지금\s*)?어디|여기\s*(가\s*)?어디|현재\s*위치/,
  ],
  [
    "guide_add",
    /등록\s*(은|는|하는|하려면|하고\s*싶|방법|어떻게|할\s*수)|어떻게\s*등록|(팝업|카페)\s*(올리|추가)\s*(하|는|방법)/,
  ],
  [
    "guide_edit",
    /수정\s*(은|는|하는|하려면|방법|어떻게|할\s*수)|어떻게\s*(수정|고쳐|고치)|(정보|날짜|주소)\s*(가|이)?\s*(틀|잘못|달라)/,
  ],
  [
    "guide_delete",
    /삭제\s*(는|은|하는|하려면|방법|어떻게|요청|할\s*수)|어떻게\s*(삭제|지워|지우)|지우는\s*(법|방법)|내\s*(글|리뷰)\s*지우/,
  ],
  ["guide_bookmark", /북마크\s*(는|은|하는|하려면|방법|어떻게|가\s*뭐)|찜\s*(하는|어떻게|은|는)|어떻게\s*(북마크|찜)/],
  [
    "guide_login",
    /(로그인|로그아웃|회원\s*가입|가입|탈퇴)\s*(은|는|하는|하려면|방법|어떻게|안\s*(돼|되)|할\s*수)|어떻게\s*(로그인|가입|탈퇴)/,
  ],
  ["guide_cal", /캘린더\s*(는|은|가|뭐|어떻게|사용|보는)|알림\s*(은|는|이|언제|어떻게|왜|안\s*(와|오))/],
  ["guide_map", /지도\s*(보기)?\s*(는|은|어떻게|사용|보는\s*법)/],
  ["guide_list", /리스트\s*(보기)?\s*(는|은|어떻게|사용|보는\s*법)/],
  [
    "usage",
    /사용법|사용\s*방법|이용\s*방법|쓰는\s*(법|방법)|어떻게\s*(써|쓰|사용|이용)|가이드|도움말|매뉴얼|기능\s*(이|은|뭐|알려|소개)|뭐\s*할\s*수|뭘\s*할\s*수|뭘\s*물어|뭐\s*물어/,
  ],
  ["my_favs", /(내|제|나의)\s*(북마크|찜)/],
  ["today", /오늘\s*(이\s*)?(몇\s*월|며칠|몇\s*일|날짜|무슨\s*요일|요일)/],
  ["contact", /문의|연락처|고객\s*센터|신고|관리자\s*(에게|한테|연락|누구)|운영자/],
  ["who", /(너|넌|당신)\s*(는|은)?\s*(누구|뭐|무엇|뭘)|(너|넌)\s*(이름|정체)|자기\s*소개/],
  ["thanks", /^(고마워|고맙|감사|땡큐|thanks?|thx|잘\s*했)/i],
  [
    "count_all",
    /(팝업|카페)\s*(이|가|은|는)?\s*(몇\s*(개|곳|군데)|총|전체\s*몇)|몇\s*(개|곳)\s*(있|등록|열려)|등록된\s*팝업\s*(수|몇)/,
  ],
  ["help", /^(안녕|하이|hi|hello|반가|도움|도와)/i],
  ["blog_rank", /블로그.*(많|적|높|낮|순위|랭킹)|(많|적).*블로그/],
  ["rating_rank", /(별점|평점)\s*(이|가)?\s*(가장|제일|젤|높|낮|좋|나쁜|순|랭킹)|(높|낮|좋|나쁜)\S*\s*(별점|평점)/],
  ["review_rank", /(리뷰|후기|댓글)\s*(가|이)?\s*(가장|제일|젤)?\s*(많|적|없|순|랭킹)|(많|적)\S*\s*(리뷰|후기)/],
  ["near", /가까운|근처|주변|내\s*위치|여기서|가까이/],
  ["by_region", /지역\s*별|지역마다|동네\s*별|어느\s*지역|지역\s*순/],
  ["recommend", /추천|어디\s*갈까|갈\s*만한|가볼\s*만한|볼\s*만한|베스트|좋은\s*팝업/i],
  ["ending", /곧\s*끝|마감|끝나기\s*전|종료\s*임박|얼마\s*안\s*남|막바지|끝나는/],
  [
    "upcoming",
    /오픈\s*예정|곧\s*(열|시작|오픈)|새로\s*(열|생|오픈)|신규|예정\s*(된|중|인)|예정이|다가오는|오픈하는|시작하는|아직\s*(안\s*(열|시작)|시작\s*전|오픈\s*전|예정)|시작\s*전|오픈\s*전/,
  ],
  ["popular", /인기|북마크\s*많|핫한|사람\s*많|유명한/],
  ["reviewed", /리뷰\s*많|후기\s*많|후기\s*좋|별점\s*(높|좋)|평점/],
];

export function detectIntent(question: string): string | null {
  const q = question.trim();
  for (const [name, pat] of INTENTS) if (pat.test(q)) return name;
  return null;
}

/** 이 질문에 내 위치가 필요한가 (화면이 답하기 전에 위치 권한을 묻는다) */
export function needsLocation(question: string, items: Item[], today: string): boolean {
  const intent = detectIntent(question);
  if (intent === "me_loc") return true;
  return intent === "near" && parse(question, items, today).places.length === 0;
}

const HEADS: Record<string, string> = {
  near: "내 위치에서 가까운 순",
  recommend: "추천 (별점 → 리뷰 많은 순)",
  ending: "곧 끝나는 순",
  upcoming: "곧 열리는 순",
  popular: "별점 · 곧 끝나는 순",
  reviewed: "후기 많은 순",
  review_rank: "다녀온 후기 수 순",
  rating_rank: "별점 순",
};
export const headOf = (intent: string) => HEADS[intent] || "";

const GUIDE_SECTIONS: Record<string, string> = {
  map: "지도로 보기",
  list: "리스트로 보기",
  cal: "내 캘린더 · 알림",
  add: "팝업 등록하기",
  edit: "정보 수정하기",
  delete: "삭제 요청하기",
  bookmark: "북마크",
  login: "로그인 · 회원가입",
};
const GUIDE_TEXT: Record<string, string> = {
  add: "팝업 등록은 ANI:WHERE 앱에서 회원만 할 수 있어요. 앱 화면 오른쪽 아래 + 버튼 → 작품·카페·기간·주소를 넣고 저장하면 바로 지도와 리스트에 올라가요.",
  edit: "팝업 상세 화면의 '리뷰·북마크는 ANI:WHERE 앱에서'를 눌러 앱의 '수정하기' 탭에서 고칠 수 있어요 (회원만). 고친 기록은 모두 남아요.",
  delete:
    "글은 바로 지워지지 않고 앱에서 '삭제 요청'으로 받아요. 관리자가 확인하고 결과는 앱의 종 알림으로 알려 드려요.",
  bookmark:
    "북마크는 ANI:WHERE 앱에서 로그인하면 쓸 수 있어요. 북마크한 팝업은 내 캘린더에 날짜 막대로 보이고, 오픈·종료 3일 전부터 알림이 와요.",
  login: "메뉴바 오른쪽 '로그인'을 누르면 ANI:WHERE 앱에서 카카오·네이버 간편 로그인이나 아이디로 가입할 수 있어요.",
  cal: "내 캘린더(회원)는 ANI:WHERE 앱에서 북마크한 팝업을 날짜 막대로 보여 줘요. 알림은 북마크한 팝업의 오픈·종료 3일 전부터 와요.",
  map: "지도로 보기는 왼쪽 데일리 팝업 노트(날짜·지역별 목록)와 지도를 함께 봐요. 핀에 마우스를 올리면 카드, 누르면 그 자리의 팝업 목록이 열려요.",
  list: "리스트로 보기는 포스터 카드로 모아 봐요. 위에서 지역·정렬을 고르고, 아래 'N건 더보기'로 더 불러와요. 오른쪽에서 저에게 물어볼 수도 있어요.",
};
const guideLink = (key: string): [string, string][] => [
  [`사용자 튜토리얼 · ${GUIDE_SECTIONS[key]} 보기`, `/guide#${key}`],
];

function km(a: LatLng, b: LatLng): number {
  const r = (x: number) => (x * Math.PI) / 180;
  const h =
    Math.sin(r(b.lat - a.lat) / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(r(b.lng - a.lng) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

/** 질문 속 작품·지역·날짜 조건 + (기본) 진행 중만 (ask.py _filtered) */
function filtered(q: Query, items: Item[], today: string, ongoingOnly = true): Item[] {
  return items.filter((r) => {
    if (ended(r, today)) return false;
    if (ongoingOnly && !q.window && !ongoing(r, today)) return false;
    if (q.window && !overlaps(r, q.window)) return false;
    const work = norm(r.work);
    if (q.works.length && !(work && q.works.some((w) => work.includes(norm(w)) || norm(w).includes(work))))
      return false;
    if (q.places.length && !q.places.some((p) => placeMatch(p, r))) return false;
    return true;
  });
}

const rating = (r: Item) => r.rating ?? { avg: 0, n: 0 };
/** 홈 랭킹과 같은 뒷순서: 진행 중 먼저 → 곧 끝나는 순 → 최근 등록 순 */
const homeOrder = (today: string) => (a: Item, b: Item) =>
  Number(!ongoing(a, today)) - Number(!ongoing(b, today)) ||
  a.end.localeCompare(b.end) ||
  b.created.localeCompare(a.created);

function done(q: Query, intent: string, text: string, hits: Item[] = [], extra: Partial<AskResult> = {}): AskResult {
  q.intent = intent;
  return { text, hits, distances: {}, guide: false, links: [], query: q, ...extra };
}

function intentAnswer(question: string, items: Item[], today: string, ctx: AskCtx): AskResult | null {
  const intent = detectIntent(question);
  if (!intent) return null;
  const q = parse(question, items, today);
  const cond = describe(q);
  const condTxt = cond ? `${cond} 조건으로 ` : "";
  const loc = ctx.loc ?? null;

  if (intent === "help")
    return done(
      q,
      intent,
      "작품·지역·날짜로 물어보세요. 예: '내 주변 가까운 팝업', '팝업 추천해줘', '지금 진행 중인 부산 팝업', '곧 끝나는 팝업', '이번 주말 성수 팝업'.",
    );
  if (intent === "blog_rank")
    return done(
      q,
      intent,
      // 앱도 블로그 글 수를 못 셀 때(네이버 검색 연결 없음·한도) 이 문구. 웹 물어보기는 브라우저에서 돌아 글 수를 미리 세지 않는다
      "블로그 후기 수를 지금은 셀 수 없어요 (네이버 검색 연결이 꺼져 있거나 이번 달 검색 한도를 다 썼어요). 팝업 상세의 '블로그 후기' 탭에서 글을 볼 수 있어요.",
    );
  if (intent === "review_rank" || intent === "rating_rank") {
    const low = /적|낮|나쁜|없는|최하|꼴찌/.test(question);
    const pool = filtered(q, items, today, false).filter((r) => rating(r).n > 0);
    if (!pool.length)
      return done(
        q,
        intent,
        `${condTxt}아직 별점이 달린 팝업이 없어요. 다녀온 후기에 별점을 남기면 순위를 보여 드려요.`,
      );
    const val = (r: Item) => (intent === "rating_rank" ? rating(r).avg : rating(r).n);
    pool.sort((a, b) => (low ? val(a) - val(b) : val(b) - val(a)) || a.end.localeCompare(b.end));
    const word = intent === "rating_rank" ? "별점" : "다녀온 후기";
    const head = `${word} ${intent === "rating_rank" ? (low ? "낮은" : "높은") : low ? "적은" : "많은"} 순`;
    const unit = (r: Item) => (intent === "rating_rank" ? `별점 ${rating(r).avg.toFixed(1)}` : `후기 ${rating(r).n}개`);
    const lines = pool
      .slice(0, 3)
      .map((r, i) => `${i + 1}. ${r.work} (${unit(r)})`)
      .join(" · ");
    return done(q, intent, `${condTxt}${head}으로 ${pool.length}곳이에요. ${lines}`, pool);
  }

  // 나 · 사용법 · 잡담
  if (intent === "me_nick")
    return done(q, intent, "이 웹에서는 로그인하지 않아요. ANI:WHERE 앱에서 로그인하면 닉네임을 볼 수 있어요.", [], {
      links: guideLink("login"),
    });
  if (intent === "me_loc") {
    if (!loc) return done(q, intent, "내 위치를 알 수 없어요. 브라우저에서 위치 권한을 허용하면 알려 드릴게요.");
    let best: [number, Item] | null = null;
    for (const r of items) {
      if (r.lat === null || r.lng === null) continue;
      const k = km(loc, { lat: r.lat, lng: r.lng });
      if (!best || k < best[0]) best = [k, r];
    }
    const region = best ? best[1].area || best[1].city : "";
    if (!region) return done(q, intent, "위치는 받았는데 지역 이름을 찾지 못했어요. 지도로 보기에서 확인해 주세요.");
    return done(
      q,
      intent,
      `현재 위치는 ${region} 근처예요. '내 주변 가까운 팝업'이라고 물어보면 가까운 순으로 찾아 드려요.`,
    );
  }
  if (intent === "usage")
    return done(
      q,
      intent,
      "지도로 보기 · 리스트로 보기 · 내 캘린더 · 등록하기 · 수정하기 · 삭제 요청 방법을 한 페이지에 정리해 뒀어요. 아래 링크를 눌러 보세요.",
      [],
      {
        links: [["사용자 튜토리얼 열기", "/guide"]],
      },
    );
  if (intent.startsWith("guide_")) {
    const key = intent.slice(6);
    return done(q, intent, GUIDE_TEXT[key], [], { links: guideLink(key) });
  }
  if (intent === "today") {
    const { y, m, day } = ymdParts(today);
    return done(q, intent, `오늘은 ${y}년 ${m}월 ${day}일 ${WEEK_KO[wd(today)]}요일이에요.`);
  }
  if (intent === "who")
    return done(
      q,
      intent,
      "저는 ANI:WHERE 팝업 도우미예요. 등록된 애니 팝업·카페·굿즈 행사에서 작품·지역·날짜로 찾아 드려요.",
      [],
      {
        links: [["사용자 튜토리얼 열기", "/guide"]],
      },
    );
  if (intent === "thanks") return done(q, intent, "천만에요! 더 궁금한 팝업이 있으면 언제든 물어봐 주세요.");
  if (intent === "contact")
    return done(
      q,
      intent,
      "문의·신고는 개인정보처리방침의 연락처(10번)로 보내 주세요. 잘못된 글은 상세 화면의 '삭제 요청'으로 관리자에게 바로 알릴 수 있어요.",
      [],
      {
        links: [["개인정보처리방침 · 연락처 보기", "/privacy"]],
      },
    );
  if (intent === "count_all" || intent === "my_favs") {
    if (q.works.length || q.places.length || q.window) return null; // '주술회전 팝업 몇 개' → 검색으로
    if (intent === "my_favs")
      return done(q, intent, "북마크는 ANI:WHERE 앱에서 로그인하면 쓸 수 있어요.", [], { links: guideLink("login") });
    const live = items.filter((r) => ongoing(r, today)).length;
    const soon = items.filter((r) => r.start > today).length;
    return done(q, intent, `지금 진행 중인 팝업은 ${live}곳, 오픈 예정은 ${soon}곳이에요 (모두 ${live + soon}곳).`);
  }

  if (intent === "near") {
    if (q.places.length) return null; // '홍대 근처 팝업' → 그 지역 검색으로
    if (!loc)
      return done(
        q,
        intent,
        "내 위치를 알 수 없어요. 브라우저에서 위치 권한을 허용하면 가까운 순으로 찾아 드려요. '홍대 팝업'처럼 동네 이름으로 물어봐도 돼요.",
      );
    const cand = filtered(q, items, today)
      .filter((r) => r.lat !== null && r.lng !== null)
      .map((r) => [km(loc, { lat: r.lat as number, lng: r.lng as number }), r] as [number, Item])
      .sort((a, b) => a[0] - b[0]);
    if (!cand.length) return done(q, intent, `${condTxt}지금 열려 있는 팝업 중 위치를 아는 곳이 없어요.`);
    const distances: Record<string, number> = {};
    for (const [k, r] of cand) distances[r.id] = k;
    return done(
      q,
      intent,
      `${condTxt}내 위치에서 가까운 진행 중인 팝업이에요.`,
      cand.map((t) => t[1]),
      { distances },
    );
  }
  if (intent === "by_region") {
    const groups = new Map<string, Item[]>();
    for (const r of filtered(q, items, today)) {
      const g = r.city || "지역 미상";
      groups.set(g, [...(groups.get(g) ?? []), r]);
    }
    if (!groups.size) return done(q, intent, "지금 진행 중인 팝업이 없어요.");
    const order = [...groups.entries()].sort((a, b) => b[1].length - a[1].length);
    const summary = order.map(([g, v]) => `${g} ${v.length}곳`).join(" · ");
    const reps = order.map(
      ([, v]) => [...v].sort((a, b) => rating(b).avg - rating(a).avg || homeOrder(today)(a, b))[0],
    );
    return done(q, intent, `지역별 진행 중 팝업: ${summary}`, reps);
  }
  if (intent === "recommend" || intent === "popular") {
    const live = filtered(q, items, today);
    if (!live.length) return done(q, intent, `${condTxt}지금 진행 중인 팝업이 없어요. 조건을 하나 빼 보세요.`);
    // 별점 높은 순 → 리뷰 많은 순 → (북마크 수는 공개 데이터에 없어서) 곧 끝나는 순 → 최근 등록 순
    live.sort((a, b) => rating(b).avg - rating(a).avg || rating(b).n - rating(a).n || homeOrder(today)(a, b));
    const rated = live.some((r) => rating(r).n > 0);
    const why = rated ? "별점 높은 순 → 리뷰 많은 순" : "아직 별점이 없어 곧 끝나는 순";
    const pre = intent === "popular" ? "북마크 수는 ANI:WHERE 앱에서만 볼 수 있어서, " : "";
    // 추천은 그 순서의 상위 5곳만 — 나머지를 '더보기' 로 다 보여 주면 추천이 아니다 (11/20 요청, 앱 _done limit=5 와 같게).
    // '서울 팝업 추천해줘' 처럼 지역 · 작품 조건이 있으면 그 안에서 5곳 (filtered)
    return done(q, intent, `${condTxt}${pre}지금 갈 수 있는 팝업을 ${why}으로 골랐어요.`, intent === "recommend" ? live.slice(0, 5) : live);
  }
  if (intent === "ending") {
    const live = filtered(q, items, today)
      .filter((r) => r.end && diff(today, r.end) <= 7)
      .sort((a, b) => a.end.localeCompare(b.end));
    if (!live.length) return done(q, intent, `${condTxt}7일 안에 끝나는 팝업이 없어요.`);
    return done(q, intent, `${condTxt}7일 안에 끝나는 팝업이에요 (끝나는 날이 가까운 순).`, live);
  }
  if (intent === "upcoming") {
    const q2: Query = { ...q, window: null, windowLabel: "" };
    const soon = filtered(
      q2,
      items.filter((r) => r.start && r.start > today),
      today,
      false,
    ).sort((a, b) => a.start.localeCompare(b.start));
    if (!soon.length) return done(q, intent, `${condTxt}오픈 예정인 팝업이 없어요.`);
    return done(q, intent, `${condTxt}곧 열리는 팝업이에요 (시작일이 가까운 순).`, soon);
  }
  if (intent === "reviewed") {
    const live = filtered(q, items, today)
      .filter((r) => rating(r).n > 0)
      .sort((a, b) => rating(b).n - rating(a).n || rating(b).avg - rating(a).avg);
    if (!live.length) return done(q, intent, `${condTxt}아직 다녀온 후기가 달린 진행 중 팝업이 없어요.`);
    return done(q, intent, `${condTxt}다녀온 후기가 많은 진행 중 팝업이에요.`, live);
  }
  return null;
}

/** 질문 하나에 답한다 (ask.py answer 의 규칙 부분). AI 를 부르지 않고, 어디에도 보내지 않는다 */
export function answer(question: string, items: Item[], today: string, ctx: AskCtx = {}): AskResult {
  const qq = (question || "").trim().slice(0, MAX_QUESTION);
  const empty: Query = { works: [], characters: [], places: [], window: null, windowLabel: "", words: [], intent: "" };
  if (!qq) return done(empty, "invalid", "질문을 입력해 주세요. 예: 이번 주말 성수에서 하는 팝업 있어?");
  if (qq.length < 2) return done(empty, "invalid", "질문이 너무 짧아요. 작품 이름이나 지역을 함께 적어 주세요.");
  const special = intentAnswer(qq, items, today, ctx);
  if (special) return special;
  const q = parse(qq, items, today);
  if (!understood(q, items)) return done(q, "unknown", GUIDE_HEAD, [], { guide: true });
  const hits = search(q, items, today);
  return { text: countAnswer(q, hits.length, items, today), hits, distances: {}, guide: false, links: [], query: q };
}
