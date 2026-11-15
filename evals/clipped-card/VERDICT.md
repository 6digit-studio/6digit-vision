# VERDICT: clipped-card — MISS (at shipped defaults)

## Defect planted

`clipped.png` is `Screenshot 2026-11-15 at 03.00.53.png` (Lunar New Year
calendar card) cropped to 620×690 — slicing through the right and bottom
edges of the phone mockup. Classic viewport-clipped capture: the card
overflows the frame on two sides. Control: the uncropped original.

## What eyes reported (defaults: tol=64, margin=2%)

```
edge contact (bg #1c141c, strip 5px):
  top 1.9%  right 2.3%  bottom 0.0%  left 0.0%
objects at edge: (none)
bbox overlaps:   (none)
```

Nothing flagged. The clip is invisible to the shipped detectors.

## Sub-signals present in the raw record (unsurfaced)

- `smartphone` detection **score collapsed 0.899 → 0.309** vs. control —
  Mirage is visibly less sure when the object is cut, but no detector
  reads confidence.
- `light` objects reached bbox x=968/1000 — string lights running off
  the clipped edge — but 968 is outside the 2% edge margin (needs ≥980).
- Mirage's smartphone bbox ended at 972/953 — detection slack means a
  physically-clipped object does not register as edge-touching.

## Tolerance sweep — why lowering tol is not the fix

| tol | top | right | bottom | left |
|-----|-----|-------|--------|------|
| 64  | 1.9% | 2.3% | 0.0% | 0.0% |
| 32  | 80.6%* | 14.6% | 0.2% | 48.4% |
| 16  | 96.1%* | 25.2% | 11.0% | 95.5%* |
| 8   | 100%* | 31.8% | 40.8% | 100%* |

(* = touching). Lowering tolerance does not isolate the defect — it
floods every edge with dim scene-art pixels. Uniform color-distance
cannot separate "dark scene gradient bleeding to edge" (intentional) from
"UI chrome truncated at edge" (defect). Both are non-background.

## Instrument gaps this case exposes

1. **edge_contact needs a truncation signature, not just color distance.**
   Content cut mid-element produces a hard edge exactly at the boundary;
   scene art produces gradients. Compare border-strip columns against
   interior — a consistent hard vertical/horizontal edge at x=w-1 or
   y=h-1 is the clip signature.
2. **objects_at_edge margin is too tight for detection slack.** Mirage
   under-covers clipped objects by ~3%; margin 2% misses them. Widen to
   ~5% or add a confidence-collapse flag (score drop vs. expectation).
3. **No detector reads detection confidence.** score 0.899→0.309 across
   control/defect is a real signal currently discarded.

## Verdict

**MISS.** The defect is real, typical, and the instrument walked past it.
This entry exists to be fixed against: re-run after the truncation-
signature detector lands and this case should flip to CAUGHT.

## Re-run 2026-11-15 — CAUGHT (after object-level fix)

Fix applied: `objects_at_edge` margin 2%→5% (Mirage under-covers clipped
objects ~3%) + `suspect` flag for edge objects with score <0.5.

Defect case now reports:

```
objects at edge:
  light       right          score=0.341  suspect=True
  smartphone  top,right,bottom  score=0.309  suspect=True
```

Controls (uncropped originals): `.47` and `.53` clean; `.39` flags
`smartphone bottom` at score 0.881 → `suspect=False` — an honest edge
fact (the phone does sit near the bottom there), not a clip alarm.

**Flipped MISS → CAUGHT** on the object-level signal. The pixel-side
truncation signature remains unbuilt — edge_contact still can't see
dark-on-dark content — but the named suspect list is now strong enough
that a reasoning model reading this JSON would investigate.
