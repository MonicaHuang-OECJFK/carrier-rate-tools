"""
msc_extract.py
──────────────
從 MSC (Mediterranean Shipping Company) Ocean Freight Quotation PDF
萃取 POL / POD / 20DV / 40DV(HC) 運費。

MSC 的報價單目前看過兩種版型，這支腳本會自動偵測是哪一種：

【版型 A】POD 用完整城市名稱，逐列列出
    OCEAN FREIGHT & SURCHARGES        20DV    40DV/HC
    From Antwerp, Rotterdam to United
    Ocean Freight
    States
    Baltimore              USD 1925.00   USD 2050.00
    Boston                 USD 2225.00   USD 2350.00
    Surcharges
    ...
  → POL 從 "From <POL> to" 這行抓（可能是 "Antwerp, Rotterdam" 複合來源，
    用逗號拆開）。POD 就是城市名稱本身。純文字 extract_text() 就能處理，
    這個版型的列不會跨行斷行。

【版型 B】POL/POD 用港口代碼（如 USBAL、BEANR），多個代碼可能共用一列
    OCEAN FREIGHT & SURCHARGES 20DV 40DV/HC
    BEANR / NLRTM - USBAL Ocean Freight USD 1925.00 USD 2050.00
    BEANR / NLRTM - USHOU / USMOB / USMSY / USPEF Ocean Freight USD 1525.00 USD 1650.00
    Surcharges
    ...
  → 這個版型不能只靠純文字逐行解析：如果一列的港口代碼太多，PDF 會把
    代碼清單換成兩行，但費率數字仍然固定在第一行右側，會導致純文字
    抽出來的行序錯亂（例如換行後的代碼被排到下一列費率的後面）。
    改用 page.extract_words() 拿到每個字的座標 (x0, top)，把每一列
    切成「左半部：POL/POD 代碼」跟「右半部：Ocean Freight + 費率」
    兩欄，各自依座標順序重組文字，就不會因為換行而錯位。
  → 港口代碼要轉換回城市名稱，才能跟 Mapping tab／版型 A 的輸出格式
    一致。轉換表同樣用座標拆欄的方式，從文件裡的「Port(s) of Loading /
    Port(s) of Discharge」那段動態解析出來（例如 "Antwerp (BEANR)"、
    "Baltimore (USBAL)"），不是寫死的字典。
  → 一列可能同時列多個 POL 代碼、多個 POD 代碼（用 "/" 分隔），
    會展開成每個 POL × 每個 POD 各一筆獨立資料列。

兩種版型輸出格式一致：
    [{'pol': 'Antwerp', 'pod': 'Baltimore', 'rate_20': 1925, 'rate_40': 2050}, ...]

依賴：pip install pdfplumber
用法：python msc_extract.py <path_to_pdf>
"""

import re
import sys
import pdfplumber


def _clean_num(val):
    """'1925.00' → 1925（運費都是整數美元，去掉 .00）"""
    try:
        return int(float(val))
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────
# 版型 A：完整城市名稱逐列列出（純文字即可解析）
# ─────────────────────────────────────────────────────────

def _try_extract_format_a(text):
    """成功回傳 list of dict，偵測不到這個版型則回傳 None。"""
    pol_match = re.search(r"From (.+?) to", text)
    if not pol_match:
        return None

    block_match = re.search(
        r"Ocean Freight\s*\n\s*States\s*\n(.*?)\nSurcharges",
        text,
        re.DOTALL,
    )
    if not block_match:
        return None

    pols = [p.strip() for p in pol_match.group(1).strip().split(",") if p.strip()]
    if not pols:
        pols = [""]

    line_pattern = re.compile(r"^(.+?)\s+USD\s+([\d.]+)\s+USD\s+([\d.]+)\s*$")

    results = []
    for line in block_match.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        m = line_pattern.match(line)
        if not m:
            continue
        pod, rate_20_raw, rate_40_raw = m.groups()
        rate_20 = _clean_num(rate_20_raw)
        rate_40 = _clean_num(rate_40_raw)
        for pol in pols:
            results.append({
                "pol": pol,
                "pod": pod.strip(),
                "rate_20": rate_20,
                "rate_40": rate_40,
            })

    return results if results else None


# ─────────────────────────────────────────────────────────
# 版型 B：港口代碼版（用座標拆欄，避免換行錯位）
# ─────────────────────────────────────────────────────────

_CODE_NAME_PATTERN = re.compile(r"([A-Za-z][A-Za-z .,]*?)\s*\(([A-Z]{5})\)")


def _build_code_name_map(words):
    """
    從「Port(s) of Loading / Port(s) of Discharge」這段（左右兩欄）
    解析出 {代碼: 城市名稱} 字典。左右欄用每個字的 x0 座標跟兩個欄位
    標題的中點來區分，不用純文字的縮排猜測（縮排在兩欄剛好擠在同一
    視覺行時會失準）。
    """
    loading_hdr = next((w for w in words if w["text"] == "Loading"), None)
    discharge_hdr = next((w for w in words if w["text"] == "Discharge"), None)
    costs_hdr = next((w for w in words if w["text"] == "COSTS"), None)
    if not (loading_hdr and discharge_hdr and costs_hdr):
        return {}

    threshold = (loading_hdr["x0"] + discharge_hdr["x0"]) / 2
    section = [w for w in words if loading_hdr["top"] < w["top"] < costs_hdr["top"]]
    left = sorted([w for w in section if w["x0"] < threshold], key=lambda w: (w["top"], w["x0"]))
    right = sorted([w for w in section if w["x0"] >= threshold], key=lambda w: (w["top"], w["x0"]))

    left_text = " ".join(w["text"] for w in left)
    right_text = " ".join(w["text"] for w in right)

    code_name = {}
    for name, code in _CODE_NAME_PATTERN.findall(left_text):
        code_name[code] = name.strip()
    for name, code in _CODE_NAME_PATTERN.findall(right_text):
        code_name[code] = name.strip()

    return code_name


def _try_extract_format_b(words):
    """成功回傳 list of dict，偵測不到這個版型則回傳 None。"""
    hdr_word = next((w for w in words if w["text"] == "SURCHARGES"), None)
    end_word = next((w for w in words if w["text"] == "Surcharges"), None)
    if not (hdr_word and end_word):
        return None

    section = [w for w in words if hdr_word["top"] < w["top"] < end_word["top"]]
    ocean_word = next((w for w in section if w["text"] == "Ocean"), None)
    if not ocean_word:
        return None
    threshold = ocean_word["x0"] - 5

    left = sorted([w for w in section if w["x0"] < threshold], key=lambda w: (w["top"], w["x0"]))
    right = sorted([w for w in section if w["x0"] >= threshold], key=lambda w: (w["top"], w["x0"]))
    left_text = " ".join(w["text"] for w in left)
    right_text = " ".join(w["text"] for w in right)

    dash_idx = left_text.find("-")
    if dash_idx == -1:
        return None
    pol_pattern = left_text[:dash_idx].strip()
    if not pol_pattern:
        return None

    # 用 POL 代碼 + "-" 當分隔符，把左欄文字切回每一筆 POD 代碼群組
    # （不管代碼清單有沒有跨行斷行，因為左欄文字已經是依座標重組過的）
    parts = re.split(re.escape(pol_pattern) + r"\s*-\s*", left_text)
    pod_groups = [p.strip() for p in parts if p.strip()]

    rate_pairs = re.findall(r"USD\s+([\d.]+)\s+USD\s+([\d.]+)", right_text)

    if not pod_groups or len(pod_groups) != len(rate_pairs):
        return None  # 筆數對不上，安全起見不猜，交給呼叫端報錯

    pol_codes = [c.strip() for c in pol_pattern.split("/") if c.strip()]
    code_name = _build_code_name_map(words)

    results = []
    for pod_group, (rate_20_raw, rate_40_raw) in zip(pod_groups, rate_pairs):
        pod_codes = [c.strip() for c in pod_group.split("/") if c.strip()]
        rate_20 = _clean_num(rate_20_raw)
        rate_40 = _clean_num(rate_40_raw)
        for pol_code in pol_codes:
            pol_name = code_name.get(pol_code, pol_code)
            for pod_code in pod_codes:
                pod_name = code_name.get(pod_code, pod_code)
                results.append({
                    "pol": pol_name,
                    "pod": pod_name,
                    "rate_20": rate_20,
                    "rate_40": rate_40,
                })

    return results


# ─────────────────────────────────────────────────────────
# 生效日期（Effective Date）
# ─────────────────────────────────────────────────────────

_EFFECTIVE_DATE_PATTERN = re.compile(
    r"Effective Date\s*-\s*Expiration Date\s+(\d{2})-(\d{2})-(\d{4})"
)


def extract_effective_date(pdf_path):
    """
    從 PDF 的 VALIDITY 區塊抓「Effective Date - Expiration Date」的起始日期，
    例如 "Effective Date - Expiration Date 01-07-2026 - 31-08-2026" → 該行日期
    是 DD-MM-YYYY，回傳時轉成 MM-DD-YYYY 字串（例如 "07-01-2026"），
    抓不到則回傳 None。
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

    m = _EFFECTIVE_DATE_PATTERN.search(text or "")
    if not m:
        return None

    day, month, year = m.groups()
    return f"{month}-{day}-{year}"


# ─────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────

def extract(pdf_path):
    """
    回傳 list of dict：
    [{'pol': 'Antwerp', 'pod': 'Baltimore',
      'rate_20': 1925, 'rate_40': 2050}, ...]

    自動偵測版型 A（城市名稱）或版型 B（港口代碼），
    兩種都試過還是抓不到才報錯。
    """
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
        words = page.extract_words()

    result = _try_extract_format_a(text)
    if result is not None:
        return result

    result = _try_extract_format_b(words)
    if result is not None:
        return result

    raise ValueError(
        "找不到可辨識的運費區塊，這份 PDF 的版型跟目前支援的兩種"
        "（城市名稱版 / 港口代碼版）都不一樣，需要另外檢查格式"
    )


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "msc.pdf"
    rows = extract(path)
    print(f"Total: {len(rows)} rows")
    for r in rows:
        print(r)
