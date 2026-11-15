"""Generate defect.png + control.png for evals/semantic-surprise.

Mock payment-result card. The defect: the status icon is the SUCCESS
checkmark (green circle, white tick) rendered on a FAILED payment —
the classic agent bug where the status glyph is hardcoded or keyed to
the wrong state. Text says "Payment failed"; the icon celebrates.

Everything else is pixel-identical to the control, which renders the
same failed state with the correct error glyph (red circle, white X).
The wrongness is purely semantic — geometry, palette role, and layout
are all normal.

Run from repo root:
    uv run --with pillow python3 evals/semantic-surprise/make_images.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

W, H = 880, 640
PAGE_BG = (243, 244, 246)
CARD_BG = (255, 255, 255)
BORDER = (229, 231, 235)
INK = (17, 24, 39)
BODY = (55, 65, 81)
SUB = (107, 114, 128)
ACCENT = (37, 99, 235)

# status glyphs
GREEN_OK = (22, 163, 74)     # #16a34a — success green
RED_ERR = (220, 38, 38)      # #dc2626 — error red
WHITE = (255, 255, 255)

FONT_DIR = "/System/Library/Fonts/Supplemental"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_HEAD = font("Arial Bold.ttf", 27)
F_BODY = font("Arial.ttf", 15)
F_LABEL = font("Arial.ttf", 14)
F_VALUE = font("Arial Bold.ttf", 15)
F_BTN = font("Arial Bold.ttf", 15)


def rounded_card(draw, box, radius=18, fill=CARD_BG, outline=BORDER, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill,
                           outline=outline, width=width)


def draw_check(draw, cx, cy, r):
    """White checkmark inscribed in the status circle."""
    # tick: short down-stroke then long up-stroke
    x0, y0 = cx - int(r * 0.52), cy + int(r * 0.02)
    x1, y1 = cx - int(r * 0.14), cy + int(r * 0.38)
    x2, y2 = cx + int(r * 0.55), cy - int(r * 0.42)
    draw.line([(x0, y0), (x1, y1), (x2, y2)], fill=WHITE, width=11,
              joint="curve")


def draw_x(draw, cx, cy, r):
    """White X inscribed in the status circle."""
    o = int(r * 0.42)
    w = 11
    draw.line([(cx - o, cy - o), (cx + o, cy + o)], fill=WHITE, width=w)
    draw.line([(cx - o, cy + o), (cx + o, cy - o)], fill=WHITE, width=w)


def build(icon: str, out_path: Path) -> None:
    img = Image.new("RGB", (W, H), PAGE_BG)
    d = ImageDraw.Draw(img)

    card = (190, 60, 690, 590)
    rounded_card(d, card)
    x0, y0, x1, y1 = card
    cx = (x0 + x1) // 2

    # --- status icon: THE semantic element ---
    icx, icy, ir = cx, y0 + 105, 46
    if icon == "check":
        d.ellipse((icx - ir, icy - ir, icx + ir, icy + ir), fill=GREEN_OK)
        draw_check(d, icx, icy, ir)
    else:
        d.ellipse((icx - ir, icy - ir, icx + ir, icy + ir), fill=RED_ERR)
        draw_x(d, icx, icy, ir)

    # --- headline ---
    head = "Payment failed"
    hw = d.textlength(head, font=F_HEAD)
    d.text((cx - hw / 2, icy + ir + 34), head, font=F_HEAD, fill=INK)

    # --- body ---
    body1 = "Your card ending in 4242 was declined."
    body2 = "No charge was made to your account."
    bw1 = d.textlength(body1, font=F_BODY)
    bw2 = d.textlength(body2, font=F_BODY)
    by = icy + ir + 82
    d.text((cx - bw1 / 2, by), body1, font=F_BODY, fill=BODY)
    d.text((cx - bw2 / 2, by + 26), body2, font=F_BODY, fill=BODY)

    # --- summary row ---
    ry = by + 74
    d.line([(x0 + 44, ry), (x1 - 44, ry)], fill=BORDER, width=1)
    ry += 20
    d.text((x0 + 48, ry), "Order", font=F_LABEL, fill=SUB)
    d.text((x0 + 48, ry + 22), "#48213 · Apr 12, 2026", font=F_VALUE,
           fill=INK)
    vw = d.textlength("$49.00", font=F_VALUE)
    d.text((x1 - 48 - vw, ry + 22), "$49.00", font=F_VALUE, fill=INK)

    # --- primary button ---
    btn_w, btn_h = 260, 46
    bx0 = cx - btn_w // 2
    by0 = y1 - 96
    d.rounded_rectangle((bx0, by0, bx0 + btn_w, by0 + btn_h), radius=10,
                        fill=ACCENT)
    bl = "Try again"
    lw = d.textlength(bl, font=F_BTN)
    d.text((bx0 + (btn_w - lw) / 2, by0 + (btn_h - 24) / 2), bl,
           font=F_BTN, fill=WHITE)

    img.save(out_path)
    print(f"wrote {out_path}  icon={icon}")


def main() -> None:
    # DEFECT: failed payment wearing the success checkmark.
    build("check", HERE / "defect.png")
    # CONTROL: same failed state, correct error glyph.
    build("x", HERE / "control.png")


if __name__ == "__main__":
    main()
