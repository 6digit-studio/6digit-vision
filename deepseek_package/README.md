# DeepSeek A/B package — eyes fact sheets vs native vision

You are being tested on screenshot-to-HTML reproduction. You have
native image vision. This package tests whether a measured fact sheet
from the `eyes` instrument improves your reproduction versus your own
perception alone.

## The two arms (run BOTH, independently)

- **Arm A — vision only:** reproduce each reference from the image
  alone. Do not read anything in `facts/`.
- **Arm B — vision + eyes:** reproduce each reference WITH the
  corresponding `facts/<name>.json` fact sheet as additional input.

Same model, same references, same task — the only difference is the
fact sheet. Produce both arms blind to each other's outputs.

## Task (per reference, per arm)

1. Study the reference (and the fact sheet in Arm B).
2. Write `candidate.html` reproducing it as faithfully as you can —
   HTML/CSS only, render at the reference's exact pixel dimensions.
3. Render it (headless Chrome: `--headless --screenshot --window-size=W,H`)
   and LOOK at your render. Iterate 3-5 times fixing what you see.
4. Deliver per arm per reference: `candidate.html`, `candidate.png`,
   and `VERDICT.md` stating: sensing mode, what you believe is missing,
   and your own 1-10 fidelity estimate.

## What the fact sheet contains

`eyes interrogate` output — deterministic measurements, not
interpretation: dominant palette hex + coverage, text inventory with
strings, layout-family guess, per-row text alignment, detected
accent/selection blobs with position+color+shape, and conditional
probes (weekday headers, muted cells, grid continuation, header lines
above titles). Treat it as measured evidence to check against your
own perception — where it disagrees with what you see, note it.

## References

Four captures in `images/` — a quantum-computing landing page, a
text-free visual, a health metric widget ("82 mmhg"), and a
flight-status card (SFO/YEG). Deliberately different families.
