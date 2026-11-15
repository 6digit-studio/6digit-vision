"""fdiff/pyramid — Gaussian-pyramid multi-scale image diff.

Mechanism: build Gaussian pyramids for both images, diff at every
level, and fuse with coarse-heavy weights — coarse levels carry
structure (missing cards, shifted blocks, color fields) while the
finest level (AA edges, compression, subpixel text jitter) is
present but weakly weighted.

Alignment: a 1px global translation produces massive edge diffs at the
finest level. To fix that, phase correlation at half resolution
proposes a global shift (subpixel-refined), then an SSD search at
full resolution over a small window verifies and snaps it to an
integer shift. The shift is only applied if it measurably reduces the
full-res mean-abs diff — so unrelated image pairs can't be hurt by a
spurious alignment.

Localization: per-level diffs are thresholded adaptively and
upsampled; the union forms a change mask that is connected-componented
into pixel bboxes on the common canvas.

API: fdiff(a_path, b_path) -> {"score": 0..1, "regions": [...],
"notes": [...]}
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

MAX_LEVELS = 6
# Per-level fusion weights, level 0 = finest. Coarse levels dominate;
# the finest level still contributes (fine edits) at ~1/4 of the
# coarsest weight.
LEVEL_W = np.array([0.05, 0.09, 0.15, 0.22, 0.24, 0.25], dtype=np.float64)
# Per-level region-mask thresholds on max-channel |diff| (0..1).
# Absolute: identical -> 0 everywhere; AA/compression stays < ~0.08.
MASK_THR = 0.10
# Hysteresis low threshold used to grow confirmed seeds.
MASK_LO = 0.06
# Score thresholds on the fused map F (weighted mean level diff).
SOFT_THR = 0.02   # soft-energy knee: below = noise floor
FRAC_THR = 0.05   # changed-fraction knee
MIN_REGION_AREA = 24          # px on the common canvas
MAX_REGIONS = 16
ALIGN_IMPROVE = 0.995         # apply shift only if cost < this * zero-cost
ALIGN_RADIUS = 2              # SSD search radius around phase proposal


def _load(a_path, b_path):
    """Both -> float32 RGB 0..1 on a common canvas (B resized to A)."""
    ia = Image.open(str(a_path)).convert("RGB")
    ib = Image.open(str(b_path)).convert("RGB")
    if ib.size != ia.size:
        ib = ib.resize(ia.size, Image.BILINEAR)
    A = np.asarray(ia, dtype=np.float32) / 255.0
    B = np.asarray(ib, dtype=np.float32) / 255.0
    return A, B


def _gray(img):
    if img.ndim == 2:
        return img.astype(np.float32, copy=False)
    return (0.299 * img[..., 0] + 0.587 * img[..., 1]
            + 0.114 * img[..., 2]).astype(np.float32)


def _down2(g):
    """One Gaussian-pyramid step on a 2-D float image."""
    g = ndimage.gaussian_filter(g, sigma=1.0)
    return g[::2, ::2]


def _pyramid(img, levels):
    """Gaussian pyramid of a 3-D (H,W,C) or 2-D image, finest first."""
    pyr = [img]
    cur = img
    for _ in range(levels - 1):
        if cur.ndim == 3:
            g = ndimage.gaussian_filter(cur, sigma=(1.0, 1.0, 0.0))
        else:
            g = ndimage.gaussian_filter(cur, sigma=1.0)
        cur = g[::2, ::2]
        pyr.append(cur)
    return pyr


def _shift_img(img, dy, dx):
    """out[y,x] = img[y-dy, x-dx]; borders replicate the edge."""
    if dy == 0 and dx == 0:
        return img
    h, w = img.shape[:2]
    ay, ax = abs(dy), abs(dx)
    pad_width = [(ay, ay), (ax, ax)] + ([(0, 0)] if img.ndim == 3 else [])
    p = np.pad(img, pad_width, mode="edge")
    y0 = ay - dy
    x0 = ax - dx
    return p[y0:y0 + h, x0:x0 + w]


def _phase_shift(ga, gb):
    """Phase correlation: returns (dy, dx, conf) — gb is ga shifted by
    (dy, dx), i.e. gb[y,x] ~= ga[y-dy, x-dx]. Subpixel via parabolic
    peak interpolation."""
    h, w = ga.shape
    win = np.outer(np.hanning(h).astype(np.float32),
                   np.hanning(w).astype(np.float32))
    Fa = np.fft.fft2((ga - ga.mean()) * win)
    Fb = np.fft.fft2((gb - gb.mean()) * win)
    R = Fa * np.conj(Fb)
    R /= (np.abs(R) + 1e-9)
    r = np.abs(np.fft.ifft2(R))
    iy, ix = np.unravel_index(int(np.argmax(r)), r.shape)
    peak = float(r[iy, ix])
    conf = peak / (float(np.median(r)) + 1e-9)
    dy = float(iy if iy <= h // 2 else iy - h)
    dx = float(ix if ix <= w // 2 else ix - w)

    def _ref(v_prev, v0, v_next):
        den = v_prev - 2.0 * v0 + v_next
        if abs(den) < 1e-12:
            return 0.0
        return float(np.clip(0.5 * (v_prev - v_next) / den, -1.0, 1.0))

    dy += _ref(r[(iy - 1) % h, ix], peak, r[(iy + 1) % h, ix])
    dx += _ref(r[iy, (ix - 1) % w], peak, r[iy, (ix + 1) % w])
    return dy, dx, conf


def _mad_cost(ga, gb, dy, dx):
    """Mean |ga - shifted gb| on a strided view (SSD-lite)."""
    sh = _shift_img(gb, dy, dx)
    d = np.abs(ga - sh)
    return float(d[::2, ::2].mean())


def _estimate_global_shift(A, B):
    """Integer (dy, dx) to apply to B so it aligns to A, else (0,0).

    Phase correlation at half resolution proposes; full-res mean-abs
    search over base +/- ALIGN_RADIUS decides. (0,0) is always a
    candidate, so a bad proposal can never be forced."""
    ga = _gray(A)
    gb = _gray(B)
    # half-res phase correlation (robust to fine noise; a full-res 1px
    # shift is a detectable ~0.5px there)
    dy1, dx1, conf = _phase_shift(_down2(ga), _down2(gb))
    base_y = int(round(2.0 * dy1))
    base_x = int(round(2.0 * dx1))

    best = (0, 0)
    best_cost = _mad_cost(ga, gb, 0, 0)
    zero_cost = best_cost
    rng = range(-ALIGN_RADIUS, ALIGN_RADIUS + 1)
    for dy in (base_y + k for k in rng):
        for dx in (base_x + k for k in rng):
            if dy == 0 and dx == 0:
                continue
            c = _mad_cost(ga, gb, dy, dx)
            if c < best_cost:
                best_cost = c
                best = (dy, dx)
    # require a real improvement, not noise-level tie-breaking
    if best != (0, 0) and best_cost < ALIGN_IMPROVE * zero_cost:
        return best
    return (0, 0)


def _upsample2(d, w, h):
    """Bilinear upsample of a 2-D level diff to (h, w)."""
    zh, zw = h / d.shape[0], w / d.shape[1]
    return ndimage.zoom(d.astype(np.float32), (zh, zw), order=1)


def fdiff(a_path, b_path):
    notes = []
    A, B = _load(a_path, b_path)
    h, w = A.shape[:2]

    # --- global alignment ---
    # `shift` is the correction to apply to B (verified by SSD search)
    shift = _estimate_global_shift(A, B)
    if shift != (0, 0):
        B = _shift_img(B, shift[0], shift[1])
    notes.append(f"global_align_px={list(shift)}")

    # --- pyramids ---
    levels = MAX_LEVELS
    while levels > 1 and min(h, w) // (2 ** (levels - 1)) < 24:
        levels -= 1
    pa = _pyramid(A, levels)
    pb = _pyramid(B, levels)

    # --- per-level diffs, fused + region mask ---
    weights = LEVEL_W[:levels]
    weights = weights / weights.sum()
    F = np.zeros((h, w), dtype=np.float32)
    mask_hi = np.zeros((h, w), dtype=bool)
    mask_lo = np.zeros((h, w), dtype=bool)
    lvl_means = []
    for l in range(levels):
        d = np.abs(pa[l] - pb[l])
        if d.ndim == 3:
            d = d.max(axis=2)
        lvl_means.append(round(float(d.mean()), 5))
        up = _upsample2(d, w, h)
        F += np.float32(weights[l]) * up
        mask_hi |= up > MASK_THR
        mask_lo |= up > MASK_LO

    # hysteresis: keep low-threshold pixels connected to a high seed
    if mask_hi.any():
        lab_lo, _ = ndimage.label(mask_lo)
        lab_hi, _ = ndimage.label(mask_hi)
        keep = set(np.unique(lab_lo[mask_hi]).tolist()) - {0}
        keep_arr = np.isin(lab_lo, list(keep))
        mask = keep_arr & mask_lo
    else:
        mask = mask_hi

    # light closing to merge fragments of one logical change
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    lab, n = ndimage.label(mask)
    regions = []
    if n:
        min_area = MIN_REGION_AREA
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            if sl is None:
                continue
            area = int((lab[sl] == i).sum())
            if area < min_area:
                continue
            y0, y1 = sl[0].start, sl[0].stop
            x0, x1 = sl[1].start, sl[1].stop
            # mean fused diff inside the region (signal strength)
            sub = F[sl]
            regions.append({
                "bbox_px": [int(x0), int(y0), int(x1), int(y1)],
                "area_px": area,
                "area_frac": round(area / (h * w), 5),
                "mean_diff": round(float(sub.mean()), 4),
            })
        regions.sort(key=lambda r: (-r["area_px"], -r["mean_diff"]))
        regions = regions[:MAX_REGIONS]

    # --- score ---
    # Two terms, both noise-robust:
    #  - soft energy: mean of (F - SOFT_THR)+ — diffuse sub-threshold
    #    noise (AA, JPEG blocks, sensor grain) contributes ~0, real
    #    edits contribute their excess mass.
    #  - changed fraction: share of canvas with F > FRAC_THR.
    soft_e = float(np.maximum(F - SOFT_THR, 0.0).mean())
    frac = float((F > FRAC_THR).mean())
    score = 1.0 - min(1.0, 6.0 * soft_e + 1.5 * frac)
    score = round(float(np.clip(score, 0.0, 1.0)), 4)

    notes.append(f"levels={levels}")
    notes.append(f"level_mean_diff={lvl_means}")
    notes.append(f"soft_energy={soft_e:.5f} changed_frac={frac:.5f}")
    return {
        "score": score,
        "regions": regions,
        "notes": notes,
        # extra diagnostics (harmless to the harness)
        "n_regions": len(regions),
        "align_shift_px": list(shift),
        "size": [w, h],
    }


if __name__ == "__main__":
    import sys
    r = fdiff(sys.argv[1], sys.argv[2])
    for k, v in r.items():
        print(f"{k}: {v}")
