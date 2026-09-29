"""Analyze the Azure DevOps screenshot to find content elements."""
from PIL import Image

im = Image.open(r"W:\unbound-preaching\inspiration\AzureDevOps\Screenshot_20200710-231927.jpg").convert("RGB")
W, H = im.size
px = im.load()

print("=== NON-WHITE PIXELS in y=400-1000 ===")
for y in range(400, 1000):
    non_white = []
    for x in range(0, W):
        r, g, b = px[x, y]
        if not (r > 240 and g > 240 and b > 240):
            non_white.append((x, r, g, b))
    if non_white:
        clusters = []
        start = non_white[0]
        prev = non_white[0]
        for px_x, r, g, b in non_white[1:]:
            if px_x - prev[0] <= 3:
                prev = (px_x, r, g, b)
            else:
                clusters.append((start[0], prev[0]))
                start = (px_x, r, g, b)
                prev = (px_x, r, g, b)
        clusters.append((start[0], prev[0]))
        print(f"y={y}: {clusters}")
