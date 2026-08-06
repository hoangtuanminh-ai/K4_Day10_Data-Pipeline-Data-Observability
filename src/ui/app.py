import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import random

# Tùy chỉnh giao diện trang
st.set_page_config(
    page_title="Data Observability Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. Cấu hình Đường dẫn (Paths Setup)
# ---------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RESULTS_DIR = PROJECT_ROOT / "data" / "results"

# ---------------------------------------------------------
# 2. Hàm Load Dữ liệu
# ---------------------------------------------------------
@st.cache_data
def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Lỗi đọc file {filepath.name}: {e}")
        return None

# Load Metrics
baseline_metrics = load_json(DATA_RESULTS_DIR / "baseline_metrics.json")
corrupted_metrics = load_json(DATA_RESULTS_DIR / "corrupted_metrics.json")
repaired_metrics = load_json(DATA_RESULTS_DIR / "repaired_metrics.json")

# Load Answers
baseline_ans = load_json(DATA_RESULTS_DIR / "baseline_answers.json")
corrupted_ans = load_json(DATA_RESULTS_DIR / "corrupted_answers.json")
repaired_ans = load_json(DATA_RESULTS_DIR / "repaired_answers.json")

# Load Corruption Log
corruption_log = load_json(DATA_RESULTS_DIR / "corruption_log.json")

# ---------------------------------------------------------
# 3. Thanh điều hướng (Sidebar Navigation)
# ---------------------------------------------------------
st.sidebar.title("🔍 Data Observability")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Điều hướng (Navigation)",
    ["1. Tổng quan (Overview)", 
     "2. Phương pháp Tiêm lỗi (Corruption)", 
     "3. Chỉ số & Báo cáo (Metrics)", 
     "4. Trực quan RAG Q&A"]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Mục đích:**\nTrực quan hóa sự ảnh hưởng của Dữ liệu Lỗi (Corrupted Data) "
    "đến hệ thống RAG và cách tính năng Active Repair phục hồi hiệu năng."
)

# ---------------------------------------------------------
# 4. Giao diện từng Trang
# ---------------------------------------------------------

if page == "1. Tổng quan (Overview)":
    st.title("🌟 Tổng quan Hệ thống (Overview)")
    st.markdown("Chào mừng đến với **Data Observability Dashboard**.")
    
    st.subheader("Kiến trúc luồng xử lý (Data Flow)")
    st.info("Quy trình đánh giá chất lượng dữ liệu được chia làm 3 giai đoạn độc lập:")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("🟢 1. Baseline Pipeline")
        st.write("Dữ liệu sạch được nạp trực tiếp vào ChromaDB. Đo lường hiệu năng của LLM trong điều kiện lý tưởng (Không có lỗi).")
    with col2:
        st.error("🔴 2. Corrupted Pipeline")
        st.write("Cố tình tiêm nhiễu (xóa, nhân bản, sửa ngày, rỗng text) vào dữ liệu gốc để mô phỏng lỗi thực tế, sau đó đánh giá lại sự suy giảm hiệu năng.")
    with col3:
        st.info("🔵 3. Repaired Pipeline")
        st.write("Áp dụng thuật toán **Self-Healing** (Active Repair) để vá từng ô dữ liệu bị hỏng, sau đó kiểm chứng khả năng phục hồi hiệu năng.")
        
    st.markdown("---")
    st.subheader("Số lượng mẫu đánh giá (Testset Samples)")
    if baseline_metrics:
        st.metric(label="Tổng số câu hỏi được dùng để đánh giá", value=baseline_metrics.get("samples", 0))

elif page == "2. Phương pháp Tiêm lỗi (Corruption)":
    st.title("🦠 Phân tích Phương pháp Tiêm lỗi")
    st.markdown("Dữ liệu gốc đã bị tiêm các loại nhiễu (Noise) để mô phỏng sự cố thực tế.")
    
    if corruption_log:
        # Xử lý log để đếm số lượng từng loại lỗi
        error_counts = {}
        for log in corruption_log:
            etype = log.get("type", "unknown")
            # Nếu là add_duplicates có paper_ids list
            if etype == "add_duplicates" and "paper_ids" in log:
                error_counts[etype] = error_counts.get(etype, 0) + len(log["paper_ids"])
            # Nếu là drop có details
            elif etype == "drop_key_testset_records" and "Dropped IDs" in log.get("details", ""):
                # Đếm số ID (xấp xỉ bằng số phẩy + 1)
                ids_str = log["details"].split("[")[1].split("]")[0]
                count = len(ids_str.split(",")) if ids_str else 0
                error_counts[etype] = error_counts.get(etype, 0) + count
            else:
                error_counts[etype] = error_counts.get(etype, 0) + 1
                
        df_errors = pd.DataFrame(list(error_counts.items()), columns=["Loại lỗi (Corruption Type)", "Số lượng bị tiêm"])
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(df_errors, use_container_width=True, hide_index=True)
            
        with col2:
            fig = px.pie(df_errors, values='Số lượng bị tiêm', names='Loại lỗi (Corruption Type)', 
                         title='Phân bổ các loại lỗi dữ liệu',
                         hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
            
        st.markdown("""
        ### Giải thích các loại lỗi:
        - **blank_summary**: Mô phỏng lỗi scrap thiếu dữ liệu (rỗng trường text).
        - **inject_noise**: Chèn chuỗi `[SYSTEM ERROR]` vào văn bản để làm rối loạn Embedding.
        - **truncate_title**: Cắt ngắn tiêu đề bài báo.
        - **add_duplicates**: Nhân bản bài viết (lỗi Kafka gửi message nhiều lần).
        - **stale_date**: Sửa ngày xuất bản thành năm 2000 (lỗi Cache trả về dữ liệu cũ).
        - **drop_key_testset_records**: Xóa hoàn toàn bản ghi (lỗi rơi rớt dữ liệu mạng).
        """)
    else:
        st.warning("Không tìm thấy dữ liệu `corruption_log.json`.")

elif page == "3. Chỉ số & Báo cáo (Metrics)":
    st.title("📈 Báo cáo Chỉ số RAG (Metrics Comparison)")
    
    if baseline_metrics and corrupted_metrics and repaired_metrics:
        # Chuẩn bị dữ liệu
        metrics_names = ["Hit Rate", "Token F1", "Judge Score"]
        
        baseline_vals = [
            baseline_metrics.get("retrieval_hit_rate", 0),
            baseline_metrics.get("mean_token_f1", 0),
            baseline_metrics.get("mean_judge_score", 0)
        ]
        
        corrupted_vals = [
            corrupted_metrics.get("retrieval_hit_rate", 0),
            corrupted_metrics.get("mean_token_f1", 0),
            corrupted_metrics.get("mean_judge_score", 0)
        ]
        
        repaired_vals = [
            repaired_metrics.get("retrieval_hit_rate", 0),
            repaired_metrics.get("mean_token_f1", 0),
            repaired_metrics.get("mean_judge_score", 0)
        ]
        
        df_compare = pd.DataFrame({
            "Metric": metrics_names,
            "Baseline (Sạch)": baseline_vals,
            "Corrupted (Lỗi)": corrupted_vals,
            "Repaired (Đã sửa)": repaired_vals
        })
        
        st.subheader("Bảng so sánh tổng quát")
        # Format df để hiển thị đẹp hơn
        df_display = df_compare.copy()
        for col in ["Baseline (Sạch)", "Corrupted (Lỗi)", "Repaired (Đã sửa)"]:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.4f}")
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Biểu đồ sụt giảm và khôi phục hiệu năng")
        
        # Vẽ 3 biểu đồ cho 3 loại chỉ số
        col1, col2, col3 = st.columns(3)
        
        def plot_metric(metric_name, bas, cor, rep, color_scale):
            fig = go.Figure(data=[
                go.Bar(name='Baseline', x=['Baseline'], y=[bas], marker_color='#2ca02c'),
                go.Bar(name='Corrupted', x=['Corrupted'], y=[cor], marker_color='#d62728'),
                go.Bar(name='Repaired', x=['Repaired'], y=[rep], marker_color='#1f77b4')
            ])
            fig.update_layout(title=metric_name, showlegend=False, height=400)
            return fig
            
        with col1:
            st.plotly_chart(plot_metric("Retrieval Hit Rate", baseline_vals[0], corrupted_vals[0], repaired_vals[0], None), use_container_width=True)
        with col2:
            st.plotly_chart(plot_metric("Token F1 Score", baseline_vals[1], corrupted_vals[1], repaired_vals[1], None), use_container_width=True)
        with col3:
            st.plotly_chart(plot_metric("LLM Judge Score (1-5)", baseline_vals[2], corrupted_vals[2], repaired_vals[2], None), use_container_width=True)
            
        st.success("✅ **Kết luận:** Dữ liệu lỗi làm suy giảm đáng kể các chỉ số (đặc biệt là Token F1 và Judge Score). Tính năng Active Repair đã khôi phục thành công các chỉ số trở lại mức Baseline ban đầu.")

elif page == "4. Trực quan RAG Q&A":
    st.title("💬 Trực quan hóa RAG Q&A")
    st.markdown("So sánh câu trả lời của AI cho **cùng một câu hỏi** ở 3 luồng dữ liệu khác nhau.")
    
    if baseline_ans and corrupted_ans and repaired_ans:
        # Chọn câu hỏi
        question_ids = [q["id"] for q in baseline_ans]
        selected_id = st.selectbox("Chọn một câu hỏi (ID):", question_ids)
        
        # Tìm dữ liệu của ID đó trong 3 luồng
        b_item = next((item for item in baseline_ans if item["id"] == selected_id), None)
        c_item = next((item for item in corrupted_ans if item["id"] == selected_id), None)
        r_item = next((item for item in repaired_ans if item["id"] == selected_id), None)
        
        if b_item and c_item and r_item:
            st.markdown(f"### ❓ Câu hỏi:\n> **{b_item['question']}**")
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.success("🟢 1. Luồng Baseline (Sạch)")
                ans = b_item.get('answer', '').strip()
                st.markdown(f"**Câu trả lời:**\n{ans if ans else '*(Không có câu trả lời)*'}")
                with st.expander("Xem Document Truy xuất (Context)"):
                    st.write(b_item.get("retrieved_contexts", ["No context"])[0][:500] + "...")
                    
            with col2:
                st.error("🔴 2. Luồng Corrupted (Lỗi)")
                ans = c_item.get('answer', '').strip()
                st.markdown(f"**Câu trả lời:**\n{ans if ans else '*(AI từ chối trả lời hoặc trả về chuỗi rỗng do không tìm thấy ngữ cảnh)*'}")
                with st.expander("Xem Document Truy xuất (Context)"):
                    st.write(c_item.get("retrieved_contexts", ["No context"])[0][:500] + "...")
                    
            with col3:
                st.info("🔵 3. Luồng Repaired (Đã sửa)")
                ans = r_item.get('answer', '').strip()
                st.markdown(f"**Câu trả lời:**\n{ans if ans else '*(Không có câu trả lời)*'}")
                with st.expander("Xem Document Truy xuất (Context)"):
                    st.write(r_item.get("retrieved_contexts", ["No context"])[0][:500] + "...")
                    
            st.markdown("---")
            st.markdown("### 🔍 Phân tích của LLM Judge (Trích xuất từ luồng lỗi)")
            # Tìm xem có Judge info không
            judge_info = c_item.get("judge_info", {})
            if judge_info:
                st.warning(f"**Lý do AI trả lời sai:** {judge_info.get('reason', 'Không có')}")
                st.metric("Điểm (Corrupted)", judge_info.get("score", "N/A"))
            else:
                st.write("Không có dữ liệu Judge cho câu hỏi này.")
        else:
            st.error("Không tìm thấy dữ liệu đồng bộ cho ID này.")
    else:
        st.warning("Dữ liệu câu trả lời chưa sẵn sàng.")
