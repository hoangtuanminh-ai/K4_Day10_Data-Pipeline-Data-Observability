# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Trường Giang |
| MSSV | 2A202601224 |
| Khóa/Lớp | K4 |
| Tên nhóm | Chưa xác định |
| Vai trò chính | Role 5 — Data Observability & Evaluation Specialist |
| Repository | `K4_Day10_Data-Pipeline-Data-Observability` |
| Ngày hoàn thành phần việc | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Evaluation test set | `src/evaluation/testset.py` — `build_test_set` | Clean dataframe có paper metadata | `data/eval/test_set.json` | Hoàn thành code |
| Evaluation metrics | `src/evaluation/metrics.py` — rà interface `evaluate_pipeline` | Test set và embedding index | `*_metrics.json`, `*_answers.json` khi pipeline chạy | Đã xác minh code có sẵn |
| Quality & freshness | `src/observability/quality.py` | Clean/corrupted/repaired dataframe, `Settings` | Quality JSON và freshness JSON | Hoàn thành code |
| Evidence reports | `src/observability/reporting.py` | Metrics, quality, freshness, source summary | `phase1_report.md`, `corruption_report.md` | Hoàn thành code |

Tôi chỉ sở hữu phần evaluation và observability. Các module ingestion, cleaning, retrieval/index và orchestration thuộc các role khác; chúng cung cấp dataframe, index và path cần thiết cho phần việc của tôi.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đối chiếu contract | `src/evaluation/metrics.py`, `src/retrieval/qa.py` | Test set được thiết kế để câu hỏi và ground truth khớp cách hàm trả lời hiện có hoạt động. |
| Rà interface integration | `src/pipelines/*` | Xác định starter dùng `evaluation.metrics.evaluate_pipeline`, không có module `evaluation.evaluator.py`. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tạo test set có thể tái lập | `build_test_set` | Tối đa 8 paper, 4 câu hỏi/paper: summary, authors, date, categories | `python -m compileall -q src` thành công; pipeline sẽ ghi `data/eval/test_set.json` |
| Thiết kế quality gates | `run_data_quality_checks` | Kiểm tra số dòng, ID null/trùng, title rỗng, summary ngắn, age invalid và stale | Báo cáo JSON tại `data/quality/<report_name>.json` |
| Theo dõi freshness | `build_freshness_report` | Latest/oldest publication, invalid dates, stale rows, `is_fresh` | Báo cáo JSON tại path do pipeline truyền vào |
| Viết report dựa trên evidence | `generate_phase1_report`, `generate_corruption_report` | Baseline report và bảng so sánh metrics/quality/freshness | Render từ dict metrics và quality/freshness artifacts, không hard-code số liệu |

Output cụ thể của phần việc là các hàm ghi artifact JSON/Markdown. Tại thời điểm viết báo cáo, repository chưa có raw/clean/index artifact và dependencies runtime chưa đầy đủ, nên chưa có metrics thật để điền vào báo cáo kết quả.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG pipeline không thể chỉ dựa vào việc script chạy xong. Cần một bộ câu hỏi có ground truth ổn định để đo retrieval/answer quality, đồng thời cần quality và freshness signals để chứng minh dữ liệu lỗi liên quan thế nào đến kết quả của agent.

### Cách triển khai

`build_test_set` kiểm tra schema đầu vào và yêu cầu ít nhất ba record hợp lệ. Hàm loại paper thiếu ID/title/summary, deduplicate theo `paper_id`, sort theo `published` và `paper_id` để cùng raw snapshot luôn sinh cùng test set. Mỗi paper sinh bốn loại câu hỏi. Câu hỏi trích title chính xác trong dấu nháy, còn ground truth summary lấy câu đầu tiên để khớp với `retrieval.qa._extract_answer`; nhờ đó token F1 phản ánh retrieval/answer thay vì bị giảm do khác độ dài câu trả lời.

Quality checks trả về vừa phần tóm tắt vừa chi tiết từng check có `passed`, actual/invalid row count và threshold. Freshness được tính từ `age_days`, còn `published` được parse độc lập để phát hiện ngày không hợp lệ. Hai report chỉ trình bày số liệu nhận vào; report so sánh tính delta corrupted-baseline và repaired-corrupted, không tự kết luận recovery hoàn toàn.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean dataframe cần có `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`. |
| Output | Test set JSON; quality/freshness JSON; Markdown reports. |
| Module phụ thuộc | `core.utils` để ghi JSON/text; `core.config.Settings` cho quality path và freshness threshold. |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, `evaluation.metrics.evaluate_pipeline`. |
| Điều kiện lỗi cần xử lý | Thiếu cột, ít hơn 3 document hợp lệ, ID trùng/rỗng, date không parse được, summary ngắn/rỗng. |

### Cách xác minh

```bash
python -m compileall -q src
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Hai flow tạo test set, metrics/answers, quality/freshness và Markdown reports.
- **Kết quả thực tế:** Kiểm tra cú pháp thành công. Hai flow chưa chạy được trên môi trường hiện tại vì thiếu dependency runtime `pandas`.
- **Artifact/log:** Khi chạy thành công, kiểm tra `data/eval/`, `data/results/`, `data/quality/`, `data/reports/`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Test set phải công bằng khi so sánh baseline, corrupted và repaired.
- **Các phương án đã cân nhắc:** Tạo câu hỏi ngẫu nhiên ở mỗi lần chạy; hoặc tạo bộ câu hỏi cố định từ cleaned dataset.
- **Phương án đã chọn:** Chọn tối đa 8 record theo thứ tự xác định và lưu test set JSON để tái sử dụng nguyên vẹn.
- **Lý do:** Bộ cố định giữ nguyên question, ground truth và document IDs; vì vậy chênh lệch metrics đến từ dữ liệu/index, không do mẫu đánh giá thay đổi.
- **Bằng chứng quyết định phù hợp:** Hàm sort theo `published` và `paper_id`, sau đó ghi `test_set.json`; pipeline chỉ tạo lại khi `REFRESH_TEST_SET` được bật.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'pandas'`.
- **Lệnh hoặc bước tái hiện:** Chạy smoke test Python với dataframe giả sau khi hoàn thành code Role 5.
- **Nguyên nhân gốc:** `.venv` hiện chưa cài dependency của project; môi trường chỉ có pip cơ bản.
- **Cách xử lý:** Không thay đổi code để né dependency. Cần chạy `uv sync` hoặc cài project theo hướng dẫn README trước khi chạy end-to-end.
- **Cách xác minh sau khi sửa:** Chạy lại smoke test và hai entrypoint pipeline; kiểm tra artifacts thật.
- **Điều học được:** Compile chỉ kiểm tra syntax. Cần environment dependencies và artifacts thật để xác nhận hợp đồng runtime.

## 7. Hiểu biết về luồng end-to-end

1. Role ingestion fetch Crossref và lưu raw response/records. Cleaning chuẩn hóa thành dataframe, tạo `text_for_embedding` và `age_days`; retrieval biến dataframe thành embeddings/Chroma collection.
2. Test set lưu ground truth answer và `paper_id` của document đúng. Evaluator so sánh IDs retrieved với ground-truth IDs để tính retrieval hit rate, đồng thời chấm answer bằng token F1 và judge score.
3. Quality kiểm tra tính đầy đủ, uniqueness và validity của các cột; freshness theo dõi độ mới của dữ liệu dựa trên `published`/`age_days`. Đây là hai góc nhìn bổ sung nhau.
4. Dùng cùng test set loại trừ biến đánh giá khỏi phép so sánh; metrics khác nhau khi đó mới có thể quy cho khác biệt giữa baseline, corrupted và repaired data.
5. Repair thành công khi repaired data/index/quality artifacts được tạo từ raw snapshot, quality/freshness phục hồi và metrics cải thiện so với corrupted. Không nên kết luận hồi phục hoàn toàn nếu metrics chưa bằng hoặc gần baseline.

## 8. Phân tích kết quả

Chưa có số liệu thực nghiệm vì baseline và corruption flow chưa được chạy. Các ô dưới đây sẽ được cập nhật từ JSON artifacts sau khi môi trường cài đủ dependencies.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa chạy | Chưa chạy | Chưa chạy | Đọc từ ba file metrics. |
| `mean_token_f1` | Chưa chạy | Chưa chạy | Chưa chạy | Đối chiếu cùng test set. |
| `judge_accuracy` | Chưa chạy | Chưa chạy | Chưa chạy | Có fallback nếu LLM judge không khả dụng. |
| `mean_judge_score` | Chưa chạy | Chưa chạy | Chưa chạy | Không suy diễn trước khi có artifact. |
| Quality checks | Chưa chạy | Chưa chạy | Chưa chạy | Corruption dự kiến tạo duplicate/summary rỗng/stale. |
| Freshness status | Chưa chạy | Chưa chạy | Chưa chạy | Đọc từ freshness reports. |

Sau khi chạy, cần chứng minh theo evidence: corruption → quality/freshness signal thay đổi → retrieval/answer metric thay đổi; sau đó repair từ raw → signal phục hồi → metric phục hồi hoặc chỉ ra metric chưa phục hồi.

## 9. Điều học được và hướng cải thiện

1. Evaluation đáng tin cậy cần test set có document identity ổn định, không chỉ có câu trả lời tham chiếu.
2. Observability cần artifact có thể audit: mỗi quality/freshness conclusion phải có JSON/Markdown tương ứng.
3. Dữ liệu tốt là một phần trực tiếp của chất lượng RAG; vector model không thể tự khắc phục summary rỗng, record bị mất hoặc duplicate.

Nếu có thêm thời gian, tôi sẽ thêm unit tests cho các trường hợp data rỗng, duplicate, invalid date và thay đổi câu hỏi để đo deterministic output của test-set builder.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [ ] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu. Chưa có metrics runtime.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Trường Giang<br>
**Ngày xác nhận:** 2026-08-06
