#!/usr/bin/env python3
"""make_synth.py — synthetic controls for edge-census.

Renders three 1080x640 mock pages with PIL so the detector's flag path
is exercised on KNOWN ground truth (the eval images only provide one
clean/one-defect pair, and several other evals yield zero repeated
strings — a weak control):

  synth_clean.png   — card grid + toolbar, every repeated element
                      perfectly aligned. Expect CLEAN.
  synth_drift.png   — same scene, deterministic per-element dx/dy of
                      1-6px plus a +5px toolbar-label baseline shift.
                      Expect FLAGGED (column_drift + row_drift).
  synth_ragged.png  — same strings legitimately repeated at DIFFERENT
                      x positions (second mini-table reusing 'Active' /
                      'Engineering', scattered standalone labels).
                      Expect CLEAN — sub-clustering must not merge
                      legitimately separate columns.

Run from repo root:  uv run python detectors/edge-census/make_synth.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/System/Library/Fonts/Supplemental"
OUT = Path(__file__).resolve().parent


def font(name: str, size: int):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_TITLE = font("Arial Bold.ttf", 22)
F_NAME = font("Arial Bold.ttf", 16)
F_EMAIL = font("Arial.ttf", 12)
F_ROLE = font("Arial.ttf", 14)
F_PILL = font("Arial Bold.ttf", 12)
F_HEAD = font("Arial Bold.ttf", 11)
F_BTN = font("Arial.ttf", 13)

W, H = 1080, 640
BG = "#f4f5f7"
CARD = "#ffffff"
EDGE = "#e2e5ea"
INK = "#111827"
SUB = "#4b5563"
SLATE = "#64748b"
PILL_ACTIVE = "#dcfce7"
PILL_INVITED = "#fef9c3"
PILL_EDGE = "#d1d5db"

RIGHT = 1000  # right padding line, mirrors eval layout

# 5 cards, pitch 76, tops 150..454 (bottoms +64 -> last 518)
CARD_TOPS = [150, 226, 302, 378, 454]
ROLES = ["Engineering", "Engineering", "Design", "Data", "Engineering"]
STATUSES = ["Active", "Active", "Invited", "Active", "Invited"]
NAMES = ["Ada Lovelace", "Grace Hopper", "Katherine Johnson",
         "Margaret Hamilton", "Radia Perlman"]
EMAILS = ["ada@analytical.io", "grace@navy.mil", "kat@space.gov",
          "marg@apollo.mit", "radia@bridges.net"]

# deterministic per-card drift (dx, dy) applied to interior elements
DRIFT = [(2, 1), (-3, 0), (5, -2), (-1, 3), (4, -1)]
HEAD_DRIFT = {"MEMBER": (2, 0), "ROLE": (-3, 0), "STATUS": (-5, 0)}
TOOLBAR_Y = 600  # shared baseline; drift version shifts middle label +5


def draw_pill(d, cx_right, cy, text, fill):
    """Right-anchored pill: right edge at cx_right, vertically centered cy."""
    bbox = d.textbbox((0, 0), text, font=F_PILL)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 10, 5
    pw, ph = tw + 2 * pad_x, th + 2 * pad_y
    x1 = cx_right
    x0 = x1 - pw
    y0 = cy - ph // 2
    d.rounded_rectangle([x0, y0, x1, y0 + ph], radius=8,
                        fill=fill, outline=PILL_EDGE, width=1)
    d.text((x0 + pad_x - bbox[0], y0 + pad_y - bbox[1]),
           text, font=F_PILL, fill=INK)


def draw_card(d, top, i, dx=0, dy=0):
    # card body
    d.rounded_rectangle([48, top, 1032, top + 64], radius=8,
                        fill=CARD, outline=EDGE, width=1)
    # avatar circle
    ax, ay = 88 + dx, top + 32 + dy
    d.ellipse([ax - 20, ay - 20, ax + 20, ay + 20], fill=SLATE)
    # name / email
    d.text((115 + dx, top + 14 + dy), NAMES[i], font=F_NAME, fill=INK)
    d.text((115 + dx, top + 40 + dy), EMAILS[i], font=F_EMAIL, fill=SUB)
    # role
    d.text((446 + dx, top + 25 + dy), ROLES[i], font=F_ROLE, fill=INK)
    # status pill (right-anchored at RIGHT)
    fill = PILL_ACTIVE if STATUSES[i] == "Active" else PILL_INVITED
    draw_pill(d, RIGHT + dx, top + 32 + dy, STATUSES[i], fill)
    # dots "..." near right edge
    d.text((968 + dx, top + 26 + dy), "...", font=F_ROLE, fill=SUB)


def draw_header(d, drift_map=None):
    drift_map = drift_map or {}
    y = 128
    for label, x in (("MEMBER", 115), ("ROLE", 446), ("STATUS", 846)):
        dx, dy = drift_map.get(label, (0, 0))
        d.text((x + dx, y + dy), label, font=F_HEAD, fill=SUB)


def draw_toolbar(d, dy_middle=0):
    """Three identical 'Export' labels in one row — row-census witness."""
    for j, x in enumerate((200, 500, 800)):
        dy = dy_middle if j == 1 else 0
        d.text((x, TOOLBAR_Y + dy), "Export", font=F_BTN, fill=INK)


def base(title_right="Invite member"):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((48, 30), "Members", font=F_TITLE, fill=INK)
    # invite button (decorative)
    d.rounded_rectangle([880, 34, 1032, 62], radius=6, fill="#2563eb")
    d.text((905, 40), title_right, font=F_BTN, fill="#ffffff")
    return img, d


def make_clean():
    img, d = base()
    draw_header(d)
    for i, top in enumerate(CARD_TOPS):
        draw_card(d, top, i)
    draw_toolbar(d)
    img.save(OUT / "synth_clean.png")


def make_drift():
    img, d = base()
    draw_header(d, HEAD_DRIFT)
    for i, top in enumerate(CARD_TOPS):
        draw_card(d, top, i, dx=DRIFT[i][0], dy=DRIFT[i][1])
    # +5px baseline wobble on the middle toolbar label -> row_drift
    draw_toolbar(d, dy_middle=5)
    img.save(OUT / "synth_drift.png")


def make_ragged():
    """Legitimately ragged: same strings at genuinely different columns.

    'Active'/'Engineering' appear both in the card grid AND in a second
    mini-table offset right, plus standalone labels — every cluster is
    internally aligned, so the census must stay CLEAN.
    """
    img, d = base()
    draw_header(d)
    for i, top in enumerate(CARD_TOPS):
        draw_card(d, top, i)
    # second mini-table, x-offset ~+180, reusing the same strings
    for j, top in enumerate((150, 226, 302)):
        d.rounded_rectangle([560, top, 900, top + 64], radius=8,
                            fill=CARD, outline=EDGE, width=1)
        d.text((580, top + 14), NAMES[(j + 2) % 5], font=F_NAME, fill=INK)
        d.text((580, top + 40), EMAILS[(j + 2) % 5], font=F_EMAIL, fill=SUB)
        d.text((830, top + 25), ROLES[j], font=F_ROLE, fill=INK)
        fill = PILL_ACTIVE if STATUSES[j] == "Active" else PILL_INVITED
        draw_pill(d, 880, top + 32, STATUSES[j], fill)
    # standalone scattered repeats (unique positions -> n=1 clusters)
    d.text((300, 560), "Active", font=F_ROLE, fill=SUB)
    d.text((620, 560), "Engineering", font=F_ROLE, fill=SUB)
    draw_toolbar(d)
    img.save(OUT / "synth_ragged.png")


if __name__ == "__main__":
    make_clean()
    make_drift()
    make_ragged()
    print("wrote synth_clean.png synth_drift.png synth_ragged.png")
