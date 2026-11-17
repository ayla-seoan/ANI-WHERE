// 서버·브라우저 양쪽에서 쓰는 순수 함수와 타입. 네트워크·키는 여기 두지 않는다 (lib/data.ts 전용).

export type Status = "ongoing" | "upcoming" | "ended" | "undated";

export type Popup = {
  id: string;
  name: string;
  work: string;
  characters: string;
  address: string;
  region: string;
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
  rating: { avg: number; n: number } | null;
};

export type DataSource = "supabase" | "github" | "none";

export const APP_URL = "https://ani-where.streamlit.app";
export const PLACEHOLDER_POSTER = "/poster-placeholder.svg";

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

// ---- 상태·배지 ----

export function statusOf(p: Pick<Popup, "start" | "end">, today: string): Status {
  if (!p.start || !p.end) return "undated";
  if (p.end < today) return "ended";
  if (p.start > today) return "upcoming";
  return "ongoing";
}

export type Badge = { label: string; tone: "live" | "soon" | "closing" | "ended" | "muted" };

export function badgeOf(p: Pick<Popup, "start" | "end">, today: string): Badge {
  const s = statusOf(p, today);
  if (s === "undated") return { label: "기간 미정", tone: "muted" };
  if (s === "ended") return { label: "종료", tone: "ended" };
  if (s === "upcoming") {
    const d = daysBetween(today, p.start);
    return { label: d === 1 ? "내일 시작" : `D-${d}`, tone: "soon" };
  }
  const left = daysBetween(today, p.end);
  if (left <= 3) return { label: left === 0 ? "오늘 종료" : `종료 임박 D-${left}`, tone: "closing" };
  return { label: "진행 중", tone: "live" };
}

const STATUS_ORDER: Record<Status, number> = { ongoing: 0, upcoming: 1, undated: 2, ended: 3 };

/** 진행 중 → 예정 → 기간 미정 → 종료. 같은 묶음 안에서는 시작일 순 (종료는 최근 것 먼저) */
export function sortPopups(list: Popup[], today: string): Popup[] {
  return [...list].sort((a, b) => {
    const sa = statusOf(a, today);
    const sb = statusOf(b, today);
    if (sa !== sb) return STATUS_ORDER[sa] - STATUS_ORDER[sb];
    if (sa === "ended") return b.end.localeCompare(a.end);
    return a.start.localeCompare(b.start) || a.name.localeCompare(b.name, "ko");
  });
}

// ---- 지역 ----

const PROVINCES: Record<string, string> = {
  서울: "서울", 서울시: "서울", 서울특별시: "서울",
  부산: "부산", 부산시: "부산", 부산광역시: "부산",
  대구: "대구", 대구시: "대구", 대구광역시: "대구",
  인천: "인천", 인천시: "인천", 인천광역시: "인천",
  광주: "광주", 광주시: "광주", 광주광역시: "광주",
  대전: "대전", 대전시: "대전", 대전광역시: "대전",
  울산: "울산", 울산시: "울산", 울산광역시: "울산",
  세종: "세종", 세종시: "세종", 세종특별자치시: "세종",
  제주: "제주", 제주도: "제주", 제주특별자치도: "제주",
  강원: "강원", 강원도: "강원", 강원특별자치도: "강원",
  충북: "충북", 충청북도: "충북", 충남: "충남", 충청남도: "충남",
  전북: "전북", 전라북도: "전북", 전북특별자치도: "전북",
  전남: "전남", 전라남도: "전남", 경북: "경북", 경상북도: "경북",
  경남: "경남", 경상남도: "경남",
};

// 주소 첫 단어가 시·도가 아닌 경우(동네·랜드마크 이름)를 대략 맞춘다
const ALIASES: Record<string, string> = {
  성수동: "서울", 성수: "서울", 강남역: "서울", 홍대: "서울", 합정: "서울", 잠실: "서울",
  용산: "서울", 명동: "서울", 신촌: "서울", 건대: "서울", 서면: "부산", 해운대: "부산",
  판교: "성남", 분당: "성남", 라페스타: "고양", 일산: "고양",
};
// '수원 행궁동' 처럼 시 이름만 먼저 쓴 주소
for (const c of [
  "수원", "성남", "고양", "용인", "부천", "안산", "안양", "화성", "남양주", "평택", "의정부", "시흥", "파주",
  "김포", "광명", "하남", "군포", "오산", "이천", "구리", "춘천", "강릉", "원주", "청주", "천안", "전주",
  "포항", "창원", "김해", "경주", "여수", "순천", "목포",
]) {
  ALIASES[c] = c;
}

/** 주소에서 짧은 지역 이름: 서울특별시 → 서울, 경기도 수원시 → 수원 */
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

/** 검색용 소문자 텍스트 (작품·캐릭터·매장·주소·태그) */
export function searchText(p: Popup): string {
  return [p.work, p.characters, p.name, p.address, p.region, ...p.tags].join(" ").toLowerCase();
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// ---- 앱(Streamlit)과 같은 카드 표기 ----

/** 카드용 짧은 기간 '11/21-12/20' (앱 카드와 같은 모양). 연도가 다르면 '26/12/20' 처럼 앞에 붙인다 */
export function cardPeriod(p: Pick<Popup, "start" | "end">, today: string): string {
  const f = (ymd: string) => {
    if (!ymd) return "";
    const [y, m, d] = ymd.split("-").map(Number);
    return String(y) === today.slice(0, 4) ? `${m}/${d}` : `${String(y).slice(2)}/${m}/${d}`;
  };
  if (!p.start && !p.end) return "기간 미정";
  return `${f(p.start)}-${f(p.end)}`;
}

/** 지역 배지 색 — 앱(app_cafemap.py CITY_COLORS)과 같은 색 */
const CITY_COLORS: Record<string, string> = {
  서울: "#56C2A7", 부산: "#3B82C4", 인천: "#8B6CD1", 대구: "#E0884A", 대전: "#D9A400", 광주: "#4CA36A",
  울산: "#2BA3B5", 제주: "#F2789B", 세종: "#7F8C3A", 수원: "#E06C6C", 고양: "#5A7BD8", 성남: "#B0639E",
};
const MORE_COLORS = ["#6C9A8B", "#C77D4E", "#7A6FB3", "#4F95A8", "#B5654A", "#5E8F4A", "#A0628B", "#8A7D3E"];

export function regionColor(region: string): string {
  if (!region || region === "기타") return "#9AA5A1";
  if (CITY_COLORS[region]) return CITY_COLORS[region];
  let sum = 0;
  for (const ch of region) sum += ch.codePointAt(0) ?? 0;
  return MORE_COLORS[sum % MORE_COLORS.length];
}

/** 카드 오른쪽 위 배지 글자 — 앱처럼 'D-3' / '진행 중' / '오늘 종료' */
export function cardBadge(p: Pick<Popup, "start" | "end">, today: string): string {
  const s = statusOf(p, today);
  if (s === "undated") return "기간 미정";
  if (s === "ended") return "종료";
  if (s === "upcoming") return `D-${daysBetween(today, p.start)}`;
  return daysBetween(today, p.end) === 0 ? "오늘 종료" : "진행 중";
}
