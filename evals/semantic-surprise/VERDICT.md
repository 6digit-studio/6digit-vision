# VERDICT: semantic-surprise — PARTIAL (instrument-alone) / PARTIAL (instrument+reasoning)

## Defect planted

`defect.png` (880×640) is a mock payment-result card: white card on gray
page, status emblem top-center, headline "Payment failed", body "Your card
ending in 4242 was declined. / No charge was made to your account.", an
order summary row, and a blue "Try again" button. **The defect: the status
emblem is the SUCCESS glyph — a green circle (#16a34a) with a white
checkmark — rendered on a FAILED payment.** The canonical agent bug:
status icon hardcoded, keyed to the wrong state, or copied from the
success screen. Geometry, palette roles, and layout are all normal; only
the meaning is wrong.

`control.png` is the identical card with the correct error glyph for the
same failed state: red circle (#dc2626) with a white X. Same text, same
layout, same colors-in-roles — only the emblem's hue and glyph differ.
Pixel-verified before running eyes: defect circle = green + 788 white
glyph px; control = red + 1165 white glyph px; headline ink identical
(585 px both). `make_images.py` regenerates both.

## What eyes reported

### `eyes describe defect.png --stats`

Mirage read **every text string correctly**, including the defect's whole
premise:

```json
{"string": "Payment failed", "bbox": [374, 378, 626, 432], "score": 0.805}
{"string": "Your card ending in 4242 was declined.", "score": 0.782}
{"string": "No charge was made to your account.", "score": 0.773}
```

But the status emblem was filed as a **logo** — the glyph inside it was
never named:

```json
{"name": "logo", "position": "top center", "score": 0.609,
 "description": {"color": "green", "shape": "circular"}}
```

Mirage's own `reasoning` field: `"lang: en | green circular logo, black
text, blue button | logos identify brands, buttons trigger actions | text
on a logo is read as the brand name | ... | cannot know the company or its
purpose"` — the VLM saw a green circle, called it a brand mark, and moved
on. No checkmark, no status icon, no flag.

`describe control.png` produces the mirror image: `"logo", red,
circular` — plus an OCR-noise string `"*"` (score 0.304) which is
Mirage reading the white X as an asterisk. Neither record distinguishes
check from X; both emblems collapse to "colored circular logo".

### `eyes layout defect.png --describe`

```
edge contact (bg #f4f4f4, strip 4px):  all 0.0%
objects at edge:    (none)
bbox overlaps:      (none)
text flush at interior edge: (none)
legibility flags:
  'Order'      contrast 2.11  low_contrast
  'Try again'  contrast 2.46  low_contrast
```

The two legibility flags are **not defect-attributable** — control.png
flags the identical two strings (its small gray label and white-on-blue
button text), plus one extra for the `"*"` OCR noise. Mock noise, present
in both images.

### `eyes score control.png defect.png`

```
score: 92.3 / 100
  palette   96.6  {}
  objects   83.3  {'matched': 5, 'missing': ['logo'], 'extra': ['logo']}
  layout    99.9  {'mean_center_dist': 0.0002, 'pairs': 5}
  text      87.5  {}
  scene    100.0  {}
```

The objects component fires — but only because `score_objects`'s hard
rule treats disjoint color sets as unmatchable: red circular logo ≠ green
circular logo, so the emblem reports as one missing + one extra. The
signal says *"the icon region changed color,"* nothing about wrongness —
a legitimate brand recolor produces the identical signature. (text 87.5
is control-side OCR noise: the `"*"` string best-matches poorly.)

### Probe — same defect, same color (not catalogued)

Regenerated the defect with the checkmark colored **red** — wrong glyph,
but the same hue as the correct error icon — and scored against the same
control:

```
eyes score control.png /tmp/probe_check_red.png
score: 97.4 / 100
  objects  100.0  {'matched': 6, 'missing': [], 'extra': []}
```

**The semantic defect becomes completely invisible.** Both emblems sign
as `{logo, red, circular}`; check-vs-X lives below the record's
resolution. The 92.3 "catch" above was incidental to the hue change.

### `eyes ask defect.png -q "...is the status icon consistent with the
payment result stated in the text?"`

The pack (abridged) contains: `scene`, six objects — the emblem as
`{"name": "logo", "position": "top center", "score": 0.609,
"description": {"color": "green", "shape": "circular"}}` — seven correct
text strings including "Payment failed", empty findings except the two
unrelated legibility flags, then the question and the instruction
*"say 'insufficient evidence' rather than guessing."*

## Reasoning-layer verdict (me, answering the ask-pack question)

Citable facts: the card reports failure three ways ("Payment failed",
"declined", "No charge was made"); a green circular emblem sits top-center
and is labeled **logo**.

Honest answer under the pack's own instruction: **insufficient evidence
to confirm the defect.** The pack never establishes that the emblem is a
checkmark, or that it is a status icon at all — "logo" is Mirage's
catch-all and actively misdirects ("logos identify brands"). What can be
said: a *green* emblem on a *failed-payment* screen is circumstantially
anomalous — green connotes success — so a careful reader should flag it
for human verification. That is suspicion, not a catch: green brand marks
exist, and nothing in the pack names the glyph.

**Reasoning-layer verdict: PARTIAL** — the pack supports raising a flag,
not proving the defect. A stricter evidence-only reading is MISS; I am
reporting the generous end because "green emblem over 'Payment failed'"
genuinely is the kind of thing a reasoning layer exists to notice.

## Verdicts

- **Instrument alone (describe + layout): MISS.** Nothing fires; the
  emblem is unnamed as a glyph and unflagged.
- **Instrument alone, pairwise (score vs control): PARTIAL.** Names the
  exact locus (logo missing/extra) — enough to aim a human glance — but
  carries no wrongness semantics, and fires only because the wrong glyph
  also changed hue (probe: same-color wrong glyph → 97.4, perfect match).
- **Instrument + reasoning layer: PARTIAL.** The ask pack contains the
  failure text and the emblem's color/shape/position — enough for
  suspicion, not proof. The decisive fact ("it's a checkmark") never
  enters the record, so no reasoning layer can recover it from the pack.

## Instrument gaps this case exposes

1. **No glyph-level perception.** Mirage's object vocabulary tops out at
   "colored circular logo." Check, X, warning triangle, spinner,
   download, trash — the entire icon semantics layer — is invisible.
   This is the whole defect class: semantic surprise lives *inside*
   detected regions, below object granularity.
2. **"logo" is a semantic black hole.** The catch-all label erases the
   distinction between brand mark and status glyph — the two have
   opposite failure modes (a wrong logo is a branding bug; a wrong status
   glyph is a correctness bug) and the record can't tell them apart.
3. **`score_objects` signatures can't see interior glyph changes.**
   Color+shape+name tokens match a red-check to a red-X perfectly
   (probe: objects 100.0). Pairwise scoring is blind to the most common
   shape of this defect — same-style wrong icon.
4. **Perception gap, not judgment gap.** Unlike text-truncation (fact in
   the pack, reasoning caught it), here the fact never reaches the pack.
   No reasoning layer can catch what perception never named — the
   architecture's weak link is upstream of `ask`.
5. **Detection confidence again unsurfaced.** The emblem scored 0.609 —
   Mirage's lowest object score — same pattern as clipped-card's
   collapsed smartphone score. Nothing reads it.

## What would catch this

- **Glyph classification pass (primary).** Crop each detected
  emblem/icon region (Mirage already localizes it — bbox is in the full
  record) and classify the interior glyph against a small vocabulary:
  check, x, warning, info, spinner, download, trash, etc. Cheapest form:
  a second targeted VLM query per region ("what symbol is inside this
  circle?"); better: template matching against a rendered glyph set for
  the common UI icon font. Once the record says `status_icon: check`,
  the existing reasoning layer catches the contradiction for free —
  "check" + "Payment failed" is a one-line judgment.
- **Polarity cross-check (secondary, once #1 lands).** Extract outcome
  sentiment from OCR'd text (failed/declined/success) and status class
  from icon classification; flag disagreements. This is a rule, not a
  model — cheap and deterministic once both sides are named.
- **Ask-pack enrichment (cheap partial).** Include object bboxes and a
  per-object detail field in `evidence_pack`; even today a reasoning
  layer with bbox access could crop-and-look at the emblem itself. The
  pack currently strips the geometry that would let the *consumer* do
  the glyph read the instrument couldn't.

## Verdict

**PARTIAL** — the honest split, not a soft MISS: pairwise score locates
the changed emblem (92.3, objects 83.3 missing/extra 'logo'), and the
ask-pack reasoning layer can raise a green-on-failure suspicion, but no
surface names the checkmark and no surface says anything is *wrong*.
The probe proves the catch is incidental: same defect in the same color
scores 97.4 with a perfect object match. This entry exists to be fixed
against: a glyph-classification pass over detected icon regions should
flip instrument+reasoning to CAUGHT — the contradiction is then a
one-line reasoning call on facts the record actually contains.
