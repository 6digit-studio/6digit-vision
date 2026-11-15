"""dct-phash fdiff — DCT/pHash-style perceptual image distance.

Mechanism: both images are reduced to a small fixed canvas (32x32), a 2D
DCT-II (ortho) is taken per RGB channel, and only the low-frequency
8x8 coefficient band (DC excluded) is kept. That band is the perceptual
channel: page structure, missing cards, shifted blocks and color fields
live there, while AA edges, JPEG ringing and subpixel text jitter live
above it and are discarded by construction.

Score: ``1 - distance`` where distance is the max of
  - band_rel_l2: mean over channels of ||Va-Vb|| / (||Va||+||Vb||) on the
    non-DC band vectors (bounded [0,1] by the triangle inequality), and
  - color_rel:   the same relative-L2 on the 3-vector of channel means,
    which catches full-canvas color/brightness swaps the DC-less band
    cannot see.
Identical images -> distance 0 -> score 1.0.

Localization: the common canvas is split into ~150px cells; each cell
pair is reduced to 32x32 and its band-coefficient difference is measured
in ABSOLUTE units normalized by the global band energy G (stable on flat
UI cells where a per-cell ratio would blow up). Cells above a fixed
threshold are merged into regions; each region bbox is then tightened by
a low-pass residual (gaussian-blurred per-channel abs diff) inside the
cell union. Bboxes are pixel coords of the common canvas.

Secondary metric reported (not scored): pHash-style sign agreement —
per-channel fraction of band coefficients whose sign-vs-median bit
flipped (hamming distance / nbits).

Known honest limits:
- A 1px global translation still perturbs low-band coefficients near
  sharp edges; measured max cell distance ~0.33 vs threshold 0.35, so it
  produces ~zero regions and a ~0.99 score — suppressed, not aligned.
- Global score is structural, not pixel-fidelity: a localized 20px
  block shift scores ~0.95 while a broad fine-render difference (ui1
  pair) scores ~0.75 — different instruments, different scales.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy.fftpack import dct
from scipy import ndimage

CANVAS = 32          # perceptual thumbnail size
BAND = 8             # keep BAND x BAND low-freq coeffs per channel
CELL_PX = 150        # localization cell target size
CELL_CANVAS = 32     # per-cell DCT canvas
REGION_THR = 0.35    # cell distance threshold (units of global band norm)
MIN_CELL_AREA_FRAC = 0.0005  # min merged-region area as fraction of canvas
MAX_DIM = 1600       # cap on working canvas long side

_MASK = np.ones((BAND, BAND), bool)
_MASK[0, 0] = False  # exclude DC from the structural band


def _load_rgb(path) -> Image.Image:
    return Image.open(str(path)).convert("RGB")


def _prep(a, b):
    """Load both to float RGB arrays on a common canvas.

    b is resized to a's size when sizes differ; oversized canvases are
    downscaled proportionally to MAX_DIM. Returns float32 HxWx3 in
    [0,1] plus the canvas (w, h).
    """
    ia, ib = _load_rgb(a), _load_rgb(b)
    if ib.size != ia.size:
        ib = ib.resize(ia.size, Image.BILINEAR)
    w, h = ia.size
    scale = min(1.0, MAX_DIM / max(w, h))
    if scale < 1.0:
        nw, nh = max(8, int(w * scale)), max(8, int(h * scale))
        ia = ia.resize((nw, nh), Image.BILINEAR)
        ib = ib.resize((nw, nh), Image.BILINEAR)
        w, h = nw, nh
    A = np.asarray(ia, dtype=np.float32) / 255.0
    B = np.asarray(ib, dtype=np.float32) / 255.0
    return A, B, (w, h)


def _small(img: np.ndarray, size: int = CANVAS) -> np.ndarray:
    """Resize an HxWx3 float array to size x size via PIL."""
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    im = im.resize((size, size), Image.BILINEAR)
    return np.asarray(im, dtype=np.float32) / 255.0


def _bandvec(img_small: np.ndarray) -> np.ndarray:
    """Concat non-DC low-band DCT coefficients over RGB channels."""
    out = []
    for ch in range(3):
        d = dct(dct(img_small[..., ch], axis=0, norm="ortho"),
                axis=1, norm="ortho")[:BAND, :BAND]
        out.append(d[_MASK].ravel())
    return np.concatenate(out)


def _channel_bands(img_small: np.ndarray):
    """Per-channel non-DC band vectors (for per-channel rel-L2)."""
    vecs = []
    for ch in range(3):
        d = dct(dct(img_small[..., ch], axis=0, norm="ortho"),
                axis=1, norm="ortho")[:BAND, :BAND]
        vecs.append(d[_MASK].ravel())
    return vecs


def _rel_l2(va: np.ndarray, vb: np.ndarray, eps: float = 1e-3) -> float:
    """||va-vb|| / (||va||+||vb||+eps), bounded ~[0,1]; 0 when both flat."""
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na + nb < eps:
        return 0.0
    return float(np.linalg.norm(va - vb) / (na + nb + eps))


def _mean_color(img_small: np.ndarray) -> np.ndarray:
    return img_small.reshape(-1, 3).mean(axis=0)


def _phash_hamming(a_small: np.ndarray, b_small: np.ndarray) -> float:
    """Fraction of band coeffs whose sign-vs-median bit differs."""
    flips, total = 0, 0
    for ch in range(3):
        d = dct(dct(a_small[..., ch], axis=0, norm="ortho"),
                axis=1, norm="ortho")[:BAND, :BAND]
        e = dct(dct(b_small[..., ch], axis=0, norm="ortho"),
                axis=1, norm="ortho")[:BAND, :BAND]
        va, vb = d[_MASK].ravel(), e[_MASK].ravel()
        flips += int(((va > np.median(va)) != (vb > np.median(vb))).sum())
        total += va.size
    return flips / max(total, 1)


def _cell_grid(shape):
    H, W = shape[:2]
    cols = max(4, int(round(W / CELL_PX)))
    rows = max(3, int(round(H / CELL_PX)))
    ys = np.linspace(0, H, rows + 1).astype(int)
    xs = np.linspace(0, W, cols + 1).astype(int)
    return ys, xs


def _cell_distances(A: np.ndarray, B: np.ndarray, G: float):
    """Per-cell band distance in absolute units of global band norm G.

    Returns (D, ys, xs) with D shape (rows, cols).
    """
    ys, xs = _cell_grid(A.shape)
    rows, cols = len(ys) - 1, len(xs) - 1
    D = np.zeros((rows, cols), dtype=np.float64)
    for r in range(rows):
        for c in range(cols):
            ta = A[ys[r]:ys[r + 1], xs[c]:xs[c + 1]]
            tb = B[ys[r]:ys[r + 1], xs[c]:xs[c + 1]]
            ca = _small(ta, CELL_CANVAS)
            cb = _small(tb, CELL_CANVAS)
            # absolute band distance normalized by global energy — stable
            # on flat cells where a relative ratio would be undefined
            d_band = float(np.linalg.norm(_bandvec(ca) - _bandvec(cb)) / (G + 1e-9))
            # mean-color relative distance catches flat color-field swaps
            d_col = _rel_l2(_mean_color(ca), _mean_color(cb))
            D[r, c] = max(d_band, d_col)
    return D, ys, xs


def _regions_from_cells(D: np.ndarray, ys, xs, A: np.ndarray, B: np.ndarray):
    """Threshold hot cells, merge 8-connected components, tighten bboxes
    with a low-pass residual inside each component's cell union."""
    hot = D > REGION_THR
    lab, n = ndimage.label(hot, structure=np.ones((3, 3), int))
    regions = []
    H, W = A.shape[:2]
    min_area = max(1, int(MIN_CELL_AREA_FRAC * H * W))
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        r0 = sl[0].start
        c0 = sl[1].start
        member = lab[sl] == i
        # union of member cell bounds
        rows_hit = np.where(member.any(axis=1))[0]
        cols_hit = np.where(member.any(axis=0))[0]
        y0 = int(ys[r0 + rows_hit[0]])
        y1 = int(ys[r0 + rows_hit[-1] + 1])
        x0 = int(xs[c0 + cols_hit[0]])
        x1 = int(xs[c0 + cols_hit[-1] + 1])
        # dilate one cell so refinement has margin
        ry0 = int(ys[max(0, r0 + rows_hit[0] - 1)])
        ry1 = int(ys[min(len(ys) - 1, r0 + rows_hit[-1] + 2)])
        rx0 = int(xs[max(0, c0 + cols_hit[0] - 1)])
        rx1 = int(xs[min(len(xs) - 1, c0 + cols_hit[-1] + 2)])
        # tighten with low-pass residual inside dilated union: each
        # significant residual cluster becomes its own region box
        boxes = _tighten_boxes(A[ry0:ry1, rx0:rx1],
                               B[ry0:ry1, rx0:rx1])
        if boxes:
            for (by0, by1, bx0, bx1) in boxes:
                ty0, ty1 = ry0 + by0, ry0 + by1
                tx0, tx1 = rx0 + bx0, rx0 + bx1
                area = (ty1 - ty0) * (tx1 - tx0)
                if area < min_area:
                    continue
                regions.append({
                    "bbox_px": [int(tx0), int(ty0), int(tx1), int(ty1)],
                    "area_px": int(area),
                    "area_frac": round(area / (H * W), 5),
                    "cell_dist_max": round(float(D[sl][member].max()), 4),
                })
            continue
        area = (y1 - y0) * (x1 - x0)
        if area < min_area:
            continue
        strength = float(D[sl][member].max())
        regions.append({
            "bbox_px": [int(x0), int(y0), int(x1), int(y1)],
            "area_px": int(area),
            "area_frac": round(area / (H * W), 5),
            "cell_dist_max": round(strength, 4),
        })
    regions.sort(key=lambda r: -r["area_px"])
    return regions[:12]


def _tighten_boxes(ta: np.ndarray, tb: np.ndarray):
    """Low-pass residual clusters within a crop. Returns a list of
    (y0,y1,x0,x1) crop-coord bboxes — one per residual component holding
    >=5% of the crop's hot mass — or [] if the residual is empty."""
    # gaussian-blurred per-channel abs diff ~ the spatial footprint of the
    # low band our DCT keeps; threshold at a fraction of the crop max
    diff = np.abs(ta - tb).mean(axis=2)
    blur = ndimage.gaussian_filter(diff, sigma=max(4.0, min(ta.shape[:2]) / 40.0))
    peak = float(blur.max())
    if peak <= 1e-6:
        return []
    mask = blur > max(0.02, 0.30 * peak)
    lab, n = ndimage.label(mask)
    if n == 0:
        return []
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None or sizes[i - 1] < 0.05 * mask.sum():
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        boxes.append((int(y0), int(y1), int(x0), int(x1)))
    return boxes


def fdiff(a_path, b_path) -> dict:
    A, B, (w, h) = _prep(a_path, b_path)

    # ---- global perceptual distance on the 32x32 canvas ----
    aS, bS = _small(A, CANVAS), _small(B, CANVAS)
    ca, cb = _channel_bands(aS), _channel_bands(bS)
    band_terms = [_rel_l2(va, vb) for va, vb in zip(ca, cb)]
    band_d = float(np.mean(band_terms)) if band_terms else 0.0
    col_d = _rel_l2(_mean_color(aS), _mean_color(bS))
    dist = max(band_d, col_d)
    score = float(np.clip(1.0 - dist, 0.0, 1.0))

    # ---- localization on ~150px cells ----
    G = float(np.linalg.norm(np.concatenate([v for v in ca])))
    D, ys, xs = _cell_distances(A, B, G)
    regions = _regions_from_cells(D, ys, xs, A, B)

    notes = [
        f"canvas={w}x{h} thumb={CANVAS}x{CANVAS} band={BAND}x{BAND}/ch "
        f"(DC excluded)",
        f"band_rel_l2={band_d:.4f} color_rel={col_d:.4f} "
        f"cell_thr={REGION_THR} cell_px~{CELL_PX}",
        "score = 1 - max(band_rel_l2, color_rel); low band discards "
        "AA/compression/high-freq jitter by construction",
    ]
    if G < 1e-6:
        notes.append("near-flat global band (G~0): structural term "
                     "degenerate, color term dominates")

    return {
        "score": round(score, 4),
        "distance": round(dist, 4),
        "band_rel_l2": round(band_d, 4),
        "color_rel": round(col_d, 4),
        "phash_hamming": round(_phash_hamming(aS, bS), 4),
        "n_regions": len(regions),
        "regions": regions,
        "size": [w, h],
        "notes": notes,
    }


def main() -> int:
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = fdiff(args.a, args.b)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"fdiff score={r['score']} band={r['band_rel_l2']} "
              f"color={r['color_rel']} phash={r['phash_hamming']} "
              f"regions={r['n_regions']}")
        for reg in r["regions"][:6]:
            print(f"  {reg}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
