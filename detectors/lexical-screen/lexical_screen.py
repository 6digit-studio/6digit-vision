# /// script
# requires-python = ">=3.11"
# dependencies = ["wordfreq"]
# ///
"""lexical-screen — OOV-token screen + OCR line-fragmentation detector.

Fills the gap named in evals/ocr-hostile/VERDICT.md: hostile type styling
makes Mirage OCR emit non-words ('delvered wechly', 'bouguets',
'NE WSPRINGCOLLECTIoN') while the clean control reads fine, and
`score_text` forgives them via best-match SequenceMatcher. Two
deterministic signals, zero model calls, on data `eyes describe`
already emits:

  1. lexical-validity screen — tokenize each text record's string;
     every alphabetic token >=3 chars is checked against a lexicon
     (wordfreq en top-60k union /usr/share/dict/* union). Rescue
     passes before declaring OOV: camelCase splits ('ShopJournal' ->
     shop+journal), regular inflections ('couriered' -> courier+ed,
     'bouquets' -> bouquet+s, 'stems' -> stem+s). A string whose
     scored tokens are >=50% out-of-vocabulary is `non_lexical_text`;
     a string with any OOV token below that fraction is
     `contains_out_of_vocabulary` (names the token, doesn't overclaim).

  2. OCR-fragmentation (runner-up from the same eval) — cluster text
     bboxes into line bands by vertical overlap; a band holding >=2
     records with substantially overlapping x-ranges is
     `ocr_line_fragmented` — the letterspaced/script signature. Pure
     geometry on bboxes already collected.

Why dictionary OOV and not char n-grams: prototyped and rejected —
real word 'bouquets' scores WORSE (-6.82 mean bigram logp) than
hostile 'bouguets' (-6.30); rare-letter words and one-glyph OCR errors
are indistinguishable to letter statistics. Wordhood is a lexicon
question, not a letter-plausibility question.

Honest limits (see VERDICT.md): brand names, jargon, and non-English
text produce OOV tokens — mitigated only by the >=50% string rule and
by reporting tokens as facts, not verdicts. OCR clipping produces
real-word fragments ('easonal', 'untl', 'poriland') that ARE
out-of-vocabulary and WILL be named; that is correct — they are not
words — but it means clean-but-lossy OCR also lights up the token
list. Inflection rescue assumes stems are words AND (when wordfreq is
loaded) stems clear a zipf floor — 'delvered'->'delver' is morphologically
valid but 'delver' sits at zipf 1.48, too rare to legitimize it; without
wordfreq the floor is absent and 'delvered' is rescued (the string still
flags via its other OOV token).

Usage (from repo root):
    uv run detectors/lexical-screen/lexical_screen.py evals/ocr-hostile/defect.png
    uv run detectors/lexical-screen/lexical_screen.py --json evals/ocr-hostile/*.png
    uv run detectors/lexical-screen/lexical_screen.py record.json   # saved `eyes describe` output
    uv run detectors/lexical-screen/lexical_screen.py --fail-on-non-lexical *.png

Exit code is 0 unless --fail-on-non-lexical is given and any image has
a `non_lexical_text` string.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------ tunables

MIN_TOKEN_LEN = 3        # alpha tokens shorter than this are exempt ('NE', 'W', 'pm')
NON_LEXICAL_FRAC = 0.5   # >= this fraction of scored tokens OOV -> non_lexical_text
CAMEL_MIN_PARTS = 2      # need at least this many camel parts to attempt merge rescue
MERGE_KNOWN_FRAC = 0.5   # >= this fraction of camel parts in lexicon -> 'merged' (not OOV)
BAND_Y_OVERLAP = 0.5     # vertical overlap / max(record heights) to share a line band
BAND_X_OVERLAP = 0.5     # horizontal overlap / min(record widths) -> fragmented pair
ZIPF_STEM_MIN = 2.5      # min wordfreq zipf for an inflection STEM to count
                         # ('delver' zipf 1.48 is a real word but too rare to
                         #  legitimize 'delvered'; 'courier' 3.68, 'bouquet'
                         #  3.41 pass). Only applied when wordfreq is loaded —
                         #  the dict-only path has no frequencies.

# suffix -> replacement, longest-first so 'ies' beats 's', 'ied' beats 'ed'.
# Each generates stem candidates; variants (undouble final consonant,
# restore silent 'e') are tried before giving up.
INFLECTIONS = [
    ("ies", "y"), ("ied", "y"),
    ("ing", ""), ("ed", ""),
    ("es", ""), ("s", ""),
    ("ly", ""), ("er", ""), ("est", ""),
    ("ment", ""), ("ness", ""), ("ity", ""),
    ("ful", ""), ("less", ""), ("able", ""),
]

TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*")
SPLIT_RE = re.compile(r"['’\-]")
# standard camelCase splitter: CAPS-run | Capitalized | lowercase | digits
CAMEL_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+|[0-9]+")
ALPHA_RE = re.compile(r"[A-Za-z]")

DICT_DIR = Path("/usr/share/dict")
DICT_FILES = ("words", "web2a", "web2", "propernames", "connectives")


# ------------------------------------------------------------------ lexicon

def load_lexicon() -> tuple[set[str], list[str], Callable[[str], float] | None]:
    """Union of available lexicons. Returns (words, sources, zipf_fn).

    zipf_fn(w) -> wordfreq zipf_frequency or None when wordfreq is absent
    (dict-only path: inflection stems are then accepted without a
    frequency floor — documented precision loss, see VERDICT.md).
    """
    lex: set[str] = set()
    sources: list[str] = []
    zipf_fn = None

    try:
        import wordfreq  # PEP 723 dep; absent under plain python3 -> dict path
        lex.update(w.lower() for w in wordfreq.top_n_list("en", 60000)
                   if w.isalpha())
        sources.append("wordfreq:en-top60k")
        zipf_fn = lambda w: wordfreq.zipf_frequency(w, "en")
    except Exception:
        pass

    for name in DICT_FILES:
        p = DICT_DIR / name
        if not p.exists():
            continue
        before = len(lex)
        for line in p.read_text(errors="ignore").splitlines():
            w = line.strip().lower()
            if w.isalpha():
                lex.add(w)
        if len(lex) > before:
            sources.append(f"dict:{name}")

    return lex, sources, zipf_fn


# ------------------------------------------------------------------ tokens

def atomic_tokens(text: str) -> list[str]:
    """Alpha tokens >=1 char; hyphen/aprophe compounds split into parts.

    'Hand-tied' -> ['Hand','tied']; \"don't\" -> ['don','t'];
    '$1.24M' -> ['M'] (len<3 -> exempt downstream); '2pm' -> ['pm'].
    """
    out: list[str] = []
    for chunk in TOKEN_RE.findall(text):
        out.extend(p for p in SPLIT_RE.split(chunk) if p)
    return out


def camel_parts(token: str) -> list[str] | None:
    """Split 'hopJournalAbout' -> ['hop','Journal','About'].

    Returns None when the token shows no case structure worth testing
    (all-lowercase or all-uppercase tokens have no internal boundary —
    'WSPRINGCOLLECTIoN' still yields parts but they won't resolve).
    """
    if not re.search(r"[a-z]", token) or not re.search(r"[A-Z]", token):
        return None
    parts = [p for p in CAMEL_RE.findall(token) if ALPHA_RE.search(p)]
    return parts if len(parts) >= CAMEL_MIN_PARTS else None


def _stem_variants(stem: str) -> list[str]:
    """Undouble a final consonant ('runn'->'run') and restore silent 'e'
    ('mak'->'make', 'updat'->'update')."""
    out = [stem]
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in "aeiou":
        out.append(stem[:-1])
    if not stem.endswith("e"):
        out.append(stem + "e")
    return out


def inflection_match(token: str, lex: set[str],
                     zipf_fn=None) -> tuple[str, str] | None:
    """Return (lexicon_form, rule) if token is a regular inflection.

    When zipf_fn is available the matched stem must clear
    ZIPF_STEM_MIN — 'delvered' -> 'delver' is morphologically valid but
    'delver' (zipf 1.48) is too rare to legitimize it, while 'couriered'
    -> 'courier' (3.68) passes. Without wordfreq there is no frequency
    signal and every stem in the lexicon is accepted."""
    low = token.lower()
    for suf, repl in INFLECTIONS:
        if not low.endswith(suf) or len(low) - len(suf) < 3:
            continue
        stem = low[: -len(suf)] + repl
        for var in _stem_variants(stem):
            if var in lex and (zipf_fn is None
                               or zipf_fn(var) >= ZIPF_STEM_MIN):
                return var, f"-{suf}" + ("+e" if var == stem + "e" and var != stem else "")
    return None


def classify_token(token: str, lex: set[str], zipf_fn=None) -> dict:
    """Classify one atomic alpha token. Statuses:

    known            — in lexicon directly
    inflected        — rescued by suffix strip to a lexicon stem
    merged           — camelCase parts all resolve (>= MERGE_KNOWN_FRAC known)
    merged_partial   — camelCase parts mostly resolve; unknown fragments noted
                       (counts as NOT oov — a merge artifact, not hostile type)
    out_of_vocabulary— no rescue fired; the token is not a word we know
    exempt           — shorter than MIN_TOKEN_LEN
    """
    if len(token) < MIN_TOKEN_LEN:
        return {"token": token, "status": "exempt", "reason": f"<{MIN_TOKEN_LEN} chars"}

    low = token.lower()
    if low in lex:
        return {"token": token, "status": "known"}

    parts = camel_parts(token)
    if parts:
        # only >=MIN_TOKEN_LEN parts earn "known" credit — single letters
        # and 2-char fragments ('Io', 'N', 'O') are not words for our
        # purposes and must not launder a fused mega-token into 'merged'
        known_parts = [p for p in parts
                       if len(p) >= MIN_TOKEN_LEN and p.lower() in lex]
        frac = len(known_parts) / len(parts)
        if frac >= MERGE_KNOWN_FRAC:
            unknown = [p for p in parts
                       if not (len(p) >= MIN_TOKEN_LEN and p.lower() in lex)]
            status = "merged" if not unknown else "merged_partial"
            return {"token": token, "status": status,
                    "parts": parts, "unknown_parts": unknown}
        # <half parts known: fall through — treat as a single OOV candidate

    m = inflection_match(token, lex, zipf_fn)
    if m:
        stem, rule = m
        return {"token": token, "status": "inflected",
                "stem": stem, "rule": rule}

    # prefix-noise gate: dense-UI glyphs (vote triangles, icons) OCR as
    # a single leading char glued to the real word ('AShow' <- 'A'+'Show').
    # If stripping one leading char yields a resolvable token, the OOV
    # is measurement noise, not hostile type. Hostile tokens survive:
    # 'delvered'->'elpered', 'bouguets'->'ouguets' don't resolve.
    if len(token) >= MIN_TOKEN_LEN + 1 and token[0].isupper():
        rest = token[1:]
        if len(rest) >= MIN_TOKEN_LEN and (
                rest.lower() in lex
                or inflection_match(rest, lex, zipf_fn)):
            return {"token": token, "status": "prefix_noise",
                    "stripped": rest}

    return {"token": token, "status": "out_of_vocabulary"}


# ------------------------------------------------------------------ strings

def screen_string(rec: dict, lex: set[str], zipf_fn=None) -> dict:
    """Lexical screen for one text record."""
    text = rec.get("string", "")
    atomic = atomic_tokens(text)
    tokens = [classify_token(t, lex, zipf_fn) for t in atomic]
    scored = [t for t in tokens if t["status"] != "exempt"]
    oov = [t for t in scored if t["status"] == "out_of_vocabulary"]

    frac = len(oov) / len(scored) if scored else 0.0
    if oov and frac >= NON_LEXICAL_FRAC:
        verdict = "non_lexical_text"
    elif oov:
        verdict = "contains_out_of_vocabulary"
    else:
        verdict = "clean"

    return {
        "string": text,
        "bbox": rec.get("bbox"),
        "ocr_score": rec.get("score"),
        "verdict": verdict,
        "oov_fraction": round(frac, 3),
        "tokens": tokens,
        "oov_tokens": [t["token"] for t in oov],
    }


# ------------------------------------------------------------------ fragmentation

def _y_overlap(a: list, b: list) -> float:
    """Vertical overlap of two [x0,y0,x1,y1] bboxes / MAX height.

    Max (not min) denominator: a tall record ('Bloom & Stem' script,
    h=82) that vertically swallows a short nav line (h=35) must NOT be
    merged into the nav's line band — 38px of overlap is 100% of the
    nav record but only 46% of the wordmark. Same-size fragments
    (eyebrow/nav reads, h~30-38) still overlap ~90%+ and cluster fine.
    """
    h = max(a[3] - a[1], b[3] - b[1])
    if h <= 0:
        return 0.0
    ov = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, ov) / h


def _x_overlap(a: list, b: list) -> float:
    w = min(a[2] - a[0], b[2] - b[0])
    if w <= 0:
        return 0.0
    ov = min(a[2], b[2]) - max(a[0], b[0])
    return max(0.0, ov) / w


def fragmented_bands(text_records: list[dict]) -> list[dict]:
    """Cluster text records into line bands; flag bands with overlapping reads.

    A band is a transitive cluster of records whose y-intervals overlap by
    >= BAND_Y_OVERLAP of the smaller record's height. Within a band of
    >=2 records, if any pair's x-ranges overlap by >= BAND_X_OVERLAP of
    the smaller width, the band is `ocr_line_fragmented` — the signature
    of letterspaced caps / script display type fragmenting one visual
    line into several overlapping OCR records.
    """
    recs = [(i, r) for i, r in enumerate(text_records)
            if isinstance(r.get("bbox"), list) and len(r["bbox"]) == 4]
    recs.sort(key=lambda ir: (ir[1]["bbox"][1], ir[1]["bbox"][0]))

    bands: list[list[int]] = []
    for idx, r in recs:
        placed = False
        for band in bands:
            # joins if it y-overlaps ANY current member enough
            if any(_y_overlap(r["bbox"], text_records[j]["bbox"]) >= BAND_Y_OVERLAP
                   for j in band):
                band.append(idx)
                placed = True
                break
        if not placed:
            bands.append([idx])

    findings = []
    for band in bands:
        if len(band) < 2:
            continue
        members = [text_records[j] for j in band]
        frag_pair = None
        for a_i in range(len(members)):
            for b_i in range(a_i + 1, len(members)):
                xa = _x_overlap(members[a_i]["bbox"], members[b_i]["bbox"])
                if xa >= BAND_X_OVERLAP:
                    frag_pair = (members[a_i].get("string", "?"),
                                 members[b_i].get("string", "?"),
                                 round(xa, 3))
                    break
            if frag_pair:
                break
        if not frag_pair:
            continue
        ys = [m["bbox"][1] for m in members] + [m["bbox"][3] for m in members]
        longest = max(members, key=lambda m: len(m.get("string", "")))
        findings.append({
            "kind": "ocr_line_fragmented",
            "y_band": [min(ys[0::2]), max(ys[1::2])],
            "n_records": len(members),
            "records": [{"string": m.get("string"), "bbox": m.get("bbox"),
                         "score": m.get("score")} for m in members],
            "x_overlap_example": frag_pair,
            "encompassing_record": (longest.get("string")
                                    if len(longest.get("string", "")) > 12
                                    else None),
        })
    return findings


# ------------------------------------------------------------------ record io

def run_eyes_describe(image: str) -> dict:
    """`eyes describe <image>` via PATH or `uv run eyes` (project env)."""
    eyes = shutil.which("eyes")
    if eyes:
        cmd = [eyes, "describe", image]
    elif shutil.which("uv"):
        cmd = ["uv", "run", "eyes", "describe", image]
    else:
        raise SystemExit("neither `eyes` nor `uv` on PATH")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"eyes describe failed: {proc.stderr.strip()[:400]}")
    return json.loads(proc.stdout)


def load_record(path: str) -> tuple[dict, str]:
    """Return (describe_record, source_label). .json -> saved record;
    anything else -> run eyes describe on it."""
    p = Path(path)
    if p.suffix == ".json" and p.exists():
        data = json.loads(p.read_text())
        # accept a bare record or {"record": {...}} / eyes reel frames_detail style
        if isinstance(data, dict) and "text" not in data:
            for key in ("record", "describe", "result"):
                if isinstance(data.get(key), dict) and "text" in data[key]:
                    data = data[key]
                    break
        return data, str(path)
    return run_eyes_describe(path), path


# ------------------------------------------------------------------ analyze

def analyze(path: str, lex: set[str], zipf_fn=None) -> dict:
    try:
        rec, source = load_record(path)
    except Exception as e:
        return {"image": path, "verdict": "error", "notes": [str(e)]}

    text_records = rec.get("text") or []
    strings = [screen_string(r, lex, zipf_fn) for r in text_records
               if isinstance(r, dict) and r.get("string")]
    bands = fragmented_bands(text_records)

    n_nonlex = sum(1 for s in strings if s["verdict"] == "non_lexical_text")
    n_oov = sum(1 for s in strings if s["oov_tokens"])
    if n_nonlex:
        verdict = "non_lexical_text_detected"
    elif n_oov:
        verdict = "out_of_vocabulary_tokens"
    else:
        verdict = "clean"

    return {
        "image": source,
        "verdict": verdict,
        "n_text_records": len(strings),
        "non_lexical_strings": n_nonlex,
        "strings_with_oov": n_oov,
        "fragmented_bands": len(bands),
        "strings": strings,
        "fragmentation": bands,
    }


# ------------------------------------------------------------------ output

def fmt_token(t: dict) -> str:
    st = t["status"]
    if st == "known":
        return ""
    if st == "exempt":
        return f"  ({t['reason']})"
    if st == "inflected":
        return f"  -> {t['stem']} {t['rule']}"
    if st == "merged":
        return f"  = {'+'.join(t['parts'])}"
    if st == "merged_partial":
        return (f"  = {'+'.join(t['parts'])} "
                f"[unresolved: {', '.join(t['unknown_parts'])}]")
    return "  *** OOV ***"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Lexical-validity screen on `eyes describe` text "
                    "records + OCR line-fragmentation detector. Flags OCR "
                    "strings whose tokens are out-of-vocabulary "
                    "(hostile-type signature) and text bands fragmented "
                    "into overlapping records (letterspaced/script).")
    ap.add_argument("inputs", nargs="+",
                    help="image path(s) — `eyes describe` is run on each — "
                         "or a saved describe .json")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--fail-on-non-lexical", action="store_true",
                    help="exit 1 if any image verdict is "
                         "non_lexical_text_detected")
    args = ap.parse_args(argv)

    lex, sources, zipf_fn = load_lexicon()
    if not lex:
        print("lexical-screen: no lexicon found (wordfreq unavailable and "
              "/usr/share/dict absent) — cannot screen", file=sys.stderr)
        return 2

    results = [analyze(p, lex, zipf_fn) for p in args.inputs]

    meta = {"lexicon": {"size": len(lex), "sources": sources,
                        "zipf_stem_floor": ZIPF_STEM_MIN if zipf_fn else None,
                        "min_token_len": MIN_TOKEN_LEN,
                        "non_lexical_frac": NON_LEXICAL_FRAC,
                        "band_y_overlap": BAND_Y_OVERLAP,
                        "band_x_overlap": BAND_X_OVERLAP}}

    if args.json:
        print(json.dumps({"lexicon": meta["lexicon"], "results": results},
                         indent=2, ensure_ascii=False))
    else:
        print(f"lexicon: {len(lex)} words from {', '.join(sources)}")
        for r in results:
            if r.get("verdict") == "error":
                print(f"{r['image']}: ERROR {r['notes'][0]}")
                continue
            print(f"\n{r['image']}  records={r['n_text_records']}  "
                  f"non_lexical={r['non_lexical_strings']}  "
                  f"oov_strings={r['strings_with_oov']}  "
                  f"frag_bands={r['fragmented_bands']}")
            for s in r["strings"]:
                if s["verdict"] == "clean" and not any(
                        t["status"] in ("merged", "merged_partial", "inflected")
                        for t in s["tokens"]):
                    continue  # quiet: only show strings with findings/rescues
                mark = {"non_lexical_text": "!!", "contains_out_of_vocabulary": "!",
                        "clean": " "}[s["verdict"]]
                print(f"  {mark} {s['verdict']:<28} "
                      f"oov={s['oov_fraction']:<5} {s['string']!r}")
                for t in s["tokens"]:
                    note = fmt_token(t)
                    if note:
                        print(f"        {t['token']:<22}{note}")
            for b in r["fragmentation"]:
                mem = " | ".join(m["string"] for m in b["records"])
                print(f"  ## ocr_line_fragmented y={b['y_band']} "
                      f"n={b['n_records']} x_overlap={b['x_overlap_example'][2]}"
                      + (f"  encompassing={b['encompassing_record']!r}"
                         if b["encompassing_record"] else ""))
                print(f"       {mem}")
            print(f"  VERDICT: {r['verdict'].upper()}")

    any_nonlex = any(r.get("verdict") == "non_lexical_text_detected"
                     for r in results)
    return 1 if (args.fail_on_non_lexical and any_nonlex) else 0


if __name__ == "__main__":
    sys.exit(main())
