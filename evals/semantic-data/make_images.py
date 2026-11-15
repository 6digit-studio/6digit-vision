"""Generate defect.png + control.png for evals/semantic-data.

Mock coffee-roaster invoice/receipt card. The defect: the SUBTOTAL is
bound to the wrong value ($87.50 instead of the $77.50 the four line
items actually sum to) — the canonical agent bug where a computed field
is hardcoded or bound to a stale/previous-order value. Tax (8%) and
Total are then computed CORRECTLY from the wrong subtotal, so every
adjacent pair of numbers agrees with every other adjacent pair:
subtotal+tax=total holds, tax=8%*subtotal holds. The ONLY way to catch
it is to sum the line items — a reasoning-layer arithmetic check, not a
consistency check.

Everything else is pixel-identical to the control, which carries the
correct subtotal ($77.50), tax ($6.20), and total ($83.70).

Line items (identical in both images):
    Ethiopia Yirgacheffe 250g ......... $38.00
    Colombia Huila 250g ............... $19.00
    Chemex filters 100ct .............. $14.50
    Standard shipping ................. $ 6.00
    sum ................................ $77.50

DEFECT:  subtotal $87.50  tax $7.00  total $94.50   (internally consistent,
         wrong vs items — off by exactly $10.00)
CONTROL: subtotal $77.50  tax $6.20  total $83.70   (correct)

Run from repo root:
    uv run --with pillow python3 evals/semantic-data/make_images.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

W, H = 680, 660
PAGE_BG = (240, 242, 245)
CARD_BG = (255, 255, 255)
BORDER = (229, 231, 235)
INK = (17, 24, 39)
BODY = (55, 65, 81)
SUB = (107, 114, 128)
ACCENT = (37, 99, 235)

FONT_DIR = "/System/Library/Fonts/Supplemental"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_MERCHANT = font("Arial Bold.ttf", 24)
F_INVOICE = font("Arial.ttf", 15)
F_ITEM = font("Arial.ttf", 16)
F_AMT = font("Arial.ttf", 16)
F_TOTAL_L = font("Arial.ttf", 16)
F_TOTAL_V = font("Arial Bold.ttf", 19)
F_FOOT = font("Arial.ttf", 13)

ITEMS = [
    ("Ethiopia Yirgacheffe 250g", "$38.00"),
    ("Colombia Huila 250g", "$19.00"),
    ("Chemex filters 100ct", "$14.50"),
    ("Standard shipping", "$6.00"),
]

# the wrong binding: subtotal +10.00; tax/total correctly derived from it
TOTALS = {
    "defect": [("Subtotal", "$87.50"),
               ("Tax (8%)", "$7.00"),
               ("Total", "$94.50", True)],
    "control": [("Subtotal", "$77.50"),
                ("Tax (8%)", "$6.20"),
                ("Total", "$83.70", True)],
}


def build(kind: str, out_path: Path) -> None:
    img = Image.new("RGB", (W, H), PAGE_BG)
    d = ImageDraw.Draw(img)

    card = (60, 40, 620, 620)
    x0, y0, x1, y1 = card
    d.rounded_rectangle(card, radius=16, fill=CARD_BG,
                        outline=BORDER, width=2)

    rx = x1 - 52          # right edge for amounts
    lx = x0 + 48          # left edge for labels

    # --- header ---
    d.text((lx, y0 + 36), "Acme Coffee Roasters", font=F_MERCHANT,
           fill=INK)
    d.text((lx, y0 + 74), "Invoice #1042  ·  November 14, 2025",
           font=F_INVOICE, fill=SUB)

    # --- line items ---
    sep_y = y0 + 116
    d.line([(lx, sep_y), (rx, sep_y)], fill=BORDER, width=1)
    iy = sep_y + 24
    for name, amt in ITEMS:
        d.text((lx, iy), name, font=F_ITEM, fill=BODY)
        aw = d.textlength(amt, font=F_AMT)
        d.text((rx - aw, iy), amt, font=F_AMT, fill=BODY)
        iy += 38

    # --- totals ---
    ty = iy + 10
    d.line([(lx, ty), (rx, ty)], fill=BORDER, width=1)
    ty += 22
    for row in TOTALS[kind]:
        label, value = row[0], row[1]
        bold = len(row) > 2 and row[2]
        lf = F_TOTAL_V if bold else F_TOTAL_L
        vf = F_TOTAL_V if bold else F_AMT
        fill = INK if bold else BODY
        d.text((lx, ty), label, font=lf, fill=fill)
        vw = d.textlength(value, font=vf)
        d.text((rx - vw, ty), value, font=vf, fill=fill)
        ty += 40 if bold else 34

    # --- footer ---
    d.text((lx, ty + 14),
           "Questions about this invoice? billing@acmecoffee.example",
           font=F_FOOT, fill=SUB)
    d.text((lx, ty + 36), "Thank you for your order.",
           font=F_FOOT, fill=SUB)

    img.save(out_path)
    print(f"wrote {out_path}  kind={kind}")


def main() -> None:
    # DEFECT: subtotal bound wrong (+$10.00); tax and total derived
    # correctly from the wrong subtotal — only item-summation catches it.
    build("defect", HERE / "defect.png")
    # CONTROL: correct subtotal, tax, total.
    build("control", HERE / "control.png")

    # sanity: assert the arithmetic the defect hides
    items_sum = 38.00 + 19.00 + 14.50 + 6.00
    assert abs(items_sum - 77.50) < 1e-9
    assert abs(0.08 * 77.50 - 6.20) < 1e-9
    assert abs(0.08 * 87.50 - 7.00) < 1e-9
    assert abs(77.50 + 6.20 - 83.70) < 1e-9
    assert abs(87.50 + 7.00 - 94.50) < 1e-9


if __name__ == "__main__":
    main()
