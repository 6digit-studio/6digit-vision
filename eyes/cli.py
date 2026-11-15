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
    from PIL import Image

    from . import color, mirage, score

    ref_rec = mirage.describe(args.reference)
    cand_rec = mirage.describe(args.candidate)
    result = score.score_pair(
        ref_rec,
        cand_rec,
        ref_pal=color.palette(args.reference),
        cand_pal=color.palette(args.candidate),
        ref_size=Image.open(args.reference).size,
        cand_size=Image.open(args.candidate).size,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"score: {result['score']:.1f} / 100\n")
    for name, comp in result["components"].items():
        extras = {k: v for k, v in comp.items() if k != "score"}
        print(f"  {name:<8} {comp['score'] * 100:5.1f}  {extras}")
    return 0


def cmd_grid(args) -> int:
    from . import color

    cells = color.grid_stats(args.image, cols=args.cols)
    if args.json:
        print(json.dumps(cells, indent=1))
        return 0
    # ANSI truecolor map: bg = dominant cell color; ' ' = flat, '.' = textured
    hi_std = args.hi_std
    for row in cells:
        line = []
        for c in row:
            r, g, b = c["mean"]
            mark = " " if c["std"] < hi_std else "."
            line.append(f"\x1b[48;2;{r};{g};{b}m{mark}\x1b[0m")
        print("".join(line))
    print(f"({args.cols}x{len(cells)} cells; '.' = std>{hi_std} textured)")
    return 0


def cmd_structure(args) -> int:
    from . import mirage, structure

    rec = mirage.describe(args.image)
    texts = [t for t in rec.get("text", []) if t.get("score", 0) > args.min_score]
    s = structure.summarize(texts)
    if args.json:
        print(json.dumps(s, indent=2, ensure_ascii=False))
        return 0
    print(f"rows: {s['n_rows']}  cols: {s['n_cols']}  col_xs: {s['col_xs']}")
    for r in s["grid"]:
        print(f"  y={r['y']:>5}  {' | '.join('' if c is None else c for c in r['cells'])}")
    if "inference" in s:
        print(f"\ninference: {s['inference']['kind']}")
        print(f"  header: {s['inference']['weekday_header']}")
        print(f"  days: {s['inference']['day_sequence']}")
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
        eb = report.get("edge_bisect") or {}
        print(f"\nedge bisects ({eb.get('verdict','?')}):")
        for f in eb.get("findings") or ["  (none)"]:
            if isinstance(f, dict):
                print(f"  {f.get('string')!r}  {f.get('axis')} line={f.get('line_px')} "
                      f"cov={f.get('coverage')} ink_dist={f.get('ink_dist_px')}px")
            else:
                print(f"  {f}")
        co = report.get("content_overflow") or {}
        print(f"\ncontent overflow ({co.get('verdict','?')}):")
        for f in co.get("findings") or ["  (none)"]:
            print(f"  {f}")
        for n in co.get("notes") or []:
            print(f"  {n}")
    return 0


def cmd_pixdiff(args) -> int:
    from . import pixdiff as _pd

    r = _pd.pixdiff(args.a, args.b)
    if args.json:
        print(json.dumps(r, indent=2))
        return 0
    print(f"pixdiff score={r['score']} ssim={r['ssim_mean']} "
          f"mismatch={r['mismatch_frac']} regions={r['n_regions']}")
    for reg in r["regions"][:8]:
        print(f"  {reg}")
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
    lc = report.get("lifecycle") or {}
    if lc.get("departures"):
        print(f"\nlifecycle departures ({lc.get('verdict','?')}):")
        for d in lc["departures"]:
            print(f"  {d.get('kind','?'):<22} {d.get('element','?')}  {d.get('detail','')}")
    return 0


def cmd_ask(args) -> int:
    from . import ask

    pack = ask.evidence_pack(args.image, question=args.question)
    print(json.dumps(pack, indent=2, ensure_ascii=False))
    return 0


def cmd_palette(args) -> int:
    from . import color

    for p in color.palette(args.image, n=args.n):
        bar = "#" * round(p["frac"] * 40)
        print(f"{p['hex']}  {p['frac'] * 100:5.1f}%  {bar}")
    return 0


def cmd_parse(args) -> int:
    from . import mirage, scene_tree

    rec = mirage.describe(args.image)
    tree = scene_tree.build_tree(rec)
    if args.json:
        print(json.dumps(tree, indent=2, ensure_ascii=False))
        return 0
    print(f"scene: {tree.get('scene')}")
    print(f"\nregions ({len(tree['regions'])}):")
    for i, r in enumerate(tree["regions"]):
        names = ", ".join(e["name"][:24] for e in r["elements"][:6])
        more = f" +{len(r['elements']) - 6}" if len(r["elements"]) > 6 else ""
        print(f"  [{i}] bbox={r['bbox']}  {len(r['elements'])} elements: {names}{more}")
    if tree["loose_objects"]:
        print(f"\nloose objects ({len(tree['loose_objects'])}):")
        for r in tree["loose_objects"]:
            print(f"  {r['elements'][0]['name'][:40]}  bbox={r['bbox']}")
    return 0


def cmd_diff(args) -> int:
    from PIL import Image

    from . import mirage, scene_tree

    ref_rec = mirage.describe(args.reference)
    cand_rec = mirage.describe(args.candidate)
    result = scene_tree.diff_records(
        ref_rec, cand_rec,
        ref_size=Image.open(args.reference).size,
        cand_size=Image.open(args.candidate).size)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    print(f"objects: {result['counts']['ref_objects']} ref / "
          f"{result['counts']['cand_objects']} cand, "
          f"{result['counts']['ref_text']} / {result['counts']['cand_text']} text")
    for ch in result["object_changes"]:
        print(f"  ~ {ch['element'][:36]:<38} {ch['deltas']}")
    for o in result["objects_added"]:
        print(f"  + {o['name'][:40]}")
    for o in result["objects_removed"]:
        print(f"  - {o['name'][:40]}")
    for t in result["text_changes"]:
        if t["type"] == "text_edited":
            print(f"  T {t['ref'][:30]!r} -> {t['cand'][:30]!r}")
        elif t["type"] == "text_added":
            print(f"  T+ {t['cand'][:40]!r}")
        else:
            print(f"  T- {t['ref'][:40]!r}")
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

    p = sub.add_parser("pixdiff", help="pixel-level diff: SSIM map + change regions")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_pixdiff)

    p = sub.add_parser("grid", help="sample colors on a uniform grid (ANSI map / JSON)")
    p.add_argument("image")
    p.add_argument("--cols", type=int, default=16)
    p.add_argument("--hi-std", type=float, default=30.0,
                   help="stddev threshold marking textured (imagery) cells")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_grid)

    p = sub.add_parser("structure", help="induce rows/columns/grids from OCR layout")
    p.add_argument("image")
    p.add_argument("--min-score", type=float, default=0.4)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_structure)

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

    p = sub.add_parser("ask", help="evidence pack for the reasoning layer (optionally framed with a question)")
    p.add_argument("image")
    p.add_argument("-q", "--question", default=None)
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("palette", help="dominant color histogram")
    p.add_argument("image")
    p.add_argument("-n", type=int, default=8)
    p.set_defaults(fn=cmd_palette)

    p = sub.add_parser("parse", help="hierarchical scene tree: regions + elements")
    p.add_argument("image")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_parse)

    p = sub.add_parser("diff", help="element-level change list: reference vs candidate")
    p.add_argument("reference")
    p.add_argument("candidate")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_diff)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except FileNotFoundError as e:
        print(f"eyes: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
