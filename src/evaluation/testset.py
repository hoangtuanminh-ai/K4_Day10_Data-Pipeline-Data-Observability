from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd

def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Tạo bộ Evaluation Test Set cố định từ clean dataframe."""
    print(f"[ROLE 5] Generating Evaluation Test Set from {len(df)} documents...")
    if len(df) < 3:
        raise ValueError("[TEST LỖI] Dataset quá ngắn để tạo test set!")

    test_samples = []
    sample_df = df.head(10).reset_index(drop=True)

    for idx, row in sample_df.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        summary = row["summary"]
        authors = row["authors_joined"]
        published = row["published"]

        # Question type 1: Summary
        test_samples.append({
            "id": f"eval_summary_{idx}",
            "question_type": "summary",
            "question": f"What is the main summary/contribution of the paper '{title}'?",
            "ground_truth": summary,
            "ground_truth_doc_ids": [paper_id],
        })

        # Question type 2: Authors
        test_samples.append({
            "id": f"eval_authors_{idx}",
            "question_type": "authors",
            "question": f"Who are the authors of the paper titled '{title}'?",
            "ground_truth": f"The authors are {authors}.",
            "ground_truth_doc_ids": [paper_id],
        })

        # Question type 3: Published Date
        test_samples.append({
            "id": f"eval_date_{idx}",
            "question_type": "date",
            "question": f"When was the paper '{title}' published?",
            "ground_truth": f"It was published on {published}.",
            "ground_truth_doc_ids": [paper_id],
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_samples, f, ensure_ascii=False, indent=2)

    print(f"[CONSOLE TEST] Test set created: {len(test_samples)} questions -> Saved to {output_path}")
    return test_samples
