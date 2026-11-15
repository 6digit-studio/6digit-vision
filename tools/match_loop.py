#!/usr/bin/env python3
"""match_loop — the PRD's closed loop, runnable.

reference design -> candidate render -> eyes score + ask-pack evidence ->
critic emits ONE targeted edit -> apply -> repeat. Trace = JSONL + table.

Critic backends:
  --critic agent    pack written to --pack-dir; loop pauses for an edit
                    JSON file (--edit-file) — a real model (the agent
                    running this) reads the pack and answers. Honest
                    label: agent-in-loop, not automated.
  --critic needle   Cactus Needle tool-call attempt (documented
                    unreliable for this — see loop/NEEDLE.md notes in
                    VERDICT if used).

Candidates are PROGRAMMATIC parametric edits of a PIL-drawn UI — honest
synthetic candidates, not generated designs. The loop proves mechanics:
evidence -> critique -> targeted edit -> measurable score delta.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

W, H = 640, 400

# canonical reference params — the "design"
REF = {
    "title_y": 56, "accent": (37, 99, 235), "chip_gap": 18,
    "button_color": (37, 99, 235), "radius": 10, "subtitle_y": 92,
}

PALETTE = {
    "blue": (37, 99, 235), "green": (22, 163, 74), "red": (220, 38, 38),
    "violet": (124, 58, 237), "orange": (234, 88, 12), "teal": (13, 148, 136),
}
COLOR_PARAMS = {"accent", "button_color"}


def render(params: dict, path: Path) -> None:
    img = Image.new("RGB", (W, H), (248, 250, 252))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=params["accent"])
    d.text((32, params["title_y"]), "Quarterly Report", fill=(17, 24, 39))
    d.text((32, params["subtitle_y"]), "Revenue overview — Q3", fill=(107, 114, 128))
    x = 32
    for i, (label, val) in enumerate([("Revenue", "$1.2M"), ("Users", "48k"), ("NPS", "+62")]):
        d.rounded_rectangle([x, 150, x + 170, 210], radius=params["radius"],
                            fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        d.text((x + 14, 162), label, fill=(107, 114, 128))
        d.text((x + 14, 184), val, fill=(17, 24, 39))
        x += 170 + params["chip_gap"]
    d.rounded_rectangle([32, 250, 220, 296], radius=params["radius"],
                        fill=params["button_color"])
    d.text((70, 264), "View details", fill=(255, 255, 255))
    img.save(path)


def score_candidate(ref_rec, ref_pal, ref_size, cand_path, workdir) -> dict:
    from eyes import color, mirage, score
    cand_rec = mirage.describe(str(cand_path))
    cand_pal = color.palette(str(cand_path))
    return score.score_pair(
        ref_rec, cand_rec, ref_pal=ref_pal, cand_pal=cand_pal,
        ref_size=ref_size, cand_size=(W, H))


def build_ask_pack(cand_path: Path, question: str) -> dict:
    """Compact evidence pack for the critic — score summary + top
    detector findings, not the full describe dump."""
    from eyes import ask
    pack = ask.evidence_pack(str(cand_path), question=question)
    det = pack.get("detectors") or {}
    slim = {k: v for k, v in det.items() if v}
    return {
        "question": question,
        "objects": pack.get("objects"),
        "text": pack.get("text"),
        "findings": pack.get("findings"),
        "detectors": slim,
    }


def apply_edit(params: dict, edit: dict) -> dict:
    out = dict(params)
    p = edit.get("param")
    if p in COLOR_PARAMS:
        name = edit.get("value") or edit.get("delta")
        if name in PALETTE:
            out[p] = PALETTE[name]
        elif isinstance(name, str) and name.startswith("#"):
            out[p] = tuple(int(name[i:i + 2], 16) for i in (1, 3, 5))
    elif p in out:
        delta = edit.get("delta", 0)
        out[p] = out[p] + int(delta)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--critic", choices=["agent", "needle"], default="agent")
    ap.add_argument("--iters", type=int, default=6)
    ap.add_argument("--workdir", default="loop_runs/latest")
    ap.add_argument("--edit-file", default=None,
                    help="agent critic: path the loop watches for edit JSON")
    args = ap.parse_args()

    work = ROOT / args.workdir
    work.mkdir(parents=True, exist_ok=True)
    trace_path = work / "trace.jsonl"

    ref_path = work / "reference.png"
    render(REF, ref_path)

    from eyes import color, mirage
    ref_rec = mirage.describe(str(ref_path))
    ref_pal = color.palette(str(ref_path))
    ref_size = (W, H)

    # starting candidate: perturbed params (the "first generation")
    params = dict(REF)
    params.update({"title_y": 86, "accent": PALETTE["red"],
                   "chip_gap": 34, "button_color": PALETTE["violet"],
                   "radius": 4, "subtitle_y": 78})

    trace = open(trace_path, "a")
    print(f"{'iter':>4} {'score':>7} {'edit':<38} {'reason'}")
    best = {"score": -1, "params": None}

    for it in range(args.iters + 1):
        cand = work / f"cand_{it:02d}.png"
        render(params, cand)
        t0 = time.time()
        res = score_candidate(ref_rec, ref_pal, ref_size, cand, work)
        dt = time.time() - t0
        comp = {k: round(v["score"], 3) for k, v in res["components"].items()}
        rec = {"iter": it, "score": res["score"], "components": comp,
               "params": {k: (list(v) if isinstance(v, tuple) else v)
                          for k, v in params.items()},
               "ms": round(dt * 1000)}
        trace.write(json.dumps(rec) + "\n")
        print(f"{it:>4} {res['score']:>7.1f} {'(render)':<38} "
              f"{comp}")

        if res["score"] > best["score"]:
            best = {"score": res["score"], "params": dict(params)}

        if it == args.iters:
            break

        # --- critic step ---
        pack = build_ask_pack(
            cand, "List the concrete visual differences vs the reference "
                  "design and the single most impactful fix.")
        pack_path = work / f"pack_{it:02d}.json"
        pack_path.write_text(json.dumps(pack, indent=2, default=str))

        if args.critic == "agent":
            edit_path = Path(args.edit_file or (work / "edit.json"))
            if edit_path.exists():
                edit_path.unlink()
            print(f"  pack -> {pack_path}")
            print(f"  awaiting critic edit at {edit_path} ...")
            deadline = time.time() + 600
            while not edit_path.exists() and time.time() < deadline:
                time.sleep(1)
            if not edit_path.exists():
                print("  critic timeout — stopping")
                break
            edit = json.loads(edit_path.read_text())
        else:
            edit = {"param": "title_y", "delta": -30,
                    "reason": "needle critic unavailable — noop"}
            break

        rec["edit"] = edit
        trace.write(json.dumps({"iter": it, "critic_edit": edit}) + "\n")
        trace.flush()
        print(f"       critic: {edit.get('param')} "
              f"{edit.get('delta', edit.get('value',''))} — "
              f"{edit.get('reason','')[:60]}")
        params = apply_edit(params, edit)

    print(f"\nbest score {best['score']:.1f} at iter "
          f"{max(0, args.iters)}; trace -> {trace_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
