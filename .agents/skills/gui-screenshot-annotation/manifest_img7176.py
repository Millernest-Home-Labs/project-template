# manifest_img7176.py - Amminox Today screen, single output
# Rules applied: no Status Bar, specific names, one representative per repeated element.
# All boxes = measured chrome bounds + margin (>=12px/side).
SRC = r"E:\Documents\Working\amminox\inspiration\IMG_7176.PNG"
DST = r"E:\Documents\Working\amminox\inspiration\IMG_7176-annotated.png"
SCALE = 1.0
BRIGHT_THRESHOLD = 45

CALLOUTS = [
    # --- header ---
    ("Go Premium Button", (806, 229, 1099, 339), (37, 580)),       # subscription upsell CTA
    ("Streak Badge", (1177, 256, 1270, 314), (560, 580)),          # daily-log streak counter
    # --- summary cards ---
    ("Calories Card", (37, 647, 1282, 909), (37, 646)),            # daily calorie budget (below, gap)
    ("Macros Card", (36, 909, 1283, 1254), (36, 1254)),            # carb/fat/protein breakdown
    # --- ad ---
    ("Banner Ad", (162, 1374, 1157, 1703), (400, 1308)),           # third-party ad
    ("Upgrade Text Link", (252, 1720, 1068, 1777), (560, 1777)),   # ad-free upsell link
    ("Section Header", (47, 1833, 212, 1896), (47, 1777)),         # "Meals"
    ("Text Link", (1038, 1837, 1274, 1900), (1038, 1777)),         # View diary
    # --- meals list (one representative card) ---
    ("Meal List Card", (36, 1927, 1283, 2164), (36, 2164)),        # Breakfast row card
    ("Leading Icon", (106, 2004, 181, 2079), (100, 1938)),         # meal type icon
    ("List Cell Label", (214, 2005, 444, 2065), (460, 1938)),      # "Breakfast"
    ("Overflow Menu", (914, 2018, 985, 2053), (600, 2053)),        # per-meal more actions
    ("Log Button", (1034, 1975, 1229, 2097), (1034, 2097)),        # log meal CTA
    # --- navigation ---
    ("Tab Bar", (55, 2610, 1054, 2813), (55, 2544)),               # bottom navigation
    ("Add FAB", (1059, 2607, 1268, 2816), (760, 2535)),            # add food entry
]
