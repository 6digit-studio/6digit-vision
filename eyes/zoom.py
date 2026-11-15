"""zoom — crop + magnify a region for re-perception.

The tightening stage of the coarse-to-fine loop: pixdiff/region_map
localize WHERE diff mass concentrates; zoom crops that patch (with
padding), upscales it, and re-runs perception at higher effective
resolution — recovering OCR/detections that were sub-threshold at full
frame. Renderer-agnostic: operates on pixels, so it works identically
on HTML renders and GPU framebuffers.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def crop_zoom(image, bbox, scale: int = 3, pad_frac: float = 0.12):
    """Crop bbox (+padding) and upscale. Returns (PIL image, pixel bbox used).

    `image` is a path or PIL image; `bbox` is x,y,w,h in source pixels.
    """
    img = Image.open(str(image)).convert("RGB") if isinstance(image, (str, Path)) else image.convert("RGB")
    W, H = img.size
    x, y, w, h = bbox
    px, py = int(w * pad_frac), int(h * pad_frac)
    x0, y0 = max(0, int(x) - px), max(0, int(y) - py)
    x1, y1 = min(W, int(x + w) + px), min(H, int(y + h) + py)
    crop = img.crop((x0, y0, x1, y1))
    crop = crop.resize((crop.width * scale, crop.height * scale), Image.LANCZOS)
    return crop, (x0, y0, x1 - x0, y1 - y0)


def save_zoom(image, bbox, out, scale: int = 3, pad_frac: float = 0.12):
    crop, used = crop_zoom(image, bbox, scale=scale, pad_frac=pad_frac)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    crop.save(out)
    return crop, used
