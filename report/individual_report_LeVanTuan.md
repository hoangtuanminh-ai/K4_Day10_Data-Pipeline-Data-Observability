# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Văn Tuấn             |
| MSSV               | 2A202601016                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B2-2     |
| Vai trò chính    | Data Ingestion & Raw Lineage Specialist |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Crossref Ingestion | `src/ingestion/crossref.py` | Thông số truy vấn Crossref | `raw_api_response.json`, `raw_records.json` | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Fetch Data từ API | `fetch_source_records` | `data/raw/raw_records.json` | Đọc file JSON gồm 24 records |
| Parsing Data payload | `parse_crossref_payload` | List of `PaperRecord` | Pipeline phase 1 chạy thành công không lỗi |

## 4. Giải thích phần kỹ thuật đã thực hiện
### Vấn đề cần giải quyết
Lấy dữ liệu thô từ Crossref REST API và chuẩn hóa về dạng Data Object cơ bản (PaperRecord) để các khâu tiếp theo có thể xử lý dễ dàng.

### Cách triển khai
Gửi HTTP request bằng thư viện `requests`, parse trường `message.items` thành một danh sách dataclass `PaperRecord`. Quản lý cơ chế retry nếu API gọi lỗi.

### Input, output và contract
- **Input**: `settings.source_query` (retrieval augmented generation)
- **Output**: JSON lưu các fields `paper_id, title, summary, authors, published...`
- **Module phụ thuộc**: `core.config`
- **Module sử dụng output**: `cleaning.py`
- **Điều kiện lỗi cần xử lý**: API timeout hoặc rate limit, đã thêm retry 3 lần.

### Cách xác minh
```bash
python -c "from src.core.config import load_settings; from src.ingestion.crossref import fetch_source_records; fetch_source_records(load_settings())"
```
- **Kết quả mong đợi:** 24 bản ghi JSON.
- **Kết quả thực tế:** Tạo đủ JSON trong mục `data/raw/`.

## 5. Một quyết định kỹ thuật quan trọng
- **Bối cảnh:** Lấy được `DOI` từ API nhưng bị format chứa các ký hiệu `/`.
- **Các phương án đã cân nhắc:** Thay `/` bằng `-` hoặc tạo UUID.
- **Phương án đã chọn:** Dùng hàm `safe_slug` để format DOI thành chuỗi hợp lệ (`paper_id`).
- **Lý do:** Giữ lại thông tin DOI (làm ID unique) nhưng không bị lỗi khi làm filesystem naming.

## 6. Một lỗi hoặc blocker đã xử lý
- **Triệu chứng/lỗi nguyên văn:** API request đôi lúc bị Connection Reset.
- **Nguyên nhân gốc:** Không khai báo User-Agent trong Header nên API block.
- **Cách xử lý:** Bổ sung param `headers = {"User-Agent": "..."}`.
- **Điều học được:** Khi thu thập data công cộng, luôn cần xưng danh (User-Agent) văn minh.

## 7. Hiểu biết về luồng end-to-end
- Dữ liệu thu thập từ `crossref.py` (JSON) được `cleaning.py` làm sạch (CSV), chuyển hóa thành vector và nhét vào ChromaDB (Role 4). Nếu hỏng dữ liệu, luồng corruption_flow sẽ đọc lại chính file raw JSON này của tôi để chạy lại (Repair).

## 8. Phân tích kết quả
- Data gốc từ API quyết định tất cả luồng tiếp theo. Việc Repair hoàn toàn dựa vào snapshot raw data của module ingestion.

## 9. Điều học được và hướng cải thiện
- Việc parse JSON response cồng kềnh cần rất tỉ mỉ để tránh lỗi type error. 
- Hướng cải thiện: Xử lý pagination lấy nhiều data hơn.

## 10. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Lê Văn Tuấn
**Ngày xác nhận:** 2026-08-06
