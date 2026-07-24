import streamlit as st

st.set_page_config(page_title="Carrier PDF Rate Tools", layout="centered")

st.markdown("""
<style>
    div[data-testid="stButton"] > button {
        aspect-ratio: 1;
        border-radius: 12px;
        border: 0.5px solid rgba(128,128,128,0.3);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 600;
        white-space: normal;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📦 Carrier PDF Rate Tools")
st.markdown("Select the carrier you want to update")
st.write("")

carriers = [
    ("📄\n\nONE TAWB", "pages/1_ONE_TAWB.py"),
    ("📄\n\nCOSCO NEUR to USA", "pages/2_COSCO_NEUR.py"),
    ("📄\n\nCOSCO Italy to USA", "pages/3_COSCO_Italy.py"),
    ("📄\n\nEMC NEUR to USA", "pages/4_EMC_NEUR.py"),
    ("📄\n\nMSC NEUR to USA", "pages/5_MSC_NEUR.py"),
]

cols = st.columns(3)
for i, (label, page) in enumerate(carriers):
    with cols[i % 3]:
        if st.button(label, key=f"btn_{i}", use_container_width=True):
            st.switch_page(page)