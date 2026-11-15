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


def grid_stats(image, cols: int = 16) -> list[list[dict]]:
    """Sample the image on a uniform cols x rows grid.

    Each cell reports mean RGB, the dominant 5-bit-quantized color, and
    per-channel stddev — stddev is the texture signal: flat UI chrome
    scores ~0, photographic/gradient content scores high. This is the
    spatial complement to palette(): where palette() says WHAT colors
    dominate globally, grid_stats() says WHERE they live.
    """
    img = _open(image)
    w, h = img.size
    rows = max(1, round(cols * h / w / 2))  # ~2:1 cells, terminal-friendly
    cw, ch = w / cols, h / rows
    cells = []
    for ry in range(rows):
        row = []
        for rx in range(cols):
            box = (
                round(rx * cw), round(ry * ch),
                round((rx + 1) * cw), round((ry + 1) * ch),
            )
            crop = img.crop(box)
            px = list(crop.getdata())
            n = len(px)
            if not n:
                row.append({"hex": "#000000", "mean": [0, 0, 0], "std": 0.0})
                continue
            means = [sum(p[c] for p in px) / n for c in range(3)]
            var = sum(
                sum((p[c] - means[c]) ** 2 for p in px) / n for c in range(3)
            ) / 3
            counts: dict[tuple[int, int, int], int] = {}
            for p in px:
                key = tuple(((v >> 3) << 3) | 4 for v in p)
                counts[key] = counts.get(key, 0) + 1
            dom = max(counts.items(), key=lambda kv: kv[1])[0]
            row.append({
                "hex": "#%02x%02x%02x" % dom,
                "mean": [round(m) for m in means],
                "std": round(var ** 0.5, 1),
            })
        cells.append(row)
    return cells


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
