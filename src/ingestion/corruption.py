from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Giả lập tiêm lỗi mạnh mẽ (Strong Corruption) trực tiếp trên tập dữ liệu."""
    print(f"[ROLE 3] Simulating Strong Data Corruption on {len(df)} rows...")
    df_corrupted = df.copy()
    corruption_logs = []

    # 1. Xóa 3 bài báo chính thuộc tập Test Set (Làm suy giảm nghiêm trọng Retrieval Hit Rate)
    if len(df_corrupted) >= 8:
        dropped_indices = [1, 4, 7]
        dropped_ids = df_corrupted.iloc[dropped_indices]["paper_id"].tolist()
        df_corrupted = df_corrupted.drop(index=dropped_indices).reset_index(drop=True)
        corruption_logs.append({"type": "drop_key_testset_records", "details": f"Dropped IDs: {dropped_ids}"})

    # 2. Làm rỗng tóm tắt (Blank summary) trên nhiều bài báo
    for idx in [0, 2, 5]:
        if idx < len(df_corrupted):
            df_corrupted.loc[idx, "summary"] = ""
            corruption_logs.append({"type": "blank_summary", "paper_id": df_corrupted.loc[idx, "paper_id"]})

    # 3. Chèn nhiễu chữ rác ngẫu nhiên (Inject heavy noise)
    for idx in [1, 3]:
        if idx < len(df_corrupted):
            df_corrupted.loc[idx, "summary"] = "[SYSTEM ERROR 404 DATA CORRUPTED GARBAGE TEXT] " * 10
            df_corrupted.loc[idx, "authors_joined"] = "Unknown Corrupted Author"
            corruption_logs.append({"type": "inject_noise", "paper_id": df_corrupted.loc[idx, "paper_id"]})

    # 4. Truncate title (Cắt ngắn tiêu đề)
    if len(df_corrupted) >= 3:
        df_corrupted.loc[2, "title"] = df_corrupted.loc[2, "title"][:5]
        corruption_logs.append({"type": "truncate_title", "paper_id": df_corrupted.loc[2, "paper_id"]})

    # 5. Stale date (Đổi ngày về năm 2000)
    if len(df_corrupted) >= 4:
        df_corrupted.loc[3, "published"] = "2000-01-01"
        df_corrupted.loc[3, "age_days"] += 8000
        corruption_logs.append({"type": "stale_date", "paper_id": df_corrupted.loc[3, "paper_id"]})

    # 6. Add duplicate rows (Tạo nhiều hàng trùng lặp)
    if len(df_corrupted) >= 2:
        duplicate_rows = df_corrupted.iloc[[0, 2]]
        df_corrupted = pd.concat([df_corrupted, duplicate_rows], ignore_index=True)
        corruption_logs.append({"type": "add_duplicates", "paper_ids": duplicate_rows["paper_id"].tolist()})

    # Rebuild `text_for_embedding`
    df_corrupted["text_for_embedding"] = df_corrupted.apply(
        lambda r: f"Title: {r['title']}\nAuthors: {r['authors_joined']}\nCategories: {r['categories_joined']}\nSummary: {r['summary']}",
        axis=1
    )

    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump(corruption_logs, f, indent=2)

    print(f"[CONSOLE TEST] Strong Corruption completed. Total logs recorded: {len(corruption_logs)}")
    return df_corrupted
