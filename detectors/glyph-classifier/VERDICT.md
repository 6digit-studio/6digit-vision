# VERDICT: glyph-classifier — CAUGHT (detector scope)

## Gap filled

`evals/semantic-surprise/VERDICT.md`, instrument gap #1: **"No glyph-level
perception."** Mirage files the status emblem as `{"name": "logo",
"description": {"color": "green", "shape": "circular"}}` — the checkmark
inside it never reaches the record, so no reasoning layer can catch
"success glyph on a failed payment."

This detector consumes the `eyes describe` record, selects emblem/icon
objects, crops each Mirage bbox, separates container fill from the
interior glyph (flood-fill hole detection), skeletonizes both sides
(Zhang-Suen), and classifies against 10 rendered templates (check, x,
warning, info, spinner, download, trash, play, plus, minus) by symmetric
chamfer distance. Pure PIL + stdlib, no model. Output emits
`status_icons: {object_id: glyph}` plus per-region scores — the fact the
record was missing.

## How it works (one paragraph)

For each candidate object the crop's container color is the quantized
bin forming the **largest connected component** (the circle fill is one
big blob; glyph strokes and page margins are not — this survives both
loose bboxes and dense center glyphs, where center-patch and whole-crop
modes each fail). Pixels within Chebyshev-56 of that color are dilated
1px and flood-filled from the border; whatever is left over is an
enclosed interior mark — the glyph. The glyph mask is normalized to a
96px canvas (aspect preserved), skeletonized, and chamfer-matched
against skeletonized PIL-rendered templates. A label is emitted only
when best score ≤ 0.16 (normalized chamfer); otherwise `unknown` with
the nearest guess still reported.

## Real output — defect (should be check-ish)

```
$ uv run python detectors/glyph-classifier/glyph_classifier.py \
    evals/semantic-surprise/defect.png
```

```json
{
  "image": "evals/semantic-surprise/defect.png",
  "candidates": 1,
  "regions": [{
    "object_id": 1, "name": "logo", "mirage_score": 0.609,
    "position": "top center", "bbox_px": [392, 117, 490, 209],
    "container_hex": "#18a848", "container_hue": "green",
    "glyph_px": 566, "glyph_aspect": 1.293, "glyph_fill": 0.26,
    "scores": {"check": 0.0443, "play": 0.0734, "spinner": 0.0747,
               "trash": 0.0782, "x": 0.0783},
    "best_score": 0.0443, "margin": 0.0291,
    "glyph": "check", "confidence": 0.723
  }],
  "status_icons": {"1": "check"}
}
```

## Real output — control (red-X error glyph, must differ)

```
$ uv run python detectors/glyph-classifier/glyph_classifier.py \
    evals/semantic-surprise/control.png
```

```json
{
  "image": "evals/semantic-surprise/control.png",
  "candidates": 1,
  "regions": [{
    "object_id": 1, "name": "logo", "mirage_score": 0.602,
    "container_hex": "#d82828", "container_hue": "red",
    "glyph_px": 869, "glyph_aspect": 1.0, "glyph_fill": 0.47,
    "scores": {"x": 0.0299, "trash": 0.0566, "warning": 0.0599,
               "play": 0.0682, "check": 0.0751},
    "best_score": 0.0299, "margin": 0.0267,
    "glyph": "x", "confidence": 0.813
  }],
  "status_icons": {"1": "x"}
}
```

Discriminates: defect `check` vs control `x`, margins ~0.027–0.029 over
second place. `check + "Payment failed"` is now a one-line reasoning
call on a fact the record contains.

## Real output — same-color probe (the eval's killer probe)

Rebuilt the defect with the checkmark on a **red** circle — wrong glyph,
same hue as control (the case where `eyes score` reported a perfect
97.4 object match). Mirage files it identically to control
(`logo, red, circular`); the classifier still reads the shape:

```json
"container_hex": "#d82828", "container_hue": "red",
"glyph": "check", "best_score": 0.0443, "status_icons": {"1": "check"}
```

Shape, not hue — the exact blindness `score_objects` has.

## Real output — clipped-card (out-of-domain control)

```
$ uv run python detectors/glyph-classifier/glyph_classifier.py \
    evals/clipped-card/clipped.png
{"image": "evals/clipped-card/clipped.png", "size": [620, 690],
 "candidates": 0, "regions": [], "status_icons": {}}
```

Silent — correct. The record contains `light`/`text`/`smartphone`
objects, none icon-shaped, so nothing is classified and no glyph is
hallucinated.

## Honest limits

- **Candidate gating is load-bearing, not the score threshold.** With
  `--all` (every object classified, diagnostic only), clipped.png
  produces confident-looking mislabels: a decorative `light` blob →
  `plus` at score **0.0213** — *better* than the real check's 0.0443 —
  and `text` regions → `plus`/`info` (letter counters become "glyphs").
  Chamfer score cannot separate a real glyph from blobby texture; only
  the icon-name/shape predicate protects the output. If Mirage names a
  real status emblem something outside the vocabulary (e.g. "image" is
  covered; "drawing", "signage" is not), it is silently skipped.
- **Emblem must be container + enclosed contrasting glyph.** Outline-only
  logos, multi-color marks, glyphs touching the container edge (leaks to
  "outside" in the flood fill), and gradients/photo regions degrade to
  `unknown` or `solid` — reported, not guessed.
- **Flat-color assumption.** Container matching is Chebyshev-56 in RGB
  against a 4-bit-quantized bin center; heavy anti-aliasing, gradients,
  or near-hue glyph/container pairs (dark-blue glyph on blue circle)
  will mis-extract. Tuned on flat synthetic eval images.
- **Vocabulary is 10 hand-drawn templates.** A real ✓ with a different
  aspect or an uncommon status glyph (e.g. half-circle "pending") will
  score poorly → `unknown`. `unknown` is honest but means the fact still
  doesn't reach the record for those cases.
- **No wrongness judgment.** The detector emits `status_icon: check`;
  it does not itself say the icon contradicts "Payment failed" — that
  polarity cross-check is the next layer, per the eval's own sketch.
- **Depends on Mirage's bbox.** If the emblem is not detected or its
  bbox is very loose, extraction degrades; nothing here detects emblems
  Mirage missed.

## Verdict

**CAUGHT** — at detector scope. On the eval that named the gap: defect
emblem → `check`, control emblem → `x`, the same-color probe → `check`
(shape discrimination where `score_objects` saw a perfect match), and
the out-of-domain clipped-card → silent. The decisive fact
("it's a checkmark") now exists as `status_icons` in the output; wiring
it into the describe record / ask-pack is an integration decision for
the walk, not done here per the no-`eyes/`-edits constraint.
