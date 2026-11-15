# /// script
# requires-python = ">=3.11"
# ///
"""totals-consistency — deterministic invoice/document arithmetic auditor.

Fills the gap named in evals/semantic-data/VERDICT.md: an invoice whose
SUBTOTAL is bound to the wrong value ($87.50 instead of the $77.50 the
line items sum to) while Tax and Total derive *consistently* from the
wrong subtotal. Every perceptual detector, `eyes score`, and an
unprompted describe walk past it — the wrong number is dark-on-white,
correctly typeset, mid-frame. Only summation catches it, and nothing in
the instrument computes sums.

This detector adds that layer, model-free, on data `eyes describe`
already emits:

  1. band text records into rows by bbox-y overlap (same transitive
     clustering as lexical-screen);
  2. extract currency amounts per row — '$'/'€'/'£'/'¥' prefixed numbers
     (with K/M/B magnitude suffixes) or bare cents-decimals ('87.50'),
     with '-', '−', '(' ')' sign handling; the row's value is its
     RIGHTMOST amount token (extended-price column convention);
  3. classify each amount-bearing row via a small label lexicon —
     subtotal / tax(+rate) / total / discount / shipping / fee / item;
  4. check the arithmetic identities a consistent document must satisfy:
       line_items_sum : Σ signed(line rows) == Subtotal
       totals_block   : Subtotal + Tax + charges − discounts == Total
       tax_rate       : Tax == stated_rate% × base   (when a rate is printed)

On the eval defect it emits `line_items_sum_mismatch:
items=77.50 subtotal=87.50 delta=10.00` while `totals_block` and
`tax_rate` report ok — the internally-consistent-but-wrong signature
exactly as the eval described.

Honest limits (see VERDICT.md): the label lexicon is small — brand names
colliding with it ('Total Wine'), unlabeled charge rows in the totals
block (check skipped, not guessed), tax bases that legitimately differ
from subtotal (shipping taxable or not is jurisdiction-dependent — a
rate mismatch with adjustment rows present is demoted to a note), and
quantity×price rows where the rightmost-amount heuristic can pick the
wrong figure. Non-document images produce `no_currency_amounts` —
silence, not a verdict.

Usage (from repo root):
    uv run detectors/totals-consistency/totals_consistency.py evals/semantic-data/defect.png
    uv run detectors/totals-consistency/totals_consistency.py --json evals/semantic-data/*.png
    uv run detectors/totals-consistency/totals_consistency.py record.json   # saved `eyes describe` output
    uv run detectors/totals-consistency/totals_consistency.py --fail-on-inconsistent *.png

Exit code is 0 unless --fail-on-inconsistent is given and any image
verdict is `totals_inconsistent`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------ tunables

BAND_Y_OVERLAP = 0.5     # vertical overlap / max(record heights) to share a row
SUM_TOL_ABS = 0.05       # flat cents tolerance for every identity
SUM_TOL_REL = 0.001      # plus this fraction of the base (OCR noise floor)
MAGNITUDE = {"k": 1e3, "m": 1e6, "b": 1e9}

# Amounts: '$38.00', '€1.234,56' is NOT handled (US-style decimals only —
# documented limit), '$1.24M' -> 1240000, '-$5.00', '($5.00)', '87.50'.
# Bare (symbol-less) amounts MUST carry exactly two decimals so '2025',
# '#1042', '250g', '8%' never parse as money.
_AMOUNT_RE = re.compile(r"""
    (?P<lead>[-−(+]?)\s*                       # optional sign/paren before symbol
    (?P<cur>[$€£¥])\s*(?P<csign>[-−])?\s*
    (?P<cnum>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)
    (?P<cmag>[KkMmBb])?
    (?![\d.%]|\.(?=\d)|[A-Za-z])
    |
    (?<![\w.,$€£¥])
    (?P<blead>[-−(+]?)\s*
    (?P<bnum>\d+(?:,\d{3})*\.\d{2})
    (?P<bmag>[KkMmBb])?
    (?![\d.%]|\.(?=\d)|[A-Za-z])
""", re.VERBOSE)

_RATE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per\s+cent)", re.I)

# Role lexicon, checked in order — subtotal MUST precede total ('Sub-total'
# contains a word-boundary 'total'). item is the fallthrough.
ROLE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("subtotal", re.compile(r"\bsub\s*-?\s*tot\w*\b", re.I)),
    ("tax",      re.compile(r"\b(?:sales\s+|state\s+|local\s+|county\s+)?"
                            r"(?:tax|taxes|vat|gst|hst|pst)\b", re.I)),
    ("discount", re.compile(r"\b(?:discount|coupon|promo(?:tion|\s*code)?|"
                            r"rebate|voucher|markdown|savings|price\s*cut)\b"
                            r"|\bcredit\b(?!\s*card)", re.I)),
    ("shipping", re.compile(r"\b(?:shipping|delivery|freight|postage|"
                            r"courier|parcel)\b", re.I)),
    ("fee",      re.compile(r"\b(?:fees?|service\s+charge|surcharge|tip|"
                            r"gratuity|insurance|deposit|handling)\b", re.I)),
    ("total",    re.compile(r"\b(?:grand\s+|order\s+|invoice\s+|balance\s+)?"
                            r"tot\w*\b|\bamount\s+due\b|\bbalance\s+due\b|"
                            r"\bamount\s+payable\b|\btotal\s+amount\b", re.I)),
]

TOTALS_ROLES = {"subtotal", "tax", "total"}
LINE_ROLES = {"item", "shipping", "fee", "discount"}
ADDITIVE_ROLES = {"item", "shipping", "fee"}   # discount subtracts via sign


# ------------------------------------------------------------------ amounts

def extract_amounts(text: str) -> list[dict]:
    """All currency amounts in one record string, in reading order.

    Each hit: {value (signed float), raw, end (char offset of match end)}.
    Sign comes from an explicit '-', '−', or '(' ... ')' wrap; discount
    LABEL-implied negativity is applied later at row level, not here.
    """
    hits = []
    for m in _AMOUNT_RE.finditer(text):
        if m.group("cur"):
            num_s, mag_s = m.group("cnum"), m.group("cmag")
            sign_s = m.group("lead") or m.group("csign") or ""
            end = m.end()
        else:
            num_s, mag_s = m.group("bnum"), m.group("bmag")
            sign_s = m.group("blead") or ""
            end = m.end()
        try:
            value = float(num_s.replace(",", ""))
        except ValueError:
            continue
        if mag_s:
            value *= MAGNITUDE[mag_s.lower()]
        neg = sign_s.startswith(("-", "−", "("))
        # '( $5.00 )' wrap: lead captured '(' only when adjacent to symbol;
        # a ')' right after the number confirms it — either way '(' means neg.
        hits.append({"value": -value if neg else value,
                     "raw": m.group(0).strip(), "end": end})
    return hits


# ------------------------------------------------------------------ rows

def _y_overlap(a: list, b: list) -> float:
    """Vertical overlap of two [x0,y0,x1,y1] bboxes / MAX height —
    same convention as lexical-screen's line bands."""
    h = max(a[3] - a[1], b[3] - b[1])
    if h <= 0:
        return 0.0
    ov = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, ov) / h


def build_rows(text_records: list[dict]) -> list[dict]:
    """Cluster text records into visual rows; extract label + value.

    Only bands containing >=1 amount become rows. Row value = the
    rightmost amount token (max member x1, then max char offset) — the
    extended-price column convention on invoices.
    """
    recs = [(i, r) for i, r in enumerate(text_records)
            if isinstance(r, dict) and isinstance(r.get("bbox"), list)
            and len(r["bbox"]) == 4 and r.get("string")]
    recs.sort(key=lambda ir: (ir[1]["bbox"][1], ir[1]["bbox"][0]))

    bands: list[list[int]] = []
    for idx, _r in recs:
        r = text_records[idx]
        placed = False
        for band in bands:
            if any(_y_overlap(r["bbox"], text_records[j]["bbox"])
                   >= BAND_Y_OVERLAP for j in band):
                band.append(idx)
                placed = True
                break
        if not placed:
            bands.append([idx])

    rows = []
    for band in bands:
        members = sorted((text_records[j] for j in band),
                         key=lambda r: (r["bbox"][0], r["bbox"][1]))
        label = " ".join(m.get("string", "").strip() for m in members)
        # collect every amount hit with its column position
        best = None  # (x1, end, value)
        for m in members:
            for hit in extract_amounts(m.get("string", "")):
                key = (m["bbox"][2], hit["end"])
                if best is None or key > (best[0], best[1]):
                    best = (*key, hit["value"], hit["raw"])
        if best is None:
            continue  # no money on this visual row
        x1, _end, value, raw = best
        role = "item"
        for name, pat in ROLE_PATTERNS:
            if pat.search(label):
                role = name
                break
        # a printed rate only means something on a tax row — '%' figures
        # elsewhere are deltas/changes, not tax rates
        rate = None
        if role == "tax":
            rm = _RATE_RE.search(label)
            if rm:
                rate = float(rm.group(1))
        # label-implied sign: a 'discount' row states a reduction even
        # when OCR dropped the '-' — but never flip an explicit negative.
        if role == "discount" and value > 0:
            value = -value
        ys = [m["bbox"][1] for m in members] + [m["bbox"][3] for m in members]
        rows.append({
            "role": role, "value": round(value, 2), "raw_amount": raw,
            "rate_pct": rate, "label": label,
            "y": [min(ys[0::2]), max(ys[1::2])],
            "n_records": len(members),
            "records": [{"string": m.get("string"), "bbox": m.get("bbox"),
                         "score": m.get("score")} for m in members],
        })
    rows.sort(key=lambda r: r["y"][0])
    return rows


# ------------------------------------------------------------------ checks

def _tol(base: float) -> float:
    return max(SUM_TOL_ABS, abs(base) * SUM_TOL_REL)


def _signed(row: dict) -> float:
    return row["value"]  # discount rows already negated at build time


def analyze(path: str) -> dict:
    try:
        rec, source = _load_record(path)
    except Exception as e:
        return {"image": path, "verdict": "error", "notes": [str(e)]}

    rows = build_rows(rec.get("text") or [])
    notes: list[str] = []
    findings: list[dict] = []
    checks: list[dict] = []

    if not rows:
        return {"image": source, "verdict": "no_currency_amounts",
                "n_text_records": len(rec.get("text") or []),
                "n_amount_rows": 0,
                "rows": [], "findings": [], "checks": [], "notes": notes}

    # region split: totals block starts at the first subtotal/tax/total row
    totals_start = next((i for i, r in enumerate(rows)
                         if r["role"] in TOTALS_ROLES), len(rows))
    line_rows = [r for r in rows[:totals_start] if r["role"] in LINE_ROLES]
    totals_rows = rows[totals_start:]

    subtotal_rows = [r for r in rows if r["role"] == "subtotal"]
    total_rows = [r for r in rows if r["role"] == "total"]
    tax_rows = [r for r in rows if r["role"] == "tax"]

    subtotal = subtotal_rows[0] if len(subtotal_rows) == 1 else None
    stated_total = total_rows[-1] if len(total_rows) == 1 else None
    base_value = None
    base_kind = None
    if subtotal is not None:
        base_value, base_kind = subtotal["value"], "subtotal"
    elif line_rows:
        base_value = round(sum(_signed(r) for r in line_rows), 2)
        base_kind = "line_items_sum"

    # -- shared totals-block pieces (needed by identity 2 AND by the H2
    #    verification inside identity 1) ---------------------------------
    line_sum = round(sum(_signed(r) for r in line_rows), 2) if line_rows else None
    unclassified = [r for r in totals_rows if r["role"] == "item"]
    # block net = tax + shipping + fee − discount (discounts already carry
    # negative values); the subtotal row itself is not a component.
    block_net = round(sum(_signed(r) for r in totals_rows
                          if r["role"] in ("tax", "shipping", "fee", "discount")), 2)

    # -- identity 1: line items (+charges) sum to the stated subtotal -----
    h2_active = False
    h2_info = None
    if len(subtotal_rows) > 1:
        checks.append({"identity": "line_items_sum", "result": "skipped",
                       "detail": f"{len(subtotal_rows)} subtotal rows — ambiguous"})
        notes.append("multiple_subtotal_rows")
    elif subtotal is None:
        checks.append({"identity": "line_items_sum", "result": "skipped",
                       "detail": "no subtotal row to verify against"})
    elif not line_rows:
        checks.append({"identity": "line_items_sum", "result": "skipped",
                       "detail": "no line-item rows above the totals block"})
        notes.append("no_line_item_rows")
    else:
        diff = round(line_sum - subtotal["value"], 2)
        tol = _tol(subtotal["value"])
        if abs(diff) <= tol:
            checks.append({"identity": "line_items_sum", "result": "ok",
                           "detail": f"items={line_sum} == subtotal={subtotal['value']}"})
        else:
            # Alternative hypothesis H2: shipping/fee rows listed among the
            # items are actually post-subtotal charges. It is confirmed
            # only when the item-only sum matches the subtotal AND the
            # stated total still reconciles with those charges added
            # after it — otherwise the primary reading stands and the
            # mismatch is a real finding.
            item_only = round(sum(_signed(r) for r in line_rows
                                  if r["role"] in ("item", "discount")), 2)
            shipfee = round(sum(_signed(r) for r in line_rows
                                if r["role"] in ("shipping", "fee")), 2)
            h2_sub_ok = abs(item_only - subtotal["value"]) <= _tol(subtotal["value"])
            h2_expected = round(subtotal["value"] + block_net + shipfee, 2) \
                if (h2_sub_ok and len(total_rows) == 1
                    and stated_total is not None and not unclassified) else None
            h2_total_ok = (abs(h2_expected - stated_total["value"])
                           <= _tol(stated_total["value"])) \
                if h2_expected is not None else None
            h2_info = {"item_only_sum": item_only, "shipping_fee_sum": shipfee,
                       "subtotal_holds": h2_sub_ok, "expected_total": h2_expected,
                       "total_holds": h2_total_ok}
            if h2_sub_ok and (h2_total_ok is True or
                              (h2_total_ok is None and not total_rows)):
                # confirmed by the total, or no total row exists to
                # contradict it — consistent under the alternate reading
                checks.append({"identity": "line_items_sum",
                               "result": "ok_alternative",
                               "detail": f"items+ship/fee={line_sum} != subtotal="
                                         f"{subtotal['value']}, but items-only="
                                         f"{item_only} == subtotal and ship/fee "
                                         f"{shipfee} reconciles post-subtotal"})
                h2_active = True
                notes.append("shipping_fees_post_subtotal")
            else:
                why = ("alternative_hypothesis_contradicted_by_total"
                       if h2_total_ok is False else
                       "alternative_hypothesis_unverifiable" if h2_sub_ok
                       else "alternative_hypothesis_failed")
                notes.append(why)
                checks.append({"identity": "line_items_sum", "result": "mismatch",
                               "detail": f"items={line_sum} != subtotal={subtotal['value']} "
                                         f"(delta={diff})"})
                findings.append({
                    "kind": "line_items_sum_mismatch",
                    "line_sum": line_sum, "subtotal": subtotal["value"],
                    "delta": diff, "tolerance": round(tol, 4),
                    "n_line_rows": len(line_rows),
                    "line_rows": [{"role": r["role"], "value": r["value"],
                                   "label": r["label"], "y": r["y"]}
                                  for r in line_rows],
                    "alternative_hypothesis": h2_info,
                })

    # -- identity 2: subtotal/lines + totals-block charges == stated total -
    if len(total_rows) > 1:
        checks.append({"identity": "totals_block", "result": "skipped",
                       "detail": f"{len(total_rows)} total-labeled rows — ambiguous"})
        notes.append("multiple_total_rows")
    elif stated_total is None:
        checks.append({"identity": "totals_block", "result": "skipped",
                       "detail": "no total row"})
    elif base_value is None:
        checks.append({"identity": "totals_block", "result": "skipped",
                       "detail": "no subtotal and no line items — base unknown"})
        notes.append("no_determinable_base")
    elif unclassified:
        checks.append({"identity": "totals_block", "result": "skipped",
                       "detail": "unlabeled amount row(s) inside totals block: "
                                 + "; ".join(r["label"][:40] for r in unclassified)})
        notes.append("unclassified_amount_in_totals")
    else:
        h2_shipfee = h2_info["shipping_fee_sum"] if h2_active and h2_info else 0.0
        expected = round(base_value + block_net + h2_shipfee, 2)
        diff = round(expected - stated_total["value"], 2)
        tol = _tol(stated_total["value"])
        components = [{"role": r["role"], "value": r["value"],
                       "label": r["label"]} for r in totals_rows]
        if abs(diff) <= tol:
            detail = f"expected={expected} == total={stated_total['value']}"
            if h2_active:
                detail += " (line ship/fee charged post-subtotal)"
            checks.append({"identity": "totals_block", "result": "ok",
                           "detail": detail})
        else:
            checks.append({"identity": "totals_block", "result": "mismatch",
                           "detail": f"expected={expected} != total={stated_total['value']} "
                                     f"(delta={diff})"})
            findings.append({
                "kind": "totals_block_mismatch",
                "expected_total": expected, "stated_total": stated_total["value"],
                "delta": diff, "tolerance": round(tol, 4),
                "base": {"kind": base_kind, "value": base_value},
                "components": components,
            })

    # -- identity 3: printed tax rate x base == stated tax -----------------
    if len(tax_rows) == 1 and tax_rows[0]["rate_pct"] is not None \
            and base_value is not None:
        tax_row = tax_rows[0]
        expected_tax = round(base_value * tax_row["rate_pct"] / 100.0 + 1e-9, 2)
        diff = round(tax_row["value"] - expected_tax, 2)
        tol = _tol(expected_tax)
        # tax bases legitimately differ from subtotal when shipping is
        # taxable or discounts apply — demote mismatches to a note when
        # adjustment rows exist rather than overclaim.
        adjustments = [r for r in rows
                       if r["role"] in ("shipping", "fee", "discount")]
        if abs(diff) <= tol:
            checks.append({"identity": "tax_rate", "result": "ok",
                           "detail": f"{tax_row['rate_pct']}% x {base_value} "
                                     f"= {expected_tax} == tax={tax_row['value']}"})
        elif adjustments:
            checks.append({"identity": "tax_rate", "result": "skipped",
                           "detail": f"{tax_row['rate_pct']}% x {base_value} "
                                     f"= {expected_tax} vs tax={tax_row['value']} "
                                     f"— adjustment rows present, tax base ambiguous"})
            notes.append("tax_base_ambiguous")
        else:
            checks.append({"identity": "tax_rate", "result": "mismatch",
                           "detail": f"{tax_row['rate_pct']}% x {base_value} "
                                     f"= {expected_tax} != tax={tax_row['value']}"})
            findings.append({
                "kind": "tax_rate_mismatch",
                "rate_pct": tax_row["rate_pct"], "base": base_value,
                "expected_tax": expected_tax, "stated_tax": tax_row["value"],
                "delta": diff, "tolerance": round(tol, 4),
                "tax_label": tax_row["label"],
            })
    else:
        why = []
        if not tax_rows:
            why.append("no tax row")
        elif len(tax_rows) > 1:
            why.append(f"{len(tax_rows)} tax rows")
        elif tax_rows[0]["rate_pct"] is None:
            why.append("tax row prints no rate")
        if base_value is None:
            why.append("no determinable base")
        checks.append({"identity": "tax_rate", "result": "skipped",
                       "detail": "; ".join(why) or "insufficient structure"})

    mismatch_kinds = {"line_items_sum_mismatch", "totals_block_mismatch",
                      "tax_rate_mismatch"}
    if any(f["kind"] in mismatch_kinds for f in findings):
        verdict = "totals_inconsistent"
    elif any(c["result"] in ("ok", "ok_alternative") for c in checks):
        verdict = "totals_consistent"
    else:
        verdict = "insufficient_structure"

    return {
        "image": source,
        "verdict": verdict,
        "n_text_records": len(rec.get("text") or []),
        "n_amount_rows": len(rows),
        "rows": [{k: r[k] for k in ("role", "value", "raw_amount", "rate_pct",
                                    "label", "y", "n_records")}
                 for r in rows],
        "findings": findings,
        "checks": checks,
        "notes": notes,
    }


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


def _load_record(path: str) -> tuple[dict, str]:
    """Return (describe_record, source_label). .json -> saved record;
    anything else -> run eyes describe on it."""
    p = Path(path)
    if p.suffix == ".json" and p.exists():
        data = json.loads(p.read_text())
        if isinstance(data, dict) and "text" not in data:
            for key in ("record", "describe", "result"):
                if isinstance(data.get(key), dict) and "text" in data[key]:
                    data = data[key]
                    break
        return data, str(path)
    return run_eyes_describe(path), path


# ------------------------------------------------------------------ output

def _fmt_rows(rows: list[dict]) -> str:
    out = []
    for r in rows:
        rate = f" ({r['rate_pct']:g}%)" if r["rate_pct"] is not None else ""
        out.append(f"    {r['role']:<8} {r['value']:>10.2f}  "
                   f"y={r['y']}  {r['label'][:64]!r}{rate}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic totals-consistency audit on `eyes "
                    "describe` text records: groups OCR strings into rows "
                    "by bbox-y overlap, classifies amount rows via a "
                    "label lexicon, and checks the arithmetic identities "
                    "(Σitems=Subtotal, Subtotal+charges−discounts=Total, "
                    "Tax=rate×base). No model in the loop.")
    ap.add_argument("inputs", nargs="+",
                    help="image path(s) — `eyes describe` is run on each — "
                         "or a saved describe .json")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--fail-on-inconsistent", action="store_true",
                    help="exit 1 if any image verdict is totals_inconsistent")
    args = ap.parse_args(argv)

    results = [analyze(p) for p in args.inputs]

    if args.json:
        print(json.dumps({"results": results}, indent=2, ensure_ascii=False))
    else:
        for r in results:
            if r.get("verdict") == "error":
                print(f"{r['image']}: ERROR {r['notes'][0]}")
                continue
            print(f"\n{r['image']}  text_records={r['n_text_records']}  "
                  f"amount_rows={r['n_amount_rows']}")
            if r["rows"]:
                print(_fmt_rows(r["rows"]))
            for f in r["findings"]:
                print(f"  !! {f['kind']}: {json.dumps(f, ensure_ascii=False)}")
            for c in r["checks"]:
                mark = {"ok": "  ", "ok_alternative": " ~",
                        "mismatch": "!!", "skipped": " -"}[c["result"]]
                print(f"{mark} check {c['identity']:<15} {c['result']:<8} "
                      f"{c['detail']}")
            for n in r["notes"]:
                print(f"  ~ note: {n}")
            print(f"  VERDICT: {r['verdict'].upper()}")

    bad = any(r.get("verdict") == "totals_inconsistent" for r in results)
    return 1 if (args.fail_on_inconsistent and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
