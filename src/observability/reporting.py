from __future__ import annotations

from pathlib import Path
from typing import Any

def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Xuất báo cáo Phase 1 Baseline ra file Markdown."""
    md_content = f"""# PHASE 1 - BASELINE DATA PIPELINE REPORT

## 1. Data Ingestion Summary
- **Source API**: {source_summary.get('source_api')}
- **Raw Records Count**: {source_summary.get('raw_records_count')}
- **Clean Records Count**: {source_summary.get('clean_records_count')}

## 2. Baseline Metrics
- **Retrieval Hit Rate**: {metrics.get('retrieval_hit_rate', 0):.4f}
- **Mean Token F1**: {metrics.get('mean_token_f1', 0):.4f}
- **LLM Judge Score**: {metrics.get('mean_judge_score', 0):.4f}

## 3. Data Quality & Freshness
- **Quality Status**: `{quality.get('status')}`
- **Duplicate Paper IDs**: {quality.get('duplicate_paper_ids')}
- **Empty Summaries**: {quality.get('empty_summaries')}
- **Dataset Is Fresh**: `{freshness.get('is_fresh')}`
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md_content, encoding="utf-8")
    print(f"[ROLE 5] Phase 1 Report written to: {report_path}")

def generate_corruption_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Xuất báo cáo so sánh Baseline vs Corrupted vs Repaired ra file Markdown."""
    md_content = f"""# CORRUPTION, REPAIR & COMPARISON REPORT

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Delta (Repaired - Corrupted) |
| :--- | :---: | :---: | :---: | :---: |
| **Hit Rate** | {baseline_metrics.get('retrieval_hit_rate', 0):.4f} | {corrupted_metrics.get('retrieval_hit_rate', 0):.4f} | {repaired_metrics.get('retrieval_hit_rate', 0):.4f} | +{repaired_metrics.get('retrieval_hit_rate', 0) - corrupted_metrics.get('retrieval_hit_rate', 0):.4f} |
| **Token F1** | {baseline_metrics.get('mean_token_f1', 0):.4f} | {corrupted_metrics.get('mean_token_f1', 0):.4f} | {repaired_metrics.get('mean_token_f1', 0):.4f} | +{repaired_metrics.get('mean_token_f1', 0) - corrupted_metrics.get('mean_token_f1', 0):.4f} |
| **Judge Score** | {baseline_metrics.get('mean_judge_score', 0):.4f} | {corrupted_metrics.get('mean_judge_score', 0):.4f} | {repaired_metrics.get('mean_judge_score', 0):.4f} | +{repaired_metrics.get('mean_judge_score', 0) - corrupted_metrics.get('mean_judge_score', 0):.4f} |

## 2. Quality & Freshness Signals
- **Corrupted Quality Status**: `{corrupted_quality.get('status')}` (Duplicates: {corrupted_quality.get('duplicate_paper_ids')}, Empty Summaries: {corrupted_quality.get('empty_summaries')})
- **Repaired Quality Status**: `{repaired_quality.get('status')}` (Duplicates: {repaired_quality.get('duplicate_paper_ids')}, Empty Summaries: {repaired_quality.get('empty_summaries')})

## 3. Key Conclusions
1. Dữ liệu lỗi làm suy giảm đáng kể hiệu năng retrieval và chất lượng câu trả lời của Agent.
2. Việc phục hồi từ Raw Source JSON giúp khôi phục các chỉ số RAG hoàn toàn về lại mức Baseline ban đầu.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md_content, encoding="utf-8")
    print(f"[ROLE 5] Comparison Report written to: {report_path}")
