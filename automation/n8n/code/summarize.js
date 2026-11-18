// n8n Code 노드 ②: '정리' 탭 전체 → 버전(1차 · 2차)별 A(평소 방법) · B(ANI:WHERE) 비교 숫자 + 메일 본문(규칙으로 만든 요약)
// 모드: Run Once for All Items. 입력 = Google Sheets 'Get Rows' 의 items
// 숫자는 여기서 센다 (AI 는 문장만 다듬는다). 같은 규칙: common/stats.py survey_summary (관리자 '사용자 테스트' 탭)

const all = $input.all().map((i) => i.json).filter((r) => r.닉네임 && r.과제);
const TASKS = ['질문 1', '질문 2', '질문 3', '질문 4'];
const ok = (r) => r.결과 === '해냈어요' || r.결과 === '어렵게 해냈어요';
const avg = (xs) => (xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : null);
const nums = (xs) => xs.map(Number).filter((x) => Number.isFinite(x) && x > 0);
const pct = (a, b) => (b ? Math.round((a / b) * 1000) / 10 : null);
const fmt = (v, u) => (v === null || v === undefined ? '-' : `${v}${u}`);

function summarize(rows) {
  const people = rows.filter((r) => r.과제 === '질문 1');
  const taskStats = TASKS.map((t) => {
    const ts = rows.filter((r) => r.과제 === t);
    return { 과제: t, 성공률: pct(ts.filter(ok).length, ts.length), 평균초: avg(nums(ts.filter(ok).map((r) => r.걸린시간초))), 명: ts.length };
  });
  const count = (key) => {
    const c = {};
    people.forEach((r) => String(r[key] || '').split(',').map((x) => x.trim()).filter(Boolean).forEach((x) => { c[x] = (c[x] || 0) + 1; }));
    return Object.entries(c).sort((a, b) => b[1] - a[1]);
  };
  const blocks = {};
  rows.forEach((r) => { const b = String(r['막힌 지점'] || '').trim(); if (b) blocks[`${r.과제} · ${b}`] = (blocks[`${r.과제} · ${b}`] || 0) + 1; });
  const sat = avg(nums(people.map((r) => r.만족도)).map((x) => x * 10));
  const cmp = avg(nums(people.map((r) => r.비교)).map((x) => x * 10));
  return {
    응답자: people.length, 과제별: taskStats, 성공률: pct(rows.filter(ok).length, rows.length),
    평소초: avg(nums(people.map((r) => r.평소걸린시간초))), 질문1초: taskStats[0].평균초,
    비교: cmp === null ? null : cmp / 10, 만족도: sat === null ? null : sat / 10,
    다시쓸의향: pct(people.filter((r) => r.다시쓸의향 === '있어요').length, people.length),
    불편한점: count('불편한점').slice(0, 3),
    막힌곳: Object.entries(blocks).sort((a, b) => b[1] - a[1]).slice(0, 3),
  };
}

const ver = (r) => (String(r.버전 || '').trim() === '1차' ? '1차' : '2차');   // 버전 칸이 없던 응답은 2차
const s = { '1차': summarize(all.filter((r) => ver(r) === '1차')), '2차': summarize(all.filter((r) => ver(r) === '2차')) };

const lines = [`ANI:WHERE 사용해 보기 설문 요약 (${new Date().toISOString().slice(0, 10)})`, ''];
for (const v of ['1차', '2차']) {
  const x = s[v];
  lines.push(`■ ${v} — 응답자 ${x.응답자}명`);
  if (!x.응답자) { lines.push('- 아직 응답 없음', ''); continue; }
  lines.push(
    `A/B — "이번 주말 서울 팝업 하나 찾기": 평소 방법 ${fmt(x.평소초, '초')} → ANI:WHERE ${fmt(x.질문1초, '초')}`,
    `과제 성공률(4개 평균): ${fmt(x.성공률, '%')}  [목표 80% 이상: ${x.성공률 === null ? '아직 없음' : x.성공률 >= 80 ? '달성' : '미달'}]`,
    `질문 1 평균 시간: ${fmt(x.질문1초, '초')}  [목표 60초 이하: ${x.질문1초 === null ? '아직 없음' : x.질문1초 <= 60 ? '달성' : '미달'}]`,
    `평소 방법보다 편했다(5점): ${x.비교 === null ? '-' : x.비교.toFixed(1)} · 만족도(5점): ${x.만족도 === null ? '-' : x.만족도.toFixed(1)} · 다시 쓸 의향: ${fmt(x.다시쓸의향, '%')}`,
    '과제별 (성공률 · 성공한 사람 평균 시간)',
    ...x.과제별.map((t) => `- ${t.과제}: ${fmt(t.성공률, '%')} · ${fmt(t.평균초, '초')} (${t.명}명)`),
    '평소 가장 불편한 점: ' + (x.불편한점.length ? x.불편한점.map(([p, n]) => `${p}(${n})`).join(', ') : '없음'),
    '자주 막힌 곳: ' + (x.막힌곳.length ? x.막힌곳.map(([b, n]) => `${b}(${n})`).join(', ') : '없음'),
    '',
  );
}
const a = s['1차'], b = s['2차'];
if (a.응답자 && b.응답자) {
  lines.push('■ 1차 → 2차',
    `과제 성공률 ${fmt(a.성공률, '%')} → ${fmt(b.성공률, '%')} · 질문 1 평균 ${fmt(a.질문1초, '초')} → ${fmt(b.질문1초, '초')}` +
    ` · 만족도 ${a.만족도 === null ? '-' : a.만족도.toFixed(1)} → ${b.만족도 === null ? '-' : b.만족도.toFixed(1)}`);
}

return [{ json: { 숫자: s, 요약: lines.join('\n'), 행수: all.length } }];
