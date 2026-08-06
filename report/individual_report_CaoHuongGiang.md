# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Cao Hương Giang             |
| MSSV               | 2A202601420                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B2-2     |
| Vai trò chính    | RAG Engine & Vector Store Specialist |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Vector Indexing | `src/retrieval/index.py` | `df_clean` (Pandas) | ChromaDB Collection, Embeddings JSON | Hoàn thành |
| RAG Agent | `src/retrieval/agent.py` | Chroma Index, Question | Final Answer, Context Sources | Hoàn thành |

## 3. Kết quả theo vai trò
| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| ChromaDB Local Persistent | `LocalEmbeddingIndex.build()` | `data/chroma/`, `data/embeddings/` | Check folder `data/chroma/` sinh ra |
| RAG semantic search | `RAGAgent.answer_question()` | Câu trả lời kèm source | Chạy Smoke test role 4 |

## 4. Giải thích phần kỹ thuật đã thực hiện
### Vấn đề cần giải quyết
Tạo Database Vector để lưu các bài báo đã làm sạch (Embedding), và cho phép tìm kiếm theo ngữ nghĩa (Semantic Search) để cung cấp Context cho LLM trả lời (RAG).

### Cách triển khai
- Dùng `sentence-transformers/all-MiniLM-L6-v2` để sinh vector nhúng cho cột `text_for_embedding`.
- Insert vectors, metadata và doc ID vào ChromaDB.
- Khởi tạo LLM Chat model, khi có câu hỏi, query top-k docs từ Chroma, nhét vào prompt context và gọi LLM.

### Input, output và contract
- **Input**: DataFrame sạch chứa nội dung cần lưu.
- **Output**: Thư mục lưu trữ database vector. Hàm query trả về list docs gần nhất.
- **Điều kiện lỗi**: Bỏ qua các doc có vector rỗng. Nếu LLM lỗi thì báo exception.

## 5. Một quyết định kỹ thuật quan trọng
- **Bối cảnh:** Cần lưu index phân biệt giữa baseline và corrupted.
- **Phương án đã chọn:** Tạo các collection riêng biệt (ví dụ: `papers-baseline`, `papers-corrupted`) trong cùng một ChromaDB client.
- **Lý do:** Dễ dàng query so sánh, không bị đè dữ liệu.

## 6. Một lỗi hoặc blocker đã xử lý
- **Lỗi nguyên văn:** ChromaDB warning về batch size quá lớn.
- **Cách xử lý:** Cắt list doc thành các chunk nhỏ (ví dụ 100 docs) để upsert thay vì nhét toàn bộ 1 lần. 

## 7. Hiểu biết về luồng end-to-end
- Tôi lấy CSV từ Role 3, xây Vector Index để Role 5 đo đạc metrics. Dữ liệu lỗi (corrupted) nếu lọt vào Vector Index của tôi sẽ làm sai lệch Semantic Search, dẫn đến trả về source sai cho Agent. 

## 8. Phân tích kết quả
- Sự suy giảm Hit rate khi Corruption xảy ra là do vector DB không thể matching query của user với các bài báo bị nhiễu text (noise) hoặc rỗng.

## 9. Điều học được và hướng cải thiện
- Việc chọn Embedding model và cấu trúc đoạn text (format) cực kỳ ảnh hưởng đến khả năng search.
- Hướng cải thiện: Sử dụng Cohere hoặc OpenAI embedding thay vì Local MiniLM để vector chuẩn hơn.

## 10. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc.
- [x] Không sao chép nguyên văn báo cáo khác.

**Họ và tên:** Cao Hương Giang
**Ngày xác nhận:** 2026-08-06
