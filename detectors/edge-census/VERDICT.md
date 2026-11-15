# VERDICT: edge-census — CAUGHT (flips evals/grid-misalign instrument-alone MISS to named findings)

## Gap filled

`evals/grid-misalign/VERDICT.md` proved the whole regularity/alignment
class dark: every shipped detector measures frame edges, intersections,
or legibility — "elements that should share a coordinate don't" is a
self-consistency check nothing computes. Its #1 suggestion was a
~40-line repeated-element edge census over `record["text"]`; its #2 was
a pixel-side leading-edge census for icon-only UIs. This entry ships
both, in one directory:

- **`edge_census.py`** — the assigned detector. Groups Mirage text
  records by normalized string, sub-clusters along x (column pass) and
  y (row pass), and flags edge spread above a calibrated floor. Zero
  new model calls when fed a record; one `eyes describe` when fed an
  image. Emits e.g. `column_drift: 'Active' x-edge spread 9u (~9.7px)
  (n=4)` — the exact defect, named.
- **`pixel_edges.py`** — the runner-up, implemented because it was
  cheap enough to calibrate honestly. No OCR, no VLM: page-bg mask →
  row bands → per-band ink intervals → cross-band x-clusters of
  uniform-width elements → anchored-edge spread. Reproduces the eval's
  own pixel table (avatar 8px, pill 8–9px, dots 7px) with no record at
  all — the channel that still works when OCR fails or elements are
  icon-only.

## Calibration (measured, not vibes)

Mirage `describe` is **deterministic** on this box — two runs on
`defect.png` produced byte-identical text bboxes, so the noise floor is
OCR bbox variance on identical content, not run jitter.

| image | max identical-string edge spread (text census) | max anchored spread (pixel census) |
|---|---|---|
| `grid-misalign/control.png` | **2 units** ('Engineering' x1) | **1 px** |
| `grid-misalign/defect.png` | 4–9 units ('Active' x0 **9**, 'Invited' 9, 'Engineering' 5, 'Data' 4) | 7–9 px (avatar 8, pill 9, dots 7, +name/role columns pre-guard) |

Floors sit in the measured gap: text `FLOOR=3.0` units (flag >3.0 ⇒
≥4 on integer bboxes; control ceiling 2, ~1 unit margin each side),
pixel `FLOOR_PX=3.0` (control ceiling 1px). Both are CLI-tunable.

## Defect case — real output

```
$ uv run python detectors/edge-census/edge_census.py evals/grid-misalign/defect.png
edge-census: evals/grid-misalign/defect.png
  image 1080x640  (1 x-unit ~= 1.08px, 1 y-unit ~= 0.64px)
  text records: 28  repeated strings (n>=2): 4  clusters audited: 4
  floor: edge spread > 3.0 units
  FINDING column_drift: 'Active' n=4 x-edge spread 9u (~9.7px) (x0 9 x1 6 y0 607 y1 604 w 6)
      bbox [839, 597, 889, 636]
      bbox [841, 841, 894, 880]
      bbox [844, 234, 894, 276]
      bbox [848, 475, 895, 516]
  FINDING column_drift: 'Invited' n=2 x-edge spread 9u (~9.7px) (x0 6 x1 9 y0 357 y1 360 w 3)
  FINDING column_drift: 'Engineering' n=3 x-edge spread 5u (~5.4px) (x0 5 x1 5 y0 484 y1 478 w 6)
  FINDING column_drift: 'Data' n=2 x-edge spread 4u (~4.3px) (x0 4 x1 2 y0 238 y1 237 w 2)
  VERDICT: FLAGGED
```

```
$ uv run python detectors/edge-census/pixel_edges.py evals/grid-misalign/defect.png
pixel-edges: evals/grid-misalign/defect.png  1080x640
  bg=[238, 240, 245]  row bands: 8  intervals: 36
  bands (y-ranges): 12-48 88-95 141-185 223-267 294-338 374-418 451-495 525-569
  FINDING edge_drift: x0[903..920] n_bands=7 left 17px right 9px center 8px -> anchored 9px (floor 3.0px)
  FINDING edge_drift: x0[65..73] n_bands=6 left 8px right 8px center 8px -> anchored 8px (floor 3.0px)
  FINDING edge_drift: x0[983..990] n_bands=6 left 7px right 7px center 7px -> anchored 7px (floor 3.0px)
  VERDICT: FLAGGED
```

The pixel findings are the eval's pixel-verified drift table almost
verbatim: avatar left edge 8px (eval: 8), pill right edge 9px anchored
(eval: 8), dots left edge 7px (eval: 7) — plus the name/role text
columns the width guard now skips (they're prose-width-variable; the
text census owns those).

## Control case — real output

```
$ uv run python detectors/edge-census/edge_census.py evals/grid-misalign/control.png
edge-census: evals/grid-misalign/control.png
  image 1080x640  (1 x-unit ~= 1.08px, 1 y-unit ~= 0.64px)
  text records: 29  repeated strings (n>=2): 4  clusters audited: 4
  floor: edge spread > 3.0 units
  max audited spread: 'Engineering' column 2u (n=3)
  max audited spread: 'Active' column 1u (n=4)
  max audited spread: 'Data' column 1u (n=2)
  VERDICT: CLEAN
```

```
$ uv run python detectors/edge-census/pixel_edges.py evals/grid-misalign/control.png
pixel-edges: evals/grid-misalign/control.png  1080x640
  bg=[238, 240, 245]  row bands: 8  intervals: 36
  bands (y-ranges): 12-48 88-95 136-180 212-256 288-332 364-408 440-484 516-560
  max anchored spread: x0[128..129] n=7 1px (L1 R98 C50)
  max anchored spread: x0[68..68] n=6 0px (L0 R0 C0)
  max anchored spread: x0[489..489] n=7 0px (L0 R46 C23)
  max anchored spread: x0[908..909] n=6 0px (L1 R0 C0)
  max anchored spread: x0[986..986] n=6 0px (L0 R0 C0)
  VERDICT: CLEAN
```

## Synthetic controls (`make_synth.py` — PIL, known ground truth)

Three 1080×640 pages exercising both directions through the real
`eyes describe` path:

- `synth_clean.png` — aligned grid + toolbar: text census CLEAN (max
  audited 2u), pixel census CLEAN (max 1px).
- `synth_drift.png` — same scene, deterministic ±1–6px per-element drift
  + a +5px toolbar baseline shift: text census FLAGGED
  (`column_drift 'Active' 6u`, `'Engineering' 6u`, `row_drift 'Export'
  11u (~7.0px)` — the row pass works); pixel census FLAGGED (pill
  column anchored 7px).
- `synth_ragged.png` — the same strings legitimately repeated at
  *different* columns (second mini-table reusing 'Active'/
  'Engineering', scattered standalone labels): both channels CLEAN —
  sub-clustering and the width/anchor guards do not merge legitimately
  separate columns.

## Out-of-domain sweep (honest false-positive audit)

**Text census** on saved `eyes describe --stats` records: CLEAN on
`semantic-data` ctl+def, `text-truncation` ctl+def, `ocr-hostile`
control — all with **zero** repeated strings (n≥2), i.e. the census
simply has nothing to group on prose/document UIs. It cannot false-
positive where there is no repetition; it also cannot *see* anything
there.

**Pixel census** on all 25 static eval images + 3 synth: before the
width guard it fired on 9 of 10 non-grid scenes — prose columns are
legitimately ragged and "anchored edge" is meaningless without the
repeated-element prior. The `WIDTH_MAX=25px` guard (uniform-size
clusters only) took it to CLEAN on every document/UI eval ctl+def pair
(semantic-data, text-truncation, ocr-hostile, theme-drift, z-order,
low-contrast, aspect-abuse, semantic-surprise) and on synth_ragged.
Two residual fires, disclosed plainly:

- `clipped-card/clipped.png` — FLAGGED (x0[409..429] anchored 8px,
  n_bands=7): coincidental uniform-width structure in a photographic
  calendar card. Not a grid; the cluster is real, the "should align"
  interpretation is not.
- `chaotic-motion/frame_01.png` — FLAGGED (x0[227..238] anchored 11px,
  n_bands=3): a meeting-card UI with repeated elements; single frame,
  defect-attribution unverifiable — plausibly real repeated-element
  variance, reported as a fact not a verdict.

## Honest limits

- **Identical strings only.** Unique labels ('MEMBER', 'Invite member',
  each name/email) are n=1 — invisible to the text census. The header
  labels' own drift is caught only indirectly (pixel channel folds the
  header band into column clusters).
- **Sub-floor drift is invisible.** ~3 units ≈ 3.3px on x; the eval's
  1–2px drifts sit below OCR noise and are correctly not flagged.
- **n=2 findings are weaker** — one OCR outlier among two members can
  produce a spread; they are emitted with n visible, floor unchanged.
- **Objects are excluded deliberately.** Measured, not assumed: Mirage
  relabels 'tab'→'button' wholesale and object boxes are region-scale —
  inside one x-cluster on *both* images, x1 spreads hit ~860 units.
  Name-grouping objects is noise, not signal (the eval measured the
  same churn in `score`).
- **Legitimately ragged same-strings** are handled by x/y sub-clustering
  (gap 30u/25u), the multi-row/multi-column span requirements, and
  merged-column/row collision guards — synth_ragged proves the common
  case. Two intended columns <~30 units (~32px) apart with members in
  the same rows could still merge and flag; on a 1080 canvas that is
  itself a spacing smell.
- **pixel_edges is x-direction only** and cannot see drift smaller than
  a row band; it assumes a roughly uniform page background (dark/photo
  backgrounds produce garbage bands — clipped-card's fire is the
  symptom). It emits measured spreads; whether a cluster *should* be
  aligned remains the reader's judgment — matching the catalog's
  facts-out/judgment-decides pattern.
- **Row pass is thin.** It caught the synth toolbar baseline shift
  (11u) but needs ≥2 identical strings sharing a row — rarer than
  columns in real UIs.

## Verdict

**CAUGHT.** The assigned detector flips the eval's instrument-alone
MISS to named findings: `'Active'` pill column x0 spread 9 units
(~9.7px, n=4) on defect vs 0–1 on control — the exact signature the
eval said was "sitting in the bboxes the whole time," now computed with
a documented noise floor instead of invented by the reasoning layer.
Control stays clean on every case tried; the pixel channel independently
reproduces the eval's pixel-verified spreads with zero model calls.
