from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Giả lập 6 dạng lỗi dữ liệu thực tế."""
    print(f"[ROLE 3] Simulating Data Corruption on {len(df)} rows...")
    df_corrupted = df.copy()
    corruption_logs = []

    # 1. Drop 3 bài báo mới nhất (Missing latest records)
    if len(df_corrupted) > 5:
        dropped_ids = df_corrupted.tail(3)["paper_id"].tolist()
        df_corrupted = df_corrupted.iloc[:-3].reset_index(drop=True)
        corruption_logs.append({"type": "drop_latest_records", "details": f"Dropped IDs: {dropped_ids}"})

    # 2. Blank summary
    if len(df_corrupted) >= 2:
        df_corrupted.loc[0, "summary"] = ""
        corruption_logs.append({"type": "blank_summary", "paper_id": df_corrupted.loc[0, "paper_id"]})

    # 3. Inject noise
    if len(df_corrupted) >= 3:
        df_corrupted.loc[2, "summary"] += " [SYSTEM ERROR 404 DATA CORRUPTED GARBAGE TEXT]"
        corruption_logs.append({"type": "inject_noise", "paper_id": df_corrupted.loc[2, "paper_id"]})

    # 4. Truncate title
    if len(df_corrupted) >= 4:
        df_corrupted.loc[3, "title"] = df_corrupted.loc[3, "title"][:10]
        corruption_logs.append({"type": "truncate_title", "paper_id": df_corrupted.loc[3, "paper_id"]})

    # 5. Stale date (Đổi ngày về năm 2000)
    if len(df_corrupted) >= 5:
        df_corrupted.loc[4, "published"] = "2000-01-01"
        df_corrupted.loc[4, "age_days"] += 8000
        corruption_logs.append({"type": "stale_date", "paper_id": df_corrupted.loc[4, "paper_id"]})

    # 6. Add duplicate row
    if len(df_corrupted) >= 1:
        duplicate_row = df_corrupted.iloc[[0]]
        df_corrupted = pd.concat([df_corrupted, duplicate_row], ignore_index=True)
        corruption_logs.append({"type": "add_duplicate", "paper_id": df_corrupted.loc[0, "paper_id"]})

    # Rebuild `text_for_embedding`
    df_corrupted["text_for_embedding"] = df_corrupted.apply(
        lambda r: f"Title: {r['title']}\nAuthors: {r['authors_joined']}\nCategories: {r['categories_joined']}\nSummary: {r['summary']}",
        axis=1
    )

    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump(corruption_logs, f, indent=2)

    print(f"[CONSOLE TEST] Corruption completed. Total logs recorded: {len(corruption_logs)}")
    return df_corrupted
