import streamlit as st
from cosco_neur.cosco_parser import parse_cosco_pdf
from cosco_neur.excel_writer import update_excel_rates

import tempfile

st.title("SBS Rate Updater")

pdf_file = st.file_uploader("Upload PDF", type="pdf")
excel_file = st.file_uploader("Upload Excel", type="xlsx")

if st.button("Run"):

    if pdf_file and excel_file:

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(pdf_file.read())
            pdf_path = tmp_pdf.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
            tmp_excel.write(excel_file.read())
            excel_path = tmp_excel.name

        rates = parse_cosco_pdf(pdf_path)
        update_excel_rates_test(excel_path, rates)

        with open(excel_path, "rb") as f:
            st.download_button(
                "Download Updated Excel",
                f,
                file_name="updated_cheatsheet.xlsx"
            )

    else:
        st.warning("Please upload both PDF and Excel.")