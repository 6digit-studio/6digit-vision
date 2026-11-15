# VERDICT: totals-consistency — CAUGHT (detector scope)

## Gap filled

`evals/semantic-data/VERDICT.md`: an invoice mock whose **SUBTOTAL is
bound to the wrong value** — $87.50 instead of the $77.50 the four line
items sum to — while Tax (8%) and Total derive *consistently* from the
wrong subtotal. Instrument-alone verdict was **MISS**: every number is
dark-on-white, correctly typeset, mid-frame; `eyes score` saw "3 similar
strings differ"; only an `ask` + arithmetic question caught it, and only
because a reasoning layer chose to sum. The eval's own sketch named the
fix: a `totals_consistency` detector over the already-recorded bboxes —
"~150 lines, no model." This is that detector, productized (~560 lines
including docs/CLI; the check core is ~200).

## How it works (one paragraph)

Consumes `eyes describe` text records (image path → runs `eyes describe`;
or a saved describe `.json`). Records are clustered into visual rows by
transitive bbox-y overlap (same convention as lexical-screen). Each
amount-bearing row gets a label-role from a small lexicon checked in
order — `subtotal → tax(rate) → discount → shipping → fee → total →
item` fallthrough — and a value = its **rightmost** currency token
(`$`/`€`/`£`/`¥` prefix, optional `-`/`(`/`)` sign, optional K/M/B
magnitude; bare decimals require exactly two places so `2025`, `#1042`,
`250g`, `8%` never parse as money). Three identities are then checked:
`Σ signed(line rows) = Subtotal`, `Subtotal + Tax + charges − discounts
= Total`, and `Tax = printed_rate% × base` when a rate is printed. An
alternative hypothesis (H2) guards one real layout: shipping/fee rows
printed among the items but charged *after* the subtotal — it is
confirmed only when the item-only sum matches the subtotal AND the
total still reconciles, so it cannot launder a real mismatch.

Delta convention: `computed − stated` (line delta −10.00 = items fall
$10 short of the stated subtotal).

## Real output — defect (the eval case)

```
$ uv run detectors/totals-consistency/totals_consistency.py \
    evals/semantic-data/defect.png
```

```
evals/semantic-data/defect.png  text_records=19  amount_rows=7
    item          38.00  y=[267, 303]  'Ethiopia Yirgacheffe 250g $38.00'
    item          19.00  y=[325, 362]  'Colombia Huila 250g $19.00'
    item          14.50  y=[382, 419]  'Chemex flters 100ct $14.50'
    shipping       6.00  y=[440, 476]  'Standard shipping $6.00'
    subtotal      87.50  y=[546, 583]  'Subtotal $87.50'
    tax            7.00  y=[595, 634]  'Tax (8%) $7.00' (8%)
    total         94.50  y=[648, 691]  'Total $94.50'
  !! line_items_sum_mismatch: {"kind": "line_items_sum_mismatch",
     "line_sum": 77.5, "subtotal": 87.5, "delta": -10.0,
     "tolerance": 0.0875, "n_line_rows": 4, ...}
!! check line_items_sum  mismatch items=77.5 != subtotal=87.5 (delta=-10.0)
   check totals_block    ok       expected=94.5 == total=94.5
   check tax_rate        ok       8.0% x 87.5 = 7.0 == tax=7.0
  ~ note: alternative_hypothesis_failed
  VERDICT: TOTALS_INCONSISTENT
```

This is the exact signature the eval predicted: `line_items_sum`
mismatch names the $10.00 gap, while `totals_block` and `tax_rate`
report **ok** — the totals block is internally consistent and wrong only
against the items. Instrument-alone goes from MISS to CAUGHT for the
additive-checkable subset (invoices, carts, order summaries, budgets).

## Real output — control (must stay clean)

```
$ uv run detectors/totals-consistency/totals_consistency.py \
    evals/semantic-data/control.png
```

```
evals/semantic-data/control.png  text_records=19  amount_rows=7
    item          38.00  y=[267, 303]  'Ethiopia Yirgacheffe 250g $38.00'
    item          19.00  y=[325, 362]  'Colombia Huila 250g $19.00'
    item          14.50  y=[382, 419]  'Chemex flters 100ct $14.50'
    shipping       6.00  y=[439, 476]  'Standard shipping $6.00'
    subtotal      77.50  y=[546, 583]  'Subtotal $77.50'
    tax            6.20  y=[595, 635]  'Tax (8%) $6.20' (8%)
    total         83.70  y=[648, 691]  'Total $83.70'
   check line_items_sum  ok       items=77.5 == subtotal=77.5
   check totals_block    ok       expected=83.7 == total=83.7
   check tax_rate        ok       8.0% x 77.5 = 6.2 == tax=6.2
  VERDICT: TOTALS_CONSISTENT
```

Zero findings, all three identities verified. `--fail-on-inconsistent`
exits 1 on the defect record, 0 on the control (verified).

## Out-of-domain controls — honest silence

```
$ uv run detectors/totals-consistency/totals_consistency.py \
    evals/text-truncation/control.png evals/text-truncation/defect.png \
    evals/grid-misalign/control.png evals/grid-misalign/defect.png \
    evals/semantic-surprise/control.png evals/semantic-surprise/defect.png
```

- **text-truncation (both):** dashboard card with `$1.24M`, `$842K`,
  `$398K` stat rows (K/M magnitudes parsed correctly → 1,240,000 /
  842,000 / 398,000) but no totals labels → `INSUFFICIENT_STRUCTURE`,
  zero findings.
- **grid-misalign (both):** `NO_CURRENCY_AMOUNTS`.
- **semantic-surprise (both):** one stray `$49.00` transaction amount,
  no totals structure → `INSUFFICIENT_STRUCTURE`, zero findings. A lone
  amount with nothing to check against is reported, not guessed at.

## Synthetic probes (saved-record inputs, not eval images)

Six hand-built describe records exercised the paths the eval images
don't reach — all behaved as designed:

- **H2 layout** (shipping printed among items, charged post-subtotal:
  items $60 + ship-line $6, Subtotal $60, Tax 8% $4.80, Total $70.80)
  → `ok_alternative` + `shipping_fees_post_subtotal` note,
  `TOTALS_CONSISTENT`. The FP guard works: primary reading
  (66 ≠ 60) does not fire when the alternate reading fully reconciles.
- **Discount + tax-on-discounted-base** (items $80, Discount −$10,
  Tax 10% $7.00 on the $70 net, Total $77) → `TOTALS_CONSISTENT`;
  tax_rate check **demoted** to `tax_base_ambiguous` note rather than
  claiming 10%×80=8≠7 — shipping-taxability is jurisdiction-dependent
  and the detector refuses to overclaim.
- **Wrong tax, no adjustments** (Subtotal $100, Tax (10%) $15,
  Total $115) → `tax_rate_mismatch` finding, `TOTALS_INCONSISTENT` —
  catches the same "internally consistent, externally wrong" class as
  the eval defect, one level down.
- **Wrong total** (Subtotal $30 + Tax $3 → Total stated $40) →
  `totals_block_mismatch` expected=33.0 vs 40.0.
- **Cent rounding** (items $30.00 vs Subtotal $30.02) → forgiven inside
  the $0.05/0.1% tolerance, `TOTALS_CONSISTENT`.
- **No amounts** → `NO_CURRENCY_AMOUNTS`.

## Honest limits

- **The label lexicon is small and English.** `subtotal/tax/total/
  discount/shipping/fee` + item fallthrough. Brand collisions
  ("Total Wine $12.00" → `total` role), product names containing
  "tax"/"credit"/"handling", and non-English invoices degrade to
  misclassification — which can produce a wrong-role row, a skipped
  check (`unclassified_amount_in_totals`), or in the worst case a false
  mismatch. Same OOV-class limit lexical-screen documents.
- **Rightmost-amount heuristic.** Rows with multiple amounts
  ("2 @ $9.50 = $19.00", unit price + extended price) take the
  rightmost token — usually the extended price, but column order is an
  assumption, not a guarantee. Two-column invoice layouts can also merge
  unrelated label+amount pairs into one y-band.
- **US-style decimals only.** `1.234,56` European format does not
  parse; `$1.24M`-style K/M/B suffixes do. "million"/"billion" words do
  not.
- **Structure-gated.** No totals-labeled row (subtotal/total) → no
  checkable identity → `insufficient_structure`/`no_currency_amounts`.
  This is deliberate silence, but it means invoices whose totals use
  vocabulary outside the lexicon ("Amount due" is covered; "Sum",
  "Balance", "Qty total" partially) may be missed entirely.
- **Ambiguity → skip, not guess.** Multiple subtotal or total rows, an
  unlabeled amount row inside the totals block, or >1 tax row all skip
  the dependent check with a named note.
- **Tax-rate check is deliberately narrow.** Fires only with exactly
  one rate-printing tax row and a determinable base; any mismatch with
  adjustment rows (shipping/fee/discount) present is demoted to a note
  because the tax base legitimately varies. A wrong tax on a doc *with*
  adjustments is therefore a note, not a finding — precision over
  recall, stated plainly.
- **Tolerance is $0.05 or 0.1% of base, whichever is larger.** Forgives
  cent-level OCR noise; a genuine 3-cent error on an $80 document is
  inside tolerance. The defect's $10.00 gap is ~100× the floor.
- **Inherits Mirage's OCR.** The eval's own caveat stands: '$19.00'
  read at 0.559 and 'Subtotal' at 0.568 — the catch rests on trusting
  ~0.6-confidence currency reads. A misread digit changes a sum (false
  mismatch) or can mask a real one; per-record `score` is carried in the
  JSON output for consumers that want to weight evidence.
- **Discount sign is label-implied.** A `discount`-role row with a
  positive printed amount is treated as a reduction (the common
  convention); explicit `-`/`(`/`)` signs are honored first. A document
  that prints discounts as positive additions will be mis-summed.

## Verdict

**CAUGHT** — at detector scope, on the eval that named the gap. The
defect image produces `line_items_sum_mismatch: items=77.50
subtotal=87.50 delta=-10.00` while the internally-consistent totals
block reports ok — instrument-alone flips from MISS to CAUGHT for every
document whose arithmetic is checkable from OCR'd text. The control
stays clean, four non-invoice eval images stay silent, and six synthetic
probes confirm the check core fires on wrong-tax/wrong-total variants
and refuses to fire on consistent alternate layouts. Integration into
`eyes/` (e.g., as a describe-time finding or ask-pack section) is a walk
decision, not done here per the no-`eyes/`-edits constraint.
