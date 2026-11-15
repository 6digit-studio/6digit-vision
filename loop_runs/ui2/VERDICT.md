# ui2 — calendar month-view mimicry (grid/dense-cells family)

Reference: Screenshot 2026-11-15 at 03.00.39.png (802x778, dark
calendar month view). Sibling captures .47/.53 are different views of
the same app (week strip "THU 31 DEC" + "New Year's Eve" — triangulated
via describe since image viewing unavailable this session).

## Trace

| iter | score | pixdiff | palette | objects | layout | text | scene |
|------|-------|---------|---------|---------|--------|------|-------|
| 0 | 21.9 | — | .196 | .042 | .000 | .779 | .402 |
| 1 | 24.3 | .494 | .197 | .170 | .000 | .596 | .536 |
| 2 | 28.3 | .490 | .278 | .117 | .000 | .922 | .402 |

## Verdict: semantic matcher hits its floor on dense grids — pixdiff carries truth

The grid/dense-cells family is the stress test it was chosen for:
- **objects+layout floor ~0.1**: Mirage cannot parse 7x5 tiny day
  cells into meaningful objects — detections collapse to noise
  ('app icon' fragments). Semantic score's two heaviest components
  (objects .30 + layout .20 weight) are blind here.
- **text+palette respond honestly**: cell backgrounds lifted palette
  .20->.28, text .78->.92 as real structure landed.
- **pixdiff is the honest channel**: 0.49 pixel-truth where semantic
  score can't see — exactly the division of labor the instrument
  docs now claim: semantic=WHAT, pixdiff=WHERE.
- **Ceiling without image vision**: the top ~40% of the reference
  (app chrome/sidebar region) couldn't be modeled blind — OCR gives
  positions but not appearance; cell-level fidelity needs either
  image input or iterative pixdiff-region-guided edits.

Convergence verdict: PARTIAL — coarse grid structure lands and scores
respond, but the family's semantic floor caps total ~30 without
pixdiff-guided fine edits. Named upgrade: pixdiff-region -> targeted
CSS edit loop (regions already localize diffs to bboxes).
