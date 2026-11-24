// 서버·브라우저 양쪽에서 쓰는 순수 함수와 타입. 네트워크·키는 여기 두지 않는다 (lib/data.ts 전용).

export type Status = "ongoing" | "upcoming" | "ended" | "undated";

export type Popup = {
  id: string;
  name: string;
  work: string;
  characters: string;
  address: string;
  region: string;
  /** 카드 배지용 짧은 지역 이름 (앱 geo.area_name 과 같은 규칙: 서울은 구 '마포', 그 밖은 시 '부산') */
  area: string;
  /** 배지 색을 정하는 시 이름 (서울의 구는 모두 '서울') */
  city: string;
  lat: number | null;
  lng: number | null;
  start: string; // YYYY-MM-DD 또는 ''
  end: string; // YYYY-MM-DD 또는 ''
  perks: string[];
  goods: string[];
  tags: string[];
  images: string[]; // 완성된 이미지 URL. 첫 번째가 포스터
  links: string[]; // recal.kr 은 맨 뒤
  intro: string;
  updatedAt: string;
  /** 처음 등록한 시각 (첫 revision). 모르면 updatedAt */
  createdAt: string;
  rating: { avg: number; n: number } | null;
};

export type DataSource = "supabase" | "github" | "none";

/** 앱(Streamlit)의 static/default_poster.png 를 작게 줄인 것 */
export const PLACEHOLDER_POSTER = "/default_poster.webp";

// ---- 날짜 (한국 시간 기준) ----

/** 오늘 날짜를 KST 기준 YYYY-MM-DD 로 */
export function todayKST(now: Date = new Date()): string {
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  return kst.toISOString().slice(0, 10);
}

function toUTCDate(ymd: string): Date {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function addDays(ymd: string, n: number): string {
  const d = toUTCDate(ymd);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function daysBetween(from: string, to: string): number {
  return Math.round((toUTCDate(to).getTime() - toUTCDate(from).getTime()) / 86400000);
}

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

export function weekday(ymd: string): string {
  return WEEKDAYS[toUTCDate(ymd).getUTCDay()];
}

/** 이번 주 일요일 (오늘이 일요일이면 오늘) */
export function thisSunday(today: string): string {
  const dow = toUTCDate(today).getUTCDay();
  return addDays(today, dow === 0 ? 0 : 7 - dow);
}

/** 이 주의 월요일 */
export function mondayOf(today: string): string {
  const dow = toUTCDate(today).getUTCDay(); // 0=일
  return addDays(today, dow === 0 ? -6 : 1 - dow);
}

/** '2026-11-01' → '11.1(일)', 연도가 오늘과 다르면 '2027.1.3(일)' */
export function shortDate(ymd: string, today: string): string {
  if (!ymd) return "";
  const [y, m, d] = ymd.split("-").map(Number);
  const head = String(y) === today.slice(0, 4) ? `${m}.${d}` : `${y}.${m}.${d}`;
  return `${head}(${weekday(ymd)})`;
}

export function periodText(p: Pick<Popup, "start" | "end">, today: string): string {
  if (!p.start && !p.end) return "기간 미정";
  if (p.start && p.end) return `${shortDate(p.start, today)} ~ ${shortDate(p.end, today)}`;
  return p.start ? `${shortDate(p.start, today)} ~` : `~ ${shortDate(p.end, today)}`;
}

// ---- 상태 ----

export function statusOf(p: Pick<Popup, "start" | "end">, today: string): Status {
  if (!p.start || !p.end) return "undated";
  if (p.end < today) return "ended";
  if (p.start > today) return "upcoming";
  return "ongoing";
}

const STATUS_ORDER: Record<Status, number> = { ongoing: 0, upcoming: 1, undated: 2, ended: 3 };

/** 진행 중 → 예정 → 기간 미정 → 종료. 같은 묶음 안에서는 시작일 순 (종료는 최근 것 먼저) */
export function sortPopups<T extends Pick<Popup, "start" | "end" | "name">>(list: T[], today: string): T[] {
  return [...list].sort((a, b) => {
    const sa = statusOf(a, today);
    const sb = statusOf(b, today);
    if (sa !== sb) return STATUS_ORDER[sa] - STATUS_ORDER[sb];
    if (sa === "ended") return b.end.localeCompare(a.end);
    return a.start.localeCompare(b.start) || a.name.localeCompare(b.name, "ko");
  });
}

export type StateColor = "green" | "blue" | "red" | "gray";
export type StateInfo = { label: string; color: StateColor; rank: number };

/** 앱 _status 와 같은 상태: 종료(회색) · D-n(파랑) · 마감임박(빨강, 끝나는 날까지 3일 이하) · 진행 중(초록) */
export function stateOf(p: Pick<Popup, "start" | "end">, today: string): StateInfo {
  if (!p.start || !p.end) return { label: "기간 미정", color: "gray", rank: 1 };
  if (p.end < today) return { label: "종료", color: "gray", rank: 2 };
  if (p.start > today) return { label: `D-${daysBetween(today, p.start)}`, color: "blue", rank: 1 };
  if (daysBetween(today, p.end) <= 3) return { label: "마감임박", color: "red", rank: 0 };
  return { label: "진행 중", color: "green", rank: 0 };
}

/** 상세 머리글 상태: 종료 · 오늘 종료 · 오픈 예정 D-n · 진행 중 */
export function detailState(p: Pick<Popup, "start" | "end">, today: string): string {
  if (!p.start || !p.end) return "기간 미정";
  if (p.end < today) return "종료";
  if (p.end === today) return "오늘 종료";
  if (p.start > today) return `오픈 예정 D-${daysBetween(today, p.start)}`;
  return "진행 중";
}

// ---- 기간 글자 (앱과 같은 모양) ----

const two = (n: number) => String(n).padStart(2, "0");
function parts(ymd: string) {
  const [y, m, d] = ymd.split("-").map(Number);
  return { y, m, d };
}

function period(p: Pick<Popup, "start" | "end">, f: (s: string) => string): string {
  if (!p.start) return "기간 확인 필요";
  return p.end ? `${f(p.start)} ~ ${f(p.end)}` : `${f(p.start)} ~ 상시`;
}

/** '11.12 ~ 12.03' (앱 홈 카드) */
export const periodDot = (p: Pick<Popup, "start" | "end">) => period(p, (s) => `${two(parts(s).m)}.${two(parts(s).d)}`);
/** '12월 11일 ~ 01월 10일' (앱 리스트 카드, PC) */
export const periodLong = (p: Pick<Popup, "start" | "end">) =>
  period(p, (s) => `${two(parts(s).m)}월 ${two(parts(s).d)}일`);
/** '12/11 ~ 01/10' (앱 리스트 카드, 모바일) */
export const periodSlash = (p: Pick<Popup, "start" | "end">) =>
  period(p, (s) => `${two(parts(s).m)}/${two(parts(s).d)}`);

/** '26.11.12(목)' / '12.03(목)' (앱 상세 일정 _day) */
export function dayLabel(ymd: string, withYear: boolean): string {
  const { y, m, d } = parts(ymd);
  const head = withYear ? `${String(y).slice(2)}.${two(m)}.${two(d)}` : `${two(m)}.${two(d)}`;
  return `${head}(${weekday(ymd)})`;
}

/** 상세 '일정' 줄: '26.11.12(목) - 12.03(목)' (끝 해가 다르면 끝에도 연도) */
export function detailSpan(p: Pick<Popup, "start" | "end">): string {
  if (!p.start) return "기간 확인 필요";
  if (!p.end) return `${dayLabel(p.start, true)} ~ 상시`;
  return `${dayLabel(p.start, true)} - ${dayLabel(p.end, p.end.slice(0, 4) !== p.start.slice(0, 4))}`;
}

// ---- 지역 ----

const PROVINCES: Record<string, string> = {
  서울: "서울",
  서울시: "서울",
  서울특별시: "서울",
  부산: "부산",
  부산시: "부산",
  부산광역시: "부산",
  대구: "대구",
  대구시: "대구",
  대구광역시: "대구",
  인천: "인천",
  인천시: "인천",
  인천광역시: "인천",
  광주: "광주",
  광주시: "광주",
  광주광역시: "광주",
  대전: "대전",
  대전시: "대전",
  대전광역시: "대전",
  울산: "울산",
  울산시: "울산",
  울산광역시: "울산",
  세종: "세종",
  세종시: "세종",
  세종특별자치시: "세종",
  제주: "제주",
  제주도: "제주",
  제주특별자치도: "제주",
  강원: "강원",
  강원도: "강원",
  강원특별자치도: "강원",
  충북: "충북",
  충청북도: "충북",
  충남: "충남",
  충청남도: "충남",
  전북: "전북",
  전라북도: "전북",
  전북특별자치도: "전북",
  전남: "전남",
  전라남도: "전남",
  경북: "경북",
  경상북도: "경북",
  경남: "경남",
  경상남도: "경남",
};

// 주소 첫 단어가 시·도가 아닌 경우(동네·랜드마크 이름)를 대략 맞춘다
const ALIASES: Record<string, string> = {
  성수동: "서울",
  성수: "서울",
  강남역: "서울",
  홍대: "서울",
  합정: "서울",
  잠실: "서울",
  용산: "서울",
  명동: "서울",
  신촌: "서울",
  건대: "서울",
  서면: "부산",
  해운대: "부산",
  판교: "성남",
  분당: "성남",
  라페스타: "고양",
  일산: "고양",
};
// '수원 행궁동' 처럼 시 이름만 먼저 쓴 주소
for (const c of [
  "수원",
  "성남",
  "고양",
  "용인",
  "부천",
  "안산",
  "안양",
  "화성",
  "남양주",
  "평택",
  "의정부",
  "시흥",
  "파주",
  "김포",
  "광명",
  "하남",
  "군포",
  "오산",
  "이천",
  "구리",
  "춘천",
  "강릉",
  "원주",
  "청주",
  "천안",
  "전주",
  "포항",
  "창원",
  "김해",
  "경주",
  "여수",
  "순천",
  "목포",
]) {
  ALIASES[c] = c;
}

/** 주소에서 짧은 시·도 이름: 서울특별시 → 서울, 경기도 수원시 → 수원 */
export function regionOf(address: string): string {
  const tokens = (address || "")
    .replace(/[(),·]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
  if (!tokens.length) return "기타";
  const first = tokens[0];
  if (first === "경기" || first === "경기도") {
    const city = tokens[1] || "";
    const m = city.match(/^(.+?)(시|군)$/);
    if (m) return m[1];
    return ALIASES[city] || "경기";
  }
  if (PROVINCES[first]) return PROVINCES[first];
  if (ALIASES[first]) return ALIASES[first];
  const m = first.match(/^(.+?)시$/);
  if (m && m[1].length >= 2) return m[1];
  return "기타";
}

const SEOUL_GU = [
  "강남",
  "강동",
  "강북",
  "강서",
  "관악",
  "광진",
  "구로",
  "금천",
  "노원",
  "도봉",
  "동대문",
  "동작",
  "마포",
  "서대문",
  "서초",
  "성동",
  "성북",
  "송파",
  "양천",
  "영등포",
  "용산",
  "은평",
  "종로",
  "중랑",
  "중",
];
const METRO = ["부산", "대구", "대전", "울산", "인천", "세종"];
// 시·도 이름 없이 동네로 적은 주소 (앱 geo 사전 중 자주 나오는 것만)
const AREA_ALIAS: Record<string, string> = {
  홍대: "마포",
  합정: "마포",
  연남: "마포",
  망원: "마포",
  상암: "마포",
  성수: "성동",
  왕십리: "성동",
  잠실: "송파",
  건대: "광진",
  신촌: "서대문",
  이대: "서대문",
  여의도: "영등포",
  이태원: "용산",
  명동: "중",
  을지로: "중",
  강남역: "강남",
  코엑스: "강남",
  압구정: "강남",
  신림: "관악",
  목동: "양천",
  서면: "부산",
  해운대: "부산",
  동성로: "대구",
  둔산: "대전",
  송도: "인천",
  부평: "인천",
  청라: "인천",
  판교: "판교",
  분당: "분당",
  일산: "고양",
};
const SEOUL_AREAS = new Set(SEOUL_GU);
const GYEONGGI_OF: Record<string, string> = { 판교: "성남", 분당: "성남" };

/** 카드 왼쪽 위 지역 배지 이름. 앱 common/geo.py area_name 과 같은 결과가 나오게 맞춘 간단한 버전 */
export function areaName(address: string): string {
  const a = (address || "").trim();
  if (!a) return "";
  if (a.startsWith("광주광역시") || /광주\s+(광산|북|남|동|서)구/.test(a) || a.includes("광주통합특별시"))
    return "광주";
  for (const c of METRO) if (a.startsWith(c)) return c;
  if (a.startsWith("서울")) {
    const m = a.match(/(?:^|\s)([가-힣]{1,3})구(?=[\s,]|$)/);
    if (m && SEOUL_AREAS.has(m[1])) return m[1];
    const t = a.split(/[\s,]+/)[1] || "";
    if (SEOUL_AREAS.has(t)) return t;
    for (const [k, v] of Object.entries(AREA_ALIAS)) if (a.includes(k)) return v;
    return "서울";
  }
  if (a.startsWith("경기")) {
    const m = a.match(/([가-힣]{2,})시(?=[\s,]|$)/);
    if (m) return m[1];
    const t = (a.split(/[\s,]+/)[1] || "").replace(/시$/, "");
    if (t) return t;
  }
  for (const [k, v] of Object.entries(AREA_ALIAS)) if (a.includes(k)) return v;
  const gu = a.match(/^([가-힣]{1,3})구(?=\s|$)/);
  if (gu && SEOUL_AREAS.has(gu[1])) return gu[1];
  const m = a.match(/([가-힣]{2,})시(?=\s|$)/);
  if (m && !/(특별|광역|자치)$/.test(m[1])) return m[1];
  const r = regionOf(a);
  return r === "기타" ? "" : r;
}

/** 배지 색을 정할 시 이름: 서울의 구는 모두 '서울', 판교·분당은 성남 */
export function cityName(address: string): string {
  if ((address || "").trim().startsWith("서울")) return "서울";
  const area = areaName(address);
  if (SEOUL_AREAS.has(area)) return "서울";
  return GYEONGGI_OF[area] || area;
}

/** 지역 배지 색 — 앱(app_cafemap.py CITY_COLORS)과 같은 색 */
const CITY_COLORS: Record<string, string> = {
  서울: "#56C2A7",
  부산: "#3B82C4",
  인천: "#8B6CD1",
  대구: "#E0884A",
  대전: "#D9A400",
  광주: "#4CA36A",
  울산: "#2BA3B5",
  제주: "#F2789B",
  세종: "#7F8C3A",
  수원: "#E06C6C",
  고양: "#5A7BD8",
  성남: "#B0639E",
};
const MORE_COLORS = ["#6C9A8B", "#C77D4E", "#7A6FB3", "#4F95A8", "#B5654A", "#5E8F4A", "#A0628B", "#8A7D3E"];

/** 시 색을 어둡게 (물어보기 카드처럼 옅은 민트 바탕 위에서 지역 배지가 묻히지 않게, 11/20 요청). k = 남길 밝기 비율 */
export function darken(hex: string, k = 0.72): string {
  const n = parseInt(hex.slice(1, 7), 16);
  const f = (v: number) => Math.round(v * k).toString(16).padStart(2, "0");
  return `#${f((n >> 16) & 255)}${f((n >> 8) & 255)}${f(n & 255)}`;
}

export function regionColor(city: string): string {
  if (!city || city === "기타") return "#9AA5A1";
  if (CITY_COLORS[city]) return CITY_COLORS[city];
  let sum = 0;
  for (const ch of city) sum += ch.codePointAt(0) ?? 0;
  return MORE_COLORS[sum % MORE_COLORS.length];
}

/** 검색용 소문자 텍스트 (작품·캐릭터·매장·주소·태그) */
export function searchText(p: Popup): string {
  return [p.work, p.characters, p.name, p.address, p.region, p.area, ...p.tags].join(" ").toLowerCase();
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// ---- 그 밖의 앱 규칙 ----

/** 파이썬 sorted() 와 같은 글자 코드 순 비교 (앱과 같은 순서: 영문 대문자 → 한글) */
export function byCode(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** 사전예약 팝업 (앱 _is_reserve 와 같은 낱말. 운영용 note 칸은 공개 데이터에 없어서 태그·굿즈만 본다) */
export function isReserve(p: Pick<Popup, "tags" | "goods">): boolean {
  return /사전\s*예약|예약제|사전\s*예매/.test([...p.tags, ...p.goods].join(" "));
}

/** 앱 _work_key: 작품 이름 비교용 (띄어쓰기·기호·대소문자 무시) */
export function workKey(text: string): string {
  return (text || "").toLowerCase().replace(/[^0-9a-z가-힣ぁ-んァ-ン一-龥]/g, "");
}

/** 카카오맵에서 위치 열기 (앱 _map_link 와 같은 규칙) */
export function mapLink(p: Pick<Popup, "name" | "lat" | "lng" | "address">): string {
  const name = (p.name || "카페").replace(/[,/]/g, " ").trim();
  if (p.lat !== null && p.lng !== null)
    return `https://map.kakao.com/link/map/${encodeURIComponent(name)},${p.lat},${p.lng}`;
  return `https://map.kakao.com/link/search/${encodeURIComponent(p.address || name)}`;
}

/** 브라우저(클라이언트 화면)로 보내는 카드 한 장 분량. 소개·링크 같은 긴 칸은 빼서 HTML 을 가볍게 */
export type Item = {
  id: string;
  name: string;
  work: string;
  area: string;
  city: string;
  address: string;
  lat: number | null;
  lng: number | null;
  start: string;
  end: string;
  poster: string;
  /** 카드에 보이는 첫 칩 (이벤트 태그 → 굿즈 순으로 첫 번째, 12자 넘으면 줄임) */
  chip: string;
  /** 첫 칩이 이벤트 태그면 true (민트로 채운 칩), 굿즈면 false (흰 칩) */
  chipTag: boolean;
  created: string;
  reserve: boolean;
  text: string;
  /** 물어보기(lib/ask.ts)용: 캐릭터 · (특전 · 굿즈 · 이벤트 태그) · 공개 별점 집계 */
  characters: string;
  extra: string;
  /** 특전 칸만 (물어보기 '특전 있는 · 엽서 주는 팝업', 11/24) */
  perks: string;
  rating: { avg: number; n: number } | null;
};

const FLAG_TAGS = new Set(["상시", "기간 확인 필요"]);

export function toItem(p: Popup): Item {
  // 앱 _chips: 카드에는 (태그 2개 + 굿즈 3개) 중 첫 번째 하나만. '상시'·'기간 확인 필요' 표시는 카드에서 뺀다
  const tags = p.tags.filter((t) => !FLAG_TAGS.has(t));
  const chipTag = tags.length > 0;
  const chip = (chipTag ? tags[0] : p.goods[0]) ?? "";
  return {
    id: p.id,
    name: p.name,
    work: p.work,
    area: p.area,
    city: p.city,
    address: p.address,
    lat: p.lat,
    lng: p.lng,
    start: p.start,
    end: p.end,
    poster: p.images[0] ?? "",
    chip: chip.length > 12 ? `${chip.slice(0, 11).trimEnd()}…` : chip,
    chipTag,
    created: p.createdAt,
    reserve: isReserve(p),
    text: searchText(p),
    characters: p.characters,
    extra: [...p.perks, ...p.goods, ...p.tags].join(" "),
    perks: p.perks.join(" "),
    rating: p.rating,
  };
}

/** 띄어쓰기를 무시한 검색 (앱처럼 '스파이 패밀리' = '스파이패밀리') */
export function matchQuery(text: string, q: string): boolean {
  const words = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const flat = text.replace(/\s+/g, "");
  return flat.includes(words.join("")) || words.every((w) => text.includes(w));
}
