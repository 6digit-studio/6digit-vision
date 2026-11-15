#!/usr/bin/env python3
"""gallery_cover.png — readable 2-reference cover for the main gallery page."""
import json, pathlib
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
REFS = [("ref1-collage", "1 · KODOR collage"),
        ("ref4-flight", "4 · flight card")]
COLS = [("ref", "REFERENCE"), ("A", "A · vision only"),
        ("B", "B · vision + facts"), ("C", "C · eyes loop")]
res = {(r["ref"], r["arm"]): r for r in json.loads((ROOT / "results.json").read_text())["rows"]}

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

DISP_W, pad, gap, lab_h = 420, 24, 16, 48
scaled = {}
for slug, _ in REFS:
    for arm, _ in COLS:
        p = ROOT / "A" / slug / "reference.png" if arm == "ref" else ROOT / arm / slug / "candidate.png"
        im = Image.open(p).convert("RGB")
        s = DISP_W / im.width
        scaled[(slug, arm)] = im.resize((DISP_W, round(im.height * s)), Image.LANCZOS)
row_h = {s: max(scaled[(s, a)].height for a, _ in COLS) + lab_h for s, _ in REFS}
W = pad * 2 + len(COLS) * DISP_W + (len(COLS) - 1) * gap
H = pad * 2 + 64 + sum(row_h.values()) + gap * (len(REFS) - 1)
canvas = Image.new("RGB", (W, H), (16, 17, 20))
d = ImageDraw.Draw(canvas)
d.text((pad, 20), "Does eyes add anything?  A/B/C on screenshot→HTML", font=font(24, bold=True), fill=(240, 242, 245))
d.text((pad, 52), "mean SSIM 0.684 (A) → 0.890 (B) → 0.888 (C)   ·   facts-only pair: no measurable gain",
       font=font(13), fill=(150, 154, 165))
y = 80
for slug, label in REFS:
    d.text((pad, y), label, font=font(16, bold=True), fill=(165, 168, 180))
    y += 28
    for i, (arm, cap) in enumerate(COLS):
        x = pad + i * (DISP_W + gap)
        im = scaled[(slug, arm)]
        canvas.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(58, 60, 68))
        sub = cap
        if arm != "ref":
            r = res.get((slug, arm))
            sub += f"   SSIM {r['ssim']:.3f}"
        d.text((x, y + im.height + 8), sub, font=font(13), fill=(180, 183, 194))
    y += row_h[slug] + gap
canvas.save(ROOT / "gallery_cover.png")
print("saved", ROOT / "gallery_cover.png", canvas.size)
