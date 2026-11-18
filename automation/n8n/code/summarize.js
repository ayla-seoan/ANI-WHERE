// n8n Code 노드 ②: '정리' 시트 전체 → 1차 · 2차 비교 숫자 + 메일 본문(규칙으로 만든 요약)
// 모드: Run Once for All Items. 입력 = Google Sheets 'Get Rows' 의 items (참가자·버전·과업·성공·소요초·막힌 지점·메모)
// 숫자는 여기서 센다 (AI 는 문장만 다듬는다 — 앱의 물어보기와 같은 원칙: 건수는 규칙, 설명은 AI)

const rows = $input.all().map((i) => i.json).filter((r) => r.참가자 && r.과업);
const TARGET = { success: 80, t1: 60 };            // PRD 사용자 지표: 과업 성공률 80% 이상, T1 평균 60초 이하

function stat(ver) {
  const rs = rows.filter((r) => r.버전 === ver);
  const people = new Set(rs.map((r) => r.참가자)).size;
  const okRate = rs.length ? Math.round((rs.filter((r) => r.성공 === 'Y').length / rs.length) * 1000) / 10 : null;
  const byTask = {};
  for (const t of ['T1', 'T2', 'T3', 'T4']) {
    const ts = rs.filter((r) => r.과업 === t);
    const secs = ts.filter((r) => r.성공 === 'Y' && r.소요초 !== '' && r.소요초 != null).map((r) => Number(r.소요초));
    byTask[t] = {
      성공률: ts.length ? Math.round((ts.filter((r) => r.성공 === 'Y').length / ts.length) * 1000) / 10 : null,
      평균초: secs.length ? Math.round(secs.reduce((a, b) => a + b, 0) / secs.length) : null,
      명: ts.length,
    };
  }
  const blocks = {};
  for (const r of rs) {
    const b = String(r['막힌 지점'] || '').trim();
    if (b) blocks[b] = (blocks[b] || 0) + 1;
  }
  const top = Object.entries(blocks).sort((a, b) => b[1] - a[1]).slice(0, 3);
  return { 버전: ver, 참가자: people, 과업수: rs.length, 성공률: okRate, 과업별: byTask, 막힌곳: top };
}

const v1 = stat('1차');
const v2 = stat('2차');
const fmt = (v) => (v === null || v === undefined ? '-' : v);
const diff = (a, b, unit) => (a === null || b === null ? '' : ` (${b - a >= 0 ? '+' : ''}${Math.round((b - a) * 10) / 10}${unit})`);
const pass = (v) => (v.성공률 === null ? '아직 없음' : v.성공률 >= TARGET.success ? '목표 달성' : '목표 미달');
const passT1 = (v) => (v.과업별.T1.평균초 === null ? '아직 없음' : v.과업별.T1.평균초 <= TARGET.t1 ? '목표 달성' : '목표 미달');

const lines = [
  `ANI:WHERE 사용자 테스트 요약 (${new Date().toISOString().slice(0, 10)})`,
  '',
  `참가자: 1차 ${v1.참가자}명 · 2차 ${v2.참가자}명`,
  `과업 성공률: 1차 ${fmt(v1.성공률)}% → 2차 ${fmt(v2.성공률)}%${diff(v1.성공률, v2.성공률, '%p')}  [목표 80% 이상: 2차 ${pass(v2)}]`,
  `T1(이번 주말 서울 팝업 찾기) 평균: 1차 ${fmt(v1.과업별.T1.평균초)}초 → 2차 ${fmt(v2.과업별.T1.평균초)}초${diff(v1.과업별.T1.평균초, v2.과업별.T1.평균초, '초')}  [목표 60초 이하: 2차 ${passT1(v2)}]`,
  '',
  '과업별 (성공률 · 성공한 사람 평균 시간)',
  ...['T1', 'T2', 'T3', 'T4'].map((t) =>
    `- ${t}: 1차 ${fmt(v1.과업별[t].성공률)}% · ${fmt(v1.과업별[t].평균초)}초 → 2차 ${fmt(v2.과업별[t].성공률)}% · ${fmt(v2.과업별[t].평균초)}초`),
  '',
  '자주 막힌 곳',
  ...(v2.막힌곳.length ? v2.막힌곳.map(([b, n]) => `- (2차) ${b} — ${n}번`) : ['- (2차) 아직 없음']),
  ...(v1.막힌곳.length ? v1.막힌곳.map(([b, n]) => `- (1차) ${b} — ${n}번`) : []),
];

return [{ json: { 숫자: { 일차: v1, 이차: v2, 목표: TARGET }, 요약: lines.join('\n'), 행수: rows.length } }];
