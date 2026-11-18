// 닉네임 규칙 (common/nickrule.py 와 같은 목록·같은 비교): 욕설·음란한 말·운영자 사칭은 닉네임으로 쓸 수 없다.
// 띄어쓰기·숫자·특수문자를 끼워 피하는 경우('시1발', 'ㅅ.ㅂ')도 잡도록 한글·영문만 남기고 비교한다.

const ABUSE = [
  "시발",
  "씨발",
  "씨빨",
  "씨팔",
  "시팔",
  "쓰발",
  "ㅅㅂ",
  "ㅆㅂ",
  "ㅅㅃ",
  "ㅆㅃ",
  "병신",
  "븅신",
  "빙신",
  "ㅂㅅ",
  "ㅄ",
  "지랄",
  "ㅈㄹ",
  "좆",
  "존나",
  "졸라",
  "ㅈㄴ",
  "개새끼",
  "개새기",
  "개색기",
  "개색끼",
  "개세끼",
  "개쉐",
  "개같",
  "개년",
  "개놈",
  "ㄱㅅㄲ",
  "미친놈",
  "미친년",
  "미친새",
  "ㅁㅊ",
  "또라이",
  "똘아이",
  "닥쳐",
  "꺼져",
  "엿먹",
  "염병",
  "육시랄",
  "썅",
  "쌍년",
  "쌍놈",
  "썅년",
  "니미",
  "느금",
  "니애미",
  "니애비",
  "애미",
  "애비",
  "에미",
  "앰창",
  "엠창",
  "등신",
  "찐따",
  "틀딱",
  "한남충",
  "김치녀",
  "맘충",
  "급식충",
  "일베",
  "메갈",
  "fuck",
  "fuk",
  "shit",
  "bitch",
  "asshole",
  "bastard",
  "nigger",
  "nigga",
  "retard",
];
const SEXUAL = [
  "섹스",
  "쎅스",
  "섹드립",
  "보지",
  "자지",
  "꼬추",
  "고추먹",
  "딸딸이",
  "자위",
  "야동",
  "포르노",
  "강간",
  "성폭행",
  "윤간",
  "창녀",
  "창년",
  "걸레년",
  "매춘",
  "원조교제",
  "조건만남",
  "빨통",
  "젖꼭지",
  "가슴만지",
  "엉덩이만지",
  "발정",
  "음란",
  "변태",
  "몸캠",
  "노출증",
  "섹시녀",
  "sex",
  "porn",
  "pussy",
  "dick",
  "cock",
  "penis",
  "vagina",
  "boob",
  "nude",
  "hentai",
  "milf",
];
const RESERVED = ["관리자", "운영자", "운영진", "애니웨어", "aniwhere", "admin", "administrator", "운영팀", "고객센터"];

/** 한글(자모 포함)·영문만 남기고 소문자로 (숫자·띄어쓰기·특수문자는 뺀다) */
export function normalize(text: string): string {
  return String(text || "")
    .toLowerCase()
    .replace(/[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ]/g, "")
    .replace(/[0-9]/g, "");
}

/** 쓸 수 없는 말이 있으면 그 종류('욕설'·'음란'·'사칭'), 없으면 '' */
export function problem(nick: string): string {
  const n = normalize(nick);
  if (!n) return "";
  for (const [kind, words] of [
    ["사칭", RESERVED],
    ["음란", SEXUAL],
    ["욕설", ABUSE],
  ] as const) {
    if (words.some((w) => n.includes(w))) return kind;
  }
  return "";
}

/** 중복 확인용: 띄어쓰기·대소문자 차이는 같은 닉네임 */
export function same(a: string, b: string): boolean {
  const key = (s: string) =>
    String(s || "")
      .replace(/\s+/g, "")
      .toLowerCase();
  return !!key(a) && key(a) === key(b);
}
