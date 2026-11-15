# VERDICT: lexical-screen — CAUGHT (assigned gap), control stays below threshold

Detector: `detectors/lexical-screen/lexical_screen.py` — standalone, PEP 723
(`uv run` resolves wordfreq itself; `/usr/share/dict/*` unioned in when
present), zero model calls, consumes `eyes describe` text records
(`string`/`bbox`/`score`) via subprocess or a saved `.json` record.

## Gap filled

From `evals/ocr-hostile/VERDICT.md` instrument-gap #1 and "what would
catch this" #1+#2: hostile type styling makes Mirage OCR emit
**non-words** ('delvered wechly', 'bouguets', 'NE WSPRINGCOLLECTIoN')
that `score_text` forgives at 0.83 via best-match SequenceMatcher, and
the eyebrow's three overlapping records are an unharvested geometric
signature. This detector ships both, deterministic:

1. **Lexical-validity screen** — every alphabetic token ≥3 chars in
   each `text[].string` is checked against a 263k-word lexicon
   (wordfreq en top-60k ∪ /usr/share/dict/*). Before declaring
   out-of-vocabulary, two rescue passes fire: camelCase splitting
   ('ShopJournal'→shop+journal, 'hopJournalAbout'→hop+journal+about)
   and regular inflection stripping ('couriered'→courier+ed,
   'bouquets'→bouquet+s, 'wrapped'→wrap+ped→wrap). Inflection stems
   must additionally clear a wordfreq zipf ≥2.5 floor when wordfreq is
   loaded — 'delver' is a real word (zipf 1.48) but too rare to
   legitimize 'delvered'; 'courier' (3.68) and 'bouquet' (3.41) pass.
   String verdicts: `non_lexical_text` when ≥50% of scored tokens are
   OOV (the eval's "most tokens fail" rule), `contains_out_of_vocabulary`
   below that (names the token, doesn't overclaim).

2. **OCR-fragmentation** (the eval's runner-up sketch) — text bboxes
   cluster into line bands by vertical overlap ≥50% of the *max* record
   height (max, not min: the tall script wordmark must not be absorbed
   into the short nav band's cluster); a band with ≥2 records whose
   x-ranges overlap ≥50% of the smaller width is `ocr_line_fragmented`.

**Why dictionary OOV, not char n-grams** — prototyped and rejected with
numbers: mean-bigram logp gives real word 'bouquets' **−6.82**, *worse*
than hostile 'bouguets' **−6.30** ('weekly' −6.85, 'queue' −6.64 vs
'delvered' −5.18, 'easonal' −5.00 — near-median). Rare-letter words and
one-glyph OCR errors are indistinguishable to letter statistics.
Wordhood is a lexicon question.

## Real output — defect + control + out-of-domain

```
$ uv run detectors/lexical-screen/lexical_screen.py \
    evals/ocr-hostile/defect.png evals/ocr-hostile/control.png \
    evals/text-truncation/defect.png evals/text-truncation/control.png

lexicon: 263445 words from wordfreq:en-top60k, dict:words

evals/ocr-hostile/defect.png  records=14  non_lexical=2  oov_strings=4  frag_bands=2
    clean                        oov=0.0   'ShopJournal'
        ShopJournal             = Shop+Journal
    clean                        oov=0.0   'hopJournalAbout Cart ('
        hopJournalAbout         = hop+Journal+About
  !! non_lexical_text             oov=1.0   'NE WSPRINGCOLLECTIoN'
        NE                      (<3 chars)
        WSPRINGCOLLECTIoN       *** OOV ***
  ! contains_out_of_vocabulary   oov=0.333 'Hand tied bouguets,'
        bouguets                *** OOV ***
  !! non_lexical_text             oov=1.0   'delvered wechly'
        delvered                *** OOV ***
        wechly                  *** OOV ***
  ! contains_out_of_vocabulary   oov=0.111 'easonal stems, wrapped by hand and couriered the same day'
        easonal                 *** OOV ***
        by                      (<3 chars)
        couriered               -> courier -ed
    clean                        oov=0.0   'Portland, ORest. 2019 - Open Tue-Sun ·- Same-day until 2pm'
        ORest                   = O+Rest [unresolved: O]
        pm                      (<3 chars)
  ## ocr_line_fragmented y=[50, 88] n=5 x_overlap=0.854  encompassing='hopJournalAbout Cart ('
       hopJournalAbout Cart ( | ShopJournal | About Cart (O | Journal | Shop
  ## ocr_line_fragmented y=[329, 362] n=3 x_overlap=0.859  encompassing='NE WSPRINGCOLLECTIoN'
       NE WSPRINGCOLLECTIoN | NE W | SPRING
  VERDICT: NON_LEXICAL_TEXT_DETECTED

evals/ocr-hostile/control.png  records=12  non_lexical=0  oov_strings=2  frag_bands=1
    clean                        oov=0.0   'ShopJournal'
        ShopJournal             = Shop+Journal
    clean                        oov=0.0   'nopJournalAbout Cart'
        nopJournalAbout         = nop+Journal+About [unresolved: nop]
  ! contains_out_of_vocabulary   oov=0.111 'easonal stems, wrapped by hand and couriered the same day'
        easonal                 *** OOV ***
        by                      (<3 chars)
        couriered               -> courier -ed
  ! contains_out_of_vocabulary   oov=0.25  'Poriland, ORest. 2019 - Open Tue-Sun · Same-day untl 2pm'
        Poriland                *** OOV ***
        ORest                   = O+Rest [unresolved: O]
        untl                    *** OOV ***
        pm                      (<3 chars)
  ## ocr_line_fragmented y=[43, 89] n=6 x_overlap=0.845  encompassing='nopJournalAbout Cart'
       Bloom & Stem | ShopJournal | nopJournalAbout Cart | About Cart ( | Journal | Shop
  VERDICT: OUT_OF_VOCABULARY_TOKENS

evals/text-truncation/defect.png  records=13  non_lexical=0  oov_strings=0  frag_bands=1
  ## ocr_line_fragmented y=[304, 343] n=2 x_overlap=0.98  encompassing='Q3 financial summary - updated 2h ago'
       3 financial summary - updated 2h ago | Q3 financial summary - updated 2h ago
  VERDICT: CLEAN

evals/text-truncation/control.png  records=13  non_lexical=0  oov_strings=2  frag_bands=1
  ! contains_out_of_vocabulary   oov=0.25  'Quarterly Revenue Overview Repor'
        Repor                   *** OOV ***
  ! contains_out_of_vocabulary   oov=0.25  'nancial summary - updated 2h ago'
        nancial                 *** OOV ***
        h                       (<3 chars)
  ## ocr_line_fragmented y=[305, 343] n=2 x_overlap=0.871  encompassing='Q3 financial summary - updated 2h ago'
       nancial summary - updated 2h ago | Q3 financial summary - updated 2h ago
  VERDICT: OUT_OF_VOCABULARY_TOKENS
```

`--json` emits per-token status, per-string oov_fraction, band
membership, and the lexicon provenance block; `--fail-on-non-lexical`
exits 1 on `non_lexical_text_detected` (verified: defect→1, control→0).

## What the detector actually caught

- **'delvered wechly' → `non_lexical_text`, oov=1.0** — both tokens OOV.
  'delvered' needed the zipf floor: morphologically it parses as
  delver+ed ('delver' is a real word) but zipf 1.48 rejects the stem.
- **'NE WSPRINGCOLLECTIoN' → `non_lexical_text`, oov=1.0** — the fused
  mega-token is not a word; camel splitting cannot rescue it (parts
  'WSPRINGCOLLECT'/'Io'/'N' don't resolve; single chars earn no credit).
- **'bouguets' named** inside 'Hand tied bouguets,' (`contains_oov`,
  1/3 tokens) — the token-level finding names the exact hostile word
  without overclaiming the string.
- **Eyebrow fragmentation band y=[329,362]** — the eval's three nested
  records ('NE W' / 'SPRING' / mega-read) as one `ocr_line_fragmented`
  finding with `encompassing_record` naming the fused read. Control
  has **no** band there (single clean record) — frag_bands 2 vs 1.

## Honest limits — what it does NOT do

- **OOV ≠ hostile.** Clean-but-lossy OCR emits non-words too, and the
  detector names them as facts: 'easonal' (clipped 'S' — a Mirage quirk
  present in *both* images), 'Poriland'/'untl' (footer clipping, control
  only), 'Repor'/'nancial' (text-truncation control). None reach the
  ≥50% string threshold, so no `non_lexical_text` fires — but the token
  list is not clean on controls and shouldn't be read as such.
- **Nav fragmentation fires on both images.** Mirage's overlapping nav
  reads ('Shop'/'ShopJournal'/'Journal'/…) produce an
  `ocr_line_fragmented` band in defect *and* control (and the
  text-truncation duplicate 'Q3 financial…'/'3 financial…' reads do the
  same). The discriminating signal is the defect-only *content-region*
  eyebrow band; the detector reports bands as facts and does not claim
  nav=defect.
- **Word-fusions are invisible to it.** 'hopJournalAbout' and
  'nopJournalAbout' are sequences of real words fused by OCR — rescued
  as `merged`/`merged_partial`, correctly *not* flagged (they are not
  non-words; the merge is a different defect class).
- **FP surface is real**: brand names, jargon, non-English text, and
  any lone display-font token produce OOV findings; a single-token
  string that's one unknown word reads `non_lexical_text` at oov=1.0.
  English-only lexicon; `merged_partial` can launder a mostly-real
  fusion ('nop' unresolved but forgiven at 2/3 known parts).
- **Dict-only degradation**: without wordfreq (plain `python3`, no
  `/usr/share/dict`), inflection stems lose the zipf floor —
  'delvered'→delver+ed is then rescued and 'delvered wechly' flags at
  exactly oov=0.5 (still fires, via 'wechly'). 'Portland' also drops to
  OOV. Verified via `uv run --no-project`: verdicts unchanged on all
  four cases, precision lower.
- **Mirage nondeterminism is inherited**: the detector screens whatever
  `eyes describe` emits; a luckier OCR pass ('delivered weekly' on the
  defect) would produce no findings — it detects the *symptom*, not the
  typeface.

## Verdict

**CAUGHT.** The detector flips the eval's named gap on the lexical axis:
`non_lexical_text` fires on exactly the hostile strings the eval
enumerated ('delvered wechly', 'NE WSPRINGCOLLECTIoN' — plus 'bouguets'
named at token level), the control produces zero `non_lexical_text`
strings and no eyebrow band, and the out-of-domain text-truncation pair
shows honest symmetric noise rather than a clean sweep. Instrument-alone
on this axis now has a deterministic, model-free screen where the eval
recorded only SequenceMatcher forgiveness. The remaining gap the eval
named — *why* the type is hostile (font concept, two-pass OCR
disagreement) — is untouched; this detector answers "the OCR output
isn't words," which is the fact layer, not the cause layer.
