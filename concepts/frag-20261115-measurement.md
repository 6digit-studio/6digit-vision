---
type: concept
id: frag-20261115-measurement
provenance: ab_runs/REPORT.md — A/B/C reproduction run, 2026-11-15
ts: 2026-11-15T20:00:00+01:00
tags: [perception, measurement, reproduction, regime-change]
---

# Give a seeing agent a ruler, not a description

For an agent that can already see, structured facts about an image are not
perception. They are a lossy compression of it, and their errors arrive
labelled `measured`. In the controlled reproduction run, adding the
`interrogate` fact sheet to a vision-capable agent changed nothing (clean pair:
SSIM 0.785 vs 0.782 on the collage, 0.420 vs 0.375 on the BP widget) — and on
the collage the sheet's OCR error `M0WQ → MOwQ` propagated into the candidate
while the vision-only cell got it right. Its consumers spent budget auditing
it: a 0/4 hit rate on the glow probe, alignment rows that fused four columns
into one, 10+ recorded conflicts.

What moved fidelity was a closed measurement loop: measure the reference,
render, measure the candidate with the same instruments, localize the delta,
edit one variable, gate on pixel truth. Vision-only averaged 0.684 SSIM; with a
loop, 0.889. The loop's *instrument* mattered less than its existence: hand-built
pixel rigs reached 0.890, `eyes` reached 0.888. The agents' own confidence
estimates correlated with measured fidelity at only r ≈ 0.42, so the loop's
first gift is calibration, not pixels.

The load-bearing consequence: the product surface is `parse`/`pixdiff` plus
measurement primitives, not `interrogate`'s answers. Facts are for the
text-only user the project was founded for; a seeing agent needs calipers.

**What would correct this belief:** a fact sheet that materially raises a
seeing agent's fidelity *without* a measurement loop, or a measurement loop
that fails to beat vision-only on a fair pair. Either would show the ruler is
not the active ingredient.
