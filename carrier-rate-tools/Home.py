import streamlit as st

st.set_page_config(page_title="Carrier PDF Rate Tools", layout="centered")

# Custom styling for bigger, card-style page links
st.markdown("""
<style>
    .stPageLink {
        padding: 12px 18px !important;
        border: 0.5px solid rgba(128,128,128,0.3) !important;
        border-radius: 12px !important;
        margin-bottom: 8px !important;
    }
    .stPageLink p {
        font-size: 18px !important;
        font-weight: 500 !important;
    }
    h1 {
        font-size: 32px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📦 Carrier PDF Rate Tools")
st.markdown("<p style='font-size:17px; color:gray;'>Select the carrier you want to update</p>", unsafe_allow_html=True)
st.write("")

st.page_link("pages/1_ONE_TAWB.py", label="ONE TAWB", icon="📄")
st.page_link("pages/2_COSCO_NEUR.py", label="COSCO NEUR to USA", icon="📄")
st.page_link("pages/3_COSCO_Italy.py", label="COSCO Italy to USA", icon="📄")
st.page_link("pages/4_EMC_NEUR.py", label="EMC NEUR to USA", icon="📄")
st.page_link("pages/5_MSC_NEUR.py", label="MSC NEUR to USA", icon="📄")