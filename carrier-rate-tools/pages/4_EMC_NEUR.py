import streamlit as st
import tempfile
import os
from datetime import date
from emc_neur.emc_extract import extract
from emc_neur.excel_writer import update_rates

st.title("EMC TAWB Rate Updater")


st.markdown("""
### 📌 What this tool does
- 📄 Extracts ocean freight rate **POL / POD / 2SD / 4SD / 4SH** from EMC PDF
- ✍️ Updates the **20' / 40' / 40'HC** columns in the cheatsheet

### ⚠️ Important Notes
- If the PDF has **new or removed** POL/POD lanes, remember to add/delete the
  corresponding row in the cheatsheet, with the **exact**
  POL/POD spelling as it appears in the PDF extraction
""")

st.markdown("<br>", unsafe_allow_html=True)

pdf_file   = st.file_uploader("Upload EMC PDF", type="pdf")
excel_file = st.file_uploader("Upload Cheatsheet (xlsx)", type="xlsx")

if st.button("Run"):
    if pdf_file and excel_file:
        with st.spinner("Processing..."):
            try:
                # Save uploads to temp files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(pdf_file.read())
                    pdf_path = tmp_pdf.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
                    tmp_excel.write(excel_file.read())
                    excel_path = tmp_excel.name

                output_path = excel_path.replace(".xlsx", "_updated.xlsx")

                # Extract rates from PDF
                all_rates = extract(pdf_path)

                # Write into cheatsheet
                updated_count, skipped = update_rates(
                    excel_path, all_rates, output_path=output_path
                )

                # Result summary
                st.success(f"✅ Updated {updated_count} rows successfully")

                # Download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        "📥 Download Updated Cheatsheet",
                        f,
                        file_name=f"EMC TAWB Cheat sheet {date.today().strftime('%m%d%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except ValueError as e:
                st.error(f"❌ Error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                raise
            finally:
                # Clean up temp files
                for path in [pdf_path, excel_path]:
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
    else:
        st.warning("Please upload both PDF and Cheatsheet.")
