"""Synthetic fixtures for edge-bisect — no Mirage needed (--record).

  uv run detectors/edge-bisect/make_synthetic.py

Writes into detectors/edge-bisect/synthetic/:
  v-slice.png / v-slice.json   — vertical panel edge slicing a text line
                                 mid-glyph (axis-symmetry proof)
  divider.png / divider.json   — flat divider 30px below the ink band,
                                 inside a tall text bbox (ink-adjacency
                                 false-positive guard; must stay silent)
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "synthetic"
OUT.mkdir(exist_ok=True)


def glyph_row(draw: ImageDraw.ImageDraw, y: int, x0: int, x1: int,
              h: int = 12, color=(20, 20, 20)):
    """Fake 'text': three rounded bars resembling glyph bodies."""
    w = x1 - x0
    for i, (a, b) in enumerate([(0.05, 0.35), (0.4, 0.7), (0.75, 0.98)]):
        xa = x0 + int(w * a)
        xb = x0 + int(w * b)
        draw.rounded_rectangle([xa, y, xb, y + h], radius=3, fill=color)


def norm(bbox_px, w, h):
    x0, y0, x1, y1 = bbox_px
    return [round(v / (w if i % 2 == 0 else h) * 1000) for i, v in
            enumerate(bbox_px)]


# --- fixture 1: vertical slice -------------------------------------------------
# 400x240 white page. Sidebar panel (light gray) with a darker 2px border at
# its right edge, painted OVER a line of "text" — the edge at x=120 cuts the
# glyph row mid-body. Text bbox covers the whole block.
W, H = 400, 240
img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
# "text" lines at y=90..102 and y=118..130, spanning x=60..260
glyph_row(d, 90, 60, 260)
glyph_row(d, 118, 60, 260)
# panel: x<118 gray, border cols 118-119 darker — painted last (occludes)
d.rectangle([0, 0, 117, H], fill=(238, 238, 238))
d.rectangle([118, 0, 119, H], fill=(205, 205, 205))
img.save(OUT / "v-slice.png")
rec = {"text": [{"string": " sliced label ", "score": 0.6,
                 "bbox": norm([50, 80, 280, 140], W, H)}]}
(OUT / "v-slice.json").write_text(json.dumps(rec))

# --- fixture 2: divider in padding (must NOT fire) ------------------------------
# 400x240 white page, one "text" line y=90..102 inside a tall bbox down to
# y=160; a flat horizontal rule at y=140 (30px below ink) spans full width.
img = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(img)
glyph_row(d, 90, 60, 260)
d.rectangle([40, 140, 360, 141], fill=(180, 180, 180))  # divider rule
img.save(OUT / "divider.png")
rec = {"text": [{"string": " roomy label ", "score": 0.6,
                 "bbox": norm([50, 80, 280, 160], W, H)}]}
(OUT / "divider.json").write_text(json.dumps(rec))

print("wrote", OUT)
