# VERDICT: semantic-data — MISS (instrument-alone) / CAUGHT (instrument+reasoning, audit-question dependent)

## Defect planted

`defect.png` / `control.png` (680×660) — a mock "Acme Coffee Roasters"
invoice card: merchant header, invoice number + date, four line items
with right-aligned amounts, then Subtotal / Tax (8%) / Total, footer
notes. Clean document aesthetic, nothing visually wrong.

**The defect: the SUBTOTAL is bound to the wrong value — $87.50 instead
of the $77.50 the four line items actually sum to** (off by exactly
$10.00, the classic stale-binding/hardcoded-total agent bug). Tax and
Total are then derived *correctly from the wrong subtotal*:

```
items:   $38.00 + $19.00 + $14.50 + $6.00 = $77.50
DEFECT:  Subtotal $87.50 · Tax (8%) $7.00 · Total $94.50
         — 8% × 87.50 = 7.00 ✓ · 87.50 + 7.00 = 94.50 ✓ — internally
           consistent, wrong vs the items. ONLY summation catches it.
CONTROL: Subtotal $77.50 · Tax (8%) $6.20 · Total $83.70 — correct.
```

`ImageChops.difference` bbox = **(519, 367, 559, 450)** — the diff is
confined to the amounts column of the three totals rows; every label,
item, and glyph position is identical. `make_images.py` (PIL, Arial)
regenerates both and asserts the arithmetic.

## What eyes reported

### `uv run eyes describe defect.png --stats`

Mirage read **every number correctly**, including the wrong one:

```json
{"string": "$38.00",  "score": 0.649, "bbox": [755, 266, 842, 303]}
{"string": "$19.00",  "score": 0.559, "bbox": [753, 322, 842, 362]}
{"string": "$14.50",  "score": 0.646, "bbox": [753, 380, 843, 419]}
{"string": "$6.00",   "score": 0.813, "bbox": [767, 438, 844, 476]}
{"string": "Subtotal","score": 0.568, "bbox": [153, 546, 250, 581]}
{"string": "$87.50",  "score": 0.602, "bbox": [755, 545, 842, 583]}
{"string": "Tax (8%)","score": 0.778}
{"string": "$7.00",   "score": 0.822}
{"string": "Total",   "score": 0.7}
{"string": "$94.50",  "score": 0.757}
```

Scene: `{"background": "white", "style": "document"}`; one `form`
object (score 0.875); Mirage's `reasoning` field is identical
defect-vs-control ("white rectangular form with black text… the form's
purpose and the text content are not readable"). Minor OCR noise in
both: `'Chemex flters 100ct'` drops an 'i'; the footer produces two
overlapping reads (`'Questions about this inv'` + the full string).
Control's describe is the same shape with `$77.50 / $6.20 / $83.70`.

### `uv run eyes layout defect.png --describe`

```
edge contact: all 0.0%          objects at edge: form top,bottom
                               suspect=False (both images)
bbox overlaps: (none)           text flush at interior edge: (none)
edge bisects: (none)
legibility flags: 6 — all shared mock noise, byte-identical class on
  control ('Invoice #1042…' low_contrast, '$19.00' + 'Subtotal' +
  'Thank you…' low_ocr_confidence, footer duplicate reads).
```

Nothing defect-attributable. The wrong number is dark-on-white,
correctly typeset, mid-frame.

### `uv run eyes score control.png defect.png`

```
score: 98.2 / 100
  palette   95.6  {}
  objects   99.6  {'matched': 18, 'missing': [], 'extra': [],
                  'attr_sim': 0.9964, 'attr_changes': []}
  layout    99.9  {'mean_center_dist': 0.0002, 'pairs': 18}
  text      96.3  {}
  scene    100.0  {}
```

`score_text` is SequenceMatcher best-match over normalized strings —
the three changed amounts ('87.50'↔'77.50', '7.00'↔'6.20',
'94.50'↔'83.70') are similar enough to score 96.3. The component says
*"3 strings differ from the reference,"* never *"a number is wrong."*
Pairwise diff is structurally blind to plausible-wrong data: a wrong
value that looks like a value matches fine.

### `uv run eyes ask defect.png -q "Do the line items on this invoice
add up to the subtotal shown? Check the arithmetic."`

The pack carries **every fact needed, correctly OCR'd, with bboxes**:

- `text`: all four item amounts + all three totals values + labels
- `findings`: only shared mock noise (the `form` edge object, legibility
  flags identical on control); `bbox_overlaps`/`text_edge_flush` empty
- `detectors`: `hue_census` → `insufficient_chroma`,
  `anisotropy` → `insufficient_witnesses`, `lexical_screen` flags only
  product names (`'Ethiopia Yirgacheffe'`, `'Colombia Huila'`,
  `'Chemex flters'` — OOV coffee terms) + footer OCR noise;
  `frag_bands` fires on the footer duplicate reads, unrelated.
  `status_icons_error`: `"cannot unpack non-iterable NoneType object"`
  — glyph classifier crashes when no icon candidates exist (pack noise
  worth noting).

## Reasoning-layer verdict (me, answering the ask-pack question)

Pairing strings to rows by bbox-y overlap (item rows y≈266–476, totals
rows y≈545–691 — cleanly separated):

> Items: $38.00 + $19.00 + $14.50 + $6.00 = **$77.50**.
> Subtotal shown: **$87.50** → **$10.00 unexplained gap.**
> Totals block is internally consistent: 8% × 87.50 = 7.00 ✓;
> 87.50 + 7.00 = 94.50 ✓. No discount/credit line appears in the
> record, so the gap is not itemized anywhere.
>
> **The invoice is arithmetically inconsistent — the subtotal does not
> match its line items. CAUGHT.**

Hedges, honestly stated: '$19.00' OCR'd at 0.559 (flagged
`low_ocr_confidence`) and 'Subtotal' at 0.568 — mid-confidence reads;
a stricter evidence-only layer could hedge on the item sum, though all
four amounts sit in the same band and none is disqualifying. And the
catch is **question-dependent**: `ask` is question-agnostic — the pack
is identical for any query; nothing in the instrument ever computes or
prompts arithmetic. An unprompted "describe this document" consumer
that never audits numbers would walk past it exactly as the detectors
did.

## Verdicts

- **Instrument alone (describe + layout): MISS.** Clean bill of health
  on a document whose central number is wrong.
- **Instrument pairwise (`score` vs control): PARTIAL (whisper).**
  98.2 with `text` 96.3 — names that three strings differ, cannot say
  any is *incorrect*. Wrong-but-plausible is invisible to string-diff
  scoring by construction.
- **Instrument + reasoning (`ask` + arithmetic question): CAUGHT.**
  The pack contains every required fact — amounts, labels, row
  geometry — correctly OCR'd. The reasoning layer sums, compares, and
  names the $10.00 gap plus the self-consistent-but-wrong totals
  block. Conditional on the consumer asking the audit question.

## Instrument gaps this case exposes

1. **No numeric-consistency layer exists anywhere.** Every detector is
   perceptual or geometric; "the numbers don't add up" has no surface
   short of ask+reasoning. This is the entire defect class: meaning-
   wrongness on perception-right input.
2. **`score_text` can't see plausible-wrong values.** SequenceMatcher
   similarity treats '$87.50' vs '$77.50' as near-identical — correct
   for detecting *change*, useless for detecting *incorrectness*. A
   pairwise diff can only ever say "differs," and a wrong value in a
   world with no reference is undetectable by diff at all.
3. **The pack is sufficient — but nothing prompts the check.** Unlike
   semantic-surprise (decisive fact never entered the record), here
   every fact arrives correctly. The gap moved downstream: the consumer
   must know to ask. `ask`'s question field is the only audit trigger.
4. **Currency OCR confidence is middling.** '$19.00' at 0.559 and
   'Subtotal' at 0.568 get flagged `low_ocr_confidence` — an evidence-
   strict reader could honestly hedge the sum. Worth recording: the
   catch rests on trusting ~0.6-confidence currency reads.
5. **Pack noise:** `status_icons_error` leaks a crash string
   (`cannot unpack non-iterable NoneType`) instead of a clean empty
   result when no icon candidates exist.

## What would catch this

1. **`totals_consistency` detector (primary, deterministic).** Parse
   currency/number tokens from `record["text"]`, group into rows by
   bbox-y overlap (already in the records), classify rows via a small
   label lexicon (item / Subtotal / Tax / Total / Discount / Shipping),
   then check the arithmetic identities: `Σ items = Subtotal`,
   `Subtotal + Tax = Total`, `Tax = rate × Subtotal`. On this artifact:
   `line_items_sum_mismatch: items=77.50 subtotal=87.50 delta=10.00` —
   a named finding, instrument-alone CAUGHT for the additive-checkable
   subset of the class (invoices, carts, order summaries, budgets).
   ~150 lines, no model, reuses existing bbox geometry.
2. **Structured `numbers` section in the ask pack (cheap partial).**
   Emit parsed `{label, value, row_bbox}` triples so any consumer gets
   row-pairing for free instead of re-deriving it from raw strings.
   Doesn't detect anything itself — makes the reasoning-layer check a
   one-liner and drops the bbox-pairing burden that today only a
   careful reader performs.
3. **Standing audit protocol (architectural).** The catch required the
   right question. A consumer-side policy — "on document-style scenes,
   verify all stated arithmetic" — turns this from lucky-question CAUGHT
   into systematic CAUGHT. `ask`'s pack already supports it; the gap is
   that nothing schedules the question.

## Verdict

**MISS instrument-alone / CAUGHT instrument+reasoning (conditional).**
This is the cleanest demonstration yet of the PRD's facts-out/judgment-
department split working *and* of where it strains: the evidence pack
carried 100% of the decisive facts — every amount, every label, the row
geometry — and the reasoning layer caught the $10.00 discrepancy in one
pass. But the instrument itself saw a flawless document, pairwise
scoring saw "3 similar strings differ," and nothing anywhere computes
that 38+19+14.5+6 ≠ 87.5. The defect class lives entirely in the
question the consumer thinks to ask. This entry exists to be fixed
against: a `totals_consistency` detector over the already-recorded
bboxes would flip instrument-alone to CAUGHT without any model in the
loop.
