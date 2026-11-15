#!/usr/bin/env python3
"""Build the clean control for lifecycle-diff.

Same "Site Traffic" card as evals/object-dropout, same animation
(ticking count, moving bars, pulsing dot) — but the LIVE badge is
present in ALL five frames. Nothing persistent ever departs, so a
correct lifecycle detector must report `clean` (or at most record-noise
departures, which it should label honestly).

Reuses evals/object-dropout/build_frames.py unmodified via import.

Run from repo root:  uv run python detectors/lifecycle-diff/make_control.py
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "evals" / "object-dropout"))

import build_frames  # noqa: E402  (eval helper, unmodified)

OUT = Path(__file__).resolve().parent / "control-clean"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    # identical states to the defect EXCEPT live=True on every frame
    states = [
        (12847, [0.45, 0.62, 0.50, 0.78, 0.66, 0.90, 0.72], True, 4),
        (12912, [0.50, 0.58, 0.66, 0.72, 0.80, 0.85, 0.68], True, 6),
        (12987, [0.55, 0.70, 0.60, 0.82, 0.75, 0.95, 0.78], True, 5),
        (13044, [0.62, 0.66, 0.74, 0.78, 0.88, 0.90, 0.84], True, 7),
        (13102, [0.58, 0.74, 0.68, 0.86, 0.80, 1.00, 0.90], True, 4),
    ]
    for i, state in enumerate(states, 1):
        build_frames.draw_frame(*state, OUT / f"frame_{i:02d}.png")
    for p in sorted(OUT.glob("*.png")):
        print(f"{p}  {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
