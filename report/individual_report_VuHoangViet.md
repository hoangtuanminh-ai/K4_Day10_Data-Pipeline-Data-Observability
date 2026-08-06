# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Vũ Hoàng Việt             |
| MSSV               | 2A202601250                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B2-2     |
| Vai trò chính    | Data Cleaning, Corruption & Recovery Specialist |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Cleaning | `src/ingestion/cleaning.py` | `list[PaperRecord]` | `papers_clean.csv` | Hoàn thành |
| Data Corruption | `src/ingestion/corruption.py` | `papers_clean.csv` | `papers_corrupted.csv`, `corruption_log.json` | Hoàn thành |

## 3. Kết quả theo vai trò
| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Clean raw records | `build_clean_dataframe` | `data/clean/papers_clean.csv` | Check DataFrame len và các cột gộp |
| Simulate Errors | `corrupt_clean_dataframe` | `data/results/corruption_log.json` | Đọc file JSON corruption log |

## 4. Giải thích phần kỹ thuật đã thực hiện
### Vấn đề cần giải quyết
Làm sạch dữ liệu thô (chuẩn bị string cho Embedding) và cố ý làm bẩn dữ liệu để kiểm tra sức chịu đựng của Data Observability.

### Cách triển khai
- Cleaning: Chuyển array thành string, format datetime và nối cột làm text embedding.
- Corruption: Gán rỗng summary, sửa đổi date để thành stale data, thêm row duplicate và tạo log.

### Input, output và contract
- **Input**: Raw objects và Clean DF.
- **Output**: Pandas DataFrame và CSV file lưu trữ kết quả.
- **Điều kiện lỗi**: Bỏ qua các record không có đủ nội dung summary.

## 5. Một quyết định kỹ thuật quan trọng
- **Phương án đã chọn:** Format cột `text_for_embedding` bằng cách ghép "Title: ... \n Summary: ...".
- **Lý do:** Tăng khả năng trích xuất thông tin (retrieval semantic) khi vector DB so sánh query của user.

## 6. Một lỗi hoặc blocker đã xử lý
- **Nguyên nhân gốc:** Khi corrupt dữ liệu sửa giá trị ID thành null, Pandas tự convert sang float (NaN) làm hỏng type str của vector.
- **Cách xử lý:** Thay vì đặt NaN, gán chuỗi rỗng `""` hoặc inject text nhiễu `"GARBAGE"`.

## 7. Hiểu biết về luồng end-to-end
- Tôi nhận JSON từ Role 2, biến nó thành CSV cho Role 4. Nếu Role 5 chạy Quality checks mà báo FAILED, tôi phải đảm bảo phần Corruption của tôi đang chạy đúng mô phỏng. Khi Repair, tôi gọi lại module của mình trên source raw.

## 8. Phân tích kết quả
- Sự thay đổi từ Corruption (Duplicate=2, Empty=5) làm Pipeline rớt Hit Rate 40%. Điều này chứng tỏ data quality kém sẽ phá hỏng ngay lập tức chất lượng trả lời (RAG) bất chấp mô hình LLM.

## 9. Điều học được và hướng cải thiện
- Data contract cực kỳ quan trọng; việc có report quality tự động (Role 5) giúp phát hiện rác dữ liệu trước khi đi vào mô hình.

## 10. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc.
- [x] Không có token hoặc secret trong báo cáo.

**Họ và tên:** Vũ Hoàng Việt
**Ngày xác nhận:** 2026-08-06
