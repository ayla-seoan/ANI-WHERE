# 자동화: 사용자 테스트 설문 (n8n)

1차(11/25)·2차(11/30) 사용자 테스트 기록을 **구글 폼 → n8n → 구글 시트 → AI 에이전트 요약 → 메일** 로 자동 정리한다.
2차 PO 지표(과업 성공률 80% 이상, T1 평균 60초 이하)의 **1차 → 2차 비교**가 매일 저녁 메일로 온다.

```
구글 폼 (진행자가 참가자마다 1번 제출)
  → 폼 응답 시트 (새 줄)
  → n8n ① 응답 정리: 과업 4줄(T1~T4)로 나누고 이름·연락처 지우기 → '정리' 탭에 쌓기
  → n8n ② 매일 21:00 (또는 '지금 실행'): '정리' 탭 읽기 → 1차·2차 숫자 세기(규칙)
       → GitHub 에서 프롬프트 읽기 → AI 에이전트(gpt-4o-mini)가 해석·다음에 고칠 것 → 메일
```

| 파일 | 내용 |
| --- | --- |
| `survey-form.md` | 구글 폼 문항 (이름 그대로 만들기) |
| `survey_collect.json` | 워크플로 ① 응답 정리 — n8n 에 가져오기(import) |
| `survey_report.json` | 워크플로 ② 1차·2차 요약 메일 — n8n 에 가져오기 |
| `code/*.js` | 두 워크플로의 Code 노드 원본 (JSON 은 `python scripts/build_n8n.py` 로 만든다) |
| `../../common/prompts/survey_summary.v1.txt` | AI 에이전트 프롬프트 (워크플로 안에 두지 않고 GitHub 에서 읽음) |

## 왜 이렇게 만들었나 (PO 판단)

| 고민 | 결정 | 이유 |
| --- | --- | --- |
| 숫자를 AI 가 세게 할까? | **숫자는 Code 노드(규칙)가 센다.** AI 는 해석·제안만 | 물어보기와 같은 원칙 — 건수가 흔들리면 지표를 믿을 수 없다 |
| AI 가 실패하면? | 숫자 요약은 그대로 메일로 가고 `[규칙 기반 대체]` 표시 | 키가 없거나 오류여도 보고는 멈추지 않게 (CLAUDE.md 예외 처리) |
| 참가자 정보 | 이름·연락처 문항 없음, `P번호` 가 아니면 버림, 자유 답변의 전화번호·이메일 지움 | 개인정보 최소 수집 (앱과 같은 원칙) |
| 프롬프트를 어디에? | `common/prompts/survey_summary.v1.txt` 를 n8n 이 GitHub 에서 읽음 | 프롬프트는 코드 안에 두지 않고 버전 파일로 (CLAUDE.md) |
| Apps Script 가 아니라 n8n? | 설문은 n8n | 폼 응답 → 시트 → AI 에이전트 → 메일을 한 화면에서 잇고, 실행 기록이 남아 발표 때 보여 주기 좋다. 주간 브리핑은 그대로 Apps Script |

## 설치 (20분)

1. **n8n 계정**: https://n8n.io → 무료 체험(Cloud). (내 컴퓨터에 띄우려면 `npx n8n` 후 http://localhost:5678)
2. **구글 폼 · 시트**: `survey-form.md` 대로 폼을 만들고 응답을 시트로 연결, `정리` 탭을 만든다.
3. **연결(Credentials)** — n8n 왼쪽 `Credentials → Add`:
   - `Google Sheets OAuth2` · `Google Sheets Trigger OAuth2` · `Gmail OAuth2` (구글 로그인으로 허용)
   - `OpenAI` — API 키 (없으면 건너뛰어도 된다. 메일에 숫자 요약만 `[규칙 기반 대체]` 로 온다)
4. **가져오기**: `Workflows → Import from File` 로 `survey_collect.json`, `survey_report.json` 을 하나씩.
5. 가져온 워크플로에서 빨간 표시가 있는 노드를 열어:
   - 구글 시트 노드 3개: **Document** 에 시트 주소를 붙여넣고, Credential 을 고른다 (`설문지 응답 시트1` · `정리` 탭 이름이 다르면 바꾼다)
   - `OpenAI (gpt-4o-mini)`: OpenAI Credential
   - `메일 보내기`: **받는 주소를 여기에 넣으세요** 를 내 메일로 바꾸고 Gmail Credential (주소는 n8n 안에만 두고 저장소에는 적지 않는다)
6. 폼을 한 번 시험 제출 → ① 워크플로 `Execute workflow` → `정리` 탭에 4줄이 생기면 성공.
7. ② 워크플로에서 `지금 실행` → 메일이 오면 성공. 두 워크플로 오른쪽 위 **Active** 를 켠다.

## 실패하면

- **`정리` 탭에 안 쌓임**: 폼 문항 이름이 `survey-form.md` 와 글자까지 같은지 (특히 띄어쓰기). 참가자 번호가 `P1` 꼴인지.
- **메일에 `[규칙 기반 대체]`**: OpenAI Credential 이 없거나 키가 틀림. 숫자는 맞으니 그대로 써도 된다.
- **프롬프트 읽기 실패**: 저장소가 공개인지, `main` 에 `common/prompts/survey_summary.v1.txt` 가 있는지.
- JS 를 고쳤으면 `python scripts/build_n8n.py` 로 JSON 을 다시 만들고 다시 가져온다.

## 결과를 저장소에 남기기

테스트가 끝나면 `정리` 탭을 CSV 로 내려받아 `docs/user-test/results.csv` 에 붙이고, `/user-test-report` 스킬로 `docs/user-test/report.md` 를 만든다 (날짜별로 쌓기만).
