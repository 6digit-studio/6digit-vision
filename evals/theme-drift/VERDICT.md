# VERDICT: theme-drift — PARTIAL

## Defect planted

`state-a.png` / `state-b.png` (1100×760) — two states of the same
"Overview" dashboard in a fictional analytics app. **State A**
("This week" selected) uses the brand blue accent `#2563eb` throughout.
**State B** ("This month" selected) is the theme break: the app shell —
sidebar nav, logo, "New report" button, avatar — keeps brand blue
(shared components), but every main-content accent element renders in
violet `#7c3aed`: the active toggle segment, stat-card icon chips,
the chart's current-period line/area/dots/legend, "Export CSV" and
"View all" links, and the goals progress bars. No semantic
justification — this is not a success/error/warning state; it is the
canonical agent token-leak: a regenerated view variant that carried a
different `--accent` token than the shell.

Non-color differences between states are deliberately minimal and
legitimate: the subtitle ("Week of Nov 10 - 16, 2025" → "November 2025
- month to date") and which toggle segment is active. Layout, data,
and all other strings are identical.

`make_images.py` (PIL) regenerates both. Verification was
programmatic (this environment cannot display images): chrome regions
are **pixel-identical** (diff bbox `None` on sidebar, search, button,
avatar); 105,711 px (12.6%) differ, all inside the content column;
mean |ΔLuminance| = 4.0 vs mean |ΔRGB| = 19.9 — a hue rotation, not a
geometry or shading change. Sampled accent pixels: state A chart
`(37,99,235)` = `#2563eb`, state B same coordinates `(124,58,237)` =
`#7c3aed`.

## What eyes reported

### `uv run eyes palette state-a.png` / `state-b.png`

```
A: #fcfcfc 54.0%  #ecf4f4 24.3%  #f4fcfc  9.8%  #f4f4fc 1.8%
   #dcecfc  1.1%  #f4f4f4 0.9%  #e4ecf4 0.6%  #ececf4 0.6%
B: #fcfcfc 63.5%  #ecf4f4 24.3%  #f4f4fc 1.8%  #f4f4f4 0.8%
   #dcecfc  0.7%  #e4ecf4 0.6%  #ececf4 0.6%  #fcf4fc 0.4%
```

**Neither accent hue appears in either top-8.** The saturated accents
(button, line, chips, bars) are each <1% of pixels and get split across
5-bit bins; only the *tinted blends* show — `#f4fcfc` (blue-tint blend,
9.8%) is gone in B, `#fcf4fc` (violet-tint blend, 0.4%) appears. The
palette sees *that* color mass moved, not *which* hue moved.

### `uv run eyes score state-a.png state-b.png`

```
score: 64.8 / 100

  palette   82.8  {}
  objects   72.5  {'matched': 33, 'missing': ['text label' x6],
                  'extra': ['button' x19]}
  layout     7.2  {'mean_center_dist': 0.3247, 'pairs': 33}
  text      95.8  {}
  scene     65.0  {}
```

Reverse direction `score state-b.png state-a.png`: **64.4** —
`objects` missing/extra swap to 19×'button' missing / 6×'text label'
extra. Symmetric composite; the objects/layout drops are stable across
direction.

### `uv run eyes describe <img> --stats` (excerpts — full records in /tmp)

State A: 39 objects = 38×`text label` + 1×`window`; **all 38 text
labels carry `description.color: "blue"`** regardless of actual glyph
color. `scene: {"setting": "computer screen", "style": "screenshot"}`,
reasoning: `"white window with blue buttons, gray sidebar, blue text
labels"`.

State B: 52 objects = 32×`text label` + 19×`button` + 1×`window`;
`description.color` counter: **51×"blue", 1×"white" — zero violet/
purple tokens anywhere**. Reasoning again: `"white window with blue
buttons, gray sidebar, blue text labels"`. Mirage calls the violet UI
"blue."

`_color.objects` mean_hex is background-dominated on both
(`#d7d8dc`/`#eef2f0` per bbox) — the accent pixels are a sliver of each
bbox, so the measured-color layer never isolates them.

### `uv run eyes layout <img> --describe`

Both states produce essentially identical reports:

```
edge contact (bg #fcfcfc, strip 4px):
  top 0.0%  right 4.7%  bottom 0.0%  left 0.0%
objects at edge: 17 hits in A (16 'text label' + 'window'),
  21 in B (13 'text label' + 7 'button' + 'window'), nearly all
  suspect=True (Mirage box noise on flat UI; 'window' all-sides
  score=0.64, suspect=False)
bbox overlaps: (none)
text flush at interior edge: 4 hits, identical strings both states
  ('lenterprise', '3,891', 'NPS score', '88%' flush to line_y=708)
legibility flags: ~20 per image, identical set both states —
  mostly 10-12px FAINT/SUB gray text at contrast 1.5-3.5
  (a real but state-invariant minor issue in the mock, correctly
  not attributed to the theme break)
```

## Why PARTIAL, not CAUGHT or MISS

**What surfaced:** `score` 64.5/100 is a loud, correct high-level fact —
these two states are substantially different (prior near-identical
pairs scored 95-98). And `palette` at 82.8 is the only component whose
drop corresponds to the true defect axis (hue). A reasoning layer told
"same screen, two states" *could* zero in on palette.

**What is missing:**

1. **No component names the defect axis.** `score_palette` returns
   `{score: 82.8}` with empty detail — no hex diff, no hue identity.
   The two largest weighted drops — `objects` 72.5 and `layout` 7.2 —
   are Mirage label noise on pixel-identical geometry and actively
   *misattribute* the difference to object identity and position.
   `layout` claims `mean_center_dist 0.3247` where the geometry is
   literally identical outside hue — a fabricated signal pointing the
   reasoning layer the wrong way.
2. **Mirage's color channel fails on this input.** It describes the
   violet state's UI as "blue buttons, blue text labels" — the
   `_obj_signature` color-token disjointness rule (score.py:70) can
   never fire because both sides claim "blue."
3. **`eyes palette` cannot name either accent** — both hues sit below
   the top-8 cutoff; only tint blends register.
4. **`layout --describe` is state-invariant** — correctly silent on
   geometry (there is none) and has no theme channel at all.

Net: the instrument detected *that* the states differ and pointed,
weakly, at color — but cannot say the difference is a hue/theme break,
and its strongest signals claim object/position changes that do not
exist. That is ambiguous surfacing, not detection.

## Instrument gaps this case exposes

1. **`score_pair` never compares pixels.** The single most diagnostic
   fact here — 12.6% of pixels differ with mean |ΔL|=4.0 vs |ΔRGB|=19.9,
   i.e. a hue rotation on identical geometry — is invisible to the
   scorer, which sees only records + palette histograms.
2. **No theme/accent coherence model.** Nothing encodes "a design has
   one accent token" — the internal inconsistency in state B (blue
   chrome + violet content on one screen) has no detector.
3. **RGB-bin palette shatters hues.** 5-bit-per-channel quantization
   splits a hue family across bins and dilutes small-area accents;
   an HSV hue histogram weighted by saturation would put the swap in
   the top bins.
4. **VLM color naming is uncalibrated on flat UI.** "blue" for violet
   pixels means the object-color signature layer is dead weight on
   exactly the synthetic-clean inputs agents generate.

## What would catch this

**Accent-hue census — a single-image detector, already demonstrated.**
Sample pixels, RGB→HSV, mask `S>0.35, V>0.35`, histogram hue in 15°
bins. Run on these artifacts:

```
A top hue bins: [(210°, 3624), (135°, 85), (0°, 30)]   # ONE accent family
B top hue bins: [(255°, 1853), (210°, 1761), (135°, 85), (0°, 30)]
```

State A has a single accent family (210° blue; the 135°/0° bins are the
semantic green/red deltas, tiny). State B has **two** — 255° violet
(content token) + 210° blue (chrome token) — the exact signature of a
theming-token split, detectable with zero reference image. A flag like
"≥2 hue families each covering >0.5% of saturated area" flips this to
CAUGHT and generalizes to any half-applied theme. ~30 lines of
numpy/PIL; no model needed.

**Runner-up: chroma-vs-luma pixel diff inside `score_pair`.** Register
the candidate to the reference (same canvas here; phase-correlation or
feature alignment in general), compute per-pixel ΔE in Lab space, and
split the diff into luminance vs chroma components. Report a
`chromatic_drift` fact when geometric/photometric diff ≈ 0 but a
coherent hue rotation covers a contiguous region — here: 12.6% of
pixels, |ΔL|≈4 vs |ΔRGB|≈20. That is the pairwise complement: the census
catches the *internal* inconsistency, the diff catches the *cross-state*
break when both states are individually consistent (e.g., full accent
swap).

Also worth queuing: emit the palette symmetric difference
(colors present in one top-N, absent in the other, with fractions) and
diff `object_color_stats.mean_hex` for matched pairs — both use data
the record already carries but currently discards.

## Re-run 2026-11-15 (integrated instrument) — detector-backed CAUGHT

`detectors/hue-census` is wired into `eyes ask` packs: state-b reports
`accent_hue_split` (violet + blue families) zero-reference. The hue
signal that `score` could not attribute now arrives as a named fact.
PARTIAL -> detector-backed.
