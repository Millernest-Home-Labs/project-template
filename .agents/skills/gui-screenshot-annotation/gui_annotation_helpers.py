"""Shared measurement helpers for GUI screenshot annotation manifests.

Manifests call these inside run_assertions(rgb_img, Helpers) to pin
measured facts before the engine draws. Importable from the skill folder.
"""
from __future__ import annotations


class Helpers:
    _px = None
    _W = 0
    _H = 0

    @classmethod
    def set_image(cls, rgb_img):
        cls._px = rgb_img.load()
        cls._W, cls._H = rgb_img.size

    @classmethod
    def brightness(cls, x, y):
        r, g, b = cls._px[int(x), int(y)]
        return (r + g + b) // 3

    @classmethod
    def assert_band(cls, rgb_img, x, y_lo, y_hi, min_bright=10):
        """Column x must be brighter than min_bright somewhere in y_lo..y_hi
        (e.g. a card edge exists there)."""
        hit = any(cls.brightness(x, y) > min_bright
                  for y in range(int(y_lo), int(y_hi), 2))
        assert hit, f"assert_band failed: col x={x} dark throughout y {y_lo}..{y_hi}"

    @classmethod
    def assert_dark(cls, x0, x1, y0, y1, max_bright=40, stride=6):
        """Rect must be entirely dark (open space) - used to re-verify a
        tag slot picked by hand."""
        for y in range(int(y0), int(y1), max(2, stride // 2)):
            for x in range(int(x0), int(x1), stride):
                assert cls.brightness(x, y) <= max_bright, (
                    f"assert_dark failed at ({x},{y}) "
                    f"brightness={cls.brightness(x, y)}")

    @classmethod
    def find_row_bands(cls, x0, x1, y0, y1, thr=30, min_h=6, step=2):
        """Return bright-row spans inside a region (text lines, icons)."""
        spans = []
        start = None
        for y in range(int(y0), int(y1), int(step)):
            hit = any(cls.brightness(x, y) > thr
                      for x in range(int(x0), int(x1), 8))
            if hit and start is None:
                start = y
            elif not hit and start is not None:
                if y - start >= min_h:
                    spans.append((start, y))
                start = None
        if start is not None:
            spans.append((start, int(y1)))
        return spans

    @classmethod
    def find_col_clusters(cls, y0, y1, x0=0, x1=None, thr=60, min_w=10):
        """Return bright-column clusters inside a horizontal band (icons)."""
        x1 = x1 or cls._W
        clusters = []
        start = None
        for x in range(int(x0), int(x1), 2):
            hit = any(cls.brightness(x, y) > thr
                      for y in range(int(y0), int(y1), 4))
            if hit and start is None:
                start = x
            elif not hit and start is not None:
                if x - start >= min_w:
                    clusters.append((start, x))
                start = None
        if start is not None:
            clusters.append((start, int(x1)))
        return clusters

    @classmethod
    def bbox_of_bright(cls, x0, x1, y0, y1, thr=45):
        """Tight bounding box of bright pixels inside a region."""
        xs, ys = [], []
        for y in range(int(y0), int(y1), 2):
            for x in range(int(x0), int(x1), 2):
                if cls.brightness(x, y) > thr:
                    xs.append(x)
                    ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    @classmethod
    def card_bands(cls, y0=0, y1=None, thr=8, step=2):
        """Return state-change (y, is_card) transitions for the full-width
        row-brightness scan - finds card boundaries vs black background."""
        y1 = y1 or cls._H
        bands = []
        prev = None
        for y in range(int(y0), int(y1), int(step)):
            s = n = 0
            for x in range(0, cls._W, 8):
                s += cls.brightness(x, y)
                n += 1
            avg = s // n
            state = avg > thr
            if state != prev:
                bands.append((y, state))
                prev = state
        return bands
