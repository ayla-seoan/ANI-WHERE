"""n8n 워크플로 JSON 만들기 — automation/n8n/code/*.js 를 Code 노드에 넣어 가져오기(import)용 파일로.

    python scripts/build_n8n.py

만든 파일: automation/n8n/survey_collect.json (응답 정리), automation/n8n/survey_report.json (요약 메일)
JS 는 code/ 폴더 한 곳에서만 고친다 (Node 로 시험할 수 있게). 프롬프트는 common/prompts/survey_summary.v3.txt 를
n8n 이 GitHub 에서 읽는다 (프롬프트를 워크플로 안에 문자열로 두지 않는다 — CLAUDE.md).
받는 메일 주소 · 시트 주소 · 키는 여기 적지 않는다. 가져온 뒤 n8n 화면에서 넣는다 (automation/n8n/README.md).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "automation" / "n8n"
CODE = OUT / "code"
PROMPT_URL = "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/common/prompts/survey_summary.v3.txt"
SHEET = {"__rl": True, "mode": "url", "value": ""}           # 가져온 뒤 n8n 에서 구글 시트 주소를 넣는다


def node(name: str, typ: str, ver: float, pos: tuple[int, int], params: dict, **extra) -> dict:
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"aniwhere/{name}")), "name": name, "type": typ,
            "typeVersion": ver, "position": list(pos), "parameters": params, **extra}


def code_node(name: str, file: str, pos: tuple[int, int]) -> dict:
    return node(name, "n8n-nodes-base.code", 2, pos, {"jsCode": (CODE / file).read_text(encoding="utf-8")})


def link(*names: str) -> dict:
    return {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}


def collect() -> dict:
    nodes = [
        node("폼 응답 들어옴", "n8n-nodes-base.googleSheetsTrigger", 1, (0, 0),
             {"pollTimes": {"item": [{"mode": "everyMinute"}]}, "documentId": SHEET,
              "sheetName": {"__rl": True, "mode": "name", "value": "설문지 응답 시트1"}, "event": "rowAdded", "options": {}}),
        node("1차 폼 응답 들어옴", "n8n-nodes-base.googleSheetsTrigger", 1, (0, 200),       # 1차 폼 (같은 시트의 '1차 응답' 탭)
             {"pollTimes": {"item": [{"mode": "everyMinute"}]}, "documentId": SHEET,
              "sheetName": {"__rl": True, "mode": "name", "value": "1차 응답"}, "event": "rowAdded", "options": {}}),
        code_node("과업 4줄로 정리 · 개인정보 지우기", "clean_response.js", (240, 0)),
        node("정리 시트에 쌓기", "n8n-nodes-base.googleSheets", 4.5, (480, 0),
             {"operation": "append", "documentId": SHEET, "sheetName": {"__rl": True, "mode": "name", "value": "정리"},
              "columns": {"mappingMode": "autoMapInputData", "value": {}}, "options": {}}),
    ]
    return {"name": "ANI:WHERE 사용자 테스트 ① 응답 정리", "nodes": nodes,
            "connections": {**link("폼 응답 들어옴", "과업 4줄로 정리 · 개인정보 지우기", "정리 시트에 쌓기"),
                            **link("1차 폼 응답 들어옴", "과업 4줄로 정리 · 개인정보 지우기")},
            "settings": {"timezone": "Asia/Seoul", "executionOrder": "v1"}, "active": False}


def report() -> dict:
    nodes = [
        node("매일 21시", "n8n-nodes-base.scheduleTrigger", 1.2, (0, 0),
             {"rule": {"interval": [{"field": "cronExpression", "expression": "0 21 * * *"}]}}),
        node("지금 실행", "n8n-nodes-base.manualTrigger", 1, (0, 200), {}),
        node("정리 시트 읽기", "n8n-nodes-base.googleSheets", 4.5, (240, 100),
             {"operation": "read", "documentId": SHEET, "sheetName": {"__rl": True, "mode": "name", "value": "정리"},
              "options": {}}),
        code_node("1차·2차 숫자 세기", "summarize.js", (480, 100)),
        node("프롬프트 읽기 (GitHub)", "n8n-nodes-base.httpRequest", 4.2, (720, 100),
             {"url": PROMPT_URL, "options": {"response": {"response": {"responseFormat": "text", "outputPropertyName": "prompt"}}}}),
        node("AI 에이전트 요약", "@n8n/n8n-nodes-langchain.agent", 1.7, (960, 100),
             {"promptType": "define",
              "text": "={{ '[규칙으로 센 요약]\\n' + $('1차·2차 숫자 세기').item.json.요약 + '\\n\\n[숫자 JSON]\\n' + JSON.stringify($('1차·2차 숫자 세기').item.json.숫자) }}",
              "options": {"systemMessage": "={{ $json.prompt }}"}},
             onError="continueRegularOutput"),
        node("OpenAI (gpt-4o-mini)", "@n8n/n8n-nodes-langchain.lmChatOpenAi", 1.2, (960, 320),
             {"model": {"__rl": True, "mode": "list", "value": "gpt-4o-mini"}, "options": {"temperature": 0}}),
        code_node("메일 본문 만들기", "compose_mail.js", (1200, 100)),
        node("메일 보내기", "n8n-nodes-base.gmail", 2.1, (1440, 100),
             {"sendTo": "받는 주소를 여기에 넣으세요", "subject": "={{ $json.제목 }}", "emailType": "text",
              "message": "={{ $json.본문 }}", "options": {}}),
    ]
    conns = link("매일 21시", "정리 시트 읽기", "1차·2차 숫자 세기", "프롬프트 읽기 (GitHub)", "AI 에이전트 요약",
                 "메일 본문 만들기", "메일 보내기")
    conns["지금 실행"] = {"main": [[{"node": "정리 시트 읽기", "type": "main", "index": 0}]]}
    conns["OpenAI (gpt-4o-mini)"] = {"ai_languageModel": [[{"node": "AI 에이전트 요약", "type": "ai_languageModel", "index": 0}]]}
    return {"name": "ANI:WHERE 사용자 테스트 ② 1차·2차 요약 메일", "nodes": nodes, "connections": conns,
            "settings": {"timezone": "Asia/Seoul", "executionOrder": "v1"}, "active": False}


if __name__ == "__main__":
    for file, wf in (("survey_collect.json", collect()), ("survey_report.json", report())):
        (OUT / file).write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
        print("만듦:", OUT / file)
