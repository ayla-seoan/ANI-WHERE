// 민감정보 막기 — common/guard.py PATTERNS 를 옮긴 것 (서버·브라우저 같이 쓴다).
// 순서가 중요하다: 겹치면 먼저 잡힌 쪽 이름이 남으므로 긴 형식(주민번호·카드번호)을 앞에 둔다.
// 파이썬의 \w 는 한글까지 포함해서, 이메일 패턴은 유니코드 글자(\p{L}\p{N})로 맞춘다.

export const PATTERNS: [string, RegExp][] = [
  ["주민등록번호", /(?<!\d)\d{6}[-\s]?[1-4]\d{6}(?!\d)/g],
  ["카드번호", /\b(?:\d{4}[-\s]?){3}\d{4}\b/g],
  ["전화번호", /01[016-9][-.\s]?\d{3,4}[-.\s]?\d{4}/g],
  ["유선전화번호", /(?<!\d)0(?:2|[3-6][1-5]|50[2-8]|70|80)[-.\s]\d{3,4}[-.\s]\d{4}(?!\d)/g],
  ["이메일", /[\p{L}\p{N}_.+-]+@[\p{L}\p{N}_-]+\.[\p{L}\p{N}_.]+/gu],
  ["계좌번호", /(?<![\d-])(?=(?:\d-?){10,14}(?![\d-]))\d{2,6}-\d{2,6}-\d{2,7}(?:-\d{1,3})?(?![\d-])/g],
];

export type Finding = { kind: string; text: string };

/** 민감정보로 의심되는 부분을 모두 찾는다 (guard.scan) */
export function scan(text: string): Finding[] {
  const found: Finding[] = [];
  const taken: [number, number][] = [];
  for (const [kind, re] of PATTERNS) {
    re.lastIndex = 0;
    for (const m of (text || "").matchAll(re)) {
      const s = m.index ?? 0;
      const e = s + m[0].length;
      if (taken.some(([a, b]) => s < b && a < e)) continue;
      taken.push([s, e]);
      found.push({ kind, text: m[0] });
    }
  }
  return found;
}

/** 민감정보를 ● 로 가린다 (guard.mask) */
export function mask(text: string): string {
  let out = text || "";
  for (const [, re] of PATTERNS) out = out.replace(re, (m) => "●".repeat([...m].length));
  return out;
}

/** 리뷰 입력칸 아래 경고 (앱 _block_sensitive 와 같은 문구) */
export function sensitiveWarning(text: string): string {
  const kinds = [...new Set(scan(text).map((f) => f.kind))].sort();
  return kinds.length
    ? `민감한 개인정보(${kinds.join(", ")})는 입력할 수 없습니다. 해당 내용을 지우고 다시 입력해 주세요.`
    : "";
}
