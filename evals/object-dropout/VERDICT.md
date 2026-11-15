# VERDICT: object-dropout — PARTIAL

## Defect planted

`frame_01..05.png` — five frames of a light-theme "Site Traffic"
analytics card (640×400, built by `build_frames.py`, PIL). A visitor
count ticks up (12,847 → 13,102), a 7-bar chart animates every frame,
and a red "LIVE" pill badge (pulse dot + label) sits in the card
header.

**The defect: the LIVE badge is present in frames 1–2 and silently
absent from frames 3–5.** Nothing else changes to explain it — the
count keeps climbing, the bars keep moving, the footer still reads
"Auto-refresh every 5s · data delayed ≤ 5s". This is the classic
`{isStreaming && <LiveBadge/>}` conditional that desynced (or a render
that failed once and never recovered): a *missing* element mid-sequence
while surrounding live data keeps flowing. Verified programmatically:
the badge region holds ~1,600–1,700 red pixels in frames 1–2 and **0**
in frames 3–5.

Distinct from `frozen-frames` (duplicated frame → `changed 0.0%`):
here motion continues normally and one element's pixels + record
entries drop out. Most typical instance of the class — no adversarial
geometry, no contrast games, everything else coherent.

## What eyes reported — pixel-only (`--no-records`)

```
5 frames, records=off

frame_01.png -> frame_02.png: changed 1.9%  mean|d| 2.26
frame_02.png -> frame_03.png: changed 2.6%  mean|d| 3.72
frame_03.png -> frame_04.png: changed 1.9%  mean|d| 2.26
frame_04.png -> frame_05.png: changed 1.9%  mean|d| 2.27
```

The dropout pair is the sequence maximum on both pixel metrics
(2.6% / 3.72 vs ~1.9% / ~2.26 baseline) — but "more changed" is not
"an element vanished"; the elevation is modest and `diff_bbox`
([137,206,895,606] on the 256×160 working canvas) spans the whole
chart+count region, not just the badge.

## What eyes reported — with Mirage records (console)

```
5 frames, records=on

frame_01.png -> frame_02.png: changed 1.9%  mean|d| 2.26  labels 1.00  ocr 0.89
frame_02.png -> frame_03.png: changed 2.6%  mean|d| 3.72  labels 0.40  ocr 0.78
frame_03.png -> frame_04.png: changed 1.9%  mean|d| 2.26  labels 0.50  ocr 0.88
frame_04.png -> frame_05.png: changed 1.9%  mean|d| 2.27  labels 0.50  ocr 0.88
```

All three channels agree pair 2→3 is the anomalous transition: max
pixel diff, min label stability (0.40), min OCR overlap (0.78). But the
console output shows unexplained score dips — no cause, no named
object.

## What eyes reported — `--json` (the decisive layer)

Per-frame `frames_detail[].text` — the badge's label exists only in
the first two frames' records:

```
frame_01 text: [..., "LIVE", ..., "12,847", ...]
frame_02 text: [..., "LIVE", ..., "12,912", ...]
frame_03 text: [..., "12,987", ...]        <- no "LIVE"
frame_04 text: [..., "13,044", ...]        <- no "LIVE"
frame_05 text: [..., "13,102", ...]        <- no "LIVE"
```

Pairwise record diffs name what vanished:

```json
pair frame_02 -> frame_03:
  "labels": {"score": 0.4,  "only_a": ["red circle"], "only_b": ["bar", "logo"]}
  "ocr":    {"score": 0.7778, "unmatched": ["live", "12,912"]}

pair frame_03 -> frame_04:  ocr.unmatched: ["12,987"]   (count only)
pair frame_04 -> frame_05:  ocr.unmatched: ["13,044"]   (count only)
pair frame_01 -> frame_02:  ocr.unmatched: ["12,847"]   (count only)
```

`"live"` is the **only non-numeric string in any pair's `unmatched`
list**, and it appears in exactly one pair — the dropout pair.
`"red circle"` (Mirage's read of the badge/pulse dot) appears in
`only_a` on the same pair. `eyes describe` confirms at frame level:
`frame_01.png` objects include `"red circle"` and text includes
`"LIVE"`; `frame_03.png` has neither — every other record entry is
unchanged modulo the animated count/bars.

## Instrument gaps / ambiguity observed

1. **No dropout detector, no sequence summary.** `reel` emits raw
   per-pair facts; nothing computes entity lifecycles. The evidence
   ("live" unmatched once, "LIVE" absent from frames 3–5 text,
   "red circle" gone) is all *in* the JSON but requires the reader to
   cross-reference `frames_detail` against `pairs[].ocr.unmatched`.
   The default console output — scores only — cannot distinguish this
   from a bigger animation step.
2. **Label stability is noisy on synthetic UI.** Post-dropout pairs
   3→4 and 4→5 report `labels 0.50` from phantom `"bar"`/`"logo"`
   detection churn between near-identical dropout frames (frame_03
   detects `bar, bar chart, logo, text label`; frame_04 detects only
   `bar chart, text label`). The object-level story is therefore
   muddy: 0.40 on the dropout pair is the minimum, but 0.50 persists
   afterward for reasons unrelated to the defect. OCR carried the
   clean attribution; labels could not.
3. **`scene.style` flipped `"screenshot"` → `"infographic"`** exactly
   at the dropout boundary (frame_02 vs frame_03 records) — Mirage
   noise on synthetic UI, but a reasoning layer could misread it as a
   scene change. Same noise class frozen-frames already documented.
4. **Pixel signal is real but unattributed.** Pair 2→3 is the max on
   `changed_pct` (2.6%) and `mean_abs_diff` (3.72), and `diff_bbox`
   does cover the badge's neighborhood — but the box spans the whole
   animating chart region, so it localizes poorly. Nothing separates
   "element erased" (content→background pixels) from "element moved"
   or "element changed".

## What would catch this

Concrete instrumentation, cheapest first:

1. **Entity-lifecycle diff in `reel` (data already collected).**
   `frames_detail` already stores per-frame object-name sets and OCR
   strings; `reel` currently only Jaccard-scores *pairs*. Diff the
   sets across the sequence and emit lifecycles: `"LIVE" present
   frames 1–2, absent 3–5` / `"red circle" present 1–2, absent 3–5`.
   A persistence rule (seen in ≥2 consecutive frames, gone in ≥2
   consecutive later frames, siblings still animating) separates
   chrome from the per-frame-churning count digits — counts produce 5
   distinct one-frame strings and are excluded for free. This turns
   the dropout into a named fact with zero new model calls.
2. **Erase-signature detector (OpenCV, no model).** Register frames
   (same scene, static layout), compute per-pixel signed diffs, and
   classify clusters: badge removal is a *content→background*
   transition — saturated red/white-glyph pixels in frame_02 become
   card-white in frame_03 — whereas bar/count animation is
   bidirectional. A "vanished color cluster" check (each saturated
   color blob in frame i must have a counterpart in i+1) or
   normalized-cross-correlation of the header patch across frames
   (corr ≈ 1.0 while badge lives, ≈ background-only after) catches
   dropouts even for elements Mirage never names.
3. **Two-pass VLM judge on record pairs.** Feed consecutive compact
   records (not pixels) to a small model with the question "which
   persistent UI elements disappeared without explanatory change?"
   The records already contain everything needed — this is `eyes
   ask` extended from single-image to pair/sequence input, matching
   the PRD's facts-out/judgment-department split.
4. **OCR-string stability floor.** Strings that persist verbatim
   across ≥2 frames are chrome candidates; alert when one vanishes
   while the frame's other chrome persists. "LIVE" qualifies; the
   ticking count does not (value changes every frame). Nearly free —
   pure set arithmetic on `record["text"]`.

## Verdict

**PARTIAL.** The defect is real, typical, and demonstrably exhibited
(badge pixels verified: ~1,700 → 0). The instrument surfaced the
dropout *pair* unambiguously — it is the simultaneous maximum of
pixel diff and minimum of both coherence scores — and the `--json`
record names the casualty precisely: `"live"` is the only vanished
OCR string in the entire reel, `"LIVE"` absent from frames 3–5 text,
`"red circle"` gone from objects. What is missing is the *naming*:
no detector, flag, or summary says "object dropout"; the default
console shows unexplained score dips; and the labels channel's
synthetic-UI noise (0.50 post-dropout from phantom `bar`/`logo`)
leaves object-level attribution ambiguous without cross-referencing
`unmatched` lists by hand. A reasoning layer reading the full JSON
calls this instantly; a reader of the console output sees only that
something changed more on one pair. Under the instrument's
facts-not-verdicts contract the facts are all present — this sits
between frozen-frames' self-evident `0.0%` and text-truncation's
invisible interior clip: the anomaly is flagged by every channel,
but its identity as a *missing element* lives one JSON level below
the default surface.
