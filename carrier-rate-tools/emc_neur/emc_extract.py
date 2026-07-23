"""
emc_extract.py
──────────────
從 Evergreen (EMC) PDF 萃取 POL / POD / 2SD / 4SD / 4SH。

結構說明：
  - 資料分佈在多頁，每頁有一張 table
  - Header 是 ['POL', 'POD', '2SD', '4SD', '4SH', ...]
  - 欄位乾淨，直接用 pdfplumber table 萃取

依賴：pip install pdfplumber
用法：python emc_extract.py <path_to_pdf>
"""

import re
import sys
import pdfplumber


def clean(val):
    if val is None:
        return ""
    return str(val).replace("\n", " ").strip()

def parse_rate(val):
    """
    '2,250' → 2250 ; '1.200' (EU thousands sep) → 1200

    運費欄位永遠是整數美元，不會有小數，所以「,」和「.」
    只可能是千位分隔符，兩個符號一律去掉即可，不用判斷格式。
    """
    val = clean(val).replace(",", "").replace(".", "")
    try:
        return int(val)
    except ValueError:
        return None

def is_header_row(row):
    """判斷這列是不是 header（POL / POD / 2SD 都在）"""
    vals = [clean(v).upper() for v in row]
    return "POL" in vals and "POD" in vals and "2SD" in vals

def extract(pdf_path):
    """
    回傳 list of dict：
    [{'pol': 'ANTWERP', 'pod': 'NEW YORK, NY', '2sd': 1550, '4sd': 1750, '4sh': 1750}, ...]
    """
    results = []

    # col mapping 跨頁沿用（Page 2 之後可能沒有 header）
    pol_col = pod_col = sd2_col = sd4_col = sh4_col = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                # 找 header 列的 index
                header_idx = None
                for i, row in enumerate(table):
                    if is_header_row(row):
                        header_idx = i
                        break

                if header_idx is not None:
                    # 更新 col mapping
                    header = [clean(v).upper() for v in table[header_idx]]
                    try:
                        pol_col = header.index("POL")
                        pod_col = header.index("POD")
                        sd2_col = header.index("2SD")
                        sd4_col = header.index("4SD")
                        sh4_col = header.index("4SH")
                    except ValueError:
                        continue
                    data_start = header_idx + 1
                else:
                    # 沒有 header，沿用上一頁的 col mapping
                    if pol_col is None:
                        continue
                    data_start = 0

                # 萃取資料列
                for row in table[data_start:]:
                    if max(pol_col, pod_col, sd2_col, sd4_col, sh4_col) >= len(row):
                        continue
                    pol = clean(row[pol_col])
                    pod = clean(row[pod_col])

                    if not pol or not pod:
                        continue

                    sd2 = parse_rate(row[sd2_col])
                    sd4 = parse_rate(row[sd4_col])
                    sh4 = parse_rate(row[sh4_col])

                    if sd2 is None:
                        continue

                    results.append({
                        "pol": pol,
                        "pod": pod,
                        "2sd": sd2,
                        "4sd": sd4,
                        "4sh": sh4,
                    })

    # 去重（同 POL+POD 可能出現在多頁）
    seen = set()
    unique = []
    for r in results:
        key = (r["pol"], r["pod"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "evergreen.pdf"
    rows = extract(path)
    print(f"Total: {len(rows)} rows")
    for r in rows:
        print(r)
