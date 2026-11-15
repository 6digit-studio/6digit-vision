# testcases — adversarial-ish reference corpus

Four desktop captures (2026-11-15 ~19:08), all dark, low-quality,
deliberately different families. Interrogate facts in
`*_facts.json` per image.

| file | size | content | family stress |
|------|------|---------|---------------|
| 19.08.41 | 548x570 | approval/status timeline ("Request submitted", "Under review", "Approved") | timeline/stepper — no detector |
| 19.08.42 | 536x290 | onboarding carousel ("Plan Build Launch", "Set your goals") | cards/carousel — no detector |
| 19.08.54 | 544x228 | goals widget ("Daily Goals", day selector 5/6) | dense small widget |
| 19.09.12 | 770x1406 | imagery-dominant screen, ~1 text item | figure-ground / non-text content |

Interrogate pass 2026-11-15: all four return layout_family
"unstructured"; dark-bg small-text OCR is the shared stress;
#19.09.12 exposes the non-text comprehension gap entirely.
