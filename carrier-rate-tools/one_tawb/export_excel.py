from openpyxl import Workbook

def export_to_excel(data, output_path="ONE_output.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "ONE Rates"

    headers = [
        "Page",
        "Commodity",
        "Origin",
        "Destination",
        "Destination Via",
        "Type",
        "20",
        "40",
        "40HC",
        "Valid From",
        "Valid To"
    ]

    ws.append(headers)

    for block in data:
        commodity = block["commodity_label"]
        valid_from = block.get("valid_from")
        valid_to = block["valid_to"]

        for origin in block["origins"]:
            for r in origin["rates"]:
                ws.append([
                    r["page"],
                    commodity,
                    r["origin"],
                    r["destination"],
                    r["destination_via"],
                    r["type"],
                    r["20"],
                    r["40"],
                    r["40HC"],
                    valid_from,
                    valid_to
                ])

    wb.save(output_path)