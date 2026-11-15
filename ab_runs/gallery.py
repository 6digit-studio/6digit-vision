#!/usr/bin/env python3
"""Build gallery.png: reference vs each arm, per reference, with metrics."""
import json, pathlib, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
REFS = [("ref1-collage", "1 · KODOR collage  (1520×794)"),
        ("ref2-knob",    "2 · knob / keycap  (438×393)"),
        ("ref3-bp",      "3 · BP widget      (394×210)"),
        ("ref4-flight",  "4 · flight card    (400×155)")]
ARMS = [a for a in ["A", "B", "C", "D"] if (ROOT / a).exists()]
res = {}
rp = ROOT / "results.json"
if rp.exists():
    for r in json.loads(rp.read_text())["rows"]:
        res[(r["ref"], r["arm"])] = r

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()

DISP_W, pad, gap, lab_h = 560, 22, 14, 40
scaled = {}
for slug, _ in REFS:
    for arm in ["ref"] + ARMS:
        p = (ROOT / "A" / slug / "reference.png") if arm == "ref" \
            else (ROOT / arm / slug / "candidate.png")
        if p.exists():
            im = Image.open(p).convert("RGB")
            s = DISP_W / im.width
            scaled[(slug, arm)] = im.resize((DISP_W, max(1, round(im.height * s))),
                                            Image.LANCZOS)

row_h = {slug: max(scaled[(slug, a)].height for a in ["ref"] + ARMS
                   if (slug, a) in scaled) + lab_h for slug, _ in REFS}
cols = 1 + len(ARMS)
W = pad * 2 + cols * DISP_W + (cols - 1) * gap
H = pad * 2 + 56 + sum(row_h.values()) + gap * (len(REFS) - 1)
canvas = Image.new("RGB", (W, H), (16, 17, 20))
d = ImageDraw.Draw(canvas)
d.text((pad, 20), "eyes A/B — reference vs vision-only (A) vs vision+facts (B)"
       + ("  vs measurement-loop (C)" if "C" in ARMS else ""),
       font=font(21, bold=True), fill=(240, 240, 242))
d.text((pad, 48), "SSIM ↑ / mismatch ↓ are pixel metrics; score is semantic, normalized against the reference's self-ceiling.",
       font=font(12), fill=(140, 142, 150))
y = 74
for slug, label in REFS:
    d.text((pad, y), label, font=font(14, bold=True), fill=(150, 152, 165))
    y += 26
    for i, arm in enumerate(["ref"] + ARMS):
        if (slug, arm) not in scaled:
            continue
        x = pad + i * (DISP_W + gap)
        im = scaled[(slug, arm)]
        canvas.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(58, 60, 68))
        if arm == "ref":
            cap, col = "REFERENCE", (170, 172, 182)
        else:
            r = res.get((slug, arm))
            if r:
                cap = f"ARM {arm}   SSIM {r['ssim']:.3f} · score {r['score']:.1f}/{r['ceiling']:.1f}"
                col = (120, 220, 180) if r["ssim"] >= 0.7 else (220, 200, 120)
            else:
                cap, col = f"ARM {arm}", (170, 172, 182)
        d.text((x, y + im.height + 7), cap, font=font(12), fill=col)
    y += row_h[slug] + gap
out = ROOT / "gallery.png"
canvas.save(out)
print("saved", out, canvas.size)
