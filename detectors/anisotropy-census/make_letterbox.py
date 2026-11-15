# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Rebuild the aspect-abuse eval's letterboxed control variant.

evals/aspect-abuse/VERDICT.md's confound probe: the SAME 1200x675 source
contain-fit into the SAME 1000x1000 canvas the defect uses — uniform
scale (1000x562), 219px page-background bars top/bottom. This is what
the agent *should* have shipped at that canvas size. The eval built it
at /tmp/ab_letterbox.png (ephemeral); this script regenerates it
deterministically so the anisotropy-census control is reproducible.

The bars use APP_BG (238,241,245) — the source's own page background —
matching the eval probe exactly.

Run from repo root:
    uv run detectors/anisotropy-census/make_letterbox.py
"""

from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent / "evals" / "aspect-abuse" / "control.png"
OUT = HERE / "letterbox-1000.png"

CANVAS = 1000
APP_BG = (238, 241, 245)  # same page background as make_images.py


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    sw, sh = src.size
    scale = min(CANVAS / sw, CANVAS / sh)
    fw, fh = round(sw * scale), round(sh * scale)
    fitted = src.resize((fw, fh), Image.BILINEAR)
    canvas = Image.new("RGB", (CANVAS, CANVAS), APP_BG)
    canvas.paste(fitted, ((CANVAS - fw) // 2, (CANVAS - fh) // 2))
    canvas.save(OUT)
    print(f"{OUT}: canvas={CANVAS}x{CANVAS} fitted={fw}x{fh} "
          f"scale={scale:.4f} bars={(CANVAS - fh) // 2}px top/bottom")


if __name__ == "__main__":
    main()
