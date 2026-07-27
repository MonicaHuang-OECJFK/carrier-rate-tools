import streamlit as st
import tempfile
import os
from datetime import date
from msc_neur.msc_extract import extract, extract_effective_date
from msc_neur.excel_writer import update_rates

st.set_page_config(page_title="MSC NEUR Parser", layout="centered")
st.title("MSC NEUR to USA Rate Updater")


st.markdown("""
### 📌 What this tool does
- 📄 Extracts ocean freight rates: **POL / POD / 20DV / 40DV(HC)** from MSC
  East Coast / West Coast / Gulf Coast PDFs
- ✍️ Updates the **20' / 40' / 40'HC** columns in the cheatsheet

### ⚠️ Important Notes
- MSC sends **three separate PDFs** (East Coast, West Coast, Gulf Coast) — upload all
  three below
- If a PDF has **new or removed** POL/POD lanes, remember to add/delete the
  corresponding row in the cheatsheet, and add the matching pair to the **Mapping**
  tab with the **exact** POL/POD spelling as it appears in the PDF extraction
""")

st.markdown("<br>", unsafe_allow_html=True)

east_pdf   = st.file_uploader("Upload East Coast PDF", type="pdf", key="east_pdf")
west_pdf   = st.file_uploader("Upload West Coast PDF", type="pdf", key="west_pdf")
gulf_pdf   = st.file_uploader("Upload Gulf Coast PDF", type="pdf", key="gulf_pdf")
excel_file = st.file_uploader("Upload Cheatsheet (xlsx)", type="xlsx", key="excel_file")

if st.button("Run"):
    if east_pdf and west_pdf and gulf_pdf and excel_file:
        with st.spinner("Processing..."):
            east_path = west_path = gulf_path = excel_path = None
            try:
                # Save uploads to temp files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_east:
                    tmp_east.write(east_pdf.read())
                    east_path = tmp_east.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_west:
                    tmp_west.write(west_pdf.read())
                    west_path = tmp_west.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_gulf:
                    tmp_gulf.write(gulf_pdf.read())
                    gulf_path = tmp_gulf.name

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
                    tmp_excel.write(excel_file.read())
                    excel_path = tmp_excel.name

                output_path = excel_path.replace(".xlsx", "_updated.xlsx")

                # Effective date, read from the East Coast PDF (falls back to today)
                eff_date = extract_effective_date(east_path) or date.today().strftime("%m-%d-%Y")

                # Extract rates from all three PDFs
                east_rates = extract(east_path)
                west_rates = extract(west_path)
                gulf_rates = extract(gulf_path)
                all_rates = east_rates + west_rates + gulf_rates

                # Write into cheatsheet
                updated_count, skipped_rows, formula_skipped = update_rates(
                    excel_path, all_rates, output_path=output_path
                )

                # Result summary
                st.success(f"✅ Updated {updated_count} rows successfully")
                st.markdown(f"""
                - East Coast: {len(east_rates)} rates extracted
                - West Coast: {len(west_rates)} rates extracted
                - Gulf Coast: {len(gulf_rates)} rates extracted
                """)

                if skipped_rows:
                    st.warning(
                        f"⚠️ {len(skipped_rows)} cheatsheet row(s) had no matching rate "
                        f"(check Mapping tab / POL-POD spelling)"
                    )
                    with st.expander("Show skipped rows"):
                        for row_num, pol, pod in skipped_rows:
                            st.write(f"Row {row_num}: {pol} / {pod}")

                # Download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        "📥 Download Updated Cheatsheet",
                        f,
                        file_name=f"MSC_Europe_eff_{eff_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except ValueError as e:
                st.error(f"❌ Error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                raise
            finally:
                # Clean up temp files
                for path in [east_path, west_path, gulf_path, excel_path]:
                    if path:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass
    else:
        st.warning("Please upload all three PDFs (East / West / Gulf) and the Cheatsheet.")
