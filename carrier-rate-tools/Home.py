import streamlit as st

st.set_page_config(page_title="Carrier PDF Rate Tools", layout="centered")

st.markdown("""
<style>
    .carrier-card {
        aspect-ratio: 1;
        background: rgba(128,128,128,0.05);
        border: 0.5px solid rgba(128,128,128,0.3);
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 16px;
        text-decoration: none !important;
        color: inherit !important;
    }
    .carrier-card:hover {
        border-color: rgba(128,128,128,0.6);
    }
    .carrier-icon {
        font-size: 28px;
        margin-bottom: 8px;
    }
    .carrier-label {
        font-size: 15px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📦 Carrier PDF Rate Tools")
st.markdown("Select the carrier you want to update")
st.write("")

carriers = [
    ("ONE TAWB", "pages/1_ONE_TAWB.py"),
    ("COSCO NEUR to USA", "pages/2_COSCO_NEUR.py"),
    ("COSCO Italy to USA", "pages/3_COSCO_Italy.py"),
    ("EMC NEUR to USA", "pages/4_EMC_NEUR.py"),
    ("MSC NEUR to USA", "pages/5_MSC_NEUR.py"),
]

cols = st.columns(3)
for i, (label, page) in enumerate(carriers):
    with cols[i % 3]:
        st.page_link(page, label=label, icon="📄", use_container_width=True)