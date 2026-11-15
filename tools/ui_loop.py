#!/usr/bin/env python3
"""ui_loop — HTML/CSS reproduction loop against a reference screenshot.

The real test of the product claim: screenshot -> working UI
approximation -> measurable convergence. Candidate source is an HTML
file rendered through headless Chrome (same CDP path as the web-real
corpus) — REAL browser rendering, not PIL stand-ins.

Each run: render candidate.html -> PNG, eyes score ref-vs-cand,
eyes diff element-level changes, eyes ask evidence pack. Appends one
JSONL trace row + writes pack_NN.json for the critic to read.

The critic is the agent in the loop (same honest pattern as
tools/match_loop.py): it reads the pack and edits candidate.html —
one targeted change per iteration, prefer editing over regenerating.

Usage:
  uv run python3 tools/ui_loop.py loop_runs/ui1 \
      --ref evals/web-real/corpus/github_com_login.png \
      --html loop_runs/ui1/candidate.html
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render(html_path: Path, out_png: Path, w: int = 1200, h: int = 800) -> None:
    """Headless Chrome screenshot — real browser rendering."""
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu",
         f"--screenshot={out_png}",
         f"--window-size={w},{h}", "--hide-scrollbars",
         f"file://{html_path.resolve()}"],
        check=True, capture_output=True, timeout=60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--html", required=True)
    ap.add_argument("--iter", type=int, default=None,
                    help="iteration number (default: next in trace)")
    args = ap.parse_args()

    run = Path(args.run_dir)
    run.mkdir(parents=True, exist_ok=True)
    ref = Path(args.ref)
    html = Path(args.html)
    cand_png = run / "candidate.png"

    render(html, cand_png)

    from eyes import mirage, score, scene_tree, ask, color
    from PIL import Image

    ref_rec = mirage.describe(str(ref))
    cand_rec = mirage.describe(str(cand_png))
    rw, rh = Image.open(str(ref)).size
    cw, ch = Image.open(str(cand_png)).size
    scores = score.score_pair(
        ref_rec, cand_rec,
        ref_pal=color.palette(str(ref)),
        cand_pal=color.palette(str(cand_png)),
        ref_size=(rw, rh), cand_size=(cw, ch))
    diff = scene_tree.diff_records(ref_rec, cand_rec)
    pack = ask.evidence_pack(str(cand_png),
                             question="what differs from the reference UI?")
    pack["element_diff"] = diff
    pack["score"] = scores

    trace = run / "trace.jsonl"
    it = args.iter
    if it is None:
        it = (sum(1 for _ in trace.open()) if trace.exists() else 0)
    pack_path = run / f"pack_{it:02d}.json"
    pack_path.write_text(json.dumps(pack, indent=2, default=str))

    row = {
        "iter": it, "ts": time.strftime("%H:%M:%S"),
        "score": scores.get("total") or scores.get("score"),
        "components": scores.get("components"),
        "diff_changes": len(diff.get("changes") or []),
        "pack": str(pack_path.name),
    }
    with trace.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
