# VERDICT: aspect-abuse — MISS (instrument-alone) / PARTIAL (instrument+reasoning)

## Defect planted

`control.png` (1200×675, 16:9) is a mock "Weekly metrics" dashboard
share-card: white card on gray page, header with title/subtitle/share
button/avatar, three stat cards with circular icon chips, a line chart
with 14 circular data/legend dots, and a bottom row of list + progress
cards. Circle-rich by design — the distortion has many witnesses.

`defect.png` (1000×1000) is the same source non-uniformly resized to a
square canvas — the canonical agent bug: `img.resize((1000, 1000))` in
PIL or `object-fit: fill` (the CSS default) in a square container when
the asset spec demanded 1:1. Scale factors sx=0.833, sy=1.481 —
anisotropy 1.78×: every circle becomes a tall ellipse, glyphs narrow
and stretch, the chart's proportions lie.

Verified programmatically in `make_images.py` output:

```
control.png: (1200, 675) aspect=1.778 avatar=(1.0, (32, 32))
defect.png:  (1000, 1000) aspect=1.000 avatar=(1.808, (26, 47))
scale factors: sx=0.833 sy=1.481  (anisotropy 1.78x)
```

Glyph-level proof on the identical "$48.2k" string (column-projection
segmentation, ink threshold):

```
control : median glyph w/h = 0.545, ink height 22px
defect  : median glyph w/h = 0.303, ink height 33px
```

Same 6 glyph columns; ink height grew 1.5× while glyph width shrank —
the stretch measured directly.

## What eyes reported

### `uv run eyes describe defect.png --stats`

Mirage produced a coherent record — `scene {"background": "white",
"style": "screenshot"}`, reasoning `"white window with blue buttons,
black text labels, blue arrows"` — but the record contains **zero
dimension information**: `width`, `height`, `size`, `aspect`,
`dimension` each occur 0 times in the JSON. Bboxes are per-axis
normalized to [0,1000] (`eyes/color.py:14`), so aspect ratio is erased
by construction.

Object vocabulary never engaged shape: 30 objects = 20×`text label` +
10×`button`, every description just `{"color": ...}` — no "ellipse",
no "oval", nothing that could register circle→ellipse. Control produced
21 objects = 1×`text label` + 20×`button` — detection churn, different
labeling, same blindness.

OCR degraded systematically under the stretch — 30 strings vs control's
22, with characteristic misreads:

```
defect : 'Nor 10 - Nov 16, 2025 -all regions'   (control: correct)
         'Acive users'   'Chum nisk'   'Cunen' (Current)
         'Traling 7 days-U50'   'Top poges'   'bloglaunch'
         '04 revenue' (Q4)   'New sigups'   'Idocslapi'   '124%'   '-04%'
control: 'Nov 10 - Nov 16, 2025 - all regions' 'Active users'
         'Churn risk' 'Current' 'Top pages' 'Q4 revenue' (minor noise:
         'Export CsV', 'Traling 7 days - USD', 'Idocs/api')
```

The corruption is in the record, unflagged — describe is perception,
not detection.

### `uv run eyes layout defect.png --describe`

```
edge contact (bg #fcfcfc, strip 5px):  all 0.0%
objects at edge:  {'name': 'button', 'sides': ['right'],
                   'bbox': [929, 149, 964, 202], 'score': 0.424,
                   'suspect': True}
bbox overlaps:    text label×text label iou=0.196,
                  text label×button iou=0.196
text flush:       'New sigups' flush top line_y=918
legibility flags: 25 entries
```

Control `--describe`: identical clean edge contact; the same `button`
right-edge flag (score 0.475 — the Share button sits near the edge in
both, not defect-attributable); **no bbox overlaps**; 3 text_edge_flush
hits; **16 legibility flags**.

The legibility channel is the only detector that moved: 25 flags vs 16,
and defect OCR scores sit lower on corresponding strings ('Share
report' 0.515 vs 0.593, 'New sigups' 0.471, 'Thu' 0.405 vs 0.475).
But every flag is named `low_contrast` / `low_ocr_confidence` — the
instrument reports "hard to read", never "stretched". And the control
fires 16 flags of the same names on the identical mock, so the signal
is a *delta*, not a detection: nothing in a single-image report says
this page is worse than it should be.

### `uv run eyes score control.png defect.png`

```
score: 58.7 / 100
  palette   93.4  {}
  objects   40.8  {'matched': 10, 'missing': [10×'button'],
                  'extra': [20×'text label']}
  layout    14.8  {'mean_center_dist': 0.298, 'pairs': 10}
  text      95.2  {}
  scene     58.3  {}
```

Loud — until the confound probe.

### Confound probe — same canvas, correct fit (not catalogued)

Built `/tmp/ab_letterbox.png`: the same source contain-fit into the
**same 1000×1000 canvas** the defect uses — uniform scale 1000×562,
219px background bars top/bottom. This is what the agent *should* have
shipped at that canvas size.

```
eyes score control.png /tmp/ab_letterbox.png   ->  36.7 / 100
  objects    9.3  (Mirage re-reads the scene: 'window', 'toolbar',
                  4×'arrow', 16×'text label' appear from nowhere)
  layout     4.5  scene 26.2  palette 64.6  text 94.8

eyes score /tmp/ab_letterbox.png defect.png    ->  35.5 / 100
  objects    3.9  layout 0.0  scene 40.0
```

**The correctly-proportioned letterboxed variant scores LOWER (36.7)
against control than the distorted defect does (58.7).** The objects/
layout collapse is Mirage detection churn on synthetic UI — bars and
squash both reshuffle its object vocabulary — not geometry. `score`
cannot attribute its own loudest signal to aspect abuse; if anything
it ranks the defect as *more* faithful to control than the honest
export. `palette` 93.4 on the defect vs 64.6 on the letterbox — the
non-uniform resize preserves the color histogram almost exactly, so
the one component that should notice sees nothing.

### `uv run eyes ask defect.png -q "...is any content visibly
distorted, stretched, or squashed — e.g. circles rendered as
ellipses or text stretched out of proportion?..."`

The evidence pack is the only surface where aspect appears at all —
nested inside two detector outputs:

```
detectors.status_icons.size: [1000, 1000]
detectors.hue_census.size:   [1000, 1000]
findings.legibility_flagged: 25 entries
text: 30 strings incl. 'Chum nisk', 'Cunen', 'New sigups', '04 revenue'
objects: 29 generic 'text label'/'button' entries, no bboxes, no shapes
```

Control pack for comparison: `size: [1200, 675]`, 16 legibility flags,
22 mostly-clean strings. The delta is citable — but the pack strips
exactly the geometry needed (no object bboxes, no shape fields, no
per-string bbox aspect) and contains no statement of intended aspect.

## Instrument gaps this case exposes

1. **Aspect ratio is erased at the record layer.** Per-axis [0,1000]
   normalization (`color.py:14`) makes a 1200×675 and a 1000×1000
   image indistinguishable in bbox space; `describe` emits no
   width/height/size/aspect key at all (verified: 0 occurrences). The
   *canvas* fact survives only by accident inside two detectors'
   sub-objects in the ask pack.
2. **No shape-fidelity measurement exists.** The decisive signature —
   designed circles measuring 1.78:1 — lives in raw pixels. Mirage's
   vocabulary never said "ellipse"; no detector measures blob aspect.
   The instrument can see *that* OCR got worse but has no channel that
   says *why* (stretched glyphs vs low contrast vs blur all produce
   the same `low_ocr_confidence`).
3. **`score` is confounded on canvas/fit changes.** The objects/layout
   components are Mirage-label-churn dominated on synthetic UI; my
   probe shows a *correct* variant scoring below the *defect*. Until
   detection stabilizes, composite deltas on fit-mode changes are
   unattributable — the report may not launder them into a catch.
4. **Legibility flags are symptom-named, not cause-named.** The 25 vs
   16 flag delta is real, but `low_contrast` on stretched-but-black-
   on-white text is a misattribution: contrast didn't change, glyph
   proportions did. A `glyph_anisotropy` flag would have named it.

## What would catch this

1. **Shape-fidelity census (primary — demonstrated numbers above).**
   Emit `image: {width, height, aspect}` in `describe`/`ask` (the dims
   already exist inside detector outputs — hoist them). Then a
   model-free anisotropy check: threshold non-background, find filled
   blobs, measure bbox aspect of near-square candidates (UI circles —
   avatars, icon chips, dots, legend swatches — are drawn circular by
   convention). Flag when the population's median |log(aspect)| exceeds
   ~0.15. On this case: avatar 1.0→1.808, every chip/dot/legend dot
   ~1.78 — unanimous; control all 1.0. ~40 lines numpy/PIL. Crucially
   this catches *squash*, not *letterbox*: contain-fit bars don't
   distort shapes, so the honest variant stays clean — the probe proves
   the distinction is measurable.
2. **Glyph-proportion check inside `legibility.py` (demonstrated).**
   The module already crops each OCR text bbox; add column-projection
   glyph segmentation and median glyph-width/ink-height per string.
   Latin glyphs sit ~0.45–0.6; this defect measured 0.303 vs control
   0.545 on the *same string*. Flag population median outside
   [0.35, 0.75] as `glyph_anisotropy` — catches squash in both
   directions and covers text-only UIs where no circles exist.
3. **Ask-pack geometry passthrough.** `record["text"]` and
   `record["objects"]` carry bboxes that `evidence_pack` strips. Emit
   per-string `bbox_aspect` and top-level `image.size`; a reasoning
   layer could then do the anisotropy judgment itself — today the pack
   contains the *consequences* (garbled strings) but removes the
   *measurements*.
4. **Score-pair aspect guard (honest caveat).** Pass image dims into
   `score_pair` and add an `aspect` component — but aspect delta alone
   is a fact, not a defect (square exports are legitimate; my letterbox
   probe is the proof). It only means something paired with
   anisotropy evidence, and `score`'s objects/layout need a Mirage-
   churn floor before deltas on fit-mode changes are reportable.

## Verdict

**MISS — instrument alone.** Every surface walked past the distortion:
describe erases aspect by normalization and Mirage never named a
shape; layout's only movement is a legibility-flag *delta* (25 vs 16)
reported under wrong names on a mock that already fires 16; palette is
bit-identical in distribution; and the one loud number — score 58.7 —
is proven non-attributable because the correct-aspect letterboxed
variant scores *lower* (36.7). Nothing in the output says "aspect" or
"distorted" or "stretched".

**PARTIAL — instrument + reasoning.** The ask pack carries the square
dimensions ([1000, 1000], the stack's only aspect datum), 25
legibility flags, and systematically corrupted OCR strings. A reasoning
layer answering the probe question can honestly report "this export
shows signs of a rendering/scaling fault — text is corrupted and the
canvas is square; inspect the source asset" — a real flag in the
defect's neighborhood. It cannot confirm aspect abuse: no shape
measurements exist, no intended-aspect reference exists, and under the
pack's own "insufficient evidence" instruction the strict answer is
that distortion is *consistent with* but not *proven by* the evidence.
A stricter reader calls this MISS; I report the generous end because
"square canvas + corrupted text" would genuinely prompt a human to
look.

This entry exists to be fixed against: the glyph-aspect and
shape-fidelity checks above are demonstrated, model-free, and would
flip instrument-alone to CAUGHT — the signature is sitting in the
pixels the whole time.
