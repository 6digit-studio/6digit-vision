"""eyes CLI — describe, score, palette.

  eyes describe image.png [--masks] [--stats]
  eyes score reference.png candidate.png [--json]
  eyes palette image.png [--n 8]
"""

from __future__ import annotations

import argparse
import json
import sys


def cmd_describe(args) -> int:
    from . import color, mirage

    rec = mirage.describe(args.image, include_masks=args.masks)
    if args.stats:
        rec["_color"] = {
            "palette": color.palette(args.image, n=args.palette_n),
            "objects": color.object_color_stats(args.image, rec),
        }
    print(mirage.to_json(rec))
    return 0


def cmd_score(args) -> int:
    from . import color, mirage, score

    ref_rec = mirage.describe(args.reference)
    cand_rec = mirage.describe(args.candidate)
    result = score.score_pair(
        ref_rec,
        cand_rec,
        ref_pal=color.palette(args.reference),
        cand_pal=color.palette(args.candidate),
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"score: {result['score']:.1f} / 100\n")
    for name, comp in result["components"].items():
        extras = {k: v for k, v in comp.items() if k != "score"}
        print(f"  {name:<8} {comp['score'] * 100:5.1f}  {extras}")
    return 0


def cmd_layout(args) -> int:
    from . import layout, mirage

    rec = mirage.describe(args.image) if args.describe else None
    report = layout.layout_report(args.image, record=rec, tol=args.tol)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    ec = report["edge_contact"]
    print(f"edge contact (bg {ec['bg']}, strip {ec['strip_px']}px):")
    for s in ("top", "right", "bottom", "left"):
        flag = "  <-- TOUCHING" if s in ec["touching"] else ""
        print(f"  {s:<7} {ec[s] * 100:5.1f}%{flag}")
    if "objects_at_edge" in report:
        print("\nobjects at edge:")
        for o in report["objects_at_edge"] or ["  (none)"]:
            print(f"  {o}")
        print("\nbbox overlaps:")
        for o in report["bbox_overlaps"] or ["  (none)"]:
            print(f"  {o}")
        print("\ntext flush at interior edge:")
        for o in report.get("text_edge_flush") or ["  (none)"]:
            print(f"  {o}")
        flagged = [l for l in report.get("legibility", []) if l["flags"]]
        print("\nlegibility flags:")
        for l in flagged or ["  (none)"]:
            print(f"  {l}")
    return 0


def cmd_reel(args) -> int:
    from . import temporal

    report = temporal.reel_report(args.inputs, with_records=not args.no_records)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(f"{report['frames']} frames, records={'on' if report['with_records'] else 'off'}\n")
    for pair in report["pairs"]:
        px = pair["pixel"]
        static = "  STATIC" if pair.get("static") else ""
        line = (f"{pair['pair'][0]} -> {pair['pair'][1]}: "
                f"changed {px['changed_pct'] * 100:.1f}%  "
                f"mean|d| {px['mean_abs_diff']}{static}")
        if "labels" in pair:
            line += f"  labels {pair['labels']['score']:.2f}  ocr {pair['ocr']['score']:.2f}"
        print(line)
    if report.get("static_pairs"):
        print(f"\nstatic pairs: {report['static_pairs']}")
    return 0


def cmd_palette(args) -> int:
    from . import color

    for p in color.palette(args.image, n=args.n):
        bar = "#" * round(p["frac"] * 40)
        print(f"{p['hex']}  {p['frac'] * 100:5.1f}%  {bar}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="eyes", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("describe", help="structured perception record for one image")
    p.add_argument("image")
    p.add_argument("--masks", action="store_true", help="include polygon masks")
    p.add_argument("--stats", action="store_true", help="add quantitative color stats")
    p.add_argument("--palette-n", type=int, default=8)
    p.set_defaults(fn=cmd_describe)

    p = sub.add_parser("score", help="decomposed similarity: candidate vs reference")
    p.add_argument("reference")
    p.add_argument("candidate")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_score)

    p = sub.add_parser("layout", help="overflow/layout facts: edge contact, edge objects, overlaps")
    p.add_argument("image")
    p.add_argument("--describe", action="store_true",
                   help="also run Mirage and include object-level findings")
    p.add_argument("--tol", type=int, default=64,
                   help="color distance from background counted as content")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_layout)

    p = sub.add_parser("reel", help="frame-sequence coherence: pixel diffs + record stability")
    p.add_argument("inputs", nargs="+", help="image paths and/or directories")
    p.add_argument("--no-records", action="store_true",
                   help="pixel diffs only, skip Mirage (faster)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_reel)

    p = sub.add_parser("palette", help="dominant color histogram")
    p.add_argument("image")
    p.add_argument("-n", type=int, default=8)
    p.set_defaults(fn=cmd_palette)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except FileNotFoundError as e:
        print(f"eyes: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
