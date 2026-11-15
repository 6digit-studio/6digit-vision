# VERDICT: anisotropy-census — CAUGHT (assigned gap)

Detector: `detectors/anisotropy-census/anisotropy_census.py` — standalone,
PEP 723 (`uv run` resolves numpy+pillow+scipy itself), no model calls,
~0.5 s/image. Consumes images only.

## Gap filled

From `evals/aspect-abuse/VERDICT.md`, instrument gaps #2 and the "what
would catch this" sketch: **no shape-fidelity measurement exists.** The
record layer erases aspect (per-axis [0,1000] normalization), Mirage
never names "ellipse", `score` can't attribute the signal (the correct
letterboxed variant scored *lower* than the defect, 36.7 vs 58.7), and
the legibility flags fire under wrong names (`low_contrast` on text that
isn't low-contrast — it's stretched). This detector is the attribution
layer the eval asked for: two model-free pixel measurements that name
the cause directly.

**Channel A — solid-blob aspect census.** Mask pixels far from the two
dominant light surfaces (page bg = border median; card = quantized mode
of interior), keep only components with a thick core (survive 2×
Chebyshev erosion — kills 1–3 px strokes: text, chart polylines,
hairlines, and *separates data dots from the lines they're drawn on*),
then cluster the survivors' bbox aspects (h/w). Designed circles/chips/
dots/avatar are drawn round by convention → isotropic render clusters at
~1.0; non-uniform resize drags the whole cluster to k = sy/sx. Cluster =
densest ±12% log-aspect window scored by member area, refined to ±8%;
fires when ≥4 members (or ≥3 covering ≥2000 px) agree within spread
≤0.30 log and |median log aspect| > 0.15. Filled rects (core_fill >0.85:
cards, buttons, pills) are candidates but not "round" witnesses — see
limits.

**Channel B — glyph-proportion census.** Luminance-ink mask (lum<200),
row-projection text bands, column-projection glyph segmentation per
band, median glyph-width/band-ink-height per line, population median
over lines (≥5 qualifying lines, ≥8 segments each — dot-rows and button
bodies can't qualify). Latin glyphs sit ~0.45–0.6 w/h; fires outside
[0.35, 0.75] per the eval sketch.

Verdicts: `anisotropic_squash` (both channels fire — corroborated),
`shape_cluster_anomalous` / `glyph_anisotropy` (one channel — candidate,
named honestly), `isotropic` (both channels measured clean),
`insufficient_witnesses` (not enough round shapes / text lines — an
honest non-answer, not a clean bill). Emits `image.size` always — the
dimension fact the record layer drops.

## Real output — defect + controls

```
$ uv run detectors/anisotropy-census/anisotropy_census.py \
    evals/aspect-abuse/defect.png evals/aspect-abuse/control.png \
    detectors/anisotropy-census/letterbox-1000.png \
    evals/theme-drift/state-a.png

evals/aspect-abuse/defect.png  1000x1000
  surfaces: bg=#eef1f5 card=#ffffff  ink_px=35939
  blob channel: 113 cores -> 34 candidates (29 round-witnesses); cluster 7 members (24% of witnesses) median aspect=1.786 spread=0.090
    bbox=(690,320)-(727,386) 38x67  aspect(h/w)=1.763  core=1562px fill=0.729 *
    bbox=(124,321)-(159,385) 36x65  aspect(h/w)=1.806  core=1430px fill=0.733 *
    bbox=(933,152)-(960,201) 28x50  aspect(h/w)=1.786  core=697px fill=0.631 *
    bbox=(675,575)-(685,593) 11x19  aspect(h/w)=1.727  core=69px fill=0.657 *
    ... (* = cluster member; members = 3 icon chips + avatar + small dots)
  glyph channel: 7 text lines, ink_px=26386, population median w/h=0.3182
    line medians: min=0.179 p25=0.229 med=0.318 p75=0.357 max=0.471
  VERDICT: ANISOTROPIC_SQUASH — CORROBORATED: solid-shape cluster at aspect 1.786 (tall) AND glyph w/h 0.318 outside Latin band — two independent channels agree on non-uniform scale

evals/aspect-abuse/control.png  1200x675
  blob channel: 38 cores -> 15 candidates (10 round-witnesses); cluster 5 members (50% of witnesses) median aspect=1.000 spread=0.000
    bbox=(148,216)-(192,260) 45x45  aspect(h/w)=1.000  core=1237px fill=0.736 *
    bbox=(828,216)-(872,260) 45x45  aspect(h/w)=1.000  core=1237px fill=0.736 *
    bbox=(1120,103)-(1152,135) 33x33  aspect(h/w)=1.000  core=426px fill=0.507 *
    bbox=(810,388)-(822,400) 13x13  aspect(h/w)=1.000  core=41px fill=0.506 *
    bbox=(914,388)-(926,400) 13x13  aspect(h/w)=1.000  core=41px fill=0.506 *
  glyph channel: 7 text lines, ink_px=19688, population median w/h=0.5833
  VERDICT: ISOTROPIC — shape cluster aspect 1.000, glyph w/h 0.583 — both channels inside isotropic bands

detectors/anisotropy-census/letterbox-1000.png  1000x1000
  blob channel: 49 cores -> 12 candidates (11 round-witnesses); cluster 4 members (36% of witnesses) median aspect=1.014 spread=0.062
    bbox=(690,399)-(727,435) 38x37  aspect(h/w)=0.974  core=817px fill=0.728 *
    bbox=(124,399)-(159,435) 36x37  aspect(h/w)=1.028  core=738px fill=0.699 *
    bbox=(933,304)-(960,332) 28x29  aspect(h/w)=1.036  core=355px fill=0.592 *
    bbox=(675,542)-(685,552) 11x11  aspect(h/w)=1.000  core=25px fill=0.51  *
  glyph channel: 7 text lines, ink_px=15182, population median w/h=0.5526
  VERDICT: ISOTROPIC — shape cluster aspect 1.014, glyph w/h 0.553 — both channels inside isotropic bands

evals/theme-drift/state-a.png  1100x760
  blob channel: 40 cores -> 15 candidates (5 round-witnesses); cluster 3 members (60% of witnesses) median aspect=0.875 spread=0.134
  glyph channel: 11 text lines, ink_px=25486, population median w/h=0.5263
  VERDICT: INSUFFICIENT_WITNESSES
```

The measured cluster aspect **1.786** vs the eval's hand measurement
1.808 on the avatar — same signature, independently derived. The
defect's `anisotropic_squash` verdict names the cause `score` could not
attribute; the letterbox — the eval's falsification probe, rebuilt
deterministically by `make_letterbox.py` (contain-fit 1000×562 into
1000×1000, 219 px bars, verified) — stays **ISOTROPIC**: uniform scale +
bars is not squash, exactly the distinction the eval demanded.

## Direction symmetry + CI mode (real output)

A wide-squash variant (control resized non-uniformly to 1680×418,
anisotropy 2.26×, `/tmp/ab_wide.png`) fires in the other direction:

```
/tmp/ab_wide.png  1680x418
  blob channel: 93 cores -> 27 candidates (19 round-witnesses); cluster 3 members (16% of witnesses) median aspect=0.458 spread=0.073
    bbox=(1159,134)-(1221,161) 63x28  aspect(h/w)=0.444  core=1028px fill=0.726 *
    bbox=(209,134)-(267,160) 59x27  aspect(h/w)=0.458  core=917px fill=0.725 *
    bbox=(1568,63)-(1613,84) 46x22  aspect(h/w)=0.478  core=454px fill=0.601 *
  glyph channel: 7 text lines, ink_px=18714, population median w/h=0.8103
  VERDICT: ANISOTROPIC_SQUASH — CORROBORATED: solid-shape cluster at aspect 0.458 (wide) AND glyph w/h 0.810 outside Latin band — two independent channels agree on non-uniform scale
```

(The three cluster members are the icon chips + avatar — the only large
solid witnesses that survived; dots-on-lines scatter under wide squash
but the corroborated verdict doesn't need them.)

```
$ uv run detectors/anisotropy-census/anisotropy_census.py \
    --fail-on-anisotropy evals/aspect-abuse/control.png \
    detectors/anisotropy-census/letterbox-1000.png   # exit 0
$ uv run detectors/anisotropy-census/anisotropy_census.py \
    --fail-on-anisotropy evals/aspect-abuse/defect.png  # exit 1
```

## Sweep — no false positives on sibling evals

All 12 other catalog images run clean or honestly inconclusive —
**zero** anisotropy flags:

| image | verdict |
|---|---|
| clipped-card/clipped.png | insufficient_witnesses (dark bg — glyph channel skips by design) |
| low-contrast control+defect | insufficient_witnesses (0 round-witness blobs) |
| ocr-hostile control | insufficient_witnesses |
| ocr-hostile defect | insufficient_witnesses |
| semantic-surprise control | insufficient_witnesses |
| text-truncation control | insufficient_witnesses |
| theme-drift state-a / state-b | insufficient_witnesses |
| z-order control | insufficient_witnesses |

State-a is the instructive near-miss: three identical 259×95 stat cards
*do* form a unanimous non-square cluster — but they're filled rects
(core_fill ~0.93 > 0.85) so they're excluded from "round" witnesses, and
the glyph channel reads a clean 0.526. The detector measured them,
classified them correctly, and stayed silent.

## Honest limits

- **Intent is not measurable.** A design that genuinely draws ovals, or
  a UI full of same-aspect pill badges, produces the same unanimous
  non-square cluster as squash. `core_fill ≤ 0.85` excludes rect-cards/
  buttons, but true oval badges remain a false-positive class — which is
  why a blob-only hit is `shape_cluster_anomalous` ("needs a reference
  or human eye"), and only blob+glyph agreement earns
  `anisotropic_squash`. The detector measures *that* shapes disagree
  with round, not *why*.
- **Glyph channel assumes Latin-ish proportions.** CJK-dominant text
  (~square glyphs, w/h ≈ 0.9–1.1), condensed/extended typefaces, or
  all-caps-wide layouts can push the population median outside
  [0.35, 0.75] and fire `glyph_anisotropy` on an honest render. Not
  observed in the 12-image sweep; unmeasured beyond it.
- **Dots fused to chart lines are distorted witnesses.** The polyline
  thickens each dot's erosion core, scattering their measured aspects
  (visible in the defect's 1.3–2.25 stragglers). The clean witnesses —
  chips, avatar, legend dots — carry the cluster; dot-heavy UIs with no
  other circles get thinner evidence.
- **Erosion biases small blobs.** Interior holes (glyphs inside chips,
  "AK" inside the avatar) and anti-aliased edges shift measured bboxes
  by ~±2 px — negligible at chip scale, visible on the smallest dots.
  This is also why `MIN_EXPANDED_DIM=6` exists.
- **Two-surface assumption.** The ink mask needs a dominant light pair
  (page bg + card). Single-surface images fall back to bg-only masking
  (still works); dark themes keep the blob channel but the glyph channel
  skips itself (border luminance <128 → `dark background` note, seen on
  clipped.png). Multi-surface designs (sidebar + content + modal)
  measure against the two most dominant only — accents on a third
  surface still mask correctly since they're far from both.
- **Insufficient witnesses is a real verdict.** Images with <3 round
  witnesses or <5 text lines get `insufficient_witnesses` — the detector
  declines rather than guesses. On this catalog that's 12/16 images;
  the aspect-abuse family is circle-rich by design, so coverage there
  is strong but not universal.
- Consumes images only — no `eyes` record/reel input. Aspect-vs-
  *intended*-aspect (the eval's sketch item 4, an `aspect` score
  component) stays a pairing concern; this detector supplies the
  anisotropy evidence such a component would need.

## Verdict

**CAUGHT.** Fires `ANISOTROPIC_SQUASH` on the eval defect with the
measured signature the eval predicted (cluster aspect 1.786 ≈ avatar's
1.808; glyph w/h 0.318 ≈ eval's 0.303), stays `ISOTROPIC` on the
correct-aspect control *and* on the rebuilt letterboxed variant — the
exact probe that broke `score`'s attribution — reads `INSUFFICIENT` on
the out-of-domain theme-drift control, and produced zero false flags
across the remaining 12 catalog images. Direction-symmetric (wide
squash corroborates at aspect 0.458), `--fail-on-anisotropy` exits 1/0
correctly, `--json` emits full per-blob and per-line detail. The
attribution gap the eval named — "nothing says *why* the legibility
flags fired" — now has a named answer: `glyph_anisotropy` /
`anisotropic_squash`, cause not symptom.
