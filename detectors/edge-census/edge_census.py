#!/usr/bin/env python3
"""edge-census — repeated-element edge census over a Mirage record.

Fills the gap named by evals/grid-misalign/VERDICT.md: `eyes` has no
regularity/alignment detector — every shipped detector measures frame
edges, intersections, or legibility, while "elements that should share a
coordinate don't" is a self-consistency check nothing computes. The eval
proved the evidence is already in the record: identical strings in a
repeated column share x-edges in the control ('Active' x0 spread 0) and
ragged in the defect (spread 9, ~10px of pill drift).

Method (zero new model calls — consumes `eyes describe` output only):

  1. Group record["text"] entries by normalized string.
  2. Within each group, sub-cluster members along x (single-linkage,
     gap > XGAP) for the column pass, and along y for the row pass.
     Sub-clustering keeps the same word in two legitimately different
     columns from being compared against each other.
  3. A column cluster only counts if its members span multiple rows
     (y0 spread > ROW_MIN) — identical strings side by side in one row
     have no shared x-edge to violate. A symmetric guard rejects
     clusters whose members collide in y (two columns merged by the
     x-cluster), detected as adjacent y0s closer than ROW_SAME.
  4. Flag when max(x0 spread, x1 spread) > FLOOR. Identical strings
     have identical glyph width, so both edges of a repeated column
     should coincide; either edge spreading is drift. The row pass is
     the transpose (y0/y1 spread).

Calibration (measured, not vibes — see VERDICT.md):
  control.png: max identical-string edge spread = 2 units
  defect.png : planted signals 4..9 units; 'Active' x0 spread = 9
  Mirage describe is deterministic on this box (two runs, identical
  records), so the noise floor is OCR bbox variance on identical
  content, measured <= 2 units on the control. FLOOR defaults to 3.0
  (flag spread > 3.0, i.e. >= 4 on integer bboxes) — midpoint of the
  measured gap, ~1 unit of margin each side.

Deliberately text-only: the eval measured object-name grouping as pure
noise (Mirage relabels 'tab'->'button' wholesale and object boxes are
region-scale, x1 spreads ~860 units inside one x-cluster on BOTH
images). Objects are not grouped here.

Usage (from repo root):
    uv run python detectors/edge-census/edge_census.py evals/grid-misalign/defect.png
    uv run python detectors/edge-census/edge_census.py record.json --json
    uv run eyes describe img.png --stats > rec.json   # record input also OK
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CANVAS = 1000.0  # Mirage normalizes each axis to [0, CANVAS]

# ---- calibrated defaults (see module docstring / VERDICT.md) ----
FLOOR = 3.0        # flag edge spread strictly greater than this (units)
MIN_N = 2          # minimum cluster size to census
XGAP = 30.0        # x-cluster linkage gap (units; ~32px on a 1080 canvas)
YGAP = 25.0        # y-cluster linkage gap for the row pass
ROW_MIN = 40.0     # column clusters must span > this in y0 (units)
COL_MIN = 40.0     # row clusters must span > this in x0 (units)
ROW_SAME = 8.0     # adjacent y0s closer than this => merged columns, skip
COL_SAME = 8.0     # adjacent x0s closer than this => merged rows, skip
WIDTH_GUARD = 15.0 # width spread above this => OCR-noise-dominated, don't flag


def norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def spread(vals: list[float]) -> float:
    return max(vals) - min(vals) if vals else 0.0


def cluster_1d(items: list[dict], coord, gap: float) -> list[list[dict]]:
    """Single-linkage clustering on one bbox coordinate."""
    items = sorted(items, key=lambda it: coord(it["bbox"]))
    if not items:
        return []
    clusters, cur = [], [items[0]]
    for it in items[1:]:
        if coord(it["bbox"]) - coord(cur[-1]["bbox"]) > gap:
            clusters.append(cur)
            cur = [it]
        else:
            cur.append(it)
    clusters.append(cur)
    return clusters


def has_collision(members: list[dict], coord, same: float) -> bool:
    """True if any two members share ~the same coord — i.e. the cluster
    merged two parallel lines (two columns in a row cluster, etc.)."""
    vals = sorted(coord(m["bbox"]) for m in members)
    return any(b - a < same for a, b in zip(vals, vals[1:]))


def census_cluster(members: list[dict], axis: str) -> dict:
    """Spread stats for one cluster. axis='x' => column pass."""
    bbs = [m["bbox"] for m in members]
    x0 = [b[0] for b in bbs]
    y0 = [b[1] for b in bbs]
    x1 = [b[2] for b in bbs]
    y1 = [b[3] for b in bbs]
    w = [b[2] - b[0] for b in bbs]
    h = [b[3] - b[1] for b in bbs]
    if axis == "x":
        edge_spread = max(spread(x0), spread(x1))
        cross_spread = spread(y0)  # must span rows to be a column
        size_spread = spread(w)
    else:
        edge_spread = max(spread(y0), spread(y1))
        cross_spread = spread(x0)  # must span columns to be a row
        size_spread = spread(h)
    return {
        "n": len(members),
        "edge_spread": edge_spread,
        "x0_spread": spread(x0),
        "x1_spread": spread(x1),
        "y0_spread": spread(y0),
        "y1_spread": spread(y1),
        "width_spread": spread(w),
        "height_spread": spread(h),
        "cross_spread": cross_spread,
        "size_spread": size_spread,
        "members": bbs,
    }


def census(record: dict, *, floor: float, min_n: int,
           xgap: float, ygap: float, row_min: float, col_min: float,
           row_same: float, col_same: float, width_guard: float) -> dict:
    texts = [t for t in record.get("text", [])
             if isinstance(t.get("bbox"), list) and len(t["bbox"]) == 4
             and t.get("string")]

    groups: dict[str, list[dict]] = {}
    for t in texts:
        groups.setdefault(norm_key(t["string"]), []).append(t)

    findings: list[dict] = []
    audited: list[dict] = []

    for key in sorted(groups):
        members = groups[key]
        if len(members) < min_n:
            continue
        display = members[0]["string"].strip()

        # ---- column pass: cluster by x0, require multi-row span ----
        for cl in cluster_1d(members, lambda b: b[0], xgap):
            if len(cl) < min_n:
                continue
            st = census_cluster(cl, "x")
            entry = {"string": display, "axis": "column", **{k: st[k] for k in
                     ("n", "edge_spread", "x0_spread", "x1_spread",
                      "y0_spread", "y1_spread", "width_spread",
                      "cross_spread", "size_spread")},
                     "members": st["members"]}
            audited.append(entry)
            if st["cross_spread"] <= row_min:
                continue  # horizontal arrangement — no shared x-edge owed
            if has_collision(cl, lambda b: b[1], row_same):
                entry["skipped"] = "merged_columns"  # two columns fused
                continue
            if st["size_spread"] > width_guard:
                entry["skipped"] = "width_spread_too_large"
                continue
            if st["edge_spread"] > floor:
                findings.append({**entry, "kind": "column_drift",
                                 "floor": floor})

        # ---- row pass: cluster by y0, require multi-column span ----
        for cl in cluster_1d(members, lambda b: b[1], ygap):
            if len(cl) < min_n:
                continue
            st = census_cluster(cl, "y")
            entry = {"string": display, "axis": "row", **{k: st[k] for k in
                     ("n", "edge_spread", "x0_spread", "x1_spread",
                      "y0_spread", "y1_spread", "width_spread",
                      "cross_spread", "size_spread")},
                     "members": st["members"]}
            audited.append(entry)
            if st["cross_spread"] <= col_min:
                continue  # vertical arrangement — no shared y-edge owed
            if has_collision(cl, lambda b: b[0], col_same):
                entry["skipped"] = "merged_rows"
                continue
            if st["size_spread"] > width_guard:
                entry["skipped"] = "height_spread_too_large"
                continue
            if st["edge_spread"] > floor:
                findings.append({**entry, "kind": "row_drift",
                                 "floor": floor})

    findings.sort(key=lambda f: -f["edge_spread"])
    return {
        "params": {"floor": floor, "min_n": min_n, "xgap": xgap,
                   "ygap": ygap, "row_min": row_min, "col_min": col_min,
                   "row_same": row_same, "col_same": col_same,
                   "width_guard": width_guard},
        "text_records": len(texts),
        "repeated_strings": sum(1 for v in groups.values()
                                if len(v) >= min_n),
        "clusters_audited": len(audited),
        "audit": audited,
        "findings": findings,
        "verdict": "FLAGGED" if findings else "CLEAN",
    }


def px_factors(size: tuple[int, int] | None) -> tuple[float, float] | None:
    """bbox units -> px for a known image size, else None."""
    if not size:
        return None
    w, h = size
    return w / CANVAS, h / CANVAS


def main() -> int:
    p = argparse.ArgumentParser(
        description="Repeated-element edge census over a Mirage record.")
    p.add_argument("input", help="image path (described via eyes.mirage) "
                                 "or a record .json from `eyes describe`")
    p.add_argument("--json", action="store_true", help="emit JSON only")
    p.add_argument("--floor", type=float, default=FLOOR,
                   help="edge-spread flag threshold in [0,1000] units "
                        f"(default {FLOOR}; control measured <=2, defect 4-9)")
    p.add_argument("--min-n", type=int, default=MIN_N,
                   help="minimum cluster size (default %(default)s)")
    p.add_argument("--xgap", type=float, default=XGAP)
    p.add_argument("--ygap", type=float, default=YGAP)
    p.add_argument("--row-min", type=float, default=ROW_MIN,
                   help="min y0 span for a column cluster (units)")
    p.add_argument("--col-min", type=float, default=COL_MIN,
                   help="min x0 span for a row cluster (units)")
    p.add_argument("--width-guard", type=float, default=WIDTH_GUARD,
                   help="max allowed size spread before cluster is "
                        "deemed OCR-noise-dominated")
    args = p.parse_args()

    src = Path(args.input)
    size = None
    if src.suffix.lower() == ".json" or src.name.endswith(".json"):
        raw = src.read_text()
        i = raw.find("{")
        record = json.JSONDecoder().raw_decode(raw[i:])[0]
    else:
        from eyes import mirage
        from PIL import Image
        img = Image.open(src).convert("RGB")
        size = img.size
        record = mirage.describe(img)

    result = census(record,
                    floor=args.floor, min_n=args.min_n,
                    xgap=args.xgap, ygap=args.ygap,
                    row_min=args.row_min, col_min=args.col_min,
                    row_same=ROW_SAME, col_same=COL_SAME,
                    width_guard=args.width_guard)
    result["input"] = str(src)
    result["image_size"] = list(size) if size else None

    factors = px_factors(size)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"edge-census: {src}")
    if size:
        print(f"  image {size[0]}x{size[1]}  "
              f"(1 x-unit ~= {size[0]/CANVAS:.2f}px, "
              f"1 y-unit ~= {size[1]/CANVAS:.2f}px)")
    print(f"  text records: {result['text_records']}  "
          f"repeated strings (n>={args.min_n}): "
          f"{result['repeated_strings']}  "
          f"clusters audited: {result['clusters_audited']}")
    print(f"  floor: edge spread > {args.floor} units")
    for f in result["findings"]:
        axis = "x" if f["axis"] == "column" else "y"
        sp = f["edge_spread"]
        px = ""
        if factors:
            fac = factors[0] if axis == "x" else factors[1]
            px = f" (~{sp * fac:.1f}px)"
        print(f"  FINDING {f['kind']}: '{f['string']}' n={f['n']} "
              f"{axis}-edge spread {sp:.0f}u{px} "
              f"(x0 {f['x0_spread']:.0f} x1 {f['x1_spread']:.0f} "
              f"y0 {f['y0_spread']:.0f} y1 {f['y1_spread']:.0f} "
              f"w {f['width_spread']:.0f})")
        for m in f["members"]:
            print(f"      bbox {m}")
    skipped = [a for a in result["audit"] if a.get("skipped")]
    for a in skipped:
        print(f"  skipped {a['axis']} cluster '{a['string']}' n={a['n']}: "
              f"{a['skipped']} (edge_spread {a['edge_spread']:.0f})")
    if not result["findings"]:
        near = sorted(result["audit"], key=lambda a: -a["edge_spread"])[:3]
        for a in near:
            print(f"  max audited spread: '{a['string']}' {a['axis']} "
                  f"{a['edge_spread']:.0f}u (n={a['n']})")
    print(f"  VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
