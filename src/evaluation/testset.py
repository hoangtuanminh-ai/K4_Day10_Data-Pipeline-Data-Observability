from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic, corpus-grounded evaluation set.

    The questions deliberately quote the exact paper title.  This lets the
    retrieval layer exercise both semantic retrieval and its exact-title
    lookup path, while every answer remains verifiable from one clean row.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "published",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Cannot build test set; missing columns: {', '.join(missing_columns)}")

    candidates = df.copy()
    candidates["title"] = candidates["title"].fillna("").map(normalize_whitespace)
    candidates["summary"] = candidates["summary"].fillna("").map(normalize_whitespace)
    candidates = candidates[
        candidates["paper_id"].notna()
        & candidates["title"].ne("")
        & candidates["summary"].ne("")
    ].drop_duplicates(subset=["paper_id"])

    if len(candidates) < 3:
        raise ValueError("Need at least three valid, unique documents to build an evaluation set.")

    # Stable ordering makes baseline/corrupted/repaired comparisons reproducible.
    candidates = candidates.sort_values(["published", "paper_id"], ascending=[False, True]).head(8)
    samples: list[dict[str, Any]] = []

    for row_number, (_, row) in enumerate(candidates.iterrows(), start=1):
        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors = normalize_whitespace(str(row["authors_joined"]))
        categories = normalize_whitespace(str(row["categories_joined"]))
        published = str(row["published"])

        # Keep references aligned with retrieval.qa._extract_answer().
        question_specs = [
            ("summary", f"What is the main contribution of the paper '{title}'?", first_sentence(summary)),
            ("authors", f"Who authored the paper '{title}'?", authors),
            ("date", f"When was the paper '{title}' published?", published),
            ("categories", f"What categories does the paper '{title}' belong to?", categories),
        ]
        for question_type, question, ground_truth in question_specs:
            samples.append(
                {
                    "id": f"{question_type}_{row_number:02d}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    write_json(output_path, samples)
    return samples
