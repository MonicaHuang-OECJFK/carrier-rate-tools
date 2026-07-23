import pdfplumber
import re


# =========================
# Utils
# =========================

def normalize_rate(rate_str):
    if not rate_str:
        return None

    s = str(rate_str).replace("USD", "").replace("$", "").strip()

    if "/" in s:
        s = s.split("/")[-1]

    s = s.replace(",", "")

    try:
        return int(float(s))
    except:
        return None


def is_target_table(table):
    if not table or not table[0]:
        return False

    header = " ".join(str(h) for h in table[0] if h)
    return "Destination" in header and "Type" in header


def get_words(page):
    return page.extract_words(use_text_flow=True, keep_blank_chars=False)


# =========================
# Block markers
# =========================

def find_markers(words):
    markers = []

    i = 0
    while i < len(words):
        text = words[i]["text"].strip()

        # Case 1: 32) COMMODITY
        if re.fullmatch(r"\d+\)", text):
            if i + 1 < len(words) and "COMMODITY" in words[i + 1]["text"].upper():
                markers.append({
                    "type": "commodity",
                    "label": text[:-1],
                    "top": words[i]["top"]
                })
                i += 2
                continue

        # Case 2: 279 ) COMMODITY / 279 COMMODITY
        if re.fullmatch(r"\d+", text):
            window = " ".join(
                words[j]["text"].upper()
                for j in range(i + 1, min(i + 4, len(words)))
            )

            if "COMMODITY" in window:
                markers.append({
                    "type": "commodity",
                    "label": text,
                    "top": words[i]["top"]
                })
                i += 1
                continue

        # NOTE FOR COMMODITY
        if text == "<":
            phrase = " ".join(w["text"] for w in words[i:i+6]).upper()
            if "NOTE FOR COMMODITY" in phrase:
                markers.append({
                    "type": "note",
                    "top": words[i]["top"]
                })

        i += 1

    markers.sort(key=lambda x: x["top"])
    return markers


# =========================
# valid line（只抓第一個）
# =========================

def find_valid_line_position(words, y0, y1):
    lines = {}

    for w in words:
        if y0 <= w["top"] < y1:
            key = round(w["top"], 1)
            lines.setdefault(key, []).append(w["text"])

    sorted_lines = sorted(lines.items(), key=lambda x: x[0])

    note_seen = False

    for top, words_in_line in sorted_lines:
        line = " ".join(words_in_line)

        if "NOTE FOR COMMODITY" in line.upper():
            note_seen = True
            continue

        if not note_seen:
            continue

        # ⭐ 只抓第一個 valid
        m1 = re.search(r"Rates\s+are\s+valid\s+to\s+(\d{8})", line, re.IGNORECASE)
        if m1:
            return top, None, m1.group(1)

        m2 = re.search(
            r"Rates\s+are\s+valid\s+from\s+(\d{8})\s+to\s+(\d{8})",
            line,
            re.IGNORECASE
        )
        if m2:
            return top, m2.group(1), m2.group(2)

    return None, None, None


# =========================
# ORIGIN
# =========================

def get_origin_positions_in_region(words, y0, y1):
    region_words = [w for w in words if y0 <= w["top"] < y1]
    origins = []

    i = 0
    while i < len(region_words):
        if region_words[i]["text"].strip().upper() == "ORIGIN":
            line_top = region_words[i]["top"]
            j = i + 1

            while (
                j < len(region_words)
                and abs(region_words[j]["top"] - line_top) < 3
                and region_words[j]["text"].strip() == ":"
            ):
                j += 1

            origin_words = []
            while j < len(region_words):
                same_line = abs(region_words[j]["top"] - line_top) < 3
                if not same_line:
                    break
                origin_words.append(region_words[j]["text"])
                j += 1

            origin_text = " ".join(origin_words).strip()
            if origin_text:
                origins.append({
                    "origin": origin_text,
                    "top": line_top
                })

            i = j
        else:
            i += 1

    return origins


# =========================
# Build blocks
# =========================

def build_blocks(pdf):
    blocks = []
    current_block = None

    for page_idx, page in enumerate(pdf.pages):
        page_num = page_idx + 1
        words = get_words(page)
        markers = find_markers(words)

        for marker in markers:
            if marker["type"] == "commodity":
                if current_block:
                    blocks.append(current_block)

                current_block = {
                    "commodity_label": marker["label"],
                    "start_page": page_num,
                    "start_y": marker["top"],
                    "end_page": None,
                }

            elif marker["type"] == "note":
                if current_block:
                    current_block["end_page"] = page_num
                    blocks.append(current_block)
                    current_block = None

    return blocks


# =========================
# Parse block
# =========================

def parse_block(pdf, block):
    block_result = {
        "commodity_label": block["commodity_label"],
        "start_page": block["start_page"],
        "end_page": block["end_page"],
        "valid_to": None,
        "origins": []
    }

    carry_origin = None

    for page_num in range(block["start_page"], block["end_page"] + 1):
        page = pdf.pages[page_num - 1]
        words = get_words(page)

        y0 = block["start_y"] if page_num == block["start_page"] else 0
        y1 = float("inf")

        # ⭐ 只抓第一個 valid
        if page_num == block["end_page"]:
            valid_top, valid_from, valid_to = find_valid_line_position(words, y0, float("inf"))

            if valid_to:
                block_result["valid_to"] = valid_to
                block_result["valid_from"] = valid_from
                y1 = valid_top

        origins = get_origin_positions_in_region(words, y0, y1)

        tables = []
        for tb in page.find_tables():
            raw = tb.extract()
            if not is_target_table(raw):
                continue

            tb_top = tb.bbox[1]
            if y0 <= tb_top < y1:
                tables.append({
                    "type": "table",
                    "top": tb_top,
                    "raw": raw
                })

        events = (
            [{"type": "origin", "top": o["top"], "origin": o["origin"]} for o in origins]
            + tables
        )
        events.sort(key=lambda x: x["top"])

        current_origin = carry_origin

        for event in events:
            if event["type"] == "origin":
                current_origin = event["origin"]
                carry_origin = current_origin
                continue

            matched_origin = current_origin or carry_origin
            if not matched_origin:
                continue

            carry_origin = matched_origin

            if (
                not block_result["origins"]
                or block_result["origins"][-1]["origin"] != matched_origin
            ):
                block_result["origins"].append({
                    "origin": matched_origin,
                    "rates": []
                })

            current_origin_data = block_result["origins"][-1]

            for row in event["raw"][1:]:
                if not row or len(row) < 10:
                    continue

                if str(row[5]).strip().upper() != "DRY":
                    continue

                current_origin_data["rates"].append({
                    "origin": matched_origin,
                    "destination": str(row[0]).strip().upper(),
                    "destination_via": str(row[2]).strip().upper(),
                    "type": "DRY",
                    "20": normalize_rate(row[7]),
                    "40": normalize_rate(row[8]),
                    "40HC": normalize_rate(row[9]),
                    "page": page_num
                })

    block_result["origins"] = [o for o in block_result["origins"] if o["rates"]]

    return block_result


# =========================
# Main
# =========================

def parse_one_pdf(pdf_path):
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        blocks = build_blocks(pdf)

        for b in blocks:
            parsed = parse_block(pdf, b)

            if parsed["origins"] or parsed["valid_to"]:
                results.append(parsed)

    return results