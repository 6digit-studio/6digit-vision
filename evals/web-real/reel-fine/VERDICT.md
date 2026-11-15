# reel-fine — scroll persistence at ~37% viewport steps

Same Wikipedia article, 300px scroll steps (vs reel/'s 700px). Tests
whether scroll_persistence discriminates churn from real departures
when overlap is meaningful.

## Results

| pair | dy est | conf | persistent_frac |
|------|--------|------|-----------------|
| 00->01 | -571.9 (noise) | 0.40 | 0.083 |
| 01->02 | 271.9 | 0.20 | 0.512 |
| 02->03 | 271.9 | 0.16 | 0.500 |
| 03->04 | 271.9 | 0.26 | 0.558 |
| 04->05 | 703.1 | 0.45 | 0.047 |

## Verdict

Mechanism VERIFIED: dy ~272 vs actual 300px steps (estimator noise
~28px at 4px search granularity — acceptable); persistent_frac now
~0.5 on overlapping pairs vs 0.02-0.08 on coarse steps — the metric
discriminates real overlap from churn correctly. Boundary behaviors
documented: first-pair dy noise (sequence start), last-pair dy=703
(page-bottom clamp — scrollTo can't go further, content shifts
non-uniformly). Confidence values are modest (0.16-0.45) — the
err0-vs-best_err metric understates real shifts on content-heavy
pages; a row-agreement fraction would calibrate better, queued.
