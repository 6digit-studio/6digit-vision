"""Build defect.png + control.png for evals/z-order.

Mock "Projects" list page: app bar + three stacked project cards, each
with a "..." overflow button. Card 1's dropdown menu is open, hanging
down over card 2's top region.

THE DEFECT (defect.png): wrong paint order / stacking context — cards
2 and 3 are drawn AFTER the menu element, so card 2's opaque white
surface covers the menu's lower half. Menu item 2's text is sliced
horizontally mid-glyph at card 2's top edge, items 3-4 and the menu's
bottom border/shadow are completely invisible. This is the canonical
agent z-index bug: the popover lost the paint-order fight to a later
sibling (missing z-index, or an ancestor stacking context).

control.png: byte-identical scene except the menu is painted LAST —
correct z-order — so all four items and the full menu chrome float
visibly above card 2.

The ONLY intended difference between the two images is what covers the
menu/card-2 overlap region. Everything else is pixel-identical.

Run from repo root:  uv run --with pillow python3 evals/z-order/make_images.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

W, H = 960, 720
PAGE = (243, 244, 246)        # light gray page
CARD = (255, 255, 255)
BORDER = (229, 231, 235)
INK = (17, 24, 39)
BODY = (71, 85, 105)
FAINT = (100, 116, 139)
BTN_BG = (243, 244, 246)
BLUE = (37, 99, 235)
RED = (220, 38, 38)
GREEN_BG = (220, 252, 231)
GREEN_FG = (21, 128, 61)
AMBER_BG = (254, 243, 199)
AMBER_FG = (146, 64, 14)

FONT_DIR = "/System/Library/Fonts/Supplemental"


def font(name: str, size: int):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_TITLE = font("Arial Bold.ttf", 24)
F_NAME = font("Arial Bold.ttf", 20)
F_META = font("Arial.ttf", 14)
F_PILL = font("Arial Bold.ttf", 12)
F_MENU = font("Arial.ttf", 16)
F_NEW = font("Arial Bold.ttf", 15)

# ---- layout constants (shared by both renders) ----
COL_X, COL_W = 120, 720          # content column
CARD_H, GAP = 125, 16
CARD_Ys = [96, 237, 378]         # card1, card2, card3 top edges
CARD_RIGHT = COL_X + COL_W       # 840

# card 1 "..." button: 38x38, right-aligned with 24px padding
BTN = (CARD_RIGHT - 24 - 38, CARD_Ys[0] + 41, CARD_RIGHT - 24, CARD_Ys[0] + 79)
# menu: right edge aligned to button right edge, 6px below button bottom
MENU_W = 210
MENU_X = BTN[2] - MENU_W         # 816 - 210 = 606
MENU_Y = BTN[3] + 6              # 181
MENU_PAD, MENU_ITEM_H = 6, 34
MENU_H = MENU_PAD * 2 + MENU_ITEM_H * 4   # 148 -> bottom 329
MENU_ITEMS = ["Rename", "Duplicate", "Archive", "Delete"]

CHIP_COLORS = [(59, 130, 246), (168, 85, 247), (16, 185, 129)]
NAMES = ["Website redesign", "Mobile app v2", "Brand guidelines"]
METAS = [
    "Sara Chen · Updated 2h ago",
    "Dev team · Updated yesterday",
    "Marketing · Updated 3d ago",
]
PILLS = [("Active", GREEN_BG, GREEN_FG),
         ("In review", AMBER_BG, AMBER_FG),
         ("Active", GREEN_BG, GREEN_FG)]


def rounded(d, box, radius, **kw):
    d.rounded_rectangle(box, radius=radius, **kw)


def draw_appbar(d):
    d.rectangle([0, 0, W, 64], fill=CARD)
    d.line([0, 64, W, 64], fill=BORDER, width=1)
    d.text((COL_X, 20), "Projects", font=F_TITLE, fill=INK)
    # "New project" button, right side
    label = "New project"
    lw = d.textlength(label, font=F_NEW)
    bw, bh = lw + 36, 36
    bx0 = CARD_RIGHT - 24 - bw
    by0 = 14
    rounded(d, (bx0, by0, bx0 + bw, by0 + bh), 8, fill=BLUE)
    d.text((bx0 + 18, by0 + (bh - 20) / 2), label, font=F_NEW,
           fill=(255, 255, 255))
    # avatar circle
    ax = CARD_RIGHT - 24 - bw - 16 - 34
    d.ellipse([ax, 15, ax + 34, 49], fill=(203, 213, 225),
              outline=BORDER)
    d.text((ax + 8, 20), "L", font=F_PILL, fill=FAINT)


def draw_card(d, idx):
    x0 = COL_X
    y0 = CARD_Ys[idx]
    x1 = CARD_RIGHT
    y1 = y0 + CARD_H
    rounded(d, (x0, y0, x1, y1), 12, fill=CARD, outline=BORDER, width=2)

    # color chip
    cx, cy = x0 + 24, y0 + 32
    rounded(d, (cx, cy, cx + 46, cy + 46), 10, fill=CHIP_COLORS[idx])
    # initials letter
    ch = NAMES[idx][0]
    cw = d.textlength(ch, font=F_NAME)
    d.text((cx + 23 - cw / 2, cy + 23 - 13), ch, font=F_NAME,
           fill=(255, 255, 255))

    # name + meta
    d.text((x0 + 88, y0 + 38), NAMES[idx], font=F_NAME, fill=INK)
    d.text((x0 + 88, y0 + 64), METAS[idx], font=F_META, fill=FAINT)

    # status pill (right of the "..." button)
    text, bg, fg = PILLS[idx]
    tw = d.textlength(text, font=F_PILL)
    pw = tw + 22
    px0 = BTN[0] - 14 - pw
    py0 = y0 + 45
    rounded(d, (px0, py0, px0 + pw, py0 + 26), 13, fill=bg)
    d.text((px0 + 11, py0 + 5), text, font=F_PILL, fill=fg)

    # "..." overflow button (three dots)
    rounded(d, BTN, 9, fill=BTN_BG, outline=BORDER, width=1)
    bx = (BTN[0] + BTN[2]) / 2
    by = (BTN[1] + BTN[3]) / 2
    for dx in (-9, 0, 9):
        d.ellipse([bx + dx - 2.4, by - 2.4, bx + dx + 2.4, by + 2.4],
                  fill=FAINT)


def draw_menu(d):
    """Dropdown menu surface + items. Returns nothing; caller controls
    WHEN this is invoked relative to cards (paint order IS the defect)."""
    mx0, my0 = MENU_X, MENU_Y
    mx1, my1 = MENU_X + MENU_W, MENU_Y + MENU_H
    # drop shadow (fake, offset)
    rounded(d, (mx0 + 1, my0 + 5, mx1 + 1, my1 + 5), 10,
            fill=(15, 23, 42, 38))
    rounded(d, (mx0, my0, mx1, my1), 10, fill=CARD, outline=BORDER,
            width=1)
    for i, label in enumerate(MENU_ITEMS):
        iy = my0 + MENU_PAD + i * MENU_ITEM_H
        color = RED if label == "Delete" else INK
        d.text((mx0 + 16, iy + 8), label, font=F_MENU, fill=color)


def render(menu_last: bool) -> Image.Image:
    img = Image.new("RGBA", (W, H), PAGE + (255,))
    d = ImageDraw.Draw(img)
    draw_appbar(d)
    draw_card(d, 0)
    if menu_last:
        pass  # menu painted after all cards -> correct z-order
    else:
        draw_menu(d)          # defect: menu under cards 2 and 3
    draw_card(d, 1)
    draw_card(d, 2)
    if menu_last:
        draw_menu(d)          # control: menu on top
    return img.convert("RGB")


def main() -> None:
    render(menu_last=False).save(HERE / "defect.png")
    render(menu_last=True).save(HERE / "control.png")
    print("wrote defect.png and control.png")
    print(f"menu box: x {MENU_X}-{MENU_X + MENU_W}, y {MENU_Y}-{MENU_Y + MENU_H}")
    print(f"card2 top edge y={CARD_Ys[1]} cuts menu at local y={CARD_Ys[1] - MENU_Y}")


if __name__ == "__main__":
    main()
