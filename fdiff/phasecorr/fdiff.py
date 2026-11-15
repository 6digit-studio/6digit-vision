"""phasecorr — frequency-domain image diff: phase-correlation alignment
+ residual diff (Kuglin-Chandrasekaran cross-power spectrum).

Mechanism
---------
1. Estimate the GLOBAL translation between the two images from the
   phase of the FFT cross-power spectrum: if B is A shifted by s,
   then conj(Fa)*Fb has phase exp(-2pi i k.s); the inverse FFT of the
   normalized cross-power spectrum is a delta at s. Subpixel refinement
   evaluates the same DTFT on a fine offset grid around the integer
   peak via two small matrix multiplies (no per-point FFTs).
2. The estimate is only applied when the correlation peak stands above
   the sidelobe floor (PSR gate). A weak peak means there is no
   coherent global translation — the argmax is noise and "aligning" by
   it would inject artificial misalignment (this is what keeps local
   edits, e.g. a moved block, from being "corrected" into a fake global
   shift).
3. B is shifted back by the estimated (subpixel) translation with the
   Fourier shift theorem — exact for any shift, no resampling blur.
   Wrapped edge bands are masked out of every statistic.
4. Residual diff on the aligned pair: per-pixel mean |RGB delta| for
   localization, plus a Gaussian-low-passed structural channel so
   AA/compression noise (which lives in high frequencies) does not
   dominate the score.

Score = exp(-(W_STRUCT * mean_struct_diff + W_FRAC * changed_frac))
-> 1.0 for identical, decays smoothly with structural change and the
fraction of pixels carrying a hard delta.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

# --- tunables (calibrated on the shared bar; see VERDICT.md) ---
PSR_GATE = 100.0        # min peak/sidelobe ratio to trust ANY shift
SUBPIXEL_PSR = 5000.0   # min PSR to trust the DTFT subpixel refinement;
                        # below this the fine peak is noise-dominated
                        # (8-bit quantization alone drops PSR to ~500)
PIX_THR = 0.08          # per-pixel mean-channel delta -> "changed"
REG_THR = 0.06          # smoothed-diff threshold for region mask
REG_SMOOTH = 1.2        # sigma for region-mask smoothing
STRUCT_SIGMA = 1.5      # sigma for the low-pass structural channel
W_STRUCT = 10.0         # score weight on mean structural diff
W_FRAC = 3.0            # score weight on changed-pixel fraction
MAX_REGIONS = 12
MIN_REGION_FRAC = 0.0005


def _load(path, size=None) -> np.ndarray:
    im = Image.open(str(path)).convert("RGB")
    if size is not None and im.size != size:
        im = im.resize(size, Image.BILINEAR)
    return np.asarray(im, dtype=np.float32) / 255.0


def _lum(x: np.ndarray) -> np.ndarray:
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def _dtft_peak(R: np.ndarray, iy: int, ix: int, h: int, w: int,
               oy_grid: np.ndarray, ox_grid: np.ndarray):
    """|sum_k R[k] exp(2pi i (fy*y + fx*x))| on a grid of pixel offsets
    around integer peak (iy,ix), via two small matmuls.

    R is the normalized cross-power spectrum (h x w, fft2 ordering).
    Returns (best_oy, best_ox, best_value).
    """
    fy = np.fft.fftfreq(h)[:, None]                    # h x 1
    fx = np.fft.fftfreq(w)[:, None]                    # w x 1
    A = np.exp(2j * np.pi * fy * (iy + np.asarray(oy_grid)[None, :]))
    B = np.exp(2j * np.pi * fx * (ix + np.asarray(ox_grid)[None, :]))
    T = R @ B                                          # h x n_ox
    C = np.abs(A.T @ T)                                # n_oy x n_ox
    oi, oj = np.unravel_index(np.argmax(C), C.shape)
    return float(oy_grid[oi]), float(ox_grid[oj]), float(C[oi, oj])


def _phase_corr(a: np.ndarray, b: np.ndarray) -> dict:
    """Kuglin-Chandrasekaran phase correlation on luminance.

    Returns estimated shift s with B(x) ~ A(x - s): dy, dx (subpixel),
    integer peak, and PSR = peak / mean(sidelobes).
    """
    ga, gb = _lum(a), _lum(b)
    h, w = ga.shape
    Fa = np.fft.fft2(ga)
    Fb = np.fft.fft2(gb)
    R = np.conj(Fa) * Fb
    R /= np.abs(R) + 1e-12
    r = np.abs(np.fft.ifft2(R))
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    dy_i = iy if iy <= h // 2 else iy - h
    dx_i = ix if ix <= w // 2 else ix - w

    # PSR: peak over mean of the correlation surface with an 11x11
    # exclusion around the peak.
    m = r.copy()
    y0, y1 = max(0, iy - 5), min(h, iy + 6)
    x0, x1 = max(0, ix - 5), min(w, ix + 6)
    m[y0:y1, x0:x1] = 0.0
    psr = float(r[iy, ix] / (m.mean() + 1e-12))

    # Subpixel refinement: the integer peak is within 0.5px of the true
    # shift; evaluate the DTFT on +-0.5 (0.05 step) then polish +-0.05
    # (0.01 step). Only when the peak is clean enough — on 8-bit inputs
    # quantization noise drops PSR to ~500 and the fine peak jumps to
    # wrong local maxima (>1px error observed); integer-only is safer.
    dy_s = dx_s = None
    if psr > SUBPIXEL_PSR:
        oy, ox, _ = _dtft_peak(R, iy, ix, h, w,
                               np.arange(-0.5, 0.51, 0.05),
                               np.arange(-0.5, 0.51, 0.05))
        oy, ox, _ = _dtft_peak(R, iy, ix, h, w,
                               np.arange(oy - 0.05, oy + 0.051, 0.01),
                               np.arange(ox - 0.05, ox + 0.051, 0.01))
        dy_s, dx_s = oy, ox

    if dy_s is None:
        dy, dx = float(dy_i), float(dx_i)
    else:
        dy, dx = float(dy_i + dy_s), float(dx_i + dx_s)
    return {"dy": dy, "dx": dx, "dyi": int(dy_i), "dxi": int(dx_i),
            "psr": psr, "subpix": dy_s is not None}


def _shift_img(img: np.ndarray, ty: float, tx: float) -> np.ndarray:
    """Fourier shift theorem: out(x) = img(x - (ty,tx)) — content moves
    by +(ty,tx). Exact for integer and subpixel shifts."""
    h, w = img.shape[:2]
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.fftfreq(w)[None, :]
    ph = np.exp(-2j * np.pi * (ky * ty + kx * tx))
    out = np.empty_like(img)
    for c in range(img.shape[2]):
        out[..., c] = np.real(np.fft.ifft2(np.fft.fft2(img[..., c]) * ph))
    return out


def _regions(d: np.ndarray, valid: np.ndarray) -> list[dict]:
    """Connected components of the smoothed diff map -> change bboxes."""
    ds = ndimage.gaussian_filter(d, REG_SMOOTH)
    mask = (ds > REG_THR) & valid
    h, w = d.shape
    lab, n = ndimage.label(mask)
    min_px = max(6, int(MIN_REGION_FRAC * h * w))
    regs = []
    if n:
        for i, sl in enumerate(ndimage.find_objects(lab), 1):
            if sl is None:
                continue
            area = int((lab[sl] == i).sum())
            if area < min_px:
                continue
            regs.append({
                "bbox_px": [int(sl[1].start), int(sl[0].start),
                            int(sl[1].stop), int(sl[0].stop)],
                "area_px": area,
                "area_frac": round(area / (h * w), 5),
            })
    regs.sort(key=lambda r: -r["area_px"])
    return regs[:MAX_REGIONS]


def fdiff(a_path, b_path) -> dict:
    A = _load(a_path)
    B = _load(b_path, size=A.shape[1::-1])  # common canvas = A's size
    h, w = A.shape[:2]

    pc = _phase_corr(A, B)
    applied = pc["psr"] >= PSR_GATE
    sdy, sdx = (pc["dy"], pc["dx"]) if applied else (0.0, 0.0)

    # B(x) ~ A(x - s); aligned B_al(x) = B(x + s) = shift by -s.
    if sdy == 0.0 and sdx == 0.0:
        B_al = B
    else:
        B_al = _shift_img(B, -sdy, -sdx)

    # Mask the wrap-around band the Fourier shift leaves at the borders.
    m = int(np.ceil(max(abs(sdy), abs(sdx)))) + 2
    valid = np.ones((h, w), bool)
    valid[:m, :] = False
    valid[-m:, :] = False
    valid[:, :m] = False
    valid[:, -m:] = False
    if not valid.any():          # degenerate: shift swallows whole canvas
        valid[:, :] = True

    # --- residual diff ---
    d = np.abs(A - B_al).mean(axis=2)              # 0..1 per-pixel delta
    dv = d[valid]

    # structural (low-frequency) channel: noise-robust score term
    A_l = ndimage.gaussian_filter(A, (STRUCT_SIGMA, STRUCT_SIGMA, 0))
    B_l = ndimage.gaussian_filter(B_al, (STRUCT_SIGMA, STRUCT_SIGMA, 0))
    dl = np.abs(A_l - B_l).mean(axis=2)
    struct_mean = float(dl[valid].mean())

    frac = float(np.mean(dv > PIX_THR))
    score = float(np.exp(-(W_STRUCT * struct_mean + W_FRAC * frac)))

    regions = _regions(d, valid)

    sub_note = ("subpixel refinement applied" if pc["subpix"] else
                "integer-only (PSR below subpixel gate — fine peak "
                "noise-dominated)" if applied else "n/a")
    notes = [
        f"phase-corr shift est=({pc['dy']:+.2f},{pc['dx']:+.2f})px "
        f"int=({pc['dyi']},{pc['dxi']}) psr={pc['psr']:.1f} [{sub_note}]",
        ("global alignment APPLIED" if applied else
         "alignment SKIPPED: peak below PSR gate — no coherent global "
         "translation, argmax treated as noise"),
        f"residual: mean_delta={float(dv.mean()):.5f} "
        f"struct_diff={struct_mean:.5f} changed_frac={frac:.5f} "
        f"(thr={PIX_THR})",
    ]

    return {
        "score": round(score, 4),
        "regions": regions,
        "notes": notes,
        "shift": {
            "estimated": [round(pc["dy"], 3), round(pc["dx"], 3)],
            "applied": [round(sdy, 3), round(sdx, 3)],
            "integer_peak": [pc["dyi"], pc["dxi"]],
            "psr": round(pc["psr"], 1),
            "subpixel": pc["subpix"],
            "applied_ok": applied,
        },
        "struct_diff": round(struct_mean, 5),
        "changed_frac": round(frac, 5),
        "mean_delta": round(float(dv.mean()), 5),
        "size": [w, h],
        "n_regions": len(regions),
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
        print(f"fdiff score={r['score']} regions={r['n_regions']} "
              f"shift={r['shift']}")
        for reg in r["regions"][:6]:
            print(f"  {reg}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
