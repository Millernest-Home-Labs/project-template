"""Azure DevOps screenshot annotation manifest - 1080x2280, 1x.

Calibration ledger (measured via structural pixel scan, raw px = logical):
  term              | measured px              | box (padded)          | tag slot
  Header Banner     | blue y0-256, x0-1078     | (0,0,1078,256)        | (500,256) below
  Search Field      | light field y412-432     | (36,412,500,432)      | (36,432) below
  Search Results    | section header y486-510  | (27,474,1078,510)     | (27,474) right
  List Row 1        | title x27-765, y498-510  | (27,486,765,510)      | (27,510) below
  Work Items        | section header y1536-1560| (315,1524,1078,1560)  | (315,1524) right
  List Row 3        | title x315-790, y1548-1560| (315,1536,790,1560)  | (315,1560) below
  More Items        | section header y2014-2038| (102,2002,1078,2038)  | (102,2002) right
  List Row 5        | title x102-992, y2026-2038| (102,2014,992,2038) | (102,2038) below
"""
SRC = r"W:\unbound-preaching\inspiration\AzureDevOps\Screenshot_20200710-231927.jpg"
DST = None
SCALE = 1.0

CALLOUTS = [
    ("Header Banner", (0, 0, 1078, 256), (500, 268)),
    ("Search Field",  (36, 412, 500, 432), None),
    ("Search Results", (27, 474, 1078, 510), None),
    ("List Row 1",    (27, 498, 765, 510), None),
    ("Work Items",    (315, 1524, 1078, 1536), None),
    ("List Row 3",    (315, 1548, 790, 1560), None),
    ("More Items",    (102, 2002, 1078, 2014), None),
    ("List Row 5",    (102, 2026, 992, 2038), None),
]
