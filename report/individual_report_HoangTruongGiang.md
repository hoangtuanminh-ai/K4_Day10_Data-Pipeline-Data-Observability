# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hoàng Trường Giang             |
| MSSV               | 2A202601224                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B2-2     |
| Vai trò chính    | Data Observability & Evaluation Specialist |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Evaluation Test Set | `src/evaluation/testset.py` | `df_clean` (Baseline) | `data/eval/test_set.json` | Hoàn thành |
| Data Quality Check | `src/observability/quality.py` | Pandas DF (3 phase) | `*_quality.json`, `*_freshness.json` | Hoàn thành |
| Report Generator | `src/observability/reporting.py` | Metrics + Quality dict | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

## 3. Kết quả theo vai trò
| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh 30 câu hỏi QA | `build_test_set` | `test_set.json` | Đọc số object trong JSON sinh ra |
| Quality Gates | `run_data_quality_checks` | `baseline_quality.json` | Status: PASSED/FAILED |
| So sánh Metrics | `generate_corruption_report` | Báo cáo Markdown so sánh | View file `.md` |

## 4. Giải thích phần kỹ thuật đã thực hiện
### Vấn đề cần giải quyết
Tự động giám sát chất lượng dữ liệu (Observability) bằng cách đo đạc các chỉ số Freshness, Completeness, Uniqueness. Đánh giá chất lượng của Agent thông qua Retrieval Hit Rate và LLM Judge.

### Cách triển khai
- Lấy N record đầu trong tập sạch, tự động extract câu hỏi về title, authors, summary.
- Xây module Quality Gate: check df.isnull(), df.duplicated().
- Xuất kết quả ra các file JSON và nối lại thành Markdown report giúp theo dõi.

### Input, output và contract
- **Input**: DataFrame, Metrics dictionary.
- **Output**: Các file Report `.md` và Quality logs `.json`.
- **Điều kiện lỗi**: Bắt buộc Dataset đầu vào > 3 records để tạo test_set.

## 5. Một quyết định kỹ thuật quan trọng
- **Bối cảnh:** Làm sao đo được RAG có tệ đi không nếu data thay đổi.
- **Phương án đã chọn:** Fix cứng Test set bằng file JSON lưu trên đĩa, chỉ sinh 1 lần ở Baseline.
- **Lý do:** Giữ nguyên test_set làm tham chiếu (benchmark). Nếu chạy lại test_set trên tập dữ liệu lỗi (Corrupted) mà Hit rate giảm, chứng tỏ lỗi thuộc về dữ liệu.

## 6. Một lỗi hoặc blocker đã xử lý
- **Triệu chứng/lỗi nguyên văn:** Freshness check luôn báo false dù data mới lấy về.
- **Nguyên nhân gốc:** So sánh Timestamp có timezone UTC với Timestamp không có timezone (naive).
- **Cách xử lý:** Đưa datetime `run_date` về cùng UTC khi so sánh với ngày published.

## 7. Hiểu biết về luồng end-to-end
- Tôi đóng vai trò QA tự động cho toàn bộ hệ thống. Data từ Role 2 (nguồn), qua Role 3 (clean), Role 4 (Vector) sẽ được Role 1 chạy liên hoàn. Cuối cùng kết quả output phải đi qua hàm check quality và metrics của tôi để verify chất lượng. Khâu Repair (Role 3/1) thành công chỉ khi hàm của tôi lại pass.

## 8. Phân tích kết quả
- Sự tương quan giữa Corruption và Metrics rất rõ rệt. Khi Quality Checks fail (Có Duplicate, Null Summary), ngay lập tức `Hit Rate` giảm 40%, `LLM Judge Score` giảm từ 2.7 -> 2.3. Điều này có nghĩa Data Observability giúp cảnh báo RAG Degradation ngay từ tầng dữ liệu mà chưa cần user complain.

## 9. Điều học được và hướng cải thiện
- Lần đầu tiên biết cách ứng dụng LLM Judge để chấm điểm tự động. Nhận ra Data Quality > Model Quality trong hệ thống RAG.
- Hướng cải thiện: Dùng framework Ragas để thêm các metrics nâng cao như Answer Relevance.

## 10. Cam kết của thành viên
- [x] Mọi kết luận đều có dựa vào artifact `data/results` đo được.
- [x] Không sao chép báo cáo của bạn khác.

**Họ và tên:** Hoàng Trường Giang
**Ngày xác nhận:** 2026-08-06
