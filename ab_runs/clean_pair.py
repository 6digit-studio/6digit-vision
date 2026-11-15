#!/usr/bin/env python3
"""clean_pair.png — the facts-only isolation pair (A2 vs B2)."""
import json, pathlib
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
REFS = [("ref1-collage", "ref1 · KODOR collage  (1520×794)"),
        ("ref3-bp", "ref3 · BP widget  (394×210)")]
cols = ["ref", "A2", "B2"]
labels = {"ref": "REFERENCE", "A2": "A2 · vision only", "B2": "B2 · vision + facts"}
data = json.loads((ROOT / "clean_results.json").read_text())
res = {(r["ref"], r["arm"]): r for r in data}

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

DISP_W, pad, gap, lab_h = 560, 22, 14, 44
scaled = {}
for slug, _ in REFS:
    for c in cols:
        p = (ROOT / "A" / slug / "reference.png") if c == "ref" \
            else (ROOT / c / slug / "candidate.png")
        if p.exists():
            im = Image.open(p).convert("RGB")
            s = DISP_W / im.width
            scaled[(slug, c)] = im.resize((DISP_W, round(im.height * s)), Image.LANCZOS)
row_h = {s: max(scaled[(s, c)].height for c in cols if (s, c) in scaled) + lab_h
         for s, _ in REFS}
W = pad * 2 + len(cols) * DISP_W + (len(cols) - 1) * gap
H = pad * 2 + 58 + sum(row_h.values()) + gap * (len(REFS) - 1)
canvas = Image.new("RGB", (W, H), (16, 17, 20))
d = ImageDraw.Draw(canvas)
d.text((pad, 20), "Facts-only isolation pair — identical perception-only rules, only facts.json differs",
       font=font(20, bold=True), fill=(240, 240, 242))
d.text((pad, 48), "No crops, zooms, pixel sampling, scripts or diffs in either cell.",
       font=font(12), fill=(140, 142, 150))
y = 76
for slug, label in REFS:
    d.text((pad, y), label, font=font(14, bold=True), fill=(150, 152, 165))
    y += 26
    for i, c in enumerate(cols):
        if (slug, c) not in scaled: continue
        x = pad + i * (DISP_W + gap)
        im = scaled[(slug, c)]
        canvas.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(58, 60, 68))
        cap = labels[c]
        r = res.get((slug, c))
        if r and c != "ref":
            cap += f"   SSIM {r['ssim']:.3f} · RMSE {r['rmse']:.3f} · score {r['score']:.1f}"
        d.text((x, y + im.height + 8), cap, font=font(12), fill=(170, 172, 182))
    y += row_h[slug] + gap
canvas.save(ROOT / "clean_pair.png")
print("saved", ROOT / "clean_pair.png", canvas.size)
