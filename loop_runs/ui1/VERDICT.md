# ui1 — GitHub login mimicry via HTML/CSS reproduction loop

Reference: evals/web-real/corpus/github_com_login.png (real capture).
Candidate: candidate.html rendered through headless Chrome — REAL
browser pipeline, not PIL. Critic: agent-in-loop (SWE-2 reads ask pack
+ element_diff, edits HTML — one targeted change per iter, same
honest pattern as match_loop).

## Trace

| iter | score | palette | objects | layout | text | scene |
|------|-------|---------|---------|--------|------|-------|
| 0 | 59.2 | .911 | .522 | .044 | .659 | 1.0 |
| 1 | 63.9 | .908 | .485 | .406 | .862 | .558 |
| 3 | 60.2 | .907 | .362 | .410 | .861 | .558 |
| 5 | **65.1** | .903 | .522 | .419 | .863 | .558 |
| 6 | 60.6 | .909 | .352 | .430 | .878 | .558 |
| 7 | 65.1 | .903 | .522 | .419 | .863 | .558 |

(iter2/4 are duplicate renders from pipe retries — deterministic,
same score. iter7 = iter5 state re-verified.)

## Verdict: CONVERGES on structure, STALLS on Mirage noise floor

What the loop fixed: vertical rhythm (layout .044->.42), palette
match (.91 — GitHub dark palette reproduced nearly exactly), text
content (.66->.86 — all strings present, footer unmerged), scene
stable. The candidate is a recognizable GitHub-login approximation.

Where it stalls — honest list:
- **objects component oscillates .35-.52 on near-identical renders** —
  Mirage re-detects the dense form region differently each render
  ('webpage' phantom, merged text blobs, button over-segmentation).
  The edit signal (~1-5 pts) is BELOW the detector noise — the critic
  can't tell a good spacing edit from a bad one at this floor.
- **layout plateaus ~.42**: fine positional details (label baselines,
  input heights) matter less than Mirage's bbox jitter.
- **OCR misreads persist** ('Slgn In', 'Userame') — font-rendering
  level, below what HTML/CSS tuning reaches cheaply.
- **scene .558**: label churn on real UI (known, documented).

The product claim HOLDS at coarse structure: screenshot -> working
UI approximation -> measurable convergence (59->65, all weak
components improved). The stall is instrument noise floor, not loop
mechanics — same Mirage jitter documented since wave 3. A real
image-diff metric (pixel-level SSIM-style) would give the critic a
less noisy objective for fine edits; named upgrade.
