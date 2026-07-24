"""
cosco_parser.py（COSCO NEUR 線）
────────────────────────────────
從 COSCO NEUR（荷比德 → USA）PDF 萃取 Ocean Freight rate：
  POL / POD / rate_20 / rate_40

設計原則：跟 cosco italy 線一樣，從 header 列讀取欄位語意，
不 hardcode col 號。

PDF 結構：每個 service（TAE / EAG / ELSA...）各自一頁，各一張表格，
header 固定含 "Port of Discharge"、"20DV"、"40DV/40HQ" 等關鍵字。
POL 欄是合併儲存格，且常常把多個港口寫在同一格
（例如 "Rotterdam, Antwerp, Bremerhaven"），要用逗號拆開成多筆。

這支只萃取 Ocean Freight rate，不處理任何 surcharge。

依賴：pip install pdfplumber
用法：python cosco_parser.py <path_to_pdf>
"""

import re
import sys
import pdfplumber


# ── 工具函式 ──────────────────────────────────────────────────

def clean(val):
    if val is None:
        return ""
    return str(val).replace("\n", " ").strip()


def parse_rate(val):
    """
    '$ 1 .600,00' → 1600（歐式千位分隔逗號小數，中間偶爾夾雜多餘空格）
    沒有 $ 或抓不到數字就回傳 None。
    """
    s = clean(val)
    if "$" not in s:
        return None
    s = s.replace("$", "").replace(" ", "")   # 去掉 $ 跟所有空格（含中間的漂移空格）
    s = s.replace(".", "").replace(",", ".")   # 1.600,00 → 1600.00
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


# ── Header 解析 ───────────────────────────────────────────────

def build_col_map(header_row):
    """
    從 header 找 pol / pod / term / rate_20 / rate_40 欄。
    回傳 {field: col_index}（找不到就不在 dict 裡）。
    """
    keywords = {
        "pol":     "pol",
        "pod":     "port of discharge",
        "term":    "term",
        "rate_20": "20dv",
        "rate_40": "40dv",
    }
    mapping = {}
    for col, val in enumerate(header_row):
        v = clean(val).lower()
        for field, kw in keywords.items():
            if field not in mapping and kw in v:
                mapping[field] = col
    return mapping


def is_rate_table(header_row):
    header_text = " ".join(clean(v) for v in header_row).lower()
    return "port of discharge" in header_text


def is_location_table(header_row):
    header_text = " ".join(clean(v) for v in header_row).lower()
    return "location" in header_text and "routing via" in header_text


# ── 已知的 PDF 地名錯字修正 ──────────────────────────────────────
# 供應商 PDF 裡固定會出現的錯字，直接在這裡加一行就能修正，
# 不用動萃取邏輯。只做明確、已知的地名修正，不做通用拼字校正。
_KNOWN_LOCATION_TYPOS = [
    (re.compile(r"\bKanas City\b", re.IGNORECASE), "Kansas City"),
]


def _fix_known_typos(location):
    for pattern, replacement in _KNOWN_LOCATION_TYPOS:
        location = pattern.sub(replacement, location)
    return location


# ── US Inland（Location）表格 ───────────────────────────────────

def build_location_col_map(header_row):
    """
    從 US inland 的 Location 表格 header 找欄位。用「完全相等」比對
    （不是 substring），避免 'Location' 跟 'Location type' 互相誤判。

    回傳 {field: col_index}（找不到就不在 dict 裡）。
    """
    keywords = {
        "location":      "location",
        "location_type": "location type",
        "routing_via":   "routing via",
        "rate_20":       "20dv",
        "rate_40":       "40dv/40hq",
        "rate_40rf":     "40rf/40rq",
    }
    mapping = {}
    for col, val in enumerate(header_row):
        v = clean(val).lower()
        for field, kw in keywords.items():
            if field not in mapping and v == kw:
                mapping[field] = col
    return mapping


def _parse_location_table(table):
    col_map = build_location_col_map(table[0])

    loc_col   = col_map.get("location")
    type_col  = col_map.get("location_type")
    via_col   = col_map.get("routing_via")
    r20_col   = col_map.get("rate_20")
    r40_col   = col_map.get("rate_40")
    r40rf_col = col_map.get("rate_40rf")   # 這欄常常整份 PDF 都是空的，可省略

    if loc_col is None or via_col is None or r20_col is None or r40_col is None:
        return []

    results = []
    for row in table[1:]:
        if not row:
            continue

        location = clean(row[loc_col]) if loc_col < len(row) else ""
        if not location:
            continue
        location = _fix_known_typos(location)

        location_type = clean(row[type_col]) if type_col is not None and type_col < len(row) else ""
        routing_via   = clean(row[via_col]) if via_col < len(row) else ""
        rate_20       = parse_rate(row[r20_col]) if r20_col < len(row) else None
        rate_40       = parse_rate(row[r40_col]) if r40_col < len(row) else None
        rate_40rf     = None
        if r40rf_col is not None and r40rf_col < len(row):
            rate_40rf = parse_rate(row[r40rf_col])

        results.append({
            "location":      location,
            "location_type": location_type,
            "routing_via":   routing_via,
            "rate_20":       rate_20,
            "rate_40":       rate_40,
            "rate_40rf":     rate_40rf,
        })

    return results


def extract_us_inland(pdf_path):
    """
    萃取 US inland 的 Location 表格（Location / Location type / Routing Via /
    20DV / 40DV/40HQ / 40RF/40RQ）。

    這張表不是每期 PDF 都有 —— 掃描全部頁面找不到就回傳空 list，
    呼叫端只要檢查回傳是不是空的，決定要不要寫入 US inland tab。

    回傳 list of dict：
      {"location", "location_type", "routing_via", "rate_20", "rate_40", "rate_40rf"}
    """
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table or not table[0]:
                    continue
                if not is_location_table(table[0]):
                    continue
                rows = _parse_location_table(table)
                if rows:
                    return rows
    return []


# ── 主要萃取邏輯 ──────────────────────────────────────────────

def _parse_table(table):
    """
    萃取單一表格內的 rate 列。
    POL 合併儲存格 fill-down，並用逗號拆成多個港口（分開輸出多筆）。
    """
    header = table[0]
    col_map = build_col_map(header)

    pol_col  = col_map.get("pol")
    pod_col  = col_map.get("pod")
    term_col = col_map.get("term")
    r20_col  = col_map.get("rate_20")
    r40_col  = col_map.get("rate_40")

    # 缺少關鍵欄位就不是我們要的 rate 表格
    if pol_col is None or pod_col is None or r20_col is None or r40_col is None:
        return []

    results = []
    current_pol = None

    for row in table[1:]:
        if not row:
            continue

        pol_cell = clean(row[pol_col]) if pol_col < len(row) else ""
        if pol_cell:
            current_pol = pol_cell   # 合併儲存格 fill-down

        pod = clean(row[pod_col]) if pod_col < len(row) else ""

        if term_col is not None:
            term = clean(row[term_col]) if term_col < len(row) else ""
            if term.upper() != "CY/CY":
                continue

        if not current_pol or not pod:
            continue

        rate_20 = parse_rate(row[r20_col]) if r20_col < len(row) else None
        rate_40 = parse_rate(row[r40_col]) if r40_col < len(row) else None

        # POL 可能是 "Rotterdam, Antwerp, Bremerhaven" 這種合併寫法，
        # 用逗號拆開成多筆（各自視為獨立 POL）。保留 PDF 原始大小寫，
        # 不在這裡轉大寫 —— 比對時才轉，方便肉眼核對萃取結果跟 PDF 是否一致。
        for pol in [p.strip() for p in current_pol.split(",") if p.strip()]:
            results.append({
                "pol":     pol,
                "pod":     pod,
                "rate_20": rate_20,
                "rate_40": rate_40,
            })

    return results


def extract_ocean_rates(pdf_path):
    """
    掃描整份 PDF 每一頁的每個表格，凡是 header 含 "Port of Discharge"
    的都當作 Ocean Freight rate 表格，全部萃取結果合併成一個 list
    （不分頁、不分 service）。

    回傳 list of dict：{"pol", "pod", "rate_20", "rate_40"}
    """
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table or not table[0]:
                    continue
                if not is_rate_table(table[0]):
                    continue
                results.extend(_parse_table(table))
    return results


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "cosco_neur.pdf"
    rates = extract_ocean_rates(path)
    print(f"\n── Ocean Freight rates ({len(rates)} rows) ──")
    for r in rates:
        print(r)

    ramp_rows = extract_us_inland(path)
    if ramp_rows:
        print(f"\n── US Inland ({len(ramp_rows)} rows) ──")
        for r in ramp_rows:
            print(r)
    else:
        print("\n── US Inland: not present in this PDF ──")
