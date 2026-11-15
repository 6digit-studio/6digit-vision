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
- **Read `facts.json` before you start.** It is the measured fact sheet
  produced by an instrument called `eyes` for this exact image. Use it as
  additional measured evidence alongside your own perception: palette
  hexes, text strings, layout alignment, accent/selection blob positions.
- Where the fact sheet disagrees with what you see, trust your eyes and
  record the conflict under `What is missing`.
- Do not run `eyes` yourself and do not read any other analysis file.
  This arm is **vision + precomputed facts**, nothing more.

## Deliverables

- `candidate.html`
- `candidate.png`
- `VERDICT.md`
