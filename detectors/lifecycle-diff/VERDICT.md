# VERDICT: lifecycle-diff — CAUGHT

Detector for the gap named by `evals/object-dropout/VERDICT.md`:
**entity-lifecycle diffing**. `eyes reel` emits per-pair facts but never
computes element lifecycles — the dropout evidence ("live" in
`ocr.unmatched` once, "LIVE" absent from frames 3–5 `text`, "red
circle" gone from `objects`) was all in the JSON but required manual
cross-referencing. This detector diffs per-frame object-name sets and
OCR strings across `frames_detail` and emits named facts:
`element X present frames a–b, absent c–d`. Zero new model calls —
consumes `frames_detail` + `pairs` only.

## Files

- `lifecycle_diff.py` — the detector. Accepts a saved
  `eyes reel --json` file, or `--reel <inputs...>` to run
  `eyes reel <inputs> --json` itself. Flags: `--min-present`,
  `--min-absent` (defaults 2/2 per the eval's sketch).
- `make_control.py` + `control-clean/` — clean control: the eval's own
  `build_frames.py` re-run with the LIVE badge present in **all** five
  frames (same ticking count, same moving bars, same pulse). Nothing
  persistent ever departs.

## Rule

For every OCR string and object label, compute the presence bitmask
across frames (normalized: lowercase, whitespace-collapsed). A
**departure** is a presence run of ≥ `min_present` consecutive frames
followed by an absence run of ≥ `min_absent` consecutive frames.
Churning values (the visitor count `12,847`→`13,102`, each a distinct
one-frame string) never hold a 2-frame run and are excluded for free.
Departures are grouped by boundary and classified:

- **dropout** (high): ≥1 OCR element AND ≥1 object element depart at the
  same boundary — cross-channel corroboration, one physical element seen
  by two record channels.
- **coordinated_departure** (low): ≥2 same-channel elements depart
  together — consistent with a content update, not an isolated loss.
- **solo_departure**: one element, no corroboration. Medium confidence
  only if absent-to-end, non-returning, non-value-like; else low.

Each event carries the transition pair's `labels`/`ocr`/`changed_pct`,
post-departure max pixel change (`siblings_animating`), and honesty
notes: `returned` (transient absence ≈ record miss), `value_like`
(digit-bearing churn class), presence runs spanning `static` pairs
(persistence may be a frozen duplicate), and static sequence tails.

## Defect run — `evals/object-dropout`

```
$ uv run python detectors/lifecycle-diff/lifecycle_diff.py --reel evals/object-dropout
```

```json
{
  "verdict": "dropout_detected",
  "summary": "2 corroborated element dropout(s): 'LIVE' (ocr) present 1-2, absent 3-5; 'red circle' (objects) present 1-2, absent 3-5. Text + object channels agree on the same boundary.",
  "params": { "min_present_frames": 2, "min_absent_frames": 2 },
  "stats": { "tracked": { "text": 13, "objects": 5 }, "frames": 5 },
  "departures": [
    {
      "element": "LIVE", "channel": "ocr",
      "present_frames": "1-2", "absent_frames": "3-5",
      "absent_to_end": true, "returned": false, "value_like": false,
      "transition_pair": ["frame_02.png", "frame_03.png"],
      "labels_score": 0.4, "ocr_score": 0.7778, "changed_pct": 0.0262,
      "post_departure_max_changed_pct": 0.0188, "siblings_animating": true,
      "kind": "dropout", "confidence": "high",
      "corroborated_with": ["red circle"],
      "notes": [
        "cross-channel corroboration: text + object depart at the same boundary — one physical element seen by two record channels",
        "absent through end of sequence"
      ]
    },
    {
      "element": "red circle", "channel": "objects",
      "present_frames": "1-2", "absent_frames": "3-5",
      "absent_to_end": true, "returned": false, "value_like": false,
      "transition_pair": ["frame_02.png", "frame_03.png"],
      "labels_score": 0.4, "ocr_score": 0.7778, "changed_pct": 0.0262,
      "post_departure_max_changed_pct": 0.0188, "siblings_animating": true,
      "kind": "dropout", "confidence": "high",
      "corroborated_with": ["LIVE"],
      "notes": [
        "cross-channel corroboration: text + object depart at the same boundary — one physical element seen by two record channels",
        "absent through end of sequence"
      ]
    }
  ],
  "arrivals": [],
  "source": "evals/object-dropout"
}
```

This is exactly the named fact the eval asked for — "'LIVE' present
frames 1–2, absent 3–5" / "'red circle' present 1–2, absent 3–5" —
emitted as structured output, with `siblings_animating: true` (post-
departure max `changed_pct` 0.0188) capturing the "everything else keeps
animating" clause, and the transition pair's `labels 0.40` / `ocr 0.78`
(the reel minimums) attached as context.

## Control 1 — `evals/frozen-frames` (has churn + a frozen frame, NO dropout)

```
$ uv run python detectors/lifecycle-diff/lifecycle_diff.py --reel evals/frozen-frames
```

```json
{
  "verdict": "departures_only",
  "summary": "2 persistent element(s) departed but none with cross-channel corroboration — consistent with content updates/churn, not an isolated dropout. See departures for the facts.",
  "stats": { "tracked": { "text": 15, "objects": 5 }, "frames": 5 },
  "departures": [
    {
      "element": "45%", "channel": "ocr",
      "present_frames": "2-3", "absent_frames": "4-5",
      "absent_to_end": true, "returned": false, "value_like": true,
      "transition_pair": ["frame_03.png", "frame_04.png"],
      "labels_score": 0.75, "ocr_score": 0.8, "changed_pct": 0.0148,
      "post_departure_max_changed_pct": 0.0129, "siblings_animating": true,
      "kind": "coordinated_departure", "confidence": "low",
      "notes": [
        "2 elements departed at this boundary — consistent with a content update, not an isolated loss",
        "presence run spans static pair(s) [['frame_02.png', 'frame_03.png']] — persistence may be a frozen/duplicated frame, not stable rendering",
        "absent through end of sequence",
        "digit-bearing value — churn-prone class"
      ]
    },
    {
      "element": "Copying flles...", "channel": "ocr",
      "present_frames": "2-3", "absent_frames": "4-5",
      "absent_to_end": true, "returned": false, "value_like": false,
      "transition_pair": ["frame_03.png", "frame_04.png"],
      "labels_score": 0.75, "ocr_score": 0.8, "changed_pct": 0.0148,
      "post_departure_max_changed_pct": 0.0129, "siblings_animating": true,
      "kind": "coordinated_departure", "confidence": "low",
      "notes": [
        "2 elements departed at this boundary — consistent with a content update, not an isolated loss",
        "presence run spans static pair(s) [['frame_02.png', 'frame_03.png']] — persistence may be a frozen/duplicated frame, not stable rendering",
        "absent through end of sequence"
      ]
    }
  ],
  "arrivals": [],
  "source": "evals/frozen-frames"
}
```

This is the honest-hard case, and it behaved correctly. The frozen
frame_03 is a byte-copy of frame_02, so the status line "45%" +
"Copying fflies..." held a 2-frame run and then departed — a naive
≥2-frame rule **would** false-positive here. The detector does not
claim a dropout: both events are `coordinated_departure` / `low`, and
the notes name *why* — they left together (status-line advance), their
"persistence" spans the static frozen pair, and "45%" is a
churn-prone value. The lifecycle facts themselves are true (those
strings did persist 2–3, absent 4–5); the classification says "content
update, not isolated loss." Verdict `departures_only`, not
`dropout_detected`.

## Control 2 — `control-clean/` (badge persists all 5 frames)

```
$ uv run python detectors/lifecycle-diff/make_control.py
$ uv run python detectors/lifecycle-diff/lifecycle_diff.py --reel detectors/lifecycle-diff/control-clean
```

```json
{
  "verdict": "clean",
  "summary": "No persistent element departed: every OCR string and object label that held a >=2-frame run either persists to the end or never left for >=2 consecutive frames.",
  "params": { "min_present_frames": 2, "min_absent_frames": 2 },
  "stats": { "tracked": { "text": 13, "objects": 3 }, "frames": 5 },
  "departures": [],
  "arrivals": [],
  "source": "detectors/lifecycle-diff/control-clean"
}
```

Full silence on a healthy animating sequence — "LIVE" and "red circle"
persist all five frames, the ticking count churns one frame at a time,
and nothing qualifies.

## Detector verdict: **CAUGHT**

Fires on the defect with the exact named fact the eval requested
(`'LIVE' present 1-2, absent 3-5` + `'red circle'` corroboration),
does not fire on either control, and on frozen-frames it reports true
lifecycle facts while explicitly declining to call them a dropout.

## Honest limits

1. **Record-layer only.** The detector sees what Mirage names. An
   element with no OCR text and no object label (a decorative glyph,
   a border artifact) can drop out invisibly — that is the
   erase-signature/pixel-diff sketch's job, not this one's.
2. **Corroboration needs both channels.** A dropout of an element
   Mirage only ever sees in ONE channel (e.g. OCR reads the label but
   no object is detected, or vice versa) yields `solo_departure` at
   medium/low confidence — still reported, weaker claim.
3. **Solo-departure false positives are possible.** A persistent OCR
   string Mirage misses for ≥2 consecutive frames and never recovers
   looks identical to a real solo dropout at this layer. Mitigations
   (returned→low, value_like tag, coordinated grouping, static-pair
   note) reduce but do not eliminate this; on a noisy reel a
   `solo_departure/medium` should be read as "suspect," not "proven."
4. **No spatial grounding.** `frames_detail` carries names and strings,
   not boxes — the detector says *what* vanished, not *where*. Pairing
   with `eyes describe`/layout output would localize it.
5. **Short reels can't fire.** Fewer than `min_present + min_absent`
   frames → the rule cannot trigger; output carries a `caveat` saying
   "clean" means "no evidence," not "verified clean."
6. **`--no-records` reels unsupported** → honest `no_record_data`
   verdict (verified: `eyes reel evals/object-dropout --no-records
   --json | lifecycle_diff.py` returns it).
7. **Departures that return** are flagged as likely record noise, but
   a genuinely blinking element is indistinguishable from an OCR miss
   here — lifecycle diffing reports the fact, judgment stays upstairs.
