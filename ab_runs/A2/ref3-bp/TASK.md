# Reproduction task (clean isolation pair)

Reproduce `reference.png` as faithfully as possible with HTML and CSS only, at
exactly 394x210 pixels.

## Method

1. Study `reference.png` with the read_image tool. Look at it as a whole.
2. Write `candidate.html` — HTML+CSS only, no external assets, no network.
   The page must render at exactly 394x210 with no scrollbars.
3. Render: `./render.sh candidate.html candidate.png`.
4. Look at `candidate.png` with read_image, compare with `reference.png`, fix the
   largest visible discrepancies. 3-5 cycles.
5. Write `VERDICT.md` with `## Sensing mode`, `## What is missing`, `## Self-estimate`
   (single integer 1-10).

## Hard rule for this pair

**Perception only.** You may look at the two full images with read_image and edit
HTML/CSS. You may NOT crop, zoom, magnify, sample pixels, measure coordinates,
compute diffs, or write/run any script or analysis code. No Python, no sips, no
ImageMagick, no `eyes`, no grid overlays. If you need a size or color, estimate it
by eye. This rule is identical in both cells of the pair — the only difference
between them is `facts.json`.

## Deliverables

`candidate.html`, `candidate.png`, `VERDICT.md`.

## Sensing mode
Vision only. Do not read any fact sheet.
