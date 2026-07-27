import streamlit as st
import tempfile
import os
from datetime import date
from cosco_neur.cosco_parser import extract_us_inland
from cosco_neur.excel_writer import update_us_inland_only

st.set_page_config(page_title="COSCO NEUR US Inland Parser", layout="centered")
st.title("COSCO NEUR US Inland Rate Updater")


st.markdown("""
### 📌 What this tool does
- ✍️ Updates only the **US inland** tab in the cheatsheet
- 🚂 Extracts **US inland 20DV / 40DV/40HQ (/ 40RF/40RQ)** rates from a
  standalone COSCO NEUR US inland PDF

### ⚠️ Important Notes
- Use this page when COSCO sends the US inland rates as their **own separate
  PDF**, instead of together with the Ocean Freight PDF. For a combined PDF,
  use the main COSCO NEUR page instead.
""")

st.markdown("<br>", unsafe_allow_html=True)

pdf_file   = st.file_uploader("Upload COSCO NEUR US Inland PDF", type="pdf")
excel_file = st.file_uploader("Upload Cheatsheet (xlsx)", type="xlsx")

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
                ramp_rows = extract_us_inland(pdf_path)

                if not ramp_rows:
                    st.error("❌ Couldn't find a US inland rate table in this PDF.")
                    st.session_state.pop("cosco_neur_inland_results", None)
                else:
                    file_name = f"COSCO NEUR US Inland Eff {date.today().strftime('%m-%d-%Y')}.xlsx"
                    out_path = excel_path.replace(".xlsx", "_updated.xlsx")

                    updated, skipped, mismatched = update_us_inland_only(
                        excel_path, ramp_rows, output_path=out_path,
                    )

                    # Read bytes into memory now — the temp file gets deleted
                    # below, but a rerun (e.g. from clicking the download
                    # button) must not lose this data.
                    with open(out_path, "rb") as f:
                        file_bytes = f.read()

                    # Persist results in session_state so clicking the
                    # download button (which triggers a rerun) doesn't wipe
                    # the results.
                    st.session_state["cosco_neur_inland_results"] = {
                        "updated":    updated,
                        "mismatched": mismatched,
                        "file_name":  file_name,
                        "file_bytes": file_bytes,
                    }

            except ValueError as e:
                st.error(f"❌ Error: {e}")
                st.session_state.pop("cosco_neur_inland_results", None)
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                st.session_state.pop("cosco_neur_inland_results", None)
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
if "cosco_neur_inland_results" in st.session_state:
    data = st.session_state["cosco_neur_inland_results"]

    st.success(f"✅ Updated {data['updated']} US inland rows")

    if data["mismatched"]:
        with st.expander(f"⚠️ {len(data['mismatched'])} "
                          f"US inland rows skipped — Location matched but "
                          f"Routing via didn't (not written, please check)"):
            for row_num, location, cs_via, pdf_via in data["mismatched"][:20]:
                st.text(f"  row {row_num}: Location={location}  "
                        f"cheatsheet Routing via={cs_via}  PDF VIA POD={pdf_via}")

    st.download_button(
        "📥 Download",
        data["file_bytes"],
        file_name=data["file_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_neur_inland",
    )
