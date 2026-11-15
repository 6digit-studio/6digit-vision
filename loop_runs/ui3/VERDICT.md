# ui3 — calendar December month-view (week-header variant)

Reference: Screenshot 2026-11-15 at 03.00.47.png (727x759). Same app
as ui2's .39 but December view with day-header ("THU 31 DEC") +
event banner ("New Year's Eve") — palette differs too (neutral
#1c1c1c vs .39's blue-tinted #141c24; palette fix 0->.29 verified
the channel responds to real color edits).

## Trace

| iter | score | pixdiff | palette | objects | layout | text | scene |
|------|-------|---------|---------|---------|--------|------|-------|
| 0 | 21.8 | .473 | .000 | .100 | .000 | .917 | .500 |
| 1 | 23.9 | .472 | .290 | .029 | .000 | .958 | .143 |

## Verdict: family floor confirmed twice — pixdiff names the blind region

Same Mirage dense-grid floor as ui2 (objects/layout ~0). The decisive
new evidence: pixdiff regions LOCALIZE the blindness — region 1 is a
16.7%-of-frame bbox covering the entire top chrome/sidebar area I
couldn't model blind (no image input this session), region 2 the
day-header/banner zone. The instrument doesn't just report "different"
— it reports WHERE, which is exactly what a pixdiff-guided edit loop
needs next. text .96 + palette responsive; semantic score capped by
unmodelable chrome, not by grid structure.

## Payoff test — region_map -> targeted edits (iters 2-3)

Applied region->element->local_diff->style evidence as critic:
- div.dayhead edit (15px->19px, weight 700, brighter): local_diff
  **.698 -> .236** — element-level improvement MEASURED, mechanism
  verified working.
- div.banner accent-border edit: local_diff .404 -> .475 REGRESSED —
  reverted.
- Total score: 23.9 -> 23.8 semantic, pixdiff .4722 -> .4716 — FLAT.

**Honest verdict: mechanism proven, ceiling is input-side.** The
element-level chain works (real CSS edit -> measurable local_diff
move), but total score can't move because the dominant diff region
is unmodelable chrome (16% of frame, no DOM target). region_map
earns integration — it correctly attributed and measured the one
editable target in range — but pushing calendar past its floor needs
image input for the chrome region, not better mapping.
