# nonuniform-scale — detector verdict

Spec: text-like row bands (6-20px, >=4 glyph column-runs) -> per-band
median(segment_width)/band_height -> population median. Horizontal
stretch inflates glyph w/h toward 1.0; isotropic sans text ~0.5-0.75.

## Why it exists

web-canvas eval MISS: CSS scaleX(1.35) on canvas was invisible —
anisotropy glyph channel needs >=5 text lines, canvas has 1. This
detector works on FEW witnesses: any qualifying band contributes.

## Results

| image | verdict | pop w/h |
|-------|---------|---------|
| web-canvas/defect (scaleX 1.35) | **scale_suspect** | 0.900 |
| web-canvas/control | isotropic | 0.650 |
| HN / BBC / Wikipedia | isotropic | 0.467-0.55 |
| github / MDN / example.com | insufficient_witnesses | — |
| web-breakpoint pair | isotropic | 0.571 / 0.619 |

Measured gap: isotropic corpus max 0.65 vs defect 0.90 — threshold
0.85 sits in real separation. Honest scope: candidate-level (single
band = thin evidence); fires as scale_suspect not definitive squash.
The 1.35x inflation factor recovered almost exactly (0.65->0.90).

## Corroboration attempt — measured stall, documented honestly

Commissioned to upgrade scale_suspect candidate->verified via a second
independent witness. Analysis: intra-canvas ratios are scale-invariant
(uniform stretch preserves bar/gap/text proportions) — the only absolute
priors are glyph-shape (channel 1, shipped) and corner-circularity
(rx~ry for border-radius). Corner probe measured: canvas #fff on
#f8fafc page is a ~2% luminance step — below cheap threshold detection;
needs edge-aware segmentation (Canny-class), disproportionate for a
candidate-level signal. scale_suspect stays single-witness BY DESIGN:
it's a review flag, not a verdict — same tier as motion-coherence's
honest PARTIAL. Named future channel: corner-ellipticity via real edge
detection, or DOM-corner analysis when the stretched element is DOM
(not canvas — DOM corners ARE detectable via objects_at_edge geometry).
