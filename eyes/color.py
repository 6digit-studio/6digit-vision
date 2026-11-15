"""Quantitative color layer: palette histograms and per-object stats.

Mirage reports high-level color names ("red", "blue"); this module adds
the measurable layer — dominant palette and mean RGB per detected object
bbox — using coordinates mapped back from Mirage's [0,1000] space.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

CANVAS = 1000.0  # Mirage normalizes each axis to [0, CANVAS]


def _open(image) -> Image.Image:
    if isinstance(image, (str, Path)):
        return Image.open(image).convert("RGB")
    return image.convert("RGB") if hasattr(image, "convert") else image


def denorm(bbox: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    """Map a Mirage [0,1000]-normalized bbox to pixel (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = bbox
    return (
        round(x0 / CANVAS * width),
        round(y0 / CANVAS * height),
        round(x1 / CANVAS * width),
        round(y1 / CANVAS * height),
    )


def palette(image, n: int = 8) -> list[dict]:
    """Top-n dominant colors as hex + fraction of pixels.

    Colors are binned to 5 bits/channel (32 levels) — coarse enough to
    group perceptually-similar shades, fine enough to separate hues.
    """
    img = _open(image)
    scale = min(1.0, 256 / img.width)
    small = img.resize((round(img.width * scale), round(img.height * scale)))
    counts: dict[tuple[int, int, int], int] = {}
    for r, g, b in small.getdata():
        key = ((r >> 3) << 3) | 4, ((g >> 3) << 3) | 4, ((b >> 3) << 3) | 4
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:n]
    return [
        {
            "hex": "#%02x%02x%02x" % k,
            "frac": round(v / total, 4),
        }
        for k, v in top
    ]


def mean_rgb(image, bbox_norm: list[float]) -> list[int] | None:
    """Mean RGB inside a Mirage-normalized bbox."""
    img = _open(image)
    x0, y0, x1, y1 = denorm(bbox_norm, img.width, img.height)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = img.crop((x0, y0, x1, y1))
    px = list(crop.getdata())
    if not px:
        return None
    n = len(px)
    return [sum(p[0] for p in px) // n, sum(p[1] for p in px) // n, sum(p[2] for p in px) // n]


def object_color_stats(image, record: dict) -> list[dict]:
    """Attach measured mean RGB to each object in a compact record."""
    img = _open(image)
    out = []
    for obj in record.get("objects", []):
        entry = {
            "id": obj.get("id"),
            "name": obj.get("name"),
            "position": obj.get("position"),
        }
        rgb = mean_rgb(img, obj["bbox"]) if "bbox" in obj else None
        if rgb is not None:
            entry["mean_rgb"] = rgb
            entry["mean_hex"] = "#%02x%02x%02x" % tuple(rgb)
        out.append(entry)
    return out
