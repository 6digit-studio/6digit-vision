# eyes — what it sees, what it catches, what it can't

`eyes` gives text-only models structured sight: a local Mirage perception
model (~22 MB, CPU, $0/call) emits scene/object/OCR records, deterministic
detectors measure geometry and legibility, and `eyes ask` packages the
evidence for whatever reasoning model consumes it. Everything below is
real output from the eval catalog — planted defects, honest verdicts.

## The detectors that catch things

### Occlusion slicing text mid-glyph — `edge-bisect`

![z-order defect](../evals/z-order/defect.png)

A dropdown menu painted *under* a card: "Duplicate" is sliced at the
card edge, "Archive"/"Delete" invisible. `eyes layout --describe`:

```
edge bisects (edge_bisect):
  'n..Eaakn'  horizontal line=239 cov=1.0 ink_dist=3px
```

The corrupted OCR string is named with its slice line. Control stays
clean; 9 out-of-domain eval images verified silent.

### Invoice arithmetic — `totals-consistency`

![semantic-data defect](../evals/semantic-data/defect.png)

Subtotal bound wrong ($87.50) while items sum to $77.50; tax and total
derive consistently from the wrong subtotal — only summing catches it.
No model in the loop:

```
line_items_sum_mismatch: items=77.50 subtotal=87.50 delta=-10.00
(totals_block ok, tax_rate ok — internally consistent, wrong vs items)
```

### Aspect-ratio squash — `anisotropy-census`

![aspect-abuse defect](../evals/aspect-abuse/defect.png)

16:9 dashboard force-fit to square. `eyes ask` pack reports
`anisotropic_squash` — blob cluster aspect 1.786, glyph w/h 0.318.
This is the case `eyes score` *cannot* attribute (defect outscores an
honest letterbox 66.0 vs 51.3 — relative similarity can't see internal
distortion); the detector owns that axis.

### Element dropout mid-sequence — `lifecycle-diff` in `eyes reel`

![object-dropout](../evals/object-dropout/frame_01.png)

A "LIVE" badge present frames 1–2, silently gone 3–5 while everything
else animates:

```
lifecycle departures (dropout_detected):
  dropout   LIVE
  dropout   red circle
```

Cross-channel corroboration (OCR string + object departing at the same
boundary) is what makes it high-confidence; it refuses to false-positive
on frozen frames.

### Flicker/strobe — `strobe` in `eyes reel`

![chaotic-motion](../evals/chaotic-motion/frame_01.png)

Uniform chaos: every pair reports ~1.2% changed — no outlier exists.
The strobe detector names the alternating element anyway:

```
strobes: 'LIVE' (ocr) present [1,3,5] absent [2,4,6]  confidence high
motion_coherence: uncorrelated_motion -0.5631
```

### Theme drift — `hue-census` in `eyes ask`

![theme-drift state-b](../evals/theme-drift/state-b.png)

Same dashboard, content accents drifted blue→violet while chrome kept
brand blue. Zero reference needed — state B alone exposes two hue
families: `accent_hue_split` (violet 261° + blue 220°, ~49/49).

### Hostile type — `lexical-screen` in `eyes ask`

![ocr-hostile defect](../evals/ocr-hostile/defect.png)

Calligraphic wordmark + letterspaced eyebrow: Mirage OCRs
`'delvered wechly'`, `'NE WSPRINGCOLLECTIoN'`. The lexical screen flags
both `non_lexical_text` — no model call, 263k-word lexicon.

### Low contrast — `legibility` in `eyes layout`

![low-contrast defect](../evals/low-contrast/defect.png)

1.45:1 contrast fine print scored 97.9/100 against its own control before
the detector existed. Now:

```
'Prices are estimates...'  contrast 1.18  low_contrast + low_ocr_confidence
```

### Viewport clipping — `objects_at_edge` suspect flag

![clipped-card](../evals/clipped-card/clipped.png)

Card sliced by frame edges. Mirage's detection confidence collapses
(0.899→0.309) — now a named signal:

```
smartphone  top,right,bottom  score=0.309  suspect=True
```

## What the reasoning layer catches (evidence, not detectors)

`eyes ask <img> -q "..."` packs record + findings + detector outputs for
the consuming text model. Two cases live there:

- **text-truncation**: pack surfaces `"Quarterly Revenue Overview Rep"`
  verbatim — "Rep" is a sliced "Report". Text-level truncation is an
  inference problem on OCR output, not a pixel problem.
- **semantic-data**: the ask-pack question "do the items add up?" gets
  summed correctly by the reasoning layer — the deterministic detector
  now covers the additive-checkable subset.

## Honest limits — what it still can't see

- **Internal distortion in `score`**: relative similarity can't detect
  non-uniform resize (aspect-abuse proved it: defect outscores honest
  letterbox). Absolute detectors own that axis — by design, not bug.
- **Invisible boundaries**: `overflow:hidden` clips leave no pixel edge
  (text-truncation needed reasoning-layer judgment).
- **Uniform chaos characterization**: motion-coherence measures
  correlation, not *why* — unseeded randomness vs legitimate data churn
  reads identically (−0.16 on a healthy control). Reported as
  `uncorrelated_motion`, not "chaos".
- **Mirage noise floor**: ~300ms/frame, label instability on UI
  ("blue app icon" vs "orange light"), bbox jitter sets detector floors.
  Every detector documents its measured floor; sub-floor defects are
  genuinely dark.
- **Single-channel dropouts** degrade to `solo_departure`; elements
  Mirage never names are invisible to record-layer detectors.


## The real-backend arc — synthetic art was the easy half

Everything above was calibrated on PIL-drawn evals. The `evals/web-real/`
corpus tests the same detectors on uncontrolled real content: headless
Chrome captures of live sites (example.com, Wikipedia, MDN, BBC, GitHub,
HN), dark-mode emulation, print stylesheets, canvas raster, and scroll
sequences. What real content taught that synthetic art couldn't:

- **`luminance-theme`** — hue drift has a sibling: luminance drift.
  Dark theme + coherent light islands (web-theme-drift defect: 5.2%
  opposite-luminance in 78 rows) fires `luminance_theme_split`.
  BBC's dark masthead fires too — intentional vs drifted is a
  reasoning call, documented boundary.
- **`content-overflow`** — viewport clipping. Aggressive clip (480px
  fixed-width) fires via same-edge row clusters; at 768px defect and
  control converge to identical edge structure — a MEASURED hard
  boundary, not a tuning gap.
- **`nonuniform-scale`** — CSS scaleX(1.35) on canvas: glyph w/h
  median 0.90 vs 0.65 control. The Omni/Metal witness pattern:
  non-DOM raster needs pixel priors, not DOM semantics. Single-band
  evidence = review-flag tier by design.
- **Reel scroll-awareness** — `estimate_vshift` + `scroll_persistence`
  separate "new content scrolled in" from detector churn on real
  captures (verified ~300px steps, persistent_frac ~0.5).

## Detector catalog state

12 verified detectors + integrated layout/legibility/reel surfaces.
Every documented real-content FP class is either gated at spec level
(lexical prefix-noise, hue balance, pixel-edge chrome margin,
edge-bisect underline guard, anisotropy merged-band guard) or proven
unfixable-by-threshold with mechanism named (anisotropy tiny-glyph
geometry, content-overflow moderate clip). 19 eval entries; 30 tests.


## The mimicry arc — screenshot -> working UI approximation

`tools/ui_loop.py` closes the product loop: reference screenshot ->
HTML/CSS candidate -> headless Chrome render -> eyes score + diff +
ask + **pixdiff** -> agent critic edits -> iterate. Three traced runs:

- **ui1 GitHub login** (`loop_runs/ui1/`): 59.2 -> 65.1, CONVERGES on
  structure — palette .91, layout .04->.42, text .66->.86. Stalls on
  Mirage object jitter (.35-.52 oscillation below edit signal) and
  OCR misreads below CSS reach.
- **ui2/ui3 calendar month views** (`loop_runs/ui2/`, `ui3/`):
  21.9->28.3 / 21.8->23.9, PARTIAL — dense day-cell grids break
  Mirage's object/layout components (floor ~0.1, heaviest weights).
  Same app, different months AND different palettes — both channels
  verified responsive to real edits.

### `eyes pixdiff` — the fine-edit channel

Pixel-level diff where semantic score can't see: gaussian-window SSIM
map + pixelmatch-style luminance-scaled threshold + connected-
component regions + heat grid. Verified: identical -> 1.0 exact,
planted shift -> localized regions, ui1 ref-vs-cand -> 0.83 with 12
named diff locations. On ui3 it LOCALIZED the blindness itself — a
16.7%-of-frame top-chrome bbox the blind critic couldn't model.
Division of labor: semantic score = WHAT, pixdiff = WHERE.
Honest blinds: no alignment step, AA/compression noise on dense text,
fidelity-not-correctness (color swaps score high).


## The diff stack — three channels, one job each

`eyes pixdiff` (pixel truth) gained two siblings in the
EYES_FDIFF_CHALLENGE wave — four parallel contestants built standalone
frequency-domain diffs against a shared falsifiable bar; ALL FIVE
criteria CAUGHT by every entry:

| contestant | mechanism | block-shift | 1px-translate | ui1 pair |
|-----------|-----------|------------|---------------|----------|
| **pyramid** (winner) | Gaussian pyramid + phase-corr alignment | .9865 | 1.0 | .8277 |
| phasecorr | FFT phase-correlation + PSR gating | .9806 | 1.0 | .7994 |
| dct-phash | DCT low-band perceptual | .9491 | .995 | .7453 |
| fft-lowband | FFT magnitude low-band | .7512 | ~1.0 | .3720 |

**Winner: pyramid** -> `eyes/fdiff.py` + `pack.fdiff` in ui_loop.
Runner-up phasecorr has the deepest mechanism (PSR-gated subpixel
alignment, semantic-data localization to the glyph) — hybrid candidate.
Honest catalog notes: dct-phash can't see sub-3px motion by
construction; fft-lowband's ui1 signal was weakest.

**The completed division of labor:**
- `score` = WHAT (semantic similarity, Mirage-grounded)
- `pixdiff` = pixel truth (SSIM + AA-aware regions + heat)
- `fdiff` = frequency structure + alignment (kills the 1px-shift
  blindness pixdiff documented)
- `region_map` / `fdiff_region_map` = WHICH-ELEMENT (diff regions ->
  DOM selectors + local diffs + computed styles)

ui_loop packs now carry all of it per iteration — the critic reads
score components, element_diff, detectors, pixdiff, fdiff, and dual
region maps in one JSON.


## The VLM loop — screenshot -> generated UI -> measured convergence

The mimicry arc's second half: a LOCAL vision model (mlx-vlm serving
Qwen3-VL-8B-Instruct-4bit, keyless) generates HTML from the reference
screenshot; eyes measures each render; surgical CSS-only edits iterate.
Full-file regeneration degenerates at 8B-4bit (recursive SVG blobs) —
scoped `<style>`-block edits preserve content and add measurable value.

**vlm1 — GitHub login** (`loop_runs/vlm1/`): 23.0 -> 45.1 -> 45.3 ->
52.6 -> **62.9** in 5 measured iterations. Positions converged to
within ~2% of frame. Trace: `trace.jsonl`, per-iter packs `pack_XX.json`.

Reference vs final candidate:

![reference](../evals/web-real/corpus/github_com_login.png)
![candidate](../loop_runs/vlm1/candidate_v6.png)

Iteration evidence — palette fix (iter2) and centering fix (iter5):

![iter2](../loop_runs/vlm1/candidate_v3.png)
![iter5](../loop_runs/vlm1/candidate_v6.png)

**vlm2 — calendar month view** (`loop_runs/vlm2/`): 9.7 -> 16.9 ->
19.5 -> **22.5** — generalization test on the grid family. Slower,
lower ceiling (dense cells + chrome harder for 8B-4bit), but every
iteration added measurable value. Exact-hex palette feedback was the
unlock (palette .05 -> .22).

![calendar ref](../Screenshot%202026-11-15%20at%2003.00.39.png)
![calendar cand](../loop_runs/vlm2/candidate_v4.png)

Honest mechanics: ~20min per VLM call at ~3tok/s; degeneration modes
documented (starfield soup on complex dark UIs, recursive SVG on
revision); the instrument captures every delta honestly including
plateaus.

## The loop that built this

`challenges/EYES_EVAL_CHALLENGE.md` generates defect cases →
`evals/` catalogs honest CAUGHT/PARTIAL/MISS verdicts →
`challenges/EYES_DETECTOR_CHALLENGE.md` builds instrumentation for the
dark regions → `detectors/` catalogs verified detectors → integration
into `eyes/` → regression. Two waves each; misses are first-class
results — the catalog's value is the honest map of blindness.
