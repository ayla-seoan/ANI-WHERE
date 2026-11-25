"""사용자 테스트 응답 검증 (11/20, 11/25 고침): 구글 폼 응답 탭에 있는 응답만 센다. 받은 시각은 따지지 않는다."""
from datetime import datetime

from common import stats

NOW = datetime(2026, 11, 20, 12, 0)


def test_parse_form_time_korean_ampm():
    assert stats.parse_form_time("2026. 11. 19 오후 9:22:00") == datetime(2026, 11, 19, 21, 22)
    assert stats.parse_form_time("2026. 11. 19 오전 12:05:00") == datetime(2026, 11, 19, 0, 5)
    assert stats.parse_form_time("2026-11-19 08:00:00") == datetime(2026, 11, 19, 8, 0)
    assert stats.parse_form_time("") is None


def test_only_real_form_responses_count():
    rows = [{"닉네임": n, "버전": v, "과제": "질문 1"} for n, v in [("a", "2차"), ("b", "2차"), ("c", "1차"), ("d", "2차")]]
    forms = {"1차": [],
             "2차": [{"닉네임": "a", "타임스탬프": "2026. 11. 19 오후 9:22:00"},     # 진짜
                     {"닉네임": "b", "타임스탬프": "2026. 11. 30 오후 6:21:00"},     # 미래 → 그래도 센다 (11/25)
                     {"닉네임": "d", "타임스탬프": ""}]}                          # 시각 없음 → 그래도 센다
    kept, info = stats.survey_verify(rows, forms, now=NOW)
    assert [r["닉네임"] for r in kept] == ["a", "b", "d"]                         # c 는 폼 응답 탭에 없어 제외
    assert info == {"전체": 4, "검증": 3, "제외": 1, "폼 응답 미래 시각": 1, "폼 응답 시각 없음": 1, "폼에 없음": 1}


def test_same_nickname_other_version_does_not_verify():
    rows = [{"닉네임": "a", "버전": "1차", "과제": "질문 1"}]
    forms = {"1차": [], "2차": [{"닉네임": "a", "타임스탬프": "2026. 11. 19 오후 1:00:00"}]}
    kept, _ = stats.survey_verify(rows, forms, now=NOW)
    assert kept == []
