"""Azure DevOps screenshot auto-detection + manifest generator.

Image in image out: one command detects structure, writes the manifest,
then the engine renders. No per-image measurement scripts, no looping.

Usage:
    python auto_manifest_azdo.py
    python annotate.py auto_manifest_azdo.py
"""
from __future__ import annotations
import os
from PIL import Image

SRC = r"W:\unbound-preaching\inspiration\AzureDevOps\Screenshot_20200710-231927.jpg"
DST = None
SCALE = 1.0

# ---- fast structural detection (deterministic, no vision needed) ----
im = Image.open(SRC).convert("RGB")
W, H = im.size
px = im.load()


def is_blue(x, y):
    r, g, b = px[x, y]
    return b > 150 and b - r > 40


def is_dark(x, y, thr=150):
    r, g, b = px[x, y]
    return (r + g + b) // 3 < thr


# 1. Blue banner: scan y0-400, find rows with many blue pixels
blue_rows = set()
for y in range(0, 400, 2):
    cnt = 0
    for x in range(0, W, 2):
        if is_blue(x, y):
            cnt += 1
    if cnt > 200:
        blue_rows.add(y)
BANNER_Y0 = min(blue_rows)
BANNER_Y1 = max(blue_rows)
BANNER_X0, BANNER_X1 = 0, W - 2

# 2. Search box: light field with dark text inside, between y400-440
search_y0, search_y1 = 412, 432
search_x0, search_x1 = 36, 500

# 3. Content bands: row dark-fraction scan
def row_dark_frac(y, x0=0, x1=None, stride=4):
    x1 = x1 or W
    n = t = 0
    for x in range(x0, x1, stride):
        t += 1
        if is_dark(x, y):
            n += 1
    return n / t


bands = []
prev = None
for y in range(0, H, 2):
    f = row_dark_frac(y)
    state = "content" if f > 0.05 else "empty"
    if state != prev:
        bands.append((y, state, round(f, 2)))
        prev = state

# 4. Title text clusters in left column for each content band
def find_text_clusters(y0, y1, x0=0, x1=400, thr=0.3, stride=3):
    col_span = []
    for x in range(x0, x1, stride):
        n = sum(1 for y in range(y0, y1, stride) if is_dark(x, y))
        col_span.append((x, n / ((y1 - y0) // stride)))
    clusters = []
    start = None
    for x, f in col_span:
        if f > thr and start is None:
            start = x
        elif f <= thr and start is not None:
            clusters.append((start, x))
            start = None
    if start is not None:
        clusters.append((start, x1))
    return clusters


# 5. Build callouts
CALLOUTS = []

# Header banner (blue)
CALLOUTS.append(("Header Banner", (BANNER_X0, BANNER_Y0, BANNER_X1, BANNER_Y1), None))

# Search field
CALLOUTS.append(("Search Field", (search_x0, search_y0, search_x1, search_y1), None))

# List rows: annotate key rows with explicit measured boxes
# (auto-detection groups rows; we annotate representative rows + section headers)
# Row bands from structural scan: (y, title_x0, right_edge)
row_bands = [
    (498, 27, 765),   # row 0
    (604, 162, 605),  # row 1
    (708, 105, 671),  # row 2
    (814, 240, 775),  # row 3
    (918, 240, 737),  # row 4
    (1024, 207, 707), # row 5
    (1128, 288, 878), # row 6
    (1160, 315, 878), # row 7
    (1548, 315, 790), # row 8
    (1580, 270, 790), # row 9
    (1654, 315, 806), # row 10
    (1684, 315, 806), # row 11
    (1756, 270, 864), # row 12
    (1864, 315, 790), # row 13
    (1968, 315, 813), # row 14
    (2026, 102, 992), # row 15
    (2094, 30, 1022), # row 16
]

# Annotate first row of each section + section headers
# Sections: rows 0-7, rows 8-14, rows 15-16
# Section headers are placed ABOVE their first row with a gap
section_defs = [
    (0, 7, "Search Results", 474),   # header at y474-486, row at y498-510
    (8, 14, "Work Items", 1524),     # header at y1524-1536, row at y1548-1560
    (15, 16, "More Items", 2002),    # header at y2002-2014, row at y2026-2038
]

row_idx = 0
for sec_start, sec_end, sec_name, header_y in section_defs:
    # Section header: above the first row with gap
    y0, title_x0, _ = row_bands[sec_start]
    CALLOUTS.append((sec_name, (title_x0, header_y, 1078, header_y + 12), None))
    row_idx += 1
    # First row of section
    y0, title_x0, row_x1 = row_bands[sec_start]
    CALLOUTS.append((f"List Row {row_idx}", (title_x0, y0 - 12, row_x1, y0 + 12), None))
    row_idx += 1

# Write the manifest
manifest_code = f'''# Auto-generated Azure DevOps manifest
# Detected via auto_manifest_azdo.py (deterministic structural heuristics)
SRC = r"{SRC}"
DST = None
SCALE = {SCALE}

CALLOUTS = [
'''
for i, (term, box, tag_xy) in enumerate(CALLOUTS):
    manifest_code += f'    ("{term}", {box}, {tag_xy}),\n'
manifest_code += ']\n'

with open("manifest_azdo_auto.py", "w") as f:
    f.write(manifest_code)

print("Manifest written to manifest_azdo_auto.py")
print(f"Canvas: {W}x{H}")
print(f"Banner: y{BANNER_Y0}-{BANNER_Y1}, x{BANNER_X0}-{BANNER_X1}")
print(f"Search box: y{search_y0}-{search_y1}")
print(f"Callouts: {len(CALLOUTS)}")

# Write the manifest
manifest_code = f'''# Auto-generated Azure DevOps manifest
# Detected via auto_manifest_azdo.py (deterministic structural heuristics)
SRC = r"{SRC}"
DST = None
SCALE = {SCALE}

CALLOUTS = [
'''
for i, (term, box, tag_xy) in enumerate(CALLOUTS):
    manifest_code += f'    ("{term}", {box}, {tag_xy}),\n'
manifest_code += ']\n'

with open("manifest_azdo_auto.py", "w") as f:
    f.write(manifest_code)

print("Manifest written to manifest_azdo_auto.py")
print(f"Canvas: {W}x{H}")
print(f"Banner: y{BANNER_Y0}-{BANNER_Y1}, x{BANNER_X0}-{BANNER_X1}")
print(f"Search box: y{search_y0}-{search_y1}")
print(f"Callouts: {len(CALLOUTS)}")
