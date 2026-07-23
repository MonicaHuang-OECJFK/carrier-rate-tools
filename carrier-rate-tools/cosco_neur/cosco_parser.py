import pdfplumber
import re

def normalize_rate(rate_str):
    if not rate_str:
        return None

    # 移除 $
    rate_str = rate_str.replace("$", "")

    # 移除空格
    rate_str = rate_str.replace(" ", "")

    # 處理歐洲格式 1.650,00 → 1650.00
    rate_str = rate_str.replace(".", "").replace(",", ".")

    return int(float(rate_str))


def parse_cosco_pdf(pdf_path):

    rates = []

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            tables = page.extract_tables()

            if not tables:
                continue

            for table in tables:

                # skip if not correct table
                header = table[0]

                if not header:
                    continue

                #print("\n=== HEADER RAW ===")
                #print(header)

                #print("=== HEADER INDEX ===")
                #for i, h in enumerate(header):
                    #print(f"col {i}: {h}")

                header_text = " ".join(str(h) for h in header if h)

                #print("=== HEADER TEXT ===")
                #print(header_text)

                if "Port of Discharge" not in header_text:
                    continue

                current_pol = None

                for row in table[1:]:

                    if not row:
                        continue

                    country = row[0]
                    pol_cell = row[1]
                    pod = row[2]
                    term = row[3]
                    rate20 = row[4]
                    rate40 = row[5]

                    # skip invalid row
                    if term != "CY/CY":
                        continue

                    # handle merged cell
                    if pol_cell:
                        current_pol = pol_cell

                    if not current_pol or not pod:
                        continue

                    pol = current_pol.split(",")[0].strip().upper()
                    pod = pod.strip().upper()

                    rate20 = normalize_rate(rate20)
                    rate40 = normalize_rate(rate40)

                    rates.append({
                        "POL": pol,
                        "POD": pod,
                        "20": rate20,
                        "40": rate40,
                        "40HC": rate40
                    })

    return rates