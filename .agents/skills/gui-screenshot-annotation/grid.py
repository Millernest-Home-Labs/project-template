"""Draw a labeled coordinate grid on a screenshot for precise annotation.

Usage: python grid.py <input.png> <output.png> [step]
"""
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = "C:/Windows/Fonts/consola.ttf"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    img = Image.open(src).convert("RGBA")
    d = ImageDraw.Draw(img)
    W, H = img.size
    try:
        f = ImageFont.truetype(FONT, 16)
    except OSError:
        f = ImageFont.load_default()
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=(255, 0, 0, 110), width=1)
        d.text((x + 2, 2), str(x), fill=(255, 60, 60, 230), font=f)
        d.text((x + 2, H - 20), str(x), fill=(255, 60, 60, 230), font=f)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=(255, 0, 0, 110), width=1)
        d.text((2, y + 2), str(y), fill=(255, 60, 60, 230), font=f)
        d.text((W - 55, y + 2), str(y), fill=(255, 60, 60, 230), font=f)
    img.convert("RGB").save(dst, "PNG")
    print(f"saved {dst} ({W}x{H}) step={step}")


if __name__ == "__main__":
    main()
