#!/usr/bin/env python3
"""nonuniform-scale — horizontally inflated raster content.

web-canvas MISS fix: CSS transform:scaleX(1.35) on a canvas chart was
invisible to every detector (anisotropy needs >=5 text lines; canvas
has 1). The witness that survives few-witness images: TEXT-LIKE row
bands — short bands (6-20px) with >=4 column-runs each narrower than
the band is tall. Per band: median(segment_width)/band_height = glyph
w/h. Isotropic sans text sits ~0.5-0.75; horizontal stretch inflates
it toward 1.0 (measured: control 0.72, defect 1.00 at scaleX 1.35 —
the inflation factor shows up almost exactly).

Honest scope: candidate-level signal — one band is thin evidence;
requires the band to have >=4 segments (a real text line, not a rule).
Model-free, numpy+PIL only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LUM_T = 0.62          # ink threshold (mid-gray and darker)
BAND_H_MIN = 6        # px; text cap-height+descender-ish
BAND_H_MAX = 20       # taller bands are panels/rules, not text lines
MIN_SEGMENTS = 4      # a real text line has several glyph runs
MAX_SEG_ASPECT = 2.5  # segment wider than 2.5x band height = bar/rule
W_OVER_H_FLAG = 0.85  # measured gap: isotropic ~0.72, 1.35x-stretch ~1.00


def _text_band_stats(ink: np.ndarray, y0: int, y1: int) -> float | None:
    band = ink[y0:y1]
    bh = y1 - y0
    colsum = band.sum(axis=0)
    xs = np.nonzero(colsum > 0)[0]
    if xs.size < MIN_SEGMENTS:
        return None
    segs, s, prev = [], xs[0], xs[0]
    for x in xs[1:]:
        if x == prev + 1:
            prev = x
        else:
            segs.append((s, prev))
            s = prev = x
    segs.append((s, prev))
    widths = [b - a + 1 for a, b in segs
              if 1 <= b - a + 1 <= MAX_SEG_ASPECT * bh]
    if len(widths) < MIN_SEGMENTS:
        return None
    return float(np.median(widths)) / bh


def census(path: str | Path) -> dict:
    px = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    lum = (0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2]) / 255.0
    h, w = lum.shape
    ink = lum < LUM_T

    rowsum = ink.sum(axis=1).astype(np.float64)
    k = 3
    smooth = np.convolve(rowsum, np.ones(k) / k, mode="same")
    thr = max(3.0, 0.004 * w)
    hit = smooth >= thr

    bands, y = [], 0
    while y < h:
        if not hit[y]:
            y += 1
            continue
        y0 = y
        gap = 0
        y += 1
        while y < h:
            if hit[y]:
                gap = 0
                y += 1
            else:
                gap += 1
                if gap > 2:
                    break
                y += 1
        bands.append((y0, y - gap))

    stats = []
    for y0, y1 in bands:
        bh = y1 - y0
        if not (BAND_H_MIN <= bh <= BAND_H_MAX):
            continue
        r = _text_band_stats(ink, y0, y1)
        if r is not None:
            stats.append({"y": [y0, y1], "band_h": bh,
                          "median_glyph_w_over_h": round(r, 3)})

    meds = [s["median_glyph_w_over_h"] for s in stats]
    pop = float(np.median(meds)) if meds else None
    result = {
        "image": str(path), "size": [w, h],
        "text_bands": stats[:20], "n_bands": len(stats),
        "population_median_w_over_h": round(pop, 3) if pop else None,
        "verdict": None, "notes": [],
    }
    if pop is None:
        result["verdict"] = "insufficient_witnesses"
        result["notes"].append("no qualifying text bands")
    elif pop > W_OVER_H_FLAG:
        result["verdict"] = "scale_suspect"
        result["notes"].append(
            f"glyph w/h median {pop} > {W_OVER_H_FLAG} — horizontally "
            "inflated raster (non-uniform scale candidate)")
    else:
        result["verdict"] = "isotropic"
        result["notes"].append(f"glyph w/h median {pop} within band")
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
            print(f"{r.get('verdict', '?'):<22} {r['image']}")
            for n in r.get("notes", []):
                print(f"    {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
