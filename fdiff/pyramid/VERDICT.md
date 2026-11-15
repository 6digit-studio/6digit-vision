# fdiff/pyramid — VERDICT

Gaussian-pyramid multi-scale diff + verified global alignment.
6 levels (1200x800 -> 37x25), per-level max-channel |diff| fused with
coarse-heavy weights `[0.05, 0.09, 0.15, 0.22, 0.24, 0.25]` (level 0 =
finest). Region mask = hysteresis union (hi 0.10 / lo 0.06) of
per-level thresholds, 5x5 closing, connected components.

Alignment: phase correlation at half-res proposes a subpixel shift;
full-res mean-abs search over base±2 snaps/verifies it; applied only
if cost improves >0.5% over zero-shift (`(0,0)` always a candidate).

## Shared bar (`uv run python3 tools/fdiff_bar.py fdiff/pyramid/fdiff.py`)

| criterion | score | regions | verdict |
|---|---|---|---|
| identical -> ~1.0 | 1.0 | 0 | CAUGHT |
| planted 20px block shift | 0.9865 | 4 | CAUGHT |
| 1px global translation | 1.0 | 0 | CAUGHT |
| same-img sanity (control vs itself) | 1.0 | 0 | CAUGHT |
| ui1 login pair | 0.8277 | 7 | CAUGHT |

Block-shift detail: all 4 region bboxes fall inside the planted window
(y 300-420, x 360-780); detected clusters total ~9.1k px of edge
diffs — a 20px-shifted block only differs where content actually
moves, so coverage is the changed-pixel set, not the op bbox.

1px-translate detail: alignment detected `(0,-1)` (B rolled +1px in
x), residual fused map is exactly 0 -> score 1.0, zero regions.
pixdiff scores 0.9726 on the same pair with mismatch_frac 0.0072 —
this is the blindness the challenge describes, fixed.

ui1 detail: phase correlation proposed ~42px vertical (conf 170.4);
SSD search settled on `(40, 0)` with mean-abs cost 0.01511 -> 0.01351
(~11% improvement — a real global offset between the two renders,
not a forced fit). With alignment disabled the pair still scores
0.8356 / 8 regions, so the signal is not an alignment artifact; the
40px correction just stops edge smear from inflating the diff.

## Extra measurements (self-run, same harness path)

| case | score | regions | note |
|---|---|---|---|
| gaussian noise s=4/255 on control.png | 1.0 | 0 | changed_frac = 0 |
| gaussian noise s=8/255 | 1.0 | 0 | heavier still clean |
| s=4 noise + JPEG q80 recompress | 1.0 | 0 | block artifacts absorbed by coarse weighting + soft-energy knee |
| 400x200 flat color-field repaint | 0.8619 | 1 | bbox [699,100,1101,304] vs planted x700-1100,y100-300 — near-exact |
| 120x40 solid-color fine edit | 0.9593 | 1 | localized; bbox [480,591,653,697] approximate (planted x500-620,y600-640) |
| global -3% brightness | 0.9343 | 0 | diffuse change: score moves, correctly no regions |
| web-breakpoint control vs defect | 0.7222 | 7 | real layout defect -> strong localized signal |
| runtime, 1200x800 pair | — | — | ~0.25 s |

## Honest weaknesses

- Localization is approximate, not semantic: bboxes bound
  changed-pixel clusters. The 120x40 fine edit produced a 15.7k-px
  region vs 4.8k planted — hysteresis growth + closing inflate small
  edits near existing edges. Right neighborhood, wrong exact extent.
- Only INTEGER global translation is corrected, and only when a
  dominant one exists (phase proposal must land within ±2px of truth
  after half-res rounding). Subpixel shifts, rotations, and local
  (per-element) motion are not aligned away — a locally moved element
  still diffs at both old and new positions, which is arguably the
  correct diff-tool behavior but means "shifted block" localizes to
  two clusters, not one.
- Score knees (SOFT_THR=0.02, FRAC_THR=0.05) were calibrated on
  measured fused-map distributions: noise pairs sit at F p99 <= 0.011,
  real edits at F p90 >= 0.026. Margin is ~2x on both sides — a
  different corpus with mid-level texture noise could land in the gap.
- weights favor coarse levels per the brief; very fine-only edits
  (single-glyph text changes) contribute mostly through the 0.05
  finest weight and may score high-0.9x — detected, but weakly.
