from __future__ import annotations

import logging
import sys
from datetime import datetime, UTC
import pandas as pd

from core.config import load_settings, require_llm_credentials
from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report

# Cấu hình logging hệ thống
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("CorruptionFlowPipeline")

# Cấu hình mã hóa UTF-8 cho stdout trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def main() -> None:
    """
    HÀM CHÍNH ĐIỀU PHỐI CORRUPTION, REPAIR & COMPARISON FLOW - ROLE 1
    
    Quy trình điều phối 3 giai đoạn chính:
    1. Giai đoạn A (Corruption Flow):
       - Nạp baseline clean dataset và metrics từ Phase 1
       - Gọi Role 3 (Corruption) để tạo dữ liệu lỗi (papers_clean_corrupted.csv)
       - Gọi Role 4 (Vector Store) để index collection mới (papers-corrupted)
       - Gọi Role 5 (Evaluation & Observability) để re-evaluate dữ liệu lỗi
    2. Giai đoạn B (Repair Flow):
       - Gọi Role 2 & 3 (Repair) nạp lại raw json snapshot để rebuild clean dataset (papers_clean_repaired.csv)
       - Gọi Role 4 (Vector Store) để index collection mới (papers-repaired)
       - Gọi Role 5 (Evaluation & Observability) để re-evaluate dữ liệu phục hồi
    3. Giai đoạn C (Comparison Reporting):
       - Gọi Role 5 (Reporting) để xuất báo cáo so sánh Baseline vs Corrupted vs Repaired
    """
    print("\n==================================================================")
    print("=== [ROLE 1] BẮT ĐẦU CHẠY CORRUPTION, REPAIR & COMPARISON FLOW ===")
    print("==================================================================\n")

    # BƯỚC 1: NẠP CẤU HÌNH VÀ KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT (BASELINE)
    print("--> [BƯỚC 1/8] Nạp cấu hình settings và kiểm tra Baseline Artifacts...")
    settings = load_settings()
    
    try:
        require_llm_credentials(settings)
    except Exception as exc:
        print(f"    [TEST LỖI - CRITICAL] Cấu hình LLM API Key thất bại: {exc}")
        sys.exit(1)

    # Đảm bảo Baseline (Phase 1) đã chạy thành công trước đó
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_csv.exists():
        print(f"    [TEST LỖI - CRITICAL] Thiếu Baseline Artifacts!")
        print(f"      - Missing: '{settings.paths.baseline_metrics}' hoặc '{settings.paths.clean_csv}'")
        print("    [GỢI Ý]: Hãy chạy Baseline Pipeline (python script/run_phase1.py) trước khi chạy Corruption Flow!")
        sys.exit(1)

    try:
        baseline_metrics = read_json(settings.paths.baseline_metrics)
        test_set = read_json(settings.paths.eval_testset)
        df_clean_baseline = pd.read_csv(settings.paths.clean_csv)
        print(f"    [OK] Nạp Baseline Metrics thành công. Baseline Hit Rate: {baseline_metrics.get('retrieval_hit_rate', 0):.4f}")
    except Exception as e:
        print(f"    [TEST LỖI] Lỗi đọc file Artifacts Baseline: {e}")
        return

    # ------------------------------------------------------------------
    # GIAI ĐOẠN A: CORRUPTION FLOW (GIẢ LẬP LỖI DỮ LIỆU & ĐÁNH GIÁ IMPACT)
    # ------------------------------------------------------------------
    print("\n--> [BƯỚC 2/8] [GIAI ĐOẠN A] Gọi Module Corruption (Role 3) để tạo dữ liệu lỗi...")
    try:
        df_corrupted = corrupt_clean_dataframe(df_clean_baseline, settings.paths.corruption_log)
        df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
        df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
        print(f"    [CONSOLE TEST - ROLE 3 CHECK] Tạo Corrupted Dataset ({len(df_corrupted)} hàng). Saved to '{settings.paths.corrupted_clean_csv}'.")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module Corruption chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 3]: Cần Role 3 triển khai hàm 'corrupt_clean_dataframe' trong 'src/ingestion/corruption.py'.")
        return

    print("\n--> [BƯỚC 3/8] [GIAI ĐOẠN A] Gọi Vector Store (Role 4) để Index Collection 'papers-corrupted'...")
    try:
        LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)
        print(f"    [CONSOLE TEST - ROLE 4 CHECK] Index Collection '{settings.corrupted_collection_name}' thành công.")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 4] Lỗi Index Corrupted Dataset: {e}")
        return

    print("\n--> [BƯỚC 4/8] [GIAI ĐOẠN A] Gọi Module Evaluation & Observability (Role 5) trên Corrupted Data...")
    try:
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
        
        hit_drop = baseline_metrics.get("retrieval_hit_rate", 0) - corrupted_metrics.get("retrieval_hit_rate", 0)
        f1_drop = baseline_metrics.get("mean_token_f1", 0) - corrupted_metrics.get("mean_token_f1", 0)
        print(f"    [CONSOLE TEST - IMPACT CORRUPTION RESULTS]:")
        print(f"      - Baseline Hit Rate  : {baseline_metrics.get('retrieval_hit_rate', 0):.4f}  ---> Corrupted Hit Rate : {corrupted_metrics.get('retrieval_hit_rate', 0):.4f} (Giảm: {hit_drop:.4f})")
        print(f"      - Baseline Token F1  : {baseline_metrics.get('mean_token_f1', 0):.4f}  ---> Corrupted Token F1 : {corrupted_metrics.get('mean_token_f1', 0):.4f} (Giảm: {f1_drop:.4f})")
        print(f"      - Quality Gate Status: '{corrupted_quality.get('status')}'")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 5] Lỗi khi đánh giá Corrupted Pipeline: {e}")
        return

    # ------------------------------------------------------------------
    # GIAI ĐOẠN B: REPAIR FLOW (PHỤC HỒI DỮ LIỆU TỪ RAW SOURCE & ĐÁNH GIÁ LẠI)
    # ------------------------------------------------------------------
    print("\n--> [BƯỚC 5/8] [GIAI ĐOẠN B] Gọi Module Ingestion & Cleaning (Role 2 & 3) để Repair từ Raw Source...")
    try:
        raw_records = load_raw_records(settings.paths.raw_records_json)
        df_repaired = build_clean_dataframe(raw_records, datetime.now(UTC))
        df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
        df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
        print(f"    [CONSOLE TEST - REPAIR CHECK] Phục hồi xong {len(df_repaired)} hàng từ Raw JSON. Saved to '{settings.paths.repaired_clean_csv}'.")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 2/3] Lỗi trong quá trình Repair Data từ Raw Source: {e}")
        return

    print("\n--> [BƯỚC 6/8] [GIAI ĐOẠN B] Gọi Vector Store (Role 4) để Index Collection 'papers-repaired'...")
    try:
        LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)
        print(f"    [CONSOLE TEST - ROLE 4 CHECK] Index Collection '{settings.repaired_collection_name}' thành công.")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 4] Lỗi Index Repaired Dataset: {e}")
        return

    print("\n--> [BƯỚC 7/8] [GIAI ĐOẠN B] Gọi Evaluation & Observability (Role 5) trên Repaired Data...")
    try:
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
        
        hit_recover = repaired_metrics.get("retrieval_hit_rate", 0) - corrupted_metrics.get("retrieval_hit_rate", 0)
        print(f"    [CONSOLE TEST - RECOVERY RESULTS]:")
        print(f"      - Corrupted Hit Rate : {corrupted_metrics.get('retrieval_hit_rate', 0):.4f}  ---> Repaired Hit Rate  : {repaired_metrics.get('retrieval_hit_rate', 0):.4f} (Tăng/Phục hồi: +{hit_recover:.4f})")
        print(f"      - Repaired Quality Status: '{repaired_quality.get('status')}'")
    except Exception as e:
        print(f"    [TEST LỖI - ROLE 5] Lỗi khi đánh giá Repaired Pipeline: {e}")
        return

    # ------------------------------------------------------------------
    # GIAI ĐOẠN C: COMPARISON REPORTING (XUẤT BÁO CÁO SO SÁNH 3 TRẠNG THÁI)
    # ------------------------------------------------------------------
    print("\n--> [BƯỚC 8/8] [GIAI ĐOẠN C] Gọi Reporting (Role 5) để tổng hợp Báo cáo So sánh Markdown...")
    try:
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
        print(f"    [CONSOLE TEST - REPORT CHECK] Đã xuất file Báo cáo So sánh tại: '{settings.paths.comparison_report}'")
    except NotImplementedError as e:
        print(f"    [TEST LỖI - BLOCKER] Module Reporting (Corruption) chưa hoàn thiện: {e}")
        print("    [ĐỜI ROLE 5]: Cần Role 5 triển khai 'generate_corruption_report' trong 'src/observability/reporting.py'.")
        return

    print("\n==================================================================")
    print("=== [ROLE 1 SUCCESS] HOÀN THÀNH CORRUPTION & REPAIR FLOW THÀNH CÔNG! ===")
    print("==================================================================\n")

if __name__ == "__main__":
    main()

