# The measurement discipline

*What four agents did when they stopped eyeballing and started measuring —
distilled from the A/B/C reproduction run in [`ab_runs/`](../ab_runs/REPORT.md).*

## Why this exists

In a controlled run on four screenshot→HTML reproductions, the same model
averaged **0.684 SSIM** when it worked by eye and **0.889 SSIM** when it closed a
measurement loop — and the loop's source barely mattered (`eyes` tools or a
hand-written PIL script). The agents' own 1–10 confidence estimates correlated
with measured fidelity at only **r ≈ 0.42**.

The lesson is not "use `eyes`". The lesson is that **visual reproduction is a
measurement problem before it is a drawing problem.** This document is the
protocol the successful cells converged on, written down so it can be repeated
without re-deriving it each time.

## The loop

```
        ┌─────────────────────────────────────────────────────────┐
        │                                                         │
  measure reference ──► build/edit one variable ──► render ──► measure candidate
        │                                                         │
        └──────────── localize delta ◄── rank regions ◄───────────┘
                              │
                    gate: did SSIM improve?
                    yes → keep, next region
                    no  → revert, try a different variable
```

Seven steps. The two that agents skip, and shouldn't:

1. **Freeze the frame.** Exact `W×H`, exact viewport, fixed font stack, fixed
   device scale factor. A renderer that lies about its viewport invalidates every
   measurement downstream. (On macOS headless Chrome, `--window-size=W,H` gives a
   `max(500,W) × (H−87)` layout viewport; use CDP `setDeviceMetricsOverride` —
   see [`tools/cdp_shot.js`](../tools/cdp_shot.js).)
2. **Measure the reference into a spec** before writing HTML. Geometry, type
   metrics, colour stops, softness. Do not "look and start typing."
3. **Build the whole frame once**, roughly, so the diff has something to say.
4. **Render and measure the candidate with the *same* instruments** used on the
   reference. Symmetry is what makes the delta meaningful.
5. **Localize and rank.** Global SSIM tells you *whether*; region decomposition
   tells you *where*; block ranking tells you *what next*. Never edit the whole
   page on a global number.
6. **Change one variable per cycle.** Font size OR colour OR position. The
   regression gate cannot attribute a mixed edit.
7. **Freeze the best-measured state**, not the last state. The best state is
   chosen by `ssim_mean` / region RMSE, never by the semantic composite.

## The instrument set

Each is cheap, deterministic, and takes minutes to write. All coordinates in
source pixels.

### Frame and geometry

- **Background-difference mask.** `mask = max|rgb − median(border)| > τ`.
  Run-length the mask on rows and columns; the long runs are card/panel edges.
  This found exact card boxes at 53/414/777/1139 × 60..755 on a four-up collage.
- **Sub-pixel edge crossing.** Walk a scanline; find where luminance crosses the
  midpoint between background and foreground; linearly interpolate. Gives ±0.2px
  edges, and the **10–90% ramp width** is the reference's softness signature —
  measure it separately for the card, the text, and the shadow.
- **Corner radius.** First non-background x per row near the corner, then
  least-squares circle fit over those points. Do not guess a border-radius.
- **Silhouette trace.** Flood-fill the object region, ray-march from a seed to
  the outermost filled pixel at N angles, subsample, and convert to a closed
  Catmull-Rom→Bézier path. This is what turned a rounded-rect keycap into the
  real organic squircle in B/ref2 and C/ref2.
- **Dot lattice.** Local-maxima + non-max suppression on a fitted lattice,
  then occupancy sampling. Recovers LED/speaker glyphs and the 21-column
  waveform; a lattice fit is one parameterization instead of 84 guesses.

### Type

- **Ink bands.** Row projection of dark/light pixels inside a region gives every
  line's top and bottom; column projection gives x-extents. Line-height is the
  delta between consecutive ink tops, not a guess.
- **Threshold ladder.** Re-bbox at several thresholds (40/70/120/200). The core
  shrinks while the halo grows; comparing the two separates *weight* from
  *softness*.
- **Ink mass (blur-invariant).** `Σ max(0, luma − background)` over a text
  window. Blur redistributes ink but conserves it, so mass distinguishes "too
  bold" from "too soft" where bbox comparison cannot. The BP/widget cells used
  this to match `82`/`mmhg`/`5 min` weights.
- **Font fitting.** FreeType `getbbox` / `getlength` and Chrome
  `canvas.measureText().actualBoundingBox*` predict ink width/height for
  family × weight × size; fit the reference's measured ink box. This is how
  13px Helvetica Neue and 16.5px Avenir Next were identified without guessing.
- **Per-glyph segmentation.** At a high threshold, digits separate into columns;
  glyph widths and gaps confirm the font and size.

### Colour

- **Scanline profiles.** Sample RGB along a text-free column/row, every ~5% of
  the range. Emit the samples directly as CSS gradient stops. The collage's
  21-stop dawn gradient and the flight card's background field came from this.
- **Percentile text colour.** Sort the patch's pixels by luminance; take p1/p5
  for the glyph core and p30–p50 for the antialias skirt. Do not average, or the
  background wins.
- **Saturation mask.** `max(r,g,b) − min(r,g,b) > τ` isolates coloured
  elements (orbs, neon, beads) from neutral chrome.
- **Beware the bin centre.** `eyes palette` reports 5-bit bin centres (±4 per
  channel), not sampled pixels: `#17181f` → `#141c1c`. Use it for "roughly this
  colour", then sample the actual pixel.

### Softness and texture

- **Blur signature.** Blur your own candidate with σ = 0.3…1.0 and re-measure
  SSIM against the reference. The σ that maximises SSIM is the reference's
  effective softness. Chromium quantizes CSS/SVG blur: below ~0.75px renders as
  0, and 0.8–1.2px renders as one kernel — so the achievable softness is coarse
  and should be chosen by measurement, not by feel.
- **Radial falloff.** For glows/beads, sample value vs radius and fit the
  profile (flat core → steep shoulder → long halo); emit radial-gradient stops
  from the fit.
- **ASCII luminance map.** Quantize a region to 10 levels and print it. It reads
  structure in near-black UI that a screenshot preview cannot show.

### Diff and ranking

- **Align before scoring.** Search ±2px `(dx,dy)` for the best SSIM before
  blaming shape. A 1px offset otherwise reads as a structural error.
- **Region decomposition.** Report RMSE/MAE per region (`bg_top`, `bg_bot`,
  `card_text`, `dots`, `icon`, `edge`) — not one global number. Pick the next
  edit from the highest-region that is above the noise floor.
- **Block ranking.** 20×20 block-mean absolute diff, sorted. It finds the
  residual you cannot see at 1:1.
- **The two gates.** `ssim_mean` must not decrease and `mismatch_frac` must not
  increase (allow a 0.002 / 0.2% tolerance for renderer noise). Global gate
  first, region gate second.

## Anti-patterns (all observed)

| anti-pattern | what happened | do instead |
|---|---|---|
| optimizing the semantic composite | component fell 86.0 → 78.5 while SSIM rose 0.801 → 0.864 (plane → "arrow") | optimize SSIM + region RMSE; composite is a coarse gate |
| eyeballing geometry | ref3 vision-only 0.544 vs measured 0.928 | one projection line beats ten glances |
| bbox comparison without blur | "reference is bolder" when it was softer | compare ink mass at matched threshold |
| scoring without alignment | 1px offset blamed on shape | shift-search first |
| multiple variables per edit | cannot attribute the delta | one variable, one cycle |
| trusting palette hexes verbatim | ±4/channel bin centres | sample the pixel |
| reading normalized bboxes as px | 3.4× position error on a 400px image | check units; `describe`/`parse` are [0,1000] |
| rendering with naive `--window-size` | layout viewport ≠ capture size | CDP device metrics |
| keeping the last render | a later edit regressed | freeze the best measured state |

## A cycle, concretely

```text
1. ref_spec = measure(reference.png)        # geometry, ink boxes, stops, softness
2. html    = build(ref_spec)
3. png     = render(html, W, H)             # exact viewport
4. cand    = measure(png)                   # same instruments
5. delta   = align_and_diff(ref_spec, cand) # ssim, mismatch, regions
6. target  = argmax(region_rmse above floor)
7. edit    = one CSS property for that region
8. gate    = ssim_new ≥ ssim_old - ε and mismatch_new ≤ mismatch_old + ε
   keep if gate else revert
9. trace   = {"iter": n, "ssim": …, "region": target, "edit": …, "kept": bool}
```

A `trace.jsonl` per run with exactly those fields makes the loop auditable and
comparable; mixing composite and SSIM in one `score` field (observed in C/ref3)
makes the trajectory unreadable.

## What this implies for `eyes`

The agents did not lack descriptions; they lacked calipers. They re-wrote the
same primitives in four separate cells. The instrument should ship them:

- `eyes measure <img> --json` → per element `bbox_px`, `ink_bbox`,
  `edge_crossings`, `radius`, `gradient_stops`, `ink_mass`, `font_metrics`,
  `blur_sigma`, `dot_lattice`.
- `eyes parse` promoted as the rebuild entry point (element boxes already exist;
  nobody used it because it wasn't named in the task).
- `eyes semantic` (old `score`) and `eyes pixel` (pixdiff) as separate verbs, so
  the composite cannot be mistaken for fidelity.
- The gates above exposed as a tiny harness: `eyes loop <ref> <cand> --json`
  returning pass/fail plus the ranked regions.

See [`TOOL_USAGE.md`](../ab_runs/TOOL_USAGE.md) for what the agents actually
invoked, and [`REPORT.md`](../ab_runs/REPORT.md) for the evidence behind the
numbers in this document.
