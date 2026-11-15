#!/usr/bin/env python3
"""region_map — pixdiff regions -> candidate DOM elements -> edit targets.

The auto region->CSS mapper: pixdiff says WHERE pixels differ; this
maps each diff region onto the candidate's actual elements (via
Playwright getBoundingClientRect + computed styles) and scores each
implicated element's LOCAL diff — turning 'something differs at
bbox X' into 'element .banner at rect R has diff 0.31, bg=#2d333b'.

Honest scope: regions with no overlapping candidate element report
`unmatched` — missing content, or non-CSS-addressable pixels
(images, canvas, graphical chrome). The mapper doesn't invent edits;
it produces critic-actionable evidence.

Usage:
  uv run --with playwright python3 tools/region_map.py \
      REF.png CANDIDATE.html [--viewport WxH]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eyes.pixdiff import pixdiff, _prep  # noqa: E402
import numpy as np  # noqa: E402


def dump_elements(html_path: Path, w: int, h: int) -> list[dict]:
    """Playwright: render page, dump visible elements with rects+styles."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(f"file://{html_path.resolve()}")
        pg.wait_for_timeout(300)
        els = pg.evaluate("""() => {
          const out = [];
          for (const el of document.querySelectorAll('*')) {
            const r = el.getBoundingClientRect();
            if (r.width < 3 || r.height < 3) continue;
            const cs = getComputedStyle(el);
            if (cs.display === 'none' || cs.visibility === 'hidden') continue;
            let sel = el.tagName.toLowerCase();
            if (el.id) sel += '#' + el.id;
            else if (el.className && typeof el.className === 'string')
              sel += '.' + el.className.trim().split(/\\s+/).join('.');
            out.push({sel, rect: [r.x, r.y, r.width, r.height],
                      bg: cs.backgroundColor, color: cs.color,
                      fontSize: cs.fontSize, text:
                      (el.childElementCount === 0 ?
                       (el.textContent || '').trim().slice(0, 40) : '')});
          }
          return out;
        }""")
        b.close()
    return els


def _local_diff(ref_arr, cand_arr, rect) -> float:
    """pixdiff score restricted to an element rect (normalized 0-1)."""
    x, y, w, h = rect
    H, W = ref_arr.shape[:2]
    x0, y0 = int(x * W), int(y * H)
    x1, y1 = int((x + w) * W), int((y + h) * H)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return 1.0
    a = ref_arr[y0:y1, x0:x1]
    b = cand_arr[y0:y1, x0:x1]
    if a.shape != b.shape:
        return 0.5
    d = np.abs(a - b).mean()
    return round(float(max(0.0, 1.0 - d * 4)), 3)


def map_regions(ref_png, cand_png, elements, max_regions: int = 8) -> dict:
    """Match pixdiff regions to candidate elements."""
    pd = pixdiff(ref_png, cand_png)
    A, B = _prep(ref_png, cand_png)
    W, H = pd["size"][1], pd["size"][0]  # size is [w,h]
    img_w, img_h = W, H

    mapped = []
    for reg in pd["regions"][:max_regions]:
        bx, by, bx1, by1 = reg["bbox_px"]
        # normalized region rect
        rx, ry = bx / img_w, by / img_h
        rx1, ry1 = bx1 / img_w, by1 / img_h
        hits = []
        reg_area = max(1, (bx1 - bx) * (by1 - by))
        covered = 0
        for el in elements:
            if el["sel"] in ("html", "body"):
                continue  # full-frame elements carry no edit target
            ex, ey, ew, eh = el["rect"]
            # element rect in px -> overlap with region
            ox0, oy0 = max(ex, bx), max(ey, by)
            ox1, oy1 = min(ex + ew, bx1), min(ey + eh, by1)
            inter = max(0, ox1 - ox0) * max(0, oy1 - oy0)
            if inter <= 0:
                continue
            covered += inter
            # element-local diff: element rect vs same rect in ref
            nx, ny = ex / img_w, ey / img_h
            nw, nh = ew / img_w, eh / img_h
            ld = _local_diff(A, B, (nx, ny, nw, nh))
            hits.append({"sel": el["sel"], "rect_px": [round(v) for v in el["rect"]],
                         "overlap_frac": round(inter / (ew * eh), 2),
                         "local_diff": ld,
                         "bg": el["bg"], "color": el["color"],
                         "fontSize": el["fontSize"], "text": el["text"]})
        hits.sort(key=lambda e: -e["overlap_frac"])
        coverage = covered / reg_area
        mapped.append({
            "region_px": reg["bbox_px"], "area_frac": reg["area_frac"],
            "region_coverage": round(coverage, 3),
            "elements": hits[:5],
            "verdict": (
                "mapped" if coverage >= 0.3 and hits else
                "mostly-unmatched" if hits else
                "unmatched — no candidate element here (missing "
                "content or non-CSS pixels: image/canvas/chrome)"),
        })
    return {"pixdiff_score": pd["score"], "regions": mapped,
            "n_elements": len(elements)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("html")
    ap.add_argument("--cand-png", default=None,
                    help="pre-rendered candidate png (else temp render)")
    ap.add_argument("--viewport", default="1200x800")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright
    vw, vh = (int(x) for x in args.viewport.split("x"))
    html = Path(args.html)

    if args.cand_png:
        cand_png = args.cand_png
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        cand_png = tmp.name
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": vw, "height": vh})
            pg.goto(f"file://{html.resolve()}")
            pg.wait_for_timeout(300)
            pg.screenshot(path=cand_png)
            b.close()

    elements = dump_elements(html, vw, vh)
    out = map_regions(args.ref, cand_png, elements)
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"pixdiff={out['pixdiff_score']} regions={len(out['regions'])} "
              f"elements={out['n_elements']}")
        for m in out["regions"]:
            print(f"  region {m['region_px']} ({m['area_frac']}) -> {m['verdict']}")
            for e in m["elements"][:3]:
                print(f"    {e['sel']:<28} diff={e['local_diff']} "
                      f"bg={e['bg']} overlap={e['overlap_frac']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
