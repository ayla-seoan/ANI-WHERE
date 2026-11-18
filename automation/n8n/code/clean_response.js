// n8n Code 노드 ①: 구글 폼 응답 한 줄 → '정리' 탭 과제 4줄 (질문 1~4). 응답자 정보(방문 빈도 · 평소 방법 · 불편한 점 ·
// 비교 · 만족도 …)는 '질문 1' 줄에만 적는다 (사람 단위로 셀 때 '질문 1' 줄만 보면 된다)
// 모드: Run Once for All Items. 입력 = 'Google Sheets Trigger'(폼 응답 시트, 새 줄) 의 items. 폼은 automation/n8n/create_form.gs
// 버전: 1차 폼 응답('1차 응답' 탭 → '1차 폼 응답 들어옴' 노드)이면 1차, 아니면 2차
// 개인정보: 이메일 · 이름 · 연락처를 받지 않는다. 자유 답변에 전화번호 · 이메일이 있으면 지운다 (common/guard.py 와 같은 생각)

const PHONE = /(01[016789]|0\d{1,2})[-.\s]?\d{3,4}[-.\s]?\d{4}/g;
const EMAIL = /[\w.+-]+@[\w-]+\.[\w.-]+/g;
const mask = (v) => String(v ?? '').replace(PHONE, '[전화번호]').replace(EMAIL, '[이메일]').trim();
const get = (row, key) => row[key] ?? '';

// 고른 구간 → 초 (구간 가운데 값. '넘게' 는 아래 끝보다 조금 크게)
const TASK_SEC = { '30초 안에': 20, '30초~1분': 45, '1~2분': 90, '2~3분': 150, '3분 넘게': 200 };
const BASE_SEC = { '1분 안에': 45, '1~3분': 120, '3~5분': 240, '5~10분': 450, '10분 넘게': 720 };

let ver = '2차';
try { if (String($prevNode.name).includes('1차')) ver = '1차'; } catch (e) { /* 노드 이름을 못 읽으면 2차 */ }

const out = [];
for (const item of $input.all()) {
  const r = item.json;
  const nick = mask(get(r, '닉네임')).slice(0, 30);
  if (!nick) continue;
  ['질문 1', '질문 2', '질문 3', '질문 4'].forEach((t, i) => {
    const first = i === 0;
    out.push({ json: {
      닉네임: nick, 버전: ver, 과제: t, 결과: get(r, `${t} 결과`),
      걸린시간초: TASK_SEC[get(r, `${t} 걸린 시간`)] ?? '',
      '막힌 지점': mask(get(r, `${t} 막힌 곳`)),
      방문빈도: first ? get(r, '방문 빈도') : '',
      정보출처: first ? mask(get(r, '정보 출처')) : '',
      불편한점: first ? mask(get(r, '불편한 점')) : '',
      평소걸린시간초: first ? (BASE_SEC[get(r, '평소 걸린 시간')] ?? '') : '',
      비교: first ? get(r, '비교') : '',
      만족도: first ? get(r, '만족도') : '',
      다시쓸의향: first ? get(r, '다시 쓸 의향') : '',
      바라는점: first ? mask(get(r, '바라는 점')) : '',
      받은시각: get(r, '타임스탬프') || new Date().toISOString(),
    } });
  });
}
return out;
