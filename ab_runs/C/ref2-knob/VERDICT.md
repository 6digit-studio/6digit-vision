## Sensing mode

Vision plus live pixel measurement: I read `reference.png` with the image tool, then drove the geometry and colour decisions from numeric probes (scanline/column profiles, flood-filled silhouettes, gradient and cyan-channel maps, zoomed crops) and checked each render against `reference.png` with pixel diffs rather than eyeballing alone.

## What is missing

- **The neon light pipe.** The reference's glow is a thick, soft, saturated cyan tube hugging the face's lower-right edge, with a bright white-cyan core, a dark dip, and a second caustic strand ~12 px further out, plus a broad bloom that tints the bezel and the background. Mine reads as two thin, hard lines with the right geometry but too little volume, too little bloom, and it sits ~2–3 px lower than the real one.
- **Bezel/face metal shading.** The reference's plate has an asymmetric sheen (rim highlight down the left wall reaching ~#434345, dark right wall ~#1f2022) and the face has a fine, slightly mottled brushed-metal gradient with a strong 1–2 px specular only on the left bevel. My gradients are smooth and slightly too flat/light, and the specular is broken into segments near the top-left corner.
- **Well depth and dark channel.** In the reference the channel between the face and the plate is a narrow (~4 px top, ~10 px left) black groove that tightens at the top; mine is wider at the bottom-left and reads as a deep black moat, so the face appears to float.
- **Dot-matrix icon fidelity.** Dot centres were lifted straight from the reference, but my dots are slightly too soft/round and the inter-dot gaps are washed out by the bloom layer, so the grid reads denser and less crisp than the reference's 6 px squares on a ~7.8 × 7.2 px pitch.
- **Ambient/contact shadow balance.** The reference has a very dark, nearly hard-edged shadow band under the plate (values ~0–3) with an untouched background above the knob; mine is slightly too light under the plate and slightly too dark at the frame's right/bottom edges.

## Self-estimate

6 — the silhouette, layout, palette, glow position and dot-matrix glyph are all in the right place, but the neon tube's light behaviour and the metal shading are clearly flatter than the reference, and an honest mean absolute pixel error of ~7.7/255 across the frame still lands it as a recognisable likeness rather than a convincing match.
