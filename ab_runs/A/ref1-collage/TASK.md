# Reproduction task

You are given `reference.png`, a screenshot. Reproduce it as faithfully as
possible with HTML and CSS only, at exactly 1520x794 pixels.

## Method

1. Study `reference.png` carefully with the read_image tool. Note layout,
   type, color, shadows, and every visible object.
2. Write `candidate.html`. Constraints:
   - HTML + CSS only. No external assets, no web fonts, no network, no
     images embedded from the reference. Anything visual must be drawn
     with CSS/SVG.
   - The page must render at exactly 1520x794; set html/body size and
     `overflow:hidden` so no scrollbars appear.
3. Render with `./render.sh candidate.html candidate.png` (headless Chrome,
   exact window size).
4. **Look at `candidate.png` with read_image** and compare it with
   `reference.png`. Identify the largest visible discrepancies and fix them.
5. Repeat step 3-4. Do at least 3 and at most 5 render/compare cycles.
6. Write `VERDICT.md` with exactly these sections:
   - `## Sensing mode` — one line.
   - `## What is missing` — the 3-5 biggest remaining gaps, concretely.
   - `## Self-estimate` — a single integer 1-10 for fidelity, plus one
     sentence of justification.

## Rules

- Work only inside this directory. Do not read files elsewhere on the
  machine. Do not use the network.
- Do not run the `eyes` command, and do not read any fact sheet,
  measurement dump, or analysis of this image. This arm is **vision only**:
  your own perception is the only input.

## Deliverables

- `candidate.html`
- `candidate.png`
- `VERDICT.md`
