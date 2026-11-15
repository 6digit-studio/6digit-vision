"""Build defect.png + control.png for evals/low-contrast.

Mock checkout UI card. The defect: footer fine-print rendered in
near-white gray on a white card — the classic "muted text token
resolved to near-background" mistake agents ship. Everything else is
readable so any signal is attributable to the one element.

control.png is the same layout with the footer in a readable muted gray.

Run from repo root:  uv run --with pillow python3 evals/low-contrast/make_artifact.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

W, H = 900, 680
PAGE_BG = (243, 244, 246)      # light gray page
CARD_BG = (255, 255, 255)      # white card
BORDER = (229, 231, 235)
INK = (17, 24, 39)             # near-black headings
BODY = (55, 65, 81)            # readable body gray
ACCENT = (37, 99, 235)         # blue button

# defect: footer text ~#d6d6d6 on #ffffff -> ~1.5:1 contrast, unreadable
FOOTER_DEFECT = (214, 214, 214)
# control: same slot, readable muted gray ~#6b7280 -> ~4.8:1
FOOTER_CONTROL = (107, 114, 128)

FONT_DIR = "/System/Library/Fonts/Supplemental"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_EYEBROW = font("Arial.ttf", 15)
F_TITLE = font("Arial Bold.ttf", 30)
F_ROW = font("Arial.ttf", 19)
F_ROW_BOLD = font("Arial Bold.ttf", 19)
F_TOTAL = font("Arial Bold.ttf", 22)
F_FOOTER = font("Arial.ttf", 15)
F_BTN = font("Arial Bold.ttf", 17)


def rounded_card(draw: ImageDraw.ImageDraw, box, radius=18, fill=CARD_BG,
                 outline=BORDER, width=2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill,
                           outline=outline, width=width)


def draw_ui(footer_rgb: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (W, H), PAGE_BG)
    d = ImageDraw.Draw(img)

    # card: centered, generous margins
    card = (110, 40, 790, 650)
    rounded_card(d, card)

    x0, y0, x1, y1 = card
    cx = (x0 + x1) // 2
    top = y0 + 42

    # eyebrow
    eyebrow = "ORDER SUMMARY"
    ew = d.textlength(eyebrow, font=F_EYEBROW)
    d.text((cx - ew / 2, top), eyebrow, font=F_EYEBROW, fill=(107, 114, 128))

    # title
    title = "Order #1042"
    tw = d.textlength(title, font=F_TITLE)
    d.text((cx - tw / 2, top + 30), title, font=F_TITLE, fill=INK)

    # divider
    dy = top + 95
    d.line([(x0 + 48, dy), (x1 - 48, dy)], fill=BORDER, width=1)

    # line items
    rows = [
        ("Subtotal", "$48.00"),
        ("Shipping", "$5.00"),
        ("Tax", "$4.20"),
    ]
    ry = dy + 34
    for label, val in rows:
        d.text((x0 + 70, ry), label, font=F_ROW, fill=BODY)
        vw = d.textlength(val, font=F_ROW)
        d.text((x1 - 70 - vw, ry), val, font=F_ROW, fill=INK)
        ry += 42

    # total row, heavier
    ry += 8
    d.line([(x0 + 48, ry), (x1 - 48, ry)], fill=BORDER, width=1)
    ry += 22
    d.text((x0 + 70, ry), "Total", font=F_TOTAL, fill=INK)
    val = "$57.20"
    vw = d.textlength(val, font=F_TOTAL)
    d.text((x1 - 70 - vw, ry), val, font=F_TOTAL, fill=INK)
    ry += 48

    # primary button (readable, part of the same mock)
    btn_w, btn_h = 220, 52
    bx0 = cx - btn_w // 2
    by0 = ry
    d.rounded_rectangle((bx0, by0, bx0 + btn_w, by0 + btn_h), radius=10,
                        fill=ACCENT)
    label = "View details"
    lw = d.textlength(label, font=F_BTN)
    d.text((bx0 + (btn_w - lw) / 2, by0 + (btn_h - 26) / 2), label,
           font=F_BTN, fill=(255, 255, 255))

    # footer fine print — THE DEFECT ELEMENT (or control color)
    fy = 528
    lines = [
        "Prices are estimates. Final amount is calculated at checkout",
        "and may differ. Delivery times shown in UTC. See terms for",
        "details and refund policy before confirming your order.",
    ]
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=F_FOOTER)
        d.text((cx - lw / 2, fy + i * 24), line, font=F_FOOTER,
               fill=footer_rgb)

    return img


def main() -> None:
    draw_ui(FOOTER_DEFECT).save(HERE / "defect.png")
    draw_ui(FOOTER_CONTROL).save(HERE / "control.png")
    print("wrote defect.png and control.png")


if __name__ == "__main__":
    main()
