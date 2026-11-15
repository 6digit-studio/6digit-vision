## Sensing mode

Vision-plus-measurement loop: read_image on the reference and on every render, `eyes score` / `eyes pixdiff` for regression, plus direct pixel/row/column sampling with a bundled Pillow script to derive exact card bounds, text baselines, colours and gradient stops.

## What is missing

1. **The three 3D "quantum sphere" renders.** The 145px marble in card 1, the 78px pearl in card 3 and the 326px globe in card 4 are rebuilt from stacked radial/conic CSS gradients plus a small feTurbulence displacement filter. They carry the right broad colour zones (near-black maroon left, hot pink/white mass centre-right, blue-grey lobe at the bottom, iridescent rim) but none of the reference's flame-like marbling, chromatic-aberration fringes or specular streak detail, so at 100% they read as smooth blobs rather than photographic renders.
2. **Pill overlay in card 4.** Mine is a uniform translucent rose wash with a faint light border; the reference pill is more opaque and milky in the centre, brighter along the top rim and softly shadowed along the bottom, and the white KODOR inside it sits at slightly higher contrast.
3. **Contact shadows of the two small balls.** They are still separable soft ellipses with a visible edge; in the reference the shadow is darkest immediately under the ball (RGB ~145 under card 1's ball, ~95 under card 3's) and dissolves over roughly 55-80px with a blue-grey tint, so mine look slightly detached and too light right at the contact point.
4. **KODOR wordmark.** The reference lettering is a custom, slightly narrower geometric face with wider inter-letter gaps; my condensed Helvetica Neue Bold (textLength squeeze) is a little heavier and tighter, and the chevron mark's second stroke is marginally too wide.
5. **Overall softness.** The reference screenshot was clearly downscaled (text and edges carry a 1-2px halo); my render is crisp, so text blocks and card edges differ in local contrast and antialiasing even where position, size and colour match to within 1px / 1-2 RGB levels.

## Self-estimate

7

Layout, card geometry, type size/line-height/colour, the 21-stop card-2 media gradient, the card-4 dawn gradient and the text content all match measurements to ~1px / ~1 RGB level, but the three painted sphere renders (a large share of the card area) are only impressionistic approximations, so fidelity is high on structure and moderate on the photographic content.
