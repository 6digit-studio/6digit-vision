# A/B/C experiment — does `eyes` add anything?

Same model (deepseek-account/deepseek-flash), same four references, same
renderer, same iteration budget (3-5 looks). Only the sensing mode differs:

- **A — vision only.** No facts, no tools.
- **B — vision + fact sheet.** `facts.json` (precomputed `eyes interrogate`)
  in context. No live measurement.
- **C — vision + measurement loop.** `eyes score` / `pixdiff` / `zoom` during
  iteration, no fact sheet.

Judged by `eyes score` (composite 0-100) and `eyes pixdiff` SSIM against the
reference, plus a visual read of the final pairs. Each cell is an isolated
directory so arms cannot contaminate each other.
