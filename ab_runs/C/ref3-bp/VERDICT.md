## Sensing mode

Vision-plus-measurement: repeated `read_image` inspection of the reference and of each render, combined with live pixel probes (blob centroids, radial/linear intensity profiles, ink statistics) and `eyes score` / `pixdiff` for regression checks.

## What is missing

- **Dot bloom falloff.** Each of the 42 pink dots gets its halo from a radial gradient fitted to one isolated dot; in the reference the halos of neighbouring dots (13.3px apart) bleed into each other a little differently, so the mid-gap greys are still off by roughly 20-40 levels. This is the hottest residual (dots band RMSE ~13.8).
- **Glyph rendering of the three text runs.** The reference is a downscaled capture, so its glyph edges are soft, its stems slightly fuller and its letter fitting a touch wider than anything Chrome draws at 1x. My SVG blur (sigma 0.8) plus per-element colour matching reproduces peak brightness and total ink well, but not the exact letter shapes (card text RMSE ~11.4).
- **Card edge softness.** The reference card boundary ramps from background to black over about 4px; mine transitions in about 1.5px. A global CSS blur large enough to fix this is quantised away below 1px and too strong at 1px, so the edge stays crisper than the original.
- **Background vignette shape.** The original backdrop is an asymmetric wash (bright at the left/right edges, dark in a band across the top-centre and bottom-centre); two radial gradients approximate it to within 2-3 grey levels but not exactly.
- **Per-dot micro-variation.** I use one uniform dot diameter and colour; in the reference the dots vary slightly in size and peak brightness (36-88 px of saturated core), and the short merged bars are inferred by splitting a blob rather than measured.

## Self-estimate

7 — layout, card geometry, all 21 bar positions and both endpoints, palette and the three text runs line up to within about a pixel, giving SSIM 0.918 / MAE 4.0/255, but the residual dot-glow and glyph-softness differences keep it from feeling like a byte-level match.
