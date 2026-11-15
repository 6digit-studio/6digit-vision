# VERDICT: edge-bisect — CAUGHT (assigned gap), both axes, 12-image control sweep clean

Detector: `detectors/edge-bisect/edge_bisect.py` — standalone, runs under
the project env (`uv run` from repo root; imports `eyes.color.denorm`,
calls `eyes.mirage.describe` unless `--record` supplies saved JSON).
No PEP 723 header on purpose: the script needs the project env for
`eyes`/`cactus`; ~1–4 s/image depending on Mirage cache.

## Gap filled

From `evals/z-order/VERDICT.md`, instrument gap #1: *"a text bbox
bisected by an interior edge line ('n..Eaakn' px-y 224–241 vs card-2 top
edge y=237)... `text_edge_flush` only checks bbox edges landing ON lines —
it never checks a line cutting through a bbox's interior."* The eval's
sketch assumed `interior_edge_lines` would supply the candidate lines —
on this artifact it returns **zero lines** (verified: the 1–2 px card
border at y=237 is below `min_strength=30` on the 256 px analysis canvas,
and on the control the same edge is hidden behind the menu). So the
detector does not reuse the global row/column profile at all; it works
**per text bbox on full-resolution pixels**:

For every Mirage `text` bbox (denormed to px), scan every row/column
transition strictly inside the bbox (2 px inset) on both axes. A cut
qualifies only when ALL hold:

- **coverage ≥ 0.80** — ≥80% of the span's columns/rows step ≥18 gray
  levels (a coherent surface edge, not glyph texture: best non-defect
  coverage anywhere in the sweep was 0.73 on clipped.png calendar digits)
- **median step ≥ 15** and **flat_frac ≥ 0.85 on BOTH sides** — each side
  of the cut is a flat surface (±10 gray of its median). Glyph rows are
  textured (flat_frac 0.0–0.6); the defect's border-band exit row scores
  1.00/1.00
- **within INK_K=6 px of the ink band** — ink = |px − crop-median| > 45,
  positions inked ≥70% of the span excluded as solid foreign bands (rules,
  borders). Kills divider-in-bbox-padding FPs
- **ink on at most ONE side** (≥2 positions AND ≥12 px each side to
  count) — substantial ink both sides = edge *between* two content
  populations, not a slice of one glyph run
- **dense cut-adjacent ink edge** — the band's edge nearest the cut must
  carry ≥50% of peak ink count in its last 2 positions: a mid-stroke
  slice leaves dense ink at the cut (defect: 37–38 vs peak 38); a natural
  glyph edge tapers (control 'Duplicate' bottoms fade 44→2; aspect-abuse
  defect's intact line tops start at 3 vs peak 25)

Adjacent qualifying rows cluster into one finding. Findings carry
string, bboxes, line position, coverage/flatness/ink-distance — facts for
a reasoning layer, not a verdict.

## Real output — assigned case

```
$ uv run detectors/edge-bisect/edge_bisect.py \
    evals/z-order/defect.png evals/z-order/control.png

evals/z-order/defect.png  960x720  scanned=16 skipped=0
  EDGE-BISECT horizontal y=239 cov=1.0 med=24.0 flat=1.0/1.0 ink_dist=3px  "n..Eaakn"  bbox_px=[619, 224, 692, 241]
  VERDICT: EDGE_BISECT

evals/z-order/control.png  960x720  scanned=18 skipped=0
  VERDICT: CLEAN
```

The finding names exactly the eval's target: the corrupted OCR string
`'n..Eaakn'`, bisected by a horizontal edge at y=239 — the exit row of
card-2's 2 px border band (entry y=237, cov 0.93 but rejected: the row
above still holds glyph ink, flat_prev 0.03). The same record's
`'Rename'` above and all card texts stay clean; control's intact
`'Duplicate'` (ink runs 232–246 straight through y=237) produces no
coherent step — the card edge is occluded by the menu there, cov max
0.59.

`--record detectors/edge-bisect/records/record-defect.json` reproduces
the identical finding without a model call; `--json` emits the full
finding object; `--fail-on-findings` exits 1 on defect, 0 on control
(both verified).

## Out-of-domain sweep — all CLEAN

Saved `eyes describe` records live in `detectors/edge-bisect/records/`
(regenerate with `uv run eyes describe <img>`). Every non-z-order eval
image stays silent:

```
evals/text-truncation/defect.png   840x560  scanned=13  VERDICT: CLEAN
evals/text-truncation/control.png  840x560  scanned=13  VERDICT: CLEAN
evals/clipped-card/clipped.png     620x690  scanned=32  VERDICT: CLEAN
evals/semantic-surprise/control.png 880x640 scanned=8   VERDICT: CLEAN
evals/semantic-surprise/defect.png  880x640 scanned=7   VERDICT: CLEAN
evals/low-contrast/defect.png      900x680  scanned=14  VERDICT: CLEAN
evals/ocr-hostile/defect.png       920x640  scanned=14  VERDICT: CLEAN
evals/theme-drift/state-a.png     1100x760  scanned=32  VERDICT: CLEAN
evals/theme-drift/state-b.png     1100x760  scanned=32  VERDICT: CLEAN
evals/aspect-abuse/defect.png     1000x1000 scanned=30  VERDICT: CLEAN
evals/aspect-abuse/control.png    1200x675  scanned=22  VERDICT: CLEAN
```

text-truncation is the important negative: its clip boundary is
pixel-invisible (no edge to find) and its title bbox's right edge is
flush, not bisected — correctly silent. clipped.png's calendar digits
produced the sweep's highest non-defect coverages (0.73) and several
near-flat steps — all rejected by the 0.80 coverage + 0.85 flatness
pair.

## Axis symmetry + FP guards (synthetic fixtures)

`make_synthetic.py` builds two fixtures with hand-written records
(`synthetic/`):

```
$ uv run detectors/edge-bisect/edge_bisect.py \
    --record detectors/edge-bisect/synthetic/v-slice.json \
    detectors/edge-bisect/synthetic/v-slice.png
detectors/edge-bisect/synthetic/v-slice.png  400x240  scanned=1 skipped=0
  EDGE-BISECT vertical x=118 cov=1.0 med=33.0 flat=1.0/1.0 ink_dist=2px  " sliced label "  bbox_px=[50, 80, 280, 140]
  VERDICT: EDGE_BISECT

$ uv run detectors/edge-bisect/edge_bisect.py \
    --record detectors/edge-bisect/synthetic/divider.json \
    detectors/edge-bisect/synthetic/divider.png
detectors/edge-bisect/synthetic/divider.png  400x240  scanned=1 skipped=0
  VERDICT: CLEAN
```

v-slice.png: a gray panel edge at x=118 slices a fake glyph row mid-body —
fires on the vertical axis. divider.png: a flat rule 30 px below the ink
inside a tall bbox — silent via ink-adjacency (this fixture initially
*did* fire: the dark rule counted as ink and stretched the band; the
FULL_INK_FRAC exclusion fixed it — see below).

## FP classes found and killed during development (all real, all measured)

1. **Solid foreign bands counted as ink.** A dark divider/rule inside a
   bbox has ~100% per-row ink coverage and stretched the ink band to
   dist=0, defeating adjacency (divider.png fired before the fix).
   `FULL_INK_FRAC=0.7` excludes ≥70%-inked positions from the band.
2. **Edge between two content populations.** aspect-abuse *control*
   '12.4k': a stat-card's bottom edge (flat 249→255 step, cov 1.0) crosses
   the bbox between the number's ink and a neighboring element's ink —
   fired before the one-sided-ink rule.
3. **Foreign edge hovering in padding near intact text.** aspect-abuse
   *defect* 'New sigups': a dark bar's bottom edge sits 3 px above an
   intact text line inside the same bbox — fired before the dense-edge
   rule (its ink tops taper 3 vs peak 25; the defect's sliced bottoms
   stay at 37–38 vs peak 38).

## Honest limits

- **CAUGHT scope: the sliced-item half only.** 'Archive' and 'Delete'
  leave zero trace in the defect record (never perceived) — single-image
  absence is the eval's recorded hard wall; this detector does not and
  cannot name fully-hidden items. Pairwise (`score`) or temporal
  (`reel`) context is still required for that half.
- **Slice-position sensitivity.** The dense-edge rule needs the cut to
  land where glyph ink is still heavy. A slice through a naturally sparse
  glyph region (e.g., between x-height bottom and descender tips) can
  taper like a natural edge → miss. Measured margin on this artifact is
  large (0.97 vs 0.12 density ratio) but it is a heuristic, not a proof.
- **Sandwich occlusion misses.** Ink on both sides of the cut (text
  visible above AND below an occluding band — e.g., a thin toolbar
  crossing a text line) is suppressed as ambiguous. Deliberate: it is
  also the legit "divider through a text block" shape.
- **Textured occluder surfaces miss.** Both sides of the cut must be
  ≥85% flat (±10 gray). A slice whose far side is photo/busy-content
  won't fire — card/panel/menu edges (the dominant UI case) are flat.
- **Mirage dependence.** No text bbox → nothing to check. Bboxes are
  loose (2–4 px padding observed); INSET=2 and INK_K=6 are tuned to that
  padding. A different detector's tighter/looser boxes shift the margins.
- **Ink model is grayscale-median.** Works for dark-on-light and
  light-on-dark (clipped.png verified silent). Text whose ink is <45
  gray levels from its local surface (low-contrast eval: 3 texts skipped)
  yields no ink band → conservative silence, never a guess.
- **Facts, not verdicts.** A finding says "a coherent flat-surface edge
  crosses this text bbox adjacent to dense one-sided ink" — whether that
  is occlusion vs. an unlucky-but-legit edge is the reasoning layer's
  call, per the PRD split.

## Verdict

**CAUGHT** on the assigned gap: fires on `evals/z-order/defect.png`
naming `'n..Eaakn'` bisected by a horizontal edge at y=239 (cov 1.0,
flat 1.0/1.0, ink_dist 3 px) — the exact fact the eval said was
computable and missing — stays silent on the identical-layout control,
on all four required out-of-domain controls, and on 7 further eval
images swept for FP confidence. Vertical axis proven on a synthetic
fixture; three real FP classes found in the sweep and killed with
measured thresholds. Standalone: no edits to `eyes/`, `tests/`, or other
detectors; `records/` + `synthetic/` are reproducible fixtures.

## Update — underline guard (2026-11-15, web-real sweep finding)

Real-page sweep found a false-positive class: underlined links read as
bisected text (example.com 'Learn more', line=756 cov=0.953
ink_dist=2px — the underline IS an edge line ~2px below ink).

Fix: `_edge_continues` requires the gradient to persist >=50% beyond
the text span on at least one side — container edges continue, local
decorations end at the bbox. Verified: example.com now CLEAN, z-order
defect still fires ('n..Eaakn' line=239 — card border continues past
the label), z-order control clean.
