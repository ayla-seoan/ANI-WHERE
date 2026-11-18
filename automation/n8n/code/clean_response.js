// n8n Code 노드 ①: 구글 폼 응답 한 줄 → results.csv 와 같은 모양의 과업 기록 4줄 (T1~T4)
// 모드: Run Once for All Items. 입력 = 'Google Sheets Trigger'(폼 응답 시트, 새 줄) 의 items
// 개인정보: 이름·연락처는 받지 않는다. 자유 답변에 전화번호·이메일이 있으면 지운다 (common/guard.py 와 같은 생각)

const PHONE = /(01[016789]|0\d{1,2})[-.\s]?\d{3,4}[-.\s]?\d{4}/g;
const EMAIL = /[\w.+-]+@[\w-]+\.[\w.-]+/g;
const mask = (v) => String(v ?? '').replace(PHONE, '[전화번호]').replace(EMAIL, '[이메일]').trim();

const yes = (v) => /^(y|yes|o|성공|예|네)$/i.test(String(v ?? '').trim());
const num = (v) => {
  const n = parseFloat(String(v ?? '').replace(/[^\d.]/g, ''));
  return Number.isFinite(n) ? n : '';
};
// 폼 문항 이름 (survey-form.md 와 같게)
const get = (row, key) => row[key] ?? row[key.replace(/\s/g, '')] ?? '';

const out = [];
for (const item of $input.all()) {
  const r = item.json;
  const who = String(get(r, '참가자 번호')).trim().toUpperCase();          // P1, P2 … (이름 아님)
  if (!/^P\d+$/.test(who)) continue;                                       // 번호가 아니면 버린다 (이름을 적었을 수 있음)
  const ver = String(get(r, '회차')).includes('2') ? '2차' : '1차';
  for (const t of ['T1', 'T2', 'T3', 'T4']) {
    let sec = num(get(r, `${t} 소요초`));
    let ok = yes(get(r, `${t} 성공`));
    if (sec !== '' && sec > 180) ok = false;                               // 3분이 넘으면 실패 (plan.md)
    out.push({ json: {
      참가자: who, 버전: ver, 과업: t, 성공: ok ? 'Y' : 'N', 소요초: sec,
      '막힌 지점': mask(get(r, `${t} 막힌 지점`)),
      메모: t === 'T1' ? mask([get(r, '가장 헷갈렸던 곳'), get(r, '만족도') && `만족도 ${get(r, '만족도')}`,
                               get(r, '다시 쓸 의향') && `다시 쓸 의향 ${get(r, '다시 쓸 의향')}`].filter(Boolean).join(' / ')) : '',
      받은시각: get(r, '타임스탬프') || new Date().toISOString(),
    } });
  }
}
return out;
