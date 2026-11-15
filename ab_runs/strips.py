#!/usr/bin/env python3
"""Per-reference output strips: REFERENCE | A | B | C with measured SSIM."""
import json, pathlib
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "strips"
OUT.mkdir(exist_ok=True)
REFS = [("ref1-collage", "ref1 · KODOR collage", "1520×794"),
        ("ref2-knob", "ref2 · knob / keycap", "438×393"),
        ("ref3-bp", "ref3 · BP widget", "394×210"),
        ("ref4-flight", "ref4 · flight card", "400×155")]
COLS = [("ref", "REFERENCE"), ("A", "A · vision only"),
        ("B", "B · vision + facts"), ("C", "C · eyes loop")]
res = {(r["ref"], r["arm"]): r for r in json.loads((ROOT / "results.json").read_text())["rows"]}

def font(sz, bold=False):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
              else "/System/Library/Fonts/Supplemental/Arial.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()

DISP_W, pad, gap, head_h, lab_h = 360, 24, 12, 58, 44
for slug, name, dims in REFS:
    scaled = {}
    for arm, _ in COLS:
        p = ROOT / "A" / slug / "reference.png" if arm == "ref" else ROOT / arm / slug / "candidate.png"
        im = Image.open(p).convert("RGB")
        s = DISP_W / im.width
        scaled[arm] = im.resize((DISP_W, round(im.height * s)), Image.LANCZOS)
    row_h = max(im.height for im in scaled.values())
    W = pad * 2 + len(COLS) * DISP_W + (len(COLS) - 1) * gap
    H = pad + head_h + row_h + lab_h + pad
    canvas = Image.new("RGB", (W, H), (16, 17, 20))
    d = ImageDraw.Draw(canvas)
    d.text((pad, 18), f"{name}  ({dims})", font=font(19, bold=True), fill=(240, 242, 245))
    metrics = "   ".join(f"{a} {res[(slug, a)]['ssim']:.3f}" for a in ["A", "B", "C"])
    d.text((pad, 42), f"SSIM  {metrics}", font=font(12), fill=(150, 154, 165))
    y = pad + head_h
    for i, (arm, label) in enumerate(COLS):
        x = pad + i * (DISP_W + gap)
        im = scaled[arm]
        canvas.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline=(58, 60, 68))
        cap = label
        if arm != "ref":
            cap += f"   {res[(slug, arm)]['ssim']:.3f}"
        d.text((x, y + im.height + 8), cap, font=font(12), fill=(180, 183, 194))
    canvas.save(OUT / f"{slug}.png")
    print("saved", OUT / f"{slug}.png", canvas.size)
