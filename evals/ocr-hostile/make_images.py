#!/usr/bin/env python3
"""Build the ocr-hostile eval pair.

defect.png  — "Bloom & Stem" landing hero where the brand wordmark is a
               Savoye LET calligraphic script, the eyebrow is wide-tracked
               all-caps, and the hero headline is Snell Roundhand script.
               Content is perfectly readable to a human; recognition is
               the question.
control.png — pixel-identical layout, colors, and copy, but every string
               set in clean Arial (regular/bold), normal tracking.

Only the type treatment differs — same positions, same palette, same
sizes (control sizes auto-fit to the defect's rendered widths).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

W, H = 920, 640

BG = (250, 246, 240)        # warm cream page
CARD = (255, 253, 250)      # slightly lighter panel
INK = (31, 61, 43)          # deep green — primary text
MUTED = (122, 110, 96)      # warm gray — secondary text
ACCENT = (178, 74, 32)      # terracotta — eyebrow + CTA
WHITE = (255, 255, 255)
LINE = (226, 216, 202)      # hairline divider

F = {
    # clean stack (control + body copy in both)
    "arial": "/System/Library/Fonts/Supplemental/Arial.ttf",
    "arial_b": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    # hostile stack (defect only)
    "wordmark": "/System/Library/Fonts/Supplemental/Savoye LET.ttc",
    "headline": "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc",
}


def font(key, size):
    return ImageFont.truetype(F[key], size)


def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def draw_tracked(draw, cx, y, s, f, fill, tracking=0.0):
    """Center a string with extra per-glyph tracking (letter-spacing)."""
    widths = [draw.textlength(ch, font=f) for ch in s]
    total = sum(widths) + tracking * max(0, len(s) - 1)
    x = cx - total / 2
    for ch, w in zip(s, widths):
        draw.text((x, y), ch, font=f, fill=fill)
        x += w + tracking
    return total


def fit_size(draw, s, key, target_w, lo=8, hi=160):
    """Binary-search a font size whose rendered width ~= target_w."""
    best = lo
    for _ in range(24):
        mid = (lo + hi) / 2
        if text_w(draw, s, font(key, mid)) < target_w:
            best, lo = mid, mid
        else:
            hi = mid
    return round(best)


def build(hostile: bool) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ---- nav -------------------------------------------------------------
    d.line([(0, 84), (W, 84)], fill=LINE, width=1)

    # wordmark — Savoye LET script vs Arial Bold
    if hostile:
        wm = font("wordmark", 46)
        wm_y = 22
    else:
        wm = font("arial_b", 30)
        wm_y = 30
    d.text((48, wm_y), "Bloom & Stem", font=wm, fill=INK)

    # nav links — clean Arial in both
    nav_f = font("arial", 15)
    for label, x in (("Shop", 700), ("Journal", 758), ("About", 828)):
        d.text((x, 37), label, font=nav_f, fill=MUTED)
    d.text((872, 37), "Cart (0)", font=nav_f, fill=INK)

    # ---- eyebrow ----------------------------------------------------------
    eyebrow = "NEW · SPRING · COLLECTION"
    if hostile:
        eb_f = font("arial_b", 15)
        eb_tracking = 7.0
    else:
        eb_f = font("arial_b", 15)
        eb_tracking = 1.0
    eb_y = 214
    eb_w = draw_tracked(d, W / 2, eb_y, eyebrow, eb_f, ACCENT, eb_tracking)

    # ---- headline ---------------------------------------------------------
    lines = ["Hand-tied bouquets,", "delivered weekly"]
    hl_y = 252
    hl_gap = 66
    if hostile:
        hl_key, hl_base = "headline", 62
    else:
        hl_key, hl_base = "arial_b", 40
    # measure the hostile line widths once, then fit control to them
    hl_fonts = []
    hl_ws = []
    for ln in lines:
        if hostile:
            f = font(hl_key, hl_base)
        else:
            # fit to the defect's width for the same string
            f = None
        hl_fonts.append(f)
    if hostile:
        hl_ws = [text_w(d, ln, f) for ln, f in zip(lines, hl_fonts)]
        for i, ln in enumerate(lines):
            f = font(hl_key, hl_base)
            d.text(((W - text_w(d, ln, f)) / 2, hl_y + i * hl_gap),
                   ln, font=f, fill=INK)
    else:
        # render defect-equivalent widths with the script font to match
        probe = font("headline", hl_base)
        for i, ln in enumerate(lines):
            target = text_w(d, ln, probe)
            size = fit_size(d, ln, "arial_b", target)
            f = font("arial_b", size)
            d.text(((W - text_w(d, ln, f)) / 2, hl_y + i * hl_gap),
                   ln, font=f, fill=INK)

    # ---- subhead ----------------------------------------------------------
    sub = "Seasonal stems, wrapped by hand and couriered the same day."
    sub_f = font("arial", 17)
    sw = text_w(d, sub, sub_f)
    d.text(((W - sw) / 2, 392), sub, font=sub_f, fill=MUTED)

    # ---- CTA ---------------------------------------------------------------
    bw, bh = 236, 54
    bx, by = (W - bw) / 2, 448
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=27,
                        fill=ACCENT)
    cta_f = font("arial_b", 17)
    cta = "Shop the collection"
    cw = text_w(d, cta, cta_f)
    # vertical center: bbox of ascender..descender approx -> use anchor
    d.text((bx + (bw - cw) / 2, by + 15), cta, font=cta_f, fill=WHITE)

    # ---- footer ------------------------------------------------------------
    foot_f = font("arial", 12)
    foot = "Portland, OR — est. 2019 · Open Tue–Sun · Same-day until 2pm"
    fw = text_w(d, foot, foot_f)
    d.text(((W - fw) / 2, 596), foot, font=foot_f, fill=MUTED)

    return img


def main():
    defect = build(hostile=True)
    control = build(hostile=False)
    defect.save(HERE / "defect.png")
    control.save(HERE / "control.png")
    print("wrote defect.png / control.png")

    # sanity: ink bbox in hero band for each
    for name, im in (("defect", defect), ("control", control)):
        g = im.convert("L")
        px = g.load()
        xs, ys = [], []
        for y in range(200, 560):
            for x in range(W):
                if px[x, y] < 120:
                    xs.append(x)
                    ys.append(y)
        if xs:
            print(f"{name}: hero ink bbox x[{min(xs)},{max(xs)}] "
                  f"y[{min(ys)},{max(ys)}] px={len(xs)}")


if __name__ == "__main__":
    main()
