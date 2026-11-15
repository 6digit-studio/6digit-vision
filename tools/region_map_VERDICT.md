# region_map — pixdiff regions -> DOM elements -> edit targets

Auto region->CSS mapper: pixdiff regions matched against candidate
elements (Playwright getBoundingClientRect + computed styles), each
hit scored by LOCAL pixel diff + reported with bg/color/fontSize.

## Verified on ui3 (documented floor case)

- Big chrome region [0,0,646,715]: maps to div.dayhead (local_diff
  .698) + div.banner (.404) — ACTIONABLE: those elements' styling is
  wrong, critic now knows which selector to edit.
- Grid-cell regions map to div.cell/.cell.hi with per-element diffs.
- Coverage-based verdicts: "mapped" / "mostly-unmatched" / "unmatched"
  distinguish CSS-addressable pixels from missing content/images.

## Where mapping itself blinds (honest)

- **Non-CSS pixels**: images, canvas, graphical chrome produce diff
  regions with no element hits -> "unmatched" (correct: can't edit
  what isn't DOM).
- **Region granularity**: connected-component regions merge adjacent
  changes — a region covering 3 elements attributes diff to all;
  per-element local_diff disambiguates partially.
- **Same-rect ambiguity**: two overlapping elements both "hit" —
  z-order/stacking context needed for precise attribution (v2).
- **It maps, doesn't decide**: output is evidence (selector + local
  diff + styles), the critic still chooses the CSS change — by design.
