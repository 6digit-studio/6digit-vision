"""edge-bisect — mid-bbox edge-bisection detector for occluded text.

Fills the gap named in evals/z-order/VERDICT.md (instrument gap #1): a
text bbox *bisected* by an interior edge line — the signature of an
occluding surface (wrong z-order / stacking context) slicing glyphs
mid-body. `eyes.layout.text_edge_flush` only checks whether a bbox edge
lands ON a globally-detected edge line; it never checks a line cutting
*through* a bbox's interior, and `interior_edge_lines`' whole-frame
row/column profiles cannot even see local occlusion edges (on the eval
artifact it returns zero lines — the card border is too subtle at the
256px analysis canvas and is hidden behind the menu on the control).

This detector works per-text-bbox, on full-resolution pixels:

    for each Mirage text bbox (denormed to px):
      1. ink band  — rows/cols inside the bbox carrying glyph ink
                     (|px - median| > INK_THRESH; median = surface estimate)
      2. scan every transition strictly inside the bbox (2px inset) on
         both axes: per-column |step| across the cut
      3. a cut qualifies when ALL of:
           - coverage >= COV_MIN      (>=80% of span columns step >= DIFF)
           - median step >= MED_MIN   (a real surface transition, not noise)
           - flat_frac >= FLAT_MIN on BOTH sides (each side is a flat
             surface within +-FLAT_TOL of its median) — this is what
             separates a foreign rule-line from glyph texture: glyph
             rows are textured (flat_frac ~0.0-0.6), surface rows are
             flat (1.00 on the eval artifact)
           - cut within INK_K px of the ink band — the edge must be
             cutting *this* text's glyphs, not floating in bbox padding
             (the divider-in-padding false-positive class)
           - ink on at most ONE side of the cut — substantial ink on
             both sides means the edge separates two content populations
             (or crosses a multi-line block), not a slice of one glyph
             run (the aspect-abuse control FP class)
           - the ink band's cut-adjacent edge is DENSE — a mid-stroke
             slice leaves heavy ink in the last visible rows/cols, while
             a natural glyph edge tapers (the aspect-abuse defect FP:
             a dark bar's edge hovering in bbox padding above an
             intact text line)
      4. adjacent qualifying rows cluster into one finding.

Consumes `eyes describe` records: pass --record to reuse saved JSON,
otherwise the detector calls eyes.mirage.describe itself (project env).

Usage (from repo root):
    uv run detectors/edge-bisect/edge_bisect.py evals/z-order/defect.png
    uv run detectors/edge-bisect/edge_bisect.py --record rec.json img.png
    uv run detectors/edge-bisect/edge_bisect.py --json *.png
    uv run detectors/edge-bisect/edge_bisect.py --fail-on-findings *.png

Exit code is 0 unless --fail-on-findings is given and any image flags.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from eyes.color import denorm  # project env: same mapping Mirage uses
except Exception:  # pragma: no cover - standalone fallback
    def denorm(bbox, width, height):
        x0, y0, x1, y1 = bbox
        return (round(x0 / 1000.0 * width), round(y0 / 1000.0 * height),
                round(x1 / 1000.0 * width), round(y1 / 1000.0 * height))

# ------------------------------------------------------------------ tunables

DIFF = 18.0          # per-column gray step counted as "transitioning"
COV_MIN = 0.80       # fraction of span columns that must transition
MED_MIN = 15.0       # median |step| across the span (surface, not noise)
FLAT_TOL = 10.0      # gray levels around a row/col median counted "flat"
FLAT_MIN = 0.85      # fraction of span positions that must be flat, BOTH sides
INSET = 2            # px: cut must be this far inside the bbox (flush territory
                     # belongs to text_edge_flush; Mirage bboxes carry ~2-4px
                     # padding, so the inset stays small)
INK_THRESH = 45.0    # |px - surface median| counted as glyph ink
INK_MIN_COUNT_FRAC = 0.02  # ...or at least this fraction of the span, whichever larger
INK_MIN_COUNT = 2
FULL_INK_FRAC = 0.7  # positions inked over >=70% of the span are solid foreign
                     # bands (rules, borders, photo edges), not glyph rows —
                     # excluding them keeps a divider inside the bbox from
                     # stretching the ink band and defeating the adjacency guard
INK_K = 6            # cut must be within this many px of the ink band
SIDE_MIN_POS = 2     # a cut with real ink on BOTH sides is an edge *between*
SIDE_MIN_PX = 12     # two content populations (or a mid-text crossing), not
                     # a slice of one glyph run — suppressed as ambiguous
EDGE_N = 2           # ink positions sampled at the band edge nearest the cut
DENSE_MIN = 0.5      # ...must carry >=this fraction of the band's peak ink
                     # count: a mid-stroke slice leaves dense ink right at the
                     # cut; a natural glyph edge tapers to near-zero (control
                     # 'Duplicate' bottoms fade 44->2 over 3 rows)
MIN_SPAN = 8         # px: bboxes smaller than this on the scanned axis are skipped


def _open_gray(path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L"), dtype=np.float32)


def _flat_frac(line: np.ndarray, tol: float = FLAT_TOL) -> float:
    """Fraction of positions within +-tol of the line's median."""
    if line.size == 0:
        return 0.0
    med = np.median(line)
    return float((np.abs(line - med) <= tol).mean())


def _ink_profile_1d(crop: np.ndarray, axis: int):
    """Ink positions + per-position ink-pixel counts along `axis`.

    crop is the bbox interior; bg is estimated as the crop median (ink is
    always the minority). axis=0 -> rows (for horizontal cuts), 1 -> cols.
    Positions inked over >=FULL_INK_FRAC of the span are solid foreign
    bands, not glyph rows, and are excluded.
    Returns (idx, counts) as np arrays, or None when no ink found.
    """
    bg = float(np.median(crop))
    ink = np.abs(crop - bg) > INK_THRESH
    counts = ink.sum(axis=1 - axis).astype(np.int64)
    width = crop.shape[1 - axis]  # span length each count is taken over
    need = max(INK_MIN_COUNT, int(np.ceil(INK_MIN_COUNT_FRAC * width)))
    full = FULL_INK_FRAC * width
    idx = np.nonzero((counts >= need) & (counts < full))[0]
    if idx.size == 0:
        return None
    return idx, counts[idx]


def _band_dist(pos: int, band: tuple[int, int], base: int) -> int:
    """Distance from absolute position `pos` to ink band (band is relative
    to `base`, the bbox origin on the cut axis)."""
    b0, b1 = base + band[0], base + band[1]
    if b0 <= pos <= b1:
        return 0
    return int(min(abs(pos - b0), abs(pos - b1)))


def _two_sided_ink(ink, cut_rel: int) -> bool:
    """True when substantial ink sits on BOTH sides of the cut — the edge
    separates two content populations (or crosses a multi-line block)
    rather than slicing one glyph run. `ink` = (idx, counts) crop-relative;
    cut_rel = cut position in crop coords (the lower row/col of the
    transition)."""
    idx, counts = ink
    lo = idx < cut_rel
    hi = idx >= cut_rel
    lo_ok = lo.sum() >= SIDE_MIN_POS and counts[lo].sum() >= SIDE_MIN_PX
    hi_ok = hi.sum() >= SIDE_MIN_POS and counts[hi].sum() >= SIDE_MIN_PX
    return bool(lo_ok and hi_ok)


def _dense_cut_edge(ink, cut_rel: int) -> bool:
    """True when the ink band's edge nearest the cut is DENSE — the
    signature of glyphs sliced mid-stroke. Natural glyph tops/bottoms
    taper (ascender tips, baseline antialiasing); a horizontal/vertical
    occlusion slice leaves substantial ink in the last visible rows/cols.

    Returns False (suppress) when the cut sits beside a tapered natural
    edge — e.g. a foreign element's boundary hovering in bbox padding
    above an intact text line (the aspect-abuse defect FP).
    """
    idx, counts = ink
    b0, b1 = int(idx[0]), int(idx[-1])
    peak = float(counts.max())
    if peak <= 0:
        return False
    if cut_rel > b1:      # cut below band -> test band's bottom edge
        edge = counts[-EDGE_N:]
    elif cut_rel <= b0:   # cut above band -> test band's top edge
        edge = counts[:EDGE_N]
    else:                 # cut inside the band: ink straddles it — the
        return True      # two-sided rule already governs this case
    return bool(edge.min() >= DENSE_MIN * peak)


def _scan_axis(gray: np.ndarray, x0: int, y0: int, x1: int, y1: int,
               axis: str, ink, k: int = INK_K):
    """Find qualifying cut positions strictly inside the bbox on one axis.

    axis 'h': horizontal edge — transitions between rows, coverage measured
    across columns [x0, x1). axis 'v': vertical edge — transitions between
    columns, coverage across rows [y0, y1).
    `ink` = (idx, counts) crop-relative ink profile on the cut axis, or
    None. Returns list of finding dicts (unclustered).
    """
    findings = []
    if axis == "h":
        lo, hi = y0 + INSET, y1 - INSET
        if hi < lo or (x1 - x0) < MIN_SPAN:
            return findings
        band = (int(ink[0][0]), int(ink[0][-1])) if ink else None
        for y in range(lo, hi + 1):
            d = np.abs(gray[y, x0:x1] - gray[y - 1, x0:x1])
            cov = float((d >= DIFF).mean())
            if cov < COV_MIN:
                continue
            med = float(np.median(d))
            if med < MED_MIN:
                continue
            ff_prev = _flat_frac(gray[y - 1, x0:x1])
            ff_cur = _flat_frac(gray[y, x0:x1])
            if min(ff_prev, ff_cur) < FLAT_MIN:
                continue
            if ink is None:
                continue
            dist = _band_dist(y, band, y0)
            if dist > k:
                continue
            if _two_sided_ink(ink, y - y0):
                continue
            if not _dense_cut_edge(ink, y - y0):
                continue
            # underline guard: a local rule (link underline, divider)
            # ends at the text bbox; a container edge continues past
            # it. Require the gradient to persist beyond the span.
            if not _edge_continues(gray, y, x0, x1, "h"):
                continue
            findings.append({
                "axis": "horizontal", "line": y,
                "coverage": round(cov, 3), "median_step": round(med, 1),
                "flat_prev": round(ff_prev, 3), "flat_cur": round(ff_cur, 3),
                "ink_dist_px": dist,
            })
    else:
        lo, hi = x0 + INSET, x1 - INSET
        if hi < lo or (y1 - y0) < MIN_SPAN:
            return findings
        band = (int(ink[0][0]), int(ink[0][-1])) if ink else None
        for x in range(lo, hi + 1):
            d = np.abs(gray[y0:y1, x] - gray[y0:y1, x - 1])
            cov = float((d >= DIFF).mean())
            if cov < COV_MIN:
                continue
            med = float(np.median(d))
            if med < MED_MIN:
                continue
            ff_prev = _flat_frac(gray[y0:y1, x - 1])
            ff_cur = _flat_frac(gray[y0:y1, x])
            if min(ff_prev, ff_cur) < FLAT_MIN:
                continue
            if ink is None:
                continue
            dist = _band_dist(x, band, x0)
            if dist > k:
                continue
            if _two_sided_ink(ink, x - x0):
                continue
            if not _dense_cut_edge(ink, x - x0):
                continue
            if not _edge_continues(gray, x, y0, y1, "v"):
                continue
            findings.append({
                "axis": "vertical", "line": x,
                "coverage": round(cov, 3), "median_step": round(med, 1),
                "flat_prev": round(ff_prev, 3), "flat_cur": round(ff_cur, 3),
                "ink_dist_px": dist,
            })
    return findings


def _edge_continues(gray: np.ndarray, pos: int, lo: int, hi: int,
                    axis: str, ext: int = 24) -> bool:
    """Does the edge gradient persist beyond the text span?

    A container boundary (card edge slicing text) continues past the
    bbox; a local decoration (link underline, text divider) ends at it.
    Samples the same transition EXT px beyond each side; requires >=50%
    of the extension window to hold the gradient on at least one side.
    """
    h, w = gray.shape
    d = DIFF
    if axis == "h":
        y = pos
        if y < 1 or y >= h:
            return False
        for a, b in ((max(0, lo - ext), lo), (hi, min(w, hi + ext))):
            if b - a < 8:
                continue
            cov = float((np.abs(gray[y, a:b] - gray[y - 1, a:b]) >= d).mean())
            if cov >= 0.5:
                return True
        return False
    x = pos
    if x < 1 or x >= w:
        return False
    for a, b in ((max(0, lo - ext), lo), (hi, min(h, hi + ext))):
        if b - a < 8:
            continue
        cov = float((np.abs(gray[a:b, x] - gray[a:b, x - 1]) >= d).mean())
        if cov >= 0.5:
            return True
    return False


def _cluster(rows: list[dict], gap: int = 3) -> list[dict]:
    """Cluster qualifying cut rows within `gap` px; keep strongest per cluster."""
    if not rows:
        return []
    rows = sorted(rows, key=lambda r: r["line"])
    clusters, cur = [], [rows[0]]
    for r in rows[1:]:
        if r["line"] - cur[-1]["line"] <= gap:
            cur.append(r)
        else:
            clusters.append(cur)
            cur = [r]
    clusters.append(cur)
    out = []
    for c in clusters:
        best = max(c, key=lambda r: (r["coverage"], r["median_step"]))
        out.append({
            "axis": best["axis"],
            "line_px": best["line"],
            "line_span_px": [c[0]["line"], c[-1]["line"]],
            "coverage": best["coverage"],
            "median_step": best["median_step"],
            "flat_prev": best["flat_prev"], "flat_cur": best["flat_cur"],
            "ink_dist_px": best["ink_dist_px"],
            "n_rows": len(c),
        })
    return out


def detect(image_path, record: dict, args) -> dict:
    gray = _open_gray(image_path)
    h, w = gray.shape
    result = {
        "image": str(image_path), "size": [w, h],
        "findings": [], "texts_scanned": 0, "texts_skipped": 0,
    }
    for t in record.get("text", []):
        if "bbox" not in t:
            continue
        x0, y0, x1, y1 = denorm(t["bbox"], w, h)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < MIN_SPAN or y1 - y0 < MIN_SPAN:
            result["texts_skipped"] += 1
            continue
        result["texts_scanned"] += 1

        crop = gray[y0:y1 + 1, x0:x1 + 1]
        ink_h = _ink_profile_1d(crop, axis=0)   # rows carrying glyph ink
        ink_v = _ink_profile_1d(crop, axis=1)   # cols carrying glyph ink
        if ink_h is None and ink_v is None:
            result["texts_skipped"] += 1
            continue

        cuts = []
        cuts += _scan_axis(gray, x0, y0, x1, y1, "h", ink_h, args.ink_k)
        cuts += _scan_axis(gray, x0, y0, x1, y1, "v", ink_v, args.ink_k)
        for c in _cluster(cuts):
            result["findings"].append({
                "string": (t.get("string") or "")[:48],
                "bbox_norm": t["bbox"],
                "bbox_px": [x0, y0, x1, y1],
                "ink_band_px": (
                    [y0 + int(ink_h[0][0]), y0 + int(ink_h[0][-1])]
                    if ink_h is not None else None),
                "ink_band_cols_px": (
                    [x0 + int(ink_v[0][0]), x0 + int(ink_v[0][-1])]
                    if ink_v is not None else None),
                **{k: v for k, v in c.items()},
            })
    result["verdict"] = "edge_bisect" if result["findings"] else "clean"
    return result


def _get_record(image: str, record_path: str | None) -> dict:
    if record_path:
        return json.loads(Path(record_path).read_text())
    from eyes import mirage
    return mirage.describe(image)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Flag text bboxes bisected by a coherent interior "
                    "edge line (mid-glyph occlusion slice).")
    p.add_argument("images", nargs="+", help="image path(s)")
    p.add_argument("--record", default=None,
                   help="precomputed `eyes describe` JSON (single image only)")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--ink-k", type=int, default=INK_K,
                   help="max px distance from cut to ink band")
    p.add_argument("--fail-on-findings", action="store_true",
                   help="exit 1 if any image produces findings")
    args = p.parse_args(argv)

    if args.record and len(args.images) != 1:
        p.error("--record requires exactly one image")

    results = []
    any_hit = False
    for img in args.images:
        try:
            rec = _get_record(img, args.record)
            r = detect(img, rec, args)
        except Exception as e:
            r = {"image": img, "verdict": "error", "notes": [str(e)]}
        results.append(r)
        any_hit |= bool(r.get("findings"))

    if args.json:
        print(json.dumps({"results": results}, indent=2, ensure_ascii=False))
    else:
        for r in results:
            if r.get("verdict") == "error":
                print(f"{r['image']}: ERROR {r['notes'][0]}")
                continue
            w, h = r["size"]
            print(f"{r['image']}  {w}x{h}  "
                  f"scanned={r['texts_scanned']} skipped={r['texts_skipped']}")
            for f in r["findings"]:
                pos = (f"y={f['line_px']}" if f["axis"] == "horizontal"
                       else f"x={f['line_px']}")
                print(f"  EDGE-BISECT {f['axis']} {pos} "
                      f"cov={f['coverage']} med={f['median_step']} "
                      f"flat={f['flat_prev']}/{f['flat_cur']} "
                      f"ink_dist={f['ink_dist_px']}px  "
                      f"\"{f['string']}\"  bbox_px={f['bbox_px']}")
            print(f"  VERDICT: {r['verdict'].upper()}")
            print()

    return 1 if (args.fail_on_findings and any_hit) else 0


if __name__ == "__main__":
    sys.exit(main())
