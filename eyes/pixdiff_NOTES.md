# pixdiff — verification notes

## Done-bar checks

- identical images -> score 1.0, ssim 1.0, mismatch 0.0 EXACT
- planted 20px block shift -> 0.983, localized regions at shift edges
- ui1 ref-vs-candidate -> 0.830, 12 regions naming diff locations
  (heading band, form fields — the fine-edit map semantic score lacks)

## Where pixdiff itself blinds (honest)

- **Anti-aliased edges**: sub-pixel rendering differences between two
  "same" UIs (different Chrome versions, font hinting) produce
  low-magnitude deltas — suppressed by luminance-scaled threshold but
  not eliminated; dense text pages accumulate mismatch noise.
- **Compression/resize**: JPEG artifacts or non-integer scaling
  shifts every pixel slightly — SSIM tolerates, mismatch mask may
  still fire on texture regions.
- **Global shifts**: a 1px translation of the whole page reads as
  massive edge diffs (every edge mismatches) — pixdiff has no
  alignment step; it's a same-geometry channel only.
- **Semantic blindness**: a color swap that preserves structure
  (blue button -> green button, same layout) scores high SSIM —
  pixdiff measures fidelity not correctness; intent stays with the
  reasoning layer.

Complement not replacement: semantic score asks "same UI?", pixdiff
asks "same pixels?". ui_loop carries both — critic uses pixdiff
regions for WHERE, semantic components for WHAT.
