import streamlit as st
import tempfile
import os
from datetime import date
from cosco_neur.cosco_parser import extract_ocean_rates, extract_us_inland
from cosco_neur.excel_writer import update_cheatsheet

st.title("COSCO NEUR to USA Rate Updater")


st.markdown("""
### 📌 What this tool does
- 📄 Extracts **Ocean Freight rates** from COSCO NEUR PDF 
- ✍️ Updates **OFT 20DV / 40DV/40HQ** in the cheatsheet
- 🚂 If the PDF includes US inland rates, also extracts and updates
  **US inland 20DV / 40DV/40HQ (/ 40RF/40RQ)** — otherwise this step is
  skipped

### ⚠️ Important Notes
- If a PDF has **new or removed** POL/POD lanes, remember to add/delete the
  corresponding row in the cheatsheet, and add the matching pair to the **Mapping**
  tab with the **exact** POL/POD spelling as it appears in the PDF extraction
""")

st.markdown("<br>", unsafe_allow_html=True)

pdf_file   = st.file_uploader("Upload COSCO NEUR PDF", type="pdf")
excel_file = st.file_uploader("Upload Cheatsheet (xlsx, must contain Mapping tab)", type="xlsx")

if st.button("Run"):
    if pdf_file and excel_file:
        with st.spinner("Processing..."):
            pdf_path = excel_path = out_path = None
            try:
                # Save uploads to temp files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(pdf_file.read())
                    pdf_path = tmp_pdf.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
                    tmp_excel.write(excel_file.read())
                    excel_path = tmp_excel.name

                # Extract from PDF
                all_rates = extract_ocean_rates(pdf_path)
                ramp_rows = extract_us_inland(pdf_path)   # [] if this PDF has no Location table

                file_name = f"COSCO NEUR to USA Eff {date.today().strftime('%m-%d-%Y')}.xlsx"
                out_path = excel_path.replace(".xlsx", "_updated.xlsx")

                result = update_cheatsheet(
                    excel_path, all_rates,
                    ramp_rows=ramp_rows,
                    output_path=out_path,
                )

                # Read bytes into memory now — the temp file gets deleted
                # below, but a rerun (e.g. from clicking the download button)
                # must not lose this data.
                with open(out_path, "rb") as f:
                    file_bytes = f.read()

                # Persist results in session_state so clicking the download
                # button (which triggers a rerun) doesn't wipe the results.
                st.session_state["cosco_neur_results"] = {
                    "has_inland": bool(ramp_rows),
                    "file_name":  file_name,
                    "result":     result,
                    "file_bytes": file_bytes,
                }

            except ValueError as e:
                st.error(f"❌ Error: {e}")
                st.session_state.pop("cosco_neur_results", None)
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                st.session_state.pop("cosco_neur_results", None)
                raise
            finally:
                for path in [pdf_path, excel_path, out_path]:
                    if path:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass
    else:
        st.warning("Please upload both PDF and Cheatsheet.")

# Render persisted results — this runs on every rerun (including the one
# triggered by clicking the download button), so results stay on screen.
if "cosco_neur_results" in st.session_state:
    data = st.session_state["cosco_neur_results"]
    result = data["result"]

    if not data["has_inland"]:
        st.info("ℹ️ This PDF doesn't include a US inland Location table — "
                "the US inland tab was left untouched.")

    st.success(f"✅ Updated {result['oft_updated']} OFT rows, "
               f"{result['inland_updated']} US inland rows")

    if result["inland_mismatched"]:
        with st.expander(f"⚠️ {len(result['inland_mismatched'])} "
                          f"US inland rows skipped — Location matched but "
                          f"Routing via didn't (not written, please check)"):
            for row_num, location, cs_via, pdf_via in result["inland_mismatched"][:20]:
                st.text(f"  row {row_num}: Location={location}  "
                        f"cheatsheet Routing via={cs_via}  PDF VIA POD={pdf_via}")

    st.download_button(
        "📥 Download",
        data["file_bytes"],
        file_name=data["file_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_neur",
    )
