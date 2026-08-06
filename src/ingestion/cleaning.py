from __future__ import annotations

from datetime import datetime, UTC
import pandas as pd
from ingestion.crossref import PaperRecord

def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Làm sạch và chuyển đổi danh sách PaperRecord thành Pandas DataFrame."""
    print(f"[ROLE 3] Cleaning {len(records)} raw records...")
    rows = []
    
    for r in records:
        title_clean = r.title.strip()
        summary_clean = r.summary.strip()
        authors_joined = ", ".join(r.authors)
        categories_joined = ", ".join(r.categories)
        
        try:
            pub_dt = datetime.strptime(r.published, "%Y-%m-%d").replace(tzinfo=UTC)
            age_days = (run_date - pub_dt).days
        except Exception:
            age_days = 0

        # Cột tổng hợp dùng làm đầu vào cho Vector Embedding
        text_for_embedding = f"Title: {title_clean}\nAuthors: {authors_joined}\nCategories: {categories_joined}\nSummary: {summary_clean}"

        rows.append({
            "paper_id": r.paper_id,
            "title": title_clean,
            "summary": summary_clean,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary_clean),
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(rows)
    initial_count = len(df)
    
    # Bỏ trùng lặp theo paper_id và lọc các bản ghi rỗng
    df = df.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    df = df[df["summary_chars"] > 10].reset_index(drop=True)
    
    print(f"[CONSOLE TEST] Clean summary: Input={initial_count} -> Output={len(df)} rows. Drop count={initial_count - len(df)}")
    return df
