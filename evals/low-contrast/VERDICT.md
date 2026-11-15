# VERDICT: low-contrast — MISS

## Defect planted

`defect.png` is a mock checkout UI ("Order #1042" summary card, 900×680).
The footer fine print — three lines of terms text at 15px Arial on the
white card — is rendered in `#d6d6d6`, a **1.45:1 contrast ratio** against
the `#ffffff` card (WCAG AA needs 4.5:1 for body text). This is the
classic agent theming/token bug: a "muted text" or "tertiary" token that
resolved to near-background. Everything else on the card — title, line
items, total, blue "View details" button — is readable, so any signal is
attributable to the one element.

`control.png` is the identical layout with the footer in `#6b7280`
(**4.83:1**, readable muted gray). `make_artifact.py` regenerates both.

Contrast verified numerically before running eyes: footer glyph pixels
are `(214,214,214)` on `(255,255,255)`; control glyphs `(107,114,128)`.

## What eyes reported

### describe defect.png --stats (abridged — full record in transcript)

Mirage read **all three low-contrast lines correctly**:

```json
"text": [
  {"string": "Prices are estimates. Final amount is calculated at checkout",
   "bbox": [282, 772, 722, 803], "score": 0.494},
  {"string": "and may differ. Delivery times shown in UTC. See terms fo",
   "bbox": [285, 809, 710, 839], "score": 0.669},
  {"string": "details and refund policy before confirming your order.",
   "bbox": [295, 844, 698, 873], "score": 0.757}
]
```

No legibility flag, no warning. The record describes the scene as
`"white dialog box with blue button, black text labels"` — Mirage reports
the footer text objects with `description.color: "black"` even though the
glyphs are `#d6d6d6`. Every "text label" object claims black.

### describe control.png --stats

Same 14 strings, same layout. Footer OCR scores:

```
'and may differ. Delivery times shown in UTC. See terms for'   0.782
'Prices are estimates. Final amount is calculated at checkout'  0.577
'details and refund policy before confirming your order.'       0.841
```

### score defect.png control.png

```
score: 97.9 / 100

  palette   95.8  {}
  objects   96.5  {'matched': 14, 'missing': ['text label'], 'extra': []}
  layout   100.0  {'mean_center_dist': 0.0001, 'pairs': 14}
  text      99.9  {}
  scene    100.0  {}
```

A 1.45:1-contrast footer scores **97.9** against the readable control.
The text component is 99.9 because OCR succeeded — `score_text` compares
string content only and discards per-string confidence.

### layout defect.png --describe

```
edge contact (bg #fcfcfc, strip 4px):
  top 0.0%  right 0.0%  bottom 0.0%  left 0.0%
objects at edge:
  {'name': 'dialog box', 'sides': ['top', 'bottom'], 'bbox': [122, 45, 883, 965],
   'score': 0.847, 'suspect': False}
bbox overlaps:
  {'a': 'text label', 'b': 'text label', 'iou': 0.199}
```

Control reports the identical `dialog box` top/bottom edge flag (score
0.838) — an artifact of the card filling most of the frame height, present
in both images, not defect-attributable. Defect adds one `text label` ×
`text label` bbox overlap (iou 0.199); control has none. Noise-level,
nothing ties it to contrast.

### palette

```
defect:  #fcfcfc 61.3%  #f4f4f4 33.3%  #2464ec 1.3%  #ececf4 1.1%  #ececec 0.5%
control: #fcfcfc 60.8%  #f4f4f4 32.3%  #2464ec 1.3%  #ececf4 1.2%  #d4d4dc 0.3%
```

The defect gray `#d6d6d6` never reaches the top-8 palette — the glyph
pixels are too few. Control's darker gray surfaces as `#d4d4dc`/`#ccccd4`
bins at 0.3% each. Palette sees a difference but cannot name it.

## Sub-signals present in the raw record (unsurfaced)

- **OCR confidence dropped consistently on the defect footer**:
  0.494/0.669/0.757 vs control's 0.577/0.782/0.841 — a ~0.08–0.11 drop on
  all three lines, the only place the instrument's own numbers register
  the legibility loss. `score_text` discards these scores; nothing
  thresholds them.
- **`object_color_stats` measures the footer bboxes** — mean_hex
  `#fafafa`/`#f9f9f9` — but bbox means are dominated by white card; the
  glyph pixels are a sliver. No code compares text color to its surround.
- **Mirage's `description.color: "black"` is wrong** for the footer
  objects — the VLM overclaims color on low-contrast text, so even the
  semantic layer can't be trusted as a contrast oracle.

## Instrument gaps this case exposes

1. **No legibility/contrast detector exists.** The stack covers layout
   geometry, palette histogram, object identity, and OCR *content* — but
   nothing computes local contrast between foreground content and its
   immediate background. This is the whole defect class, and it is fully
   dark.
2. **OCR confidence is recorded then thrown away.** Per-string `score`
   fields show a clean monotonic drop under low contrast (0.494 vs 0.577,
   0.669 vs 0.782, 0.757 vs 0.841). A min-confidence or control-diff flag
   would surface this case for free — same pattern as clipped-card's
   discarded detection scores.
3. **Mirage OCR is contrast-robust — good news, wrong instrument.** It
   read 1.45:1 text essentially perfectly (one truncation: "terms fo[r]").
   OCR succeeding means the *content* pipeline works; legibility is a
   separate human factor the record never models.

## Verdict

**MISS.** The defect is real, typical (muted-token resolved to
near-background — the single most common theming bug agents ship), and
the instrument walked past it at every layer: OCR read it, palette
ignored it, layout saw nothing, and the pairwise score called the defect
97.9% identical to the readable control. This entry exists to be fixed
against: a local-contrast detector over detected text bboxes (glyph
pixels vs surround, not bbox mean) or an OCR-confidence floor should
flip this to CAUGHT.

## Re-run 2026-11-15 — CAUGHT (after legibility detector)

`eyes/legibility.py` added: per-text-region WCAG-style contrast
(2nd/98th percentile inside bbox) + OCR-confidence floor, surfaced in
`eyes layout --describe` under `legibility flags`.

Defect case now reports the planted footer fine print verbatim:

```
'and may differ. Delivery times shown in UTC. See'  contrast 1.18  low_contrast
'Prices are estimates. Final amount is calculated' contrast 1.18  low_contrast + low_ocr_confidence
'details and refund policy before confirming your' contrast 1.18  low_contrast
```

Also flags 'ORDER SUMMARY' (2.11) and 'View details' (2.46) — secondary
low-contrast elements in the same card; plausible true positives, noted
for the walk to judge. MISS → CAUGHT.
