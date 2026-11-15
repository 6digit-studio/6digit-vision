#!/usr/bin/env python3
"""Build the smooth-motion CONTROL reel for chaotic-motion.

Identical scene to frame_01..06.png, but the voice-activity subsystem
behaves: the active speaker dwells two frames per turn, waveform bars
follow smooth sinusoidal paths (small per-frame deltas, high
frame-to-frame correlation), and the LIVE pill stays on (smooth live
indicators don't strobe). Everything else — layout, copy, colors,
static regions — is pixel-identical to the defect reel.

This is the confound probe: if the instrument's signals (flat pixel
diffs, labels churn, OCR unmatched) look the same on smooth motion,
they cannot be attributed to chaotic motion.

Run from repo root:  uv run --with pillow python3 evals/chaotic-motion/build_control.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_frames as bf  # noqa: E402

OUT = Path(__file__).resolve().parent / "control-smooth"
OUT.mkdir(exist_ok=True)

# dwell-2 speaker turns; smooth periodic waveform; pill always on
bf.SPEAKERS = [0, 0, 3, 3, 2, 2]
bf.PILL_ON = [True] * 6
bf.WAVE = [
    [round(8 + 5 * math.sin(2 * math.pi * (f * 0.18 + b * 0.11)))
     for b in range(9)]
    for f in range(6)
]


def main() -> None:
    for i in range(6):
        p = OUT / f"frame_{i + 1:02d}.png"
        bf.draw_frame(i, p)
        print(f"{p.name}  speaker={bf.PARTICIPANTS[bf.SPEAKERS[i]][0]:<12} "
              f"pill=on   wave={bf.WAVE[i]}")


if __name__ == "__main__":
    main()
