"""Dashboard quan sát Data Pipeline & RAG Observability cho demo nhóm.

Đọc trực tiếp các artifact đã được pipeline (script/run_phase1.py,
script/run_corruption_flow.py) sinh ra trong `data/` - không gọi lại LLM,
không cần API key để chạy dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(
    page_title="RAG Data Pipeline Observability",
    page_icon=":material/monitoring:",
    layout="wide",
)

PATHS = {
    "raw_records": DATA / "raw" / "crossref_records.json",
    "clean_csv": DATA / "clean" / "papers_clean.csv",
    "baseline_metrics": DATA / "results" / "baseline_metrics.json",
    "corrupted_metrics": DATA / "results" / "corrupted_metrics.json",
    "repaired_metrics": DATA / "results" / "repaired_metrics.json",
    "baseline_answers": DATA / "results" / "baseline_answers.json",
    "corrupted_answers": DATA / "results" / "corrupted_answers.json",
    "repaired_answers": DATA / "results" / "repaired_answers.json",
    "corruption_log": DATA / "results" / "corruption_log.json",
    "test_set": DATA / "eval" / "test_set.json",
    "baseline_quality": DATA / "quality" / "baseline_quality.json",
    "corrupted_quality": DATA / "quality" / "corrupted_quality.json",
    "repaired_quality": DATA / "quality" / "repaired_quality.json",
    "baseline_freshness": DATA / "quality" / "freshness_report.json",
    "corrupted_freshness": DATA / "quality" / "corrupted_freshness.json",
    "repaired_freshness": DATA / "quality" / "repaired_freshness.json",
    "phase1_report": DATA / "reports" / "phase1_report.md",
    "comparison_report": DATA / "reports" / "corruption_report.md",
}

STAGES = ["baseline", "corrupted", "repaired"]
STAGE_LABELS = {"baseline": "Baseline", "corrupted": "Corrupted", "repaired": "Repaired"}
STAGE_COLORS = {"baseline": "#6750A4", "corrupted": "#B3261E", "repaired": "#386A20"}


# =============================================================================
# Data loading (cached - clear via the refresh button after re-running the pipeline)
# =============================================================================


@st.cache_data(show_spinner=False)
def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def metrics_dataframe() -> pd.DataFrame:
    rows = []
    for stage in STAGES:
        m = load_json(PATHS[f"{stage}_metrics"]) or {}
        rows.append(
            {
                "stage": STAGE_LABELS[stage],
                "Hit rate": m.get("retrieval_hit_rate"),
                "Token F1": m.get("mean_token_f1"),
                "Judge score": m.get("mean_judge_score"),
                "Judge accuracy": m.get("judge_accuracy"),
                "samples": m.get("samples"),
            }
        )
    return pd.DataFrame(rows)


def quality_dataframe() -> pd.DataFrame:
    rows = []
    for stage in STAGES:
        q = load_json(PATHS[f"{stage}_quality"]) or {}
        f = load_json(PATHS[f"{stage}_freshness"]) or {}
        rows.append(
            {
                "stage": STAGE_LABELS[stage],
                "status": q.get("status", "N/A"),
                "total_rows": q.get("total_rows"),
                "duplicate_paper_ids": q.get("duplicate_paper_ids"),
                "empty_summaries": q.get("empty_summaries"),
                "null_paper_ids": q.get("null_paper_ids"),
                "stale_rows": q.get("stale_rows"),
                "is_fresh": f.get("is_fresh"),
                "latest_published": f.get("latest_published"),
                "oldest_published": f.get("oldest_published"),
            }
        )
    return pd.DataFrame(rows)


def status_badge(status: str | None) -> None:
    if status == "PASSED":
        st.badge("Passed", icon=":material/check_circle:", color="green")
    elif status == "FAILED":
        st.badge("Failed", icon=":material/error:", color="red")
    else:
        st.badge("N/A", icon=":material/help:", color="gray")


# =============================================================================
# Header
# =============================================================================

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.title(":material/monitoring: RAG data pipeline observability")
    if st.button(":material/refresh: Refresh data", type="tertiary"):
        st.cache_data.clear()
        st.rerun()

st.caption(
    "Crossref API → raw → clean → embedding + ChromaDB → RAG evaluation → "
    "quality/freshness reports → corrupt data → evaluate impact → repair → compare"
)

any_artifact = any(p.exists() for p in PATHS.values())
if not any_artifact:
    st.warning(
        "Chưa tìm thấy artifact nào trong `data/`. Chạy "
        "`python script/run_phase1.py` rồi `python script/run_corruption_flow.py` trước.",
        icon=":material/warning:",
    )

tab_overview, tab_compare, tab_quality, tab_corruption, tab_qa, tab_reports = st.tabs(
    [
        ":material/dashboard: Tổng quan",
        ":material/bar_chart: So sánh 3 trạng thái",
        ":material/verified: Chất lượng & freshness",
        ":material/bug_report: Corruption log",
        ":material/chat: Agent Q&A explorer",
        ":material/description: Báo cáo",
    ]
)

# =============================================================================
# Tab 1 - Overview
# =============================================================================

with tab_overview:
    raw_records = load_json(PATHS["raw_records"])
    clean_df = load_csv(PATHS["clean_csv"])
    baseline_metrics = load_json(PATHS["baseline_metrics"]) or {}

    with st.container(horizontal=True):
        st.metric(
            "Raw records (Crossref)",
            len(raw_records) if raw_records is not None else "N/A",
            border=True,
        )
        st.metric(
            "Clean records",
            len(clean_df) if clean_df is not None else "N/A",
            border=True,
        )
        st.metric(
            "Eval samples",
            baseline_metrics.get("samples", "N/A"),
            border=True,
        )
        st.metric(
            "Baseline hit rate",
            f"{baseline_metrics.get('retrieval_hit_rate', 0):.2%}"
            if baseline_metrics
            else "N/A",
            border=True,
        )

    with st.container(border=True):
        st.markdown("**Luồng dữ liệu end-to-end**")
        st.mermaid_chart(
            """
            graph LR
                A[Crossref API] --> B[Raw data]
                B --> C[Cleaned data]
                C --> D[Embedding + ChromaDB]
                D --> E[RAG evaluation]
                E --> F[Quality / freshness report]
                F --> G[Corrupt data]
                G --> H[Evaluate impact]
                H --> I[Repair from raw]
                I --> J[Compare baseline / corrupted / repaired]
            """
        )

    if clean_df is not None:
        with st.container(border=True):
            st.markdown("**Sample clean dataset**")
            st.dataframe(
                clean_df[["paper_id", "title", "primary_category", "published", "age_days"]],
                hide_index=True,
                height=280,
            )

# =============================================================================
# Tab 2 - Baseline vs Corrupted vs Repaired
# =============================================================================

with tab_compare:
    mdf = metrics_dataframe()

    if mdf[["Hit rate", "Token F1", "Judge score"]].isna().all(axis=None):
        st.info(
            "Chưa có đủ metrics của cả 3 trạng thái. Chạy corruption flow để có "
            "corrupted/repaired metrics.",
            icon=":material/info:",
        )
    else:
        base_row = mdf[mdf["stage"] == "Baseline"].iloc[0]
        with st.container(horizontal=True):
            for _, row in mdf.iterrows():
                delta = None
                if row["stage"] != "Baseline" and pd.notna(row["Judge score"]):
                    delta = f"{row['Judge score'] - base_row['Judge score']:+.2f} vs baseline"
                with st.container(border=True):
                    st.markdown(f"**{row['stage']}**")
                    st.metric("Hit rate", f"{row['Hit rate']:.2%}" if pd.notna(row["Hit rate"]) else "N/A")
                    st.metric("Token F1", f"{row['Token F1']:.4f}" if pd.notna(row["Token F1"]) else "N/A")
                    st.metric(
                        "Judge score (1-5)",
                        f"{row['Judge score']:.2f}" if pd.notna(row["Judge score"]) else "N/A",
                        delta,
                    )

        st.space("small")

        melted = mdf.melt(
            id_vars="stage",
            value_vars=["Hit rate", "Token F1", "Judge score"],
            var_name="metric",
            value_name="value",
        )
        chart = (
            alt.Chart(melted)
            .mark_bar()
            .encode(
                x=alt.X("stage:N", title=None, sort=["Baseline", "Corrupted", "Repaired"]),
                y=alt.Y("value:Q", title=None),
                color=alt.Color(
                    "stage:N",
                    title=None,
                    scale=alt.Scale(
                        domain=["Baseline", "Corrupted", "Repaired"],
                        range=[STAGE_COLORS["baseline"], STAGE_COLORS["corrupted"], STAGE_COLORS["repaired"]],
                    ),
                    legend=alt.Legend(orient="bottom"),
                ),
                column=alt.Column("metric:N", title=None),
                tooltip=["stage", "metric", alt.Tooltip("value:Q", format=".4f")],
            )
            .properties(height=280, width=180)
        )
        with st.container(border=True):
            st.markdown("**Metric theo từng trạng thái**")
            st.altair_chart(chart)

# =============================================================================
# Tab 3 - Data quality & freshness
# =============================================================================

with tab_quality:
    qdf = quality_dataframe()

    with st.container(horizontal=True):
        for _, row in qdf.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['stage']}**")
                status_badge(row["status"])
                st.metric("Total rows", row["total_rows"] if pd.notna(row["total_rows"]) else "N/A")
                st.metric("Duplicate paper_id", row["duplicate_paper_ids"] if pd.notna(row["duplicate_paper_ids"]) else "N/A")
                st.metric("Empty summaries", row["empty_summaries"] if pd.notna(row["empty_summaries"]) else "N/A")
                st.metric("Stale rows (>180d)", row["stale_rows"] if pd.notna(row["stale_rows"]) else "N/A")
                st.caption(
                    f"Fresh: {row['is_fresh']} | {row['oldest_published']} → {row['latest_published']}"
                    if pd.notna(row["is_fresh"])
                    else "Freshness: N/A"
                )

    with st.container(border=True):
        st.markdown("**Bảng chi tiết**")
        st.dataframe(qdf, hide_index=True)

# =============================================================================
# Tab 4 - Corruption log
# =============================================================================

with tab_corruption:
    log = load_json(PATHS["corruption_log"])
    if not log:
        st.info("Chưa có corruption log. Chạy `script/run_corruption_flow.py`.", icon=":material/info:")
    else:
        st.markdown(f"**{len(log)} lỗi dữ liệu đã được giả lập có chủ đích trên baseline dataset**")
        log_df = pd.DataFrame(log)
        if "details" not in log_df.columns:
            log_df["details"] = None
        if "paper_id" not in log_df.columns:
            log_df["paper_id"] = None
        log_df["details"] = log_df["details"].fillna(log_df["paper_id"])
        log_df = log_df[["type", "details"]].rename(columns={"type": "Loại lỗi", "details": "Chi tiết"})

        type_labels = {
            "drop_latest_records": ":material/delete: Mất bản ghi mới nhất",
            "blank_summary": ":material/subject: Summary rỗng",
            "inject_noise": ":material/report: Nhiễu / rác trong text",
            "truncate_title": ":material/content_cut: Title bị cắt cụt",
            "stale_date": ":material/schedule: Ngày xuất bản lỗi thời",
            "add_duplicate": ":material/content_copy: Bản ghi trùng lặp",
        }
        log_df["Loại lỗi"] = log_df["Loại lỗi"].map(lambda t: type_labels.get(t, t))
        st.dataframe(log_df, hide_index=True, width="stretch")

        with st.expander("Xem corruption_log.json gốc"):
            st.json(log)

# =============================================================================
# Tab 5 - Agent Q&A explorer
# =============================================================================

with tab_qa:
    test_set = load_json(PATHS["test_set"])

    if test_set:
        qs_df = pd.DataFrame(test_set)[["id", "question_type", "question", "ground_truth_doc_ids"]]
        with st.container(border=True):
            st.markdown(f"**Test set — {len(qs_df)} câu hỏi**")
            type_counts = qs_df["question_type"].value_counts()
            st.caption(" · ".join(f"{t}: {n}" for t, n in type_counts.items()))
            st.dataframe(
                qs_df.rename(
                    columns={
                        "id": "ID",
                        "question_type": "Loại",
                        "question": "Câu hỏi",
                        "ground_truth_doc_ids": "Ground truth doc IDs",
                    }
                ),
                hide_index=True,
                height=280,
            )
    else:
        st.info("Chưa có test set (`data/eval/test_set.json`).", icon=":material/info:")

    answers_by_stage = {stage: load_json(PATHS[f"{stage}_answers"]) for stage in STAGES}
    available = {s: a for s, a in answers_by_stage.items() if a}

    if not available:
        st.info("Chưa có answers nào. Chạy pipeline trước.", icon=":material/info:")
    else:
        ref_answers = next(iter(available.values()))
        options = {f"{a['id']} — {a['question'][:80]}": a["id"] for a in ref_answers}
        choice = st.selectbox("Chọn câu hỏi để xem chi tiết câu trả lời", options=list(options.keys()))
        qid = options[choice]

        ref_item = next(a for a in ref_answers if a["id"] == qid)
        with st.container(border=True):
            st.markdown(f"**Câu hỏi** ({ref_item['question_type']})")
            st.write(ref_item["question"])
            st.markdown("**Ground truth**")
            st.caption(ref_item["ground_truth"])

        cols = st.columns(len(available))
        for col, (stage, answers) in zip(cols, available.items()):
            item = next((a for a in answers if a["id"] == qid), None)
            with col:
                with st.container(border=True):
                    st.markdown(f"**{STAGE_LABELS[stage]}**")
                    if item is None:
                        st.caption("Không có dữ liệu cho câu hỏi này.")
                        continue
                    if item["retrieval_hit"]:
                        st.badge("Hit", icon=":material/check_circle:", color="green")
                    else:
                        st.badge("Miss", icon=":material/error:", color="red")
                    st.metric("Judge score", f"{item['judge']['score']}/5")
                    st.metric("Token F1", f"{item['token_f1']:.3f}")
                    st.markdown("**Answer**")
                    st.caption(item["answer"])
                    with st.expander("Judge reasoning"):
                        st.write(item["judge"]["reasoning"])
                    with st.expander("Retrieved doc IDs"):
                        st.write(item["retrieved_doc_ids"])

# =============================================================================
# Tab 6 - Raw reports
# =============================================================================

with tab_reports:
    phase1_report = load_text(PATHS["phase1_report"])
    comparison_report = load_text(PATHS["comparison_report"])

    if phase1_report:
        with st.expander(":material/description: Phase 1 - Baseline report", expanded=False, icon=":material/description:"):
            st.markdown(phase1_report)
    if comparison_report:
        with st.expander(":material/description: Corruption, repair & comparison report", expanded=True, icon=":material/description:"):
            st.markdown(comparison_report)
    if not phase1_report and not comparison_report:
        st.info("Chưa có report nào trong `data/reports/`.", icon=":material/info:")
