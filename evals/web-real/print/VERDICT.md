# print — print-stylesheet emulation via Playwright emulate_media

First print-media captures: Wikipedia WWII + MDN CSS docs at
1200x1600 viewport, `emulate_media(media="print")`. 2026-11-15.

## Detector behavior on print rendering

| image | luminance | hue | lexical flagged | notes |
|-------|-----------|-----|-----------------|-------|
| mdn_print | single | single_accent | 20 | dense small print text -> OCR-noise-scale lexical flags |
| wikipedia_print | **split** | dominant_with_accent | 22 | print CSS keeps dark elements on white — mixed luminance fact |

## Verdict

Print emulation path works (CDP proven again). Floors mostly hold —
luminance/hue/aniso behave; the lexical_screen flagged counts (20-22)
reproduce the documented lossy-OCR limitation at print-text density
(small dense type -> non-word OCR tokens). wikipedia_print's
luminance_theme_split is a real fact about print CSS (dark header/
footer chrome on white page) — candidate-level, intent-vs-fact
boundary as before. content_overflow probe inconclusive this pass
(record-path process-substitution didn't complete cleanly — noted,
not claimed).
