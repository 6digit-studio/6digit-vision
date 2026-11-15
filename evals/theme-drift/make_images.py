"""Generate state-a.png (consistent theme) + state-b.png (theme break).

Simulates the classic agent-shipped theming-token bug: two states of the
same "Overview" dashboard. The app shell (sidebar, header, primary
button) is a shared component and keeps the brand blue accent in both
states. The main-content components (range toggle, stat icon chips,
chart series, progress bars, links) were regenerated for the "month"
view and carry a different accent token — violet instead of blue —
with no semantic reason (this is not a success/error/warning state).

Everything else is identical: same layout, same data, same strings
except the subtitle and the toggle's active segment.

Run from repo root:
    uv run --with pillow python3 evals/theme-drift/make_images.py
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 1100, 760

# --- surfaces / ink ---
APP_BG = (238, 241, 245)        # #eef1f5
SIDE_BG = (255, 255, 255)
CARD = (255, 255, 255)
CARD_BORDER = (226, 232, 240)   # #e2e8f0
SIDE_BORDER = (219, 226, 234)   # #dbe2ea
INK = (15, 23, 42)              # #0f172a
BODY = (51, 65, 85)             # #334155
SUB = (100, 116, 139)           # #64748b
FAINT = (148, 163, 184)         # #94a3b8
TRACK = (226, 232, 240)
GRID = (237, 242, 247)
PREV = (203, 213, 225)          # previous-period series
AVATAR = (148, 163, 184)
GREEN = (22, 163, 74)
RED = (220, 38, 38)

# --- accents ---
BLUE = (37, 99, 235)            # #2563eb  brand accent
BLUE_DARK = (29, 78, 216)       # #1d4ed8
BLUE_TINT = (219, 234, 254)     # #dbeafe
VIOLET = (124, 58, 237)         # #7c3aed  the stray token
VIOLET_DARK = (109, 40, 217)    # #6d28d9
VIOLET_TINT = (237, 233, 254)   # #ede9fe

FONT_DIR = "/System/Library/Fonts/Supplemental"
F_BOLD = f"{FONT_DIR}/Arial Bold.ttf"
F_REG = f"{FONT_DIR}/Arial.ttf"

SX0 = 258          # main content left edge (sidebar is 0..230, pad 28)
SX1 = 1072         # main content right edge


def font(path, size):
    return ImageFont.truetype(path, size)


def txtw(s, f):
    return f.getlength(s)


def text_c(d, cx, cy, s, f, fill):
    """Center text horizontally at cx, vertically at cy (bbox center)."""
    bbox = d.textbbox((0, 0), s, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), s, font=f, fill=fill)


def draw_right(d, xr, y, s, f, fill):
    d.text((xr - txtw(s, f), y), s, font=f, fill=fill)


def card(d, box, r=12):
    d.rounded_rectangle(box, radius=r, fill=CARD, outline=CARD_BORDER, width=1)


# ---------------------------------------------------------------- chrome

def draw_sidebar(d):
    """Identical in both states — shared shell component, brand blue."""
    d.rectangle((0, 0, 230, H), fill=SIDE_BG)
    d.line((230, 0, 230, H), fill=SIDE_BORDER, width=1)

    # logo mark + wordmark
    d.rounded_rectangle((24, 22, 58, 56), radius=9, fill=BLUE)
    text_c(d, 41, 39, "A", font(F_BOLD, 20), (255, 255, 255))
    d.text((70, 26), "Acme Analytics", font=font(F_BOLD, 15), fill=INK)
    d.text((70, 48), "Workspace", font=font(F_REG, 11), fill=FAINT)

    d.line((24, 76, 206, 76), fill=CARD_BORDER, width=1)
    d.text((26, 92), "MENU", font=font(F_BOLD, 10), fill=FAINT)

    # nav items — Dashboard is the active page (blue pill, both states)
    nav = [
        ("Dashboard", True),
        ("Projects", False),
        ("Reports", False),
        ("Settings", False),
    ]
    y = 114
    for name, active in nav:
        if active:
            d.rounded_rectangle((16, y, 214, y + 36), radius=8, fill=BLUE_TINT)
        # icon: 2x2 squares for dashboard; simple glyphs for the rest
        ic = (30, y + 11)
        if name == "Dashboard":
            for dx, dy in ((0, 0), (8, 0), (0, 8), (8, 8)):
                d.rectangle((ic[0] + dx, ic[1] + dy, ic[0] + dx + 6,
                             ic[1] + dy + 6),
                            fill=BLUE_DARK if active else SUB)
        elif name == "Projects":
            d.rectangle((ic[0], ic[1] + 3, ic[0] + 16, ic[1] + 15),
                        outline=SUB if not active else BLUE_DARK, width=2)
            d.rectangle((ic[0] + 2, ic[1], ic[0] + 8, ic[1] + 5),
                        fill=SUB if not active else BLUE_DARK)
        elif name == "Reports":
            for i, bh in enumerate((6, 10, 14)):
                d.rectangle((ic[0] + i * 6, ic[1] + 16 - bh,
                             ic[0] + i * 6 + 4, ic[1] + 16),
                            fill=SUB if not active else BLUE_DARK)
        else:
            d.ellipse((ic[0], ic[1], ic[0] + 16, ic[1] + 16),
                      outline=SUB if not active else BLUE_DARK, width=2)
            d.ellipse((ic[0] + 6, ic[1] + 6, ic[0] + 10, ic[1] + 10),
                      fill=SUB if not active else BLUE_DARK)
        d.text((56, y + 11), name,
               font=font(F_BOLD if active else F_REG, 13),
               fill=BLUE_DARK if active else BODY)
        y += 44

    # user card pinned to bottom
    d.rounded_rectangle((16, 648, 214, 716), radius=10,
                        fill=(248, 250, 252), outline=CARD_BORDER, width=1)
    d.ellipse((28, 662, 52, 686), fill=AVATAR)
    text_c(d, 40, 674, "LD", font(F_BOLD, 9), (255, 255, 255))
    d.text((60, 664), "Lars Dev", font=font(F_BOLD, 12), fill=INK)
    d.text((60, 681), "lars@acme.io", font=font(F_REG, 10), fill=FAINT)
    d.rounded_rectangle((158, 672, 198, 692), radius=10, fill=BLUE_TINT)
    text_c(d, 178, 682, "PRO", font(F_BOLD, 9), BLUE_DARK)


def draw_header(d):
    """Identical in both states — shared shell, brand blue button."""
    d.text((SX0, 26), "Overview", font=font(F_BOLD, 24), fill=INK)
    return  # subtitle drawn per-state in draw_content


def draw_chrome_right(d):
    """Search + primary button + avatar — identical in both states."""
    # search box
    d.rounded_rectangle((SX0 + 436, 26, SX0 + 626, 62), radius=8,
                        fill=CARD, outline=(203, 213, 225), width=1)
    d.ellipse((SX0 + 452, 36, SX0 + 466, 50), outline=SUB, width=2)
    d.line((SX0 + 462, 46, SX0 + 472, 56), fill=SUB, width=2)
    d.text((SX0 + 480, 40), "Search...", font=font(F_REG, 13), fill=FAINT)
    # primary button — brand blue in BOTH states (shared chrome)
    d.rounded_rectangle((SX0 + 652, 26, SX0 + 798, 62), radius=8, fill=BLUE)
    text_c(d, SX0 + 725, 44, "New report", font(F_BOLD, 13), (255, 255, 255))
    # avatar
    d.ellipse((SX0 + 810, 27, SX0 + 844, 61), fill=(100, 116, 139))
    text_c(d, SX0 + 827, 44, "AK", font(F_BOLD, 10), (255, 255, 255))
    d.line((SX0, 76, SX1, 76), fill=(230, 234, 240), width=1)


# ---------------------------------------------------------------- content

def draw_toggle(d, month_active, acc_dark):
    """Segmented 'This week | This month' control.

    Active segment text takes the content accent — blue in state A,
    violet in state B.
    """
    x0, y0, x1, y1 = SX0, 100, SX0 + 220, 136
    d.rounded_rectangle((x0, y0, x1, y1), radius=8, fill=TRACK)
    seg_w = (x1 - x0 - 6) / 2
    for i, label in enumerate(("This week", "This month")):
        sx0 = x0 + 3 + i * seg_w
        sx1 = sx0 + seg_w
        active = (i == 1) == month_active
        if active:
            d.rounded_rectangle((sx0, y0 + 3, sx1, y1 - 3), radius=6,
                                fill=CARD)
        text_c(d, (sx0 + sx1) / 2, (y0 + y1) / 2, label,
               font(F_BOLD if active else F_REG, 12),
               acc_dark if active else SUB)


def draw_stat_cards(d, acc, acc_tint):
    cards = [
        ("Revenue", "$48.2k", "+12.4%", GREEN, "$"),
        ("Active users", "8,341", "+3.1%", GREEN, "U"),
        ("Conversion", "3.8%", "-0.4%", RED, "%"),
    ]
    y, h = 154, 96
    cw = 260
    for i, (label, val, delta, dcol, glyph) in enumerate(cards):
        x = SX0 + i * (cw + 16)
        card(d, (x, y, x + cw, y + h))
        d.rounded_rectangle((x + 18, y + 18, x + 54, y + 54), radius=9,
                            fill=acc_tint)
        text_c(d, x + 36, y + 36, glyph, font(F_BOLD, 16), acc)
        d.text((x + 68, y + 30), label, font=font(F_REG, 11), fill=SUB)
        d.text((x + 18, y + 56), val, font=font(F_BOLD, 22), fill=INK)
        d.text((x + 18, y + 80), delta, font=font(F_REG, 11), fill=dcol)


def chart_points():
    """12 deterministic data points across the plot width."""
    px0, px1 = 282, 1048
    base, top = 512, 336
    cur = [35, 58, 44, 67, 52, 74, 61, 80, 66, 85, 72, 90]
    prv = [40, 46, 51, 49, 55, 58, 62, 60, 64, 63, 67, 66]

    def pts(vals):
        step = (px1 - px0) / (len(vals) - 1)
        return [(px0 + i * step, base - v / 100 * (base - top))
                for i, v in enumerate(vals)]
    return pts(cur), pts(prv)


def draw_chart(img, d, acc, acc_tint):
    x0, y0, x1, y1 = SX0, 266, SX1, 550
    card(d, (x0, y0, x1, y1))
    d.text((x0 + 24, y0 + 20), "Revenue", font=font(F_BOLD, 15), fill=INK)
    draw_right(d, x1 - 24, y0 + 23, "Export CSV", font(F_REG, 12), acc)
    d.text((x0 + 24, y0 + 44), "Trailing 30 days - USD",
           font=font(F_REG, 11), fill=SUB)

    # legend
    d.ellipse((760, y0 + 50, 768, y0 + 58), fill=acc)
    d.text((774, y0 + 47), "Current", font=font(F_REG, 11), fill=SUB)
    d.ellipse((852, y0 + 50, 860, y0 + 58), fill=PREV)
    d.text((866, y0 + 47), "Previous", font=font(F_REG, 11), fill=SUB)

    # grid
    for gy in (336, 380, 424, 468, 512):
        d.line((282, gy, 1048, gy), fill=GRID, width=1)
    for gx, lab in ((282, "Nov 1"), (473, "Nov 7"), (665, "Nov 14"),
                    (856, "Nov 21"), (1048, "Nov 28")):
        text_c(d, gx, 526, lab, font(F_REG, 10), FAINT)

    cur, prv = chart_points()

    # current-period area fill — accent-tinted, translucent, under the lines
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon(cur + [(1048, 512), (282, 512)], fill=acc_tint + (70,))
    img.paste(overlay, (0, 0), overlay)

    # previous period — neutral gray, identical in both states
    d.line(prv, fill=PREV, width=2, joint="curve")

    # current period — THE accent element: blue in A, violet in B
    d.line(cur, fill=acc, width=3, joint="curve")
    for px, py in cur:
        d.ellipse((px - 3.5, py - 3.5, px + 3.5, py + 3.5), fill=acc)


def draw_bottom_left(d, acc):
    """'Top pages' table card."""
    x0, y0, x1, y1 = SX0, 566, SX0 + 500, 716
    card(d, (x0, y0, x1, y1))
    d.text((x0 + 20, y0 + 16), "Top pages", font=font(F_BOLD, 14), fill=INK)
    draw_right(d, x1 - 20, y0 + 18, "View all", font(F_REG, 12), acc)

    rows = [
        ("/pricing", "12,480", "+8.2%", GREEN),
        ("/blog/product-launch", "9,317", "+14.6%", GREEN),
        ("/docs/api-reference", "6,204", "+2.1%", GREEN),
        ("/enterprise", "3,891", "-1.3%", RED),
    ]
    ry = y0 + 48
    for path, count, delta, dcol in rows:
        d.text((x0 + 20, ry), path, font=font(F_REG, 12), fill=BODY)
        draw_right(d, x1 - 64, ry, count, font(F_BOLD, 12), INK)
        draw_right(d, x1 - 20, ry, delta, font(F_REG, 11), dcol)
        ry += 27


def draw_goals(d, acc):
    """'Goals' progress card."""
    x0, y0, x1, y1 = SX0 + 516, 566, SX1, 716
    card(d, (x0, y0, x1, y1))
    d.text((x0 + 20, y0 + 16), "Goals", font=font(F_BOLD, 14), fill=INK)

    goals = [("Q4 revenue target", "72%"), ("New signups", "45%"),
             ("NPS score", "88%")]
    iy = y0 + 48
    for label, pct in goals:
        d.text((x0 + 20, iy), label, font=font(F_REG, 12), fill=SUB)
        draw_right(d, x1 - 20, iy, pct, font(F_BOLD, 12), INK)
        bx0, bx1 = x0 + 20, x1 - 20
        d.rounded_rectangle((bx0, iy + 18, bx1, iy + 24), radius=3,
                            fill=TRACK)
        fw = (bx1 - bx0) * int(pct.rstrip("%")) / 100
        d.rounded_rectangle((bx0, iy + 18, bx0 + fw, iy + 24), radius=3,
                            fill=acc)
        iy += 38


def build(state, out_path):
    month_active = state == "b"
    # the theme break: content accent is violet in state B, blue in A
    acc, acc_dark, acc_tint = (
        (VIOLET, VIOLET_DARK, VIOLET_TINT) if state == "b"
        else (BLUE, BLUE_DARK, BLUE_TINT)
    )
    subtitle = ("November 2025 - month to date" if state == "b"
                else "Week of Nov 10 - 16, 2025")

    img = Image.new("RGB", (W, H), APP_BG)
    d = ImageDraw.Draw(img)

    draw_sidebar(d)          # shared chrome — blue in both states
    draw_header(d)
    d.text((SX0, 56), subtitle, font=font(F_REG, 12), fill=SUB)
    draw_chrome_right(d)     # shared chrome — blue button in both states

    draw_toggle(d, month_active, acc_dark)
    draw_stat_cards(d, acc, acc_tint)
    draw_chart(img, d, acc, acc_tint)
    draw_bottom_left(d, acc)
    draw_goals(d, acc)

    img.save(out_path)
    print(f"{out_path}: state={state} content_accent="
          f"{'#7c3aed (violet)' if state == 'b' else '#2563eb (blue)'}")


def main():
    build("a", "evals/theme-drift/state-a.png")
    build("b", "evals/theme-drift/state-b.png")


if __name__ == "__main__":
    main()
