import re
from collections import defaultdict
import pandas as pd


def extract_specs(text):
    specs = {}

    ordered_fields = [
        ("Quotation No", r"Tag ID\s*[:=]?\s*([\w-]+)"),
        ("Project ID", r"Project\s*=\s*([^\n]+)"),
        ("Design Standard", r"Design Basis\s*[:=]?\s*([^\n]+)"),
        ("Annexes Used", r"Annexes Used\s*[:=]?\s*([^\n]+)"),
        ("Internal Pressure", r"Design Internal Pressure\s*[:=]?\s*([^\n]+)"),
        ("External Pressure", r"Design External Pressure\s*[:=]?\s*([^\n]+)"),
        ("Tank Diameter", r"D of Tank\s*=\s*([\d.]+)"),
        ("Outside Diameter", r"OD of Tank\s*[:=]?\s*([\d.]+)"),
        ("Inside Diameter", r"ID of Tank\s*[:=]?\s*([\d.]+)"),
        ("Shell Height", r"Shell Height\s*=\s*([\d.]+)"),
        ("Standard Gravity (SG)", r"S\.G of Contents\s*[:=]?\s*([\d.]+)"),
        ("Liquid Level", r"Max Design Liq\. Level\s*[:=]?\s*([\d.]+)"),
        ("Design Temperature", r"Design Temperature\s*[:=]?\s*([^\n]+)"),
        ("MDMT", r"\bMDMT\s*[:=]?\s*([^\n]+)"),
        ("Roof Live Load", r"Roof Live Load\s*[:=]?\s*([^\n]+)"),
        ("Wind Speed", r"Design Wind Speed.*?=\s*([\d.]+\s*mph)"),
    ]

    for field, pattern in ordered_fields:
        match = re.search(pattern, text, re.IGNORECASE)
        specs[field] = match.group(1).strip() if match else "Not found"

    shell_matches = re.findall(
        r"Shell\s*\((\d+)\)\s*[A-Z0-9\-]+\s*:\s*([\d.]+)\s*in", text
    )
    for course_num, thickness in shell_matches:
        specs[f"Shell Course {course_num} Thickness"] = f"{thickness} in"

    match_ss = re.search(r"Ss\s*\(g\)\s*=\s*([\d.]+)", text)
    match_s1 = re.search(r"S1\s*\(g\)\s*=\s*([\d.]+)", text)
    specs["Seismic Design"] = (
        f"{match_ss.group(1)}, {match_s1.group(1)}"
        if match_ss and match_s1
        else "Not found"
    )

    shell_widths = []
    capture = False
    for line in text.splitlines():
        if "Shell Width" in line:
            capture = True
            continue
        if capture:
            if "Shell Weight" in line or "Weight CA" in line:
                break
            line = line.strip()
            if re.match(r"^\d+\s+\d+", line):
                try:
                    width = int(re.findall(r"^\d+\s+(\d+)", line)[0])
                    if 30 <= width <= 120:
                        shell_widths.append(str(width))
                except:
                    continue

    specs["Shell - Size"] = ", ".join(shell_widths) if shell_widths else "Not found"

    shell_course_numbers = re.findall(r"Shell\s*\((\d+)\)", text)
    specs["Shell - Quantity"] = (
        str(max(map(int, shell_course_numbers)))
        if shell_course_numbers
        else "Not found"
    )

    match = re.search(r"Roof\s*Type\s*[:=]\s*(.+)", text, re.IGNORECASE)
    specs["Roof Type"] = match.group(1).strip() if match else "Not found"

    match = re.search(r"Plates Material\s*=\s*(.+)", text)
    specs["Roof Material"] = match.group(1).strip() if match else "Not found"

    match = re.search(
        r"Roof.*?\bt\.actual\s*=\s*([\d.]+)\s*in", text, re.IGNORECASE | re.DOTALL
    )
    specs["Roof Thickness"] = match.group(1) + " in" if match else "Not found"

    match = re.search(r"Bottom Material\s*[:=]?\s*(.+)", text)
    specs["Bottom Material"] = match.group(1).strip() if match else "Not found"

    match = re.search(
        r"Bottom.*?\bt\.actual\s*=\s*([\d.]+)\s*in", text, re.IGNORECASE | re.DOTALL
    )
    specs["Bottom Thickness"] = match.group(1) + " in" if match else "Not found"

    match = re.search(
        r"Top Member.*?Material\s*=\s*([^\n]+)", text, re.IGNORECASE | re.DOTALL
    )
    specs["Rim Angle Material"] = match.group(1).strip() if match else "Not found"

    match = re.search(
        r"Top Member.*?Size\s*=\s*([^\n]+)", text, re.IGNORECASE | re.DOTALL
    )
    specs["Rim Angle Size"] = match.group(1).strip() if match else "Not found"

    match = re.search(
        r"Anchors.*?Quantity\s*=\s*(\d+)", text, re.IGNORECASE | re.DOTALL
    )
    specs["Anchors Quantity"] = match.group(1) if match else "Not found"

    match = re.search(r"Size\s*=\s*([\d.]+\s*in)", text, re.IGNORECASE)
    specs["Anchors Size"] = match.group(1).strip() if match else "Not found"

    match = re.search(r"Material\s*=\s*([A-Z0-9\-]+)", text, re.IGNORECASE)
    specs["Anchors Material"] = match.group(1).strip() if match else "Not found"

    match = re.search(r"c\s*=\s*([\d.]+)\s*in", text)
    specs["Top Plate Thickness (in)"] = match.group(1) if match else "Not found"

    a = re.search(r"a\s*=\s*([\d.]+)\s*in", text)
    b = re.search(r"b\s*=\s*([\d.]+)\s*in", text)
    specs["Top Plate Size"] = f"{a.group(1)}, {b.group(1)}" if a and b else "Not found"

    specs["Anchor Chair Quantity"] = specs.get("Anchors Quantity", "Not found")

    try:
        quantity = int(specs["Anchors Quantity"])
        specs["Vertical Plate Quantity"] = str(quantity * 2)
    except:
        specs["Vertical Plate Quantity"] = "Not found"

    h = re.search(r"h\s*=\s*([\d.]+)\s*in", text)
    specs["Vertical Plate Size"] = (
        f"{b.group(1)}, {h.group(1)}" if b and h else "Not found"
    )

    match = re.search(r"j\s*=\s*([\d.]+)\s*in", text)
    specs["Vertical Plate Thickness"] = match.group(1) if match else "Not found"

    return specs


def get_nozzle_blind_flags(text):
    lines = text.splitlines()
    blind_map = {}
    current_block = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        current_block.append(stripped)

        nozzle_label_match = re.match(r"^(\d{4})\s+NOZZLE$", stripped.upper())
        if nozzle_label_match:
            nozzle_number = nozzle_label_match.group(1)
            nozzle_id = f"Nozzle-{nozzle_number}"
            block_text = " ".join(current_block).upper()
            has_blind = "W/ BLIND" in block_text
            print(f"[BLIND DETECT] {nozzle_id}: {'Yes' if has_blind else 'No'}")
            blind_map[nozzle_id] = "Yes" if has_blind else "No"
            current_block = []

    return blind_map


def extract_nozzles(text):
    blind_flags = get_nozzle_blind_flags(text)

    nozzle_blocks = re.findall(
        r"(Roof|Shell) Nozzle: (Nozzle-(\d+))\s+(.*?)(?=(Roof|Shell) Nozzle:|Roof Manway:|$)",
        text,
        re.DOTALL,
    )

    grouped_data = {}

    for _, nozzle_id, _, block, *_ in nozzle_blocks:
        size_match = re.search(
            r"NOZZLE Description\s*:\s*(\d+) in SCH (\d+)[\S]* TYPE (\w+)", block
        )
        if not size_match:
            continue

        size, sch, typ = size_match.groups()
        key = (size, sch, typ)

        if key not in grouped_data:
            grouped_data[key] = {
                "QTY": 0,
                "Blind Count": 0,
                "Repad Required": "No",
                "Repad OD": "",
                "Repad Thickness": "",
            }

        grouped_data[key]["QTY"] += 1
        if blind_flags.get(nozzle_id, "No") == "Yes":
            grouped_data[key]["Blind Count"] += 1

        has_repad_text = "Reinforcement Pad is required" in block
        t_rpr_match = re.search(r"t_rpr\s*=\s*([\d.]+)\s*in", block)
        t_rpr_val = float(t_rpr_match.group(1)) if t_rpr_match else 0
        repad_required = has_repad_text and t_rpr_val > 0

        if repad_required:
            repad_od_match = re.search(
                r"Repad Size \(OD\) Must be = (\d+\.?\d*) in", block
            )
            grouped_data[key]["Repad Required"] = "Yes"
            grouped_data[key]["Repad OD"] = (
                repad_od_match.group(1) if repad_od_match else ""
            )
            grouped_data[key]["Repad Thickness"] = f"{t_rpr_val:.4f}"

    result = []
    for (size, sch, typ), info in grouped_data.items():
        result.append(
            {
                "QTY": info["QTY"],
                "Size": f'{size}"',
                "SCH": sch,
                "Type": typ,
                "With Blind": info["Blind Count"],
                "Repad Required": info["Repad Required"],
                "Repad OD (in)": info["Repad OD"],
                "Repad Thickness (in)": info["Repad Thickness"],
            }
        )

    return result


def extract_manways(text):
    manway_match = re.search(r"(Roof Manway:.*?)(?=\n\s*\n|$)", text, re.DOTALL)
    if not manway_match:
        return []

    block = manway_match.group(1)
    size_match = re.search(r"MANWAY Description\s*:\s*(\d+)", block)
    neck_match = re.search(r"Neck Thickness\s*([\d.]+)", block)

    size = size_match.group(1) if size_match else "Unknown"
    neck_thk = neck_match.group(1) if neck_match else "Unknown"

    has_repad_text = "Reinforcement Pad is required" in block
    t_rpr_match = re.search(r"t_rpr\s*=\s*([\d.]+)\s*in", block)
    t_rpr_val = float(t_rpr_match.group(1)) if t_rpr_match else 0
    repad_required = has_repad_text and t_rpr_val > 0

    repad_od_match = re.search(r"Repad Size \(OD\) Must be = (\d+\.?\d*) in", block)

    return [
        {
            "QTY": 1,
            "Size": f'{size}"',
            "Neck Thickness (in)": neck_thk,
            "Type": "",
            "Repad Required": "Yes" if repad_required else "No",
            "Repad OD (in)": repad_od_match.group(1) if repad_od_match else "",
            "Repad Thickness (in)": f"{t_rpr_val:.4f}" if repad_required else "",
        }
    ]
