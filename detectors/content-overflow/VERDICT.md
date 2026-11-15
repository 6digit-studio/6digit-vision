# content-overflow — detector verdict

Spec: non-container objects pinned at LEFT/RIGHT frame edges, requiring
a same-edge row cluster (>=2 findings with >=30% y-overlap) — the
clipped-row signature of horizontal overflow.

## Build history (honest)

1. **Pixel edge-ink**: measured unreliable — clipped cards emit thin
   rules spanning full viewport width (mimic full-bleed sections),
   near-bg fills invisible to bg-distance, tall edge blocks are
   panels/scrollbars. Abandoned.
2. **Record edge-pinning**: fired on defect but FP'd on BBC/MDN/Wiki —
   scores AND widths overlap completely with legit edge chrome.
3. **Clipped-row coherence** (final): corpus FPs are OPPOSITE-edge
   same-row pairs (nav bars, section rules — full-width chrome);
   the defect is a SAME-edge cluster (2 clipped cards, one row).

## Results

| image | verdict |
|-------|---------|
| web-breakpoint/defect | **overflow_detected** — right-edge cluster, 2 objects y-overlap 0.66 |
| web-breakpoint/control | clean |
| all 7 corpus images | clean (BBC/MDN/Wiki edge chrome correctly excluded) |

Known limit: detects the row-cluster signature; a SINGLE clipped
element or fill-only clip (fill ~= page bg) stays dark — documented,
not patched.
