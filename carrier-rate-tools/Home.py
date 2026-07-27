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
        font-size: 19px;
        font-weight: 700;
        white-space: normal;
        line-height: 1.6;
    }
    div[data-testid="stButton"] > button p {
        font-size: 19px !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("## 📦 Carrier PDF Rate Tools")
st.markdown("### Select the carrier you want to update")
st.write("")

carriers = [
    ("📄\n\n\nONE TAWB", "pages/1_ONE_TAWB.py"),
    ("📄\n\n\nCOSCO NEUR to USA", "pages/2_COSCO_NEUR.py"),
    ("📄\n\n\nCOSCO NEUR US Inland", "pages/2_COSCO_NEUR_US_Inland.py"),
    ("📄\n\n\nCOSCO Italy to USA", "pages/3_COSCO_Italy.py"),
    ("📄\n\n\nEMC NEUR to USA", "pages/4_EMC_NEUR.py"),
    ("📄\n\n\nMSC NEUR to USA", "pages/5_MSC_NEUR.py"),
]

cols = st.columns(3)
for i, (label, page) in enumerate(carriers):
    with cols[i % 3]:
        if st.button(label, key=f"btn_{i}", use_container_width=True):
            st.switch_page(page)