"""fft-lowband fdiff — FFT magnitude low-band structure diff.

Mechanism: transform both images to the frequency domain (numpy.fft.fft2
on grayscale), keep only low-frequency coefficients — the structure
carrier — and compare magnitude spectra. High-frequency content (AA
edges, compression noise, subpixel text jitter) is discarded by the
low-pass itself. A pure translation changes only phase, not magnitude,
so a global 1px shift produces ~zero diff.

Localization: the low-band coefficients are inverse-transformed into a
smoothed "structure image" per side; the spatial residual of those is
downsampled, thresholded, and connected-componented into pixel bboxes.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

# Low-band radius as a fraction of the shorter image dimension, in FFT
# bins. ~8% of 800px -> ~64 bins: captures block/card-scale structure,
# rejects glyph-edge and compression band.
LOW_BAND_FRAC = 0.08
# Spatial-residual grid downsample factor.
GRID = 8
# Connected-component threshold: residual must exceed this many robust
# sigmas above the grid median.
SIGMA_K = 6.0
MIN_COMPONENT_CELLS = 4  # on the downsampled grid
MAX_REGIONS = 24


def _load_gray(path):
    return np.asarray(Image.open(path).convert("L"), dtype=np.float64)


def _common_canvas(a, b):
    """Pad both to (maxH, maxW) with edge values -> common canvas."""
    h = max(a.shape[0], b.shape[0])
    w = max(a.shape[1], b.shape[1])
    out = []
    for img in (a, b):
        p = np.pad(img,
                   ((0, h - img.shape[0]), (0, w - img.shape[1])),
                   mode="edge")
        out.append(p)
    return out[0], out[1]


def _lowband_mask(shape, frac):
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    fy = (np.arange(h) - cy) / h  # cycles per pixel, centered
    fx = (np.arange(w) - cx) / w
    # radius in FFT bins: freq(in bins) = fy * h
    r = np.sqrt((fy[:, None] * h) ** 2 + (fx[None, :] * w) ** 2)
    return r <= frac * min(h, w)


def fdiff(a_path, b_path):
    notes = []
    a = _load_gray(a_path)
    b = _load_gray(b_path)
    a, b = _common_canvas(a, b)
    h, w = a.shape

    # Frequency domain: magnitude spectra of mean-centered images.
    fa = np.fft.fftshift(np.fft.fft2(a - a.mean()))
    fb = np.fft.fftshift(np.fft.fft2(b - b.mean()))
    ma = np.abs(fa)
    mb = np.abs(fb)

    mask = _lowband_mask(a.shape, LOW_BAND_FRAC)
    n_low = int(mask.sum())
    notes.append(f"canvas={w}x{h} lowband_bins={n_low} "
                 f"(r<={LOW_BAND_FRAC * min(h, w):.0f})")

    # --- score: relative L1 distance of low-band magnitude spectra ---
    da = ma[mask]
    db = mb[mask]
    denom = float(da.sum() + db.sum())
    rel_l1 = float(np.abs(da - db).sum() / denom) if denom > 0 else 0.0
    # rel_l1 ~ 0 identical -> score ~1.0; saturating-ish map.
    score = float(np.clip(1.0 - 2.5 * rel_l1, 0.0, 1.0))
    notes.append(f"lowband_mag_rel_l1={rel_l1:.4f}")

    # --- localization: residual of low-band reconstructions ---
    low_a = np.real(np.fft.ifft2(np.fft.ifftshift(fa * mask)))
    low_b = np.real(np.fft.ifft2(np.fft.ifftshift(fb * mask)))

    # Cheap integer global alignment on the band-limited images: a pure
    # translation is invisible to the magnitude score but would still
    # light up the spatial residual at strong low-freq gradients.
    # Cross-correlation peak gives the integer lag; roll b to compensate.
    ca = np.fft.fft2(low_a - low_a.mean())
    cb = np.fft.fft2(low_b - low_b.mean())
    xcorr = np.real(np.fft.ifft2(ca * np.conj(cb)))
    py, px = np.unravel_index(np.argmax(xcorr), xcorr.shape)
    sy = py if py <= h // 2 else py - h
    sx = px if px <= w // 2 else px - w
    if sy != 0 or sx != 0:
        # xcorr lag == shift of b relative to a; rolling b by the lag
        # itself realigns (verified: roll(b, lag) reproduces a).
        low_b = np.roll(low_b, (sy, sx), axis=(0, 1))
        notes.append(f"integer_align lag=({sy},{sx})")

    resid = np.abs(low_a - low_b)

    # Downsample residual to grid, robust threshold, CC bboxes.
    gh = h // GRID
    gw = w // GRID
    grid = resid[: gh * GRID, : gw * GRID].reshape(gh, GRID, gw, GRID).mean(axis=(1, 3))
    med = float(np.median(grid))
    mad = float(np.median(np.abs(grid - med))) * 1.4826
    thr = med + SIGMA_K * max(mad, 1e-9)
    regions = []
    if thr > med:  # only if there is any spread above noise
        lab, n = ndimage.label(grid > thr)
        objs = ndimage.find_objects(lab)
        cands = []
        for i, sl in enumerate(objs, start=1):
            if sl is None:
                continue
            area = int((lab[sl] == i).sum())
            if area < MIN_COMPONENT_CELLS:
                continue
            y0, y1 = sl[0].start, sl[0].stop
            x0, x1 = sl[1].start, sl[1].stop
            mass = float(grid[sl][lab[sl] == i].sum())
            cands.append((mass, x0, y0, x1, y1))
        cands.sort(reverse=True)
        for mass, x0, y0, x1, y1 in cands[:MAX_REGIONS]:
            regions.append({
                "x": int(x0 * GRID), "y": int(y0 * GRID),
                "w": int((x1 - x0) * GRID), "h": int((y1 - y0) * GRID),
                "mass": round(mass, 3),
            })
    notes.append(f"grid={gw}x{gh} thr={thr:.3f} med={med:.3f} "
                 f"regions={len(regions)}")

    return {"score": score, "regions": regions, "notes": notes}
