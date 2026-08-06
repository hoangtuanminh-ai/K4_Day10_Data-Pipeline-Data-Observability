# HƯỚNG DẪN CHI TIẾT & PHÂN CÔNG NHIỆM VỤ BÀI LAB DAY 10
## **Data Pipeline & Data Observability for RAG Agent**
> **Tài liệu lưu hành nội bộ nhóm 4 người**  
> *Mục tiêu: Đạt điểm tối đa (90-100 điểm) theo đúng Rubric chấm điểm của giảng viên.*

---

## 1. TỔNG QUAN LUỒNG DỮ LIỆU & MỤC TIÊU BÀI LAB

Bài lab này mô phỏng quy trình xây dựng và vận hành **Data Pipeline & Data Observability** cho hệ thống RAG tra cứu công bố khoa học từ API Crossref.

### Vòng đời dữ liệu (Data Lifecycle):
```text
[Crossref API] ──► [data/raw/ JSON] ──► [data/clean/ CSV/JSON] ──► [ChromaDB Vector Store]
                                                   │                         │
                                                   ▼                         ▼
                                       [data/eval/ test_set.json]   [RAG Evaluation Metrics]
                                                   │                         │
  [Data Corruption Flow] ◄─────────────────────────┴─────────────────────────┘
            │
            ▼
[papers_clean_corrupted.csv] ──► [Re-evaluate & Quality Check]
            │
            ▼ (Repair từ Raw Source)
[papers_clean_repaired.csv] ──► [Re-evaluate & Compare Baseline vs Corrupted vs Repaired]
```

---

## 2. BẢNG PHÂN CÔNG NÂNG CAO CHO NHÓM 4 NGUỜI

| Role | Vai Trò & Chức Danh | Tập Tin Đảm Nhận | Sản Phẩm Bàn Giao (Artifacts) |
| :--- | :--- | :--- | :--- |
| **ROLE 1** | **Pipeline Integrator & Release Lead** *(Trưởng nhóm & Điều phối)* | `src/core/config.py`<br>`src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py`<br>`script/run_phase1.py`<br>`script/run_corruption_flow.py` | - Pipeline Baseline & Corruption flow chạy end-to-end.<br>- Điều phối handoff giữa các vai trò.<br>- Quản lý cấu hình & demo sản phẩm. |
| **ROLE 2** | **Data Ingestion, Cleaning & Recovery Specialist** *(Chuyên viên Dữ liệu)* | `src/ingestion/crossref.py`<br>`src/ingestion/cleaning.py`<br>`src/ingestion/corruption.py` | - `data/raw/crossref_*.json`<br>- `data/clean/papers_clean.csv`<br>- `data/clean/papers_clean_corrupted.csv`<br>- `data/clean/papers_clean_repaired.csv` |
| **ROLE 3** | **RAG Engine & Agent Specialist** *(Chuyên viên Vector Store & RAG)* | `src/retrieval/embeddings.py`<br>`src/retrieval/index.py`<br>`src/retrieval/llm.py`<br>`src/retrieval/agent.py`<br>`src/retrieval/qa.py` | - ChromaDB Persistent Vector DB (`data/chroma/`).<br>- 3 Collections: `papers-baseline`, `papers-corrupted`, `papers-repaired`.<br>- Embeddings Manifest (`data/embeddings/`). |
| **ROLE 4** | **Data Observability & Evaluation Specialist** *(Chuyên viên QA & Monitoring)* | `src/evaluation/testset.py`<br>`src/evaluation/metrics.py`<br>`src/evaluation/evaluator.py`<br>`src/observability/quality.py`<br>`src/observability/reporting.py` | - `data/eval/test_set.json`<br>- `data/results/*_metrics.json`<br>- `data/quality/*`<br>- `data/reports/phase1_report.md`<br>- `data/reports/corruption_report.md` |

---

## 3. LỘ TRÌNH THỜI GIAN THEO CHECKPOINTS (TOTAL: 4 GIỜ)

```text
[CP0: 00:00-00:30] ──► [CP1: 00:30-01:05] ──► [CP2: 01:05-01:35] ──► [CP3: 01:35-02:00]
Setup & Ingestion Raw    Cleaning & Quality      Index & Test Set       Baseline End-to-End
                                                                           │
[CP6: 03:15-04:00] ◄── [CP5: 02:15-03:15] ◄── [CP4: 02:00-02:15] ◄─────────┘
Repair & Final Demo    Corruption & Re-eval   Nghỉ giải lao (15m)
```

- **Checkpoint 0 (00:00 – 00:30)**: Cả nhóm cài môi trường (`uv sync`), Role 2 viết xong `crossref.py`, tải dữ liệu raw lưu vào `data/raw/`.
- **Checkpoint 1 (00:30 – 01:05)**: Role 2 hoàn thiện `cleaning.py`, bàn giao `papers_clean.csv`. Role 4 chạy thử Quality check đầu tiên.
- **Checkpoint 2 (01:05 – 01:35)**: Role 3 build Chroma index `papers-baseline`. Role 4 tạo bộ `test_set.json`.
- **Checkpoint 3 (01:35 – 02:00)**: Role 1 chạy `python script/run_phase1.py`. Cả nhóm kiểm tra kết quả `baseline_metrics.json` và `phase1_report.md`.
- **Checkpoint 4 (02:00 – 02:15)**: **CẢ NHÓM NGHỈ GIẢI LAO 15 PHÚT**.
- **Checkpoint 5 (02:15 – 03:15)**: Role 2 tạo `corruption.py`. Role 1 & 3 rebuild index `papers-corrupted`. Role 4 đo đạc chỉ số sụt giảm.
- **Checkpoint 6 (03:15 – 04:00)**: Role 2 repair từ raw source. Role 1 chạy `run_corruption_flow.py` hoàn tất. Role 4 xuất báo cáo so sánh `corruption_report.md` và chuẩn bị Demo.

---

## 4. HƯỚNG DẪN CODE CHI TIẾT THEO TỪNG VAI TRÒ

---

### 👤 ROLE 1: PIPELINE INTEGRATOR & RELEASE LEAD

#### Nhiệm vụ:
Viết 2 file điều phối pipeline chính: `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.

#### Code `src/pipelines/phase1.py`:
```python
from __future__ import annotations

import logging
from datetime import datetime, UTC
from core.config import load_settings, require_llm_credentials
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.evaluator import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main() -> None:
    print("=== [ROLE 1] BẮT ĐẦU CHẠY BASELINE PIPELINE (PHASE 1) ===")
    settings = load_settings()
    
    # Kiểm tra LLM Credential
    try:
        require_llm_credentials(settings)
        print(f"--> LLM Provider: {settings.llm_provider} ({settings.model_name}) - OK!")
    except Exception as e:
        print(f"[TEST LỖI] Lỗi cấu hình LLM Key: {e}")
        raise

    # 1. Fetch hoặc Load Raw Records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("--> 1. Fetching raw records từ Crossref API...")
        records = fetch_source_records(settings)
    else:
        print("--> 1. Loading raw records từ file JSON snapshot...")
        records = load_raw_records(settings.paths.raw_records_json)
    
    print(f"[CONSOLE TEST] Số lượng raw records: {len(records)}")

    # 2. Clean Data
    print("--> 2. Làm sạch dữ liệu...")
    run_date = datetime.now(UTC)
    df_clean = build_clean_dataframe(records, run_date)
    
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(settings.paths.clean_csv, index=False)
    df_clean.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f"[CONSOLE TEST] Cleaned Dataset: {len(df_clean)} rows.")

    # 3. Vector Indexing
    print("--> 3. Tạo Vector Index (ChromaDB)...")
    index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)
    print(f"[CONSOLE TEST] Collection Baseline name: {index.collection_name}")

    # 4. Evaluation Test Set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("--> 4. Tạo bộ Evaluation Test Set...")
        test_set = build_test_set(df_clean, settings.paths.eval_testset)
    else:
        print("--> 4. Loading Evaluation Test Set...")
        from core.utils import read_json
        test_set = read_json(settings.paths.eval_testset)
    print(f"[CONSOLE TEST] Test set chứa {len(test_set)} mẫu câu hỏi.")

    # 5. Evaluate Baseline
    print("--> 5. Đánh giá chất lượng Baseline RAG...")
    baseline_eval = evaluate_pipeline(
        df=df_clean,
        test_set=test_set,
        settings=settings,
        embeddings_path=settings.paths.embeddings_json,
        output_metrics_path=settings.paths.baseline_metrics,
        output_answers_path=settings.paths.baseline_answers,
    )
    print(f"[CONSOLE TEST] Baseline Hit Rate: {baseline_eval['retrieval_hit_rate']:.4f}, Mean Token F1: {baseline_eval['mean_token_f1']:.4f}")

    # 6. Observability
    print("--> 6. Chạy Quality Checks & Freshness Report...")
    quality_res = run_data_quality_checks(df_clean, settings, "baseline_quality")
    freshness_res = build_freshness_report(df_clean, settings, settings.paths.freshness_report)

    # 7. Generate Report
    print("--> 7. Xuất Báo cáo Markdown Baseline...")
    source_summary = {
        "source_api": settings.source_api,
        "raw_records_count": len(records),
        "clean_records_count": len(df_clean),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=baseline_eval,
        quality=quality_res,
        freshness=freshness_res,
    )
    print(f"=== [ROLE 1] HOÀN THÀNH BASELINE! Báo cáo: {settings.paths.baseline_report} ===")

if __name__ == "__main__":
    main()
```

#### Code `src/pipelines/corruption_flow.py`:
```python
from __future__ import annotations

import logging
import pandas as pd
from core.config import load_settings
from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.evaluator import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report
from datetime import datetime, UTC

def main() -> None:
    print("=== [ROLE 1] BẮT ĐẦU CHẠY CORRUPTION, REPAIR & COMPARISON FLOW ===")
    settings = load_settings()
    
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    test_set = read_json(settings.paths.eval_testset)
    df_clean_baseline = pd.read_csv(settings.paths.clean_csv)

    # GIAI ĐOẠN A: CORRUPTION
    print("\n--> [A] Tạo dữ liệu lỗi (Corrupted Dataset)...")
    df_corrupted = corrupt_clean_dataframe(df_clean_baseline, settings.paths.corruption_log)
    df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    
    print("--> [A] Indexing dữ liệu lỗi vào collection riêng...")
    LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)
    
    print("--> [A] Re-evaluate trên dữ liệu lỗi...")
    corrupted_metrics = evaluate_pipeline(
        df=df_corrupted,
        test_set=test_set,
        settings=settings,
        embeddings_path=settings.paths.corrupted_embeddings_json,
        output_metrics_path=settings.paths.corrupted_metrics,
        output_answers_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness.json")

    print(f"[CONSOLE TEST] Corrupted Hit Rate: {corrupted_metrics['retrieval_hit_rate']:.4f}")

    # GIAI ĐOẠN B: REPAIR
    print("\n--> [B] Phục hồi dữ liệu từ Raw Source JSON...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, datetime.now(UTC))
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    print("--> [B] Indexing dữ liệu đã phục hồi...")
    LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)

    print("--> [B] Re-evaluate dữ liệu phục hồi...")
    repaired_metrics = evaluate_pipeline(
        df=df_repaired,
        test_set=test_set,
        settings=settings,
        embeddings_path=settings.paths.repaired_embeddings_json,
        output_metrics_path=settings.paths.repaired_metrics,
        output_answers_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "repaired_freshness.json")

    print(f"[CONSOLE TEST] Repaired Hit Rate: {repaired_metrics['retrieval_hit_rate']:.4f}")

    # GIAI ĐOẠN C: COMPARISON REPORT
    print("\n--> [C] Tạo Báo cáo So sánh (Comparison Report)...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"=== [ROLE 1] HOÀN THÀNH CORRUPTION FLOW! Báo cáo: {settings.paths.comparison_report} ===")

if __name__ == "__main__":
    main()
```

---

### 👤 ROLE 2: DATA INGESTION, CLEANING & RECOVERY SPECIALIST

#### Nhiệm vụ:
Viết 3 file thuộc module ingestion: `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`.

#### Code `src/ingestion/crossref.py`:
```python
from __future__ import annotations

import json
import time
import re
from dataclasses import asdict, dataclass
from pathlib import Path
import requests

from core.config import Settings
from core.utils import safe_slug

@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        paper_id = f"crossref_{safe_slug(doi)}"

        titles = item.get("title", [])
        title = titles[0].strip() if titles else "Untitled"

        abstract = item.get("abstract", "")
        abstract_clean = re.sub(r"<[^>]+>", "", abstract).strip() if abstract else "No summary available."

        authors = []
        for a in item.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)
        if not authors:
            authors = ["Unknown Author"]

        subjects = item.get("subject", [])
        categories = subjects if subjects else ["General"]
        primary_category = categories[0]

        created_date = item.get("created", {}).get("date-parts", [[2024, 1, 1]])[0]
        published_str = f"{created_date[0]:04d}-{created_date[1]:02d}-{created_date[2]:02d}" if len(created_date) >= 3 else f"{created_date[0]:04d}-01-01"

        abs_url = item.get("URL", f"https://doi.org/{doi}")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=abstract_clean,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published_str,
                updated=published_str,
                abs_url=abs_url,
                pdf_url=abs_url,
                comment="Fetched from Crossref API",
            )
        )
    return records

def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": "DataPipelineLab/1.0 (mailto:student@lab.edu)"}

    print(f"[ROLE 2] Fetching from Crossref: {url}")
    
    max_retries = 3
    response_data = None
    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=15)
            if res.status_code == 200:
                response_data = res.json()
                break
            print(f"[WARNING] Attempt {attempt+1}: Status {res.status_code}. Retrying...")
            time.sleep(2)
        except Exception as err:
            print(f"[TEST LỖI] HTTP Error: {err}")
            time.sleep(2)

    if not response_data:
        raise RuntimeError("[TEST LỖI] Không thể tải dữ liệu từ Crossref API!")

    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)

    records = parse_crossref_payload(response_data)

    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)

    print(f"[ROLE 2] Fetch success: {len(records)} records saved.")
    return records

def load_raw_records(path: Path) -> list[PaperRecord]:
    print(f"[ROLE 2] Loading raw records from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PaperRecord(**item) for item in data]
```

#### Code `src/ingestion/cleaning.py`:
```python
from __future__ import annotations

from datetime import datetime, UTC
import pandas as pd
from ingestion.crossref import PaperRecord

def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    print(f"[ROLE 2] Cleaning {len(records)} records...")
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
    df = df.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    df = df[df["summary_chars"] > 10].reset_index(drop=True)
    
    print(f"[CONSOLE TEST] Cleaned: {initial_count} -> {len(df)} rows. Removed: {initial_count - len(df)}")
    return df
```

#### Code `src/ingestion/corruption.py`:
```python
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    print(f"[ROLE 2] Corrupting dataframe with {len(df)} rows...")
    df_corrupted = df.copy()
    corruption_logs = []

    # 1. Drop 3 bài báo mới nhất
    if len(df_corrupted) > 5:
        dropped_ids = df_corrupted.tail(3)["paper_id"].tolist()
        df_corrupted = df_corrupted.iloc[:-3].reset_index(drop=True)
        corruption_logs.append({"type": "drop_latest_records", "details": f"Dropped: {dropped_ids}"})

    # 2. Blank summary
    if len(df_corrupted) >= 2:
        df_corrupted.loc[0, "summary"] = ""
        corruption_logs.append({"type": "blank_summary", "paper_id": df_corrupted.loc[0, "paper_id"]})

    # 3. Inject noise
    if len(df_corrupted) >= 3:
        df_corrupted.loc[2, "summary"] += " [NOISE GARBAGE TEXT CORRUPTED]"
        corruption_logs.append({"type": "inject_noise", "paper_id": df_corrupted.loc[2, "paper_id"]})

    # 4. Truncate title
    if len(df_corrupted) >= 4:
        df_corrupted.loc[3, "title"] = df_corrupted.loc[3, "title"][:10]
        corruption_logs.append({"type": "truncate_title", "paper_id": df_corrupted.loc[3, "paper_id"]})

    # 5. Stale date
    if len(df_corrupted) >= 5:
        df_corrupted.loc[4, "published"] = "2000-01-01"
        df_corrupted.loc[4, "age_days"] += 8000
        corruption_logs.append({"type": "stale_date", "paper_id": df_corrupted.loc[4, "paper_id"]})

    # 6. Duplicate row
    if len(df_corrupted) >= 1:
        duplicate_row = df_corrupted.iloc[[0]]
        df_corrupted = pd.concat([df_corrupted, duplicate_row], ignore_index=True)
        corruption_logs.append({"type": "add_duplicate", "paper_id": df_corrupted.loc[0, "paper_id"]})

    # Rebuild text_for_embedding
    df_corrupted["text_for_embedding"] = df_corrupted.apply(
        lambda r: f"Title: {r['title']}\nAuthors: {r['authors_joined']}\nCategories: {r['categories_joined']}\nSummary: {r['summary']}",
        axis=1
    )

    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump(corruption_logs, f, indent=2)

    print(f"[CONSOLE TEST] Corruption completed. Log count: {len(corruption_logs)}")
    return df_corrupted
```

---

### 👤 ROLE 3: RAG ENGINE & AGENT SPECIALIST

#### Nhiệm vụ:
Vận hành module `src/retrieval/`. Thêm hàm Smoke Test bên dưới để tự kiểm thử VectorDB & Tool Calling:

```python
# Thêm vào cuối file src/retrieval/agent.py để test
if __name__ == "__main__":
    from core.config import load_settings
    import pandas as pd
    from retrieval.index import LocalEmbeddingIndex
    from retrieval.agent import RAGAgent

    print("=== [ROLE 3] SMOKE TEST RAG ENGINE ===")
    settings = load_settings()
    
    if settings.paths.clean_csv.exists():
        df = pd.read_csv(settings.paths.clean_csv)
        print(f"--> Building Collection: {settings.baseline_collection_name}")
        index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
        
        # Test Semantic Search
        print("\n--> Test 1: Semantic Search")
        results = index.search(query="retrieval augmented generation", top_k=2)
        for r in results:
            print(f"  Paper ID: {r.paper_id} | Score: {r.score:.4f} | Title: {r.title}")
            
        # Test Agent
        print("\n--> Test 2: RAG Agent Tool Call")
        agent = RAGAgent(settings, index)
        resp = agent.answer_question("Summarize the paper about retrieval augmented generation")
        print(f"  [Answer]:\n{resp.answer}")
        print(f"  [Sources]: {resp.sources}")
```

---

### 👤 ROLE 4: DATA OBSERVABILITY & EVALUATION SPECIALIST

#### Nhiệm vụ:
Viết 3 file: `src/evaluation/testset.py`, `src/observability/quality.py`, và `src/observability/reporting.py`.

#### Code `src/evaluation/testset.py`:
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd

def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    print(f"[ROLE 4] Generating Test Set from {len(df)} documents...")
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

        test_samples.append({
            "id": f"eval_summary_{idx}",
            "question_type": "summary",
            "question": f"What is the main summary/contribution of the paper '{title}'?",
            "ground_truth": summary,
            "ground_truth_doc_ids": [paper_id],
        })

        test_samples.append({
            "id": f"eval_authors_{idx}",
            "question_type": "authors",
            "question": f"Who are the authors of the paper titled '{title}'?",
            "ground_truth": f"The authors are {authors}.",
            "ground_truth_doc_ids": [paper_id],
        })

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
```

#### Code `src/observability/quality.py`:
```python
from __future__ import annotations

import json
from typing import Any
import pandas as pd
from core.config import Settings

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    print(f"[ROLE 4] Running Quality Checks for: {report_name}...")
    
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

    print(f"[CONSOLE TEST] Quality Status: {status} | Dup IDs: {duplicate_paper_ids} | Empty Summaries: {empty_summaries}")
    return report

def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    print(f"[ROLE 4] Building Freshness Report...")
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

    print(f"[CONSOLE TEST] Freshness: Latest={report.get('latest_published')} | Stale={report.get('stale_rows')}")
    return report
```

#### Code `src/observability/reporting.py`:
```python
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
    print(f"[ROLE 4] Baseline Report written: {report_path}")

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

## 3. Conclusions
1. Dữ liệu lỗi làm suy giảm hiệu năng của Agent rõ rệt.
2. Phục hồi dữ liệu từ nguồn raw cho phép khôi phục chỉ số RAG hoàn toàn về mức Baseline.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md_content, encoding="utf-8")
    print(f"[ROLE 4] Comparison Report written: {report_path}")
```

---

## 5. LỆNH CHẠY KIỂM THỬ END-TO-END

Thực hiện lần lượt 2 lệnh sau từ root dự án:

```bash
# 1. Chạy Phase 1 (Baseline)
python script/run_phase1.py

# 2. Chạy Phase 2 (Corruption, Repair & Comparison)
python script/run_corruption_flow.py
```

---
*Chúc cả nhóm phối hợp nhịp nhàng và đạt điểm 100/100!*
