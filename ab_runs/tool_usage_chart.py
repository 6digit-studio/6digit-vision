#!/usr/bin/env python3
"""tool_usage.png — subcommand calls across the 12 experiment cells."""
import pathlib
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
USED = [("score", 27), ("pixdiff", 20), ("zoom", 11),
        ("describe", 3), ("palette", 3)]
UNUSED = ["parse", "structure", "layout", "ask", "grid", "interrogate", "diff", "reel"]

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

W, H = 1100, 640
pad, row, bar_x = 32, 34, 300
canvas = Image.new("RGB", (W, H), (16, 17, 20))
d = ImageDraw.Draw(canvas)
d.text((pad, 24), "Which eyes subcommands were actually invoked?", font=font(24, bold=True), fill=(240, 242, 245))
d.text((pad, 58), "12 reproduction cells · 67 calls, all from the four measurement-loop (C) cells · A and B: zero",
       font=font(13), fill=(150, 154, 165))

y = 100
maxv = max(v for _, v in USED)
for name, v in USED:
    d.text((pad, y + 4), name, font=font(14, bold=True), fill=(210, 214, 222))
    bw = round((W - bar_x - pad - 80) * v / maxv)
    d.rounded_rectangle([bar_x, y, bar_x + bw, y + 22], radius=5, fill=(88, 166, 255))
    d.text((bar_x + bw + 10, y + 4), str(v), font=font(13, bold=True), fill=(230, 234, 240))
    y += row

y += 10
d.text((pad, y), "never invoked", font=font(14, bold=True), fill=(139, 148, 158))
y += 26
for i, name in enumerate(UNUSED):
    col = i % 4
    xx = pad + col * 260
    yy = y + (i // 4) * 28
    d.rounded_rectangle([xx, yy, xx + 8, yy + 8], radius=2, fill=(48, 54, 61))
    d.text((xx + 18, yy - 4), name, font=font(13), fill=(139, 148, 158))

d.text((pad, 380), "calls by cell", font=font(14, bold=True), fill=(165, 168, 180))
cells = [("ref4 · flight card", 39), ("ref3 · BP widget", 14),
         ("ref1 · collage", 10), ("ref2 · knob", 4)]
y = 408
for name, v in cells:
    d.text((pad, y + 3), name, font=font(12), fill=(190, 194, 202))
    bw = round(360 * v / 39)
    d.rounded_rectangle([bar_x, y, bar_x + bw, y + 16], radius=4, fill=(63, 185, 80))
    d.text((bar_x + bw + 8, y + 2), str(v), font=font(11, bold=True), fill=(210, 214, 222))
    y += 24

y = H - 88
d.text((pad, y), "trusted for decisions", font=font(12, bold=True), fill=(63, 185, 80))
d.text((pad, y + 18), "pixdiff (SSIM / regions) and score (coarse gate only); zoom/describe/palette were tried but not relied on.",
       font=font(12), fill=(150, 154, 165))
d.text((pad, y + 40), "the eight unused commands include the rebuild surfaces — parse, structure, layout — that agents replaced with hand-written PIL probes.",
       font=font(12), fill=(150, 154, 165))
canvas.save(ROOT / "tool_usage.png")
print("saved", ROOT / "tool_usage.png", canvas.size)
