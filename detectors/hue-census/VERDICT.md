# VERDICT: hue-census — CAUGHT (assigned gap), with a documented over-fire class

Detector: `detectors/hue-census/hue_census.py` — standalone, PEP 723
(`uv run` resolves numpy+pillow itself), no model calls, ~1–2 s/image.

## Gap filled

From `evals/theme-drift/VERDICT.md`: `eyes score` reported 64.8/"differ"
but **no component named the defect axis** — palette returned
`{score: 82.8}` with empty detail, Mirage described state B's violet UI
as "blue buttons, blue text labels," and the eval's own sketch noted an
HSV hue census "flips this to CAUGHT." This is that census, productized:

- PIL RGB→HSV, mask `S>0.35 & V>0.35` (the sketch's thresholds, verified)
- 15° hue bins, **circular** (0°/360° adjacency handled; clipped.png's
  warm family correctly merges bins 0–2 into one 45°-span family)
- a "family" = maximal run of populated bins; populated = ≥8 px and
  ≥0.05% of saturated px (noise floor)
- significance = ≥1% of saturated px **AND** ≥10% of the dominant
  family's share — the dominance-relative floor is the productization
  the sketch lacked (see below)
- per family: pixel-mean hue (circular, wrap-safe), common-name label,
  share, bbox, 10-column spatial profile; `--json` for machine use,
  `--fail-on-split` for CI (exit 1 on `accent_hue_split`)

## Real output — defect + control

```
$ uv run detectors/hue-census/hue_census.py \
    evals/theme-drift/state-a.png evals/theme-drift/state-b.png \
    evals/clipped-card/clipped.png

evals/theme-drift/state-a.png  1100x760  saturated=14168 (1.695% of px)
    blue     hue~ 220.4° span  15.0°   96.85% of saturated  n=13721  bbox=(24,22)-(1056,714)
    green    hue~ 141.2° span  15.0°    2.29% of saturated  n=325    bbox=(277,236)-(736,677)  (below floors)
    red      hue~   0.0° span  15.0°    0.86% of saturated  n=122    bbox=(709,236)-(855,704)  (below floors)
  VERDICT: SINGLE_ACCENT_FAMILY — one significant family: blue (96.85% of saturated px)

evals/theme-drift/state-b.png  1100x760  saturated=14156 (1.693% of px)
    violet   hue~ 261.2° span  15.0°   48.72% of saturated  n=6897   bbox=(278,113)-(1051,714)
    blue     hue~ 220.4° span  15.0°   48.12% of saturated  n=6812   bbox=(24,22)-(1056,705)
    green    hue~ 141.2° span  15.0°    2.30% of saturated  n=325    bbox=(277,236)-(736,677)  (below floors)
    red      hue~   0.0° span  15.0°    0.86% of saturated  n=122    bbox=(709,236)-(855,704)  (below floors)
  VERDICT: ACCENT_HUE_SPLIT — 2 hue families over significance floors: violet(48.72%) + blue(48.12%). Candidate theme-token split — e.g. shared chrome on one accent and regenerated content on another. Check family bboxes/x_profiles for chrome-vs-content segregation.

evals/clipped-card/clipped.png  620x690  saturated=34218 (7.999% of px)
    orange   hue~  20.2° span  45.0°  100.00% of saturated  n=34218  bbox=(69,11)-(619,421)
  VERDICT: SINGLE_ACCENT_FAMILY — one significant family: orange (100.0% of saturated px)
```

`--json` on state-b (abridged): `verdict: accent_hue_split`,
`significant_families: 2`, `dominant_family: violet`. The x_profiles
carry the chrome-vs-content signature quantitatively — blue's column
profile is `[0.22, 0.02, …, 0.41, 0.35]` (sidebar column + header-button
columns) while violet's is `[0, 0, 0.04, …, 0.31, 0.29, 0.08]` confined
to the content column (x≥278 vs sidebar x<230).

## Zero-reference capability — confirmed

State B **alone** reports the split: violet 261.2°/48.7% + blue
220.4°/48.1% as two significant families. No reference image, no `eyes`
record, no model — the internal inconsistency (shared chrome on brand
blue, regenerated content on violet) is visible in a single census. This
is exactly the "agent token-leak" signature the eval described, and the
hue names (`blue` vs `violet`) fix the specific failure where Mirage
called the violet UI "blue."

## Why the sketch's literal rule wasn't shippable

The eval proposed "≥2 hue families each >0.5% of saturated area." Run
verbatim, that rule **false-positives on state-a.png**: its semantic
status colors (green `+12.4%` deltas, red `-0.4%`) occupy real hue bins
at 2.29% and 0.86% of saturated px — both over 0.5%. The dominance-
relative floor (≥10% of the dominant family's share) rejects them in
both states while keeping the 48/48 violet/blue split. Same mechanism
silences the frozen-frames traffic-light dots (3×177 px, ~2–7% each)
and object-dropout's red element (7.1%).

## Honest limits

- **Over-fire on intentional multi-hue designs.** `evals/semantic-surprise`
  control *and* defect both return `ACCENT_HUE_SPLIT` — a payment card
  with a blue accent + a deliberate red-X/green-check status emblem is
  legitimately two hue families (blue 68% + red 32%; blue 66% + green
  33%). The census measures families correctly; it cannot know intent.
  The verdict is labeled `accent_hue_split` and the note says
  "candidate" — a reasoning layer must judge whether the second family
  is a token leak or a semantic badge. This is the detector's main
  false-positive class: any design with two comparably-sized accent
  hues (status colors, multi-series charts, badges) will flag.
- **Sensitivity floor.** A drifted accent must reach ≥1% of saturated px
  AND ≥10% of the dominant family's share. In concentrated palettes
  (dominant ~50–97%) that is roughly 5–10% of saturated px — a theme
  break confined to a few links/icons will not fire. text-truncation's
  green element sat at 8.76% vs a 9.12% floor — the margin is real but
  not huge.
- **Mask blind spots.** `S>0.35` excludes pastel tints (by design —
  tints are blends of the accent; the saturated core carries the hue)
  and `V>0.35` excludes near-black accents. A theme break expressed only
  in tints or dark shades is invisible to this census.
- **Hue names are anchor-based**, not perceptual (CIEDE2000 etc.). They
  correctly split the eval's blue/violet pair; exotic hues get nearest-
  anchor labels.
- Consumes images only — does not read `eyes` records/reels. Pairwise
  use ("which family is new vs state A") is out of scope; the eval's
  runner-up chroma-diff suggestion covers the cross-state complement.

## Verdict

**CAUGHT** on the assigned gap: fires on state-b naming `violet` +
`blue` as the two families (the exact signature eyes could not name),
stays silent on state-a and the clipped-card control, works with zero
reference, and generalizes (synthetic two-family test → SPLIT; grayscale
→ `insufficient_chroma`; missing file → per-image error, batch continues;
`--fail-on-split` exits 1/0 correctly). The semantic-surprise over-fire
is reported above rather than tuned away — suppressing it would require
an intent model this detector deliberately doesn't have.
