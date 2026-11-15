# VERDICT: text-truncation — MISS

## Defect planted

`defect.png` (840×560) is a settings-style card on a gray app background.
The card title "Quarterly Revenue Overview Report" is set in a fixed-width
container with `overflow: hidden` semantics: the clip lands at the card's
right padding edge (img x=556) **mid-glyph** — the 'o' of "Report" is
vertically sliced, left bowl shown, right side gone. No ellipsis; the
sloppy version agents ship when they forget `text-overflow`. Verified
programmatically: defect ink stops at x=555 while the control render has
ink through x=562 for the same glyph (see `make_images.py`).

`control.png` is the same card with the clip wide enough for the full
title (+12px slack); card is 39px wider, everything else identical.

This is deliberately *interior* truncation — the cut happens at a card
edge, nowhere near the frame edge — the most common real-world shape of
this bug class.

## What eyes reported

### `uv run eyes layout defect.png --describe`

```
edge contact (bg #ececf4, strip 3px):
  top       0.0%
  right     0.0%
  bottom    0.0%
  left      0.0%

objects at edge:
    (none)

bbox overlaps:
    (none)
```

`control.png --describe` produced the identical clean report. All three
layout detectors are frame-edge-only; an interior `overflow:hidden` clip
has no surface.

### `uv run eyes describe defect.png` (text records)

```json
{"string": "Quarterly Revenue Overview Rep", "bbox": [171, 250, 662, 306], "score": 0.762}
```

The truncated title OCRs as "…Rep" — the sliced 'o' is dropped entirely.
Note the bbox ends at x=662/1000 ≈ img x=556, flush with the clip
boundary: the record carries the geometric fact of the truncation.

### `uv run eyes describe control.png` (text records)

```json
{"string": "Quarterly Revenue Overview Repor", "bbox": [178, 250, 686, 307], "score": 0.775}
```

Even the clean control loses the final 't' to OCR — Mirage's glyph-level
read is lossy on this font/size.

### `uv run eyes score control.png defect.png`

```
score: 95.2 / 100

  palette   94.2  {}
  objects   95.7  {'matched': 11, 'missing': [], 'extra': ['dialog box']}
  layout    91.2  {'mean_center_dist': 0.0307, 'pairs': 11}
  text      97.8  {}
  scene    100.0  {}
```

Text component 97.8 — a whisper, not a signal. `layout` 91.2 reflects
the honest card-width difference, not the defect.

## Verdict

**MISS.** No detector fired. The defect is real, typical (fixed-width
card + long title + no ellipsis is the canonical agent-shipped truncation),
and the instrument walked past it on every surface:

- layout: blind by construction — all three detectors measure the *frame*
  boundary, and this clip is 200+px inside the frame.
- describe: the truncated string is in the record ("…Rep"), but describe
  is perception, not detection — nothing marks it, and "Rep" is a
  plausible-looking prefix.
- score: text=97.8 because OCR is lossy enough that even the control
  misreads ("…Repor"), so a 2-glyph truncation can't resolve above noise.

## Instrument gaps this case exposes

1. **No container-edge concept.** `edge_contact`/`objects_at_edge` only
   know the image frame. Truncation at an *interior* boundary (card,
   sidebar, table cell) — the dominant real-world shape — has zero
   coverage. A detector needs "text/content bbox ending flush against a
   detected card edge" as the signature.
2. **`objects_at_edge` never scans `text` records.** The `text` array
   carries `string`+`bbox`+`score`, and the defect's title bbox ends
   exactly at the clip line (x=662 vs control 686) — but the edge scan
   iterates `objects` only. Even extended to interior edges, the data is
   already there.
3. **OCR string-diff can't resolve small truncations.** `score_text`
   uses SequenceMatcher on normalized strings; control itself drops a
   glyph ("Report"→"Repor"), so defect-vs-control delta is ~0.02. The
   geometric signal (bbox flush to a container edge) is far stronger than
   the lexical one and is currently unused.

Re-run target: a `text_at_edge`-style detector over `record["text"]`
bboxes against detected region/card boundaries should flip this to
CAUGHT — the bbox evidence is already in the record today.

## Re-run 2026-11-15 — still MISS, root cause found

`text_edge_flush` + `interior_edge_lines` added: detects text bboxes
landing flush against strong interior gradient lines (container
boundaries). On the defect image it found **zero vertical edge lines** —
the `overflow:hidden` clip boundary is pixel-invisible (no border, same
background). There is no geometric edge to flush against.

Remaining signatures, honestly assessed:
- mid-glyph ink cutoff at the text bbox's right edge — needs
  component-level CV (is the last glyph component sliced?), beyond v0
  bbox geometry
- OCR string ending in a word fragment ("Rep") — a lexical heuristic,
  weak alone since abbreviations exist; possible future signal

MISS stands. This defect class needs either glyph/component analysis or
a language prior — recorded so the next instrument iteration knows
where the wall actually is.
