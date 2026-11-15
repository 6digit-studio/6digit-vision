# VERDICT — fft-lowband

Mechanism: `numpy.fft.fft2` magnitude spectra of mean-centered grayscale,
hard low-pass at radius `0.08 * min(H,W)` FFT bins (~64 bins on the
1200x800 bar images). Score = `clip(1 - 2.5 * relL1, 0, 1)` over low-band
magnitudes. Regions = connected components (8px grid, 6 robust-sigma
threshold) of the spatial residual between low-band reconstructions,
after cheap integer global realignment via cross-correlation.

Bar run: `uv run python3 tools/fdiff_bar.py fdiff/fft-lowband/fdiff.py`

| criterion | score | regions | verdict |
|---|---|---|---|
| identical -> ~1.0 | 1.0 | 0 | CAUGHT |
| block-shift -> localized | 0.7512 | 5 | CAUGHT |
| 1px-translate -> low-diff | ~1.0 | 0 | CAUGHT |
| same-img sanity | 1.0 | 0 | CAUGHT |
| ui1-pair signal | 0.3720 | 5 | CAUGHT |

## Per-criterion detail

1. **identical -> ~1.0 — CAUGHT.** score exactly 1.0, zero regions.
   `lowband_mag_rel_l1 = 0`.

2. **block-shift -> localized — CAUGHT.** score 0.7512
   (`rel_l1 = 0.0995`). Dominant region `{x:392, y:184, w:424, h:320}`,
   mass 4927.6 vs <=4.4 for the four satellite regions — a ~1000x
   dominance ratio. Planted change was `b[300:420, 380:780] =
   a[300:420, 360:760]` (content shifted +20px inside a 400x120 band).
   The dominant bbox covers the changed band in y fully and x from 392
   to 816 — it clips ~12px on the band's left edge (x380-392) and is
   ~2.7x taller than the planted block. That inflation is inherent:
   localization comes from the low-band reconstruction, whose spatial
   resolution is structure-scale (~1/64 of the image), not pixel-scale.
   Honest scope: coarse localization, unambiguous neighborhood.

3. **1px-translate -> low-diff — CAUGHT, the mechanism's core claim.**
   score 0.9999999999999999, `rel_l1 = 0.0000` — a cyclic 1px roll
   changes FFT phase only, never magnitude, so the score is
   translation-invariant by construction. Before realignment the
   spatial residual still showed edge-gradient response (3 regions,
   max mass 2255); the integer cross-correlation realignment
   (detected lag `(0,-1)`, correct direction verified numerically)
   drives residual to exactly 0 -> 0 regions. This is the channel
   pixdiff is blind to; here it is silent on both score and regions.

4. **dense-text AA/compression noise -> low false-positive — CAUGHT
   (score), honest note on regions.** The bar row itself is an
   identical pair (1.0 / 0). Probes beyond the bar, candidate.png vs:
   - Gaussian noise sigma=3: score 0.979, **0 regions** at K=6.
   - JPEG q70 re-encode: score 0.9892, 4 regions — one diffuse bbox
     `{x:400, y:0, w:384, h:416}` mass 382 plus three mass<0.2 specks.
     JPEG q70 does perturb low-frequency DCT coefficients, so this is
     a real (if diffuse) low-band change, not a false positive of the
     detector; score stays >=0.989.
   - JPEG q50: score ~0.988.
   - Cross-page sanity (should diff hard): github login vs HN front
     page 0.0888, vs Mozilla dev page 0.0592 — score is not stuck
     mid-range; dynamic range is real.

5. **ui1-pair signal — CAUGHT.** score 0.3720 (`rel_l1 = 0.2512`),
   5 regions. Realignment found a genuine 1px vertical offset between
   the reference render and the candidate (lag `(1,0)`) — exactly the
   subpixel/render jitter that produces massive edge diffs in spatial
   diff. After compensation the residual localizes to a dominant
   region `{x:408, y:0, w:384, h:416}` mass ~40.0k (top content area)
   and a full-width footer strip `{x:0, y:752, w:1200, h:48}` mass
   ~10.8k, plus three sub-0.1% specks. Whether the dominant region
   corresponds to the specific fine edit the challenge refers to is
   unverified — I did not visually confirm which pixels changed — but
   the low-band channel produces a strong, localized, alignment-robust
   signal where the semantic score saw only jitter.

## Known limits

- Localization is structure-scale: bboxes are ~2-3x the true change
  extent vertically/horizontally because the low-pass reconstruction
  smears. Fine-grained "which glyph changed" is out of scope by design.
- Score saturates: any rel_l1 > ~0.4 maps to 0; cross-page pairs land
  at 0.06-0.09, so the useful discrimination band is roughly 0.3-1.0.
- Integer-only alignment (no subpixel); subpixel misalignment residual
  is absorbed by the 6-sigma threshold on these images.
- Magnitude discards phase entirely: a change that preserves the
  magnitude spectrum (rare — e.g. pure phase scrambles) is invisible.
  Not observed on the bar.
