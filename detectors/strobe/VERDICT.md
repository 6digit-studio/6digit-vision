# VERDICT: strobe — CAUGHT (flicker half) / PARTIAL (motion coherence)

Detector for two gaps named by `evals/chaotic-motion/VERDICT.md`:

1. **Strobe/flicker** — `lifecycle_diff.collect_events` already computes
   per-frame presence bitmasks for every OCR string and object name, then
   *discards* runs shorter than `min_present`; the churn-exclusion rule is
   exactly what strict alternation (`101010`) never satisfies. This
   detector keeps the discarded runs: an element whose presence mask
   alternates every frame (≥ `min_transitions` transitions, max run ≤
   `max_run`) is a strobe — the eval's "LIVE strobes on/off" named fact.
   Zero new model calls — `frames_detail` only.

2. **Motion coherence (stretch)** — pixel diffs measure *how much*
   changed, never *how*. Inside the union of per-pair `diff_bbox`es (the
   animated region), each pixel's luminance is a time series across
   frames; lag-1 autocorrelation measures frame-to-frame predictability.
   Eased motion is correlated; `Math.random()` output is white. Reads
   the frame images named in `frames_detail[].file` — no Mirage calls.

## Files

- `strobe.py` — the detector. Accepts a saved `eyes reel --json` file
  (frame paths re-resolved relative to the JSON's dir and repo root), or
  `--reel <inputs...>` to run `eyes reel <inputs> --json` itself.
  Flags: `--min-transitions` (default 3), `--max-run` (default 1),
  `--coh-lo/--coh-hi` (autocorr verdict band, default ±0.10),
  `--no-motion` (skip the image analysis).

## Rule — strobe half

For every OCR string and object label (normalized: lowercase,
whitespace-collapsed — same key as lifecycle-diff), compute the presence
bitmask across frames. **strobe** = `transitions ≥ 3` AND `max_run ≤ 1`
over the *whole* mask — strict alternation, the hard on/off flicker
signature. Elements with ≥3 transitions but any run >1 (partial flicker,
duty-cycle blink, blink-then-vanish like `010100`) are reported under
`alternating_elements`, not named as strobes.

**OCR-split guard:** a *stable* element misread as variant A on odd
frames and variant B on even frames (`LIVE`/`L1VE`) produces two
exact-match strobes for one physical non-flicker. Each strobe is checked
against fuzzy-similar strings in its channel (SequenceMatcher ≥0.75 on
whitespace-stripped keys — lower than `ocr_overlap`'s 0.8 because one
substituted char in a 4-char string must still count as a variant). If
the variant *family* jointly persists across consecutive frames, the
strobe is downgraded to `confidence: "low"` with a note and the sibling
names. Verified synthetically: the `LIVE`/`L1VE` split case yields two
low-confidence strobes; a genuinely absent-half-the-frames `LIVE` stays
high.

## Rule — motion coherence half

Union all per-pair `diff_bbox`es (normalized `[0,1000]`) → the animated
region, padded 10 norm units. Load each frame at native resolution
(lossless PNG → static regions stay exactly constant, no resample
noise), take luminance, and for every pixel inside the region whose
temporal variance > 4.0 compute lag-1 autocorrelation `corr(x[:-1],
x[1:])`. Report mean/median/p10/p90 plus a binary-occupancy variant
(`|x_t − x_0| > 24`, eyes' tol) as corroboration. Verdict on the mean:
`< −0.10` uncorrelated (erratic/white-noise-like), `> +0.10` correlated
(eased), between → ambiguous. Guards: <4 frames → insufficient; <50
animated px → insufficient_motion; no diff_bbox anywhere → no_motion
(static reel); missing frame files → unavailable.

## Defect run — `evals/chaotic-motion`

```
$ uv run python detectors/strobe/strobe.py --reel evals/chaotic-motion
```

```json
{
  "verdict": "strobe_detected",
  "summary": "1 element(s) strobe every frame: 'LIVE' (ocr) present [1, 3, 5] absent [2, 4, 6]. Strict on/off alternation — hard flicker, not a pulse.",
  "params": { "min_transitions": 3, "max_run": 1, "coherence_band": [-0.1, 0.1] },
  "stats": { "tracked": { "text": 38, "objects": 6 }, "frames": 6 },
  "strobes": [
    {
      "element": "LIVE", "channel": "ocr",
      "present_frames": [1, 3, 5], "absent_frames": [2, 4, 6],
      "transitions": 5, "max_run": 1, "value_like": false,
      "ocr_variant_siblings": [], "confidence": "high"
    }
  ],
  "alternating_elements": [
    { "element": "Brand Des igner", "channel": "ocr", "present_frames": [2, 6], "absent_frames": [1, 3, 4, 5], "transitions": 3, "max_run": 3, "value_like": false },
    { "element": "Brand Designer", "channel": "ocr", "present_frames": [1, 3, 4, 5], "absent_frames": [2, 6], "transitions": 3, "max_run": 3, "value_like": false },
    { "element": "Organized by bet - u", "channel": "ocr", "present_frames": [2, 3, 4, 6], "absent_frames": [1, 5], "transitions": 3, "max_run": 3, "value_like": false },
    { "element": "Organized by bet -u", "channel": "ocr", "present_frames": [1, 5], "absent_frames": [2, 3, 4, 6], "transitions": 3, "max_run": 3, "value_like": false },
    { "element": "Product Designe", "channel": "ocr", "present_frames": [2, 3, 4, 6], "absent_frames": [1, 5], "transitions": 3, "max_run": 3, "value_like": false },
    { "element": "Product Designer", "channel": "ocr", "present_frames": [1, 5], "absent_frames": [2, 3, 4, 6], "transitions": 3, "max_run": 3, "value_like": false },
    { "element": "bar chart", "channel": "objects", "present_frames": [2, 4], "absent_frames": [1, 3, 5, 6], "transitions": 4, "max_run": 2, "value_like": false },
    { "element": "text", "channel": "objects", "present_frames": [3, 5], "absent_frames": [1, 2, 4, 6], "transitions": 4, "max_run": 2, "value_like": false },
    { "element": "text label", "channel": "objects", "present_frames": [1, 2, 4, 6], "absent_frames": [3, 5], "transitions": 4, "max_run": 2, "value_like": false }
  ],
  "motion_coherence": {
    "frames": 6,
    "region_norm": [[603, 103, 920, 736]],
    "region_px": [253, 365],
    "animated_px": 5472, "animated_frac": 0.0593, "var_eps": 4.0,
    "mean_lag1_autocorr": -0.5631,
    "median_lag1_autocorr": -0.4082,
    "p10_lag1_autocorr": -1.0, "p90_lag1_autocorr": -0.25,
    "mean_lag1_autocorr_binary": -0.5612, "n_series": 5262,
    "verdict": "uncorrelated_motion",
    "reading": "animated pixels show ~zero/negative frame-to-frame autocorrelation — consistent with unseeded/random motion (white-noise-like); eased animation is correlated",
    "caveat": "only 6 frames (5 lag-1 pairs per pixel); the eval VERDICT notes >=10 frames wanted for a stable estimate — treat as directional. Luminance-only channel: hue swaps at constant luminance are invisible."
  },
  "source": "evals/chaotic-motion"
}
```

*(The `alternating_elements` block above is condensed to one line per
entry for readability — every field shown is verbatim from the real
output; the raw file has the same entries fully expanded.)*

The named fact fires exactly as the eval sketched: `'LIVE'` present
frames 1,3,5 / absent 2,4,6 — the pixel-verified pill flicker — as a
structured fact with `confidence: "high"` and no OCR-variant siblings.
The waveform-bar OCR garbage (`'.lllhl.'`, `'i..ll..'`, …) does **not**
fire: each phantom string is a singleton with ≤1 transition — the strict
alternation requirement excludes churn for free, the mirror image of
lifecycle-diff's ≥2-run rule.

The `alternating_elements` list is honest residue, not hidden: six OCR
*variant pairs* of static text (`'Brand Designer'`/`'Brand Des
igner'` etc. — Mirage reading the same pixels two ways, their masks
complementary) and three object-label rotations (`'bar chart'`/
`'text'`/`'text label'` — present on scattered frame pairs, max_run 2).
None is a strict strobe; all are reported, none named.

Motion coherence reads **−0.5631** mean lag-1 autocorrelation over
5,262 animated-pixel series in the union diff region — deeply negative,
pushed by all three defect components (strobing pill ≈ −1 per pixel,
teleporting ring, white-noise waveform). The binary-occupancy variant
agrees (−0.5612).

## Control 1 — `evals/chaotic-motion/control-smooth` (same scene, eased motion)

```
$ uv run python detectors/strobe/strobe.py --reel evals/chaotic-motion/control-smooth
```

```json
{
  "verdict": "alternating_only",
  "summary": "1 element(s) alternate >= 3 times but hold runs >1 — partial flicker/duty-cycle blink, not strict strobe. See alternating_elements.",
  "stats": { "tracked": { "text": 37, "objects": 6 }, "frames": 6 },
  "strobes": [],
  "alternating_elements": [
    { "element": "window", "channel": "objects", "present_frames": [1, 3, 6], "absent_frames": [2, 4, 5], "transitions": 4, "max_run": 2, "value_like": false }
  ],
  "motion_coherence": {
    "frames": 6, "region_norm": [[603, 243, 893, 736]], "region_px": [231, 284],
    "animated_px": 2712, "animated_frac": 0.0413,
    "mean_lag1_autocorr": 0.3803, "median_lag1_autocorr": 0.6124,
    "p10_lag1_autocorr": -0.25, "p90_lag1_autocorr": 0.6124,
    "mean_lag1_autocorr_binary": 0.3803, "n_series": 2572,
    "verdict": "correlated_motion",
    "reading": "animated pixels are frame-to-frame predictable — consistent with eased/continuous animation"
  }
}
```

*(condensed; `params`/`caveat`/`source` elided — same shape as defect
output.)* **No strobe** — `'LIVE'` is present in all 6 frames, mask
`111111`, zero transitions. The single `alternating_elements` entry is
`'window'` on the *objects* channel (Mirage label churn on the healthy
reel — the eval already documented labels noise; it holds runs of 2 so
it is not a strobe and is reported as such). Motion coherence:
**+0.3803** — eased sinusoid/dwell motion is positively autocorrelated,
opposite sign and ~0.94 apart from the defect's −0.5631.

## Control 2 — `evals/frozen-frames` (duplicate middle frame, different signature)

```
$ uv run python detectors/strobe/strobe.py --reel evals/frozen-frames
```

```json
{
  "verdict": "no_strobe",
  "summary": "No element strobes: nothing alternates presence on every frame (>= 3 transitions with max run <=1 required).",
  "stats": { "tracked": { "text": 15, "objects": 5 }, "frames": 5 },
  "strobes": [], "alternating_elements": [],
  "motion_coherence": {
    "frames": 5, "region_norm": [[166, 452, 912, 704]], "region_px": [477, 100],
    "animated_px": 8091, "animated_frac": 0.1696,
    "mean_lag1_autocorr": 0.2573, "median_lag1_autocorr": 0.5774,
    "mean_lag1_autocorr_binary": 0.3167, "n_series": 3805,
    "verdict": "correlated_motion"
  }
}
```

Correct on both halves: the frozen duplicate produces *fewer* changes,
not alternation — no element strobes, and the pixels that do change do
so as coherent step events (+0.2573), not white noise. Frozen-frames'
TOO-STILL signature and chaotic-motion's TOO-MUCH signature stay
distinct, as the eval demanded.

## Control 3 — `evals/object-dropout` (dropout, not flicker)

```
$ uv run python detectors/strobe/strobe.py --reel evals/object-dropout
```

```json
{
  "verdict": "alternating_only",
  "summary": "2 element(s) alternate >= 3 times but hold runs >1 — partial flicker/duty-cycle blink, not strict strobe. See alternating_elements.",
  "stats": { "tracked": { "text": 13, "objects": 5 }, "frames": 5 },
  "strobes": [],
  "alternating_elements": [
    { "element": "bar", "channel": "objects", "present_frames": [3, 5], "absent_frames": [1, 2, 4], "transitions": 3, "max_run": 2, "value_like": false },
    { "element": "logo", "channel": "objects", "present_frames": [3, 5], "absent_frames": [1, 2, 4], "transitions": 3, "max_run": 2, "value_like": false }
  ],
  "motion_coherence": {
    "frames": 5, "region_norm": [[127, 196, 905, 635]], "region_px": [497, 175],
    "animated_px": 10267, "animated_frac": 0.118,
    "mean_lag1_autocorr": 0.0265, "median_lag1_autocorr": -0.3333,
    "mean_lag1_autocorr_binary": 0.0237, "n_series": 7717,
    "verdict": "ambiguous",
    "reading": "autocorrelation near zero — cannot separate erratic from eased motion at this frame count"
  }
}
```

Honest behavior: the dropout reel's `'LIVE'` badge departs frames 3–5 —
a *departure*, which needs ≥2 consecutive absences and therefore cannot
strobe; nothing does. `'bar'`/`'logo'` object labels blink on frames
3,5 (Mirage churn — max_run 2) and are reported as `alternating_elements`,
not strobes. Motion coherence lands **ambiguous** (+0.0265, inside the
±0.10 deadband) — the detector declines to characterize rather than
guess.

## Extra probe — `detectors/lifecycle-diff/control-clean`

A *different* healthy scene (Site Traffic card: ticking visitor count,
random-walk bar updates, pulsing dot, LIVE badge present all frames) —
built to be lifecycle-diff's clean control, reused here as a
cross-scene generalization check:

```json
{
  "verdict": "no_strobe",
  "strobes": [], "alternating_elements": [],
  "motion_coherence": {
    "mean_lag1_autocorr": -0.1583, "median_lag1_autocorr": -0.3333,
    "mean_lag1_autocorr_binary": -0.1662,
    "verdict": "uncorrelated_motion"
  }
}
```

Strobe half: clean, as expected (badge present all 5 frames). Motion
half: **this is the honest-limit finding.** The healthy reel reads
`uncorrelated_motion` (−0.1583). Spatial breakdown shows the signal is
spread across the count digits (−0.21), the bar chart (−0.14), and the
badge/pulse area (−0.52): a per-frame ticking counter and
random-walk data bars are *genuinely* unpredictable at pixel level —
discrete updates are not eased animation. The metric is telling the
truth about temporal predictability; it just cannot distinguish
"unseeded random animation" (the defect) from "legitimate discrete data
updates" (a dashboard counter). The defect's −0.5631 is far more
extreme than this reel's −0.1583, but the ±0.10 band flags both.

## Verdicts

- **Strobe/flicker detector: CAUGHT.** Fires `'LIVE' (ocr) present
  [1,3,5] absent [2,4,6]`, confidence high, on the defect reel — the
  exact named fact the eval asked for, from data `reel --json` already
  ships. Silent (`no_strobe`/`alternating_only`) on control-smooth,
  frozen-frames, object-dropout, and an unrelated healthy reel. Strict
  alternation excludes singleton OCR garbage and dwell-based content by
  construction; the OCR-split guard covers the one record-artifact path
  to a false strobe. Limits: needs ≥4 frames for 3 transitions (5-frame
  reels can show at most 3); only *strict* whole-sequence alternation is
  named — duty-cycle flicker and blink-then-vanish are reported as
  `alternating_elements`, not `strobes`; presence masks are only as good
  as Mirage's per-frame OCR (a flicker faster than the record cadence,
  or one Mirage reads identically every frame, is invisible).
- **Motion coherence: PARTIAL.** It *does* reliably separate the
  assigned pair — chaotic-motion defect −0.5631 vs control-smooth
  +0.3803, a 0.94 gap robust across variance thresholds (0.5–16), a
  binary-occupancy variant (−0.5612/+0.3803), and native-vs-downscaled
  canvases — and it correctly refuses to characterize object-dropout
  (ambiguous, +0.0265). But it is a **motion-coherence
  characterization, not a chaos detector**: the healthy Site-Traffic
  control also reads uncorrelated (−0.1583) because ticking counters
  and random-walk data are pixel-level unpredictable too. Ship it as a
  fact ("animated pixels here are temporally unpredictable"), never as
  "this UI has a randomness bug" — the number is real, the attribution
  is not. n=6 frames means 5 lag-1 pairs per pixel; the eval itself
  says ≥10 wanted — treat all readings as directional until longer
  reels exist. Luminance-only: hue swaps at constant luminance are
  invisible to the channel.
