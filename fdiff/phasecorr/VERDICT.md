# phasecorr — VERDICT

Mechanism: Kuglin-Chandrasekaran phase correlation (unnormalized-input
cross-power spectrum on luminance, unwindowed — a Hann window was tested
and *amplified* local shifts: the planted block's coherent band out-voted
the true zero shift) → integer peak + gated DTFT subpixel refinement →
Fourier-shift alignment of B → residual diff. Score =
`exp(-(10·struct_diff + 3·changed_frac))` where struct_diff is mean
|Δ| of Gaussian(σ=1.5) images (low-frequency channel — AA/compression
noise lives above it) and changed_frac is the fraction of valid pixels
with mean-channel |Δ| > 0.08. Regions = connected components of the
σ=1.2-smoothed diff map > 0.06, min area 0.05% of canvas, top 12.

## Shared bar (`tools/fdiff_bar.py`)

| criterion | score | regions | verdict |
|---|---|---|---|
| identical -> ~1.0 | **1.0** | 0 | CAUGHT — exact zero residual |
| block-shift -> localized | **0.9806** | 5 | CAUGHT — all regions inside planted band (y 299–367, x 449–771 vs planted y 300–420, x 360–780); detects the strongest-diff subregions, not the whole strip |
| 1px-translate -> low-diff | **1.0** | 0 | CAUGHT — est shift (0,+1.00), PSR 3.2e9, applied; residual exactly 0 |
| same-img sanity (control) | **1.0** | 0 | CAUGHT |
| ui1-pair signal | **0.7994** | 12 | CAUGHT — regions tile the form/heading/footer bands ([423,297,777,367] 21k px largest); pixdiff same pair: 0.8299 |

## The headline: pixdiff's documented blindness is gone

1px GLOBAL translation of dense-text pages (the case pixdiff_NOTES
calls "massive edge diffs"):

| pair | pixdiff | phasecorr |
|---|---|---|
| ui1 candidate +1px x | 0.9726, 0 reg | **1.0, 0 reg** |
| news.ycombinator +1px x | 0.7587, 6 reg | **1.0, 0 reg** |
| bbc news +1px x | 0.8790, 12 reg | **1.0, 0 reg** |

Shift estimated exactly (+1.00px, PSR ~6e9), Fourier-shifted back,
residual diff literally zero.

## Extra measurements (beyond the bar)

- **Local block shift does NOT fake a global shift**: planted 20px
  block move → est (0,0), PSR 1666 — the coherent global component
  correctly reports no translation; the local edit stays in regions.
- **Subpixel (synthetic, float)**: (+0.40,−0.70) recovered EXACTLY,
  score ~0.9998-equivalent residual. On **8-bit-quantized** inputs the
  DTFT fine peak is noise-dominated (PSR drops to ~140–470; observed
  errors up to >1px on wrong local maxima) → subpixel refinement is
  gated at PSR > 5000 and integer-only alignment applied instead.
  Honest limit: a real 0.4px global shift on 8-bit data aligns to the
  nearest integer → residual ~0.4px → score 0.934 with edge regions.
  **PARTIAL** — precise subpixel is beyond the 8-bit noise floor.
- **Eval battery** (control vs defect pairs): semantic-data 0.9944
  with the single region [518,434,541,452] landing on the totals
  amounts column (documented diff bbox 519,367,559,450) — the
  $87.50-vs-$77.50 glyph edit localized; grid-misalign 0.7065 with
  regions tracing the member-card column; web-canvas (non-uniform
  scaleX defect) 0.5897 — correctly NOT absorbable by a global shift;
  web-theme-drift gated OFF (PSR 93.5 < 100 — refused a spurious
  −60px "alignment" that would have masked the theme change);
  cross-page hn-vs-bbc 0.0315 — genuinely different images score ~0.
- **Gaussian noise** σ=0.02 on one image: score 0.965, **0 regions** —
  noise stays under PIX_THR, no false-positive localization; score
  dips honestly because the images do differ.

## Honest limitations

- **Global translation only.** Rotation, scale, non-uniform deformation
  are out of model — residual diff catches them (web-canvas 0.59) but
  nothing aligns them away. Correct scope, stated.
- **Marginal-PSR locks happen**: web-canvas applied +18px at PSR=102 —
  a weak peak locking onto the stretched chart's dominant drift. The
  score still flagged the defect (0.59 vs 0.60 ungated) — spurious
  alignment errs toward *more* diff, the conservative direction, but
  it is not clean. PSR_GATE=100 was kept over 300+ because degraded
  real translations (quantized subpixel, PSR~140–470) still carry
  correct integer peaks that a higher gate would forfeit entirely.
- **Score is fidelity, not correctness** — same caveat as pixdiff: a
  color swap preserving layout diffs in `d` (mean-channel |Δ|) and is
  caught (synthetic 200×60 swap → 0.9157, exact bbox), but "same
  pixels?" ≠ "same intent?".
- Different input sizes: B is bilinear-resized to A's canvas — crude
  for large aspect differences, exact for the equal-size cases tested.
- Runtime ~0.1–0.3 s/pair at 1200×800 (three 2D FFTs + DTFT matmuls +
  alignment FFTs + gaussian channels).

## Reproduce

```
uv run python3 tools/fdiff_bar.py fdiff/phasecorr/fdiff.py
```
