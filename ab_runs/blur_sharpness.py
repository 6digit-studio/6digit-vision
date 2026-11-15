#!/usr/bin/env python3
"""Evidence for the 'fidelity ≠ quality' section: text-crop sharpness and a
4x side-by-side of the flight-card text."""
import math, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parent
CROPS = {
    "ref1-collage": (105, 100, 320, 165),
    "ref3-bp":      (42, 52, 150, 92),
    "ref4-flight":  (36, 34, 180, 95),
}
ARMS = ["A", "B", "C"]

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

def sharp(path, box):
    g = np.asarray(Image.open(path).convert("L").crop(box), dtype=np.float32) / 255.0
    return float(ndimage.laplace(g).var())

ratios = {}
for slug, box in CROPS.items():
    r = sharp(ROOT / "A" / slug / "reference.png", box)
    for a in ARMS:
        ratios[(slug, a)] = sharp(ROOT / a / slug / "candidate.png", box) / r

# --- 4x crop: ref | A | B | C on the flight card -------------------------
box = CROPS["ref4-flight"]
SCALE, GAP, PAD, LAB = 3, 10, 20, 40
tiles = []
for who, p in [("REFERENCE  (soft capture)", ROOT/"A"/"ref4-flight"/"reference.png")] + \
              [(f"{a}  ·  {ratios[('ref4-flight', a)]:.2f}× ref", ROOT/a/"ref4-flight"/"candidate.png") for a in ARMS]:
    im = Image.open(p).convert("RGB").crop(box)
    tiles.append((who, im.resize((im.width*SCALE, im.height*SCALE), Image.LANCZOS)))
W = PAD*2 + sum(t.width for _, t in tiles) + GAP*(len(tiles)-1)
H = PAD*2 + max(t.height for _, t in tiles) + LAB
c = Image.new("RGB", (W, H), (16, 17, 20))
d = ImageDraw.Draw(c)
x = PAD
for who, im in tiles:
    c.paste(im, (x, PAD))
    d.rectangle([x-1, PAD-1, x+im.width, PAD+im.height], outline=(58, 60, 68))
    d.text((x, PAD + im.height + 10), who, font=font(13, bold=True), fill=(190, 194, 202))
    x += im.width + GAP
c.save(ROOT / "blur_crop.png")
print("saved blur_crop.png", c.size)

# --- grouped bars: sharpness ratio, log scale ----------------------------
GROUPS = ["ref1-collage", "ref3-bp", "ref4-flight"]
SSIM = {"ref1-collage": (.833, .885, .907), "ref3-bp": (.544, .928, .910),
        "ref4-flight": (.665, .889, .864)}
W, H = 1100, 560
PAD, TOP, BOT = 40, 120, 90
plot_h = H - TOP - BOT
ymin, ymax = 0.2, 10.0
def ypos(v): return TOP + plot_h - (math.log10(v) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin)) * plot_h
c = Image.new("RGB", (W, H), (16, 17, 20))
d = ImageDraw.Draw(c)
d.text((PAD, 26), "Text sharpness vs the reference", font=font(24, bold=True), fill=(240, 242, 245))
d.text((PAD, 58), "Laplacian variance on a fixed text crop, relative to the reference · 1.0 = same softness · log scale",
       font=font(12), fill=(150, 154, 165))
# gridlines
for v in [0.3, 0.5, 1, 2, 5, 10]:
    y = ypos(v)
    d.line([PAD, y, W-PAD, y], fill=(38, 42, 49))
    d.text((W-PAD+4, y-7), f"{v:g}", font=font(11), fill=(120, 124, 132))
y1 = ypos(1.0)
d.line([PAD, y1, W-PAD, y1], fill=(139, 148, 158), width=2)
d.text((PAD+6, y1-16), "reference softness", font=font(11, bold=True), fill=(170, 174, 182))
colors = {"A": (88, 166, 255), "B": (63, 185, 80), "C": (219, 109, 222)}
gw = (W - PAD*2) / len(GROUPS)
for gi, g in enumerate(GROUPS):
    gx = PAD + gi*gw
    bw = gw/5.2
    for ai, a in enumerate(ARMS):
        v = ratios[(g, a)]
        bh = abs(ypos(v) - ypos(1.0))
        y0 = min(ypos(v), ypos(1.0))
        x = gx + gw/2 - (3*bw + 2*6)/2 + ai*(bw+6)
        d.rounded_rectangle([x, y0, x+bw, y0+bh], radius=4, fill=colors[a])
        label = f"{v:.2f}×"
        if v >= 1:
            d.text((x + bw/2, ypos(v) - 18), label, font=font(11, bold=True),
                   fill=(215, 219, 226), anchor="ma")
        else:
            d.text((x + bw/2, ypos(1.0) + 14), label, font=font(11, bold=True),
                   fill=(255, 255, 255), anchor="ma")
    s = SSIM[g]
    d.text((gx + gw/2, H - BOT + 24), g.replace("-", " "),
           font=font(13, bold=True), fill=(210, 214, 222), anchor="ma")
    d.text((gx + gw/2, H - BOT + 44), f"SSIM  A {s[0]:.3f}  B {s[1]:.3f}  C {s[2]:.3f}",
           font=font(11), fill=(150, 154, 165), anchor="ma")
# legend
lx = PAD
for a in ARMS:
    d.rectangle([lx, 88, lx+12, 100], fill=colors[a])
    d.text((lx+18, 87), f"arm {a}", font=font(12), fill=(190, 194, 202))
    lx += 90
c.save(ROOT / "sharpness.png")
print("saved sharpness.png", c.size)
for k in sorted(ratios): print(k, round(ratios[k], 3))
