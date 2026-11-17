---
name: metrics-snapshot
description: ANI:WHERE 의 PO 지표(방문 전 정보 완결률 개선 전후, Q&A 검색 정확도, 사용자 테스트 성공률, 훅 차단 횟수)를 한 번에 재고 docs/metrics-log.md 에 쌓은 뒤, 발표용 해석 3줄을 써 준다. "지표 재 줘", "전후 비교 갱신", "발표용 숫자", "metrics" 라고 하면 쓴다.
---

# 지표 스냅샷

PRD.md 의 '성공 지표' 를 실제 숫자로 확인하는 절차. 숫자를 지어내지 않고 스크립트 출력만 쓴다.

## 순서

1. `python -X utf8 scripts/eval_ask.py --save` — Q&A 검색 정확도 (samples/ask_eval.jsonl, 오늘 2026-11-17 고정)
2. 사용자 테스트 기록이 있으면 `python -X utf8 scripts/user_test_report.py --save`
3. `python -X utf8 scripts/metrics_snapshot.py --save` — 1~4번 지표를 docs/metrics-log.md 에 쌓기
4. 결과를 읽고 아래 형식으로 **해석 3줄**을 쓴다 (PO 발표의 '평가 리포트' 장에 그대로 쓴다):
   - 무엇이 얼마나 바뀌었나 (전 → 후, 단위 포함)
   - 왜 바뀌었나 (어떤 결정·기능 때문인지. PRD 의 우선순위와 연결)
   - 아직 부족한 것과 다음 행동 1개
5. 목표 미달 지표가 있으면 PRD.md '성공 지표' 표의 목표값과 비교해 미달이라고 분명히 쓴다. 숨기지 않는다.

## 지킬 것

- docs/metrics-log.md · docs/ask-eval.md · docs/user-test/report.md 는 **쌓기만** 한다. 예전 기록을 고치거나 지우지 않는다.
- 평가 세트(samples/ask_eval.jsonl)를 고쳐서 점수를 올리지 않는다. 새 질문은 **추가**만 하고, 추가한 날짜를 docs/ai-mistakes.md 나 커밋 메시지에 남긴다.
- 검색 규칙을 고친 뒤 정확도가 올랐다면 "평가 세트를 보고 고쳤으므로 새 질문으로 다시 확인 필요" 를 해석에 함께 적는다.
- 사용자 테스트 참가자는 P1, P2 처럼 번호로만 적는다 (이름·연락처 금지).
