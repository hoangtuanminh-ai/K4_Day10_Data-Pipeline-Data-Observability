# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Hoàng Tuấn Minh             |
| MSSV               | 2A202601500                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B2-2     |
| Vai trò chính    | Pipeline Integrator & Release Lead |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Pipeline Baseline | `src/pipelines/phase1.py` | Tất cả modules | Báo cáo baseline, toàn bộ metrics | Hoàn thành |
| Corruption & Repair Flow | `src/pipelines/corruption_flow.py` | Artifacts lỗi, modules phục hồi | Báo cáo comparison | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Debug & cấu hình môi trường | Cả nhóm | Toàn bộ nhóm chạy được `uv sync` không lỗi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Chạy tích hợp Phase 1 | `script/run_phase1.py` | `data/reports/phase1_report.md` | Chạy lệnh `python script/run_phase1.py` |
| Chạy tích hợp Phase 2 | `script/run_corruption_flow.py` | `data/reports/corruption_report.md` | Chạy lệnh `python script/run_corruption_flow.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Tích hợp tất cả các modules do các thành viên khác viết thành một luồng thực thi liên tục tự động từ đầu đến cuối.

### Cách triển khai
Sử dụng script Python để lần lượt gọi các hàm từ Ingestion, Cleaning, Retrieval, Evaluation và Observability, truyền tham số đầu ra của bước trước làm đầu vào của bước sau. Đảm bảo toàn vẹn dữ liệu xuyên suốt pipeline.

### Input, output và contract
- **Input**: Config settings, các script modules.
- **Output**: Output của toàn bộ luồng, in ra terminal và các file JSON/MD.
- **Module phụ thuộc**: `core.config`, `ingestion`, `retrieval`, `evaluation`, `observability`.
- **Module sử dụng output**: Các file report markdown.
- **Điều kiện lỗi cần xử lý**: Bắt exception LLM credentials bị thiếu và dừng pipeline sớm.

### Cách xác minh
```bash
python script/run_phase1.py
```
- **Kết quả mong đợi:** Báo cáo `phase1_report.md` được sinh ra thành công.
- **Kết quả thực tế:** Hit Rate đạt đúng 1.0, Quality Passed.
- **Artifact/log:** `data/reports/phase1_report.md`

## 5. Một quyết định kỹ thuật quan trọng
- **Bối cảnh:** Load lại dataset qua từng phase thay vì dùng chung dataframe context trong script.
- **Các phương án đã cân nhắc:** Pass df reference hoặc lưu ra file đọc lại.
- **Phương án đã chọn:** Lưu ra file và đọc lại.
- **Lý do:** Giúp debug độc lập từng phase dễ dàng, đảm bảo tính reproducibility.
- **Bằng chứng quyết định phù hợp:** Có file checkpoint `.csv` và `.json` lưu ở mọi phase.

## 6. Một lỗi hoặc blocker đã xử lý
- **Triệu chứng/lỗi nguyên văn:** Pipeline báo lỗi kết nối do thiếu LLM_API_KEY.
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py`
- **Nguyên nhân gốc:** Chưa thiết lập cấu hình `.env` cho RAG.
- **Cách xử lý:** Bổ sung hàm kiểm tra `require_llm_credentials(settings)`.
- **Cách xác minh sau khi sửa:** Chạy lỗi hiển thị exception báo chính xác thiếu KEY.
- **Điều học được:** Khởi tạo cấu hình và fail-fast trong pipeline.

## 7. Hiểu biết về luồng end-to-end
1. Từ Crossref fetch API -> raw JSON -> Clean -> CSV -> tạo string gộp -> ChromaDB Vector.
2. Ground-truth ID so sánh với ID do Retriever tìm được, nếu khớp thì tính là một Hit.
3. Quality check kiểm tra định dạng và logic data tĩnh (null, duplicate), freshness check kiểm tra độ mới của data dựa theo thời gian xuất bản so với hiện tại.
4. Dùng chung test set để đánh giá khách quan, đảm bảo metrics so sánh chuẩn xác khi dữ liệu bị lỗi.
5. Repair thành công nếu metrics (hit rate, F1) và quality check (PASSED) về lại bằng với mức Baseline ban đầu.

## 8. Phân tích kết quả
- Dữ liệu lỗi → Quality signal FAILED → Agent metric giảm từ 1.0 xuống 0.6.
- Repair luồng dữ liệu → Quality signal phục hồi → Agent metric trở lại 1.0.

## 9. Điều học được và hướng cải thiện
1. Việc kết nối pipeline đòi hỏi giao tiếp data contract chuẩn giữa các khâu.
2. Observability đặc biệt quan trọng để bắt lỗi trước khi ảnh hưởng LLM trả lời tồi.
3. RAG pipeline cần phải đi kèm khả năng lưu trữ raw snapshot.

## 10. Cam kết của thành viên
- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Tuấn Minh
**Ngày xác nhận:** 2026-08-06
