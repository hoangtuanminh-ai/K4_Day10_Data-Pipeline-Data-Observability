# Hướng Dẫn Chi Tiết: Luồng Tiêm Nhiễu (Corruption) và Vá Lỗi Tự Động (Active Repair)

Tài liệu này giải thích cách hệ thống giả lập các lỗi dữ liệu thực tế (Data Corruption) và cách phục hồi dữ liệu tự động (Active Repair) ở mức độ từng trường (field-level) một cách an toàn và tối ưu nhất.

---

## 1. Luồng Tiêm Nhiễu Dữ Liệu (Data Corruption Flow)

Luồng này mô phỏng lại những lỗi thường gặp nhất trong các hệ thống Data Pipeline thực tế, ví dụ như lỗi mạng, lỗi parse JSON, hệ thống bị nghẽn, hoặc lỗi do API của bên thứ 3 trả về sai cấu trúc.

Quá trình tiêm lỗi được thực hiện trong hàm `inject_corruption` (tại `src/pipelines/corruption_flow.py`). Thay vì xóa ngẫu nhiên, hệ thống nhắm vào 5 loại lỗi cốt lõi:

### Các kịch bản lỗi được giả lập:

1.  **Drop Records (Mất dữ liệu):**
    *   **Cách làm:** Xóa ngẫu nhiên 5% số lượng bài báo trong tập dữ liệu.
    *   **Ý nghĩa:** Mô phỏng tình trạng rớt gói tin hoặc lỗi timeout khi gọi API.

2.  **Duplicate Records (Nhân bản dữ liệu):**
    *   **Cách làm:** Lấy 10% dữ liệu hiện tại và chèn thêm (append) vào cuối danh sách, tạo ra các dòng bị trùng lặp `paper_id`.
    *   **Ý nghĩa:** Mô phỏng tình trạng Kafka/RabbitMQ gửi lại message nhiều lần (At-least-once delivery issues).

3.  **Corrupt Text Fields (Hỏng văn bản):**
    *   **Cách làm:** Chọn ngẫu nhiên 20% bài báo. Làm rỗng (Empty) trường `summary` hoặc chèn dòng chữ nhiễu `"[SYSTEM ERROR: TEXT TRUNCATED]"` vào. Cắt ngắn trường `title` xuống còn 5 ký tự.
    *   **Ý nghĩa:** Mô phỏng lỗi do web scraping bị chặn, hoặc parse HTML/XML bị sai.

4.  **Corrupt Metadata (Hỏng siêu dữ liệu tác giả):**
    *   **Cách làm:** Thêm chuỗi `"Corrupted, Data, User"` vào danh sách tác giả (`authors` và `authors_joined`).
    *   **Ý nghĩa:** Mô phỏng lỗi merge dữ liệu sai từ nhiều nguồn.

5.  **Stale Data (Dữ liệu cũ, hết hạn):**
    *   **Cách làm:** Sửa ngày xuất bản (`published`) về `"2000-01-01"` và đặt lại số ngày tuổi (`age_days`) thành 9999.
    *   **Ý nghĩa:** Mô phỏng lỗi do hệ thống cache trả về dữ liệu cũ (cache invalidation fail).

> **Kết quả:** Sau bước này, tập dữ liệu trở nên rất "bẩn". Nếu đưa thẳng vào ChromaDB để làm RAG (Retrieval-Augmented Generation), Agent sẽ trả lời sai do tìm kiếm phải các dòng văn bản rác hoặc rỗng.

---

## 2. Luồng Vá Lỗi Tự Động (Active Repair Flow)

Thay vì xóa toàn bộ dữ liệu lỗi và tải lại từ đầu (rất tốn tài nguyên và thời gian), hệ thống áp dụng kỹ thuật **Self-Healing (Tự chữa lành)**.

Quá trình này diễn ra trong hàm `repair_corrupted_dataframe` (tại `src/ingestion/cleaning.py`).

### Phương Pháp Lõi: Dictionary-Record Manipulation
Pandas DataFrame vốn rất dễ bị lỗi `Multi-index` hoặc lỗi chiều dài (length mismatch) khi thao tác gán dữ liệu cho từng ô bằng lệnh `.loc`. Do đó, hệ thống trích xuất DataFrame thành một **danh sách các từ điển (List of Dictionaries)**. Việc xử lý trên Dictionary của Python thuần túy là an toàn tuyệt đối và tốc độ cực nhanh.

Hệ thống sử dụng một biến `raw_map` (bản đồ dữ liệu gốc, lấy từ file `crossref_records.json` - đóng vai trò như một Source of Truth / Nguồn chân lý) để đối chiếu.

### 4 Bước Sửa Lỗi Cụ Thể:

#### Bước 1: Khử Trùng Lặp (Deduplication)
Hệ thống gộp tất cả các dòng có chung `paper_id` và chỉ giữ lại 1 dòng duy nhất.
```python
df_dedup = df_corrupted.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
records = df_dedup.to_dict(orient="records")
```

#### Bước 2: Vá Lỗi Từng Ô Chuyên Sâu (Field-level Repair)
Hệ thống duyệt qua từng dòng dữ liệu (từng cuốn từ điển). Nếu phát hiện lỗi (dựa trên quy tắc), nó sẽ nhìn sang `raw_map` để lấy lại dữ liệu đúng và ghi đè vào.
*   **Sửa Summary:** Nếu độ dài < 10 hoặc chứa chữ `"[SYSTEM ERROR"`, ghi đè lại Summary gốc.
*   **Sửa Title:** Nếu độ dài < 10, ghi đè lại Title gốc.
*   **Sửa Tác giả:** Nếu có chữ `"Corrupted"` hoặc bị rỗng, ghi đè lại mảng tác giả gốc.
*   **Sửa Ngày tháng:** Nếu bắt đầu bằng `"2000"`, ghi đè ngày gốc và tính toán lại cột `age_days`.

#### Bước 3: Phục Hồi Dữ Liệu Bị Rớt (Missing Records Restoration)
Làm sao để biết bài nào bị xóa (Drop rows)? Hệ thống lấy tập hợp (Set) các `paper_id` đang có trong tay, trừ đi danh sách gốc. Các ID còn thừa chính là các bài bị thiếu. Hệ thống tự động `build` lại các bài này và dán ngược lại vào DataFrame.
```python
existing_ids = set(df_repaired["paper_id"])
missing_records = [r for r in raw_records if r.paper_id not in existing_ids]
if missing_records:
    df_missing = build_clean_dataframe(missing_records, run_date)
    df_repaired = pd.concat([df_repaired, df_missing], ignore_index=True)
```

#### Bước 4: Tái Cấu Trúc Khối Dữ Liệu Phái Sinh (Derived Fields Rebuild)
Sau khi tiêu đề, tác giả, tóm tắt đã chuẩn xác, hệ thống ghép chúng lại thành một khối văn bản duy nhất `text_for_embedding`. Khối văn bản này sẽ được dùng để đo chiều dài (`summary_chars`) và chuẩn bị đưa vào ChromaDB cho Agent đọc hiểu.
```python
df_repaired["text_for_embedding"] = df_repaired.apply(
    lambda r: f"Title: {r['title']}\nAuthors: {r['authors_joined']}\nCategories: {r['categories_joined']}\nSummary: {r['summary']}",
    axis=1
)
```

---

### Tổng Kết
Luồng xử lý trên chứng minh một thực tiễn tốt (Best Practice) trong Data Engineering: **Không bao giờ tin tưởng hoàn toàn vào dữ liệu đầu vào, và luôn có cơ chế đối chiếu/vá lỗi trước khi đưa dữ liệu vào các hệ thống AI.**
