# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "scipy"]
# ///
"""anisotropy-census — single-image detector for non-uniform resize squash.

Fills the gap named in evals/aspect-abuse/VERDICT.md: a 16:9 dashboard
force-fit into 1000x1000 via `img.resize((1000,1000))` / `object-fit:
fill` turns every designed circle into a ~1.78:1 ellipse and every glyph
into a ~0.30 w/h sliver — and `eyes` erases aspect at the record layer
(per-axis [0,1000] normalization) while `score` cannot attribute the
signal (the correct letterboxed variant scored LOWER than the defect).

Two model-free measurement channels, both computed from raw pixels:

  A. solid-blob aspect census — mask pixels far from the two dominant
     light surfaces (page bg + card), keep only components with a thick
     core (survive 2x Chebyshev erosion — kills 1-3px strokes: text,
     chart polylines, hairlines), cluster the survivors' bbox aspects.
     UI circles/chips/dots/avatar are drawn circular by convention, so
     an isotropic render clusters at aspect ~1.0; a non-uniform resize
     drags the whole cluster to k = sy/sx. Fires when the dominant
     tight cluster's |median log(aspect)| > LOG_ASPECT_MIN.

  B. glyph-proportion census — luminance-ink mask, row-projection text
     bands, column-projection glyph segmentation per band, median
     glyph-width / band-ink-height per line, population median across
     lines. Latin glyphs sit ~0.45-0.6 w/h; the eval defect measured
     0.303 vs control 0.545 on the same string. Fires outside
     [W_OVER_H_MIN, W_OVER_H_MAX].

The channels are independent witnesses: blob aspect assumes "drawn
round" (true aspect 1.0), glyph aspect assumes "Latin-ish" (true w/h
~0.5). Agreement is strong evidence of anisotropic scale; disagreement
is reported, not averaged away.

Usage (from repo root):
    uv run detectors/anisotropy-census/anisotropy_census.py IMAGE [IMAGE ...]
    uv run detectors/anisotropy-census/anisotropy_census.py --json defect.png
    uv run detectors/anisotropy-census/anisotropy_census.py --fail-on-anisotropy *.png

Exit is 0 unless --fail-on-anisotropy and any image verdict is
anisotropic_squash / shape_cluster_anomalous / glyph_anisotropy.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

# ------------------------------------------------------------------ tunables

SURFACE_DIST_INNER = 12.0   # px must be this far from page bg to be a
                            # candidate second surface (white card sits
                            # only ~24 from a light-gray page bg!)
INK_DIST = 22.0             # px must be this far from BOTH surfaces to be "ink"
MAX_CORE_FILL = 0.85        # cluster membership ceiling: filled rects
                            # (cards/buttons/pills, fill->0.9+) are not
                            # "drawn-round" witnesses; ellipses sit ~0.55-0.78
ERODE_ITERS = 2             # Chebyshev erosions; kills strokes <= ~4px thick
MIN_CORE_AREA = 8           # eroded core must have at least this many px
MIN_CORE_DIM = 3            # ...and this bbox min-dim (px, in core space)
CORE_FILL_MIN = 0.45        # core_area / core_bbox_area — rejects stroke fragments
MAX_DIM_FRAC = 0.45         # expanded blob max-dim <= this * min(W,H)
MIN_EXPANDED_DIM = 6        # expanded blob min-dim floor (px)
CLUSTER_HALF_WIDTH = 0.12   # log-aspect cluster half-width (~ +/-12%)
CLUSTER_REFINE = 0.08       # second-pass half-width around window median
MIN_CLUSTER_MEMBERS = 4     # unanimity requirement — the eval saw ~20;
                            # erosion costs the smallest dots, so 4 solid
                            # agreeing shapes is the honest floor
MIN_CLUSTER_AREA = 2000     # ...or >=3 members covering this many px
                            # (three large agreeing ellipses beat five
                            # coincidental 8px fragments)
MAX_CLUSTER_SPREAD = 0.30   # refined members must span <= this in log
LOG_ASPECT_MIN = 0.15       # |median log(aspect)| above this = anisotropic

LUM_T = 200.0               # luminance below this = "ink" for glyph channel
ROW_SMOOTH = 3              # boxcar width on row projection
ROW_THR_MIN = 4             # min ink px per row to count as text-row
ROW_THR_FRAC = 0.004        # ...or this fraction of image width, whichever larger
BAND_MERGE_GAP = 2          # merge row-bands separated by <= this many px
BAND_MIN_H = 4              # min band height (px) to be a text line
MIN_SEGMENTS_PER_LINE = 8   # fewer column-runs -> not a text line (dot rows!)
SEG_MIN_W = 2               # min glyph column-run width (px)
SEG_MAX_ASPECT = 1.8        # reject column-runs wider than this * band ink height
W_OVER_H_MIN = 0.35         # glyph channel flag band (eval sketch)
W_OVER_H_MAX = 0.75
MIN_TEXT_LINES = 5          # need this many qualifying lines to trust census
MAX_LINES_REPORTED = 40

STRUCT = np.ones((3, 3), dtype=bool)  # 8-connectivity Chebyshev structuring element


def color_dist(px: np.ndarray, c: np.ndarray) -> np.ndarray:
    return np.sqrt(((px - c) ** 2).sum(axis=-1))


def hexcolor(c: np.ndarray) -> str:
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


# ------------------------------------------------------------- channel A: blobs

def find_surfaces(px: np.ndarray):
    """Return (page_bg, card_surface) RGB colors.

    page_bg = per-channel median of the border ring (robust to a few
    stray pixels). card_surface = mode of the quantized colors among
    inner pixels far from page_bg — the dominant second surface
    (usually the white card). Falls back to page_bg when the image has
    effectively one surface.
    """
    h, w, _ = px.shape
    border = np.concatenate([
        px[0, :, :].reshape(-1, 3),
        px[-1, :, :].reshape(-1, 3),
        px[:, 0, :].reshape(-1, 3),
        px[:, -1, :].reshape(-1, 3),
    ])
    c1 = np.median(border, axis=0)
    d1 = color_dist(px, c1)
    # The second surface (usually the white card) can sit CLOSE to the
    # page bg in RGB distance — light-gray page + white card is ~24.
    # A 40 threshold silently drops the card and the mode then picks an
    # accent color (observed: c2=#2563eb blue, which unmasked every blue
    # dot/line). 12 keeps the card while still excluding bg +- noise.
    inner = px[d1 > SURFACE_DIST_INNER]
    c2 = c1.copy()
    if inner.shape[0] >= 256:
        q = (inner / 24.0).astype(np.int64)
        keys = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
        vals, counts = np.unique(keys, return_counts=True)
        mode_key = vals[counts.argmax()]
        mq = np.array([(mode_key // 4096) % 64,
                       (mode_key // 64) % 64,
                       mode_key % 64])
        members = inner[np.all(q == mq, axis=1)]
        if members.shape[0] >= 16:
            c2 = np.median(members, axis=0)
    return c1, c2


def blob_census(px: np.ndarray, w: int, h: int) -> dict:
    """Solid-blob aspect census via erosion-core connected components."""
    c1, c2 = find_surfaces(px)
    d1 = color_dist(px, c1)
    d2 = color_dist(px, c2)
    mask = (d1 > INK_DIST) & (d2 > INK_DIST)

    er = ndimage.binary_erosion(mask, structure=STRUCT,
                                iterations=ERODE_ITERS, border_value=0)
    labels, n = ndimage.label(er, structure=STRUCT)

    blobs = []
    if n:
        objs = ndimage.find_objects(labels)
        max_dim_cap = MAX_DIM_FRAC * min(w, h)
        for lid, sl in enumerate(objs, start=1):
            if sl is None:
                continue
            ys, xs = sl
            cw = xs.stop - xs.start
            ch = ys.stop - ys.start
            if cw < MIN_CORE_DIM or ch < MIN_CORE_DIM:
                continue
            core_area = int((labels[sl] == lid).sum())
            core_fill = core_area / float(cw * ch)
            if core_area < MIN_CORE_AREA or core_fill < CORE_FILL_MIN:
                continue
            # undo the Chebyshev erosion: original extent ~ core + 2px/side
            x0 = max(0, xs.start - ERODE_ITERS)
            y0 = max(0, ys.start - ERODE_ITERS)
            x1 = min(w - 1, xs.stop - 1 + ERODE_ITERS)
            y1 = min(h - 1, ys.stop - 1 + ERODE_ITERS)
            ew = x1 - x0 + 1
            eh = y1 - y0 + 1
            if min(ew, eh) < MIN_EXPANDED_DIM:
                continue
            if max(ew, eh) > max_dim_cap:
                continue
            blobs.append({
                "bbox": [int(x0), int(y0), int(x1), int(y1)],
                "w": int(ew), "h": int(eh),
                "aspect_h_over_w": round(eh / ew, 3),
                "log_aspect": round(math.log(eh / ew), 4),
                "core_area": core_area,
                "core_fill": round(core_fill, 3),
                # filled rects (fill -> ~0.9+) are designed rectangles,
                # not drawn-round witnesses — keep as candidates but
                # exclude from the aspect cluster
                "round_witness": bool(core_fill <= MAX_CORE_FILL),
            })

    out = {
        "surfaces": {"page_bg": hexcolor(c1), "card": hexcolor(c2)},
        "ink_px": int(mask.sum()),
        "cores": n,
        "candidates": len(blobs),
        "blobs": sorted(blobs, key=lambda b: -(b["w"] * b["h"]))[:MAX_LINES_REPORTED],
    }

    # ---- dominant tight cluster of log-aspects -------------------------
    # Cluster over round_witness blobs only: ellipses/dots/chips have
    # core_fill ~0.55-0.8; cards/buttons/pills approach 0.9+ and would
    # form spurious "unanimous" clusters of genuinely-wide designs
    # (observed: three identical 259x95 stat cards in state-a.png).
    witnesses = [b for b in blobs if b["round_witness"]]
    out["round_witnesses"] = len(witnesses)
    if len(witnesses) >= 3:
        la = np.array([b["log_aspect"] for b in witnesses])
        area = np.array([b["w"] * b["h"] for b in witnesses], dtype=np.float64)
        order = np.argsort(la)
        # window score = total member area, not member count: a tight
        # cluster of three large ellipses is stronger evidence than five
        # coincidental 8px glyph fragments at some other aspect
        best = None
        for i in range(len(la)):
            j = i
            while j < len(la) and la[order[j]] - la[order[i]] <= 2 * CLUSTER_HALF_WIDTH:
                j += 1
            cnt = j - i
            if cnt < 3:
                continue  # a lone blob is not a cluster — e.g. the share
                          # button's 161x37 rect must not win on area alone
            score = float(area[order[i:j]].sum())
            if best is None or score > best[0] or (
                    score == best[0] and cnt > best[1]):
                best = (score, cnt, i, j)
        if best is None:
            out["cluster"] = None
            out["cluster_members"] = []
            return out
        _, _, i, j = best
        # refine: re-center on the window median with a tighter band —
        # the dense core of true same-design shapes survives, scattered
        # witnesses (dots fused to chart lines, glyph fragments) drop out
        window_idx = order[i:j]
        med0 = float(np.median(la[window_idx]))
        final_idx = np.nonzero(np.abs(la - med0) <= CLUSTER_REFINE)[0]
        member_la = la[final_idx]
        med = float(np.median(member_la))
        spread = float(member_la.max() - member_la.min())
        member_area = float(area[final_idx].sum())
        enough = (len(final_idx) >= MIN_CLUSTER_MEMBERS
                  or (len(final_idx) >= 3
                      and member_area >= MIN_CLUSTER_AREA))
        cluster = {
            "members": int(len(final_idx)),
            "member_area_px": int(member_area),
            "share_of_witnesses": round(len(final_idx) / len(witnesses), 3),
            "median_log_aspect": round(med, 4),
            "median_aspect_h_over_w": round(math.exp(med), 3),
            "spread_log": round(spread, 4),
            "anomalous": bool(
                enough
                and spread <= MAX_CLUSTER_SPREAD
                and abs(med) > LOG_ASPECT_MIN),
        }
        out["cluster"] = cluster
        out["cluster_members"] = [witnesses[k] for k in final_idx]
    else:
        out["cluster"] = None
        out["cluster_members"] = []
        if blobs:
            out["notes"] = [f"only {len(witnesses)} round-witness blobs "
                            "(< 3); no unanimity witnesses — aspect "
                            "census unreliable"]
    return out


# ------------------------------------------------------------- channel B: glyphs

def glyph_census(px: np.ndarray, w: int, h: int) -> dict:
    """Per-line median glyph-width / band-ink-height, population median."""
    lum = (0.299 * px[..., 0] + 0.587 * px[..., 1] + 0.114 * px[..., 2])

    # dark-theme guard: the ink mask assumes dark-on-light. On a dark
    # canvas the background itself is "ink" and every band is garbage.
    border = np.concatenate([lum[0, :], lum[-1, :], lum[:, 0], lum[:, -1]])
    if float(np.median(border)) < 128.0:
        out = {"ink_px": 0, "lum_threshold": LUM_T, "lines": [],
               "n_lines": 0, "median_glyph_w_over_h": None,
               "population_median": None,
               "notes": ["dark background (border luminance <128); "
                         "glyph census assumes dark-on-light — skipped"]}
        return out

    ink = lum < LUM_T
    ink_px = int(ink.sum())

    out = {"ink_px": ink_px, "lum_threshold": LUM_T,
           "lines": [], "n_lines": 0, "median_glyph_w_over_h": None,
           "population_median": None}

    if ink_px < 500:
        out["notes"] = [f"only {ink_px} ink px (<500); glyph census "
                        "unreliable — dark-on-light text assumed"]
        return out

    rowsum = ink.sum(axis=1).astype(np.float64)
    # boxcar smooth
    k = ROW_SMOOTH
    kern = np.ones(k) / k
    smooth = np.convolve(rowsum, kern, mode="same")
    row_thr = max(ROW_THR_MIN, ROW_THR_FRAC * w)
    hit = smooth >= row_thr

    # contiguous bands, merge across <= BAND_MERGE_GAP dead rows
    bands = []
    y = 0
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
                if gap > BAND_MERGE_GAP:
                    break
                y += 1
        bands.append((y0, y - gap))

    lines = []
    for y0, y1 in bands:
        band = ink[y0:y1 + 1]
        ink_rows = np.nonzero(band.any(axis=1))[0]
        if ink_rows.size == 0:
            continue
        band_h = int(ink_rows.max() - ink_rows.min() + 1)
        if band_h < BAND_MIN_H:
            continue
        colsum = band.sum(axis=0)
        xs = np.nonzero(colsum > 0)[0]
        if xs.size == 0:
            continue
        # column-runs = glyph candidates
        segs = []
        s = xs[0]
        prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
            else:
                segs.append((s, prev))
                s = prev = x
        segs.append((s, prev))

        widths = []
        for a, b in segs:
            sw = b - a + 1
            if sw < SEG_MIN_W or sw > SEG_MAX_ASPECT * band_h:
                continue
            widths.append(sw / band_h)
        if len(widths) < MIN_SEGMENTS_PER_LINE:
            continue
        med = float(np.median(widths))
        lines.append({
            "y": [int(y0), int(y1)],
            "band_ink_h": band_h,
            "segments": len(widths),
            "median_glyph_w_over_h": round(med, 4),
        })

    out["n_lines"] = len(lines)
    out["lines"] = lines[:MAX_LINES_REPORTED]
    if len(lines) >= MIN_TEXT_LINES:
        meds = np.array([l["median_glyph_w_over_h"] for l in lines])
        pop = float(np.median(meds))
        out["population_median"] = round(pop, 4)
        out["glyph_anomalous"] = bool(pop < W_OVER_H_MIN or pop > W_OVER_H_MAX)
    else:
        out["notes"] = [f"only {len(lines)} qualifying text lines "
                        f"(< {MIN_TEXT_LINES}); glyph census unreliable"]
    return out


# ------------------------------------------------------------------ combine

def census(path: str | Path, args: argparse.Namespace) -> dict:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = np.asarray(img, dtype=np.float32)

    blobs = blob_census(px, w, h)
    glyphs = glyph_census(px, w, h)

    blob_fire = bool(blobs.get("cluster") and blobs["cluster"]["anomalous"])
    glyph_fire = bool(glyphs.get("glyph_anomalous"))

    result = {
        "image": str(path),
        "size": [w, h],
        "thresholds": {
            "ink_dist": INK_DIST, "erode_iters": ERODE_ITERS,
            "min_cluster_members": MIN_CLUSTER_MEMBERS,
            "log_aspect_min": LOG_ASPECT_MIN,
            "glyph_w_over_h_band": [W_OVER_H_MIN, W_OVER_H_MAX],
        },
        "blobs": blobs,
        "glyphs": {k: v for k, v in glyphs.items() if k != "lines"},
        "glyph_lines": glyphs["lines"],
        "verdict": None,
        "notes": [],
    }
    result["notes"].extend(blobs.get("notes", []))
    result["notes"].extend(glyphs.get("notes", []))

    if blob_fire and glyph_fire:
        result["verdict"] = "anisotropic_squash"
        med = blobs["cluster"]["median_aspect_h_over_w"]
        direction = "tall" if med > 1 else "wide"
        result["notes"].append(
            f"CORROBORATED: solid-shape cluster at aspect {med:.3f} "
            f"({direction}) AND glyph w/h {glyphs['population_median']:.3f} "
            "outside Latin band — two independent channels agree on "
            "non-uniform scale")
    elif blob_fire:
        result["verdict"] = "shape_cluster_anomalous"
        med = blobs["cluster"]["median_aspect_h_over_w"]
        result["notes"].append(
            f"{blobs['cluster']['members']} solid blobs cluster at aspect "
            f"{med:.3f} (|log|>{LOG_ASPECT_MIN}); glyph channel "
            + (f"clean at {glyphs['population_median']:.3f}"
               if glyphs.get("population_median") is not None
               else "inconclusive")
            + " — consistent with anisotropic scale OR a design full of "
              "same-shape non-round elements (pills/badges); needs a "
              "reference or human eye")
    elif glyph_fire:
        result["verdict"] = "glyph_anisotropy"
        result["notes"].append(
            f"glyph w/h {glyphs['population_median']:.3f} outside "
            f"[{W_OVER_H_MIN}, {W_OVER_H_MAX}] across "
            f"{glyphs['n_lines']} lines; blob channel "
            + (f"clean (cluster aspect "
               f"{blobs['cluster']['median_aspect_h_over_w']:.3f})"
               if blobs.get("cluster") else "inconclusive")
            + " — text stretched/squashed without round-shape witnesses")
    else:
        have_witnesses = (
            blobs.get("cluster") is not None
            and blobs["cluster"]["members"] >= MIN_CLUSTER_MEMBERS
            and glyphs.get("population_median") is not None)
        result["verdict"] = "isotropic" if have_witnesses else "insufficient_witnesses"
        if have_witnesses:
            med = blobs["cluster"]["median_aspect_h_over_w"]
            result["notes"].append(
                f"shape cluster aspect {med:.3f}, glyph w/h "
                f"{glyphs['population_median']:.3f} — both channels "
                "inside isotropic bands")
    return result


def fmt_blob(b: dict) -> str:
    x0, y0, x1, y1 = b["bbox"]
    return (f"    bbox=({x0},{y0})-({x1},{y1}) {b['w']}x{b['h']}  "
            f"aspect(h/w)={b['aspect_h_over_w']:.3f}  "
            f"core={b['core_area']}px fill={b['core_fill']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Anisotropy census: flag non-uniform resize squash "
                    "via solid-blob aspect clustering + glyph w/h census.")
    p.add_argument("images", nargs="+", help="image path(s)")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--fail-on-anisotropy", action="store_true",
                   help="exit 1 if any image flags anisotropy")
    p.add_argument("--max-blobs", type=int, default=12,
                   help="max blob rows printed in text mode")
    args = p.parse_args(argv)

    results = []
    any_flag = False
    for path in args.images:
        try:
            r = census(path, args)
        except Exception as e:  # unreadable file etc — report, don't crash batch
            r = {"image": str(path), "verdict": "error", "notes": [str(e)]}
        results.append(r)
        any_flag |= r.get("verdict") in (
            "anisotropic_squash", "shape_cluster_anomalous",
            "glyph_anisotropy")

    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        for r in results:
            if r.get("verdict") == "error":
                print(f"{r['image']}: ERROR {r['notes'][0]}")
                continue
            w, h = r["size"]
            print(f"{r['image']}  {w}x{h}")
            bl, gl = r["blobs"], r["glyphs"]
            cl = bl.get("cluster")
            print(f"  surfaces: bg={bl['surfaces']['page_bg']} "
                  f"card={bl['surfaces']['card']}  ink_px={bl['ink_px']}")
            print(f"  blob channel: {bl['cores']} cores -> "
                  f"{bl['candidates']} candidates "
                  f"({bl.get('round_witnesses', 0)} round-witnesses)"
                  + (f"; cluster {cl['members']} members "
                     f"({cl['share_of_witnesses']:.0%} of witnesses) "
                     f"median aspect={cl['median_aspect_h_over_w']:.3f} "
                     f"spread={cl['spread_log']:.3f}"
                     if cl else "; no cluster"))
            shown = r["blobs"]["blobs"][:args.max_blobs]
            member_ids = {id(b) for b in r["blobs"].get("cluster_members", [])}
            for b in shown:
                tag = " *" if id(b) in member_ids else ""
                print(fmt_blob(b) + tag)
            print(f"  glyph channel: {gl['n_lines']} text lines, "
                  f"ink_px={gl['ink_px']}, "
                  f"population median w/h="
                  f"{gl['population_median'] if gl['population_median'] is not None else 'n/a'}")
            meds = [l["median_glyph_w_over_h"] for l in r["glyph_lines"]]
            if meds:
                lo = sorted(meds)
                print(f"    line medians: min={lo[0]:.3f} "
                      f"p25={lo[len(lo)//4]:.3f} med={lo[len(lo)//2]:.3f} "
                      f"p75={lo[3*len(lo)//4]:.3f} max={lo[-1]:.3f}")
            print(f"  VERDICT: {r['verdict'].upper()}"
                  + (f" — {'; '.join(r['notes'])}" if r["notes"] else ""))
            print()

    return 1 if (args.fail_on_anisotropy and any_flag) else 0


if __name__ == "__main__":
    sys.exit(main())
