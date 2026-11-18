import "server-only";
import { mask } from "@/lib/guard";
import { EVENT_TAGS, parseLinks } from "@/lib/cafe-rules";
import { canonicalWork, characterAliases, workAliases } from "./cafe";
import { DISTRICT_OF, GAZETTEER } from "./geo";

// 간편등록: 형식 없는 팝업·콜라보 공지문 → 등록 칸 값 (common/notice.py parse_notice 를 그대로 옮긴 것).
// AI 없이 정규식 + 사전 + 문장 패턴만. 추측 금지(확인 안 되면 null), 애매하면 '검토대기'.

// ---------------- 날짜 도우미 (파이썬 date 대신 'YYYY-MM-DD') ----------------
type D = string;
function mkdate(y: unknown, m: unknown, d: unknown): D | null {
  const [Y, M, DD] = [Number(y), Number(m), Number(d)];
  if (![Y, M, DD].every(Number.isInteger) || Y < 1 || M < 1 || M > 12 || DD < 1) return null;
  const dt = new Date(Date.UTC(Y, M - 1, DD));
  if (dt.getUTCMonth() !== M - 1 || dt.getUTCDate() !== DD) return null;
  return `${String(Y).padStart(4, "0")}-${String(M).padStart(2, "0")}-${String(DD).padStart(2, "0")}`;
}
const ymd = (s: D) => s.split("-").map(Number) as [number, number, number];
function plusDays(s: D, n: number): D {
  const [y, m, d] = ymd(s);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}
/** 월=0 … 일=6 (파이썬 weekday) */
function weekdayOf(s: D): number {
  const [y, m, d] = ymd(s);
  return (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7;
}
const yearOf = (s: D) => ymd(s)[0];

const isAscii = (s: string) => /^[\x00-\x7F]*$/.test(s);
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\/-]/g, "\\$&");
const g = (re: RegExp) => new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g");

// ================================================================ 2. 전처리
const ZERO_WIDTH = /[​-‍⁠﻿]/g;
const LAUGH = /[ㅋㅎㅠㅜ]{2,}/g;
const EMOJI = /[\u{1F000}-\u{1FAFF}☀-☄☇-➿⭐⭕️]/gu;
const BULLET = /^[*\-•·▶▷►◆◇■□○●]\s*/;
const SENTENCE_SPLIT = /(?<=[.!?。])\s+|\n+/;

export function preprocess(raw: string): string {
  let t = String(raw || "").replace(/\r\n/g, "\n");
  t = t.replace(ZERO_WIDTH, "").replace(LAUGH, " ").replace(EMOJI, " ");
  return t
    .split("\n")
    .map((ln) => ln.replace(/[ \t]+/g, " ").trim())
    .join("\n")
    .trim();
}

function sentences(text: string): string[] {
  return text
    .split(SENTENCE_SPLIT)
    .filter((s) => s && s.trim())
    .map((s) => s.replace(BULLET, "").trim());
}

// ================================================================ 10. 부정·불확실
const NEGATION = /안\s*(?:한대요|해요|합니다|함)|없(?:대요|어요|습니다|음)|미정|추후\s*공지|예정\s*없/;
const UNCERTAIN = /같아요|같은데|인\s*것\s*같|라고\s*들었|듣긴\s*했|아시는\s*분|못\s*찾|정확(?:한|히)\s*(?:위치|날짜|정보)?\s*(?:는|은)?\s*(?:아직|모름|몰라)/;
const UNCERTAIN_FACTOR = 0.3;

// ================================================================ 6.1 운영시간
const TIME_RANGE = /\d{1,2}\s*:\s*\d{2}\s*[~\-–]\s*\d{1,2}\s*:\s*\d{2}/;
const HOURS_LINE = /^[^\n]*(?:운영|영업|오픈)\s*시간\s*[:：]?[^\n]*$/gm;

function maskHours(text: string): [string, string | null] {
  let hours: string | null = null;
  for (const m of text.matchAll(HOURS_LINE)) {
    const t = TIME_RANGE.exec(m[0]);
    hours = hours || (t ? t[0].replace(/\s/g, "") : m[0].replace(/^.*?시간\s*[:：]?\s*/, "").trim() || null);
  }
  text = text.replace(HOURS_LINE, "§TIME§");
  const out = text.replace(g(TIME_RANGE), (m) => {
    hours = hours || m.replace(/\s/g, "");
    return "§TIME§";
  });
  return [out, hours];
}

// ================================================================ 3. 작품명
const EVENT_WORD = "(?:팝업\\s*카페|콜라보\\s*카페|콜라보레이션|콜라보|팝업\\s*스토어|팝업|전시|페어)";
const TITLE_CANDIDATE = new RegExp(`([가-힣A-Za-z0-9·:!?☆★×\\s]{2,25}?)\\s*${EVENT_WORD}`);
const TITLE_NOISE = /^(?:(?:헐|와|야|이번에|이번|드디어|기다리던|혹시|너|요즘|진짜|대박|곧)\s+)+/;
const SHORT_CONTEXT = /^[\s\S]{0,20}?(?:카페|콜라보|팝업|전시|굿즈)/;
const PARTICLE = "(?:랑|이랑|와|과|하고|의|가|이|는|은|도|를|을|짱|님|쨩)?";

function isShort(alias: string): boolean {
  const k = alias.replace(/ /g, "");
  return (isAscii(k) && k.length <= 3) || (!isAscii(k) && k.length <= 2);
}

/** 띄어쓰기·대소문자를 가리지 않는 이름 패턴 (notice._alias_re) */
function aliasRe(alias: string): RegExp {
  const body = [...alias.replace(/ /g, "")].map(esc).join("\\s*");
  if (isAscii(alias)) return new RegExp(`(?<![A-Za-z])${body}(?![A-Za-z])`, "gi");
  if (isShort(alias)) return new RegExp(`(?<![가-힣])${body}(?=${PARTICLE}(?![가-힣]))`, "g");
  return new RegExp(body, "gi");
}

function findWork(text: string): [string | null, number, string] {
  let best: [string, string] | null = null;
  for (const [work, names] of workAliases()) {
    for (const a of names) {
      for (const m of text.matchAll(aliasRe(a))) {
        if (isShort(a) && !SHORT_CONTEXT.test(text.slice((m.index ?? 0) + m[0].length))) continue;
        if (best === null || m[0].length > best[1].length) best = [work, m[0]];
        break;
      }
    }
  }
  if (best) return [best[0], 1.0, best[1]];
  let m = /^\s*(?:작품명?|IP)\s*[:：]\s*(.+)$/m.exec(text);
  if (m) return [canonicalWork([...m[1].trim()].slice(0, 40).join("")), 0.9, m[0]];
  m = /[『「《〈]([^』」》〉\n]{2,40})[』」》〉]/.exec(text);
  if (m) return [canonicalWork(m[1].trim()), 0.8, m[0]];
  for (const s of sentences(text)) {
    const t = TITLE_CANDIDATE.exec(s);
    if (!t) continue;
    let cand = t[1].split(/[\]】』」)|]/).pop() || "";
    cand = cand.trim().replace(/^[#[【]+/, "").trim().replace(TITLE_NOISE, "");
    cand = stripStore(cand);
    if (cand.length >= 2 && !/^[\d\s]+$/.test(cand)) return [canonicalWork(cand), 0.6, s];
  }
  for (const tm of text.matchAll(/#([^\s#]+)/g)) {
    const name = tm[1].replace(/_/g, " ").replace(new RegExp(`${EVENT_WORD}$`), "").trim();
    if (name.length >= 2) return [canonicalWork(name), 0.5, `#${tm[1]}`];
  }
  return [null, 0, ""];
}

// ================================================================ 4. 카페명
const STORES: Record<string, string[]> = {
  "애니메이트 카페": ["애니메이트 카페", "애니메이트카페", "animate cafe"],
  애니메이트: ["애니메이트", "animate"],
  애니플러스: ["애니플러스", "aniplus"],
  "일러스타 카페": ["일러스타 카페", "일러스타카페"],
  브이스퀘어: ["브이스퀘어", "v square"],
  Gratte: ["gratte", "그라떼"],
  JS스토어: ["js스토어", "제이에스스토어", "jsstore"],
};
const BRANCH = /(홍대|합정|서면|잠실\s*롯데|잠실|성수|신촌|건대입구|용산|강남|부산|대구|일산|수원)\s*(점|지점)?/;
const VENUE =
  /((?:롯데월드몰|아이파크몰|현대백화점|신세계백화점|롯데백화점|AK\s*(?:&|플라자|PLAZA)\s*홍대|더현대\s*서울|킨텍스|코엑스|에스팩토리|무신사\s*스토어|스타필드)(?:\s*[가-힣]{1,6}점)?(?:\s*(?:유플렉스|[가-힣]{1,4}관))?)/i;
const FLOOR = /(지하\s*\d+\s*층|B\d+층?|\d{1,2}\s*층|\d{1,2}\s*F)(?![A-Za-z0-9])/i;
const GENERIC_VENUE = /(?:에\s*있는|쪽에?\s*있는)\s*(?:카페|매장|곳)/;
const NAMED_CAFE =
  /(?<![가-힣A-Za-z])((?:카페|cafe)\s+[가-힣A-Za-z]{2,10}|[가-힣A-Za-z]{2,10}(?:카페|커피|cafe|coffee))(?:\s+([가-힣A-Za-z0-9]{1,8}점))?/gi;
const NOT_NAME = /^(?:콜라보|팝업|테마|이색|그|이|한|어떤|무슨|그런|이번|있는|근처)\s*(?:카페|cafe)|(?:콜라보|팝업|테마)(?:카페|cafe)$/i;

function stripStore(text: string): string {
  for (const names of Object.values(STORES)) for (const a of names) text = text.replace(aliasRe(a), "");
  return text.replace(g(BRANCH), "").replace(/^[ ·\-|]+|[ ·\-|]+$/g, "");
}

function label(text: string, labels: string): [string, string] | null {
  const m = new RegExp(`^\\s*(?:[*\\-•·]\\s*)?(${labels})\\s*[:：]\\s*(.+)$`, "m").exec(text);
  return m ? [m[1], m[2].trim()] : null;
}

const PROV = "서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주";
const ROAD = new RegExp(
  `((?:(?:${PROV})[가-힣]*\\s+)?(?:[가-힣]{1,10}(?:시|군|구)\\s+){0,2})?` +
    "([가-힣]{1,8}동\\s+)?" +
    "((?<!으)[가-힣A-Za-z0-9]{1,15}(?:대로|로|길)(?:\\s*\\d+(?:번)?길)?\\s*\\d+(?:-\\d+)?)" +
    "(?!\\s*(?:종|개|명|원|장|회|일|월|시|번째|%|가지|인|분|세))",
);
const LOT = new RegExp(`((?:(?:${PROV})[가-힣]*\\s+)?[가-힣]{1,10}(?:시|군|구))\\s*([가-힣]{1,10}동)\\s*(\\d+(?:-\\d+)?)(?:번지)?`);
const REGION_IN_ADDR = new RegExp(`(${PROV})[가-힣]*\\s+([가-힣]{1,10}(?:시|군|구))`);
const trimChars = (s: string, chars: string) => s.replace(new RegExp(`^[${chars}]+|[${chars}]+$`, "g"), "");

function findCafe(text: string): [string | null, number, string] {
  const lab = label(text, "카페명|카페|매장명?|장소|위치");
  if (lab) {
    const value = lab[1];
    if (value && !/입력해주세요|확인 필요|미정/.test(value)) {
      let name = value.replace(/\(.*?\)/g, "");
      name = ROAD.test(name) ? name.replace(g(ROAD), "") : name;
      name = name.replace(g(FLOOR), "");
      name = trimChars(name.replace(new RegExp(`^(?:${PROV})\\S*\\s*`), ""), " ,·\\-");
      name = trimChars(name.replace(/^[가-힣]{1,10}(?:시|군|구)\s+/, ""), " ,·\\-");
      if (name && !GENERIC_VENUE.test(value)) return [mask([...name].slice(0, 40).join("")), 1.0, value];
    }
  }
  const anyStore = Object.values(STORES).some((n) => n.some((a) => aliasRe(a).test(text)));
  if (GENERIC_VENUE.test(text) && !anyStore) return [null, 0, ""];
  for (const [store, names] of Object.entries(STORES)) {
    for (const a of names) {
      const m = new RegExp(aliasRe(a).source, aliasRe(a).flags.replace("g", "")).exec(text);
      if (!m) continue;
      const s0 = m.index;
      const e0 = s0 + m[0].length;
      const near = text.slice(Math.max(0, s0 - 12), s0) + " " + text.slice(e0, e0 + 15);
      const b = BRANCH.exec(text.slice(e0, e0 + 15)) || BRANCH.exec(text.slice(Math.max(0, s0 - 12), s0));
      let name = store;
      if (b) name = `${store} ${b[1].replace(/\s+/g, "")}${b[2] || "점"}`;
      return [name, 0.9, near.trim()];
    }
  }
  for (const s of sentences(text)) {
    const m = VENUE.exec(s);
    if (m && !GENERIC_VENUE.test(s.slice(m.index + m[0].length, m.index + m[0].length + 15)))
      return [m[1].replace(/\s+/g, " ").trim(), 0.6, s];
  }
  for (const s of sentences(text)) {
    if (s.startsWith("#")) continue;
    for (const m of s.matchAll(NAMED_CAFE)) {
      let name = m[1].trim();
      const end = (m.index ?? 0) + m[0].length;
      if (NOT_NAME.test(name) || GENERIC_VENUE.test(s.slice(end, end + 10))) continue;
      const rest = name.replace(/^(?:카페|cafe)\s+|(?:카페|커피|cafe|coffee)$/gi, "");
      if (rest in DISTRICT_OF || rest in GAZETTEER || /^\s*쪽/.test(s.slice(end))) continue;
      if (m[2]) name = `${name} ${m[2]}`;
      return [mask([...name].slice(0, 40).join("")), 0.6, s];
    }
  }
  return [null, 0, ""];
}

// ================================================================ 5. 주소 / 지역
function districtOfGu(gu: string): string | null {
  return Object.values(DISTRICT_OF).find((v) => v.endsWith(" " + gu)) ?? null;
}

function findArea(text: string): string | null {
  let m = REGION_IN_ADDR.exec(text);
  if (m) return `${m[1]} ${m[2]}`;
  const hits = Object.keys(DISTRICT_OF)
    .filter((k) => text.includes(k))
    .map((k) => [text.indexOf(k), k] as [number, string]);
  if (hits.length) {
    hits.sort((a, b) => a[0] - b[0] || b[1].length - a[1].length);
    return DISTRICT_OF[hits[0][1]];
  }
  m = /([가-힣]{1,10}구)(?![가-힣])/.exec(text);
  if (m && districtOfGu(m[1])) return districtOfGu(m[1]);
  m = new RegExp(`(?<![가-힣])(${PROV})(?![가-힣])`).exec(text);
  return m ? m[1] : null;
}

function findAddress(text: string): [string | null, number, string] {
  const lab = label(text, "주소|위치|장소");
  const sources = [...(lab ? [lab[1]] : []), ...sentences(text)];
  for (let i = 0; i < sources.length; i++) {
    const s = sources[i];
    const conf = lab && i === 0 ? 1.0 : 0.9;
    let m = ROAD.exec(s);
    if (m) {
      let prefix = (m[1] || "").trim();
      const dong = (m[2] || "").trim();
      let road = m[3];
      if (!/(?:시|군|구)$/.test(prefix)) {
        const k = Object.keys(DISTRICT_OF).find((k) => `${dong} ${prefix}`.includes(k));
        prefix = (k && DISTRICT_OF[k]) || prefix;
      } else if (!new RegExp(`^(?:${PROV})`).test(prefix)) {
        prefix = districtOfGu(prefix.split(/\s+/).pop() || "") || prefix;
      }
      road = road.replace(/\s+/g, " ");
      let addr = `${prefix} ${road}`.trim();
      const venue = VENUE.exec(s);
      const floor = FLOOR.exec(s);
      if (venue && !addr.includes(venue[1])) addr += " " + venue[1].replace(/\s+/g, " ");
      if (floor) addr += " " + floor[1].replace(/\s+/g, "");
      return [mask([...addr].slice(0, 80).join("")), conf, s];
    }
    m = LOT.exec(s);
    if (m) return [mask([m[1], m[2], m[3]].join(" ").slice(0, 80)), conf, s];
  }
  return [null, 0, ""];
}

// ================================================================ 6. 기간
const WD = "월화수목금토일";
const WEEKDAY = new RegExp(`(\\d{1,2})\\s*(?:월\\s*|[/.]\\s*)(\\d{1,2})\\s*일?\\s*\\(\\s*([${WD}])(?:요일)?\\s*\\)`, "g");
const SEP = "(?:부터|~|-|–|〜)";
const DATE_PATTERNS: [string, RegExp][] = [
  ["ymd_kr", new RegExp(`(\\d{4})\\s*년\\s*(\\d{1,2})\\s*월\\s*(\\d{1,2})\\s*일\\s*${SEP}+\\s*(?:(\\d{4})\\s*년\\s*)?(?:(\\d{1,2})\\s*월\\s*)?(\\d{1,2})\\s*일`)],
  ["ymd_dot", new RegExp(`(\\d{4})\\s*[.\\-/]\\s*(\\d{1,2})\\s*[.\\-/]\\s*(\\d{1,2})\\.?\\s*(?:${SEP}|부터)\\s*(?:(\\d{4})\\s*[.\\-/]\\s*)?(\\d{1,2})\\s*[.\\-/]\\s*(\\d{1,2})`)],
  ["md_kr", new RegExp(`(\\d{1,2})\\s*월\\s*(\\d{1,2})\\s*일?\\s*${SEP}\\s*(?:(\\d{1,2})\\s*월\\s*)?(\\d{1,2})\\s*일`)],
  ["md_slash", new RegExp(`(?<![\\d.])(\\d{1,2})\\s*[/.]\\s*(\\d{1,2})\\s*${SEP}\\s*(?:(\\d{1,2})\\s*[/.]\\s*)?(\\d{1,2})(?![\\d:])`)],
];
const SINGLE = /(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(부터|까지|시작|종료|오픈|마감)/g;
const SINGLE_LABELED = /^\s*(?:기간|일정|날짜|일시)\s*[:：]\s*(?:(\d{4})\s*[년.\-/]\s*)?(\d{1,2})\s*[월.\-/]\s*(\d{1,2})/m;
const TWO_ISO = /(20\d{2})[-.](\d{1,2})[-.](\d{1,2})/g;
const VAGUE = /\d{1,2}\s*월\s*(?:초순|중순|하순|중순경|말경|초|말|중)(?![가-힣])|\d{1,2}\s*월\s*경/;

function fixYear(start: D, end: D | null, today: D): [D, D | null] {
  if (end && end < start) {
    const [y, m, d] = ymd(end);
    end = mkdate(y + 1, m, d);
  }
  const shift = (s: D | null, n: number) => {
    if (!s) return s;
    const [y, m, d] = ymd(s);
    return mkdate(y + n, m, d);
  };
  if (start < plusDays(today, -183)) return [shift(start, 1) as D, shift(end, 1)];
  if (start > plusDays(today, 365)) return [shift(start, -1) as D, shift(end, -1)];
  return [start, end];
}

function checkWeekday(d: D | null, weekdays: Map<string, string>, explicitYear: boolean): [D | null, boolean] {
  if (d === null) return [d, true];
  const [y, m, dd] = ymd(d);
  const want = weekdays.get(`${m}-${dd}`);
  if (want === undefined) return [d, true];
  const idx = WD.indexOf(want);
  const years = explicitYear ? [y] : [y, y - 1, y + 1];
  for (const yy of years) {
    const c = mkdate(yy, m, dd);
    if (c && weekdayOf(c) === idx) return [c, true];
  }
  return [null, false];
}

export function findDates(text: string, today: D): [D | null, D | null, number, string[]] {
  const notes: string[] = [];
  const weekdays = new Map<string, string>();
  for (const m of text.matchAll(WEEKDAY)) weekdays.set(`${Number(m[1])}-${Number(m[2])}`, m[3]);
  const plain = text.replace(new RegExp(`\\s*\\(\\s*[${WD}](?:요일)?\\s*\\)`, "g"), "");
  let start: D | null = null;
  let end: D | null = null;
  let explicit = false;
  const ty = yearOf(today);
  for (const [kind, pat] of DATE_PATTERNS) {
    const m = pat.exec(plain);
    if (!m) continue;
    if (kind === "ymd_kr" || kind === "ymd_dot") {
      const [, y1, m1, d1, y2, m2, d2] = m;
      start = mkdate(y1, m1, d1);
      end = mkdate(y2 || y1, m2 || m1, d2);
      explicit = true;
      if (start && end && end < start && !y2) end = mkdate(Number(y1) + 1, m2 || m1, d2);
    } else {
      const [, m1, d1, m2, d2] = m;
      start = mkdate(ty, m1, d1);
      end = mkdate(ty, m2 || m1, d2);
    }
    break;
  }
  if (start === null) {
    const isos = [...plain.matchAll(TWO_ISO)];
    if (isos.length >= 2) {
      start = mkdate(isos[0][1], isos[0][2], isos[0][3]);
      end = mkdate(isos[1][1], isos[1][2], isos[1][3]);
      explicit = true;
    }
  }
  if (start === null) {
    const m = SINGLE_LABELED.exec(plain);
    if (m) {
      start = end = mkdate(m[1] || ty, m[2], m[3]);
      explicit = !!m[1];
    }
  }
  if (start === null) {
    for (const m of plain.matchAll(SINGLE)) {
      const d = mkdate(m[1] || ty, m[2], m[3]);
      explicit = explicit || !!m[1];
      if (["부터", "시작", "오픈"].includes(m[4])) start = start || d;
      else end = end || d;
    }
    if (start || end) notes.push("기간의 시작이나 끝 중 하나만 있어요");
  }
  if (start === null && end === null) {
    notes.push(VAGUE.test(plain) ? "'11월 중순' 같은 흐릿한 기간은 날짜로 바꾸지 않았어요" : "기간을 찾지 못했어요");
    return [null, null, 0, notes];
  }
  if (!explicit && start) [start, end] = fixYear(start, end, today);
  const w1 = checkWeekday(start, weekdays, explicit);
  const w2 = checkWeekday(end, weekdays, explicit);
  start = w1[0];
  end = w2[0];
  const ok1 = w1[1];
  const ok2 = w2[1];
  if (!(ok1 && ok2)) {
    notes.push("원문의 요일과 맞는 날짜가 없어요 (지난 행사일 수 있어요)");
    return [null, null, 0, notes];
  }
  if (start && end && end < start) {
    notes.push("종료일이 시작일보다 빨라요");
    return [null, null, 0, notes];
  }
  return [start, end, start && end ? 1.0 : 0.5, notes];
}

// ================================================================ 7. 캐릭터
const CHAR_CONTEXT = /캐릭터|굿즈|메뉴|특전|등장|\d+\s*명|의\s*(?:특별|한정)|라떼|케이크|음료|드링크|디저트/;

function findCharacters(text: string, sents: string[], work: string | null, workText: string): string[] {
  const lab = label(text, "캐릭터|등장\\s*캐릭터|참여\\s*캐릭터");
  const names = work ? characterAliases(work) : {};
  if (lab) {
    const found = lab[1]
      .split(/[,/·、]|\s+(?:랑|와|과|하고)\s+/)
      .map((c) => c.trim())
      .filter((c) => c && !/확인 필요|입력해주세요|해당 없음/.test(c));
    return [...new Set(found.map((c) => names[c] ?? c))].slice(0, 10);
  }
  if (!Object.keys(names).length) return [];
  const out: string[] = [];
  const aliases = Object.keys(names).sort((a, b) => b.length - a.length);
  for (let s of sents) {
    if (!CHAR_CONTEXT.test(s)) continue;
    if (workText) s = s.split(workText).join(" ");
    const hits: [number, number, string][] = [];
    for (const alias of aliases) {
      const re = new RegExp(`(?<![가-힣A-Za-z])${esc(alias)}(?=${PARTICLE}(?:[^가-힣A-Za-z]|$))`, "g");
      for (const m of s.matchAll(re)) {
        const st = m.index ?? 0;
        if (!hits.some(([a, b]) => a <= st && st < b)) hits.push([st, st + m[0].length, names[alias]]);
      }
    }
    hits.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    out.push(...hits.map((h) => h[2]));
  }
  return [...new Set(out)].slice(0, 10);
}

// ================================================================ 8. 특전 vs 굿즈
const GIVE = /증정|제공|지급|드립니다|드려요|드림|준다|줍니다|준대|주는|받을\s*수\s*있|사은품|방문\s*혜택|선착순|특전/;
const SELL = /판매|출시|발매|구매\s*가능|판대|나온다|나와요|나옵니다|라인업|팔아|판다|팝니다/;
const CONDITION =
  /((?:음료|드링크|메뉴|디저트|한정\s*메뉴|콜라보\s*메뉴)\s*(?:1\s*잔\s*|1\s*개\s*)?(?:당\s*)?(?:주문|구매|시키면|시키시면|주문하면|주문하시면|사면)\s*(?:시|하시면|하면)?|(?:굿즈\s*)?\d+[만천]?\s*원\s*이상\s*(?:구매|결제)\s*(?:시|하면|하시면)?|방문\s*시|(?:음료|드링크|메뉴|디저트|입장|방문)\s*특전)/;
const PERK_WORDS = ["포토카드", "포카", "코스터", "컵홀더", "엽서", "스티커", "클리어파일", "랜덤 카드", "일러스트 카드", "포스터", "브로마이드", "티켓"];
const GOODS_WORDS = ["아크릴 스탠드", "아크릴 키링", "캔뱃지", "캔배지", "키링", "인형", "피규어", "머그", "에코백", "쿠션", "담요", "파우치", "블라인드"];
// 파이썬 sorted(set(...), key=len, reverse=True) — 같은 길이끼리의 순서는 집합 순서라 정해져 있지 않다. 여기서는 글자 순으로 고정
const ITEM_NOUNS = [
  ...new Set([
    "코스터", "포토카드", "엽서", "엽서 세트", "스티커", "포스터", "태피스트리", "미니 태피스트리",
    "아크릴 스탠드", "아크릴스탠드", "아크릴 키링", "키링", "캔뱃지", "뱃지", "badge", "인형", "쿠션",
    "마스킹테이프", "클리어파일", "머그컵", "틴케이스", "봉투", "카드",
    ...PERK_WORDS, ...GOODS_WORDS,
  ]),
].sort((a, b) => b.length - a.length || (a < b ? -1 : a > b ? 1 : 0));
const MODIFIER = "(?:(?:랜덤|한정|특별|오리지널|캐릭터|일러스트|미니|콜라보|스페셜)\\s*)*";
const CLAUSE_SPLIT = /,\s*|，\s*|\s\/\s|\s그리고\s|\s및\s|(?<=[가-힣])(?:하고|하며|이고|고|며)\s+/;

function items(clause: string): string[] {
  const taken: [number, number][] = [];
  const out: [number, string][] = [];
  for (const noun of ITEM_NOUNS) {
    for (const m of clause.matchAll(new RegExp(MODIFIER + esc(noun), "gi"))) {
      const s = m.index ?? 0;
      const e = s + m[0].length;
      if (taken.some(([a, b]) => a < e && s < b)) continue;
      taken.push([s, e]);
      out.push([s, m[0].replace(/\s+/g, " ").trim()]);
    }
  }
  return out.sort((a, b) => a[0] - b[0]).map((x) => x[1]);
}

function condition(clause: string): string {
  const m = CONDITION.exec(clause);
  if (!m) return "";
  let c = m[0].replace(/\s+/g, " ").trim();
  c = c.replace(/(시키면|시키시면|주문하면|주문하시면|사면)$/, "주문 시");
  c = c.replace(/(주문|구매|결제)\s*(하면|하시면)$/, "$1 시");
  c = c.replace(/(주문|구매|결제)$/, "$1 시");
  c = c.replace(/1\s*잔\s*당?\s*|1\s*개\s*당?\s*|당\s+/g, "");
  return c;
}

function perksGoods(sents: string[]): [string[], string[]] {
  const perks: string[] = [];
  let goods: string[] = [];
  const given = new Set<string>();
  const sells: [string, boolean][] = [];
  const lastWord = (i: string) => i.split(/\s+/).pop() || i;
  for (const s of sents) {
    const give = GIVE.test(s);
    const sell = SELL.test(s);
    const clauses = give !== sell ? [s] : give && sell ? s.split(CLAUSE_SPLIT) : [];
    for (const c of clauses) {
      let cg = GIVE.test(c);
      let cs = SELL.test(c);
      if (give && sell && cg === cs) {
        cg = give && !sell;
        cs = sell && !give;
      }
      if (cg && !cs) {
        const multi = (c.match(new RegExp(CONDITION.source, "g")) || []).length > 1;
        for (const part of multi ? c.split(CLAUSE_SPLIT) : [c]) {
          const its = items(part);
          if (!its.length) continue;
          its.forEach((i) => given.add(lastWord(i)));
          const cond = condition(part) || condition(s);
          perks.push(`${cond ? cond + " " : ""}${its.join(", ")} 증정`);
        }
      } else if (cs && !cg) sells.push([c, give && sell]);
    }
  }
  for (const [c, mixed] of sells) {
    let its = items(c).filter((i) => !(mixed && given.has(lastWord(i))));
    if (!its.length) {
      const m = /((?:캐릭터|한정|콜라보|오피셜|공식)\s*굿즈)/.exec(c);
      its = m ? [m[1].replace(/\s+/g, " ")] : [];
    }
    goods = goods.concat(its);
  }
  return [[...new Set(perks)].slice(0, 10), [...new Set(goods)].slice(0, 10)];
}

// ================================================================ 9. 이벤트
const EVENT_WORDS: Record<string, string[]> = {
  "사전 예약": ["사전 예약", "사전예약", "예약제", "예약 후 입장", "선예약", "예약 판매"],
  "럭키 드로우": ["럭키드로우", "럭키 드로우", "럭드"],
  가챠: ["가챠", "캡슐"],
  "미성년자 입장불가": ["미성년자", "19세", "성인만"],
  포토부스: ["포토부스", "포토 부스", "네컷", "인생네컷"],
  "스탬프 투어": ["스탬프"],
  "랜덤 특전": ["랜덤 특전"],
};
const OTHER_EVENTS = ["래플", "추첨", "이벤트 존", "포토존", "전시", "상영", "토크쇼"];
const nospace = (s: string) => s.replace(/\s+/g, "");

export function eventTags(text: string): string[] {
  const compact = nospace(text);
  return EVENT_TAGS.filter((t) => (EVENT_WORDS[t] || [t]).some((w) => compact.includes(nospace(w))));
}

// ================================================================ 14. 전체 순서
export type Parsed = {
  work: string | null;
  cafe_name: string | null;
  address: string | null;
  area: string | null;
  start_date: string | null;
  end_date: string | null;
  characters: string[];
  perks: string[];
  goods: string[];
  tags: string[];
  events: string[];
  hours: string | null;
  links: string[];
  confidence: Record<string, number>;
  status: "자동등록" | "검토대기";
  reasons: string[];
};

/** 공지 한 건 → 등록 칸 값 + 신뢰도 + 상태 + 이유 (notice.parse_notice). '---' 줄로 나누면 첫 번째만 */
export function parseNotice(rawText: string, today: D): Parsed {
  const raw = String(rawText || "").split(/\n\s*(?:-{3,}|={3,})\s*\n/)[0];
  const text = preprocess(raw);
  const [masked, hours] = maskHours(text);
  const sents = sentences(masked);
  const usable = sents.filter((s) => !NEGATION.test(s));
  const uncertain = sents.filter((s) => UNCERTAIN.test(s));
  const conf = (value: number, source: string) =>
    source && uncertain.some((u) => source.includes(u) || u.includes(source)) ? Math.round(value * UNCERTAIN_FACTOR * 100) / 100 : value;

  const [work, cWork, workSrc] = findWork(masked);
  const [start, end, cDate, notes] = findDates(masked, today);
  const [address, cAddr, addrSrc] = findAddress(masked);
  const area = findArea(address || masked);
  const [cafeName, cCafe, cafeSrc] = findCafe(masked);
  const characters = findCharacters(masked, usable, work, workSrc);
  const perkLab = label(masked, "특전");
  const goodsLab = label(masked, "굿즈");
  const rest = usable.filter((s) => !/^\s*(?:특전|굿즈)\s*[:：]/.test(s));
  let [perks, goods] = perksGoods(rest);
  const splitV = (v: string) =>
    v
      .split(/\s*[,/·、]\s*/)
      .map((p) => p.trim())
      .filter((p) => p && !/입력해주세요|확인 필요/.test(p));
  if (perkLab) perks = splitV(perkLab[1]).length ? splitV(perkLab[1]) : perks;
  if (goodsLab) goods = splitV(goodsLab[1]).length ? splitV(goodsLab[1]) : goods;
  const eventsText = usable.join(" ");
  const tags = eventTags(eventsText);
  const others = OTHER_EVENTS.filter((e) => nospace(eventsText).includes(nospace(e)));

  const confidence: Record<string, number> = {
    작품명: cWork,
    카페명: conf(cCafe, cafeSrc),
    주소: conf(cAddr, addrSrc),
    기간: cDate,
  };
  if (uncertain.some((u) => /\d{1,2}\s*(?:월|\/)/.test(u))) confidence["기간"] = Math.round(confidence["기간"] * UNCERTAIN_FACTOR * 100) / 100;
  const reasons = [...notes];
  if (!work) reasons.push("작품명을 찾지 못했어요");
  else if (confidence["작품명"] < 0.8) reasons.push("작품명이 목록에 없어 확인이 필요해요");
  if (!(address || area)) reasons.push("주소나 지역을 찾지 못했어요");
  if (uncertain.length) reasons.push("'~같아요', '아시는 분' 같은 불확실한 표현이 있어요");
  const ended = !!(end && end < today);
  if (ended) reasons.push(`이미 끝난 행사예요 (${start} ~ ${end}). 요일로 연도를 맞췄다면 지난 공지일 수 있어요`);
  const auto = !!(work && confidence["작품명"] >= 0.8 && start && end && (address || area) && !uncertain.length && !ended);
  return {
    work,
    cafe_name: cafeName,
    address,
    area,
    start_date: start,
    end_date: end,
    characters,
    perks,
    goods,
    tags,
    events: others,
    hours,
    links: parseLinks((raw.match(/https?:\/\/\S+/g) || []).join(" "))[0],
    confidence,
    status: auto ? "자동등록" : "검토대기",
    reasons: [...new Set(reasons)],
  };
}
