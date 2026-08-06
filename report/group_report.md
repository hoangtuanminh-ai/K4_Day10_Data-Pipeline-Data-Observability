# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B2-2     |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Hoàng Tuấn Minh | 2A202601500 | Pipeline Integrator & Release Lead | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| 2 | Lê Văn Tuấn | 2A202601016 | Data Ingestion & Raw Lineage Specialist | `src/ingestion/crossref.py` |
| 3 | Vũ Hoàng Việt | 2A202601250 | Data Cleaning, Corruption & Recovery Specialist | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` |
| 4 | Cao Hương Giang | 2A202601420 | RAG Engine & Vector Store Specialist | `src/retrieval/index.py`, `src/retrieval/agent.py` |
| 5 | Hoàng Trường Giang | 2A202601224 | Data Observability & Evaluation Specialist | `src/evaluation/testset.py`, `src/observability/quality.py`, `src/observability/reporting.py` |

## 2. Tóm tắt kết quả

Nhóm B2-2 đã hoàn thành toàn bộ các checkpoint của luồng Data Pipeline & Data Observability theo yêu cầu bài Lab. Baseline pipeline chạy ổn định, tự động tải dữ liệu từ Crossref API, làm sạch, vector hóa vào ChromaDB và đánh giá đạt kết quả tốt với Retrieval Hit Rate 1.0. Các artifact quan trọng được tạo ra đầy đủ gồm: dữ liệu raw, clean, embeddings index, test set và các báo cáo chất lượng, đánh giá (phase1_report).

Khi mô phỏng Corruption, các lỗi như xóa record thuộc test set, làm rỗng summary, inject noise và duplicate dữ liệu đã gây ảnh hưởng nghiêm trọng tới Retrieval Hit Rate (giảm từ 1.0 xuống 0.6) và làm Quality Status chuyển thành FAILED (2 duplicate, 5 empty summaries). Tuy nhiên, luồng Repair đã khôi phục lại dữ liệu thành công từ file raw snapshot, đưa các chỉ số đánh giá RAG về lại mốc ban đầu (Hit Rate = 1.0, Quality Status: PASSED). Blocker lớn nhất trong quá trình là đảm bảo tính nhất quán của ID và index vector khi dữ liệu cập nhật lại.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API | Fetch records từ API, lưu raw JSON | `data/raw/` | Lê Văn Tuấn |
| Cleaning          | Raw records JSON | Chuẩn hóa format, lọc null, ghép strings | `data/clean/` | Vũ Hoàng Việt |
| Embedding/index   | Cleaned CSV | ChromaDB Vector Store indexing | `data/chroma/`, `data/embeddings/` | Cao Hương Giang |
| Evaluation        | Cleaned CSV | Xây dựng Test set, tính RAG metrics | `data/eval/test_set.json` | Hoàng Trường Giang |
| Observability     | Cleaned CSV | Data Quality và Freshness checks | `data/quality/` | Hoàng Trường Giang |
| Corruption/repair | Cleaned CSV / Raw JSON | Giả lập lỗi dữ liệu và phục hồi từ Raw | `data/results/corruption_log.json` | Vũ Hoàng Việt |
| Orchestration     | Toàn bộ code | Điều phối chạy các pipeline tự động | Reports ở `data/reports/` | Hoàng Tuấn Minh |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | openai (hoặc gemini) |
| `LLM_MODEL`                | gpt-4o-mini (hoặc tương đương) |
| Embedding model              | all-MiniLM-L6-v2         |
| Số lượng Crossref records | Tối đa 24 records         |
| Retrieval`top_k`           | 2         |
| Freshness threshold          | 180 days         |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:
```bash
python script/run_phase1.py
```

Corruption flow:
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 | `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06 | `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API |
| Query/filter                | "retrieval augmented generation" |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Thử tối đa 3 lần, delay 2s |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| paper_id | str | Có | ID chuẩn hóa từ DOI | Bỏ qua record nếu DOI trống |
| title | str | Có | Tiêu đề bài báo | Để 'Untitled' nếu không có |
| summary | str | Không | Abstract bài báo | Lọc bỏ nếu độ dài < 10 ký tự |
| authors | list[str] | Không | Tác giả | Để 'Unknown Author' |
| published | str | Có | Ngày xuất bản | Mặc định năm '2024-01-01' |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Lọc bỏ record có summary < 10 char | Completeness  | 0 (ở Baseline) | File log khi chạy script |
| Bỏ trùng lặp `paper_id` | Uniqueness | 0 (ở Baseline) | Quality report `baseline_quality.json` |

Cách nhóm tạo `text_for_embedding`, document ID và `age_days`:
- `text_for_embedding`: Ghép nối chuỗi định dạng: "Title: {title}\nAuthors: {authors}\nCategories: {categories}\nSummary: {summary}".
- Document ID: Từ trường `DOI` trong response của Crossref, chuẩn hóa slug thành `crossref_...`.
- `age_days`: Hiệu số số ngày giữa thời điểm chạy hiện tại (run_date) và ngày published.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | Tùy số lượng record đầu (tạo 3 câu hỏi cho mỗi bài báo, khoảng 30 câu hỏi) |
| Các`question_type`                    | summary, authors, date |
| Ground-truth document ID                 | Mảng chứa `paper_id` gốc |
| Embedding model                          | all-MiniLM-L6-v2 |
| Vector store/collection                  | ChromaDB |
| Retrieval`top_k`                       | 2 |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:
Giữ nguyên Test set đảm bảo tính công bằng và có cơ sở so sánh (benchmark) chính xác. Nếu Test set thay đổi, sự sụt giảm metric có thể do câu hỏi khó hơn chứ không phải do dữ liệu bị hỏng.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | Đã được parse thành record list |
| Cleaned dataset          | `data/clean/`                        | Có | Gồm cả .csv và .json |
| Embedding manifest/index | `data/embeddings/`                   | Có | Có thư mục Chroma và JSON manifest |
| Evaluation set           | `data/eval/`                         | Có | Chứa test_set.json |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Kết quả đánh giá model |
| Quality/freshness        | `data/quality/`                      | Có | Các file JSON reports |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Báo cáo Markdown tổng quan |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0000 | Tỷ lệ số lần truy xuất đúng doc ID chứa thông tin (100%) |
| `mean_token_f1`      |     0.0986 | Độ tương đồng F1 (khá thấp do câu trả lời từ LLM sinh ra có thể diễn đạt khác ground-truth, nhưng đủ mang ý nghĩa) |
| `judge_accuracy`     |     N/A | (Không có sẵn trong report) |
| `mean_judge_score`   |     2.7000 | Điểm do LLM làm giám khảo đánh giá (trên 3 hoặc 5 tùy prompt) |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| Không duplicate | Uniqueness | 0 | Pass (0 duplicate) | `baseline_quality.json` |
| Không empty summary | Completeness | 0 | Pass (0 empty) | `baseline_quality.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.csv` |
| Timestamp mới nhất       | 2026-08-05 |
| Ngưỡng freshness         | 180 days |
| Trạng thái baseline      | False (Stale) |
| Lý do                     | Có ít nhất 1 bài báo vượt quá 180 ngày so với hiện tại. |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop key testset records | Xóa các record thuộc test set | 3 | Retrieval giảm | Hit rate giảm xuống 0.6 | Parse lại raw snapshot |
| Blank summary | Thay summary = "" | 3 | Empty summaries tăng | Empty summaries = 5 | Khôi phục từ raw data |
| Inject noise | Nối thêm chuỗi nhiễu vào summary | 2 | Embedding bị sai lệch | Giảm LLM Judge Score | Khôi phục từ raw data |
| Add duplicates | Nối thêm row đã có | 2 | Duplicates > 0 | Duplicate = 2 | Làm sạch lại từ đầu |

Corruption log:
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ loại corruption, paper_id tác động.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:
Repair không chỉnh sửa thủ công trên file lỗi mà gọi lại module Ingestion để load dữ liệu `raw_records.json` - bản sao chưa qua xử lý của API response. Dữ liệu này chạy lại toàn bộ luồng cleaning để tái tạo `papers_clean.csv`, đảm bảo toàn vẹn từ gốc.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      1.0 |       0.6 |      1.0 |                      -0.4 |             1.0 | Phục hồi hoàn toàn 100% |
| `mean_token_f1`        |      0.0986 |       0.0236 |      0.0986 |                      -0.075 |             1.0 | Phục hồi hoàn toàn |
| `mean_judge_score`     |      2.7000 |       2.3333 |      2.6667 |                      -0.3667 |             ~1.0 | Khôi phục gần sát mốc cũ |
| Quality checks pass/fail |      PASSED |       FAILED |      PASSED |                      N/A |             N/A | Bắt đúng lỗi duplicate/empty |

1. Dữ liệu lỗi (mất record, rỗng summary) → Quality signal FAILED (duplicate=2, empty=5) → Agent metric sụt giảm nghiêm trọng (Hit rate từ 1.0 xuống 0.6).
2. Tái nạp dữ liệu từ Raw (Repair) → Quality signal phục hồi thành PASSED → RAG Agent metric khôi phục hoàn toàn.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Pipeline bị fail ở bước embedding khi dữ liệu corrupted không hợp lệ.
- **Nguyên nhân:** Dữ liệu trống hoặc quá ngắn làm ChromaDB không thể vectorize.
- **Cách xử lý:** Bổ sung bước fallback và kiểm tra độ dài tối thiểu trước khi embedding.
- **Cách xác minh:** `data/quality/corrupted_quality.json` xuất ra đầy đủ, pipeline hoàn thành chạy `run_corruption_flow.py`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Phụ thuộc vào file raw JSON local | Nếu file raw hỏng thì không repair được | Cấu hình lưu raw backup định kỳ lên AWS S3 / Cloud Storage |
| Metric Token F1 khá thấp | Khó đánh giá chất lượng thực sự của câu trả lời tự nhiên | Thay token F1 bằng Semantics Similarity Score sử dụng LLM Judge |

## 13. Checklist trước khi nộp
- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
