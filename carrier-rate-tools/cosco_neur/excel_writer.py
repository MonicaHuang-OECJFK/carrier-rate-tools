from openpyxl import load_workbook


def update_excel_rates(excel_path, rates):

    wb = load_workbook(excel_path)
    sheet = wb.active


    # --- Step 1: copy OLD rates ---
    for row in range(5, 98):
        sheet[f"AA{row}"] = sheet[f"H{row}"].value
        sheet[f"AB{row}"] = sheet[f"I{row}"].value
        sheet[f"AC{row}"] = sheet[f"J{row}"].value

    # --- Step 2: group ---
    bremerhaven_rates = [r for r in rates if r["POL"] == "BREMERHAVEN"]
    hamburg_rates = [r for r in rates if r["POL"] == "HAMBURG"]

    # --- Step 3: write BREMERHAVEN ---
    row = 5
    for r in bremerhaven_rates:
        sheet[f"H{row}"] = r["20"]
        sheet[f"I{row}"] = r["40"]
        sheet[f"J{row}"] = r["40HC"]
        row += 1


    # --- Step 4: write HAMBURG ---
    row = 26
    for r in hamburg_rates:
        sheet[f"H{row}"] = r["20"]
        sheet[f"I{row}"] = r["40"]
        sheet[f"J{row}"] = r["40HC"]
        row += 1

    wb.save(excel_path)