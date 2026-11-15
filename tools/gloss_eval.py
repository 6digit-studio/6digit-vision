#!/usr/bin/env python3
"""gloss_eval — 20-crop eval: real diff regions -> local VLM descriptions.

Pulls regions from ui_loop packs (pixdiff+fdiff), glosses each crop,
saves raw descriptions + region metadata for grading."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eyes.gloss import gloss

ROOT = Path(__file__).resolve().parents[1]
RUNS = [
    ("ui1", "evals/web-real/corpus/github_com_login.png",
     "loop_runs/ui1/candidate.png", "loop_runs/ui1/pack_10.json"),
    ("ui2", "Screenshot 2026-11-15 at 03.00.39.png",
     "loop_runs/ui2/candidate.png", "loop_runs/ui2/pack_02.json"),
    ("ui3", "Screenshot 2026-11-15 at 03.00.47.png",
     "loop_runs/ui3/candidate.png", "loop_runs/ui3/pack_04.json"),
]

def regions_from_pack(pack_path):
    p = json.loads(Path(pack_path).read_text())
    regs = []
    for src in ("pixdiff", "fdiff"):
        for r in ((p.get(src) or {}).get("regions") or [])[:4]:
            regs.append({"src": src, "bbox_px": r["bbox_px"],
                         "area_frac": r.get("area_frac")})
    # dedupe near-identical bboxes
    out, seen = [], []
    for r in regs:
        b = r["bbox_px"]
        if any(abs(b[0]-s[0])<15 and abs(b[1]-s[1])<15 for s in seen):
            continue
        seen.append(b); out.append(r)
    return out[:7]

def main():
    results = []
    for name, ref, cand, pack in RUNS:
        regs = regions_from_pack(str(ROOT/pack))
        img = str(ROOT/ref)  # gloss the REFERENCE region (what should exist)
        for i, r in enumerate(regs):
            bbox = r["bbox_px"]  # already px on common canvas
            g = gloss(img, bbox)
            results.append({"run": name, "src": r["src"], "bbox": bbox,
                            "area_frac": r["area_frac"], **g})
            print(f"[{name}:{i}] {r['src']} {bbox} -> "
                  f"{'OK' if g.get('description') else 'ERR'}", flush=True)
    Path(ROOT/"loop_runs/gloss_eval.json").write_text(
        json.dumps(results, indent=2))
    print(f"\n{len(results)} crops -> loop_runs/gloss_eval.json")

if __name__ == "__main__":
    main()
