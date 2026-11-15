## Sensing mode

Vision plus live measurement: eyed the reference, then used `eyes score`/`pixdiff`/`zoom` together with direct pixel sampling of `reference.png` (edges, ink boxes, peaks, ink flux) to place and colour every element.

## What is missing

- **Edge softness.** The reference is clearly a down-scaled render (card edge ramps over ~4 px, small text never reaches its nominal colour). I soften with `filter: blur(1px)`; Chromium quantises any sub-pixel radius to 0 or 1 px, so 1 px is slightly stronger than the reference — my text peaks land at ~205–240 where the reference reaches 230–252.
- **The airplane glyph** is hand-drawn SVG. Its swept-wing silhouette, the small tail planes, and the white bloom around it are approximations of a real SF-Symbol-style plane; the reference's white core is more compact/broken up (mine reads a touch crisper and thinner).
- **Type weight of the secondary rows.** `San Francisco` / `Edmonton` / times / status use the system UI face at fitted sizes (16/16/16/15.3 px, weights 600/500); the reference's glyphs are slightly lighter in the small rows, so labels look marginally bolder than the original.
- **The muted cyan of "Arrives in 20m"** (measured peak ≈ rgb 160,184,183) is matched with #aecac8, but the reference's chroma-subsampled value drifts per pixel, so the hue is only approximately right.
- **Ambient shadow field.** The reference background is not uniform (#2b2b2b at corners, ~29 at bottom centre, ~36 top centre, ~41 at left edge); I fake it with layered radial/linear gradients + a tight card shadow, which is within ~2–6/255 but not exact — the bottom-left falloff especially.

## Self-estimate

8 — geometry, bar, text placement and palette are within a pixel or two everywhere, but the reference's sub-pixel softness and the hand-drawn plane keep it from being a 9–10.
