# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""accent-hue census — single-image detector for theme-token splits.

Fills the gap named in evals/theme-drift/VERDICT.md: `eyes score` reports
that two states differ but nothing names *hue*, and Mirage describes the
violet state's UI as "blue". This detector needs no reference image:

    RGB -> HSV (PIL) -> mask S>0.35 & V>0.35 -> 15-degree hue histogram
    -> circular contiguous-bin families -> significance filter ->
    >=2 significant families == candidate accent-hue split.

A "family" is a maximal circular run of populated hue bins. It is
significant when it covers >= --min-family-share of saturated pixels AND
>= --rel-to-dominant of the dominant family's share. The relative floor
is what keeps semantic micro-accents (a green +12.4% delta at ~2.4% of
saturated px) from being reported as theme families — the literal
">0.5% of saturated area" rule from the eval sketch false-positives on
exactly that bin in state-a.png.

Usage (from repo root):
    uv run detectors/hue-census/hue_census.py IMAGE [IMAGE ...]
    uv run detectors/hue-census/hue_census.py --json evals/theme-drift/state-b.png
    uv run detectors/hue-census/hue_census.py --fail-on-split *.png   # CI mode

Exit code is 0 unless --fail-on-split is given and any image splits.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# ------------------------------------------------------------------ tunables

S_MIN = 0.35          # saturation floor for "chromatic" pixels
V_MIN = 0.35          # value floor — drops near-black noise
BIN_DEG = 15.0        # hue histogram resolution (360 / 15 = 24 bins)
MIN_BIN_PX = 8        # a bin needs at least this many px to be "present"
MIN_BIN_SHARE = 0.0005  # ...or this fraction of saturated px, whichever is larger
MIN_SATURATED_PX = 256  # below this the census is declared unreliable
MIN_FAMILY_SHARE = 0.01   # family must cover >=1% of saturated px
REL_TO_DOMINANT = 0.10    # ...and >=10% of the dominant family's share
X_PROFILE_BINS = 10       # column histogram resolution for spatial report

# hue (deg) -> common name; nearest anchor wins, ties break toward the
# earlier (warmer) anchor. Tuned so tailwind blue-600 (#2563eb, h~221)
# names "blue" and violet-600 (#7c3aed, h~262) names "violet" — the exact
# pair Mirage conflates.
HUE_NAMES = [
    (0.0, "red"), (25.0, "orange"), (48.0, "amber"), (62.0, "yellow"),
    (85.0, "lime"), (135.0, "green"), (168.0, "teal"), (190.0, "cyan"),
    (208.0, "azure"), (228.0, "blue"), (248.0, "indigo"), (270.0, "violet"),
    (292.0, "purple"), (315.0, "magenta"), (340.0, "pink"),
]


def hue_name(deg: float) -> str:
    """Nearest anchor by circular distance."""
    best, best_d = HUE_NAMES[0][1], 360.0
    for anchor, name in HUE_NAMES:
        d = abs((deg - anchor + 180.0) % 360.0 - 180.0)
        if d < best_d:
            best, best_d = name, d
    return best


def circular_mean_deg(angles_deg: np.ndarray, weights: np.ndarray) -> float:
    """Weighted circular mean; correct across the 0/360 wrap."""
    rad = np.deg2rad(angles_deg)
    z = (weights * np.exp(1j * rad)).sum()
    if abs(z) < 1e-9:
        return float("nan")
    return float(np.rad2deg(np.angle(z)) % 360.0)


def census(path: str | Path, args: argparse.Namespace) -> dict:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    n_px = w * h

    # PIL's HSV: H,S,V each 0..255, H wraps 0..360.
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32) / 255.0
    hue = hsv[..., 0] * 360.0
    sat = hsv[..., 1]
    val = hsv[..., 2]

    mask = (sat > args.s_min) & (val > args.v_min)
    n_sat = int(mask.sum())

    result = {
        "image": str(path),
        "size": [w, h],
        "saturated_px": n_sat,
        "saturated_pct_of_image": round(100.0 * n_sat / n_px, 3),
        "mask": {"s_min": args.s_min, "v_min": args.v_min,
                 "bin_deg": args.bin_deg},
        "thresholds": {
            "min_family_share": args.min_family_share,
            "rel_to_dominant": args.rel_to_dominant,
        },
        "families": [],
        "significant_families": 0,
        "verdict": None,
        "notes": [],
    }

    if n_sat < args.min_saturated_px:
        result["verdict"] = "insufficient_chroma"
        result["notes"].append(
            f"only {n_sat} saturated px (< {args.min_saturated_px}); "
            "census unreliable — image is effectively grayscale")
        return result

    n_bins = int(round(360.0 / args.bin_deg))
    hue_masked = hue[mask]                       # 1-D, aligned with bin_idx
    bin_idx = (hue_masked / args.bin_deg).astype(np.int64) % n_bins
    counts = np.bincount(bin_idx, minlength=n_bins).astype(np.int64)

    # A bin is "present" above an absolute+relative floor so JPEG noise /
    # dither specks cannot seed phantom families.
    bin_floor = max(MIN_BIN_PX, int(math.ceil(MIN_BIN_SHARE * n_sat)))
    present = counts >= bin_floor

    # Maximal circular runs of present bins -> candidate families.
    # Rotate so we start just after an absent bin (guaranteed unless all
    # bins are present, which collapses to one family anyway).
    if present.all():
        runs = [list(range(n_bins))]
    else:
        gap = int(np.argmin(present.astype(np.int64)))  # an absent bin
        order = [(gap + 1 + i) % n_bins for i in range(n_bins)]
        runs, cur = [], []
        for b in order:
            if present[b]:
                cur.append(b)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)

    # coordinates of masked pixels, in the same row-major order as bin_idx
    ys, xs = np.nonzero(mask)

    families = []
    for run in runs:
        n_fam = int(counts[run].sum())
        share = n_fam / n_sat
        span = len(run) * args.bin_deg  # bins are contiguous by construction
        # spatial extent of this family's pixels: bin_idx[i] is the hue bin
        # of masked pixel (ys[i], xs[i])
        sel = np.isin(bin_idx, run)
        # family center = circular mean of member *pixels'* hues (not bin
        # centers) — a single-bin family still reports its true mean hue
        mean_hue = circular_mean_deg(hue_masked[sel],
                                     np.ones(int(sel.sum())))
        fam_ys = ys[sel]
        fam_xs = xs[sel]
        x0, x1 = int(fam_xs.min()), int(fam_xs.max())
        y0, y1 = int(fam_ys.min()), int(fam_ys.max())
        # column profile: fraction of family px per image tenth
        edges = np.linspace(0, w, X_PROFILE_BINS + 1)
        prof, _ = np.histogram(fam_xs, bins=edges)
        x_profile = [round(float(c) / n_fam, 4) for c in prof]
        families.append({
            "hue_center_deg": round(mean_hue, 1) if not math.isnan(mean_hue)
                              else None,
            # nan only if member hues perfectly cancel around the wheel —
            # report honestly rather than mislabel as the first anchor
            "hue_name": (hue_name(mean_hue)
                         if not math.isnan(mean_hue) else None),
            "hue_span_deg": span,
            "pixel_count": n_fam,
            "share_of_saturated": round(share, 4),
            "share_pct": round(100.0 * share, 2),
            "bbox": [x0, y0, x1, y1],
            "x_profile": x_profile,
        })

    families.sort(key=lambda f: -f["pixel_count"])
    dominant_share = families[0]["share_of_saturated"] if families else 0.0

    for f in families:
        f["significant"] = bool(
            f["share_of_saturated"] >= args.min_family_share
            and f["share_of_saturated"] >= args.rel_to_dominant * dominant_share
        )

    sig = [f for f in families if f["significant"]]
    result["families"] = families
    result["significant_families"] = len(sig)
    result["dominant_family"] = sig[0]["hue_name"] if sig else None

    if len(sig) >= 2:
        result["verdict"] = "accent_hue_split"
        names = " + ".join(f"{f['hue_name'] or '?'}({f['share_pct']}%)"
                           for f in sig)
        result["notes"].append(
            f"{len(sig)} hue families over significance floors: {names}. "
            "Candidate theme-token split — e.g. shared chrome on one accent "
            "and regenerated content on another. Check family bboxes/"
            "x_profiles for chrome-vs-content segregation.")
    elif len(sig) == 1:
        result["verdict"] = "single_accent_family"
        result["notes"].append(
            f"one significant family: {sig[0]['hue_name']} "
            f"({sig[0]['share_pct']}% of saturated px)")
    else:
        result["verdict"] = "no_significant_family"
        result["notes"].append(
            "saturated pixels exist but no hue family clears the "
            "significance floors — diffuse/low-chroma content")
    return result


def fmt_family(f: dict) -> str:
    x0, y0, x1, y1 = f["bbox"]
    flag = "" if f["significant"] else "  (below floors)"
    name = f["hue_name"] or "?"
    center = (f"{f['hue_center_deg']:>6.1f}°" if f["hue_center_deg"] is not None
              else "   n/a ")
    return (f"    {name:<8} hue~{center} "
            f"span {f['hue_span_deg']:>5.1f}°  {f['share_pct']:>6.2f}% of "
            f"saturated  n={f['pixel_count']:<6} "
            f"bbox=({x0},{y0})-({x1},{y1}){flag}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Accent-hue census: flag images whose saturated pixels "
                    "split into >=2 hue families (theme-token drift).")
    p.add_argument("images", nargs="+", help="image path(s)")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--s-min", type=float, default=S_MIN)
    p.add_argument("--v-min", type=float, default=V_MIN)
    p.add_argument("--bin-deg", type=float, default=BIN_DEG,
                   help="hue bin width in degrees (must divide 360)")
    p.add_argument("--min-family-share", type=float, default=MIN_FAMILY_SHARE,
                   help="min share of saturated px for a family")
    p.add_argument("--rel-to-dominant", type=float, default=REL_TO_DOMINANT,
                   help="min share relative to dominant family")
    p.add_argument("--min-saturated-px", type=int, default=MIN_SATURATED_PX)
    p.add_argument("--fail-on-split", action="store_true",
                   help="exit 1 if any image verdict is accent_hue_split")
    args = p.parse_args(argv)

    if args.bin_deg <= 0 or 360.0 % args.bin_deg != 0:
        p.error("--bin-deg must be positive and divide 360 evenly")

    results = []
    any_split = False
    for path in args.images:
        try:
            r = census(path, args)
        except Exception as e:  # unreadable file etc — report, don't crash batch
            r = {"image": str(path), "verdict": "error", "notes": [str(e)]}
        results.append(r)
        any_split |= r.get("verdict") == "accent_hue_split"

    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        for r in results:
            if r.get("verdict") == "error":
                print(f"{r['image']}: ERROR {r['notes'][0]}")
                continue
            w, h = r["size"]
            print(f"{r['image']}  {w}x{h}  "
                  f"saturated={r['saturated_px']} "
                  f"({r['saturated_pct_of_image']}% of px)")
            for f in r["families"]:
                print(fmt_family(f))
            verdict = r["verdict"].upper()
            print(f"  VERDICT: {verdict} — {'; '.join(r['notes'])}")
            print()

    return 1 if (args.fail_on_split and any_split) else 0


if __name__ == "__main__":
    sys.exit(main())
