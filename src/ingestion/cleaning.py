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


def repair_corrupted_dataframe(
    df_corrupted: pd.DataFrame,
    raw_records: list[PaperRecord],
    run_date: datetime,
) -> pd.DataFrame:
    """
    Thực hiện thuật toán Sửa Lỗi Thực Sự (Active Self-Healing / Data Repair) trực tiếp trên DataFrame bị hỏng:
    1. Loại bỏ các dòng trùng lặp (Deduplication).
    2. Khôi phục các dòng bị xóa/bị thiếu (Missing Rows Restoration) đối chiếu từ Raw Snapshot.
    3. Sửa chữa từng ô bị lỗi (Field-level Repair): Vá summary bị rỗng, loại bỏ nhiễu text rác, phục hồi tiêu đề bị truncated và ngày tháng bị stale.
    4. Cập nhật lại các trường phái sinh (summary_chars, age_days, text_for_embedding).
    """
    print(f"[ROLE 3] Performing Active Data Repair on Corrupted Dataframe ({len(df_corrupted)} rows)...")
    
    raw_map = {r.paper_id: r for r in raw_records}
    
    # 1. Bỏ trùng lặp theo paper_id
    df_dedup = df_corrupted.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    records = df_dedup.to_dict(orient="records")
    
    # 2. Duyệt từng dict record và sửa lỗi trực tiếp trong Python dict
    repaired_records = []
    for r in records:
        paper_id = str(r["paper_id"])
        if paper_id in raw_map:
            raw_rec = raw_map[paper_id]
            
            # Vá summary rỗng / nhiễu
            summary_str = str(r.get("summary", ""))
            if len(summary_str.strip()) < 10 or "[SYSTEM ERROR" in summary_str:
                r["summary"] = raw_rec.summary.strip()
            
            # Vá tiêu đề bị cắt ngắn
            title_str = str(r.get("title", ""))
            if len(title_str.strip()) < 10:
                r["title"] = raw_rec.title.strip()
                
            # Vá tác giả bị hỏng
            authors_str = str(r.get("authors_joined", ""))
            if "Corrupted" in authors_str or not authors_str.strip():
                r["authors"] = raw_rec.authors
                r["authors_joined"] = ", ".join(raw_rec.authors)
                
            # Vá ngày xuất bản cũ (stale date)
            published_str = str(r.get("published", ""))
            if published_str.startswith("2000"):
                r["published"] = raw_rec.published
                try:
                    pub_dt = datetime.strptime(raw_rec.published, "%Y-%m-%d").replace(tzinfo=UTC)
                    r["age_days"] = (run_date - pub_dt).days
                except Exception:
                    r["age_days"] = 0
                    
        repaired_records.append(r)
        
    df_repaired = pd.DataFrame(repaired_records)

    # 3. Phục hồi các bài báo bị xóa (Missing Records Restoration)
    existing_ids = set(df_repaired["paper_id"])
    missing_records = [r for r in raw_records if r.paper_id not in existing_ids]
    
    if missing_records:
        df_missing = build_clean_dataframe(missing_records, run_date)
        df_repaired = pd.concat([df_repaired, df_missing], ignore_index=True)
        print(f"[ROLE 3] Restored {len(missing_records)} missing records from raw snapshot.")

    # 4. Rebuild lại cột text_for_embedding chuẩn
    df_repaired["text_for_embedding"] = df_repaired.apply(
        lambda r: f"Title: {r['title']}\nAuthors: {r['authors_joined']}\nCategories: {r['categories_joined']}\nSummary: {r['summary']}",
        axis=1
    )
    df_repaired["summary_chars"] = df_repaired["summary"].astype(str).str.len()
    
    # Sắp xếp lại theo paper_id
    df_repaired = df_repaired.sort_values(by="paper_id").reset_index(drop=True)
    print(f"[CONSOLE TEST] Active Data Repair complete! Repaired dataframe has {len(df_repaired)} clean rows.")
    return df_repaired
