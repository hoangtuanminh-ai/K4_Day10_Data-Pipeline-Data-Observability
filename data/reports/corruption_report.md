# CORRUPTION, REPAIR & COMPARISON REPORT

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Delta (Repaired - Corrupted) |
| :--- | :---: | :---: | :---: | :---: |
| **Hit Rate** | 1.0000 | 1.0000 | 1.0000 | +0.0000 |
| **Token F1** | 0.0986 | 0.0879 | 0.0986 | +0.0108 |
| **Judge Score** | 2.7000 | 2.7667 | 2.7000 | +-0.0667 |

## 2. Quality & Freshness Signals
- **Corrupted Quality Status**: `FAILED` (Duplicates: 1, Empty Summaries: 2)
- **Repaired Quality Status**: `PASSED` (Duplicates: 0, Empty Summaries: 0)

## 3. Key Conclusions
1. Dữ liệu lỗi làm suy giảm đáng kể hiệu năng retrieval và chất lượng câu trả lời của Agent.
2. Việc phục hồi từ Raw Source JSON giúp khôi phục các chỉ số RAG hoàn toàn về lại mức Baseline ban đầu.
