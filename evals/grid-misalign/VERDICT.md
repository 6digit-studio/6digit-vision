# VERDICT: grid-misalign — MISS (instrument alone) / PARTIAL (instrument + reasoning)

## Defect planted

`control.png` / `defect.png` (1080×640) — a mock "Members" admin page:
white app bar, a column-header strip (MEMBER / ROLE / STATUS), and six
member cards in one column. Each card carries five repeated elements
on fixed columns: avatar circle, name-over-email block, role text,
right-anchored status pill, right-anchored "…" button. Nothing
overflows, nothing overlaps, every string is readable — the only crime
is that the spacing is a few pixels wrong, repeatedly.

`control.png` obeys a strict grid: left edge x=48, right edge x=1032,
card height 64, gaps 12 (header→card1: 16), interior columns at fixed
offsets, pill/dots right edges flush at the 20px padding line.

`defect.png` is the same scene with the values an agent ships when it
hardcodes margins instead of using a spacing scale (`make_images.py`
regenerates both; all deltas are parameters, content identical):

- inter-card gaps **17, 9, 15, 11, 14** (control: 12 ×5); header→card1
  gap **21** (control: 16) — card tops drift cumulatively to +11px
- card right edges ragged: header −4, cards 3 & 6 −6 (control: all
  flush at x=1032)
- interior drift per row, each element off by 1–6px in varying
  directions, plus 1–2px vertical baseline wobble on name/role text
- header labels off their columns: MEMBER +2, ROLE −3, STATUS −5

Pixel-verified after render (scan of exact fill colors per row band):

```
              avatar_L      pill_R       dots_L       card_R
control  all  68            968          981          1031   (zero spread)
defect   r1   (slate avatar below sat. threshold)  968          981          1031
         r2   71            964          978          1031
         r3   66            970          981          1025
         r4   73            962          985          1031
         r5   65            970          979          1031
         r6   70            966          982          1025
```

Spreads: avatar 8px, pill right edge 8px, dots left edge 7px, card
right edge 6px, inter-card gaps {9..17}px. `diff bbox=(48,76,1033,582)`,
22.4% of pixels differ — positional difference only; strings, colors,
sizes identical.

## What eyes reported

### `uv run eyes describe defect.png --stats`

Mirage produced a coherent record — `scene {"setting": "computer
interface", "style": "screenshot"}`, reasoning `"white window with gray
menu bar, blue buttons, green and purple buttons…"` — 37 objects, 28
text strings. **Zero alignment/spacing/geometry-consistency fields
exist in the schema.** Object detection churned exactly as it does on
synthetic UI in prior evals: control got 35×`tab` + 2×`button` +
1×`icon`; defect got 36×`button` + 1×`menu bar` — the same text-line
fragments relabeled wholesale. OCR noise typical:
`'STATUs'`, `'alan@bleichley.dev'`, `'Radia Perlmar'`, `'kat@orbitgov'`,
avatar initials read as `'K'`, `'MH'`, `'CH'`, `'AT'`, `'RP'`.

### `uv run eyes layout defect.png --describe`

```
edge contact (bg #fcfcfc, strip 3px):  all 0.0%
objects at edge: 5 hits — 'button'/'menu bar' on top/left/right,
  all appbar-region Mirage boxes, suspect flags on score<0.5
bbox overlaps:   (none)
text flush at interior edge: (none)
legibility flags: 22 entries — every string flagged
  low_contrast (contrast 2.05–2.86) + low_ocr_confidence on weak reads
edge bisects (clean): (none)
```

`layout control.png --describe` is the same report shape: edge contact
0%, 5 appbar edge objects, **one** `tab×tab` bbox overlap (iou 0.201 —
Mirage duplicate-detection noise), 24 legibility flags of the same
names on the same strings. The legibility flood is **mock noise present
in both images** — my `#6b7280`/`#4b5563` secondary text trips the
2nd/98th-percentile contrast measure identically on the clean control
(same disclosure class as theme-drift and ocr-hostile). Nothing in
either report mentions spacing, alignment, grid, or regularity.

### `uv run eyes score control.png defect.png`

```
score: 73.3 / 100
  palette   90.7  {}
  objects   36.5  {'matched': 36, 'missing': ['tab','button'],
                  'extra': ['button'], 'attr_sim': 0.3801,
                  'attr_changes': [35× 'tab'->'button' pairs …]}
  layout    80.3  {'mean_center_dist': 0.0688, 'pairs': 36}
  text      90.8  {}
  scene    100.0  {}
```

Loud — and almost entirely misattributed. `objects` 36.5 is the
`tab`→`button` relabel churn (attr_sim 0.38 on name tokens, not
geometry). `layout` 80.3's `mean_center_dist 0.0688` ≈ **69 normalized
units** of mean center displacement — the planted drift is 3–6 units;
the measured distance is 10–30× larger, i.e. Mirage bbox instability
between two different records dominates completely. Even the one
component that *could* see position cannot resolve a 4px shift through
its own noise floor. `palette` 90.7 is shifted-anti-aliasing dust.
Nothing says "spacing" or "alignment" or "grid".

### `uv run eyes ask defect.png -q "Is the spacing/alignment
consistent? Are elements aligned to a common grid?"`

The pack carries: scene, 37 objects **without bboxes**, 28 text strings
**with bboxes**, the same noise findings as layout, and four detectors —
`status_icons` 0 candidates, `hue_census` one blue family,
`lexical_screen` flagging proper nouns ('Lovelace' OOV), `anisotropy`
firing `glyph_anisotropy` (glyph w/h 0.183, "text stretched/squashed")
— **identically on the control pack** (same verdict, same
population_median 0.1834, same 8 lines, same ink_px 23399): a
false-positive on this flat UI, not defect-attributable, and wrong
about the cause anyway — no glyph here is stretched. **No detector
output addresses regularity; the only alignment evidence in the pack
is the raw text bboxes.**

### The decisive analysis — identical-string x0 clustering on the pack data

Grouping pack `text` entries by identical string and measuring x0
spread (bbox x0, [0,1000] space; ×1.08 ≈ px on this canvas):

```
control pack:                defect pack:
  'Active'     x0={844,844,844,844}  spread 0     'Active'     {839,841,844,848}  spread 9
  'Invited'    {843,844}        spread 1          'Invited'    {841,847}           spread 6
  'Engineering'{446,447,447}    spread 1          'Engineering'{446,450,451}       spread 5
  'Data'       {445,446}        spread 1          'Data'       {440,444}           spread 4
```

`'Active'` is the clean witness: four identical right-anchored pills —
same string, same width, same column — whose left edges span **9 units
≈ 10px** in the defect vs **0** in the control. Designed pill drifts
{0,+2,−6,−2}px predict x0 {844,846,838,842}; measured {844,848,839,841}
— the record carries the defect within ~2 units of Mirage jitter. Name/
email column x0s similarly spread 114–120 (defect) vs 114–117 (control).

## Instrument gaps this case exposes

1. **No regularity/alignment detector exists — the whole class is dark.**
   Every shipped detector measures *edges of the frame* (edge_contact,
   objects_at_edge), *intersections* (bbox_overlaps, edge_bisect,
   text_edge_flush) or *legibility* (contrast/OCR). "Elements should
   share coordinates and don't" is a different predicate — a
   self-consistency check, not a boundary check — and nothing computes
   it.
2. **`interior_edge_lines` is blind to flat-UI card borders at its
   shipped threshold.** Verified: 0 vertical/horizontal lines at default
   `min_strength=30` on BOTH images; the 1px `#e2e5ea` borders on
   white-over-gray cards fall below the gradient floor even at 256px
   downscale. One threshold down the signal flickers alive — at
   `min_strength=15` control yields 6 horizontal lines at pitch ≈18
   (152px canvas ≈ the 76px card pitch, remarkably regular) vs defect's
   3 irregular ones — but nothing surfaces it, and at `min_strength=8`
   both fill with noise. Any grid detector built on this edge finder
   inherits the blindness; the regularity is one parameter away and
   completely unwired.
3. **`score`'s layout component cannot resolve sub-noise shifts.**
   `mean_center_dist` compares Mirage bbox centers; Mirage's own
   bbox jitter between records (~0.07 normalized here) is an order of
   magnitude above the planted drift (~0.005). The component reports
   "layouts differ" at a magnitude that is pure instrument noise —
   worse than silent, it points at the right axis with a fabricated
   number.
4. **The ask pack has the evidence but no statistic.** Text bboxes are
   included, so the decisive measurement (identical-string edge
   clustering) is *computable* — but nothing computes it, groups
   repeated elements, or supplies a noise floor. The reasoning layer
   must invent both the statistic and its threshold.
5. **Mirage object churn makes `score` fire loud for the wrong reason.**
   73.3/100 on a defect whose entire pixel delta is ±6px of position —
   the drop is `tab`→`button` relabeling, the documented synthetic-UI
   instability, not the defect.
6. **Detector false-positive disclosure.** `anisotropy` reports
   `glyph_anisotropy` — "text stretched/squashed" — identically on
   defect AND control (same verdict, same population_median 0.1834,
   same ink_px 23399, same 8 lines). On this flat UI it fires on every
   text line regardless of distortion. A reasoning layer reading the
   defect pack sees a named anomaly that is pure instrument noise —
   worse than silence, it points at a cause that isn't there.
   Detector verdicts need a same-image control or a per-image
   confidence before they enter the pack as findings.

## What would catch this

Concrete instrumentation, cheapest first:

1. **Repeated-element edge census (primary — demonstrated above, ~40
   lines, zero model calls).** Group `record["text"]` (and object
   bboxes when present) by normalized string; for groups with n≥2
   compute spread of x0/x1/y0/y1. Identical strings in a repeated
   column should share edges; flag spread above a calibrated floor
   (~3 units). On this case it emits e.g.
   `column_drift: 'Active' x0 spread 9 units (n=4)` — the exact defect,
   named, from data the record already carries. Control floor measured
   here: ≤1 unit on identical content. Needs a minimum group size and
   per-role grouping (left-edge columns vs right-edge columns) to avoid
   flagging legitimately ragged text; the 'Active' witness needs
   neither — identical string + right-anchor forces identical x0.
2. **Pixel-side leading-edge census (model-free, ~80 lines).**
   Demonstrated in this eval's verification pass: per card row-band
   (horizontal ink projection), take leftmost/rightmost ink of each
   element class — avatar_L spread 8px, pill_R 8px, dots_L 7px in
   defect vs **0** in control. Threshold non-background, find row bands,
   cluster component edges across bands at ~2px tolerance, report
   clusters-per-column + spread. Catches the defect with no OCR and no
   VLM — works on icon-only UIs where #1 has no text to group.
3. **Gap-regularity check on segmented regions.** Sort detected
   surface boundaries (card tops/bottoms) and measure inter-element
   gaps; flag gap CV above threshold. Requires region segmentation
   first — `interior_edge_lines` can't supply it (gap #2 above), so
   this rides on #2's component analysis rather than extending the
   gradient finder.
4. **Baseline census (cheap add-on to #1).** Same grouping on y0 for
   single-line strings within a row band catches the 1–2px vertical
   baseline wobble — weaker signal (font metrics vary), but free once
   the grouping exists.
5. **Ask-pack enrichment (cheap partial).** Emit the #1 census as a
   `findings.alignment` summary alongside the raw bboxes — the
   instrument computes the statistic, the court judges intent. Matches
   the established detector-catalog pattern: facts out, judgment
   decides.

## Verdict

**MISS — instrument alone.** Every detector surface walked past the
defect: layout reports are clean or identical mock noise on both
images; `score` fires a loud 73.3 that decomposes into Mirage relabel
churn (`objects` 36.5) and bbox jitter (`layout` 80.3 at ~15× the
planted magnitude) — nothing names spacing, alignment, or regularity,
and `interior_edge_lines` can't even see the card borders the grid
would be measured against.

**PARTIAL — instrument + reasoning.** The ask pack carries text bboxes,
and the decisive measurement is one arithmetic step away: identical
`'Active'` pills span x0 {839…848} — a ~10px ragged edge where the
control pack shows spread 0. A reasoning layer that groups repeated
strings and compares edge positions can cite a concrete inconsistency
and answer the question "no." What keeps this PARTIAL and not CAUGHT:
the pack supplies no grouping, no noise floor, and no alignment
baseline — the reasoning layer must invent the statistic *and* defend
9 units of spread against unmeasured Mirage bbox jitter in a
single-image pack. The evidence is present and quantitatively
suggestive; the instrument never points at it. This entry exists to be
fixed against: detector #1 above is ~40 lines of record math and flips
instrument-alone to CAUGHT — the signature is sitting in the bboxes
the whole time.
