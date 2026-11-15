#!/usr/bin/env python3
"""strobe — flicker/strobe detection + motion-coherence characterization
over `eyes reel --json`.

Fills two gaps named by evals/chaotic-motion/VERDICT.md:

1. STROBE/FLICKER (~20 lines on data already collected). lifecycle-diff's
   collect_events computes per-frame presence bitmasks for every OCR string
   and object name, then DISCARDS runs shorter than min_present — the rule
   that excludes churn is exactly what strict alternation (101010) never
   satisfies. This detector keeps the discarded runs: an element whose
   presence mask alternates on every frame (>= min_transitions transitions,
   max run length <= max_run) is a strobe — "LIVE strobes on/off".

2. MOTION COHERENCE (stretch). Pixel diffs measure HOW MUCH changed, never
   HOW. Within the union of per-pair diff_bboxes (the animated region),
   each pixel's luminance is a time series across frames; lag-1
   autocorrelation measures frame-to-frame predictability. Eased motion is
   correlated (r1 > 0); unseeded randomness is white (r1 ~ 0 or negative).
   Reported as a characterization fact, not a defect verdict — a
   legitimately chaotic effect (particles, jitter) reads the same.

Zero new model calls for part 1; part 2 reads the frame images already
named in frames_detail[].file (no Mirage calls).

Usage (from repo root):
    uv run eyes reel evals/chaotic-motion --json > /tmp/reel.json
    uv run python detectors/strobe/strobe.py /tmp/reel.json

    # or let the detector run eyes itself:
    uv run python detectors/strobe/strobe.py --reel evals/chaotic-motion

Honesty notes baked into the output:
  - "strobes" requires STRICT whole-sequence alternation. An element that
    strobes then settles (101100) or strobes with a duty cycle != 50%
    (101001) is reported under "alternating_elements", not "strobes".
  - presence masks are over normalized OCR/object strings. Mirage OCR
    noise can produce phantom strings, but a phantom must still alternate
    perfectly to fire — singleton garbage (the waveform bars' '.lllhl.'
    reads) has <=1 transition and cannot strobe. value_like strings
    (digit-bearing) are tagged churn-prone.
  - motion coherence needs >=4 frames to say anything (3 lag-1 pairs is
    noise); the eval reels have 6. Treat n<10 as directional, not proven.
  - luminance-only series: a pure hue swap at constant luminance is
    invisible to this channel.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- strobe --

def norm(s: str) -> str:
    """Match key: case-insensitive, whitespace-collapsed (as lifecycle-diff)."""
    return re.sub(r"\s+", " ", s).strip().lower()


def value_like(s: str) -> bool:
    return bool(re.search(r"\d", s))


def mask_stats(mask: list[bool]) -> dict:
    """Transitions + max run length over the whole presence mask."""
    n = len(mask)
    transitions = sum(1 for i in range(n - 1) if mask[i] != mask[i + 1])
    max_run = 1
    run = 1
    for i in range(1, n):
        if mask[i] == mask[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    if n == 0:
        max_run = 0
    return {"transitions": transitions, "max_run": max_run}


def present_absent_frames(mask: list[bool]) -> tuple[list[int], list[int]]:
    """1-based frame indices where the element is present / absent."""
    present = [i + 1 for i, v in enumerate(mask) if v]
    absent = [i + 1 for i, v in enumerate(mask) if not v]
    return present, absent


def _fuzzy_ratio(a: str, b: str) -> float:
    """OCR-variant similarity on normalized keys — same comparison style
    as eyes.temporal.ocr_overlap: whitespace fully stripped, SequenceMatcher
    ratio (caller picks the threshold)."""
    sa = re.sub(r"\s+", "", a)
    sb = re.sub(r"\s+", "", b)
    return SequenceMatcher(None, sa, sb).ratio()


def _annotate_strobe(rec: dict, elem: str, universe: set[str],
                     elem_masks: dict[str, list[bool]], display: dict[str, str],
                     n: int, max_run: int) -> None:
    """Guard against the OCR-split artifact: a STABLE element misread as
    variant A on odd frames and variant B on even frames produces two
    exact-match strobes for one physical non-flicker. If fuzzy-similar
    strings (ratio >= 0.75 — lower than ocr_overlap's 0.8 because one
    substituted char in a short string like 'LIVE'->'L1VE' must still
    count as a variant) jointly cover consecutive frames, the family
    does not truly alternate -> downgrade confidence and name the
    siblings."""
    siblings = [o for o in universe
                if o != elem and _fuzzy_ratio(elem, o) >= 0.75]
    rec["ocr_variant_siblings"] = [display.get(s, s) for s in sorted(siblings)]
    if not siblings:
        rec["confidence"] = "high"
        return
    family = [elem, *siblings]
    union_mask = [any(elem_masks[m][i] for m in family) for i in range(n)]
    if mask_stats(union_mask)["max_run"] > max_run:
        rec["confidence"] = "low"
        rec["note"] = ("fuzzy-similar OCR variants jointly persist across "
                       "consecutive frames — this 'strobe' may be a record "
                       "split of one stable element, not a real flicker")
    else:
        rec["confidence"] = "high"


def find_strobes(frames_detail: list[dict], min_transitions: int,
                 max_run: int) -> tuple[list[dict], list[dict], dict]:
    """Presence-mask alternation over both record channels.

    Returns (strobes, alternating, stats). strobes = strict alternation;
    alternating = >=min_transitions transitions but some run longer than
    max_run (partial flicker / duty-cycle blink — reported, not named).
    """
    n = len(frames_detail)
    strobes: list[dict] = []
    alternating: list[dict] = []
    tracked = {"text": 0, "objects": 0}

    for channel in ("text", "objects"):
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
        elem_masks = {e: [e in fs for fs in frame_sets] for e in universe}

        for elem in sorted(universe):
            mask = elem_masks[elem]
            st = mask_stats(mask)
            if st["transitions"] < min_transitions:
                continue
            present, absent = present_absent_frames(mask)
            rec = {
                "element": display.get(elem, elem),
                "channel": "ocr" if channel == "text" else "objects",
                "present_frames": present,
                "absent_frames": absent,
                "transitions": st["transitions"],
                "max_run": st["max_run"],
                "value_like": value_like(elem),
            }
            if st["max_run"] <= max_run:
                _annotate_strobe(rec, elem, universe, elem_masks, display,
                                 n, max_run)
                strobes.append(rec)
            else:
                alternating.append(rec)

    return strobes, alternating, {"tracked": tracked, "frames": n}


# ------------------------------------------------------- motion coherence --

def _resolve_frame(path_str: str, json_path: str | None) -> Path | None:
    """frames_detail[].file is relative to whatever cwd ran `eyes reel`.
    Try: as given, beside the reel JSON, then repo root."""
    p = Path(path_str)
    cands = [p]
    if json_path:
        cands.append(Path(json_path).resolve().parent / path_str)
    cands.append(REPO_ROOT / path_str)
    for c in cands:
        if c.exists():
            return c
    return None


def _union_diff_region(pairs: list[dict], w: int, h: int,
                       pad: float) -> tuple[int, int, int, int] | None:
    """Union of per-pair diff_bboxes (normalized [0,1000]) -> pixel rect."""
    xs0, ys0, xs1, ys1 = 1000, 1000, 0, 0
    seen = False
    for p in pairs:
        bb = (p.get("pixel") or {}).get("diff_bbox")
        if not bb:
            continue
        seen = True
        xs0, ys0 = min(xs0, bb[0]), min(ys0, bb[1])
        xs1, ys1 = max(xs1, bb[2]), max(ys1, bb[3])
    if not seen:
        return None
    X0 = max(0, xs0 - pad); Y0 = max(0, ys0 - pad)
    X1 = min(1000, xs1 + pad); Y1 = min(1000, ys1 + pad)
    return (int(X0 / 1000 * w), int(Y0 / 1000 * h),
            int(X1 / 1000 * w), int(Y1 / 1000 * h))


def _lag1_r1(series: "object") -> "object":
    """Per-column lag-1 autocorrelation. series: (n_frames, n_series).
    Returns array with NaN where either half has ~zero variance."""
    import numpy as np

    x0, x1 = series[:-1], series[1:]
    a = x0 - x0.mean(axis=0)
    b = x1 - x1.mean(axis=0)
    num = (a * b).sum(axis=0)
    den = np.sqrt((a ** 2).sum(axis=0) * (b ** 2).sum(axis=0))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 1e-6, num / np.maximum(den, 1e-9), np.nan)


def motion_coherence(report: dict, json_path: str | None = None,
                     var_eps: float = 4.0, pad: float = 10.0,
                     coh_lo: float = -0.10, coh_hi: float = 0.10,
                     min_frames: int = 4,
                     min_animated_px: int = 50) -> dict:
    """Lag-1 autocorrelation of per-pixel luminance inside the union of
    per-pair diff_bboxes — the animated region. Characterizes HOW the
    animated pixels evolve: correlated (eased) vs uncorrelated (erratic).
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError as e:  # pragma: no cover
        return {"verdict": "unavailable", "reason": f"numpy/PIL missing: {e}"}

    pairs = report.get("pairs") or []
    frames_detail = report.get("frames_detail") or []
    n = len(frames_detail)

    if n < min_frames:
        return {"verdict": "insufficient_frames",
                "reason": f"{n} frames < {min_frames} — lag-1 autocorrelation "
                          "needs more transitions to mean anything"}
    if not pairs or not all((p.get("pixel") or {}).get("size") for p in pairs):
        return {"verdict": "unavailable", "reason": "no pixel diff data "
                "(reel --no-records still has it; missing pairs entirely)"}

    # canvas = native frame size; diff_bbox is normalized so it maps to any
    # resolution. All frames must share one size for a coherent series.
    sizes = {(p["pixel"]["size"][0], p["pixel"]["size"][1]) for p in pairs}
    if len(sizes) != 1:
        return {"verdict": "unavailable",
                "reason": f"mixed pair canvas sizes {sorted(sizes)} — "
                          "cannot build aligned series"}
    cw, ch = pairs[0]["pixel"]["size"]

    region = _union_diff_region(pairs, cw, ch, pad)
    if region is None:
        return {"verdict": "no_motion",
                "reason": "no pair reported a diff_bbox — nothing animated "
                          "to characterize (static reel)"}
    x0, y0, x1, y1 = region
    if x1 <= x0 or y1 <= y0:
        return {"verdict": "unavailable", "reason": "degenerate diff region"}

    # resolve + load frames at native resolution (PNG is lossless; static
    # regions stay exactly constant — no resample noise)
    files = []
    missing = []
    for fd in frames_detail:
        f = fd.get("file")
        rp = _resolve_frame(f, json_path) if f else None
        if rp is None:
            missing.append(f)
        else:
            files.append(rp)
    if missing:
        return {"verdict": "unavailable",
                "reason": f"{len(missing)} frame file(s) not found "
                          f"(e.g. {missing[0]!r}) — motion coherence needs "
                          "the images, not just the JSON"}

    imgs = []
    native = None
    for rp in files:
        img = Image.open(rp).convert("RGB")
        if native is None:
            native = img.size
        elif img.size != native:
            img = img.resize(native, Image.BILINEAR)
        imgs.append(img)
    w, h = native
    # remap region: bbox was normalized on the pair canvas; native may differ
    rx0 = int(x0 / cw * w); ry0 = int(y0 / ch * h)
    rx1 = int(x1 / cw * w); ry1 = int(y1 / ch * h)
    rx0, ry0 = max(0, rx0), max(0, ry0)
    rx1, ry1 = min(w, rx1), min(h, ry1)

    lum = []
    for img in imgs:
        a = np.asarray(img, dtype=np.float32)
        lum.append(0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])
    S = np.stack([l[ry0:ry1, rx0:rx1] for l in lum])  # (n, rh, rw)
    X = S.reshape(n, -1)

    var = X.var(axis=0)
    animated = var > var_eps
    n_anim = int(animated.sum())
    region_px = int(X.shape[1])
    out = {
        "frames": n,
        "region_norm": [pairs_bbox_norm(pairs, pad)],
        "region_px": [rx1 - rx0, ry1 - ry0],
        "animated_px": n_anim,
        "animated_frac": round(n_anim / region_px, 4) if region_px else 0.0,
        "var_eps": var_eps,
    }

    if n_anim < min_animated_px:
        out.update({"verdict": "insufficient_motion",
                    "reason": f"only {n_anim} animated px (need "
                              f"{min_animated_px}) — nothing moves enough "
                              "to characterize"})
        return out

    r = _lag1_r1(X[:, animated])
    r = r[~np.isnan(r)]
    if r.size == 0:
        out.update({"verdict": "unavailable",
                    "reason": "all animated pixels degenerate under lag-1"})
        return out

    mean_r1 = float(r.mean())
    # corroborating variant: binary occupancy vs frame 0 (eyes' tol=24)
    B = (np.abs(X - X[0:1]) > 24).astype(np.float32)
    bv = B.var(axis=0)
    bm = bv > 0
    rb = _lag1_r1(B[:, bm])
    rb = rb[~np.isnan(rb)]
    mean_r1_bin = float(rb.mean()) if rb.size else None

    out.update({
        "mean_lag1_autocorr": round(mean_r1, 4),
        "median_lag1_autocorr": round(float(np.median(r)), 4),
        "p10_lag1_autocorr": round(float(np.percentile(r, 10)), 4),
        "p90_lag1_autocorr": round(float(np.percentile(r, 90)), 4),
        "mean_lag1_autocorr_binary": (round(mean_r1_bin, 4)
                                    if mean_r1_bin is not None else None),
        "n_series": int(r.size),
    })

    if mean_r1 < coh_lo:
        out["verdict"] = "uncorrelated_motion"
        out["reading"] = ("animated pixels show ~zero/negative frame-to-frame "
                          "autocorrelation — consistent with unseeded/"
                          "random motion (white-noise-like); eased animation "
                          "is correlated")
    elif mean_r1 > coh_hi:
        out["verdict"] = "correlated_motion"
        out["reading"] = ("animated pixels are frame-to-frame predictable — "
                          "consistent with eased/continuous animation")
    else:
        out["verdict"] = "ambiguous"
        out["reading"] = ("autocorrelation near zero — cannot separate erratic "
                          "from eased motion at this frame count")

    caveats = []
    if n < 10:
        caveats.append(f"only {n} frames ({n - 1} lag-1 pairs per pixel); "
                       "the eval VERDICT notes >=10 frames wanted for a "
                       "stable estimate — treat as directional.")
    caveats.append("Luminance-only channel: hue swaps at constant "
                   "luminance are invisible.")
    out["caveat"] = " ".join(caveats)
    return out


def pairs_bbox_norm(pairs: list[dict], pad: float = 0.0) -> list[int]:
    """Union of per-pair diff_bboxes in normalized [0,1000] coords,
    optionally padded (same pad the pixel region used)."""
    xs0, ys0, xs1, ys1 = 1000, 1000, 0, 0
    for p in pairs:
        bb = (p.get("pixel") or {}).get("diff_bbox")
        if bb:
            xs0, ys0 = min(xs0, bb[0]), min(ys0, bb[1])
            xs1, ys1 = max(xs1, bb[2]), max(ys1, bb[3])
    return [int(max(0, xs0 - pad)), int(max(0, ys0 - pad)),
            int(min(1000, xs1 + pad)), int(min(1000, ys1 + pad))]


# ------------------------------------------------------------------ main --

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


def detect(report: dict, json_path: str | None, min_transitions: int,
           max_run: int, do_motion: bool, coh_lo: float, coh_hi: float
           ) -> dict:
    frames_detail = report.get("frames_detail") or []

    has_records = bool(report.get("with_records", True)) and any(
        fd.get("text") or fd.get("objects") for fd in frames_detail)

    if not has_records:
        # strobe half needs frames_detail; motion coherence only needs
        # pairs + frame files, so it can still run on --no-records reels.
        out = {
            "verdict": "no_record_data",
            "summary": "reel was produced with --no-records (or records "
                       "empty): strobe detection needs frames_detail "
                       "objects/text. Re-run `eyes reel` without "
                       "--no-records.",
            "strobes": [], "alternating_elements": [],
        }
        if do_motion:
            out["motion_coherence"] = motion_coherence(
                report, json_path=json_path, coh_lo=coh_lo, coh_hi=coh_hi)
        return out

    strobes, alternating, stats = find_strobes(
        frames_detail, min_transitions, max_run)

    if strobes:
        verdict = "strobe_detected"
        named = "; ".join(
            f"{s['element']!r} ({s['channel']}) present "
            f"{s['present_frames']} absent {s['absent_frames']}"
            for s in strobes)
        summary = (f"{len(strobes)} element(s) strobe every frame: {named}. "
                   "Strict on/off alternation — hard flicker, not a pulse.")
    elif alternating:
        verdict = "alternating_only"
        summary = (f"{len(alternating)} element(s) alternate >= "
                   f"{min_transitions} times but hold runs >{max_run} — "
                   "partial flicker/duty-cycle blink, not strict strobe. "
                   "See alternating_elements.")
    else:
        verdict = "no_strobe"
        summary = ("No element strobes: nothing alternates presence on every "
                   f"frame (>= {min_transitions} transitions with max run "
                   f"<={max_run} required).")

    out = {
        "verdict": verdict,
        "summary": summary,
        "params": {"min_transitions": min_transitions, "max_run": max_run,
                   "coherence_band": [coh_lo, coh_hi]},
        "stats": stats,
        "strobes": strobes,
        "alternating_elements": alternating,
    }
    if stats["frames"] < min_transitions + 1:
        out["caveat"] = (f"only {stats['frames']} frames — max possible "
                         f"transitions is frames-1={stats['frames'] - 1} "
                         f"< {min_transitions}; 'no_strobe' means "
                         "'no evidence', not 'verified clean'")

    if do_motion:
        out["motion_coherence"] = motion_coherence(
            report, json_path=json_path, coh_lo=coh_lo, coh_hi=coh_hi)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Strobe/flicker detection + motion-coherence "
                    "characterization over `eyes reel --json` output.")
    ap.add_argument("reel_json", nargs="?",
                    help="path to saved `eyes reel --json` output")
    ap.add_argument("--reel", nargs="+", metavar="INPUT",
                    help="instead of a JSON file, run `eyes reel INPUT... "
                         "--json` (files and/or directories)")
    ap.add_argument("--min-transitions", type=int, default=3,
                    help="min present/absent transitions to call alternation "
                         "(default 3 — needs >=4 frames)")
    ap.add_argument("--max-run", type=int, default=1,
                    help="max consecutive same-state frames for a strict "
                         "strobe (default 1 = alternates every frame)")
    ap.add_argument("--no-motion", action="store_true",
                    help="skip the motion-coherence image analysis")
    ap.add_argument("--coh-lo", type=float, default=-0.10,
                    help="mean lag-1 autocorr below this = uncorrelated "
                         "motion (default -0.10)")
    ap.add_argument("--coh-hi", type=float, default=0.10,
                    help="mean lag-1 autocorr above this = correlated "
                         "motion (default 0.10)")
    args = ap.parse_args(argv)

    json_path = None
    if args.reel:
        report = run_reel(args.reel)
        source = " ".join(args.reel)
    elif args.reel_json:
        json_path = str(Path(args.reel_json))
        report = json.loads(Path(args.reel_json).read_text())
        source = args.reel_json
    else:
        ap.error("give a reel JSON path or --reel INPUT...")

    out = detect(report, json_path, args.min_transitions, args.max_run,
                 do_motion=not args.no_motion,
                 coh_lo=args.coh_lo, coh_hi=args.coh_hi)
    out["source"] = source
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
