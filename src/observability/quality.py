from __future__ import annotations

import json
from typing import Any
import pandas as pd
from core.config import Settings

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Thực hiện các kiểm tra Data Quality Gates."""
    print(f"[ROLE 5] Running Quality Checks for: {report_name}...")
    
    total_rows = len(df)
    null_paper_ids = int(df["paper_id"].isnull().sum())
    unique_paper_ids = int(df["paper_id"].nunique())
    duplicate_paper_ids = total_rows - unique_paper_ids
    empty_summaries = int((df["summary"].str.strip() == "").sum())
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    status = "PASSED" if (null_paper_ids == 0 and duplicate_paper_ids == 0 and empty_summaries == 0) else "FAILED"

    report = {
        "report_name": report_name,
        "status": status,
        "total_rows": total_rows,
        "null_paper_ids": null_paper_ids,
        "duplicate_paper_ids": duplicate_paper_ids,
        "empty_summaries": empty_summaries,
        "stale_rows": stale_rows,
    }

    out_path = settings.paths.quality_dir / f"{report_name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[CONSOLE TEST] Quality Status: {status} | Duplicates: {duplicate_paper_ids} | Empty Summaries: {empty_summaries}")
    return report

def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tổng hợp báo cáo độ tươi của dữ liệu (Freshness Report)."""
    print(f"[ROLE 5] Building Freshness Report...")
    if df.empty:
        report = {"is_fresh": False, "total_rows": 0, "message": "Empty DataFrame"}
    else:
        latest_pub = str(df["published"].max())
        oldest_pub = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        total_rows = len(df)

        report = {
            "latest_published": latest_pub,
            "oldest_published": oldest_pub,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": (stale_rows == 0),
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"[CONSOLE TEST] Freshness: Latest={report.get('latest_published')} | Stale Rows={report.get('stale_rows')}")
    return report
