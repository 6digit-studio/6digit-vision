## Sensing mode

Direct visual inspection of `reference.png` (zoom crops + pixel probes) cross-checked against the measured `facts.json` sheet; layout, palette and all geometry derived from the image itself.

## What is missing

- **Small type weight/softness.** The reference's "mmhg" and "5 min" are simultaneously soft (blurred edges, filled-in gaps between stems) and bright (peaks 157 and 221), which one uniformly blurred render cannot hit exactly; my `mmhg` ends ~2 px wider and ~2 px taller than the reference's compact lettering, and "82" sits 1 px low while being a hair smaller/dimmer than the reference's bolder digit pair.
- **Bead rim vs. halo.** Each of the 21 waveform beads in the reference has a crisp core rim plus a wide pink halo (still ~25/255 at r≈8 px); my beads are drawn with a single 1 px Gaussian over a radial gradient, so they read slightly larger and fuzzier, and the faint notch between the two beads of the near-baseline columns (e.g. columns at x≈59, 72, 272, 285) is weaker than the reference's.
- **Background unevenness.** The surround is not a flat #2b2b2b disc: it is darkest in the top and bottom centre strips (≈30 at the frame centre vs ≈43 at the corners) with 2–4 grey levels of photo-like mottling that no smooth gradient reproduces; my three layered gradient bands leave ~2–4 levels of residual error above and below the card.
- **Card edge falloff.** The reference's card boundary is softer (≈1.4 px transition) than its own text (≈0.7 px); I split the blur per element (card 1.3 px, SVG 1.0 px, text 0.55 px), but the corner falloff still differs by about a pixel, and the card measures 338×154.3 px at (25.8, 38.2) where the reference implies 337.9×154.4 at (25.4, 37.4).
- **Fact-sheet conflicts.** `facts.json` reports "no glow detected", yet every bead clearly has a pink glow measured out to r≈10 px, and its "selection blobs" are simply the dot columns; its "1 row × 7 cols" structure also under-counts the 21 waveform columns I measured (13.2 px pitch). I trusted my eyes and drew the halo.

## Self-estimate

7 — at 1:1 the card, palette, the 21-column dot waveform and the three labels register as the same image (per-pixel MAE ≈4.3/255, with the waveform region ≈6.4 and background ≈1.5), but the small type metrics, bead rim softness and the uneven background still read slightly different on close inspection.
