#!/usr/bin/env python3
"""Build the frozen-frames eval sequence.

Five frames of a typical macOS-style "Importing Photos" progress dialog:
a progress bar advancing, a spinner arc rotating, and a status line that
changes per frame. Frame 3 (frame_03.png) is a byte-identical copy of
frame 2 — the frozen-render defect: the draw loop produced (or kept) the
previous frame instead of advancing state.

Run from repo root:  uv run --with pillow python3 evals/frozen-frames/build_frames.py
"""

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 640, 400

BG = (30, 30, 46)        # window background
TITLEBAR = (22, 22, 36)
CARD = (43, 43, 67)
CARD_EDGE = (60, 60, 92)
INK = (235, 235, 245)
DIM = (152, 152, 172)
FAINT = (110, 110, 136)
ACCENT = (76, 194, 255)
TRACK = (62, 62, 90)


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


def draw_frame(pct: int, spin_deg: int, status: str, path: Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # window chrome
    d.rectangle([0, 0, W, 30], fill=TITLEBAR)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 22, 10, 30 + i * 22, 24], fill=c)
    d.text((W // 2, 15), "Photos — Import", font=font(12), fill=DIM, anchor="mm")

    # card
    d.rounded_rectangle([80, 56, 560, 344], radius=14, fill=CARD,
                        outline=CARD_EDGE, width=2)

    # header
    d.text((112, 78), "Importing Photos", font=font(22), fill=INK)
    d.text((112, 112), "Library sync in progress", font=font(14), fill=DIM)

    # spinner: static track ring + rotating arc
    cx, cy, r = 146, 210, 24
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(72, 72, 104), width=5)
    d.arc([cx - r, cy - r, cx + r, cy + r],
          start=spin_deg, end=spin_deg + 290, fill=ACCENT, width=5)

    # progress track + fill + percent
    bx0, by, bw, bh = 200, 194, 340, 24
    d.rounded_rectangle([bx0, by, bx0 + bw, by + bh], radius=12, fill=TRACK)
    fw = max(4, int(bw * pct / 100))
    d.rounded_rectangle([bx0, by, bx0 + fw, by + bh], radius=12, fill=ACCENT)
    d.text((bx0 + bw + 18, by + bh / 2), f"{pct}%", font=font(18),
           fill=INK, anchor="lm")

    # status line + footer
    d.text((112, 262), status, font=font(16), fill=DIM)
    d.text((112, 306), "Do not close this window.", font=font(13), fill=FAINT)

    img.save(path)


def main() -> None:
    states = [
        (20, 0,   "Scanning library..."),
        (45, 90,  "Copying files..."),
        # frame 3 = frozen duplicate of frame 2 (see below)
        (70, 180, "Verifying checksums..."),
        (90, 270, "Finishing up..."),
    ]
    names = ["frame_01.png", "frame_02.png", "frame_03.png",
             "frame_04.png", "frame_05.png"]

    draw_frame(*states[0], OUT / names[0])
    draw_frame(*states[1], OUT / names[1])
    # THE DEFECT: frozen render — frame 3 is exactly frame 2
    shutil.copyfile(OUT / names[1], OUT / names[2])
    draw_frame(*states[2], OUT / names[3])
    draw_frame(*states[3], OUT / names[4])

    for n in names:
        p = OUT / n
        print(f"{n}  {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
