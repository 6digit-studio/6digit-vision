#!/usr/bin/env python3
"""pixel_edges.py — pixel-side leading-edge census (experimental second
channel for detectors/edge-census).

Motivation (evals/grid-misalign/VERDICT.md, suggestion #2): the
record-based census needs repeated TEXT to group; icon-only UIs have
none. This channel needs no OCR and no VLM — it finds the defect in
raw pixels:

  1. Estimate the page background from the image border; content mask =
     pixels differing from it.
  2. Row projection -> contiguous row bands (cards, header strip,
     toolbar rows).
  3. Per band, the dominant color is the local surface (card white,
     strip gray); ink mask = pixels differing from it. Column
     projection -> x-intervals = element columns within that band.
  4. Cluster every interval across all bands by left edge
     (single-linkage, gap <= XCLUSTER px). Each cluster is one vertical
     stack of same-column elements.
  5. For clusters spanning >= MIN_BANDS bands, measure left-edge,
     right-edge, center and width spreads. Keep only UNIFORM-WIDTH
     clusters (width_spread <= WIDTH_MAX): variable-width x-columns are
     prose, whose ragged edges are legitimate — this guard is what
     separates repeated elements from text lines.
  6. Flag when the ANCHORED edge moved: min(left_spread, right_spread)
     > FLOOR_PX AND center_spread > FLOOR_PX. The min() rejects
     legitimate raggedness — left-anchored columns have ragged right
     edges by design (variable text length), right-anchored the
     reverse, centered-in-slot ragged both edges but a stable center.
     Only a real translation moves the anchored edge AND the center.

Calibration (measured): control.png max anchored spread = 1px;
defect.png carries the planted 6-9px drifts (eval's own pixel table:
avatar_L 8, pill_R 8, dots_L 7 — this census reproduces them as
anchored spreads 8/9/7). FLOOR_PX defaults to 3.

False-positive sweep (all evals/*/control.png + defect.png, 20 images):
before the width guard this fired on 9 of 10 non-grid scenes (prose
columns are legitimately ragged); after it, CLEAN on every non-grid
eval and on synth_ragged.png. It still cannot see vertical drift
smaller than a band, and elements closer than XCLUSTER px merge.
Complement to edge_census.py, not a replacement.

Usage (from repo root):
    uv run python detectors/edge-census/pixel_edges.py evals/grid-misalign/defect.png
    uv run python detectors/edge-census/pixel_edges.py img.png --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# ---- calibrated defaults ----
BG_DIST = 30      # per-channel-ish distance from page bg to count as content
SURF_DIST = 30    # distance from band-dominant color to count as ink
MIN_BAND_H = 8    # px; shorter bands are noise/antialiasing slivers
MIN_COL_INK = 3   # px of ink in a column to count toward an interval
MERGE_GAP = 8     # px; closer x-intervals within a band are one element
XCLUSTER = 12     # px; linkage gap for clustering intervals across bands
MIN_BANDS = 3     # clusters must span at least this many row bands
FLOOR_PX = 3.0    # flag threshold on anchored-edge and center spread
EDGE_MARGIN = 0.01  # fraction of width; intervals this close to the
                    # frame edge are browser chrome (scrollbar, margin),
                    # not drifting layout — real-corpus FP fix
WIDTH_MAX = 25.0  # px; max interval-width spread — rejects prose columns.
                 # Measured: pill/avatar/dots columns <= ~15px; every
                 # false positive on non-grid evals had width spread
                 # >= 44px (variable-length text lines).


def color_dist(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Max abs per-channel distance broadcast over leading dims."""
    return np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=-1)


def estimate_bg(img: np.ndarray) -> np.ndarray:
    """Median color of the outer 12px frame — the page background."""
    h, w = img.shape[:2]
    b = 12
    frame = np.concatenate([
        img[:b].reshape(-1, 3), img[-b:].reshape(-1, 3),
        img[:, :b].reshape(-1, 3), img[:, -b:].reshape(-1, 3)])
    return np.median(frame, axis=0)


def runs(mask: np.ndarray, min_len: int = 1) -> list[tuple[int, int]]:
    """Contiguous True runs in a 1-D bool array -> (start, end) inclusive."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            if j - i + 1 >= min_len:
                out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def row_bands(content: np.ndarray) -> list[tuple[int, int]]:
    counts = content.sum(axis=1)
    # a band row needs a real column of content, not specks
    active = counts > max(4, content.shape[1] * 0.002)
    return runs(active, MIN_BAND_H)


def band_intervals(bw: np.ndarray) -> list[tuple[int, int]]:
    """x-intervals of ink inside one row band (bw = band ink mask)."""
    counts = bw.sum(axis=0)
    active = counts >= MIN_COL_INK
    raw = runs(active)
    # merge intervals separated by < MERGE_GAP px of non-ink
    merged: list[list[int]] = []
    for s, e in raw:
        if merged and s - merged[-1][1] - 1 < MERGE_GAP:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def census(img: np.ndarray, floor_px: float = FLOOR_PX,
           width_max: float = WIDTH_MAX) -> dict:
    h, w = img.shape[:2]
    bg = estimate_bg(img)
    content = color_dist(img, bg) > BG_DIST

    bands = row_bands(content)
    intervals: list[dict] = []  # {band, x0, x1}
    for bi, (y0, y1) in enumerate(bands):
        band = img[y0:y1 + 1]
        # local surface = median color of the band (card white / strip gray)
        surf = np.median(band.reshape(-1, 3), axis=0)
        ink = color_dist(band, surf) > SURF_DIST
        for x0, x1 in band_intervals(ink):
            intervals.append({"band": bi, "y": (y0, y1),
                              "x0": x0, "x1": x1})

    edge_px = max(8, int(w * EDGE_MARGIN))
    intervals = [it for it in intervals
                 if it["x0"] > edge_px and it["x1"] < w - edge_px]

    # cluster intervals across bands by left edge
    xs = sorted(intervals, key=lambda it: it["x0"])
    clusters: list[list[dict]] = []
    for it in xs:
        if clusters and it["x0"] - clusters[-1][-1]["x0"] <= XCLUSTER:
            clusters[-1].append(it)
        else:
            clusters.append([it])

    audit, findings = [], []
    for cl in clusters:
        band_ids = {c["band"] for c in cl}
        if len(band_ids) < MIN_BANDS:
            continue
        x0s = [c["x0"] for c in cl]
        x1s = [c["x1"] for c in cl]
        cxs = [(c["x0"] + c["x1"]) / 2 for c in cl]
        widths = [c["x1"] - c["x0"] for c in cl]
        wsp = max(widths) - min(widths)
        lsp, rsp = max(x0s) - min(x0s), max(x1s) - min(x1s)
        csp = max(cxs) - min(cxs)
        anchored = min(lsp, rsp)
        entry = {
            "n_bands": len(band_ids), "n_intervals": len(cl),
            "x0_range": [min(x0s), max(x0s)],
            "x1_range": [min(x1s), max(x1s)],
            "width_spread": wsp,
            "left_spread": lsp, "right_spread": rsp,
            "center_spread": csp, "anchored_spread": anchored,
            "bands": sorted(band_ids),
        }
        audit.append(entry)
        # uniform-size elements only: variable-width columns are prose,
        # not repeated elements — their ragged edges are legitimate
        if wsp > width_max:
            entry["skipped"] = "variable_width"
            continue
        if anchored > floor_px and csp > floor_px:
            findings.append({**entry, "kind": "edge_drift",
                             "floor_px": floor_px})

    findings.sort(key=lambda f: -f["anchored_spread"])
    return {
        "image_size": [w, h],
        "bg": [round(float(c), 1) for c in bg],
        "bands": [{"y": list(b), "h": b[1] - b[0] + 1} for b in bands],
        "intervals": len(intervals),
        "params": {"bg_dist": BG_DIST, "surf_dist": SURF_DIST,
                   "min_band_h": MIN_BAND_H, "min_col_ink": MIN_COL_INK,
                   "merge_gap": MERGE_GAP, "xcluster": XCLUSTER,
                   "width_max": width_max,
                   "min_bands": MIN_BANDS, "floor_px": floor_px},
        "audit": audit,
        "findings": findings,
        "verdict": "FLAGGED" if findings else "CLEAN",
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Pixel-side leading-edge census (no OCR/VLM).")
    p.add_argument("image")
    p.add_argument("--json", action="store_true")
    p.add_argument("--floor-px", type=float, default=FLOOR_PX)
    p.add_argument("--width-max", type=float, default=WIDTH_MAX,
                   help="max interval-width spread for a cluster to count "
                        "as repeated elements (default %(default)s px)")
    args = p.parse_args()

    img = np.asarray(Image.open(args.image).convert("RGB"))
    result = census(img, floor_px=args.floor_px,
                    width_max=args.width_max)
    result["input"] = args.image

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    w, h = result["image_size"]
    print(f"pixel-edges: {args.image}  {w}x{h}")
    print(f"  bg={[round(float(c)) for c in result['bg']]}  "
          f"row bands: {len(result['bands'])}  "
          f"intervals: {result['intervals']}")
    print("  bands (y-ranges): " +
          " ".join(f"{b['y'][0]}-{b['y'][1]}" for b in result["bands"]))
    for f in result["findings"]:
        print(f"  FINDING edge_drift: x0[{f['x0_range'][0]}.."
              f"{f['x0_range'][1]}] n_bands={f['n_bands']} "
              f"left {f['left_spread']:.0f}px right "
              f"{f['right_spread']:.0f}px center {f['center_spread']:.0f}px "
              f"-> anchored {f['anchored_spread']:.0f}px "
              f"(floor {args.floor_px}px)")
    skipped = [a for a in result["audit"] if a.get("skipped")]
    for a in skipped:
        print(f"  skipped x0[{a['x0_range'][0]}..{a['x0_range'][1]}] "
              f"n={a['n_bands']}: {a['skipped']} "
              f"(anchored {a['anchored_spread']:.0f}px, "
              f"width_spread {a['width_spread']:.0f}px)")
    if not result["findings"]:
        near = sorted((a for a in result["audit"] if not a.get("skipped")),
                      key=lambda a: -a["anchored_spread"])[:5]
        for a in near:
            print(f"  max anchored spread: x0[{a['x0_range'][0]}.."
                  f"{a['x0_range'][1]}] n={a['n_bands']} "
                  f"{a['anchored_spread']:.0f}px "
                  f"(L{a['left_spread']:.0f} R{a['right_spread']:.0f} "
                  f"C{a['center_spread']:.0f})")
    print(f"  VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
