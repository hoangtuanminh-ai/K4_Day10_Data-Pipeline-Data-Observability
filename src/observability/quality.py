from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run auditable completeness, uniqueness, validity, and freshness checks."""
    required_columns = {"paper_id", "title", "summary", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cannot run quality checks; missing columns: {', '.join(missing_columns)}")

    total_rows = len(df)
    paper_ids = df["paper_id"].fillna("").astype(str).str.strip()
    titles = df["title"].fillna("").astype(str).str.strip()
    summaries = df["summary"].fillna("").astype(str).str.strip()
    age_days = pd.to_numeric(df["age_days"], errors="coerce")

    checks = {
        "row_count": {"passed": total_rows > 0, "actual": total_rows, "expected": "> 0"},
        "paper_id_not_null": {
            "passed": int(paper_ids.eq("").sum()) == 0,
            "invalid_rows": int(paper_ids.eq("").sum()),
        },
        "paper_id_unique": {
            "passed": int(paper_ids.duplicated(keep=False).sum()) == 0,
            "duplicate_rows": int(paper_ids.duplicated(keep=False).sum()),
        },
        "title_not_blank": {
            "passed": int(titles.eq("").sum()) == 0,
            "invalid_rows": int(titles.eq("").sum()),
        },
        "summary_min_length": {
            "passed": int(summaries.str.len().lt(20).sum()) == 0,
            "invalid_rows": int(summaries.str.len().lt(20).sum()),
            "minimum_characters": 20,
        },
        "age_days_valid": {
            "passed": int(age_days.isna().sum() + age_days.lt(0).sum()) == 0,
            "invalid_rows": int(age_days.isna().sum() + age_days.lt(0).sum()),
        },
        "freshness": {
            "passed": int(age_days.gt(settings.freshness_threshold_days).sum()) == 0,
            "stale_rows": int(age_days.gt(settings.freshness_threshold_days).sum()),
            "threshold_days": settings.freshness_threshold_days,
        },
    }
    report = {
        "report_name": report_name,
        "status": "PASSED" if all(check["passed"] for check in checks.values()) else "FAILED",
        "total_rows": total_rows,
        "null_paper_ids": int(paper_ids.eq("").sum()),
        "duplicate_paper_ids": int(paper_ids.duplicated(keep=False).sum()),
        "blank_titles": int(titles.eq("").sum()),
        "short_or_empty_summaries": int(summaries.str.len().lt(20).sum()),
        "stale_rows": int(age_days.gt(settings.freshness_threshold_days).sum()),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise publication-date freshness and persist the evidence."""
    required_columns = {"published", "age_days"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cannot build freshness report; missing columns: {', '.join(missing_columns)}")

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    age_days = pd.to_numeric(df["age_days"], errors="coerce")
    valid_dates = published.dropna()
    stale_rows = int(age_days.gt(settings.freshness_threshold_days).sum())
    report = {
        "total_rows": len(df),
        "valid_published_dates": int(valid_dates.size),
        "invalid_published_dates": int(published.isna().sum()),
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(len(df) > 0 and valid_dates.size == len(df) and stale_rows == 0),
    }
    write_json(report_path, report)
    return report
