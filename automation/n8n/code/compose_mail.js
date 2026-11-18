// n8n Code 노드 ③: 메일 제목·본문. AI 에이전트가 실패해도(키 없음·오류) 규칙으로 센 요약은 늘 보낸다
// 결과에 'AI 산출' 인지 '규칙 기반 대체' 인지 표시한다 (CLAUDE.md 예외 처리 원칙과 같게)

const base = $('1차·2차 숫자 세기').item.json;
const ai = String(($json && ($json.output || $json.text)) || '').trim();
const ok = ai.length > 0 && !$json.error;
const date = new Date().toISOString().slice(0, 10);
const 본문 = [
  base.요약,
  '',
  '────────',
  ok ? `[AI 산출] 해석 · 다음에 고칠 것\n${ai}` : '[규칙 기반 대체] AI 요약을 만들지 못해 숫자만 보냅니다.',
  '',
  `(정리 시트 ${base.행수}줄 기준 · 1차·2차는 닉네임으로만 묶음 · 이름·연락처·이메일은 받지 않음)`,
].join('\n');
return [{ json: { 제목: `[ANI:WHERE] 사용해 보기 설문 요약 ${date}`, 본문 } }];
