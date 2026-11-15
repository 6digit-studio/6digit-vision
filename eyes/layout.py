"""Layout/overflow signals — measurable geometry facts, not verdicts.

Three detectors, all backend-agnostic (pixels + Mirage record only):

- edge_contact: fraction of non-background pixels in each frame border
  strip. High value on a side = content running to (or past) the edge.
- objects_at_edge: Mirage objects whose bbox touches the frame boundary.
- bbox_overlaps: pairs of objects with significant bbox intersection,
  excluding part-whole containment (screen inside smartphone is fine).

These report facts; judging whether a fact is a defect needs context
(full-bleed photography legitimately touches edges). That judgment is
the reasoning model's job — the instrument stays honest.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .color import _open, denorm, palette

_MAX_DIM = 256


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _dist(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _prep(image, max_dim: int = _MAX_DIM) -> Image.Image:
    img = _open(image)
    scale = min(1.0, max_dim / max(img.width, img.height))
    if scale < 1.0:
        img = img.resize((round(img.width * scale), round(img.height * scale)))
    return img


def dominant_color(image) -> tuple[int, int, int]:
    "Best-effort background estimate: most common 5-bit-quantized color."
    pal = palette(image, n=1)
    return _hex_to_rgb(pal[0]["hex"]) if pal else (0, 0, 0)


def edge_contact(image, tol: int = 64, strip_frac: float = 0.02,
                 bg: tuple[int, int, int] | None = None) -> dict:
    """Fraction of non-background pixels in each outer border strip.

    Returns per-side fractions plus 'touching' flags (>0.5). Interpretation
    is left to the caller: 0.9 on `right` means content reaches the right
    edge — bleed or intentional full-bleed, the record can't say which.
    """
    img = _prep(image).convert("RGB")
    w, h = img.size
    bg = bg or dominant_color(image)
    strip = max(1, round(min(w, h) * strip_frac))
    px = img.load()

    def frac(coords) -> float:
        total = hit = 0
        for x, y in coords:
            total += 1
            if _dist(px[x, y], bg) > tol:
                hit += 1
        return round(hit / total, 4) if total else 0.0

    top = [(x, y) for x in range(w) for y in range(strip)]
    bottom = [(x, y) for x in range(w) for y in range(h - strip, h)]
    left = [(x, y) for x in range(strip) for y in range(h)]
    right = [(x, y) for x in range(w - strip, w) for y in range(h)]
    out = {
        "top": frac(top), "bottom": frac(bottom),
        "left": frac(left), "right": frac(right),
        "strip_px": strip, "bg": "#%02x%02x%02x" % bg,
    }
    out["touching"] = [s for s in ("top", "right", "bottom", "left")
                       if out[s] > 0.5]
    return out


def objects_at_edge(record: dict, margin: float = 0.05,
                    suspect_score: float = 0.5) -> list[dict]:
    """Objects whose Mirage bbox comes within `margin` (of 1000-space)
    of any frame edge — candidates for clipped/off-frame content.

    margin defaults to 5%: measured on evals/clipped-card, Mirage
    under-covers physically-clipped objects by ~3%, so 2% misses them.
    'suspect' marks edge objects whose detection score is low — the
    confidence-collapse signature of a cut object (0.899 -> 0.309 on the
    clipped-card case).
    """
    m = margin * 1000.0
    hits = []
    for obj in record.get("objects", []):
        if "bbox" not in obj:
            continue
        x0, y0, x1, y1 = obj["bbox"]
        sides = []
        if x0 <= m: sides.append("left")
        if y0 <= m: sides.append("top")
        if x1 >= 1000 - m: sides.append("right")
        if y1 >= 1000 - m: sides.append("bottom")
        if sides:
            score = obj.get("score")
            hits.append({"name": obj.get("name"), "sides": sides,
                         "bbox": obj["bbox"], "score": score,
                         "suspect": score is not None and score < suspect_score})
    return hits


def _bbox(b):
    return b[0], b[1], b[2], b[3]


def _iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter == 0:
        return 0.0
    area_a = max(0, ax1 - ax0) * max(0, ay1 - ay0)
    area_b = max(0, bx1 - bx0) * max(0, by1 - by0)
    return inter / max(area_a + area_b - inter, 1e-9)


def _containment(a, b) -> float:
    """Fraction of smaller box covered by the larger."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    area_a = max(0, ax1 - ax0) * max(0, ay1 - ay0)
    area_b = max(0, bx1 - bx0) * max(0, by1 - by0)
    smaller = min(area_a, area_b)
    return inter / smaller if smaller > 0 else 0.0


def bbox_overlaps(record: dict, iou_thresh: float = 0.15,
                  contain_thresh: float = 0.8) -> list[dict]:
    """Object pairs with significant bbox intersection.

    Pairs where one box contains the other (>contain_thresh of the
    smaller) are skipped — device > screen > icon nesting is legitimate.
    """
    objs = [o for o in record.get("objects", []) if "bbox" in o]
    pairs = []
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            a, b = _bbox(objs[i]["bbox"]), _bbox(objs[j]["bbox"])
            iou = _iou(a, b)
            if iou >= iou_thresh and _containment(a, b) < contain_thresh:
                pairs.append({
                    "a": objs[i].get("name"), "b": objs[j].get("name"),
                    "iou": round(iou, 3),
                })
    return pairs


def interior_edge_lines(image, min_strength: float = 30.0,
                        min_gap: int = 10, max_lines: int = 30) -> dict:
    """Strong vertical/horizontal gradient lines inside the frame —
    candidate container boundaries (card edges, dividers, clip lines).

    Column/row mean-abs-diff profiles, peaks above min_strength picked
    with min_gap suppression. Returns pixel positions on the _prep'd
    (<=256px) canvas plus the canvas size for denorm'ing back.
    """
    img = _prep(image).convert("L")
    w, h = img.size
    px = img.load()

    def profile(axis):
        # axis 'v': per-column score = mean |px[x,y]-px[x-1,y]|
        n = w if axis == "v" else h
        scores = [0.0] * n
        step = 2
        count = max(1, (h if axis == "v" else w) // step)
        for i in range(1, n):
            s = 0
            for j in range(0, h if axis == "v" else w, step):
                if axis == "v":
                    s += abs(px[i, j] - px[i - 1, j])
                else:
                    s += abs(px[j, i] - px[j, i - 1])
            scores[i] = s / count
        return scores

    def peaks(scores):
        idx = [i for i in range(1, len(scores) - 1)
               if scores[i] >= scores[i - 1] and scores[i] >= scores[i + 1]
               and scores[i] >= min_strength]
        idx.sort(key=lambda i: -scores[i])
        chosen = []
        for i in idx:
            if all(abs(i - c) >= min_gap for c in chosen):
                chosen.append(i)
            if len(chosen) >= max_lines:
                break
        return sorted(chosen)

    return {
        "vertical": peaks(profile("v")),
        "horizontal": peaks(profile("h")),
        "size": [w, h],
    }


def text_edge_flush(image, record: dict, tol_px: int = 8,
                    min_strength: float = 30.0) -> list[dict]:
    """Text regions whose bbox edge lands flush against an interior edge
    line — the signature of text clipped at a container boundary
    (overflow:hidden), as opposed to frame-edge clipping.

    Reports facts: string, which side is flush, the line position.
    """
    lines = interior_edge_lines(image, min_strength=min_strength)
    vw, vh = lines["size"]
    vlines, hlines = lines["vertical"], lines["horizontal"]
    img_w = _open(image).width
    img_h = _open(image).height
    # scale factor between _prep canvas and original pixels
    sx, sy = img_w / vw, img_h / vh
    findings = []
    for t in record.get("text", []):
        if "bbox" not in t:
            continue
        x0, y0, x1, y1 = denorm(t["bbox"], img_w, img_h)
        hits = []
        for lx in vlines:
            lxp = lx * sx
            if abs(x1 - lxp) <= tol_px:
                hits.append({"side": "right", "line_x": round(lxp)})
            if abs(x0 - lxp) <= tol_px:
                hits.append({"side": "left", "line_x": round(lxp)})
        for ly in hlines:
            lyp = ly * sy
            if abs(y1 - lyp) <= tol_px:
                hits.append({"side": "bottom", "line_y": round(lyp)})
            if abs(y0 - lyp) <= tol_px:
                hits.append({"side": "top", "line_y": round(lyp)})
        if hits:
            findings.append({"string": (t.get("string") or "")[:48],
                             "bbox": t["bbox"], "flush": hits})
    return findings


def layout_report(image, record: dict | None = None,
                  tol: int = 64) -> dict:
    """Combined layout facts for one image."""
    report = {"edge_contact": edge_contact(image, tol=tol)}
    if record is not None:
        report["objects_at_edge"] = objects_at_edge(record)
        report["bbox_overlaps"] = bbox_overlaps(record)
        report["text_edge_flush"] = text_edge_flush(image, record)
        from .legibility import text_legibility
        report["legibility"] = text_legibility(image, record)
    return report
