import streamlit as st

st.set_page_config(page_title="Carrier PDF Rate Tools", layout="centered")

st.title("📦 Carrier PDF Rate Tools")
st.write("Select the carrier you want to update:")

st.page_link("pages/1_ONE_TAWB.py", label="ONE TAWB", icon="📄")
st.page_link("pages/2_COSCO_NEUR.py", label="COSCO NEUR to USA", icon="📄")
st.page_link("pages/3_COSCO_Italy.py", label="COSCO Italy to USA", icon="📄")
st.page_link("pages/4_EMC_NEUR.py", label="EMC NEUR to USA", icon="📄")
st.page_link("pages/5_MSC_NEUR.py", label="MSC NEUR to USA", icon="📄")