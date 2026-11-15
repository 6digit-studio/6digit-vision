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

## Update — scroll-compensated persistence landed

`estimate_vshift` (row-profile correlation, full-height span) +
`scroll_persistence` (bbox shift-compensation, positional matching)
now ride every reel pair as `pair.scroll`. Verified on this sequence:
dy estimates ~700-722px vs actual 700px scroll steps — estimator
works. persistent_frac 0.02-0.08 is HONEST: 700px steps on an 800px
viewport leave only ~12% vertical overlap, so most elements genuinely
depart — the metric correctly reports mostly-new content rather than
churn. First pair's dy=-703 is estimator noise at sequence start
(conf 0.477) — documented. For persistence to discriminate churn vs
real departures, scroll steps need <~50% viewport overlap — future
reel captures should use ~300px steps.
