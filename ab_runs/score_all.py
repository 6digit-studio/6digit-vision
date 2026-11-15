#!/usr/bin/env python3
"""Score every arm cell: eyes score (semantic), pixdiff (SSIM/pixel), full-res RMSE,
plus the arm's own self-estimate from VERDICT.md. Writes results.json + results.md."""
import json, re, subprocess, pathlib
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
REFS = ["ref1-collage", "ref2-knob", "ref3-bp", "ref4-flight"]
ARMS = [a for a in ["A", "B", "C", "D"] if (ROOT / a).exists()]

def eyes(*args):
    p = subprocess.run(["eyes", *args], capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"error": (p.stderr or p.stdout)[:300]}

def rmse(ref, cand):
    a = np.asarray(Image.open(ref).convert("RGB"), dtype=np.float32)
    b = np.asarray(Image.open(cand).convert("RGB"), dtype=np.float32)
    if a.shape != b.shape:
        b = np.asarray(Image.open(cand).convert("RGB").resize(
            (a.shape[1], a.shape[0]), Image.BILINEAR), dtype=np.float32)
    return float(np.sqrt(((a - b) ** 2).mean()) / 255.0)

def self_est(d):
    p = d / "VERDICT.md"
    if not p.exists():
        return None
    m = re.search(r"##\s*Self-estimate.*?\n+\s*(\d+)", p.read_text(), re.S | re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{1,2})\s*/\s*10\b", p.read_text())
    return int(m.group(1)) if m else None

KNOWN_CEILINGS = {"ref1-collage": 93.4, "ref2-knob": 89.6,
                   "ref3-bp": 96.6, "ref4-flight": 96.9}
ceilings = {}
for s in REFS:
    v = eyes("score", str(ROOT / "A" / s / "reference.png"),
             str(ROOT / "A" / s / "reference.png")).get("score")
    ceilings[s] = v if isinstance(v, (int, float)) else KNOWN_CEILINGS[s]

rows = []
for slug in REFS:
    ref = ROOT / "A" / slug / "reference.png"
    for arm in ARMS:
        d = ROOT / arm / slug
        cand = d / "candidate.png"
        if not cand.exists():
            continue
        sc = eyes("score", str(ref), str(cand), "--json")
        pd = eyes("pixdiff", str(ref), str(cand), "--json")
        row = {
            "ref": slug, "arm": arm,
            "score": sc.get("score"), "ceiling": ceilings[slug],
            "norm": (round(sc["score"] / ceilings[slug], 4)
             if isinstance(sc.get("score"), (int, float)) and ceilings[slug] else None),
            "ssim": round(pd.get("ssim_mean", 0), 4),
            "mismatch": round(pd.get("mismatch_frac", 0), 4),
            "rmse": round(rmse(ref, cand), 4),
            "self_estimate": self_est(d),
            "components": {k: (v.get("score") if isinstance(v, dict) else v)
                           for k, v in (sc.get("components") or {}).items()},
            "iterations": len((d / "trace.jsonl").read_text().splitlines())
                          if (d / "trace.jsonl").exists() else None,
        }
        rows.append(row)

(ROOT / "results.json").write_text(json.dumps({"ceilings": ceilings, "rows": rows}, indent=2) + "\n")

# markdown table
lines = ["| ref | arm | SSIM | mismatch | RMSE | score/ceiling | self-est |",
         "|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(f"| {r['ref']} | {r['arm']} | {r['ssim']:.3f} | {r['mismatch']*100:.1f}% | "
                 f"{r['rmse']:.3f} | {r['score']:.1f}/{r['ceiling']:.1f} | "
                 f"{r['self_estimate'] if r['self_estimate'] is not None else '-'} |")
(ROOT / "results.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
