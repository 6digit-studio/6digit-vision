# web-real — first real-backend eval: do detector floors hold outside synthetic PIL?

First eval class rendered by a REAL backend: headless Chrome
(`--screenshot`, real font rasterization, subpixel anti-aliasing,
compositor) instead of PIL `ImageDraw`. Three 1200×800 captures from
local HTML — control, low-contrast, misalign — built 2026-11-15.

## Verdicts

| case | instrument | +reasoning | verdict |
|------|-----------|------------|---------|
| low-contrast | **CAUGHT** | — | legibility flags fire on real render |
| control | **FALSE POSITIVE** | — | clean render flagged low_contrast ×2 |
| misalign | MISS | — | 3–12px CSS drift invisible to wired detectors |

## The headline finding: legibility floor miscalibrated for real text

`eyes layout --describe` on the CLEAN control reports:

```
'Revenue overview -Q3 2025'  contrast 2.11  ocr_score 0.363
    flags: low_contrast + low_ocr_confidence
'Vlew detalls'               contrast 2.46  ocr_score 0.710
    flags: low_contrast
```

Both are perfectly legible text (#6b7280 on white ≈ 4.8:1; white on
#2563eb ≈ 5.2:1). The defect case fires correctly — but it fires on
control too, which means **the contrast estimator's floor does not
transfer from synthetic PIL text to real rasterized text**. Likely
cause: real 12–14px anti-aliased strokes are thinner relative to the
bbox than PIL's bold synthetic text; the 2nd/98th-percentile local
sampling dilutes ink further → contrast reads ~2 instead of ~5.

This is exactly what the real-backend wave exists to find: every prior
eval floor was calibrated on PIL art. The detector is not wrong that
contrast is low *as measured* — the measurement itself needs a
stroke-density correction or a smaller sampling window for small text.

## Secondary findings

- **Real-render OCR is noisier**: `'Vlew detalls'` (l→I, i→l) at 0.71,
  `'-Q3'` hyphen artifact at 0.36. lexical-screen's OOV channel would
  flag `detalls` — real text produces lossy-OCR non-words the synthetic
  catalog never showed. Documented limitation territory.
- **misalign MISS is structural, not noise**: cards carry unique labels
  (Revenue/Users/NPS) so the text-census can't group repeated strings;
  the pixel_edges channel that measured avatar/pill spreads on the
  synthetic case exists in detectors/edge-census/ but is NOT wired into
  ask packs — only the text census is. 3–12px drift is also near the
  measured floor.

## What would fix it (queued, not built)

1. legibility: stroke-density-aware contrast — weight samples by ink
   probability or sample within glyph cores rather than the whole bbox.
2. edge-census: wire pixel_edges into ask packs for icon/shape drift.
3. Recalibrate every detector floor on a real-render corpus — this eval
   is the first data point that floors don't transfer.

## Fix landed 2026-11-15 — root cause was color space, not sampling

The false positive traced to WCAG math, not stroke dilution: the
estimator used PIL `convert("L")` non-linear luma. WCAG contrast is
defined on LINEAR-light sRGB — `legibility.py` now computes per-pixel
linear luminance (`_lin` channel transfer + Rec.709 luma) before
percentiles.

Post-fix verification:
- control 'Revenue overview': contrast **2.11 -> 4.83** (true WCAG for
  #6b7280-on-white is ~4.8) — `low_contrast` flag gone; residual
  `low_ocr_confidence` is honest (OCR genuinely scored 0.363 on the
  '-Q3' artifact string)
- low-contrast defect: still fires at **1.47** — true positive preserved
- synthetic low-contrast eval: 3 flags, unchanged
- 30 tests green

## Update 2 — pixel_edges wired into ask packs

`pixel_edge_drift` now surfaces in ask packs alongside `edge_census`.
Verified: grid-misalign defect FLAGGED (edge_drift, anchored_spread
9px across 7 bands), both controls CLEAN. Honest residual: web-real
misalign stays CLEAN — its margin-top drift pattern doesn't form the
uniform-width multi-band clusters the detector keys on; real-layout
drift detection remains partially dark. 30 tests green.

## Update 3 — real-page floor sweep (uncontrolled content)

Two live captures: example.com + Wikipedia main page (headless Chrome,
real DOM/CSS/fonts — not our HTML).

| detector | example.com | Wikipedia |
|----------|------------|-----------|
| objects_at_edge | clean | 6 suspects — nav controls genuinely at frame edges (honest facts, scores 0.30-0.49) |
| legibility | clean | **0 low_contrast on dense real text** — linear-light fix holds |
| edge_bisect | **FALSE POSITIVE** — 'Learn more' flagged: link underline IS an edge line 2px from ink | clean |
| edge_census / pixel_edges | clean | clean |

New FP class catalogued: **underlined links read as bisected text**.
The slice signature (edge through glyph mid-section) and underline
(edge just below descender line) are separable — fix is a line-position
vs ink-band check, queued not built. Everything else held: the
linear-light legibility fix survived uncontrolled real text, and the
edge-object suspect flags on Wikipedia are true facts about real UI.
