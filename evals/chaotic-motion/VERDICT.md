# VERDICT: chaotic-motion — PARTIAL (instrument-alone, flicker half only) / PARTIAL (instrument+reasoning)

## Defect planted

`frame_01..06.png` (800×580) — six frames of a light-theme "Design Sync"
meeting card: static shared-screen preview, participants panel, control
pills. Everything is identical across frames **except the voice-activity
subsystem**, which carries the planted defect — uncontrolled/erratic
motion of the kind an agent ships from unseeded per-frame randomness:

1. **Discontinuous jump** — the green "active speaker" ring teleports
   between participants *every* frame (Maya → Alex → Jordan → Sam → Maya
   → Alex). No dwell, no continuity.
2. **Amplitude chaos** — the 9-bar waveform next to the active speaker is
   re-rolled to random heights (2–14px) every frame; bars teleport
   full-range with zero frame-to-frame correlation (measured lag-1
   autocorr −0.19 vs +0.39 on the smooth control).
3. **Flicker** — the red LIVE pill is present on frames 1,3,5 and gone on
   2,4,6: hard on/off alternation, not a pulse.

Bug story: `setActiveSpeaker(participants[Math.floor(Math.random()*4)])`
in the render loop, `bars = heights.map(() => rand(2,14))` with no lerp,
`{unstable && <LivePill/>}`. `build_frames.py` (PIL) regenerates the
defect reel; `build_control.py` regenerates `control-smooth/` — the same
scene with dwell-2 speaker turns, sinusoidal waveform, pill always on.

Verified programmatically before running eyes: pill-region red pixels
1770 on odd frames / **0** on even; green-ink row histogram puts the
ring+waveform on row sequence 0,3,1,2,0,3; per-pair pixel diffs touch
**only** the pill and participants regions (0 changed px in
shared-screen, header-left, controls).

Distinct from `frozen-frames` (TOO-STILL: duplicated frame → lone
`0.0%` pair): this is TOO-MUCH — every frame differs, nothing is static,
and the anomaly is in the *pattern*, not any single pair's magnitude.

## What eyes reported — defect reel, pixel-only (`--no-records`)

```
6 frames, records=off

frame_01.png -> frame_02.png: changed 1.2%  mean|d| 1.83
frame_02.png -> frame_03.png: changed 1.2%  mean|d| 1.76
frame_03.png -> frame_04.png: changed 1.2%  mean|d| 1.74
frame_04.png -> frame_05.png: changed 1.2%  mean|d| 1.78
frame_05.png -> frame_06.png: changed 1.2%  mean|d| 1.76
```

Five pairs, five identical readings. No static pairs, no spike, no
outlier — the chaos is *uniform*. `diff_bbox` (from `--json`) is
`[613,113,910,726]`/`[613,113,910,602]` on the 256×186 working canvas —
confined to the pill+participants corner, correctly localizing *where*
motion lives, but saying nothing about its character. Verified in
original coords: changed pixels exist only in the pill bbox and the
participant rows; the ymax alternates 726↔602 exactly tracking whether
the lowest row (Alex, row 3) holds the waveform that pair.

## What eyes reported — defect reel, with Mirage records

```
6 frames, records=on

frame_01.png -> frame_02.png: changed 1.2%  mean|d| 1.83  labels 0.60  ocr 0.96
frame_02.png -> frame_03.png: changed 1.2%  mean|d| 1.76  labels 0.20  ocr 0.96
frame_03.png -> frame_04.png: changed 1.2%  mean|d| 1.74  labels 0.25  ocr 0.93
frame_04.png -> frame_05.png: changed 1.2%  mean|d| 1.78  labels 0.25  ocr 0.96
frame_05.png -> frame_06.png: changed 1.2%  mean|d| 1.76  labels 0.25  ocr 0.93

lifecycle departures (departures_only):
  solo_departure         window
```

`--json` pair detail — the flicker is legible, the chaos is not:

```json
pair 01->02: ocr.unmatched ["live"]            labels only_a ["bar"]      only_b ["bar chart"]
pair 02->03: ocr.unmatched [".lllhl."]         labels 0.20  only_a ["bar chart","text label","window"] only_b ["text"]
pair 03->04: ocr.unmatched ["live","i..ll.."]  labels 0.25
pair 04->05: ocr.unmatched ["illl"]            labels 0.25
pair 05->06: ocr.unmatched ["live","iul-."]    labels 0.25
```

`frames_detail[].text` — `"LIVE"` present in frames **1,3,5 only**
(absent 2,4,6), matching the pixel-verified pill flicker exactly.
`"live"` is the only *real* string in any `unmatched` list, and it
appears on exactly the three on→off pairs.

The waveform bars produce a second, noisier signature: Mirage OCRs the
bar glyphs as garbage text — `'.lllhl.'`, `'i..ll..'`, `'illl'`,
`'iul-.'`, `'..llllL.'` — a **different phantom string on every frame**,
each unmatched on its outgoing pair. The chaotic animation literally
generates non-repeating OCR noise.

Object names churn every pair (`bar`/`bar chart`/`text label`/`text`/
`window` rotating through `only_a`/`only_b`) — labels never stabilizes:
0.60, 0.20, 0.25, 0.25, 0.25.

## The control probe — same scene, smooth motion (`control-smooth/`)

This is the falsifying check. Same card, same copy, same colors; only
the motion fixed: speaker dwells 2 frames/turn, waveform follows smooth
sinusoids, pill always on.

```
frame_01.png -> frame_02.png: changed 0.1%  mean|d| 0.08  STATIC  labels 0.50  ocr 0.96
frame_02.png -> frame_03.png: changed 0.7%  mean|d| 0.88         labels 0.50  ocr 0.96
frame_03.png -> frame_04.png: changed 0.1%  mean|d| 0.08  STATIC  labels 0.50  ocr 1.00
frame_04.png -> frame_05.png: changed 0.7%  mean|d| 0.88         labels 1.00  ocr 0.93
frame_05.png -> frame_06.png: changed 0.1%  mean|d| 0.08  STATIC  labels 0.50  ocr 1.00

static pairs: [[f1,f2],[f3,f4],[f5,f6]]
lifecycle: 3 departures — 'Brand Designer', 'Product Designer'
           (coordinated), 'Brand Des igner' (solo) — all Mirage noise
```

What the control proves:

- **Pixel channel CAN see the difference — but only against a
  reference.** Defect: uniform 1.2%/1.76 on all 5 pairs, zero static.
  Control: alternating 0.08%/0.88 with STATIC flags on dwell pairs —
  the healthy reel has *rhythm* (quiet pairs inside a dwell, motion at
  turns); the defect reel is a flatline of churn. Alone, "every pair
  changes 1.2%" is indistinguishable from any continuously-animating
  healthy UI; the instrument has no motion-coherence channel and no
  baseline to compare against.
- **labels churn is Mirage noise, not defect.** Control scores 0.50–1.00
  with the same `bar chart`/`text label`/`window` vocabulary
  flip-flopping. The defect's 0.20–0.25 is lower but the same failure
  class — on synthetic flat UI the labels channel cannot attribute
  chaotic motion. (Defect's slightly lower floor is consistent with
  more pixel churn, but the instrument cannot say that.)
- **Phantom waveform OCR is not defect-specific.** Control pairs also
  report unmatched garbage (`'allll.'`, `'iil.ll'`, `'i.lll'`,
  `'slide3'`) — the bars look like text strokes to Mirage regardless of
  how smoothly they move. What IS defect-specific: the garbage differs
  *every single frame* on the defect reel vs recurring-ish reads on
  control — a churn-rate difference no metric currently computes.
- **`'LIVE'` is the clean attribution.** Present in all 6 control frames,
  exactly frames 1,3,5 on the defect reel; `live` unmatched on exactly
  the three on→off pairs and never on control. The flicker half of the
  defect is fully recoverable from shipped JSON.
- **lifecycle-diff is noise-dominated here.** The *healthy* reel
  produced 3 departures (all Mirage OCR churn, low confidence); the
  defect reel produced 1. The detector that exists for entity
  presence/absence saw nothing defect-related on either reel.

## Instrument gaps this case exposes

1. **`reel` measures per-pair magnitude, never motion coherence.** Pixel
   diff answers "how much changed"; chaotic motion is a statement about
   *how* things changed across time — trajectory smoothness,
   acceleration continuity, oscillation periodicity. No channel computes
   it, so erratic and eased animation are indistinguishable at the fact
   level (control vs defect prove the pixel numbers *can* differ —
   1.2% flat vs 0.08/0.7 alternating — but only a reasoning layer holding
   both reels could say which is which; the instrument itself has no
   "expected motion" model).
2. **The lifecycle detector evades flicker by construction.** It
   requires ≥2 consecutive present AND ≥2 consecutive absent frames —
   the rule that excludes churn is exactly what strict alternation
   (101010) never satisfies. `'live'` strobes every frame and produces
   zero lifecycle events. The one temporal entity-tracker in the stack
   is blind to the flicker half of this defect class.
3. **`frames_detail` strips geometry.** Object bboxes — the data that
   would let a tracker follow the speaking ring row-to-row — are
   discarded before the report (same wall aspect-abuse and z-order hit).
   The teleporting highlight leaves no positional trace in the record;
   only its *indirect* churn (labels instability, phantom OCR) survives,
   and that churn is noise-dominated.
4. **No per-reel aggregation or baseline.** Five identical 1.2% diffs +
   labels never above 0.60 + a phantom unmatched string on 4/5 pairs is
   a *pattern* — "everything is unstable all the time" — but `reel`
   emits only per-pair rows. Nothing computes means, variance, streaks,
   or "N consecutive pairs below threshold". frozen-frames' upgrade
   (static-pair summary) was the first sequence-level fact; chaos needs
   its sibling.
5. **Downscale dilutes small animated regions.** `frame_diff` works on a
   256px-max canvas; the waveform+ring region is a few % of pixels, so
   full-range chaos reads as a modest 1.2%. The defect's true per-region
   churn (bars repainting ~100% of their area every frame) is invisible
   without region-referenced diffing.

## What would catch this

Concrete instrumentation, cheapest first:

1. **Flicker/strobe detector on presence masks (~20 lines, zero new
   model calls).** `lifecycle_diff.collect_events` already computes
   per-frame presence bitmasks for every text string and object name —
   it then *discards* the runs shorter than `min_present`. Emit a
   second verdict kind: mask with ≥3 present/absent transitions and max
   run length 1 → `strobe`. On this reel: `'live'` mask = 101010 →
   named fact "LIVE strobes every frame". Same arithmetic catches any
   hard-blinking UI element. This alone flips the flicker half to
   CAUGHT.
2. **Lag-1 autocorrelation / innovation-whiteness on animated-region
   crops (the chaos signature).** Union the per-pair `diff_bbox`es to
   find animated regions; for each region, extract a per-column (or
   per-pixel) time series across frames and measure frame-to-frame
   predictability. Eased motion is strongly autocorrelated; `Math.random()`
   output is white (autocorr ≈ 0, often slightly negative). Toy numbers
   on this artifact's actual heights: defect −0.19 vs control +0.39 —
   directionally right even at n=6; a real implementation wants ≥10
   frames and per-pixel series, where the separation is much wider.
   This is the detector that names *unseeded randomness* specifically —
   the bug's actual mechanism.
3. **Centroid-trajectory check on diff clusters.** Cluster changed
   pixels per pair (the ring move, waveform, and pill are spatially
   distinct); track cluster centroids across the sequence. Healthy
   animation: bounded velocity, consistent direction. This reel: the
   speaker-ring centroid jumps ~200px row-to-row every frame with
   sign-flipping direction — a teleport signature computable from
   `diff_bbox` data already emitted, no model.
4. **Per-reel health summary.** Aggregate what `reel` already collects:
   `changed_pct` mean/CV, count of static pairs, labels min/mean,
   singleton-OCR rate (strings seen in exactly 1 frame — the waveform
   garbage is 5-for-5 unique on the defect reel). "0 static pairs +
   labels <0.3 on 4/5 pairs + 5 singleton OCR strings" is a citable
   reel-level anomaly fact; today it exists only as five rows a reader
   must mentally aggregate.
5. **Region-referenced diff budget.** Diff *within* each animated
   element's bbox (from union-of-diffs or record bboxes) rather than
   whole-frame: the waveform region repaints ~full-range every frame —
   changed_pct_inside ≈ 40–80% vs the frame-level 1.2%. An "element
   repainting >50% of its area on >3 consecutive pairs" rule catches
   strobes and teleporting content that whole-frame percentages dilute
   away at 256px.

## Verdicts

- **Instrument alone (`reel`, console + `--json`): PARTIAL — and the
  weakest kind.** The flicker's fingerprint is *in* the shipped JSON:
  `"LIVE"` in `frames_detail.text` on exactly frames 1,3,5 and `"live"`
  in `ocr.unmatched` on exactly the three on→off pairs — pixel-verified
  real (red px 1770↔0). But nothing marks it: the console shows five
  uniform 1.2% diffs and unexplained score dips; recovering the pattern
  requires hand-cross-referencing `frames_detail` against
  `pairs[].ocr.unmatched`, one JSON level below the default surface —
  the same wall object-dropout documented. For the chaotic-motion half
  proper (teleporting speaker, random waveform) the instrument-alone
  verdict is effectively **MISS**: pixel diffs cannot distinguish erratic
  from eased motion, labels churn is within the Mirage noise floor the
  control reel exposes, phantom OCR strings occur on the healthy reel
  too, and lifecycle-diff sees nothing. Split honestly: flicker
  PARTIAL, motion-chaos MISS → overall PARTIAL.
- **Instrument + reasoning: PARTIAL.** A reasoning layer reading the
  full JSON can name the strobe — "LIVE present frames 1,3,5 only;
  absent pixels verified pattern; the live indicator flickers every
  frame" — a real, citable catch of component 3. It cannot catch
  components 1–2: the records carry no positions (ring teleport leaves
  no trace), pixel diffs are coherence-blind, and the control reel
  proves the churn signals are noise-dominated — an honest reasoning
  layer must report "records unstable, cause unattributable" for the
  motion half. Generous reading: suspicion on all three components;
  proof on one.

This entry exists to be fixed against: the strobe detector (#1) is ~20
lines on data already collected and would make the flicker half a named
fact; the autocorrelation/trajectory checks (#2–3) are the only
instruments that can see *erratic* motion at all — today the stack can
measure that frames differ but never how they move.
