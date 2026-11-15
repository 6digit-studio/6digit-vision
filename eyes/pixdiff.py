"""pixdiff — pixel-level image diff: SSIM map + AA-aware change regions.

The fine-edit channel semantic score can't provide: Mirage object
jitter floors objects/layout components at ~.35-.52 on near-identical
UI renders, so a 1-5pt edit signal drowns. Pixel diff has no such
floor — identical images score ~1.0, a moved button localizes to its
bbox.

Two complementary measurements:
- SSIM (structural): local mean-SSIM over gaussian windows — catches
  luminance/contrast/structure shifts, robust to small translations.
- pixelmatch-style mask: per-pixel color delta vs luminance-scaled
  threshold with anti-aliasing suppression — catches hard edges,
  text changes, color swaps that SSIM smooths over.

Output: scalar score, changed-pixel fraction, localized change
regions (connected components), and a coarse heat grid for packs.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage


def _prep(a, b, max_dim: int = 800):
    """Load both to float RGB arrays at a common size."""
    ia = Image.open(str(a)).convert("RGB")
    ib = Image.open(str(b)).convert("RGB")
    w, h = ia.size
    if ib.size != ia.size:
        ib = ib.resize(ia.size, Image.BILINEAR)
    scale = min(1.0, max_dim / max(w, h))
    if scale < 1.0:
        nw, nh = max(8, int(w * scale)), max(8, int(h * scale))
        ia = ia.resize((nw, nh), Image.BILINEAR)
        ib = ib.resize((nw, nh), Image.BILINEAR)
    return (np.asarray(ia, dtype=np.float32) / 255.0,
            np.asarray(ib, dtype=np.float32) / 255.0)


def _ssim_map(x: np.ndarray, y: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """Local SSIM on grayscale, gaussian-weighted 7x7-ish window."""
    gx = ndimage.gaussian_filter(x, sigma)
    gy = ndimage.gaussian_filter(y, sigma)
    gx2 = ndimage.gaussian_filter(x * x, sigma)
    gy2 = ndimage.gaussian_filter(y * y, sigma)
    gxy = ndimage.gaussian_filter(x * y, sigma)
    mx, my = gx, gy
    vx = np.maximum(gx2 - gx * gx, 0.0)
    vy = np.maximum(gy2 - gy * gy, 0.0)
    cov = gxy - gx * gy
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    num = (2 * mx * my + c1) * (2 * cov + c2)
    den = (mx * mx + my * my + c1) * (vx + vy + c2)
    return num / np.maximum(den, 1e-12)


def _lum(img: np.ndarray) -> np.ndarray:
    return 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]


def pixdiff(a, b, max_dim: int = 800) -> dict:
    A, B = _prep(a, b, max_dim)
    h, w = A.shape[:2]
    ga, gb = _lum(A), _lum(B)

    # --- SSIM channel ---
    smap = _ssim_map(ga, gb)
    ssim_mean = float(smap.mean())

    # --- pixelmatch-style channel ---
    # per-pixel max channel delta; AA suppression: a pixel counts as
    # changed only if its delta beats a luminance-scaled threshold —
    # anti-aliased edges have small deltas proportional to local
    # luminance gradient, hard edits don't.
    delta = np.abs(A - B).max(axis=2)
    lum = np.maximum(_lum(A), _lum(B))
    thr = 0.1 + 0.02 * lum  # blending threshold ~ pixelmatch's
    changed = delta > thr
    # suppress isolated single-pixel noise: require a changed neighbor
    if changed.any():
        kernel = np.ones((3, 3), bool)
        kernel[1, 1] = False
        has_nb = ndimage.convolve(changed.astype(np.int32),
                                  kernel.astype(np.int32)) > 0
        changed = changed & has_nb
    mismatch = float(changed.mean())

    # --- localized regions ---
    lab, n = ndimage.label(changed)
    regions = []
    if n:
        objs = ndimage.find_objects(lab)
        min_px = max(4, int(0.0002 * h * w))
        for i, sl in enumerate(objs, 1):
            if sl is None:
                continue
            area = int((lab[sl] == i).sum())
            if area < min_px:
                continue
            y0, y1 = sl[0].start, sl[0].stop
            x0, x1 = sl[1].start, sl[1].stop
            regions.append({
                "bbox_px": [int(x0), int(y0), int(x1), int(y1)],
                "area_px": area,
                "area_frac": round(area / (h * w), 5),
            })
        regions.sort(key=lambda r: -r["area_px"])
        regions = regions[:12]

    # --- heat grid (coarse diff magnitude for packs) ---
    mag = np.clip(delta / 0.5, 0, 1)
    gh, gw = 24, 32
    ys = np.linspace(0, h, gh + 1).astype(int)
    xs = np.linspace(0, w, gw + 1).astype(int)
    heat = [[round(float(mag[ys[r]:ys[r + 1], xs[c]:xs[c + 1]].mean()), 3)
             for c in range(gw)] for r in range(gh)]

    score = round(0.6 * ssim_mean + 0.4 * (1.0 - min(mismatch * 8, 1.0)), 4)
    return {
        "score": score,
        "ssim_mean": round(ssim_mean, 4),
        "mismatch_frac": round(mismatch, 5),
        "n_regions": len(regions),
        "regions": regions,
        "heat": heat,
        "size": [w, h],
        "notes": [],
    }


def main() -> int:
    import argparse, json, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = pixdiff(args.a, args.b)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"pixdiff score={r['score']} ssim={r['ssim_mean']} "
              f"mismatch={r['mismatch_frac']} regions={r['n_regions']}")
        for reg in r["regions"][:6]:
            print(f"  {reg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
