# manifest_azure_devops.py
# Azure DevOps page screenshot (1080x2280 @3x, logical 360x840)
SRC = r"W:\unbound-preaching\inspiration\AzureDevOps\Screenshot_20200710-231927.jpg"
DST = None
SCALE = 3.0

CALLOUTS = [
    # (term, (x0,y0,x1,y1) logical, tag_xy logical or None)
    ("Status Bar", (0, 0, 360, 49), None),          # top bar with app name/time
    ("App Bar",    (0, 260, 360, 360), None),       # dark header with logo + nav
    ("Search Box", (120, 400, 240, 430), None),     # search input field
    ("List Cell",  (0, 500, 360, 540), None),       # first list item
    ("List Cell",  (0, 560, 360, 600), None),       # second list item
    ("Action Button", (0, 610, 360, 640), None),    # red action button
    ("List Cell",  (0, 700, 360, 740), None),       # third list item
    ("Tab Bar",    (0, 2100, 360, 2280), None),     # bottom tab bar
]

def run_assertions(rgb_img, H):
    # Verify status bar is purple/blue
    H.assert_band(rgb_img, x=180, y_lo=0, y_hi=49, min_bright=100)
    # Verify content area is white
    H.assert_band(rgb_img, x=180, y_lo=400, y_hi=410, min_bright=240)
