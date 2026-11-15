# web-breakpoint — responsive-layout failure at 480px viewport

First eval class where the DEFECT only exists at a specific viewport:
fixed-width 1100px dashboard in a 480px window vs responsive
flex-wrap control. Both headless Chrome, 480x800.

## Verdicts

| case | instrument | +reasoning | verdict |
|------|-----------|------------|---------|
| defect (fixed-width) | PARTIAL | CAUGHT | right-edge object suspects unique to defect |
| control (responsive) | clean-ish | — | only container window suspect (shared) |

## Evidence

`eyes layout --describe` defect: two 'button' suspects on the RIGHT
edge (bboxes x≈886-980 — cards clipped past the 480px viewport) plus
the container window. Control: only the container window suspect —
its content reflows inside the frame.

The discriminating signal is real: fixed-layout overflow puts content
objects against the right frame edge; responsive layout doesn't.
Reasoning reads "objects at right edge + fixed-width container =
breakpoint failure" in one step. Instrument-alone is PARTIAL because
the container-window suspect is shared noise — the edge OBJECTS are
the tell, and suspect flags alone don't name "clipped", they name
"at edge". An `content_overflow` detector (objects whose bboxes
exceed frame bounds in normalized coords) is the queued spec-level
fix — Mirage bboxes are normalized so clipped content should show
x1 > 1.0 or edge-pinned x0.

## Update — content-overflow detector landed (detector-backed)

`detectors/content-overflow/` built through three measured iterations:
pixel edge-ink abandoned (clipped rules mimic full-bleed), record
edge-pinning FP'd on corpus chrome, final spec = non-container objects
edge-pinned left/right + same-edge row cluster (>=2, >=30% y-overlap).
Verified: defect overflow_detected (right-edge cluster named), control
+ all 7 corpus images clean. Wired into `eyes layout --describe`.
Instrument-alone upgraded PARTIAL -> detector-backed CAUGHT.

## Update — breakpoint generalization test (768px, 320px)

Same defect/control pair recaptured at tablet (768px) and small
mobile (320px) widths. content_overflow verdict: **clean on all
four** — the row-cluster signature does NOT generalize across
breakpoints. At 768px the defect produces 3 edge findings but no
same-edge y-overlap cluster (clipping pattern differs — fewer cards
visible, different row geometry); at 320px Mirage edge-pinning itself
delivers 0 findings (heavy clip changes detection). Honest floor:
detector calibrated at 480px holds there; other breakpoints need
either wider cluster tolerance or per-width calibration — documented
limitation, not threshold-fished.
