# VERDICT: z-order — MISS (instrument alone) / PARTIAL (instrument + pairwise + reasoning)

## Defect planted

`defect.png` / `control.png` (960×720) — a mock "Projects" list page:
white app bar, three stacked project cards, each with a "…" overflow
button. Card 1's dropdown menu is open, hanging down over card 2.

**The defect (defect.png): wrong paint order / stacking context.**
Cards 2 and 3 are painted *after* the menu element, so card 2's opaque
white surface covers the menu's lower half. Concretely: menu item
"Duplicate" is sliced **horizontally mid-glyph** at card 2's top edge
(y=237), items "Archive" and "Delete" are completely invisible, and the
menu's bottom border + drop shadow are cut off mid-air. This is the
canonical agent z-index bug — the popover lost the paint-order fight to
a later sibling (missing `z-index`, or an ancestor stacking context).

`control.png` is the identical scene with the menu painted last —
correct z-order — all four items and full menu chrome float above card
2. The only intended pixel difference is the menu∩card-2 region;
`ImageChops.difference` bbox = **(606, 237, 818, 335)** — exactly the
occlusion zone, nothing else.

Verified programmatically before running eyes:

- defect: "Duplicate" ink rows stop at y=236; y=238 is card-2 border
  gray `(229,231,235)`. Control: same glyphs continue to y=243.
- defect: **0** red "Delete" pixels in the item-4 zone; control: **152**.
- defect OCR read of the sliced item: `'n..Eaakn'` — control reads
  `'Duplicate'` cleanly (score 0.748).

`make_images.py` (PIL, RGBA overlay for the fake menu shadow)
regenerates both.

## What eyes reported

### `uv run eyes describe defect.png --stats`

Mirage read the visible menu items and the sliced one as garbage:

```json
{"string": "Rename",     "bbox": [644, 265, 718, 299], "score": 0.779}
{"string": "n..Eaakn",   "bbox": [645, 311, 721, 335], "score": 0.616}
```

`'n..Eaakn'` is the horizontally-sliced "Duplicate" — its bbox
(denorm → px y ≈ 224–241) straddles card 2's top edge at y=237. **"Archive"
and "Delete" are absent from the record entirely** — hidden content is
hidden from perception too. No object is named `menu`, `dropdown`,
`popup`, or anything popover-shaped; menu items are filed as generic
`text`/`button` objects. Mirage's `reasoning` field is **identical** to
the control's (`"white window with blue buttons, green and purple
buttons, black text … cannot know software name or purpose"`) — the VLM
narrative does not register the occlusion.

### `uv run eyes layout defect.png --describe`

```
edge contact (bg #f4f4f4, strip 4px):  all 0.0%
objects at edge:
  text    top   score=0.554  suspect=False   (app-bar title — both images)
  button  top   score=0.443  suspect=True    (app-bar buttons — both)
  button  top   score=0.514  suspect=False
  window  all4  score=0.353  suspect=True    (Mirage noise; control's
                                             window box differs)
bbox overlaps:
  {'a': 'text', 'b': 'text', 'iou': 0.413}
text flush at interior edge: (none)
legibility flags: 11 hits — all mock noise (white-on-blue "New project",
  single-letter chip reads 'w'/'M'/'B', gray meta text), identical class
  on control. The sliced 'n..Eaakn' is NOT flagged — its visible
  top-half pixels are still dark-on-white, contrast is fine.
```

**The one `bbox_overlaps` hit is not the defect.** Replaying
`bbox_overlaps` on the saved records shows the pair is card 2's name and
meta lines detected as two overlapping `text` objects
(`[212,379,368,436]` × `[212,401,425,447]`, iou 0.413, containment 0.61).
Control reports the same pair at iou **0.416** — Mirage duplicate-text
detection noise, present in both images. Meanwhile control detects the
whole visible menu as one `button` object (`[625,245,856,446]`,
score 0.497); defect has no menu-sized object at all — the visible sliver
wasn't detected as a unit.

### `uv run eyes score control.png defect.png`

```
score: 85.8 / 100
  palette   94.9  {}
  objects   91.9  {'matched': 17, 'missing': ['text', 'button', 'button'],
                  'extra': []}
  layout    55.6  {'mean_center_dist': 0.1554, 'pairs': 17}
  text      89.0  {}
  scene    100.0  {}
```

The three missing objects are the hidden menu items + the menu-as-button
— pairwise scoring names *that* entities vanished vs the reference, at
the right locus. But "missing" is agnostic: occlusion, deletion, and
state-change produce the identical signature. `layout` 55.6 is the
largest component drop (driven by 'n..Eaakn'↔'Duplicate' center shift
and dropped pairs) — real but unattributed.

### `uv run eyes ask defect.png -q "Is any content hidden, overlapped,
or layered incorrectly?"`

The evidence pack contains: scene, 17 generic objects (no menu/popup),
16 text strings **with bboxes stripped** — including `'Rename'` (0.779)
and the corrupted `'n..Eaakn'` (0.616) — the same noise `bbox_overlaps`
pair, 11 mock-noise legibility flags, `text_edge_flush: []`,
`status_icons: 0 candidates`, a normal `hue_census`. Nothing in the pack
says "menu", "occluded", "sliced", or names any overlap involving the
corrupted string.

## Reasoning-layer verdict (me, answering the ask-pack question)

Citable facts: two adjacent menu-item-shaped strings — `'Rename'` clean,
`'n..Eaakn'` gibberish — followed by card strings; OCR noise floor in
this record is high (`'w'`, `'M'`, `'B'` single letters appear in **both**
images). Under the pack's own instruction ("report facts you can cite;
say 'insufficient evidence' rather than guessing"), the honest answer:

> One text string ('n..Eaakn') is unreadable garbage between what appear
> to be menu items — possibly a partially-rendered or occluded label —
> but the pack carries no geometry, no named overlap, and no evidence
> that additional content exists but is hidden. **Insufficient evidence
> to confirm hidden/overlapped content.**

That is suspicion without a cause: the reasoning layer can flag the
anomaly, cannot connect it to occlusion, and cannot know items are
missing (absence is only visible against a reference the pack doesn't
have). Generous reading: PARTIAL. Strict evidence-only reading: MISS.

## Verdicts

- **Instrument alone (describe + layout, single image): MISS.** Every
  detector output is either clean or identical mock noise on the
  control; the corrupted OCR string sits unflagged in the record; the
  VLM's own reasoning narrative is unchanged defect-vs-control.
- **Instrument pairwise (`score` vs control): PARTIAL.** Composite 85.8;
  `objects` names the three vanished entities, `layout` 55.6 is the
  loudest component — enough to aim a diff, nothing that says
  *occlusion* rather than deletion/state-change.
- **Instrument + reasoning (`ask`): PARTIAL (weak).** The pack surfaces
  the corrupted string `'n..Eaakn'` — the only defect-attributable fact
  that reaches the reasoning layer — but with no bbox, no named overlap,
  and no menu concept, the layer can raise a flag and nothing more.

## Instrument gaps this case exposes

1. **No occlusion/slice detector exists.** The signature is computable
   today: a text bbox *bisected* by an interior edge line
   ('n..Eaakn' px-y 224–241 vs card-2 top edge y=237), or ink rows
   terminating flush at a foreign boundary. `text_edge_flush` only
   checks bbox edges landing ON lines — it never checks a line cutting
   *through* a bbox's interior, which is precisely the occlusion shape.
   (Same wall text-truncation hit on the vertical axis; this is the
   horizontal-axis sibling.)
2. **The ask pack strips the geometry that matters.** `text` entries
   carry `string`+`score` only — no bbox. With bboxes, 'n..Eaakn' at
   least *looks* clipped; without them it's indistinguishable from
   Mirage's usual OCR noise ('w', 'M', 'B' appear in both images).
3. **Hidden content is invisible without a reference.** "Archive" and
   "Delete" leave zero trace in the defect's record — correct behavior
   for perception, but it means single-image instruments *cannot* see
   the worst half of this defect class. Only pairwise (`score`) or
   temporal (`reel`) context can name absence; and even then "missing"
   doesn't distinguish occluded from deleted.
4. **`bbox_overlaps` measures box geometry, not paint order.** It fired
   on identical Mirage noise in both images while the real occlusion —
   a text line sliced by a card edge — produced no flag, because the
   covered content was never detected as an object to overlap *with*.
   Overlap detection needs the *occluding* surface and the *occluded*
   content to both be perceived first; here perception itself was the
   casualty.
5. **VLM narrative is occlusion-blind.** Mirage's `reasoning` string is
   character-identical defect-vs-control — the semantic layer doesn't
   model layering at all.

## What would catch this

Concrete instrumentation, cheapest first:

1. **Mid-bbox edge-bisection check (~30 lines, extends existing
   detectors).** `interior_edge_lines` already finds candidate container
   boundaries; `text_edge_flush` already denorms text bboxes. Add the
   missing predicate: flag any text bbox that an edge line passes
   *through* (line_y strictly inside [y0, y1], not within tol of an
   edge) — "text bisected by a boundary" is the occlusion signature,
   distinct from flush-truncation. On this artifact: card-2's top edge
   (y≈237) bisects 'n..Eaakn' (224–241) → named fact. Deterministic,
   no model, flips single-image instrument-alone to CAUGHT for the
   sliced-item half of the defect.
2. **Ink-continuation profile (component CV, same wall as
   text-truncation's vertical slice).** Within a flagged text bbox,
   compute the horizontal ink projection; a hard zero-band mid-glyph-row
   at a straight y, coincident with a detected edge line, confirms
   "sliced" vs "stylized font". This is the falsifier for #1's false
   positives (text legitimately crossing a border, e.g. labels on
   dividers).
3. **Occlusion-vs-absence classifier for `score_pair`/`reel`.** When an
   object is missing vs reference, sample its reference bbox region in
   the candidate: if the region contains *foreign structured content*
   (edges, text-like ink, a different surface) rather than uniform
   background, classify `occluded` not `deleted`. Here the missing
   menu-item bboxes land inside card 2's white surface with card-2 ink
   present — distinguishable from object-dropout's badge→card-white
   erase signature. Turns the existing `missing: [...]` list into an
   attributed fact.
4. **Ask-pack geometry + edge findings.** Include text bboxes in pack
   `text` entries and emit the #1 bisection finding under `findings`.
   Then the reasoning layer can cite "'n..Eaakn' is bisected by a card
   edge at y≈237" — a one-line judgment call, exactly the PRD's
   facts-out/judgment-department split. The fully-hidden items still
   need #3's pairwise context; single-image absence is a hard wall,
   recorded honestly.

## Verdict

**PARTIAL overall — MISS instrument-alone.** The defect is real,
typical (missing z-index / stacking-context on a popover is the most
common layering bug agents ship), and demonstrably exhibited: mid-glyph
horizontal slice verified at y=237, two items + shadow fully hidden,
diff confined to (606,237,818,335). The instrument saw the *visible
sliver* — OCR'd 'Rename', mangled 'Duplicate' into 'n..Eaakn', dropped
'Archive'/'Delete' — but no detector, flag, or narrative names any of
it. The corrupted string is the single fact that reaches the ask pack,
and it arrives without the geometry needed to read it. This entry
exists to be fixed against: the mid-bbox edge-bisection check (#1) is
deterministic, cheap, and would have named the slice on the first run.
