from __future__ import annotations

import logging
import sys
from datetime import datetime, UTC
import pandas as pd

from core.config import load_settings, require_llm_credentials
from core.utils import read_json
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report

# Cấu hình logging hệ thống phục vụ việc debug và theo dõi tiến trình
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("Phase1Pipeline")

# Cấu hình mã hóa UTF-8 cho stdout trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main() -> None:
    """
    HÀM CHÍNH ĐIỀU PHỐI BASELINE PIPELINE (PHASE 1) - ROLE 1
    
    Quy trình điều phối 7 bước end-to-end:
    1. Kiểm tra cấu hình hệ thống & API Key (.env)
    2. Gọi Role 2 (Ingestion) để fetch/load raw records
    3. Gọi Role 3 (Cleaning) để làm sạch và chuẩn hóa schema dữ liệu
    4. Gọi Role 4 (Vector Store) để build ChromaDB Vector Index (Collection: papers-baseline)
    5. Gọi Role 5 (Evaluation) để tạo/load test set và đánh giá chất lượng RAG Baseline
    6. Gọi Role 5 (Observability) để chạy Data Quality Checks & Freshness Report
    7. Gọi Role 5 (Reporting) để xuất báo cáo Markdown Phase 1
    """
    print("\n==================================================================")
    print("=== [ROLE 1] BẮT ĐẦU CHẠY THỬ BASELINE PIPELINE (PHASE 1) ===")
    print("==================================================================\n")
    
    # BƯỚC 1: CẤU HÌNH & KIỂM TRA CREDENTIALS
    print("--> [BƯỚC 1/7] Nạp cấu hình settings và kiểm tra LLM Credentials...")
    settings = load_settings()
    
    try:
        require_llm_credentials(settings)
        print(f"    [OK] Cấu hình LLM Provider: '{settings.llm_provider}' | Model: '{settings.model_name}'")
    except Exception as exc:
        print(f"    [TEST LỖI - CRITICAL] Cấu hình API Key thất bại: {exc}")
        print("    [GỢI Ý]: Hãy tạo file .env từ .env.example và điền API key phù hợp.")
        sys.exit(1)

    # BƯỚC 2: DATA INGESTION (HOÀN THÀNH BỞI ROLE 2)
    print("\n--> [BƯỚC 2/7] Gọi Module Ingestion (Role 2) để thu thập Raw Data...")
    try:
        if settings.refresh_source or not settings.paths.raw_records_json.exists():
            print(f"    [FETCH] Đang tải dữ liệu thực tế từ Crossref API (Query: '{settings.source_query}')...")
            records = fetch_source_records(settings)
        else:
            print(f"    [LOAD] Đang nạp dữ liệu snapshot từ file: {settings.paths.raw_records_json}")
            records = load_raw_records(settings.paths.raw_records_json)
        print(f"    [CONSOLE TEST - ROLE 2 CHECK] Nạp thành công {len(records)} raw paper records.")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module Ingestion chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 2]: Cần Role 2 triển khai các hàm 'fetch_source_records' và 'parse_crossref_payload' trong 'src/ingestion/crossref.py'.")
        return
    except Exception as e:
        print(f"    [TEST LỖI - UNEXPECTED] Lỗi khi nạp dữ liệu Raw: {e}")
        return

    # BƯỚC 3: DATA CLEANING & MODELING (HOÀN THÀNH BỞI ROLE 3)
    print("\n--> [BƯỚC 3/7] Gọi Module Cleaning (Role 3) để chuẩn hóa Data Schema...")
    try:
        run_date = datetime.now(UTC)
        df_clean = build_clean_dataframe(records, run_date)
        
        # Ghi các file Artifacts dữ liệu sạch ra thư mục data/clean/
        settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_csv(settings.paths.clean_csv, index=False)
        df_clean.to_json(settings.paths.clean_json, orient="records", indent=2)
        print(f"    [CONSOLE TEST - ROLE 3 CHECK] Dữ liệu sạch: {len(df_clean)} hàng. Đã lưu vào '{settings.paths.clean_csv}'.")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module Cleaning chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 3]: Cần Role 3 triển khai hàm 'build_clean_dataframe' trong 'src/ingestion/cleaning.py'.")
        return

    # BƯỚC 4: VECTOR INDEXING (HOÀN THÀNH BỞI ROLE 4)
    print("\n--> [BƯỚC 4/7] Gọi Module Vector Store (Role 4) để tạo ChromaDB Vector Index...")
    try:
        index = LocalEmbeddingIndex.build(df_clean, settings, settings.paths.embeddings_json)
        print(f"    [CONSOLE TEST - ROLE 4 CHECK] Index Baseline thành công. Collection name: '{index.collection_name}'.")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 4] Lỗi khi tạo Chroma Index: {e}")
        return

    # BƯỚC 5: EVALUATION TEST SET & METRICS (HOÀN THÀNH BỞI ROLE 5)
    print("\n--> [BƯỚC 5/7] Gọi Module Evaluation (Role 5) để tạo Test Set và Chấm điểm RAG...")
    try:
        if settings.refresh_test_set or not settings.paths.eval_testset.exists():
            print("    [CREATE] Đang khởi tạo bộ Evaluation Test Set mới từ clean dataset...")
            test_set = build_test_set(df_clean, settings.paths.eval_testset)
        else:
            print(f"    [LOAD] Đang nạp Evaluation Test Set từ file: {settings.paths.eval_testset}")
            test_set = read_json(settings.paths.eval_testset)
        print(f"    [CONSOLE TEST - ROLE 5 CHECK] Test set sẵn sàng với {len(test_set)} mẫu câu hỏi.")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module TestSet chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 5]: Cần Role 5 triển khai hàm 'build_test_set' trong 'src/evaluation/testset.py'.")
        return

    # Đánh giá RAG Baseline
    try:
        print("    [EVALUATE] Đang thực thi đo đạc các chỉ số Hit Rate, Token F1, LLM Judge Score...")
        baseline_eval = evaluate_pipeline(
            df=df_clean,
            test_set=test_set,
            settings=settings,
            embeddings_path=settings.paths.embeddings_json,
            output_metrics_path=settings.paths.baseline_metrics,
            output_answers_path=settings.paths.baseline_answers,
        )
        print(f"    [CONSOLE TEST - METRICS BASELINE RESULTS]:")
        print(f"      - Retrieval Hit Rate : {baseline_eval.get('retrieval_hit_rate', 0):.4f}")
        print(f"      - Mean Token F1      : {baseline_eval.get('mean_token_f1', 0):.4f}")
        print(f"      - LLM Judge Accuracy : {baseline_eval.get('judge_accuracy', 0):.4f}")
        print(f"      - Mean Judge Score   : {baseline_eval.get('mean_judge_score', 0):.4f}")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 5] Lỗi trong quá trình Evaluate RAG Pipeline: {e}")
        return

    # BƯỚC 6: OBSERVABILITY (QUALITY CHECKS & FRESHNESS) (HOÀN THÀNH BỞI ROLE 5)
    print("\n--> [BƯỚC 6/7] Gọi Module Observability (Role 5) để kiểm tra Data Quality & Freshness...")
    try:
        quality_res = run_data_quality_checks(df_clean, settings, "baseline_quality")
        freshness_res = build_freshness_report(df_clean, settings, settings.paths.freshness_report)
        print(f"    [CONSOLE TEST - OBSERVABILITY CHECK]: Quality Status = '{quality_res.get('status')}' | Is Fresh = {freshness_res.get('is_fresh')}")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module Quality/Freshness chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 5]: Cần Role 5 triển khai 'run_data_quality_checks' & 'build_freshness_report' trong 'src/observability/quality.py'.")
        return

    # BƯỚC 7: REPORTING (HOÀN THÀNH BỞI ROLE 5)
    print("\n--> [BƯỚC 7/7] Gọi Module Reporting (Role 5) để tổng hợp Phase 1 Markdown Report...")
    try:
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
        print(f"    [CONSOLE TEST - REPORT CHECK] Đã xuất file báo cáo Baseline tại: '{settings.paths.baseline_report}'")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module Reporting chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 5]: Cần Role 5 triển khai 'generate_phase1_report' trong 'src/observability/reporting.py'.")
        return

    print("\n==================================================================")
    print("=== [ROLE 1 SUCCESS] HOÀN THÀNH BASELINE PIPELINE THÀNH CÔNG! ===")
    print("==================================================================\n")

if __name__ == "__main__":
    main()

