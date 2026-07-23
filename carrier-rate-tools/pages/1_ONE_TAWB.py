import streamlit as st
import tempfile
import os

from one_tawb.ONE_parser import parse_one_pdf
from one_tawb.export_excel import export_to_excel



# =========================
# UI
# =========================

st.set_page_config(page_title="ONE PDF Parser", layout="centered")

st.title("📄 ONE Contract → Excel Tool")

st.markdown("""
### 📌 What this tool does
- Extracts Ocean Freight rates  
- Filters **DRY** containers only  
- Maps **Origin → Destination → Rates → Valid Date**

---
### ⚠️ Important Note
- If the PDF contains **both old and updated validity dates** (e.g., crossed-out or revised dates),
  the result may be **incorrect or outdated**.

👉 Please verify the correct validity period in the original PDF when multiple dates are present.
""")


# =========================
# Upload
# =========================

pdf_file = st.file_uploader("Upload PDF", type=["pdf"])


# =========================
# Run button
# =========================

if pdf_file is not None:

    if st.button("🚀 Run Parser"):

        with st.spinner("Processing PDF..."):

            # 👉 存暫存 PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_pdf.write(pdf_file.read())
                pdf_path = tmp_pdf.name

            # 👉 parse
            data = parse_one_pdf(pdf_path)

            # 👉 存 Excel
            output_path = pdf_path.replace(".pdf", ".xlsx")
            export_to_excel(data, output_path)

        st.success("✅ Processing complete!")

        # =========================
        # Download
        # =========================

        with open(output_path, "rb") as f:
            st.download_button(
                label="📥 Download Excel",
                data=f,
                file_name="ONE_output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # =========================
        # Debug info（可選）
        # =========================

        # with st.expander("🔍 Debug Info"):
        #     st.write(f"Total blocks: {len(data)}")

        #     if len(data) > 0:
        #         st.write("Sample block:")
        #         st.json(data[0])

        # 清掉暫存檔（optional）
        os.remove(pdf_path)
        os.remove(output_path)