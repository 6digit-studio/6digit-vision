#!/usr/bin/env python3
"""lifecycle-diff — entity-lifecycle diffing over `eyes reel --json`.

Fills the gap named by evals/object-dropout/VERDICT.md: `reel` emits
per-pair facts (label Jaccard, OCR overlap, pixel diffs) but nothing
computes entity lifecycles across the sequence — the reader must
cross-reference frames_detail against pairs[].ocr.unmatched by hand.

This detector diffs per-frame object-name sets and OCR strings across
a reel and emits named facts: "element X present frames a-b, absent
c-d". A >=2-frame persistence rule on BOTH sides of the transition
excludes per-frame-churning values (ticking counts, timers, percentages)
for free — they never hold a consecutive run long enough to qualify.

Zero new model calls: consumes frames_detail + pairs only.

Usage (from repo root):
    uv run eyes reel evals/object-dropout --json > /tmp/reel.json
    uv run python detectors/lifecycle-diff/lifecycle_diff.py /tmp/reel.json

    # or let the detector run eyes itself:
    uv run python detectors/lifecycle-diff/lifecycle_diff.py --reel evals/object-dropout

Honesty notes baked into the output:
  - departures are grouped by the frame boundary where absence begins;
    a text element AND an object label vanishing at the same boundary
    is cross-channel corroboration (one physical UI element seen by two
    record channels) -> kind "dropout", confidence "high".
  - >=2 same-channel elements departing together is consistent with a
    content update (status line advancing, frozen duplicate ending) ->
    kind "coordinated_departure", confidence "low".
  - a solo departure that RETURNS later is likely record noise
    (Mirage/OCR miss), not a real dropout -> confidence "low".
  - digit-bearing strings are tagged value_like (churn-prone).
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


def norm(s: str) -> str:
    """Match key: case-insensitive, whitespace-collapsed."""
    return re.sub(r"\s+", " ", s).strip().lower()


def value_like(s: str) -> bool:
    """Digit-bearing strings churn by nature (counts, %, timers)."""
    return bool(re.search(r"\d", s))


def presence_runs(mask: list[bool]) -> list[tuple[int, int]]:
    """Maximal inclusive (start, end) runs of True, 0-based."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def fmt_range(a: int, b: int) -> str:
    """1-based inclusive frame range for humans."""
    return f"{a + 1}-{b + 1}"


def collect_events(frames_detail: list[dict], min_present: int,
                   min_absent: int) -> tuple[list[dict], list[dict], dict]:
    """Diff per-frame element sets; return (departures, arrivals, stats)."""
    n = len(frames_detail)
    departures: list[dict] = []
    arrivals: list[dict] = []
    tracked = {"text": 0, "objects": 0}

    for channel in ("text", "objects"):
        # per-frame sets of normalized keys + first-seen display form
        frame_sets = []
        display: dict[str, str] = {}
        for fd in frames_detail:
            s = set()
            for raw in fd.get(channel) or []:
                if not raw:
                    continue
                k = norm(raw)
                s.add(k)
                display.setdefault(k, raw.strip())
            frame_sets.append(s)

        universe = set().union(*frame_sets) if frame_sets else set()
        tracked[channel] = len(universe)

        for elem in sorted(universe):
            mask = [elem in fs for fs in frame_sets]
            runs = presence_runs(mask)
            for idx, (a, b) in enumerate(runs):
                run_len = b - a + 1
                if run_len < min_present:
                    continue  # churn: never held a consecutive run

                # ---- departure: absence run immediately after this run
                c = b + 1
                absent_len = 0
                while c + absent_len < n and not mask[c + absent_len]:
                    absent_len += 1
                if absent_len >= min_absent:
                    absent_end = c + absent_len - 1
                    returned = any(rs > absent_end for rs, _ in runs[idx + 1:])
                    departures.append({
                        "element": display.get(elem, elem),
                        "channel": "ocr" if channel == "text" else "objects",
                        "present_frames": fmt_range(a, b),
                        "absent_frames": fmt_range(c, absent_end),
                        "absent_start_0": c,          # internal: grouping key
                        "_present_0": (a, b),          # internal: static-pair check
                        "absent_to_end": absent_end == n - 1,
                        "returned": returned,
                        "value_like": value_like(elem),
                    })

                # ---- arrival: this run follows a >=min_absent absence
                if a > 0:
                    prev_end = runs[idx - 1][1] if idx > 0 else -1
                    leading_absent = a - prev_end - 1
                    if leading_absent >= min_absent:
                        arrivals.append({
                            "element": display.get(elem, elem),
                            "channel": "ocr" if channel == "text" else "objects",
                            "absent_frames": fmt_range(prev_end + 1, a - 1),
                            "present_frames": fmt_range(a, b),
                            "value_like": value_like(elem),
                        })

    return departures, arrivals, {"tracked": tracked, "frames": n}


def pair_context(pairs: list[dict], absent_start_0: int) -> dict:
    """Facts about the transition INTO the absence + post-departure motion."""
    # transition pair index = last present frame = absent_start_0 - 1
    ti = absent_start_0 - 1
    ctx = {}
    if 0 <= ti < len(pairs):
        p = pairs[ti]
        ctx["transition_pair"] = p.get("pair")
        if "labels" in p:
            ctx["labels_score"] = p["labels"].get("score")
        if "ocr" in p:
            ctx["ocr_score"] = p["ocr"].get("score")
        ctx["changed_pct"] = p.get("pixel", {}).get("changed_pct")
    post = [p.get("pixel", {}).get("changed_pct", 0.0)
            for p in pairs[ti + 1:]] if ti >= 0 else []
    ctx["post_departure_max_changed_pct"] = round(max(post), 4) if post else None
    ctx["siblings_animating"] = bool(post) and max(post) >= 0.001
    return ctx


def classify(departures: list[dict], pairs: list[dict]) -> list[dict]:
    """Group departures by boundary; assign kind/confidence/notes."""
    by_boundary: dict[int, list[dict]] = {}
    for e in departures:
        by_boundary.setdefault(e.pop("absent_start_0"), []).append(e)

    for boundary, group in sorted(by_boundary.items()):
        channels = {e["channel"] for e in group}
        names = [e["element"] for e in group]
        for e in group:
            e.update(pair_context(pairs, boundary))
            pa, pb = e.pop("_present_0")
            # pairs strictly inside the presence run: indices pa..pb-1
            static_inside = [pairs[i].get("pair") for i in range(pa, pb)
                             if i < len(pairs) and pairs[i].get("static")]
            notes = []
            if static_inside:
                notes.append("presence run spans static pair(s) "
                             f"{static_inside} — persistence may be a "
                             "frozen/duplicated frame, not stable rendering")
            if e["returned"]:
                notes.append("element returned later — transient absence, "
                             "possibly a record miss rather than a real loss")
            if e["absent_to_end"]:
                notes.append("absent through end of sequence")
            if e["value_like"]:
                notes.append("digit-bearing value — churn-prone class")
            if not e["siblings_animating"]:
                notes.append("no pixel motion after departure — sequence tail "
                             "is static; absence may be moot")

            if len(group) >= 2 and len(channels) >= 2:
                e["kind"] = "dropout"
                e["confidence"] = "high"
                e["corroborated_with"] = [x for x in names if x != e["element"]]
                notes.insert(0, "cross-channel corroboration: text + object "
                                "depart at the same boundary — one physical "
                                "element seen by two record channels")
            elif len(group) >= 2:
                e["kind"] = "coordinated_departure"
                e["confidence"] = "low"
                notes.insert(0, f"{len(group)} elements departed at this "
                                "boundary — consistent with a content update, "
                                "not an isolated loss")
            else:
                e["kind"] = "solo_departure"
                e["confidence"] = ("medium" if (e["absent_to_end"]
                                                and not e["value_like"]
                                                and not e["returned"])
                                   else "low")
            e["notes"] = notes
    return [e for _, group in sorted(by_boundary.items()) for e in group]


def run_reel(inputs: list[str]) -> dict:
    """Invoke `eyes reel <inputs> --json` and parse stdout."""
    eyes = shutil.which("eyes")
    if eyes:
        cmd = [eyes, "reel", *inputs, "--json"]
    elif shutil.which("uv"):
        cmd = ["uv", "run", "eyes", "reel", *inputs, "--json"]
    else:
        raise SystemExit("neither `eyes` nor `uv` on PATH — pass a saved "
                         "reel JSON instead")
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          cwd=REPO_ROOT)
    if proc.returncode != 0:
        raise SystemExit(f"eyes reel failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def detect(report: dict, min_present: int, min_absent: int) -> dict:
    frames_detail = report.get("frames_detail") or []
    pairs = report.get("pairs") or []

    if not report.get("with_records", True) or not any(
            fd.get("text") or fd.get("objects") for fd in frames_detail):
        return {
            "verdict": "no_record_data",
            "summary": "reel was produced with --no-records (or records "
                       "empty): lifecycle diffing needs frames_detail "
                       "objects/text. Re-run `eyes reel` without "
                       "--no-records.",
            "departures": [], "arrivals": [],
        }

    departures, arrivals, stats = collect_events(
        frames_detail, min_present, min_absent)
    departures = classify(departures, pairs)

    dropouts = [e for e in departures if e["kind"] == "dropout"]
    if dropouts:
        verdict = "dropout_detected"
        named = "; ".join(
            f"{e['element']!r} ({e['channel']}) present {e['present_frames']}, "
            f"absent {e['absent_frames']}" for e in dropouts)
        summary = (f"{len(dropouts)} corroborated element dropout(s): {named}. "
                   "Text + object channels agree on the same boundary.")
    elif departures:
        verdict = "departures_only"
        summary = (f"{len(departures)} persistent element(s) departed but "
                   "none with cross-channel corroboration — consistent with "
                   "content updates/churn, not an isolated dropout. See "
                   "departures for the facts.")
    else:
        verdict = "clean"
        summary = ("No persistent element departed: every OCR string and "
                   "object label that held a >=%d-frame run either persists "
                   "to the end or never left for >=%d consecutive frames."
                   % (min_present, min_absent))

    out = {
        "verdict": verdict,
        "summary": summary,
        "params": {"min_present_frames": min_present,
                   "min_absent_frames": min_absent},
        "stats": stats,
        "departures": departures,
        "arrivals": arrivals,
    }
    if stats["frames"] < min_present + min_absent:
        out["caveat"] = (f"only {stats['frames']} frames — shorter than "
                         f"min_present+min_absent ({min_present}+{min_absent}); "
                         "the persistence rule cannot fire, so 'clean' means "
                         "'no evidence', not 'verified clean'")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Entity-lifecycle diff over `eyes reel --json` output: "
                    "names elements that persist then vanish mid-sequence.")
    ap.add_argument("reel_json", nargs="?",
                    help="path to saved `eyes reel --json` output")
    ap.add_argument("--reel", nargs="+", metavar="INPUT",
                    help="instead of a JSON file, run `eyes reel INPUT... "
                         "--json` (files and/or directories)")
    ap.add_argument("--min-present", type=int, default=2,
                    help="min consecutive frames present to track (default 2)")
    ap.add_argument("--min-absent", type=int, default=2,
                    help="min consecutive frames absent to call a departure "
                         "(default 2)")
    args = ap.parse_args(argv)

    if args.reel:
        report = run_reel(args.reel)
        source = " ".join(args.reel)
    elif args.reel_json:
        report = json.loads(Path(args.reel_json).read_text())
        source = args.reel_json
    else:
        ap.error("give a reel JSON path or --reel INPUT...")

    out = detect(report, args.min_present, args.min_absent)
    out["source"] = source
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
