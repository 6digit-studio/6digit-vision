# VERDICT: ocr-hostile — PARTIAL (instrument-alone) / CAUGHT (instrument+reasoning)

## Defect planted

`defect.png` / `control.png` (920×640) — a "Bloom & Stem" flower-shop
landing hero. Identical layout, palette, copy, and geometry; the only
difference is **type treatment**:

- **defect**: wordmark "Bloom & Stem" in Savoye LET calligraphic script;
  eyebrow "NEW · SPRING · COLLECTION" in Arial Bold with 7px manual
  letter-spacing; hero headline "Hand-tied bouquets, / delivered weekly"
  in Snell Roundhand script.
- **control**: every string in clean Arial/Arial Bold, normal tracking;
  headline sizes auto-fit to the defect's rendered widths.

This is the canonical agent-shipped instance of the class: a designer
asks for "elegant" or "boutique" and the model reaches for a script
display face + tracked caps — content perfect, recognition hostile.
`make_images.py` (PIL + system TTFs) regenerates both. Hero ink bboxes
verified identical: x[224,695] y[217,502] both images; 19,480 px
(3.3%) differ, confined to nav/eyebrow/headline bands.

Distinct from `low-contrast` (glyph-vs-background luminance ratio —
here contrast is 4.14:1, comfortably readable) and `text-truncation`
(content cut mid-glyph — here every glyph is whole; the *letterforms*
are the problem).

## What eyes reported

### `eyes describe defect.png --stats` — text records (abridged)

```json
{"string": "Bloom & Stem", "score": 0.451}
{"string": "ShopJournal", "score": 0.345}          // nav merged
{"string": "hopJournalAbout Cart (", "score": 0.344}
{"string": "NE W", "score": 0.31}                  // eyebrow fragments
{"string": "SPRING", "score": 0.329}               //  into 3 records
{"string": "NE WSPRINGCOLLECTIoN", "score": 0.676} // one line, 3 reads
{"string": "Hand tied bouguets,", "score": 0.552}  // missing 'q'
{"string": "delvered wechly", "score": 0.502}      // headline mangled
{"string": "easonal stems, wrapped by hand ...", "score": 0.714}
{"string": "Shop the collection", "score": 0.697}
```

### `eyes describe control.png --stats` — same strings, clean type

```json
{"string": "Bloom & Stem", "score": 0.816}
{"string": "NEW - SPRING- cOLLECTION", "score": 0.773}   // one record
{"string": "Hand-tied bouquets.", "score": 0.73}
{"string": "delivered weekly", "score": 0.554}
```

The hostile type did exactly what the class predicts: the letterspaced
eyebrow **fragmented into three overlapping OCR records** ('NE W' /
'SPRING' / 'NE WSPRINGCOLLECTIoN' — nested bboxes on one y-band), and
the script headline degraded to non-words ('delvered wechly',
'bouguets'). Note 'Bloom & Stem' still OCR'd *correctly* (score_text
best-match 1.000) despite confidence collapsing 0.816→0.451 — hostile
type hurt confidence more than content on the wordmark.

### `eyes layout defect.png --describe` — legibility flags

```
'Bloom & Stem'                 contrast 4.14  ocr 0.451  low_ocr_confidence
'NE W'                         contrast 2.30  ocr 0.310  low_contrast + low_ocr_confidence
'SPRING'                       contrast 2.30  ocr 0.329  low_contrast + low_ocr_confidence
'Hand tied bouguets,'          contrast 4.14  ocr 0.552  low_ocr_confidence
'delvered wechly'              contrast 4.14  ocr 0.502  low_ocr_confidence
+ 8 more (nav/footer/muted text)
```

### `eyes layout control.png --describe` — same detector, clean type

```
'Shop' / 'ShopJournal' / 'nopJournalAbout Cart'  low_ocr_confidence (0.32-0.55)
'delivered weekly'            contrast 4.14  ocr 0.554  low_ocr_confidence
'NEW - SPRING- cOLLECTION'    contrast 2.30  ocr 0.773  low_contrast only
```

Defect-only low_ocr flags: **'Bloom & Stem' (0.451), 'NE W' (0.310),
'SPRING' (0.329), 'Hand tied bouguets,' (0.552)** — the hostile regions.
But 'delvered wechly' is not cleanly attributable (control's
'delivered weekly' also flags at 0.554), and `low_contrast` noise
saturates both lists — my muted `#7a6e60` secondary text sits at
~2.1–2.4:1 and flags in *both* images (mock noise, disclosed, same
class of noise theme-drift recorded).

### `eyes score control.png defect.png`

```
score: 72.5 / 100
  palette   91.7  {}
  objects   52.2  {'matched': 6, 'missing': ['text' x5, 'webpage'],
                  'extra': ['text' x5]}
  layout    47.9  {'mean_center_dist': 0.1823, 'pairs': 6}
  text      95.6  {}
  scene    100.0  {}
```

A loud 72.5 — but the two biggest drops are **misattributed**: objects
52.2 is Mirage label churn (defect objects named `text`, control named
`webpage`/`button`), layout 47.9 is bbox-center noise from differently
shaped text regions. The component that should carry this defect —
`text` — reads **95.6**. Per-string best matches show why:

```
0.828  'delivered weekly'      -> 'delvered wechly'
0.857  'Hand-tied bouquets.'   -> 'handtiedbouguets,'
0.950  'NEW - SPRING- cOLLECT.' -> 'newspringcollection'  (fragment merge)
1.000  everything else (including 'easonal stems' — same leading-'S'
       drop in BOTH images, a Mirage quirk unrelated to type)
```

`score_text` is mean-of-best-matches with **no penalty for candidate-
extra strings**: the defect's three eyebrow fragments are free. And
SequenceMatcher forgives exactly the errors hostile type produces —
'delvered wechly' is not a word but scores 0.83 against 'delivered
weekly'.

### `eyes ask defect.png -q "What text is in this image? Is any of it
unreadable or mangled?"`

The pack contains the mangled strings **verbatim** plus all 13
legibility-flagged entries. `detectors` (status_icons, hue_census)
correctly report nothing — 0 icon candidates, single orange accent
family identical to control.

## Verdicts

- **Instrument alone (describe + layout + score): PARTIAL.** The
  legibility layer does enumerate the hostile strings with
  `low_ocr_confidence` — real, citable facts on exactly the right
  regions — but the flag cannot say *why* (hostile typeface vs small
  text vs blur all produce it), fires on the clean control too, and is
  drowned in `low_contrast` noise. `score` fires loud (72.5) while
  attributing the difference to object/layout noise and scoring the
  actual defect axis at 95.6.
- **Instrument + reasoning layer: CAUGHT.** The ask pack hands the
  court 'delvered wechly', 'NE WSPRINGCOLLECTIoN' + two sibling
  fragments, 'bouguets' — non-words a text model rejects on sight, and
  the control pack shows the same regions reading clean. The question
  "is any of it unreadable or mangled" is answered yes with citations.
  This is the PRD split working: facts out, judgment decides.

## Instrument gaps this case exposes

1. **`score_text` forgives hostile-type errors and ignores extras.**
   Best-match SequenceMatcher treats 'delvered wechly'≈'delivered
   weekly' at 0.83; candidate-only strings ('NE W', 'SPRING') cost
   nothing. The text component needs (a) per-string worst-match detail,
   (b) a penalty for unmatched candidate strings, and/or (c) a
   lexical-validity signal — OCR output that isn't words is a different
   failure class than OCR output that's wrong-but-wordlike.
2. **No typeface/recognition-hostility concept.** Nothing in the stack
   knows fonts exist. `low_ocr_confidence` is the only surface and it
   conflates every OCR degradation cause. A `recognition_hostile`
   signal needs either a second OCR pass under different preprocessing
   (disagreement = appearance problem, not content problem) or a
   font-agnostic readability proxy.
3. **OCR fragmentation is an unharvested signature.** One visual line
   producing 3 overlapping records ('NE W'/'SPRING'/'NE WSPRINGCOLLECTIoN',
   nested bboxes, same y-band) is characteristic of letterspaced/
   decorative type — pure geometry on data already collected, currently
   discarded.
4. **Confidence deltas vs control are unexploited.** 'Bloom & Stem'
   0.816→0.451, eyebrow 0.773→fragments at 0.31–0.68: per-region OCR-
   score drops isolate hostile regions from global OCR noise. The
   records carry both sides; nothing diffs them.
5. **Flag noise floor.** `low_contrast` fired on ~2.1:1 muted text in
   BOTH images (mock's own secondary color) — 13 flags on defect vs 9
   on control, only ~4 attributable. On real captures with proper
   muted tokens this dilutes less, but the flag list needs ranking or
   attribution to stay readable.

## What would catch this

Concrete instrumentation, cheapest first:

1. **Lexical-validity screen on OCR strings (deterministic, ~30
   lines).** Tokenize each `text[].string`; flag strings whose tokens
   are all/mostly out-of-vocabulary for the record's language
   (wordfreq top-50k or `/usr/share/dict` fallback). 'delvered wechly',
   'bouguets', 'NE WSPRINGCOLLECTIoN' all fail; every clean-control
   string passes ('easonal' clipped-S is a borderline miss — acceptable,
   facts-not-verdicts). Emits `non_lexical_text` findings naming the
   exact hostile regions. False-positive surface: brand names, jargon,
   non-English — mitigated by only flagging when *most* tokens in a
   multi-word string fail.
2. **OCR-fragmentation detector (geometry, no model).** Cluster text
   bboxes by y-overlap; when ≥2 records share a line band and at least
   one bbox substantially overlaps another's x-range, emit
   `ocr_line_fragmented`. The eyebrow's three nested records are the
   signature — letterspaced caps and script display type fragment reads
   exactly this way; clean type produces one record per line.
3. **Per-string confidence delta in `score` (data already collected).**
   `score_text` currently returns only the mean. Emit worst-match pair
   + count of candidate-extra strings: `{worst: ('delivered weekly' →
   'delvered wechly', 0.83), extra_strings: ['NE W','SPRING',
   'NE WSPRINGCOLLECTIoN']}`. The extras penalty alone drops text
   meaningfully here — three unpunished defect strings is the
   instrument's own blind spot made visible.
4. **Two-pass OCR disagreement probe.** Re-run recognition on each
   flagged text bbox after 2× upscale + binarization; strings whose
   reads *change* across preprocessings are appearance-hostile (the
   pixels, not the content, are the problem). Disagreement localizes
   the defect to specific regions — 'delvered wechly' likely stabilizes
   or worsens differently than 'delivered weekly' would. Costs one
   extra OCR call per flagged region, only where `low_ocr_confidence`
   already fired.
5. **Type-agnostic ask-pack enrichment (cheap partial).** Include text
   bboxes in the pack (currently stripped to string+score). With
   geometry, the reasoning layer could at least correlate flags with
   regions; with a crop path it could re-read the hostile type itself —
   the same "give the consumer the geometry perception lacked" fix
   semantic-surprise already queued.

## Verdict

**PARTIAL.** The defect is real, typical (script display face +
tracked-caps eyebrow is what "make it elegant" produces), and
demonstrably exhibited — Mirage itself produced the mangled reads.
Instrument-alone, the legibility flags name the hostile strings but
cannot name the cause, and `score`'s loud 72.5 misattributes to
object/layout noise while `text` — the true axis — forgives the
mangling at 95.6. Instrument+reasoning is a clean CAUGHT: the pack
contains non-word OCR output a text model rejects instantly, with the
control pack proving the same regions read clean. This entry exists to
be fixed against: a lexical-validity screen or OCR-fragmentation
detector should flip instrument-alone to CAUGHT without any model call.

## Re-run 2026-11-15 (integrated instrument) — CAUGHT (detector-backed)

`detectors/lexical-screen` is now wired into `eyes ask` packs.
Defect pack reports 2 `non_lexical_text` flags ('delvered wechly',
'NE WSPRINGCOLLECTIoN') plus OOV tokens — the hostile regions are
named without a reasoning call. Instrument-alone PARTIAL -> CAUGHT.
