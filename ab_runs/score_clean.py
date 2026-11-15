#!/usr/bin/env python3
"""Score the clean isolation pair (A2/B2) -> clean_results.json."""
import json, subprocess, pathlib
import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent

def eyes(*args):
    p = subprocess.run(["eyes", *args], capture_output=True, text=True)
    return json.loads(p.stdout)

rows = []
for slug in ["ref1-collage", "ref3-bp"]:
    ref = ROOT / "A" / slug / "reference.png"
    for arm in ["A2", "B2"]:
        cand = ROOT / arm / slug / "candidate.png"
        if not cand.exists():
            continue
        pd = eyes("pixdiff", str(ref), str(cand), "--json")
        sc = eyes("score", str(ref), str(cand), "--json")
        a = np.asarray(Image.open(ref).convert("RGB"), dtype=np.float32)
        b = np.asarray(Image.open(cand).convert("RGB"), dtype=np.float32)
        rows.append({
            "ref": slug, "arm": arm,
            "ssim": round(pd["ssim_mean"], 4),
            "mismatch": round(pd["mismatch_frac"], 4),
            "rmse": round(float(np.sqrt(((a - b) ** 2).mean()) / 255), 4),
            "score": sc["score"],
        })
(ROOT / "clean_results.json").write_text(json.dumps(rows, indent=2) + "\n")
for r in rows:
    print(r)
