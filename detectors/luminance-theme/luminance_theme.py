#!/usr/bin/env python3
"""luminance-theme — light elements on a dark theme (or vice versa).

hue_census measures accent-color drift; this measures LUMINANCE drift:
a page whose background is dark but which contains coherent near-white
regions (or light bg with dark islands) has mixed theme tokens.

Mechanism: estimate page background luminance (border median), then
measure the fraction of pixels on the OPPOSITE luminance extreme that
form spatially-coherent clusters (row-band coverage). A theme split
needs both mass AND coherence — scattered highlights (text on dark)
don't count; card-sized white regions do.

Spec: defect+control verified on evals/web-theme-drift (real Chrome
render). Model-free, numpy+PIL only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MIN_ISLAND_FRAC = 0.015   # opposite-extreme pixels must be >=1.5% of frame
MIN_BAND_COVER = 0.25     # and span >=25% of a row band to be coherent
LUM_SPLIT = 0.45          # |lum - bg_lum| beyond this counts as opposite


def census(path: str | Path) -> dict:
    img = Image.open(path).convert("RGB")
    px = np.asarray(img, dtype=np.float32)
    h, w = px.shape[:2]
    lum = (0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2]) / 255.0

    border = np.concatenate([lum[0, :], lum[-1, :], lum[:, 0], lum[:, -1]])
    bg_lum = float(np.median(border))
    dark_bg = bg_lum < 0.35

    # opposite extreme: near-white islands on dark bg, or near-black on light
    if dark_bg:
        island = lum > (1.0 - LUM_SPLIT)
    else:
        island = lum < LUM_SPLIT
    frac = float(island.mean())

    # coherence: row bands where island pixels span >= MIN_BAND_COVER width
    row_has = island.sum(axis=1)
    bands = []
    y = 0
    while y < h:
        if row_has[y] < w * MIN_BAND_COVER:
            y += 1
            continue
        y0 = y
        while y < h and row_has[y] >= w * MIN_BAND_COVER:
            y += 1
        bands.append((y0, y))

    result = {
        "image": str(path), "size": [w, h],
        "bg_luminance": round(bg_lum, 3),
        "theme": "dark" if dark_bg else "light",
        "island_frac": round(frac, 4),
        "coherent_bands": len(bands),
        "band_rows": sum(b - a for a, b in bands),
        "verdict": None,
        "notes": [],
    }
    coherent = frac >= MIN_ISLAND_FRAC and result["band_rows"] >= h * 0.05
    if coherent:
        result["verdict"] = "luminance_theme_split"
        result["notes"].append(
            f"{frac * 100:.1f}% opposite-luminance pixels in "
            f"{result['band_rows']} coherent rows on {result['theme']} theme")
    else:
        result["verdict"] = "single_luminance_theme"
        result["notes"].append(
            f"island frac {frac * 100:.1f}% / coherent rows "
            f"{result['band_rows']} below floors")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = []
    for p in args.images:
        try:
            results.append(census(p))
        except Exception as e:
            results.append({"image": str(p), "verdict": "error",
                            "notes": [str(e)]})
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r.get('verdict', '?'):<24} {r['image']}")
            for n in r.get("notes", []):
                print(f"    {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
