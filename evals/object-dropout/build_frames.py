#!/usr/bin/env python3
"""Build the object-dropout eval sequence.

Five frames of a light-theme "Site Traffic" analytics card (640x400):
a visitor count ticking up, a 7-bar chart animating, and a red "LIVE"
pill badge in the card header.

THE DEFECT: the LIVE badge (pill + pulse dot) is present in frames 1-2
and silently absent from frames 3-5. Everything else keeps animating —
the count climbs, the bars move, the footer still reads "Auto-refresh
every 5s". Nothing in the scene explains the disappearance: this is
the classic `{isStreaming && <LiveBadge/>}` conditional that desynced
(or a render that failed once and never recovered), not a state change
the UI acknowledges.

Most typical instance of the class: a small status affordance vanishing
mid-session while surrounding live data keeps flowing. Not adversarial —
no weird geometry, no extreme contrast, everything else coherent.

Run from repo root:  uv run --with pillow python3 evals/object-dropout/build_frames.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 640, 400

BG = (236, 238, 244)        # app background
NAV = (255, 255, 255)       # top nav strip
CARD = (255, 255, 255)
CARD_EDGE = (224, 228, 240)
INK = (28, 32, 46)
DIM = (104, 112, 132)
FAINT = (158, 164, 182)
DIVIDER = (232, 235, 244)
BAR = (96, 165, 250)        # blue bars
BAR_BASE = (214, 224, 248)  # bar baseline track
LIVE_RED = (239, 68, 68)
LIVE_DARK = (203, 34, 46)
PULSE = (52, 199, 89)


def font(size: int) -> ImageFont.FreeTypeFont:
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


# card geometry
CARD_BOX = [48, 64, 592, 360]
HEADER_Y = 92
COUNT_Y = 158
BARS_BASE_Y = 302
FOOTER_Y = 340

# LIVE badge pill (card header, right side)
BADGE = [498, 84, 570, 114]          # x0, y0, x1, y1
BADGE_CY = (BADGE[1] + BADGE[3]) // 2
DOT_X = BADGE[0] + 16                # pulse dot center-x
TEXT_X = BADGE[0] + 32               # "LIVE" text left edge


def draw_live_badge(d: ImageDraw.ImageDraw, pulse_r: int) -> None:
    """Red pill with a pulsing white dot and 'LIVE' label."""
    d.rounded_rectangle(BADGE, radius=15, fill=LIVE_RED,
                        outline=LIVE_DARK, width=1)
    r = pulse_r
    d.ellipse([DOT_X - r, BADGE_CY - r, DOT_X + r, BADGE_CY + r],
              fill=(255, 255, 255))
    d.text((TEXT_X, BADGE_CY), "LIVE", font=font(12), fill=(255, 255, 255),
           anchor="lm")


def draw_frame(count: int, bars: list[float], live: bool,
               pulse_r: int, path: Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # top nav strip
    d.rectangle([0, 0, W, 46], fill=NAV)
    d.rectangle([0, 45, W, 46], fill=CARD_EDGE)
    d.ellipse([20, 15, 34, 29], fill=(59, 130, 246))
    d.text((44, 23), "Acme Analytics", font=font(14), fill=INK, anchor="lm")
    d.text((W - 24, 23), "Settings", font=font(12), fill=DIM, anchor="rm")

    # card
    d.rounded_rectangle(CARD_BOX, radius=14, fill=CARD,
                        outline=CARD_EDGE, width=1)

    # header
    d.text((CARD_BOX[0] + 28, HEADER_Y), "Site Traffic",
           font=font(20), fill=INK)
    d.text((CARD_BOX[0] + 28, HEADER_Y + 26),
           "Unique visitors · last 24 hours", font=font(12), fill=DIM)

    # THE VARIABLE ELEMENT: LIVE badge — present in frames 1-2 only
    if live:
        draw_live_badge(d, pulse_r)

    # big count
    d.text((CARD_BOX[0] + 28, COUNT_Y), f"{count:,}",
           font=font(34), fill=INK)
    d.text((CARD_BOX[0] + 30, COUNT_Y + 46), "visitors",
           font=font(12), fill=DIM)

    # bar chart
    chart_x0, chart_x1 = CARD_BOX[0] + 28, CARD_BOX[2] - 28
    slot = (chart_x1 - chart_x0) / len(bars)
    bar_w = 44
    max_h = 120
    for i, frac in enumerate(bars):
        cx = chart_x0 + slot * i + slot / 2
        h = max(6, int(max_h * frac))
        x0, x1 = cx - bar_w / 2, cx + bar_w / 2
        d.rectangle([x0, BARS_BASE_Y - h, x1, BARS_BASE_Y], fill=BAR)
    d.line([chart_x0, BARS_BASE_Y, chart_x1, BARS_BASE_Y],
           fill=BAR_BASE, width=2)

    # footer
    d.line([CARD_BOX[0] + 28, FOOTER_Y - 12, CARD_BOX[2] - 28, FOOTER_Y - 12],
           fill=DIVIDER, width=1)
    d.text((CARD_BOX[0] + 28, FOOTER_Y),
           "Auto-refresh every 5s · data delayed ≤ 5s",
           font=font(11), fill=FAINT)

    img.save(path)


def main() -> None:
    # count, bar heights (0..1), badge present, pulse dot radius
    states = [
        (12847, [0.45, 0.62, 0.50, 0.78, 0.66, 0.90, 0.72], True, 4),
        (12912, [0.50, 0.58, 0.66, 0.72, 0.80, 0.85, 0.68], True, 6),
        # THE DEFECT: badge gone from frame 3 onward; everything else
        # keeps animating as if the stream were still live.
        (12987, [0.55, 0.70, 0.60, 0.82, 0.75, 0.95, 0.78], False, 0),
        (13044, [0.62, 0.66, 0.74, 0.78, 0.88, 0.90, 0.84], False, 0),
        (13102, [0.58, 0.74, 0.68, 0.86, 0.80, 1.00, 0.90], False, 0),
    ]
    names = [f"frame_{i:02d}.png" for i in range(1, 6)]
    for state, name in zip(states, names):
        draw_frame(*state, OUT / name)

    for n in names:
        p = OUT / n
        print(f"{n}  {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
