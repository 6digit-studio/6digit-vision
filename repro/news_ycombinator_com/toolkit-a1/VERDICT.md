# VERDICT — eyes-repro attempt toolkit-a1

- **reference**: evals/web-real/corpus/news_ycombinator_com.png (1200x800, HN front page)
- **sensing mode**: toolkit-only (no native vision; all perception via eyes commands)
- **approach**: interrogate fact sheet -> hand-authored HTML/CSS -> headless Chrome -> measured loop

## Score trajectory

| iter | score | layout | text | palette | scene | note |
|------|-------|--------|------|---------|-------|------|
| 0 | 48.4 | 0.0 | 71.5 | 53.5 | 100.0 | centered column — wrong position |
| 1 | 63.2 | 97.5 | 51.6 | 53.7 | 100.0 | repositioned to measured x-range |

pixdiff iter1: 0.3863, mismatch 16.2%, 12 regions (all inside story-list area).

## Fact-sheet diff (reference vs candidate)

- background: same family (#f4f4ec dominant both); candidate flatter (86% vs 51% — reference has more tonal variance)
- glow/accently: reference found orange logo blob mean_rgb [250,100,0]; candidate's equivalent blob misregistered (blue-ish [66,66,237] — accent-census noise on small orange elements)
- text_inventory: ref 32 strings (story titles); cand 25 (nav merged, subtexts leaked as items)
- layout_family: BOTH "unstructured" — no list/feed detector exists
- alignment: both left-aligned rows — match
- selection_state: ref = orange logo flame; cand = spurious blue blobs — probe found *a* blob but wrong semantics

## What closed

Column position/width (layout 0.0 -> 97.5), background palette family, left-alignment structure, story-count density.

## What stalled

Text content fidelity (51.6): full-frame OCR truncates titles ~60 chars and my subtext authors/times are fabricated — the instrument cannot supply verbatim long strings cheaply. Font metrics (Verdana vs fallback). Vertical rhythm fine-tuning.

## Instrument gaps (named, first-class)

1. **No list/feed layout-family detector** — structure.py knows grids; "unstructured" is the honest but useless answer for the most common UI family.
2. **No bulk fine-OCR probe** — per-row zoom+describe works but costs N Mirage calls; no batched row-sweep command.
3. **Font identity unmeasured** — nothing reports typeface; candidates guess.
4. **Pane/widget segmentation absent** — figure-ground for "the tile vs environment" still unprobed.
5. **Accent-census semantic gap** — finds blobs but can't name them (logo flame vs link vs icon); needs zoom-label binding (noisy, see calendar '17'/'25' misread).

## Honest call

PARTIAL. The loop closed structural gaps fast (position, palette family, alignment) and stalled on content fidelity — exactly the predicted split: structure is measurable and closable, verbatim text and typography are the residue. Two iterations, honest plateau approached but not proven — more iterations would grind pixdiff without semantic movement.
