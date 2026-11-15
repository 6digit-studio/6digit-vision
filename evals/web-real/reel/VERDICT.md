# reel — real-capture frame sequence (scroll)

First `eyes reel` run on uncontrolled real content: 6 frames of
Wikipedia WWII article at 700px scroll steps, Playwright capture,
1200x800 viewport. 2026-11-15.

## Verdicts

| check | result | honest read |
|-------|--------|-------------|
| static_pairs | [] — correct | smooth scroll = motion everywhere, no false frozen flags |
| strobe | clean | no alternation on coherent scroll |
| lifecycle departures | none | honest — scroll reveals new content continuously |
| pixel diffs | ~35% changed/step | real motion magnitude on text-heavy page |
| record stability | labels churn (score 0.0, only_a/only_b disjoint) | Mirage detection noise on scrolling content — documented floor |

## Finding

Reel's temporal detectors behave correctly on real captures: they
measure motion/coherence facts without false positives. The weak
channel is record stability — Mirage re-detects objects differently
each scroll frame (new content entering viewport legitimately changes
the object set, so label churn here is PARTLY real, partly noise —
the instrument can't fully separate "new content scrolled in" from
"detector instability" without scene-tree anchoring). eyes diff /
scene_tree region matching is the queued upgrade for exactly this.
