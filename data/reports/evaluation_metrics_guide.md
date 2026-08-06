# Hướng dẫn chi tiết về các Điểm số Đánh giá (Evaluation Metrics) trong RAG

Để đánh giá chất lượng của một hệ thống RAG (Retrieval-Augmented Generation), người ta không thể chỉ dựa vào cảm tính mà phải dùng các độ đo (metrics). Trong hệ thống của bạn, 3 điểm số này được dùng để đánh giá hai phần riêng biệt của RAG: **Chất lượng tìm kiếm (Retrieval)** và **Chất lượng sinh văn bản (Generation)**.

Dưới đây là cách tính và lý do tại sao chúng ta bắt buộc phải dùng chúng:

---

## 1. Retrieval Hit Rate (Tỉ lệ trúng đích)
Đo lường sức mạnh của hệ thống tìm kiếm (Vector Database - ChromaDB).

- **Cách tính:** 
  Mỗi câu hỏi sẽ đi kèm với ID của một bài báo chứa đáp án chuẩn (`ground_truth_doc_id`). Khi AI tìm kiếm, nó sẽ bốc ra Top 4 bài báo có độ tương đồng cao nhất (`retrieved_doc_ids`).
  - Nếu ID chuẩn nằm trong Top 4 này ➡️ Tính là Trúng (Hit = 1).
  - Nếu ID chuẩn không nằm trong Top 4 ➡️ Tính là Trượt (Hit = 0).
  > *Hit Rate = Tổng số lần trúng / Tổng số câu hỏi trong testset.*
- **Tại sao phải dùng:** 
  Đây là nút thắt cổ chai của RAG. Nếu Vector Database tìm sai tài liệu đưa cho AI đọc, thì dù mô hình LLM có thông minh cỡ nào (như GPT-4) cũng sẽ trả lời sai lệch (Hallucination). Khi bạn tiêm lỗi làm rỗng hoặc nhiễu văn bản (Corruption), Vector Database sẽ bị "mù", từ đó kéo điểm Hit Rate này xuống thấp.

---

## 2. Token F1 Score (Độ trùng khớp từ vựng)
Đo lường mức độ chính xác bề mặt (từng từ) của câu trả lời AI sinh ra so với đáp án gốc.

- **Cách tính:** 
  Chia cả câu trả lời của AI và câu trả lời chuẩn (Ground Truth) thành danh sách từng từ (tokens). Điểm F1 được tính toán dựa trên 2 yếu tố:
  - **Precision (Độ chính xác):** Số từ giống nhau / Tổng số từ mà AI nói ra. Yếu tố này phạt AI nếu nó nói quá dài hoặc nói nhảm.
  - **Recall (Độ bao phủ):** Số từ giống nhau / Tổng số từ của đáp án chuẩn. Yếu tố này phạt AI nếu nó trả lời quá ngắn hoặc thiếu ý.
  > *F1 = 2 * (Precision * Recall) / (Precision + Recall)*
- **Tại sao phải dùng:** 
  Độ đo này chạy cực nhanh, nhẹ và hoàn toàn tự động (không tốn chi phí gọi API). F1 rất phù hợp để đo lường các câu hỏi cần thông tin cứng ngắc như: *"Ai là tác giả?"*, *"Năm xuất bản là bao giờ?"*. 
  > **Nhược điểm:** F1 khá máy móc. Nếu AI dùng **từ đồng nghĩa** hoặc viết lại câu có cùng ý nghĩa nhưng khác từ vựng, F1 vẫn sẽ chấm điểm thấp.

---

## 3. LLM-as-a-Judge Score (Điểm Giám khảo LLM)
Đo lường mức độ hiểu và khả năng diễn đạt đúng ngữ nghĩa của AI.

- **Cách tính:** 
  Hệ thống sẽ gọi một mô hình AI thứ 3 (thường là mô hình mạnh hơn, ví dụ `GPT-4o-mini` hoặc `GPT-4`) đóng vai trò làm "Ban giám khảo". Giám khảo được cung cấp 3 thành phần: Câu hỏi, Đáp án gốc (Ground Truth), và Câu trả lời của hệ thống cần đánh giá. Giám khảo sẽ đọc, phân tích ngữ nghĩa và chấm điểm theo thang từ **1 đến 5**:
  - **Điểm 1:** AI trả lời sai hoàn toàn, không liên quan, hoặc bịa đặt thông tin.
  - **Điểm 3:** Trả lời đúng một nửa ý, còn thiếu thông tin quan trọng.
  - **Điểm 5:** Trả lời hoàn hảo, đầy đủ và đúng mọi ý nghĩa (dù có thể dùng từ vựng khác với đáp án gốc).
- **Tại sao phải dùng:** 
  Đây là phương pháp đánh giá hiện đại nhất để bù đắp khuyết điểm của Token F1. Chấm điểm bằng LLM Judge mô phỏng cách con người chấm bài văn. Nó giúp ta biết được chính xác rằng khi dữ liệu bị tiêm lỗi, câu trả lời của AI có bị sai lệch ý nghĩa hoặc trở nên "nguy hiểm" (như bịa thông tin y tế, tài chính) hay không. Thông qua điểm số này, ta đo đếm được trải nghiệm thực tế của người dùng cuối.
