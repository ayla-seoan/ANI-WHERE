import "server-only";
import { mask } from "@/lib/guard";

// 주소 → 지도 좌표 (common/geo.py 를 옮긴 것). 차례로:
//  1) KAKAO_REST_API_KEY 가 있으면 카카오 로컬 API
//  2) NAVER_MAPS_CLIENT_ID/SECRET 가 있으면 네이버 클라우드 지오코딩
//  3) 키가 없거나 못 찾으면 아래 표에서 지역 이름을 찾아 그 동네 중심 좌표 ('대략 위치')
// 키는 서버 환경변수에만 (NEXT_PUBLIC_ 아님). 외부로 보내는 글은 guard.mask 를 거친다.

export const GAZETTEER: Record<string, [number, number]> = {
  // 서울
  강남: [37.5172, 127.0473], 서초: [37.4837, 127.0324], 송파: [37.5145, 127.1059],
  잠실: [37.5133, 127.1], 마포: [37.5663, 126.9019], 홍대: [37.5563, 126.9236],
  합정: [37.5497, 126.9136], 연남: [37.5637, 126.9256], 성동: [37.5634, 127.0369],
  성수: [37.5447, 127.0557], 광진: [37.5385, 127.0823], 건대: [37.5403, 127.0695],
  종로: [37.573, 126.9794], 명동: [37.5636, 126.985], 을지로: [37.566, 126.991],
  용산: [37.5324, 126.99], 이태원: [37.5345, 126.9946], 영등포: [37.5264, 126.8963],
  여의도: [37.5219, 126.9245], 강서: [37.5509, 126.8495], 관악: [37.4784, 126.9516],
  신촌: [37.5551, 126.9368], 이대: [37.5569, 126.9459], 동대문: [37.5744, 127.0396],
  노원: [37.6542, 127.0568], 은평: [37.6027, 126.9291], 구로: [37.4954, 126.8874],
  금천: [37.4569, 126.8956], 강동: [37.5301, 127.1238], 중랑: [37.6066, 127.0927],
  서대문: [37.5791, 126.9368], 양천: [37.517, 126.8665], 도봉: [37.6688, 127.0471],
  강북: [37.6396, 127.0257], 성북: [37.5894, 127.0167], 동작: [37.5124, 126.9393],
  // 경기 · 인천
  수원: [37.2636, 127.0286], 성남: [37.42, 127.1267], 분당: [37.3595, 127.1052],
  판교: [37.3948, 127.1112], 용인: [37.2411, 127.1776], 고양: [37.6584, 126.832],
  일산: [37.6584, 126.77], 부천: [37.5035, 126.766], 안양: [37.3943, 126.9568],
  송도: [37.3826, 126.6569], 의정부: [37.7381, 127.0337],
  // 그 밖의 도시
  서면: [35.1578, 129.0595], 해운대: [35.1631, 129.1635],
  동성로: [35.869, 128.595], 둔산: [36.352, 127.378],
  창원: [35.228, 128.6811], 전주: [35.8242, 127.148],
  천안: [36.8151, 127.1139], 청주: [36.6424, 127.489],
  // 서울 나머지 동네
  광화문: [37.5759, 126.9768], 압구정: [37.5271, 127.0286],
  신사: [37.5163, 127.0203], 가로수길: [37.5207, 127.023], 삼성: [37.5089, 127.0631],
  코엑스: [37.5116, 127.0595], 왕십리: [37.5612, 127.0371], 신림: [37.4842, 126.9297],
  목동: [37.5268, 126.8751], 상암: [37.5794, 126.8895], 망원: [37.556, 126.9101],
  // 경기 · 인천 나머지
  하남: [37.5393, 127.2149], 스타필드: [37.5452, 127.224], 김포: [37.6153, 126.7156],
  파주: [37.76, 126.7802], 광명: [37.4786, 126.8646], 시흥: [37.38, 126.8029],
  안산: [37.3219, 126.8309], 화성: [37.1995, 126.8312], 동탄: [37.2006, 127.0745],
  평택: [36.9921, 127.1129], 오산: [37.1498, 127.0773], 군포: [37.3616, 126.9352],
  의왕: [37.3448, 126.9683], 과천: [37.4292, 126.9876], 구리: [37.5943, 127.1296],
  남양주: [37.636, 127.2165], 광주시: [37.4295, 127.255], 이천: [37.272, 127.435],
  여주: [37.2984, 127.6374], 양주: [37.7853, 127.0458], 포천: [37.8949, 127.2003],
  동두천: [37.9036, 127.0606], 가평: [37.8315, 127.5105], 양평: [37.4917, 127.4875],
  안성: [37.008, 127.2797], 광교: [37.285, 127.0446], 부평: [37.507, 126.7219],
  청라: [37.5326, 126.645], 영종: [37.4925, 126.493],
  // 강원 · 충청 · 전라 · 경상
  춘천: [37.8813, 127.7298], 원주: [37.3422, 127.9202], 강릉: [37.7519, 128.8761],
  속초: [38.207, 128.5918], 세종: [36.48, 127.289], 아산: [36.7898, 127.0018],
  공주: [36.4465, 127.119], 충주: [36.991, 127.9259], 군산: [35.9677, 126.7366],
  익산: [35.9483, 126.9577], 목포: [34.8118, 126.3922], 여수: [34.7604, 127.6622],
  순천: [34.9506, 127.4872], 포항: [36.019, 129.3435], 경주: [35.8562, 129.2247],
  구미: [36.1195, 128.3446], 안동: [36.5684, 128.7294], 김해: [35.2285, 128.8894],
  진주: [35.18, 128.1076], 양산: [35.335, 129.0371], 거제: [34.8806, 128.6211],
  서귀포: [33.2541, 126.56], 세종대로: [37.5704, 126.9769],
};

const PROVINCES: Record<string, [number, number]> = {
  서울: [37.5665, 126.978], 인천: [37.4563, 126.7052], 부산: [35.1796, 129.0756],
  대구: [35.8714, 128.6014], 대전: [36.3504, 127.3845], 광주: [35.1595, 126.8526],
  울산: [35.5384, 129.3114], 제주: [33.4996, 126.5312],
  서울특별시: [37.5665, 126.978], 경기도: [37.2752, 127.0095], 경기: [37.2752, 127.0095],
  인천광역시: [37.4563, 126.7052], 강원: [37.8854, 127.7298], 충청북도: [36.6357, 127.4917],
  충북: [36.6357, 127.4917], 충청남도: [36.6588, 126.6728], 충남: [36.6588, 126.6728],
  전라북도: [35.8203, 127.1088], 전북: [35.8203, 127.1088], 전라남도: [34.8161, 126.463],
  전남: [34.8161, 126.463], 경상북도: [36.576, 128.5056], 경북: [36.576, 128.5056],
  경상남도: [35.2383, 128.6925], 경남: [35.2383, 128.6925],
};

/** 동네·역 이름 → '시도 구/시' (geo.DISTRICT_OF). 간편등록이 지역만 채우거나 구 없는 주소에 구를 붙일 때 */
export const DISTRICT_OF: Record<string, string> = {
  홍대: "서울 마포구", 합정: "서울 마포구", 연남: "서울 마포구", 망원: "서울 마포구", 상암: "서울 마포구",
  신촌: "서울 서대문구", 이대: "서울 서대문구", 성수: "서울 성동구", 왕십리: "서울 성동구",
  건대입구: "서울 광진구", 건대: "서울 광진구", 잠실: "서울 송파구", 용산: "서울 용산구",
  이태원: "서울 용산구", 강남: "서울 강남구", 압구정: "서울 강남구", 삼성: "서울 강남구",
  코엑스: "서울 강남구", 신사: "서울 강남구", 가로수길: "서울 강남구", 여의도: "서울 영등포구",
  명동: "서울 중구", 을지로: "서울 중구", 종로: "서울 종로구", 광화문: "서울 종로구",
  신림: "서울 관악구", 목동: "서울 양천구",
  서면: "부산 부산진구", 해운대: "부산 해운대구", 동성로: "대구 중구", 둔산: "대전 서구",
  송도: "인천 연수구", 부평: "인천 부평구", 일산: "경기 고양시", 킨텍스: "경기 고양시",
  수원: "경기 수원시", 광교: "경기 수원시", 판교: "경기 성남시", 분당: "경기 성남시",
  동탄: "경기 화성시", 스타필드: "경기 하남시",
};

export type GeoResult = {
  ok: boolean;
  lat: number | null;
  lng: number | null;
  precision: "exact" | "approx" | "none";
  matched: string;
  note: string;
};
export const badgeOf = (g: Pick<GeoResult, "precision">) =>
  ({ exact: "정확한 주소", approx: "대략 위치", none: "좌표 없음" })[g.precision];

export type Candidate = { name: string; address: string; lat: number; lng: number; source: string; precision?: string };
export type SearchResult = { ok: boolean; candidates: Candidate[]; note: string };

const kakaoKey = () => (process.env.KAKAO_REST_API_KEY || "").trim() || null;
const naverMaps = () => {
  const id = process.env.NAVER_MAPS_CLIENT_ID;
  const sec = process.env.NAVER_MAPS_CLIENT_SECRET;
  return id && sec ? ([id, sec] as const) : null;
};
const naverSearch = () => {
  const id = process.env.NAVER_SEARCH_CLIENT_ID;
  const sec = process.env.NAVER_SEARCH_CLIENT_SECRET;
  return id && sec ? ([id, sec] as const) : null;
};

const fail = (note: string): GeoResult => ({ ok: false, lat: null, lng: null, precision: "none", matched: "", note });

async function getJson(url: string, headers: Record<string, string>): Promise<Record<string, unknown>> {
  const res = await fetch(url, { headers, cache: "no-store", signal: AbortSignal.timeout(5000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as Record<string, unknown>;
}

type Doc = Record<string, unknown> & { x?: string; y?: string };

async function kakao(address: string, key: string): Promise<GeoResult> {
  const q = mask(address);
  const h = { Authorization: `KakaoAK ${key}` };
  try {
    let docs = ((await getJson(`https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(q)}`, h))
      .documents || []) as Doc[];
    if (!docs.length) {
      // 주소로 못 찾으면 장소 이름으로 다시 ("OO역", 가게 이름)
      docs = ((await getJson(`https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(q)}&size=1`, h))
        .documents || []) as Doc[];
    }
    if (docs.length) {
      return {
        ok: true,
        lat: Number(docs[0].y),
        lng: Number(docs[0].x),
        precision: "exact",
        matched: String(docs[0].address_name || q),
        note: "",
      };
    }
  } catch (e) {
    return fail(`카카오 API 호출 실패: ${e instanceof Error ? e.message : e}`);
  }
  return fail("카카오에서 주소를 찾지 못했습니다.");
}

function fromGazetteer(address: string): GeoResult {
  for (const table of [GAZETTEER, PROVINCES]) {
    const name = Object.keys(table)
      .sort((a, b) => b.length - a.length)
      .find((n) => address.includes(n));
    if (name) {
      const [lat, lng] = table[name];
      return { ok: true, lat, lng, precision: "approx", matched: name, note: `'${name}' 지역 중심 좌표로 표시합니다. 정확한 위치가 아닙니다.` };
    }
  }
  return fail("아는 지역 이름이 없어 지도에 올릴 수 없습니다. 시/구 이름을 넣어 주세요.");
}

/** 주소 문자열 → 좌표 (geo.geocode). 실패해도 예외를 던지지 않는다 */
export async function geocode(address: string): Promise<GeoResult> {
  const a = (address || "").trim();
  if (!a) return fail("주소가 비어 있습니다.");
  const key = kakaoKey();
  if (key) {
    const r = await kakao(a, key);
    if (r.ok) return r;
  }
  if (naverMaps()) {
    const found = await naverGeocode(a);
    if (found.ok && found.candidates.length) {
      const c = found.candidates[0];
      return { ok: true, lat: c.lat, lng: c.lng, precision: "exact", matched: c.address, note: "" };
    }
  }
  return fromGazetteer(a);
}

export const searchAvailable = () => !!(kakaoKey() || naverMaps() || naverSearch());

/** 주소나 가게 이름으로 후보 찾기 (geo.search). 키가 없거나 실패해도 예외를 던지지 않는다 */
export async function search(query: string): Promise<SearchResult> {
  let q = (query || "").trim();
  if (!q) return { ok: false, candidates: [], note: "검색어를 입력해 주세요." };
  if (!searchAvailable())
    return {
      ok: false,
      candidates: [],
      note: "카카오 API 키가 없어 주소 검색을 쓸 수 없습니다. .env 에 KAKAO_REST_API_KEY 를 넣어 주세요.",
    };
  q = mask(q);
  const callers: [boolean, (q: string) => Promise<SearchResult>][] = kakaoKey()
    ? [[true, kakaoSearch]]
    : [
        [!!naverMaps(), naverGeocode],
        [!!naverSearch(), naverLocal],
      ];
  const found: Candidate[] = [];
  const errors: string[] = [];
  for (const [on, call] of callers) {
    if (!on) continue;
    const r = await call(q);
    for (const c of r.candidates) if (!found.some((f) => f.address === c.address)) found.push(c);
    if (!r.ok && r.note) errors.push(r.note);
  }
  if (found.length) return { ok: true, candidates: found, note: "" };
  return { ok: false, candidates: [], note: errors.join(" / ") || "검색 결과가 없습니다. 다른 이름이나 주소로 찾아 보세요." };
}

async function kakaoSearch(query: string): Promise<SearchResult> {
  const h = { Authorization: `KakaoAK ${kakaoKey()}` };
  const out: Candidate[] = [];
  try {
    const a = ((await getJson(`https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(query)}&size=5`, h))
      .documents || []) as Doc[];
    for (const d of a) {
      const road = (d.road_address || {}) as Record<string, string>;
      out.push({
        name: road.building_name || "",
        address: road.address_name || String(d.address_name || ""),
        lat: Number(d.y),
        lng: Number(d.x),
        source: "카카오맵",
      });
    }
    const k = ((await getJson(`https://dapi.kakao.com/v2/local/search/keyword.json?query=${encodeURIComponent(query)}&size=5`, h))
      .documents || []) as Doc[];
    for (const d of k)
      out.push({
        name: String(d.place_name || ""),
        address: String(d.road_address_name || d.address_name || ""),
        lat: Number(d.y),
        lng: Number(d.x),
        source: "카카오맵",
      });
  } catch (e) {
    return { ok: out.length > 0, candidates: out, note: `카카오 검색 호출 실패: ${e instanceof Error ? e.message : e}` };
  }
  return { ok: true, candidates: out, note: "" };
}

async function naverGeocode(query: string): Promise<SearchResult> {
  const keys = naverMaps();
  if (!keys) return { ok: false, candidates: [], note: "" };
  const host = process.env.NAVER_MAPS_API_HOST || "https://naveropenapi.apigw.gov-ntruss.com";
  try {
    const j = await getJson(`${host}/map-geocode/v2/geocode?query=${encodeURIComponent(query)}&count=5`, {
      "x-ncp-apigw-api-key-id": keys[0],
      "x-ncp-apigw-api-key": keys[1],
      Accept: "application/json",
    });
    const items = (j.addresses || []) as Record<string, string>[];
    return {
      ok: true,
      note: "",
      candidates: items
        .filter((a) => a.x && a.y)
        .map((a) => ({ name: "", address: a.roadAddress || a.jibunAddress || "", lat: Number(a.y), lng: Number(a.x), source: "네이버 지도" })),
    };
  } catch (e) {
    return { ok: false, candidates: [], note: `네이버 지오코딩 호출 실패: ${e instanceof Error ? e.message : e}` };
  }
}

async function naverLocal(query: string): Promise<SearchResult> {
  const keys = naverSearch();
  if (!keys) return { ok: false, candidates: [], note: "" };
  try {
    const j = await getJson(`https://openapi.naver.com/v1/search/local.json?query=${encodeURIComponent(query)}&display=5`, {
      "X-Naver-Client-Id": keys[0],
      "X-Naver-Client-Secret": keys[1],
    });
    const out: Candidate[] = [];
    for (const it of (j.items || []) as Record<string, string>[]) {
      const lng = parseInt(it.mapx, 10) / 1e7;
      const lat = parseInt(it.mapy, 10) / 1e7;
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
      out.push({ name: (it.title || "").replace(/<[^>]+>/g, ""), address: it.roadAddress || it.address || "", lat, lng, source: "네이버 지역 검색" });
    }
    return { ok: true, candidates: out, note: "" };
  } catch (e) {
    return { ok: false, candidates: [], note: `네이버 지역 검색 호출 실패: ${e instanceof Error ? e.message : e}` };
  }
}

/** 주소 검색·우편번호에서 고른 주소를 그대로 두었으면 그 좌표를, 손으로 고쳤으면 다시 찾은 좌표 (앱 locate) */
export async function locate(
  address: string,
  picked: { address: string; lat: number; lng: number; source: string; precision?: string } | null,
): Promise<GeoResult> {
  const precision = (picked?.precision || "exact") as GeoResult["precision"];
  if (picked && picked.address === address.trim() && precision !== "none" && Number.isFinite(picked.lat) && Number.isFinite(picked.lng))
    return { ok: true, lat: picked.lat, lng: picked.lng, precision, matched: `${picked.source}: ${picked.address}`, note: "" };
  return geocode(address);
}

/** 우편번호 서비스에서 고른 주소 → 후보 (앱 _postcode_field: 좌표는 고른 주소로 다시 찾는다) */
export async function postcodePick(address: string, jibun: string): Promise<Candidate> {
  const a = (address || "").trim();
  let g = await geocode(a);
  if (!g.ok && jibun) g = await geocode(jibun);
  return { name: "", address: a, lat: g.lat ?? 0, lng: g.lng ?? 0, source: "카카오 우편번호", precision: g.ok ? g.precision : "none" };
}
