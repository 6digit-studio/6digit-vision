"""Generate defect.png (title clipped mid-glyph at card edge) + control.png.

Simulates the classic agent-shipped bug: a fixed-width card with
`overflow: hidden` and a title that doesn't fit — no ellipsis, the last
glyph is sliced in half at the padding edge.

Run from repo root:
    uv run --with pillow python3 evals/text-truncation/make_images.py
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 840, 560
BG = (236, 238, 241)          # app background
CARD = (255, 255, 255)
BORDER = (223, 227, 232)
INK = (30, 34, 40)            # primary text
SUB = (110, 116, 126)         # secondary text
ACCENT = (47, 111, 224)       # button

FONT_DIR = "/System/Library/Fonts/Supplemental"
F_BOLD = f"{FONT_DIR}/Arial Bold.ttf"
F_REG = f"{FONT_DIR}/Arial.ttf"

TITLE = "Quarterly Revenue Overview Report"
SUBTITLE = "Q3 financial summary - updated 2h ago"

CARD_X, CARD_Y, CARD_H = 120, 120, 300
PAD = 24


def font(path, size):
    return ImageFont.truetype(path, size)


def rounded_card(draw, box, radius=12, fill=CARD, outline=BORDER):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)


def draw_title_layer(title, clip_w, size=26):
    """Render title into a layer exactly clip_w wide; PIL clips glyphs at
    the layer edge -> mid-glyph cut, exactly like overflow:hidden."""
    f = font(F_BOLD, size)
    th = int(size * 1.4)
    layer = Image.new("RGBA", (clip_w, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((0, 2), title, font=f, fill=INK + (255,))
    return layer, f


def build(clip_w, out_path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    full_w = int(font(F_BOLD, 26).getlength(TITLE))
    card_w = clip_w + 2 * PAD

    # --- card ---
    rounded_card(d, (CARD_X, CARD_Y, CARD_X + card_w, CARD_Y + CARD_H))

    # --- title, clipped at the padding box (card_w - PAD on the right) ---
    layer, _ = draw_title_layer(TITLE, clip_w)
    img.paste(layer, (CARD_X + PAD, CARD_Y + PAD - 4), layer)

    # --- subtitle ---
    fs = font(F_REG, 14)
    d.text((CARD_X + PAD, CARD_Y + PAD + 30), SUBTITLE, font=fs, fill=SUB)

    # --- divider ---
    dy = CARD_Y + PAD + 58
    d.line((CARD_X + PAD, dy, CARD_X + card_w - PAD, dy), fill=BORDER, width=1)

    # --- three stat rows ---
    rows = [
        ("Revenue", "$1.24M", "+12.4%"),
        ("Expenses", "$842K", "-3.1%"),
        ("Net income", "$398K", "+18.9%"),
    ]
    fr = font(F_REG, 15)
    fb = font(F_BOLD, 15)
    y = dy + 18
    for label, val, delta in rows:
        d.text((CARD_X + PAD, y), label, font=fr, fill=INK)
        d.text((CARD_X + card_w - PAD - 150, y), val, font=fb, fill=INK)
        d.text((CARD_X + card_w - PAD - 60, y), delta, font=fr, fill=(22, 163, 74))
        y += 34

    # --- button ---
    bw, bh = 120, 34
    bx = CARD_X + card_w - PAD - bw
    by = CARD_Y + CARD_H - PAD - bh + 6
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=8, fill=ACCENT)
    label = "View report"
    tw = int(font(F_BOLD, 13).getlength(label))
    d.text((bx + (bw - tw) / 2, by + 8), label, font=font(F_BOLD, 13), fill=(255, 255, 255))

    img.save(out_path)
    print(f"{out_path}: card_w={card_w} clip_w={clip_w} "
          f"title_full_px={full_w} overflow_px={full_w - clip_w}")


def main():
    f = font(F_BOLD, 26)
    full_w = int(f.getlength(TITLE))

    # DEFECT: clip lands mid-glyph — boundary at x=556 slices the 'o' of
    # "Report" (advance img-x 548..564, ink ~549..562; verified via ink
    # profile). Left bowl of 'o' shows, right side is gone.
    defect_clip = 412
    build(defect_clip, "evals/text-truncation/defect.png")

    # CONTROL: same card, clip wide enough for the whole title (+12 slack).
    control_clip = full_w + 12
    build(control_clip, "evals/text-truncation/control.png")


if __name__ == "__main__":
    main()
