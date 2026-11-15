#!/usr/bin/env python3
"""content-overflow — elements clipped by the viewport's side edges.

Born from evals/web-breakpoint: fixed-width layout in a narrow viewport.
Pixel-level edge-ink was tried first and MEASURED unreliable — clipped
cards produce thin rules that span the full viewport width (mimicking
full-bleed sections), near-bg fills are invisible to bg-distance, and
tall edge blocks are panels/scrollbars. The semantic layer is where the
signal lives: Mirage objects pinned at the LEFT/RIGHT frame edge that
aren't full-width containers.

Spec: objects_at_edge (layout.py) restricted to horizontal edges with a
container-width guard — the breakpoint defect's clipped cards surface
as edge-pinned objects; the responsive control's only edge object is
the full-width container, excluded. Top/bottom edge contact excluded:
headers/footers legitimately anchor there.

Model-free record processing. Usage: content_overflow.py IMG --record REC.json
or via eyes layout --describe integration.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

EDGE_MARGIN = 0.05    # of 1000-space, matches objects_at_edge default
CONTAINER_W = 0.75    # objects wider than 75% of frame are containers,
                      # not clipped elements — shared noise on both sides


def census(image_path, record: dict) -> dict:
    m = EDGE_MARGIN * 1000.0
    findings = []
    for obj in record.get("objects", []):
        if "bbox" not in obj:
            continue
        x0, y0, x1, y1 = obj["bbox"]
        w_frac = (x1 - x0) / 1000.0
        if w_frac > CONTAINER_W:
            continue
        sides = []
        if x0 <= m:
            sides.append("left")
        if x1 >= 1000 - m:
            sides.append("right")
        if not sides:
            continue
        findings.append({
            "name": obj.get("name"), "sides": sides,
            "bbox": obj["bbox"], "score": obj.get("score"),
            "width_frac": round(w_frac, 3),
        })
    result = {
        "image": str(image_path),
        "findings": findings,
        "verdict": "clean",
        "notes": [],
    }
    # clipped-row coherence: horizontal overflow pins a ROW of content
    # at ONE edge — >=2 same-edge findings with overlapping y-bands.
    # Opposite-edge same-row pairs are full-width chrome (nav bars,
    # section rules — BBC/MDN/Wikipedia corpus FPs, measured); same-edge
    # non-overlapping pins are scattered chrome. Only the cluster is
    # the clip signature.
    by_edge: dict[str, list[dict]] = {}
    for f in findings:
        for s in f["sides"]:
            by_edge.setdefault(s, []).append(f)
    clustered = []
    for edge, group in by_edge.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i]["bbox"], group[j]["bbox"]
                ov = min(a[3], b[3]) - max(a[1], b[1])
                smaller = min(a[3] - a[1], b[3] - b[1])
                if smaller > 0 and ov / smaller >= 0.3:
                    clustered.append({"edge": edge,
                                      "objects": [group[i]["name"],
                                                  group[j]["name"]],
                                      "y_overlap": round(ov / smaller, 2)})
    if clustered:
        result["verdict"] = "overflow_detected"
        result["clustered"] = clustered
        result["notes"].append(
            f"{len(clustered)} same-edge row cluster(s) — multiple "
            "objects clipped at one side edge (horizontal overflow)")
    elif findings:
        result["notes"].append(
            f"{len(findings)} edge pin(s) but no same-edge row cluster "
            "— scattered edge contact, not a clip pattern")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--record", required=True,
                    help="Mirage describe JSON for the image")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rec = json.loads(Path(args.record).read_text())
    r = census(args.image, rec)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        print(f"{r['verdict']:<18} {r['image']}")
        for f in r["findings"]:
            print(f"    {f}")
        for n in r["notes"]:
            print(f"    {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
