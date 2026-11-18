// n8n Code 노드 ②: '정리' 탭 전체 → A(평소 방법) · B(ANI:WHERE) 비교 숫자 + 메일 본문(규칙으로 만든 요약)
// 모드: Run Once for All Items. 입력 = Google Sheets 'Get Rows' 의 items
// 숫자는 여기서 센다 (AI 는 문장만 다듬는다). 같은 규칙: common/stats.py survey_summary (관리자 '사용자 테스트' 탭)

const rows = $input.all().map((i) => i.json).filter((r) => r.닉네임 && r.과제);
const people = rows.filter((r) => r.과제 === '질문 1');
const TASKS = ['질문 1', '질문 2', '질문 3', '질문 4'];
const ok = (r) => r.결과 === '해냈어요' || r.결과 === '어렵게 해냈어요';
const avg = (xs) => (xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : null);
const nums = (xs) => xs.map(Number).filter((x) => Number.isFinite(x) && x > 0);
const pct = (a, b) => (b ? Math.round((a / b) * 1000) / 10 : null);

const taskStats = TASKS.map((t) => {
  const ts = rows.filter((r) => r.과제 === t);
  return { 과제: t, 성공률: pct(ts.filter(ok).length, ts.length), 평균초: avg(nums(ts.filter(ok).map((r) => r.걸린시간초))), 명: ts.length };
});
const allOk = pct(rows.filter(ok).length, rows.length);
const baseSec = avg(nums(people.map((r) => r.평소걸린시간초)));
const q1Sec = taskStats[0].평균초;
const sat = avg(nums(people.map((r) => r.만족도)).map((x) => x * 10));
const cmp = avg(nums(people.map((r) => r.비교)).map((x) => x * 10));
const again = pct(people.filter((r) => r.다시쓸의향 === '있어요').length, people.length);
const count = (key) => {
  const c = {};
  people.forEach((r) => String(r[key] || '').split(',').map((x) => x.trim()).filter(Boolean).forEach((x) => { c[x] = (c[x] || 0) + 1; }));
  return Object.entries(c).sort((a, b) => b[1] - a[1]);
};
const pains = count('불편한점').slice(0, 3);
const blocks = {};
rows.forEach((r) => { const b = String(r['막힌 지점'] || '').trim(); if (b) blocks[`${r.과제} · ${b}`] = (blocks[`${r.과제} · ${b}`] || 0) + 1; });
const fmt = (v, u) => (v === null || v === undefined ? '-' : `${v}${u}`);

const lines = [
  `ANI:WHERE 사용해 보기 설문 요약 (${new Date().toISOString().slice(0, 10)})`,
  '',
  `응답자 ${people.length}명`,
  `A/B — "이번 주말 서울 팝업 하나 찾기": 평소 방법 ${fmt(baseSec, '초')} → ANI:WHERE ${fmt(q1Sec, '초')}`,
  `과제 성공률(4개 평균): ${fmt(allOk, '%')}  [목표 80% 이상: ${allOk === null ? '아직 없음' : allOk >= 80 ? '달성' : '미달'}]`,
  `질문 1 평균 시간: ${fmt(q1Sec, '초')}  [목표 60초 이하: ${q1Sec === null ? '아직 없음' : q1Sec <= 60 ? '달성' : '미달'}]`,
  `평소 방법보다 편했다(5점): ${cmp === null ? '-' : (cmp / 10).toFixed(1)} · 만족도(5점): ${sat === null ? '-' : (sat / 10).toFixed(1)} · 다시 쓸 의향: ${fmt(again, '%')}`,
  '',
  '과제별 (성공률 · 성공한 사람 평균 시간)',
  ...taskStats.map((t) => `- ${t.과제}: ${fmt(t.성공률, '%')} · ${fmt(t.평균초, '초')} (${t.명}명)`),
  '',
  '평소 가장 불편한 점 (문제 정의)',
  ...(pains.length ? pains.map(([p, n]) => `- ${p} — ${n}명`) : ['- 아직 없음']),
  '',
  '자주 막힌 곳',
  ...(Object.keys(blocks).length ? Object.entries(blocks).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([b, n]) => `- ${b} — ${n}번`) : ['- 아직 없음']),
];

return [{ json: { 숫자: { 응답자: people.length, 과제별: taskStats, 성공률: allOk, 평소초: baseSec, 질문1초: q1Sec, 다시쓸의향: again, 불편한점: pains },
                  요약: lines.join('\n'), 행수: rows.length } }];
