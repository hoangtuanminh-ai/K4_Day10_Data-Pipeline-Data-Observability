from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(metrics: dict[str, Any], name: str) -> float:
    value = metrics.get(name, 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a baseline report from actual pipeline artifacts."""
    ragas_status = metrics.get("ragas", {"skipped": "Not run"})
    content = f"""# Phase 1 — Baseline Data Pipeline Report

## Data ingestion

| Signal | Value |
| --- | --- |
| Source | {source_summary.get('source_api', 'Unknown')} |
| Raw records | {source_summary.get('raw_records_count', 'N/A')} |
| Clean records | {source_summary.get('clean_records_count', 'N/A')} |

## RAG evaluation

| Metric | Value |
| --- | ---: |
| Samples | {metrics.get('samples', 0)} |
| Retrieval hit rate | {_metric(metrics, 'retrieval_hit_rate'):.4f} |
| Mean token F1 | {_metric(metrics, 'mean_token_f1'):.4f} |
| Judge accuracy | {_metric(metrics, 'judge_accuracy'):.4f} |
| Mean judge score | {_metric(metrics, 'mean_judge_score'):.4f} |

Ragas: `{ragas_status}`

## Data quality and freshness

| Signal | Value |
| --- | --- |
| Quality status | {quality.get('status', 'UNKNOWN')} |
| Duplicate paper IDs | {quality.get('duplicate_paper_ids', 'N/A')} |
| Short or empty summaries | {quality.get('short_or_empty_summaries', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 'N/A')} |
| Latest publication | {freshness.get('latest_published', 'N/A')} |
| Fresh | {freshness.get('is_fresh', 'N/A')} |
"""
    write_text(report_path, content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write a factual baseline/corrupted/repaired comparison report."""
    metric_names = (
        ("retrieval_hit_rate", "Retrieval hit rate"),
        ("mean_token_f1", "Mean token F1"),
        ("judge_accuracy", "Judge accuracy"),
        ("mean_judge_score", "Mean judge score"),
    )
    metric_rows = []
    for key, label in metric_names:
        baseline = _metric(baseline_metrics, key)
        corrupted = _metric(corrupted_metrics, key)
        repaired = _metric(repaired_metrics, key)
        metric_rows.append(
            f"| {label} | {baseline:.4f} | {corrupted:.4f} | {repaired:.4f} | "
            f"{corrupted - baseline:+.4f} | {repaired - corrupted:+.4f} |"
        )

    content = f"""# Corruption, Repair, and Comparison Report

## RAG metrics

| Metric | Baseline | Corrupted | Repaired | Corrupted − baseline | Repaired − corrupted |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(metric_rows)}

## Quality and freshness signals

| Signal | Corrupted | Repaired |
| --- | --- | --- |
| Quality status | {corrupted_quality.get('status', 'UNKNOWN')} | {repaired_quality.get('status', 'UNKNOWN')} |
| Duplicate paper IDs | {corrupted_quality.get('duplicate_paper_ids', 'N/A')} | {repaired_quality.get('duplicate_paper_ids', 'N/A')} |
| Short or empty summaries | {corrupted_quality.get('short_or_empty_summaries', 'N/A')} | {repaired_quality.get('short_or_empty_summaries', 'N/A')} |
| Stale rows | {corrupted_freshness.get('stale_rows', 'N/A')} | {repaired_freshness.get('stale_rows', 'N/A')} |
| Is fresh | {corrupted_freshness.get('is_fresh', 'N/A')} | {repaired_freshness.get('is_fresh', 'N/A')} |

## Interpretation

The table reports observed metrics only. Treat repair as successful only when the repaired artifacts and metrics recover relative to the corrupted state; investigate any metric that does not recover.
"""
    write_text(report_path, content)
