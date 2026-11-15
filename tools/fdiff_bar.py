#!/usr/bin/env python3
"""fdiff_bar — shared falsifiable bar for fdiff contestants.

Usage: uv run python3 tools/fdiff_bar.py fdiff/<slug>/fdiff.py
Runs the 5-criterion bar and prints a table. Each contestant module
must expose fdiff(a_path, b_path) -> {"score","regions","notes"}.
"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def load_mod(path):
    spec = importlib.util.spec_from_file_location("fdiff_mod", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def mk_shifted():
    """Planted 20px block shift on ui1 candidate."""
    out = ROOT / "/tmp/fdiff_shifted.png"
    img = Image.open(ROOT / "loop_runs/ui1/candidate.png").convert("RGB")
    a = np.asarray(img); b = a.copy()
    b[300:420, 380:780] = a[300:420, 360:760]
    Image.fromarray(b).save(out)
    return str(out)

def mk_translate():
    """1px global translation of ui1 candidate."""
    out = ROOT / "/tmp/fdiff_translated.png"
    img = Image.open(ROOT / "loop_runs/ui1/candidate.png").convert("RGB")
    a = np.asarray(img); b = np.roll(a, 1, axis=1)
    b[:, 0] = a[:, -1]
    Image.fromarray(b).save(out)
    return str(out)

def region_count(r):
    regs = r.get("regions") or []
    if isinstance(regs, dict):
        regs = regs.get("regions") or []
    return len(regs)

def main():
    path = sys.argv[1]
    m = load_mod(path)
    ref = str(ROOT / "evals/web-real/corpus/github_com_login.png")
    cand = str(ROOT / "loop_runs/ui1/candidate.png")
    shifted = mk_shifted()
    translated = mk_translate()

    rows = []
    # 1. identical
    r = m.fdiff(cand, cand)
    rows.append(("identical->~1.0", r.get("score"), region_count(r)))
    # 2. planted block shift
    r = m.fdiff(cand, shifted)
    rows.append(("block-shift->localized", r.get("score"), region_count(r)))
    # 3. 1px global translation
    r = m.fdiff(cand, translated)
    rows.append(("1px-translate->low-diff", r.get("score"), region_count(r)))
    # 4. dense-text noise: two near-identical corpus pages? use control pair
    r = m.fdiff(str(ROOT / "evals/web-breakpoint/control.png"),
                str(ROOT / "evals/web-breakpoint/control.png"))
    rows.append(("same-img sanity", r.get("score"), region_count(r)))
    # 5. ui1 pair
    r = m.fdiff(ref, cand)
    rows.append(("ui1-pair signal", r.get("score"), region_count(r)))

    print(f"{'criterion':<26} {'score':>8} {'regions':>8}")
    for name, s, n in rows:
        print(f"{name:<26} {str(s):>8} {n:>8}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
