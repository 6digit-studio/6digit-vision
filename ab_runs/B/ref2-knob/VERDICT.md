## Sensing mode

Vision-first: I inspected `reference.png` with repeated 3–4× zoomed crops and numeric pixel probes (edge scans, lattice sampling, colour profiles), using `facts.json` only as a cross-check on palette and blob claims.

## What is missing

1. **Dot matrix is too heavy.** My LED dots are ~6.1 px wide on a 7.8 × 6.8 px lattice with three stacked blur layers, so the horizontal/vertical gaps wash out and the speaker reads as a solid slab; in the reference each dot is a crisper, slightly smaller square (~5–5.5 px) with a visible dark seam between dots, and individual dots vary in brightness (the outermost wave dots are dimmer and greener).
2. **Neon tube lacks punch and length.** The reference has a tight, saturated cyan core (`#78e7e9`) that stays bright from the bottom-right corner through ~x=250 and ~y=170, plus a distinct second "floor reflection" band ~12 px outside it. Mine is a softer, white-ish line whose bright run is shorter and whose floor band is not separated from the main glow.
3. **Bevel/specular shading is simplified.** The real cap has a continuous 20 px-wide specular falloff on its left bevel (peak `#e2`, decaying to `#33` by x≈140), a bright rim that reappears along the bottom-left corner, and a cyan rim-light on the bottom-right corner; mine renders the left specular as a somewhat "drawn" thin white line with a weaker falloff and misses most of the bottom-left corner rim.
4. **Plate lighting is not fully reproduced.** The plate is lit from the left but also has a per-face bevel structure: brightest along the mid-left (`#47`), darker at the top-centre (`#2a`), and noticeably darker where the bottom-left bevel turns away (`#33`); my single horizontal gradient plus a bottom fade leaves the lower-left ~5–10 units too bright in places and the upper-left too bright by up to 12.
5. **Fact-sheet conflicts (perception overrides instrument).** The `glow` answer locates the "bright region" at cell (11,5) ≈ (315,135) — that is white icon dot-matrix, not a glow; the actual glow is the cyan neon at the cap's lower-right (centroid ≈ (338,292)). The `selection_state` blob (centroid (279,236), mean `#319091`, "ring-ish") is not a selection — it is part of that same neon light band. The `background` answer's dominant `#141c1c` disagrees with my measurement: the field is a flat `#17181f`, tinted up to ≈`#192d2f` by the neon bloom near the bottom-right corner.

## Self-estimate

6 — the composition, silhouettes, icon glyph, colour relationships and the dark/teal lighting scheme all land in the right places (full-image RMSE 18.7, PSNR 22.7 dB), but the neon's intensity/definition, the coarser dot grid and the simplified bevel shading keep it visibly a reconstruction rather than a match.
