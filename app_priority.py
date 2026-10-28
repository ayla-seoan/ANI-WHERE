"""주제 1 — KPI 기반 백로그 우선순위 생성기.

핵심 흐름 하나:
    CSV 업로드 → KPI·가중치 입력 → 우선순위 Top 10 + 근거 + 뺀 항목
실행:  streamlit run app_priority.py
"""
from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from common import ai, board, guard, priority
from common.board_component import priority_board
from common.schema import PriorityResult

load_dotenv()

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "samples" / "backlog_sample.csv"

st.set_page_config(page_title="백로그 우선순위 생성기", page_icon="📋", layout="wide")
st.title("📋 KPI 기반 백로그 우선순위 생성기")
st.caption("백로그와 이번 분기 KPI를 넣으면, 무엇을 먼저 할지와 그 근거를 뽑아줍니다.")

DEFAULT_KPIS = [
    {"name": "해지율 감소", "weight": 40, "keywords": "해지 이탈 방어 유지 재가입 만족도"},
    {"name": "신규 가입 전환", "weight": 35, "keywords": "가입 전환 퍼널 신청 프로모션 마케팅"},
    {"name": "운영 비용 절감", "weight": 25, "keywords": "자동화 수기 배치 집계 리포트 상담 문의"},
]

# ----------------------------------------------------------------- 사이드바
with st.sidebar:
    st.header("1. 이번 분기 KPI")
    st.caption("가중치 합이 100이 아니어도 됩니다. 상대적인 크기만 봅니다.")
    kpi_df = st.data_editor(
        pd.DataFrame(DEFAULT_KPIS),
        num_rows="dynamic",
        width="stretch",
        column_config={
            "name": st.column_config.TextColumn("KPI 이름", required=True),
            "weight": st.column_config.NumberColumn("가중치", min_value=1, max_value=100),
            "keywords": st.column_config.TextColumn("연관 키워드", help="대체 경로에서 KPI 연결에 씁니다"),
        },
        key="kpi_editor",
    )
    st.divider()
    use_ai = st.toggle("AI 사용", value=True, help="끄면 규칙 기반으로만 계산합니다")
    st.caption(f"프롬프트 버전: `{ai.load_prompt('priority')[1]}`")

# ----------------------------------------------------------------- 입력
st.subheader("2. 백로그 올리기")
col_a, col_b = st.columns([3, 1])
with col_a:
    uploaded = st.file_uploader(
        "CSV 파일 (필수 컬럼: id, title, description, effort_days)", type=["csv"]
    )
with col_b:
    st.write("")
    st.write("")
    use_sample = st.button("샘플 35건 불러오기", width="stretch")

df: pd.DataFrame | None = None
if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"CSV를 읽을 수 없습니다. 파일이 손상되었을 수 있습니다. ({exc})")
elif use_sample or st.session_state.get("loaded_sample"):
    st.session_state["loaded_sample"] = True
    df = pd.read_csv(SAMPLE)
    st.info(f"샘플 백로그 {len(df)}건을 불러왔습니다.")

# ----------------------------------------------------------------- 빈 화면
if df is None:
    st.divider()
    st.markdown(
        "#### 아직 올린 백로그가 없습니다\n"
        "- 오른쪽 위 **샘플 35건 불러오기** 로 바로 시험해 볼 수 있습니다.\n"
        "- 직접 올리실 경우 `id, title, description, effort_days` 컬럼이 필요합니다."
    )
    st.stop()

# ----------------------------------------------------------------- 검증
validation = guard.validate_backlog(df)
for warning in validation.warnings:
    st.warning(warning)
if not validation.ok:
    st.error("이 파일로는 계산할 수 없습니다.")
    for err in validation.errors:
        st.write(f"- {err}")
    st.stop()

kpis = [
    {"name": str(r["name"]).strip(), "weight": float(r["weight"]), "keywords": str(r.get("keywords", ""))}
    for _, r in kpi_df.iterrows()
    if str(r.get("name", "")).strip()
]
if not kpis:
    st.error("KPI를 한 개 이상 입력해 주세요.")
    st.stop()

with st.expander(f"올린 백로그 {len(df)}건 보기"):
    st.dataframe(df, width="stretch", hide_index=True)

# ----------------------------------------------------------------- 실행
st.subheader("3. 우선순위 만들기")
if st.button("우선순위 생성", type="primary"):
    started = time.monotonic()
    with st.spinner("계산 중..."):
        if use_ai:
            result_meta = ai.call_structured(
                prompt_name="priority",
                user_content=priority.build_user_content(df, kpis),
                schema=PriorityResult,
                fallback=lambda: priority.rule_based(df, kpis),
            )
        else:
            result_meta = ai.AIResult(
                ok=True, data=priority.rule_based(df, kpis), source="fallback",
            )
    elapsed = time.monotonic() - started

    if not result_meta.ok:
        st.error(f"계산에 실패했습니다: {result_meta.error}")
        st.stop()

    st.session_state["result"] = result_meta
    st.session_state["elapsed"] = elapsed

# ----------------------------------------------------------------- 결과
result_meta = st.session_state.get("result")
if result_meta is None:
    st.stop()

result: PriorityResult = result_meta.data
elapsed = st.session_state.get("elapsed", 0.0)

m1, m2, m3 = st.columns(3)
m1.metric("산출 시간", f"{elapsed:.1f}초")
m2.metric("근거가 붙은 항목", f"{sum(1 for i in result.top_items if i.reason)} / {len(result.top_items)}")
m3.metric("산출 경로", result_meta.badge)

if result_meta.source == "fallback" and result_meta.error:
    st.warning(f"AI 호출이 실패해 규칙 기반으로 계산했습니다. ({result_meta.error})")

# ----------------------------------------------------------------- 보드
st.divider()
st.markdown("#### 보드에서 직접 조정하기")

template_key = st.radio(
    "보드 템플릿",
    options=list(board.TEMPLATES.keys()),
    format_func=lambda k: board.TEMPLATES[k]["label"],
    horizontal=True,
    key="template_key",
)
tpl = board.TEMPLATES[template_key]

opt1, opt2 = st.columns(2)
with opt1:
    show_excluded = st.checkbox(
        "제외 항목도 보드에 올리기", value=False,
        help="켜면 이번 분기에 빼기로 한 항목까지 보입니다. 되살리려면 위 칸으로 옮기세요.",
    )
with opt2:
    relative = st.checkbox(
        "영향도를 이번 백로그 안에서 상대 평가", value=True,
        help="끄면 점수 34/67 고정 경계를 씁니다. 그러면 대부분 아래 칸에 몰릴 수 있습니다.",
    )

stickers = board.build_stickers(
    result, df, template_key,
    relative_impact=relative, include_excluded=show_excluded,
)
state_key = f"layout::{template_key}::{show_excluded}::{relative}"
if state_key not in st.session_state:
    st.session_state[state_key] = board.initial_layout(stickers, template_key)

c1, c2 = st.columns([1, 5])
with c1:
    if st.button("AI 결과로 되돌리기", width="stretch"):
        st.session_state[state_key] = board.initial_layout(stickers, template_key)
        st.rerun()

moved = priority_board(
    template={
        "rows": tpl["rows"], "cols": tpl["cols"], "order": tpl["order"],
        "cell_notes": tpl["cell_notes"], "x_axis": tpl["x_axis"], "y_axis": tpl["y_axis"],
    },
    stickers=stickers,
    layout=st.session_state[state_key],
    key=f"board::{state_key}",
)
if moved and isinstance(moved, dict) and moved.get("layout"):
    st.session_state[state_key] = moved["layout"]

final_df = board.layout_to_ranking(st.session_state[state_key], stickers, template_key)

if final_df.empty:
    st.info("보드에 올라간 항목이 없습니다.")
else:
    diff = board.compare_ranking(final_df)
    d1, d2, d3 = st.columns(3)
    d1.metric("내가 옮긴 항목", f"{diff['moved']} / {diff['total']}")
    d2.metric("순위가 그대로인 항목", f"{diff['same_rank']} / {diff['total']}")
    d3.metric("AI 상위 10건과 겹침", f"{diff['agreement']:.0f}%")
    st.caption("AI가 뽑은 순위와 내가 정한 순위가 얼마나 다른지. 발표에서 'AI를 어디까지 따랐는가'의 근거가 됩니다.")

    st.markdown("##### 보드를 반영한 최종 순위")
    st.dataframe(final_df, width="stretch", hide_index=True)

    board_buf = io.StringIO()
    final_df.to_csv(board_buf, index=False)
    st.download_button(
        "최종 순위 CSV 내려받기",
        board_buf.getvalue().encode("utf-8-sig"),
        file_name="priority_final.csv",
        mime="text/csv",
        key="dl_final",
    )

st.divider()
with st.expander("AI 원본 결과 보기 (조정 전)"):
    st.markdown("#### 먼저 할 일")
    st.dataframe(priority.to_dataframe(result), width="stretch", hide_index=True)

    st.markdown("#### 이번 분기에 하지 않는 것")
    excluded = priority.excluded_dataframe(result)
    if len(excluded):
        st.dataframe(excluded, width="stretch", hide_index=True)
    else:
        st.caption("제외된 항목이 없습니다.")

buffer = io.StringIO()
priority.to_dataframe(result).to_csv(buffer, index=False)
st.download_button(
    "결과 CSV 내려받기",
    buffer.getvalue().encode("utf-8-sig"),
    file_name="priority_result.csv",
    mime="text/csv",
)

# ----------------------------------------------------------------- 재현성
st.divider()
st.markdown("#### 재현성 확인")
st.caption("같은 입력으로 한 번 더 돌려 Top 10 순위가 얼마나 일치하는지 봅니다.")
if st.button("한 번 더 실행해서 비교"):
    with st.spinner("다시 계산 중..."):
        if use_ai:
            second = ai.call_structured(
                prompt_name="priority",
                user_content=priority.build_user_content(df, kpis),
                schema=PriorityResult,
                fallback=lambda: priority.rule_based(df, kpis),
            )
        else:
            second = ai.AIResult(ok=True, data=priority.rule_based(df, kpis), source="fallback")

    first_ids = [i.item_id for i in result.top_items]
    second_ids = [i.item_id for i in second.data.top_items]
    same_set = len(set(first_ids) & set(second_ids))
    same_rank = sum(1 for a, b in zip(first_ids, second_ids) if a == b)
    total = max(len(first_ids), 1)

    c1, c2 = st.columns(2)
    c1.metric("Top 10 구성 일치", f"{same_set / total * 100:.0f}%")
    c2.metric("순위까지 일치", f"{same_rank / total * 100:.0f}%")
    st.dataframe(
        pd.DataFrame({"순위": range(1, total + 1), "1회차": first_ids,
                      "2회차": second_ids + [""] * (total - len(second_ids))}),
        width="stretch", hide_index=True,
    )
