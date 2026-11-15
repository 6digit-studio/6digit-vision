#!/usr/bin/env python3
"""Build the chaotic-motion eval sequence.

Six frames of a typical light-theme "Design Sync" meeting card: a shared-
screen preview (static), a participants panel, and a control-pill row.
Everything is static EXCEPT the "voice activity" subsystem, which carries
the planted defect — uncontrolled/erratic motion of the kind an agent
ships when it reaches for unseeded randomness per frame instead of
eased/seeded animation state:

  1. DISCONTINUOUS JUMP — the green "active speaker" ring teleports
     between participants EVERY frame (Maya -> Alex -> Jordan -> Sam ->
     Maya -> Alex). A real implementation dwells on one speaker for
     hundreds of ms; this has no continuity at all.
  2. AMPLITUDE CHAOS — the waveform bars next to the active speaker are
     re-rolled to random heights (2-14px) every frame. Real equalizers
     interpolate smoothly; these teleport full-range with zero
     frame-to-frame correlation.
  3. FLICKER — the red LIVE pill is present on frames 1,3,5 and gone on
     2,4,6 — hard on/off alternation, not the smooth opacity pulse a
     live indicator should have.

The bug story: `setActiveSpeaker(participants[Math.floor(Math.random()*4)])`
in the render loop, `bars = heights.map(() => rand(2,14))` with no lerp,
`pill && <LivePill/>` keyed to unstable state. All three are one-line
agent mistakes.

Run from repo root:  uv run --with pillow python3 evals/chaotic-motion/build_frames.py
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 800, 580

# page + card geometry
CX, CY, CW, CH = 50, 50, 700, 480
RX = CX + CW - 24          # right inner margin x
LX = CX + 24               # left inner margin x

PAGE = (233, 234, 240)
CARD = (255, 255, 255)
BORDER = (222, 224, 231)
INK = (28, 31, 40)
DIM = (112, 118, 130)
FAINT = (152, 157, 167)
LINE = (236, 238, 243)
PANEL_BG = (247, 248, 251)
GREEN = (21, 163, 74)
RED = (220, 38, 38)
BLUE = (37, 99, 235)
WHITE = (255, 255, 255)

PARTICIPANTS = [
    # name, role, avatar fill, avatar ink, initials
    ("Maya Chen",   "Product Designer",  (219, 234, 254), (30, 64, 175),  "MC"),
    ("Jordan Lee",  "Engineer",          (209, 250, 229), (6, 95, 70),    "JL"),
    ("Sam Rivera",  "Product Manager",   (254, 243, 199), (133, 77, 14),  "SR"),
    ("Alex Kim",    "Brand Designer",    (243, 232, 255), (107, 33, 168), "AK"),
]

# THE DEFECT — unseeded-random motion, rendered deterministically here
# (fixed seed) so the artifact is reproducible.
SPEAKERS = [0, 3, 1, 2, 0, 3]          # active speaker jumps every frame
PILL_ON = [True, False, True, False, True, False]  # LIVE pill flickers
_rng = random.Random(20261115)
WAVE = [[_rng.randint(2, 14) for _ in range(9)] for _ in range(6)]


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


def draw_shared_screen(d: ImageDraw.ImageDraw) -> None:
    """Static 'shared screen' preview — identical in every frame."""
    x0, y0, x1, y1 = LX, CY + 96, CX + 420, CY + 388
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=CARD,
                        outline=BORDER, width=1)
    # window chrome dots + doc title
    for i, c in enumerate([(239, 68, 68), (234, 179, 8), (34, 197, 94)]):
        d.ellipse([x0 + 16 + i * 14, y0 + 14, x0 + 22 + i * 14, y0 + 20], fill=c)
    d.text((x0 + 66, y0 + 17), "Roadmap-Q4.fig — Slide 3", font=font(11),
           fill=FAINT, anchor="lm")
    # slide content
    d.text((x0 + 18, y0 + 48), "Q4 Roadmap", font=font(17), fill=INK,
           anchor="lm")
    d.text((x0 + 18, y0 + 72), "Organized by bet · updated Oct 28",
           font=font(11), fill=DIM, anchor="lm")
    for i, wdt in enumerate((300, 260, 220)):
        d.rounded_rectangle([x0 + 18, y0 + 94 + i * 20,
                             x0 + 18 + wdt, y0 + 100 + i * 20],
                            radius=4, fill=(240, 242, 246))
    # bar chart
    base = y1 - 26
    for i, h in enumerate((40, 70, 55, 90, 64)):
        bx = x0 + 46 + i * 38
        d.rectangle([bx, base - h, bx + 24, base], fill=BLUE)
    d.line([x0 + 18, base, x1 - 18, base], fill=BORDER, width=1)
    d.text((x0 + 18, y1 - 12), "Maya Chen's screen", font=font(10),
           fill=FAINT, anchor="lm")


def draw_participants(d: ImageDraw.ImageDraw, speaker: int,
                      bars: list[int]) -> None:
    """Participants panel; only the active-speaker row animates."""
    px = CX + 436
    d.text((px, CY + 82), "PARTICIPANTS", font=font(11), fill=FAINT)
    for i, (name, role, fill, ink, initials) in enumerate(PARTICIPANTS):
        ry = CY + 96 + i * 72
        active = i == speaker
        ax, ay = px + 30, ry + 28          # avatar center

        if active:
            # speaking ring — teleports to a different participant each frame
            d.ellipse([ax - 25, ay - 25, ax + 25, ay + 25],
                      outline=GREEN, width=3)
        d.ellipse([ax - 20, ay - 20, ax + 20, ay + 20], fill=fill)
        d.text((ax, ay), initials, font=font(12), fill=ink, anchor="mm")

        d.text((px + 58, ry + 12), name, font=font(13), fill=INK,
               anchor="lm")
        d.text((px + 58, ry + 36), role, font=font(11), fill=DIM,
               anchor="lm")

        if active:
            # waveform — heights re-rolled randomly every frame
            bx0, by = px + 158, ry + 56
            for b, h in enumerate(bars):
                bx = bx0 + b * 7
                d.rectangle([bx, by - h, bx + 4, by], fill=GREEN)


def draw_live_pill(d: ImageDraw.ImageDraw, on: bool) -> None:
    """LIVE pill — flickers hard on/off instead of pulsing smoothly."""
    if not on:
        return
    x0, y0, x1, y1 = RX - 72, CY + 16, RX, CY + 44
    d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=RED)
    cy = (y0 + y1) // 2
    d.ellipse([x0 + 12, cy - 3, x0 + 18, cy + 3], fill=WHITE)
    d.text((x0 + 24, cy), "LIVE", font=font(11), fill=WHITE, anchor="lm")


def draw_controls(d: ImageDraw.ImageDraw) -> None:
    labels = ["Mute", "Video", "Share", "Chat", "Leave"]
    pw, ph, gap = 68, 30, 12
    total = len(labels) * pw + (len(labels) - 1) * gap
    x = CX + (CW - total) // 2
    y = CY + 420
    for i, lab in enumerate(labels):
        leave = lab == "Leave"
        d.rounded_rectangle([x, y, x + pw, y + ph], radius=15,
                            fill=RED if leave else PANEL_BG,
                            outline=None if leave else BORDER, width=1)
        d.text((x + pw / 2, y + ph / 2), lab,
               font=font(12), fill=WHITE if leave else INK, anchor="mm")
        x += pw + gap


def draw_frame(idx: int, path: Path) -> None:
    img = Image.new("RGB", (W, H), PAGE)
    d = ImageDraw.Draw(img)

    # card
    d.rounded_rectangle([CX, CY, CX + CW, CY + CH], radius=16,
                        fill=CARD, outline=BORDER, width=1)

    # header
    d.text((LX, CY + 18), "Design Sync", font=font(20), fill=INK,
           anchor="lm")
    d.text((LX, CY + 46), "Weekly sync · 4 participants", font=font(12),
           fill=DIM, anchor="lm")
    draw_live_pill(d, PILL_ON[idx])

    # divider
    d.line([LX, CY + 68, RX, CY + 68], fill=LINE, width=1)

    draw_shared_screen(d)
    draw_participants(d, SPEAKERS[idx], WAVE[idx])
    draw_controls(d)

    img.save(path)


def main() -> None:
    for i in range(6):
        p = OUT / f"frame_{i + 1:02d}.png"
        draw_frame(i, p)
        print(f"{p.name}  speaker={PARTICIPANTS[SPEAKERS[i]][0]:<12} "
              f"pill={'on ' if PILL_ON[i] else 'off'}  "
              f"wave={WAVE[i]}")


if __name__ == "__main__":
    main()
