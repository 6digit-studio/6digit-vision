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
