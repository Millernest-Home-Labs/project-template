"""Red-markup GUI annotator -- STABLE ENGINE. Do not edit per image.

Draws red rounded rectangles around GUI elements with adjacent pill-shaped
NAME TAGS (number + term together - no cross-referencing legend needed).

Usage: python annotate.py <manifest.py> [source_image_override]

The MANIFEST is the only per-image artifact. It is a tiny Python file:

    # manifest_addfood.py
    SRC = r"E:\\...\\IMG_8013.PNG"   # clean source screenshot
    DST = None                       # default: <SRC stem>-annotated.png
    SCALE = 3.0                      # @3x screenshot: coords below are
                                     # logical points (440x956)
    CALLOUTS = [
        # (term, (x0,y0,x1,y1) logical, tag_xy logical or None)
        ("Status Bar", (0, 13, 440, 49), (70, 53)),
        ("Button",     (24, 58, 135, 109), None),   # None = auto-place
    ]

    # optional measured-fact assertions, fail loudly BEFORE drawing:
    def run_assertions(rgb_img, H):
        H.assert_band(rgb_img, x=220, y_lo=673, y_hi=681, min_bright=10)

Engine guarantees on every run (no per-image code):
  1. baked-markup gate  - exact annotation-red scan; aborts pre-annotated input
  2. validator          - tags on-canvas, no tag/tag overlap, no tag/box
                          crossing, no tag over bright source pixels
  3. auto-placement     - centered flush below/above/right/left, then a
                          vertical free-slot scan; first verified-open slot wins
  4. inclusive bounds   - touching is not overlapping
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

RED = (232, 58, 68, 255)          # annotation red (also the baked-markup probe)
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"
FONT_FALLBACK = "C:/Windows/Fonts/arial.ttf"


def load_font(size):
    for p in (FONT_PATH, FONT_FALLBACK):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_manifest(path):
    d = os.path.dirname(os.path.abspath(path))
    if d not in sys.path:
        sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location("gui_manifest", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gate_baked_markup(im, stride=10):
    px = im.load()
    W, H = im.size
    exact = 0
    for y in range(0, H, stride):
        for x in range(0, W, stride):
            if px[x, y] == RED[:3]:
                exact += 1
    return exact


def main():
    if len(sys.argv) < 2:
        print("usage: python annotate.py <manifest.py> [source_image_override]")
        raise SystemExit(2)
    mod = load_manifest(sys.argv[1])
    src = sys.argv[2] if len(sys.argv) > 2 else mod.SRC

    img = Image.open(src).convert("RGBA")
    W, H = img.size
    print("canvas:", W, H)

    baked = gate_baked_markup(img.convert("RGB"))
    print("baked-in markup red samples:", baked)
    if baked > 50:
        print("SOURCE LOOKS PRE-ANNOTATED - find the clean original. Aborting.")
        raise SystemExit(1)

    scale = float(getattr(mod, "SCALE", 1))
    u = W / 1320.0 * 1.5  # chrome metrics relative to 884-logical baseline
    font = load_font(int(26 * u))
    TAG_H = int(44 * u)
    TAG_R = TAG_H // 2
    PAD_X = int(11 * u)
    PAD_RIGHT = int(23 * u)
    NUM_R = int(15 * u)
    STROKE = max(3, int(4 * u))
    step_y = max(2, int(3 * u))
    step_x = max(6, int(8 * u))
    # Open-space brightness threshold. Dark themes have card/page backgrounds
    # above 40, which makes auto-placement impossible; manifests may override.
    bright_thresh = int(getattr(mod, "BRIGHT_THRESHOLD", 40))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    src_px = img.convert("RGB").load()

    def tag_rect(term, xy):
        tw = d.textlength(term, font=font)
        pw = NUM_R * 2 + PAD_X + PAD_RIGHT + int(tw)
        x, y = xy
        x = max(0, min(int(round(x)), W - pw))
        y = max(0, min(int(round(y)), H - TAG_H))
        return (x, y, x + pw, y + TAG_H)

    def overlaps(a, b):
        # inclusive bounds: touching is NOT overlapping
        return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])

    def area_is_open(tr):
        if tr[0] < 0 or tr[1] < 0 or tr[2] > W or tr[3] > H:
            return False
        for yy in range(tr[1], tr[3], step_y):
            for xx in range(tr[0], tr[2], step_x):
                r, g, b = src_px[xx, yy]
                if (r + g + b) // 3 > bright_thresh:
                    return False
        return True

    callouts = []
    for term, box, tag_xy in mod.CALLOUTS:
        sbox = tuple(int(round(v * scale)) for v in box)
        stag = None if tag_xy is None else (int(round(tag_xy[0] * scale)),
                                            int(round(tag_xy[1] * scale)))
        callouts.append([term, sbox, stag])

    # manifest assertions (measured facts) run BEFORE any drawing
    if hasattr(mod, "run_assertions"):
        from gui_annotation_helpers import Helpers
        Helpers.set_image(img.convert("RGB"))
        mod.run_assertions(img.convert("RGB"), Helpers)
        print("manifest assertions passed")

    # auto-place tags where tag_xy is None
    for i in range(len(callouts)):
        term, box, stag = callouts[i]
        if stag is not None:
            continue
        x0, y0, x1, y1 = box
        rep = tag_rect(term, (x0, y1))
        pw = rep[2] - rep[0]
        others_boxes = [callouts[j][1] for j in range(len(callouts)) if j != i]
        others_tags = [tag_rect(callouts[j][0], callouts[j][2])
                       for j in range(len(callouts)) if j != i and callouts[j][2]]
        cands = []
        cands.append((x0 + (x1 - x0) // 2 - pw // 2, y1))              # below
        cands.append((x0 + (x1 - x0) // 2 - pw // 2, y0 - TAG_H))      # above
        cands.append((x1, y0 + (y1 - y0) // 2 - TAG_H // 2))           # right
        cands.append((x0 - pw, y0 + (y1 - y0) // 2 - TAG_H // 2))      # left
        y = y0 - TAG_H                                                  # scan up
        while y > 0:
            cands.append((x0, y))
            y -= TAG_H // 2
        y = y1                                                          # scan down
        while y < H - TAG_H:
            cands.append((x0, y))
            y += TAG_H // 2
        pick = None
        for cand in cands:
            tr = tag_rect(term, cand)
            if not area_is_open(tr):
                continue
            if any(overlaps(tr, b) for b in others_boxes):
                continue
            if any(overlaps(tr, t2) for t2 in others_tags):
                continue
            pick = (tr[0], tr[1])
            break
        callouts[i][2] = pick or (x0, max(0, y0 - TAG_H))

    # ---- validation pass (final placements) ----
    tag_rects = []
    errors = []
    for i, (term, box, stag) in enumerate(callouts):
        tr = tag_rect(term, stag)
        if tr[0] < 0 or tr[1] < 0 or tr[2] > W or tr[3] > H:
            errors.append(f"{i+1} {term}: off-canvas {tr}")
        for j, (t2, _, s2) in enumerate(callouts):
            if j != i:
                tr2 = tag_rect(t2, s2)
                if overlaps(tr, tr2):
                    errors.append(f"{i+1} {term} tag overlaps {j+1} {t2} tag")
        for j, (t2, b2, _) in enumerate(callouts):
            if i == j:
                continue  # a tag may sit inside its own element's box region
            if overlaps(tr, b2):
                # ancestor-aware: crossing an ANCESTOR container is allowed
                # (nested element's tag lives inside the parent's bounds);
                # crossing a sibling or unrelated box is a defect.
                bi = box
                is_ancestor = (b2[0] <= bi[0] and b2[1] <= bi[1]
                               and b2[2] >= bi[2] and b2[3] >= bi[3])
                if not is_ancestor:
                    errors.append(f"{i+1} {term} tag crosses {j+1} {t2} box")
        for yy in range(tr[1], tr[3], step_y):
            bad = False
            for xx in range(tr[0], tr[2], step_x):
                r, g, b = src_px[xx, yy]
                if (r + g + b) // 3 > bright_thresh:
                    errors.append(f"{i+1} {term} tag covers bright pixel ({xx},{yy})")
                    bad = True
                    break
            if bad:
                break
        tag_rects.append(tr)

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        raise SystemExit(1)

    # ---- draw ----
    for term, box, _ in callouts:
        d.rounded_rectangle(box, radius=int(14 * u), outline=RED, width=STROKE)
    # leader lines for tags separated from their element (skill rule:
    # tasteful elbows, never diagonal shots; never crossing the box)
    for i, (term, box, stag) in enumerate(callouts):
        tr = tag_rect(term, stag)
        x0, y0, x1, y1 = box
        tcx = (tr[0] + tr[2]) / 2
        tcy = (tr[1] + tr[3]) / 2
        inside = (tr[0] >= x0 and tr[2] <= x1 and tr[1] >= y0 and tr[3] <= y1)
        touching = overlaps(tr, box) or (x0 <= tcx <= x1 and (tr[3] >= y0 - 2 and tr[1] <= y1 + 2)) \
            or (y0 <= tcy <= y1 and (tr[2] >= x0 - 2 and tr[0] <= x1 + 2))
        if inside or touching:
            continue
        if x0 <= tcx <= x1:
            # vertically aligned: straight vertical connector
            if tr[3] < y0:
                d.line([(tcx, tr[3]), (tcx, y0)], fill=RED, width=3)
            elif tr[1] > y1:
                d.line([(tcx, y1), (tcx, tr[1])], fill=RED, width=3)
        else:
            # beside/offset: elbow - vertical at the tag's near box edge,
            # then horizontal into the box edge midpoint
            lx = x0 - 12 if tcx < x0 else x1 + 12
            lx = max(2, min(lx, W - 2))
            ey = min(max(tcy, y0), y1)
            d.line([(lx, tr[1] if tr[1] > y1 else tr[3]), (lx, ey)], fill=RED, width=3)
            d.line([(lx, ey), (x0 if tcx < x0 else x1, ey)], fill=RED, width=3)
    for i, (term, box, stag) in enumerate(callouts):
        tr = tag_rect(term, stag)
        d.rounded_rectangle(tr, radius=TAG_R, fill=RED)
        cx, cy = tr[0] + PAD_X + NUM_R, tr[1] + TAG_H / 2
        d.ellipse((cx - NUM_R, cy - NUM_R, cx + NUM_R, cy + NUM_R),
                  fill=(255, 255, 255, 255))
        bb = d.textbbox((0, 0), str(i + 1), font=font)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]),
               str(i + 1), fill=RED, font=font)
        d.text((tr[0] + PAD_X + NUM_R * 2 + PAD_X, cy), term,
               fill=(255, 255, 255, 255), font=font, anchor="lm")

    dst = getattr(mod, "DST", None) or os.path.splitext(src)[0] + "-annotated.png"
    Image.alpha_composite(img, overlay).convert("RGB").save(dst, "PNG")
    for i, (term, box, _) in enumerate(callouts):
        tr = tag_rects[i]
        print(f"  {i+1}. {term}: box={box} tag=({tr[0]},{tr[1]})-({tr[2]},{tr[3]})")
    print(f"saved {dst} ({W}x{H}) - validation clean")

    try:
        ps = ("Add-Type -AssemblyName System.Windows.Forms; "
              f"[Windows.Forms.Clipboard]::SetImage("
              f"[System.Drawing.Image]::FromFile('{dst}'))")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       check=True, capture_output=True, timeout=15)
        print("copied to clipboard")
    except Exception as e:
        print(f"clipboard copy skipped: {e}")


if __name__ == "__main__":
    main()
