"""Generate control.png (correct 16:9 aspect) + defect.png (square-squashed).

Simulates the classic agent-shipped bug: a dashboard "share card" designed
at 1200x675 (16:9) gets exported to a square 1000x1000 asset by a
non-uniform resize — PIL `img.resize((1000, 1000))` or CSS
`object-fit: fill` (the default) in a square container. Content fills the
canvas but is squeezed horizontally (sx=0.833) and stretched vertically
(sy=1.481): every circle becomes a ~1.78:1 tall ellipse, glyphs stretch,
the chart's aspect lies.

The scene is deliberately circle-rich (stat icon chips, avatar, legend
dots, 12 chart data points) so the distortion is machine-verifiable, not
aesthetic opinion.

Run from repo root:
    uv run --with pillow python3 evals/aspect-abuse/make_images.py
"""

from PIL import Image, ImageDraw, ImageFont

SRC_W, SRC_H = 1200, 675          # the design's natural 16:9 canvas
OUT = 1000                        # the square export canvas (the bug)

# --- surfaces / ink (same palette language as theme-drift) ---
APP_BG = (238, 241, 245)
CARD = (255, 255, 255)
CARD_BORDER = (226, 232, 240)
TINT = (247, 249, 252)
INK = (15, 23, 42)
BODY = (51, 65, 85)
SUB = (100, 116, 139)
FAINT = (148, 163, 184)
TRACK = (226, 232, 240)
GRID = (237, 242, 247)
PREV = (203, 213, 225)
AVATAR = (100, 116, 139)
GREEN = (22, 163, 74)
RED = (220, 38, 38)
BLUE = (37, 99, 235)
BLUE_TINT = (219, 234, 254)
AMBER = (217, 119, 6)
AMBER_TINT = (254, 243, 199)
VIOLET = (124, 58, 237)
VIOLET_TINT = (237, 233, 254)

FONT_DIR = "/System/Library/Fonts/Supplemental"
F_BOLD = f"{FONT_DIR}/Arial Bold.ttf"
F_REG = f"{FONT_DIR}/Arial.ttf"

# card geometry inside the 1200x675 source
CX0, CY0, CX1, CY1 = 90, 55, 1110, 620      # outer card
HX, HY = 130, 95                            # header text origin


def font(path, size):
    return ImageFont.truetype(path, size)


def text_c(d, cx, cy, s, f, fill):
    bbox = d.textbbox((0, 0), s, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), s, font=f, fill=fill)


def draw_right(d, xr, y, s, f, fill):
    d.text((xr - f.getlength(s), y), s, font=f, fill=fill)


def card(d, box, r=12, fill=CARD, outline=CARD_BORDER):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=1)


def build_source():
    img = Image.new("RGB", (SRC_W, SRC_H), APP_BG)
    d = ImageDraw.Draw(img)

    # ------------------------------------------------ outer card + header
    card(d, (CX0, CY0, CX1, CY1), r=16)

    d.text((HX, HY), "Weekly metrics", font=font(F_BOLD, 26), fill=INK)
    d.text((HX, HY + 36), "Nov 10 - Nov 16, 2025 - all regions",
           font=font(F_REG, 13), fill=SUB)

    # share button (rounded rect) + avatar circle — right side of header
    d.rounded_rectangle((950, HY + 4, 1110, HY + 40), radius=10, fill=BLUE)
    text_c(d, 1030, HY + 22, "Share report", font(F_BOLD, 13),
           (255, 255, 255))
    d.ellipse((1120, HY + 8, 1152, HY + 40), fill=AVATAR)
    text_c(d, 1136, HY + 24, "AK", font(F_BOLD, 10), (255, 255, 255))

    d.line((HX, 178, CX1 - 20, 178), fill=(230, 234, 240), width=1)

    # ------------------------------------------------ 3 stat cards
    # each: circular icon chip (ellipse -> the distortion tell),
    # label, big value, delta
    stats = [
        ("Revenue", "$48.2k", "+12.4%", GREEN, "$", BLUE, BLUE_TINT),
        ("Active users", "8,341", "+3.1%", GREEN, "U", VIOLET, VIOLET_TINT),
        ("Churn risk", "3.8%", "-0.4%", RED, "%", AMBER, AMBER_TINT),
    ]
    sy, sh = 198, 118
    sw, gap = 320, 20
    for i, (label, val, delta, dcol, glyph, acc, tint) in enumerate(stats):
        x = HX + i * (sw + gap)
        card(d, (x, sy, x + sw, sy + sh), r=12, fill=TINT,
             outline=(233, 238, 244))
        # circular icon chip — 44px circle in source
        d.ellipse((x + 18, sy + 18, x + 62, sy + 62), fill=tint)
        text_c(d, x + 40, sy + 40, glyph, font(F_BOLD, 18), acc)
        d.text((x + 74, sy + 26), label, font=font(F_REG, 12), fill=SUB)
        d.text((x + 18, sy + 62), val, font=font(F_BOLD, 26), fill=INK)
        d.text((x + 18, sy + 94), delta, font=font(F_REG, 12), fill=dcol)

    # ------------------------------------------------ chart card
    cy0, cy1 = 340, 540
    card(d, (HX, cy0, CX1 - 20, cy1), r=12)
    d.text((HX + 24, cy0 + 18), "Revenue",
           font=font(F_BOLD, 15), fill=INK)
    draw_right(d, CX1 - 44, cy0 + 20, "Export CSV",
               font(F_REG, 12), BLUE)
    d.text((HX + 24, cy0 + 42), "Trailing 7 days - USD",
           font=font(F_REG, 11), fill=SUB)

    # legend: two small circles + labels
    d.ellipse((CX1 - 300, cy0 + 48, CX1 - 288, cy0 + 60), fill=BLUE)
    d.text((CX1 - 282, cy0 + 45), "Current", font=font(F_REG, 11),
           fill=SUB)
    d.ellipse((CX1 - 196, cy0 + 48, CX1 - 184, cy0 + 60), fill=PREV)
    d.text((CX1 - 178, cy0 + 45), "Previous", font=font(F_REG, 11),
           fill=SUB)

    # gridlines + y range
    plot_x0, plot_x1 = HX + 40, CX1 - 60
    base, top = cy1 - 42, cy0 + 110
    for gy in (380, 420, 460, 500):
        d.line((plot_x0, gy, plot_x1, gy), fill=GRID, width=1)

    cur = [42, 55, 48, 66, 58, 74, 70]
    prv = [38, 44, 47, 52, 50, 55, 57]

    def pts(vals):
        step = (plot_x1 - plot_x0) / (len(vals) - 1)
        return [(plot_x0 + i * step, base - v / 100 * (base - top))
                for i, v in enumerate(vals)]

    cpts, ppts = pts(cur), pts(prv)

    # area fill under current series (translucent blue)
    overlay = Image.new("RGBA", (SRC_W, SRC_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon(cpts + [(plot_x1, base), (plot_x0, base)],
               fill=BLUE_TINT + (90,))
    img.paste(overlay, (0, 0), overlay)
    d = ImageDraw.Draw(img)

    d.line(ppts, fill=PREV, width=2, joint="curve")
    d.line(cpts, fill=BLUE, width=3, joint="curve")
    # 7 circular data points — become ellipses under the squash
    for px, py in cpts:
        d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=BLUE)
    for px, py in ppts:
        d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=PREV)

    # x labels
    for i, lab in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
                             "Sun")):
        text_c(d, plot_x0 + i * (plot_x1 - plot_x0) / 6, cy1 - 18,
               lab, font(F_REG, 10), FAINT)

    # ------------------------------------------------ bottom row: list + goals
    by0, by1 = 566, 612
    card(d, (HX, by0, HX + 470, by1), r=12, fill=TINT,
         outline=(233, 238, 244))
    d.text((HX + 18, by0 + 10), "Top pages",
           font=font(F_BOLD, 13), fill=INK)
    rows = [("/pricing", "12.4k"), ("/blog/launch", "9.1k"),
            ("/docs/api", "6.2k")]
    ry = by0 + 34
    for path, cnt in rows:
        d.text((HX + 18, ry), path, font=font(F_REG, 11), fill=BODY)
        draw_right(d, HX + 452, ry, cnt, font(F_BOLD, 11), INK)
        ry += 14

    gx0 = HX + 490
    card(d, (gx0, by0, CX1 - 20, by1), r=12, fill=TINT,
         outline=(233, 238, 244))
    d.text((gx0 + 18, by0 + 10), "Goals",
           font=font(F_BOLD, 13), fill=INK)
    goals = [("Q4 revenue", 72), ("New signups", 45)]
    gy = by0 + 32
    for label, pct in goals:
        d.text((gx0 + 18, gy), label, font=font(F_REG, 11), fill=SUB)
        bx0, bx1 = gx0 + 18, CX1 - 38
        d.rounded_rectangle((bx0, gy + 15, bx1, gy + 20), radius=2,
                            fill=TRACK)
        d.rounded_rectangle((bx0, gy + 15, bx0 + (bx1 - bx0) * pct / 100,
                             gy + 20), radius=2, fill=BLUE)
        gy += 20

    return img


def circle_ellipses(img):
    """Verify the distortion: a known source circle's pixel bbox aspect.

    The avatar is drawn at source coords (1120..1152, HY+8..HY+40) =
    32x32 px circle. Returns its bbox aspect (h/w) in the given image —
    1.0 = circle, ~1.78 = the squash.
    """
    w, h = img.size
    sx, sy = w / SRC_W, h / SRC_H
    x0 = round(1120 * sx)
    y0 = round((HY + 8) * sy)
    x1 = round(1152 * sx)
    y1 = round((HY + 40) * sy)
    crop = img.crop((x0, y0, x1, y1)).convert("L")
    px = crop.load()
    xs, ys = [], []
    for y in range(crop.height):
        for x in range(crop.width):
            if px[x, y] < 128:  # avatar fill is dark slate on white card
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    return round(bh / bw, 3), (bw, bh)


def main():
    src = build_source()

    # CONTROL: the design at its intended aspect — what the agent should
    # have shipped. Saved at native 1200x675.
    src.save("evals/aspect-abuse/control.png")
    print(f"control.png: {src.size} aspect={src.width / src.height:.3f} "
          f"avatar={circle_ellipses(src)}")

    # DEFECT: the agent's square export — non-uniform resize, the
    # object-fit:fill / PIL resize((1000,1000)) bug. sx=0.833, sy=1.481.
    defect = src.resize((OUT, OUT), Image.BILINEAR)
    defect.save("evals/aspect-abuse/defect.png")
    print(f"defect.png: {defect.size} aspect=1.000 "
          f"avatar={circle_ellipses(defect)}")
    print("scale factors: sx=%.3f sy=%.3f  (anisotropy %.2fx)"
          % (OUT / SRC_W, OUT / SRC_H, (OUT / SRC_H) / (OUT / SRC_W)))


if __name__ == "__main__":
    main()
