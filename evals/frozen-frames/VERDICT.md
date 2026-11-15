# VERDICT: frozen-frames — CAUGHT

## Defect planted

`frame_01..05.png` — five frames of a typical macOS-style "Importing
Photos" progress dialog (progress bar advancing 20→45→70→90%, spinner
arc rotating, status line changing per frame). **The defect: `frame_03.png`
is a byte-identical copy of `frame_02.png`** (md5 `189f91de…` for both) —
a frozen render mid-animation: the draw loop kept the previous frame
instead of advancing state, then motion resumed at frame 4. This is the
most typical instance of the class: a duplicated/stuck frame in an
otherwise healthy sequence, not an adversarial construction.

Built by `build_frames.py` (PIL, in this directory).

## What eyes reported — pixel-only (`--no-records`)

```
5 frames, records=off

frame_01.png -> frame_02.png: changed 1.4%  mean|d| 1.72
frame_02.png -> frame_03.png: changed 0.0%  mean|d| 0.0
frame_03.png -> frame_04.png: changed 1.5%  mean|d| 1.79
frame_04.png -> frame_05.png: changed 1.3%  mean|d| 1.49
```

## What eyes reported — with Mirage records

```
5 frames, records=on

frame_01.png -> frame_02.png: changed 1.4%  mean|d| 1.72  labels 0.75  ocr 0.80
frame_02.png -> frame_03.png: changed 0.0%  mean|d| 0.0  labels 1.00  ocr 1.00
frame_03.png -> frame_04.png: changed 1.5%  mean|d| 1.79  labels 0.75  ocr 0.80
frame_04.png -> frame_05.png: changed 1.3%  mean|d| 1.49  labels 0.40  ocr 0.80
```

## Why this is CAUGHT

The frozen pair is the **only** pair in the reel reporting `changed 0.0%`
/ `mean|d| 0.0`, and `frame_diff` omits `diff_bbox` entirely when nothing
changed (test-pinned behavior: `assert "diff_bbox" not in r`). Surrounded
by pairs moving ~1.3–1.5%, a zero pair mid-sequence is an unambiguous
fact — the instrument's contract is "report facts; judgment belongs to
the reasoning layer," and the fact here is reported at full strength.

The record layer adds a corroborating tell: the frozen pair is also the
**only** pair with `labels 1.00 / ocr 1.00` — the "too coherent" pair.
Perfect semantic stability on identical pixels is exactly what a dead
frame produces; a reasoning layer reading this JSON sees motion →
perfect stillness → motion resuming, which is a frozen frame, not a
transition.

## Instrument gaps / signals observed

1. **No freeze detection, no baseline.** `reel` reports raw diffs with
   no threshold and no sequence-level summary. CAUGHT here depends
   entirely on the reader noticing the lone `0.0%` — fine for an exact
   duplicate, but nothing flags it.
2. **"Suspiciously low motion" is unmeasured.** Probe (not part of the
   catalog): two frames differing only by a 14×14 status dot →
   `changed 0.1% mean|d| 0.15`. Nonzero but ~10× below this sequence's
   real motion (~1.4%). The instrument happily reports `0.1%` the same
   way it reports `1.4%` — distinguishing "barely moving" from "moving"
   is entirely the reasoning layer's job. A `min_changed_pct` or
   per-reel motion baseline would be the natural detector.
3. **Coherence metrics reward the defect.** `labels`/`ocr` score
   *stability*, so a frozen frame scores a perfect 1.00/1.00 — the
   highest possible "good" value. Read naively, the frozen pair looks
   like the *best* transition in the reel. The defect is only visible
   by cross-referencing the pixel diff, which is the right composition
   but worth stating: stability metrics are defect-blind without the
   motion floor.
4. **Ambiguity boundary:** a duplicate *final* frame (animation end
   state) produces the identical `0.0%` signature — legitimate hold vs.
   stall is indistinguishable at the fact level. The mid-sequence
   position (motion resumes after) is what makes this instance
   unambiguous; the instrument supplies pair order via file names but
   no positional semantics.
5. **Mirage record noise on synthetic UI.** `eyes describe
   frame_02.png` hallucinates objects (`checkmark icon`, three
   `button`s on a title bar) and OCRs `Copying flles...` — yet the
   label/ocr Jaccard signals still behaved correctly for this case
   because identical inputs produce identical records. On noisier
   real captures the 1.00/1.00 tell could degrade.

## Verdict

**CAUGHT.** The defect is typical, the artifact demonstrably exhibits
it (byte-identical frames 2/3, md5-verified), and the instrument
surfaces it at full signal strength: the frozen pair is the lone
`0.0% / mean|d| 0.0` with no `diff_bbox`, plus perfect 1.00/1.00 record
coherence. No detector names it — consistent with the instrument's
facts-not-verdicts contract — but nothing needed to catch this was
missing from the output.
