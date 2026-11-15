#!/usr/bin/env python3
"""glyph-classifier — status-glyph pass over Mirage emblem/icon regions.

Gap filled (evals/semantic-surprise/VERDICT.md, gap #1 "No glyph-level
perception"): Mirage files a status emblem as a generic "logo" — the
check/X/warning inside it never reaches the record, so no reasoning
layer can catch "success glyph on a failed payment".

This detector consumes an `eyes describe` record, selects emblem/icon-
shaped objects, crops each region, separates the container (circle/
square fill) from the interior glyph by flood-fill hole detection, then
classifies the glyph against a small rendered vocabulary (check, x,
warning, info, spinner, download, trash, play, plus, minus) using
symmetric chamfer distance on Zhang-Suen-skeletonized masks. Pure PIL +
stdlib — no model, no numpy.

Usage (from repo root):
    uv run python detectors/glyph-classifier/glyph_classifier.py IMAGE.png
    uv run python detectors/glyph-classifier/glyph_classifier.py IMAGE.png --record rec.json
    uv run python detectors/glyph-classifier/glyph_classifier.py IMAGE.png --all   # classify every object (diagnostic)

Output: JSON findings on stdout. `glyph` is the best vocabulary match
when its chamfer score clears ACCEPT_SCORE, else "unknown" (with the
nearest guess still reported for transparency). "solid" means the
region had a container but no enclosed interior mark at all.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import shutil
import subprocess
import sys
from collections import Counter, deque
from pathlib import Path

from PIL import Image, ImageDraw

CANVAS_NORM = 1000.0  # Mirage normalizes each bbox axis to [0,1000]
MATCH_CANVAS = 96     # glyph masks are normalized to this square
FIT_PX = 72           # glyph bbox is scaled to fit inside this box
T_CONT = 56           # Chebyshev RGB distance to container color
ACCEPT_SCORE = 0.16   # max symmetric chamfer (normalized) to trust a label
MIN_GLYPH_PX = 8      # below this the "glyph" is noise

# ---------------------------------------------------------------------------
# candidate selection
# ---------------------------------------------------------------------------

ICON_WORDS = (
    "logo", "icon", "emblem", "badge", "symbol", "avatar", "sticker",
    "illustration", "pictogram", "pictograph", "glyph", "medallion",
    "seal", "stamp", "insignia", "logomark", "logotype", "brand",
    "image", "picture", "photo", "graphic", "sign",
)

# names that are containers/UI, not glyph carriers — excluded even when a
# round-ish shape is reported
DENY_NAMES = {
    "text", "button", "link", "input", "field", "search", "bar", "navbar",
    "header", "footer", "panel", "card", "window", "dialog", "menu", "tab",
    "slider", "toggle", "table", "chart", "graph", "screen", "smartphone",
    "laptop", "computer", "monitor", "television", "tv", "tablet", "device",
    "phone", "watch", "camera", "video", "map", "keyboard", "mouse",
    "printer", "speaker", "headphone", "lamp", "light", "bulb", "clock",
    "calendar", "battery", "signal", "wifi", "bluetooth", "usb", "port",
    "cable", "cord", "plug", "socket", "outlet", "person", "people", "man",
    "woman", "face", "hand", "body", "building", "house", "car", "tree",
    "flower", "animal", "bird", "fish", "food", "drink", "book", "paper",
    "document", "folder", "file", "money", "coin", "credit", "card",
}

ROUND_SHAPES = {"circular", "round", "oval", "square", "rectangular",
                "rounded", "square-ish", "circular-ish"}


def _denorm(bbox: list[float], w: int, h: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    return (round(x0 / CANVAS_NORM * w), round(y0 / CANVAS_NORM * h),
            round(x1 / CANVAS_NORM * w), round(y1 / CANVAS_NORM * h))


def is_candidate(obj: dict, classify_all: bool = False) -> bool:
    if classify_all:
        return True
    name = (obj.get("name") or "").lower()
    desc = obj.get("description") or {}
    shape = (desc.get("shape") or "").lower()
    if any(w in name for w in ICON_WORDS):
        return True
    if shape in ROUND_SHAPES and name not in DENY_NAMES \
            and not any(d in name for d in DENY_NAMES):
        return True
    return False


# ---------------------------------------------------------------------------
# glyph mask extraction: container fill vs enclosed interior mark
# ---------------------------------------------------------------------------

def _cheb(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def find_container(crop: Image.Image):
    """Container color = quantized bin whose pixels form the largest
    8-connected component in the crop.

    The emblem fill (circle/square) is always one big coherent blob;
    glyph strokes are thin multi-component marks and page margins are
    separate components — so biggest-blob wins where a center-patch mode
    fails (a dense X can outvote the fill near the middle) and where a
    whole-crop mode fails (a loose bbox lets background dominate).
    Returns the bin-center RGB, or None for a uniform crop.
    """
    w, h = crop.size
    px = crop.load()
    ctr = Counter()
    bins = [[None] * w for _ in range(h)]
    for y in range(h):
        row = bins[y]
        for x in range(w):
            r, g, b = px[x, y]
            key = (r >> 4, g >> 4, b >> 4)
            row[x] = key
            ctr[key] += 1
    if not ctr:
        return None
    best_bin, best_size, best_count = None, -1, -1
    for key, count in ctr.most_common(4):
        mask = {(x, y) for y in range(h) for x in range(w)
                if bins[y][x] == key}
        # largest connected component of this color
        seen = set()
        largest = 0
        for p in mask:
            if p in seen:
                continue
            size = 0
            dq = deque([p])
            seen.add(p)
            while dq:
                x, y = dq.popleft()
                size += 1
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        q = (x + dx, y + dy)
                        if q in mask and q not in seen:
                            seen.add(q)
                            dq.append(q)
            largest = max(largest, size)
        if largest > best_size or (largest == best_size and count > best_count):
            best_bin, best_size, best_count = key, largest, count
    return tuple((v << 4) + 8 for v in best_bin)


def extract_glyph(crop: Image.Image):
    """Return (glyph_pixel_set, container_rgb) or (None, container_rgb).

    The container mask (pixels within T_CONT of the container color) is
    dilated one px to seal anti-aliased leaks, then everything reachable
    from the crop border without crossing it is 'outside'. Pixels left
    over are enclosed interior marks — the glyph.
    """
    w, h = crop.size
    container = find_container(crop)
    if container is None:
        return None, None
    px = crop.load()
    cont = set()
    for y in range(h):
        for x in range(w):
            if _cheb(px[x, y], container) <= T_CONT:
                cont.add((x, y))
    if not cont:
        return None, container
    # dilate container by 1 px (3x3) to seal thin AA gaps
    cont_d = set(cont)
    for x, y in cont:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    cont_d.add((nx, ny))
    # flood fill the complement from the border
    outside = set()
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            p = (x, y)
            if p not in cont_d and p not in outside:
                outside.add(p)
                dq.append(p)
    for y in range(h):
        for x in (0, w - 1):
            p = (x, y)
            if p not in cont_d and p not in outside:
                outside.add(p)
                dq.append(p)
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                p = (nx, ny)
                if p not in cont_d and p not in outside:
                    outside.add(p)
                    dq.append(p)
    glyph = {(x, y) for y in range(h) for x in range(w)
             if (x, y) not in cont_d and (x, y) not in outside}
    # drop specks: keep 8-connected components >= MIN_GLYPH_PX
    glyph = _filter_components(glyph, MIN_GLYPH_PX)
    return (glyph or None), container


def _filter_components(mask: set, min_size: int) -> set:
    seen = set()
    keep = set()
    for p in mask:
        if p in seen:
            continue
        comp = []
        dq = deque([p])
        seen.add(p)
        while dq:
            x, y = dq.popleft()
            comp.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in mask and q not in seen:
                        seen.add(q)
                        dq.append(q)
        if len(comp) >= min_size:
            keep.update(comp)
    return keep


# ---------------------------------------------------------------------------
# normalization + chamfer matching
# ---------------------------------------------------------------------------

def mask_to_canvas(mask: set, src_w: int, src_h: int):
    """Crop mask to its bbox, scale to FIT_PX preserving aspect, center on
    a MATCH_CANVAS square. Returns (fg_set, (gw, gh)) or (None, None)."""
    if not mask:
        return None, None
    xs = [p[0] for p in mask]
    ys = [p[1] for p in mask]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    gw, gh = x1 - x0 + 1, y1 - y0 + 1
    scale = min(FIT_PX / gw, FIT_PX / gh)
    scale = min(scale, 4.0)  # don't over-amplify tiny blobs
    nw = max(1, round(gw * scale))
    nh = max(1, round(gh * scale))
    sub = Image.new("L", (gw, gh), 0)
    d = ImageDraw.Draw(sub)
    for x, y in mask:
        d.point((x - x0, y - y0), fill=255)
    sub = sub.resize((nw, nh), Image.BILINEAR)
    canvas = Image.new("L", (MATCH_CANVAS, MATCH_CANVAS), 0)
    ox, oy = (MATCH_CANVAS - nw) // 2, (MATCH_CANVAS - nh) // 2
    canvas.paste(sub, (ox, oy))
    px = canvas.load()
    fg = {(x, y) for y in range(MATCH_CANVAS) for x in range(MATCH_CANVAS)
          if px[x, y] >= 100}
    if not fg:
        return None, None
    return fg, (gw, gh)


def _dist_transform(fg: set):
    """Two-pass 3-4 chamfer distance transform (approx Euclidean, units of
    1/3 px) of the complement of `fg` on the MATCH_CANVAS grid."""
    INF = 10 ** 6
    w = h = MATCH_CANVAS
    dt = [[INF] * w for _ in range(h)]
    for x, y in fg:
        dt[y][x] = 0
    for y in range(h):
        row = dt[y]
        for x in range(w):
            v = row[x]
            if x > 0:
                v = min(v, row[x - 1] + 3)
            if y > 0:
                up = dt[y - 1]
                v = min(v, up[x] + 3)
                if x > 0:
                    v = min(v, up[x - 1] + 4)
                if x < w - 1:
                    v = min(v, up[x + 1] + 4)
            row[x] = v
    for y in range(h - 1, -1, -1):
        row = dt[y]
        for x in range(w - 1, -1, -1):
            v = row[x]
            if x < w - 1:
                v = min(v, row[x + 1] + 3)
            if y < h - 1:
                dn = dt[y + 1]
                v = min(v, dn[x] + 3)
                if x < w - 1:
                    v = min(v, dn[x + 1] + 4)
                if x > 0:
                    v = min(v, dn[x - 1] + 4)
            row[x] = v
    return dt


def _chamfer_dir(src: set, dt) -> float:
    """Mean distance from src pixels to nearest dt-zero pixel, in px."""
    total = 0.0
    for x, y in src:
        total += dt[y][x]
    return total / len(src) / 3.0


def symmetric_chamfer(a: set, dt_a, b: set, dt_b) -> float:
    """Symmetric chamfer normalized by canvas side."""
    d1 = _chamfer_dir(a, dt_b)
    d2 = _chamfer_dir(b, dt_a)
    return (d1 + d2) / 2.0 / MATCH_CANVAS


# ---------------------------------------------------------------------------
# template glyphs — rendered with PIL primitives, matched as binary masks
# ---------------------------------------------------------------------------

def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (MATCH_CANVAS, MATCH_CANVAS), 0)
    return img, ImageDraw.Draw(img)


def _to_fg(img: Image.Image) -> set:
    px = img.load()
    return {(x, y) for y in range(MATCH_CANVAS) for x in range(MATCH_CANVAS)
            if px[x, y] >= 100}


def thin(mask: set) -> set:
    """Zhang-Suen skeletonization. Reduces thick strokes to ~1px
    centerlines so chamfer compares shape, not stroke width."""
    P = set(mask)
    # neighbor offsets in Zhang-Suen order: N, NE, E, SE, S, SW, W, NW
    NB = ((0, -1), (1, -1), (1, 0), (1, 1),
          (0, 1), (-1, 1), (-1, 0), (-1, -1))

    def neighbors(p):
        x, y = p
        return [(x + dx, y + dy) for dx, dy in NB]

    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            remove = []
            for p in P:
                ns = neighbors(p)
                inset = [q in P for q in ns]
                B = sum(inset)
                if B < 2 or B > 6:
                    continue
                seq = inset + [inset[0]]
                A = sum(1 for i in range(8) if not seq[i] and seq[i + 1])
                if A != 1:
                    continue
                p2, p3, p4, p5, p6, p7, p8, p9 = inset
                if step == 0:
                    if p2 and p4 and p6:
                        continue
                    if p4 and p6 and p8:
                        continue
                else:
                    if p2 and p4 and p8:
                        continue
                    if p2 and p6 and p8:
                        continue
                remove.append(p)
            if remove:
                changed = True
                for p in remove:
                    P.discard(p)
    return P


def _tpl_check(w):
    img, d = _canvas()
    d.line([(30, 50), (44, 62), (68, 30)], fill=255, width=w, joint="curve")
    return _to_fg(img)


def _tpl_x(w):
    img, d = _canvas()
    d.line([(33, 33), (63, 63)], fill=255, width=w)
    d.line([(33, 63), (63, 33)], fill=255, width=w)
    return _to_fg(img)


def _tpl_warning(w):
    img, d = _canvas()
    d.line([(48, 24), (72, 66), (24, 66), (48, 24)], fill=255, width=max(6, w - 4), joint="curve")
    d.line([(48, 40), (48, 52)], fill=255, width=w)
    d.ellipse((43, 56, 53, 66), fill=255)
    return _to_fg(img)


def _tpl_info(w):
    img, d = _canvas()
    d.line([(48, 28), (48, 54)], fill=255, width=w)
    d.ellipse((41, 60, 55, 74), fill=255)
    return _to_fg(img)


def _tpl_spinner(w):
    img, d = _canvas()
    # 300-degree arc, gap centered near top-right (PIL: 0°=3 o'clock, cw)
    d.arc((22, 22, 74, 74), start=320, end=200, fill=255, width=w)
    return _to_fg(img)


def _tpl_download(w):
    img, d = _canvas()
    d.line([(48, 26), (48, 50)], fill=255, width=w)
    d.line([(40, 40), (48, 50), (56, 40)], fill=255, width=w, joint="curve")
    d.line([(36, 66), (60, 66)], fill=255, width=max(6, w - 4))
    d.line([(40, 58), (40, 66)], fill=255, width=max(6, w - 4))
    d.line([(56, 58), (56, 66)], fill=255, width=max(6, w - 4))
    return _to_fg(img)


def _tpl_trash(w):
    img, d = _canvas()
    d.line([(32, 30), (64, 30)], fill=255, width=max(6, w - 4))
    d.ellipse((43, 23, 53, 33), fill=255)
    d.line([(39, 38), (57, 38), (54, 68), (42, 68), (39, 38)],
           fill=255, width=w, joint="curve")
    return _to_fg(img)


def _tpl_play_filled(_w):
    img, d = _canvas()
    d.polygon([(36, 26), (36, 70), (74, 48)], fill=255)
    return _to_fg(img)


def _tpl_play_outline(w):
    img, d = _canvas()
    d.line([(36, 26), (36, 70), (74, 48), (36, 26)], fill=255, width=w, joint="curve")
    return _to_fg(img)


def _tpl_plus(w):
    img, d = _canvas()
    d.line([(48, 26), (48, 70)], fill=255, width=w)
    d.line([(26, 48), (70, 48)], fill=255, width=w)
    return _to_fg(img)


def _tpl_minus(w):
    img, d = _canvas()
    d.line([(30, 48), (66, 48)], fill=255, width=w)
    return _to_fg(img)


# name -> list of skeleton variants (stroke width is irrelevant after
# thinning; variants cover fill-vs-outline and pose differences)
TEMPLATES = {
    "check":    [thin(_tpl_check(13))],
    "x":        [thin(_tpl_x(13))],
    "warning":  [thin(_tpl_warning(13))],
    "info":     [thin(_tpl_info(12))],
    "spinner":  [thin(_tpl_spinner(13))],
    "download": [thin(_tpl_download(13))],
    "trash":    [thin(_tpl_trash(12))],
    "play":     [thin(_tpl_play_filled(0)), thin(_tpl_play_outline(13))],
    "plus":     [thin(_tpl_plus(13))],
    "minus":    [thin(_tpl_minus(13))],
}

_DT_CACHE: dict = {}  # (name, variant_idx) -> distance transform


def _dts():
    """Distance transforms for every template skeleton, computed once."""
    if not _DT_CACHE:
        for name, variants in TEMPLATES.items():
            for i, fg in enumerate(variants):
                _DT_CACHE[(name, i)] = _dist_transform(fg)
    return _DT_CACHE


def classify_glyph(obs_fg: set):
    """Return (best_name, best_score, ranked list of (name, score)).

    Both sides are skeletonized first — chamfer then measures centerline
    distance, so stroke width and fill density stop mattering.
    """
    obs_skel = thin(obs_fg)
    if not obs_skel:
        return None, None, []
    obs_dt = _dist_transform(obs_skel)
    dts = _dts()
    scores = {}
    for name, variants in TEMPLATES.items():
        best = min(
            symmetric_chamfer(obs_skel, obs_dt, TEMPLATES[name][i],
                              dts[(name, i)])
            for i in range(len(variants))
        )
        scores[name] = best
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    return ranked[0][0], ranked[0][1], ranked


# ---------------------------------------------------------------------------
# record acquisition + region loop
# ---------------------------------------------------------------------------

def get_record(image: str, record_path: str | None) -> dict:
    if record_path:
        return json.loads(Path(record_path).read_text())
    cmd = None
    if shutil.which("eyes"):
        cmd = ["eyes", "describe", image]
    else:
        cmd = [sys.executable, "-m", "eyes.cli", "describe", image]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError(f"eyes describe failed: {out.stderr.strip()[:400]}")
    return json.loads(out.stdout)


def _hue_name(rgb) -> str:
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.15 or v < 0.12:
        return "gray" if v >= 0.12 else "black"
    deg = h * 360
    for lim, name in ((15, "red"), (45, "orange"), (70, "yellow"),
                      (160, "green"), (200, "cyan"), (250, "blue"),
                      (290, "purple"), (335, "magenta"), (361, "red")):
        if deg < lim:
            return name
    return "red"


def classify_image(image_path: str, record: dict, classify_all: bool = False):
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    objects = record.get("objects", [])
    regions = []
    for obj in objects:
        if not is_candidate(obj, classify_all):
            continue
        bbox = obj.get("bbox")
        if not bbox:
            continue
        x0, y0, x1, y1 = _denorm(bbox, w, h)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < 6 or y1 - y0 < 6:
            continue
        crop = img.crop((x0, y0, x1, y1))
        glyph_mask, container = extract_glyph(crop)
        entry = {
            "object_id": obj.get("id"),
            "name": obj.get("name"),
            "mirage_score": obj.get("score"),
            "position": obj.get("position"),
            "bbox_px": [x0, y0, x1, y1],
        }
        if container is not None:
            entry["container_hex"] = "#%02x%02x%02x" % container
            entry["container_hue"] = _hue_name(container)
        if not glyph_mask:
            entry["glyph"] = "solid" if container else "unknown"
            entry["glyph_px"] = 0
            regions.append(entry)
            continue
        obs_fg, (gw, gh) = mask_to_canvas(glyph_mask, crop.width, crop.height)
        if obs_fg is None:
            entry["glyph"] = "unknown"
            entry["glyph_px"] = len(glyph_mask)
            regions.append(entry)
            continue
        fill = len(glyph_mask) / max(1, gw * gh)
        entry["glyph_px"] = len(glyph_mask)
        entry["glyph_aspect"] = round(gw / max(1, gh), 3)
        entry["glyph_fill"] = round(fill, 3)
        best_name, best_score, ranked = classify_glyph(obs_fg)
        if best_name is None:
            entry["glyph"] = "unknown"
            entry["glyph_px"] = len(glyph_mask)
            entry["note"] = "glyph mask did not skeletonize"
            regions.append(entry)
            continue
        top = [(n, round(s, 4)) for n, s in ranked[:5]]
        second = ranked[1][1] if len(ranked) > 1 else None
        entry["scores"] = dict(top)
        entry["best_score"] = round(best_score, 4)
        if second is not None:
            entry["margin"] = round(second - best_score, 4)
        if best_score <= ACCEPT_SCORE:
            entry["glyph"] = best_name
            entry["confidence"] = round(max(0.0, 1.0 - best_score / ACCEPT_SCORE), 3)
        else:
            entry["glyph"] = "unknown"
            entry["nearest"] = best_name
            entry["confidence"] = 0.0
        regions.append(entry)

    icons = {str(r["object_id"]): r["glyph"] for r in regions
             if r.get("glyph") not in (None, "unknown", "solid")}
    return {
        "image": image_path,
        "size": [w, h],
        "candidates": len(regions),
        "regions": regions,
        "status_icons": icons,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image", help="image to inspect")
    ap.add_argument("--record", default=None,
                    help="path to a saved `eyes describe` JSON record "
                         "(skips running Mirage)")
    ap.add_argument("--all", action="store_true",
                    help="classify every detected object, not just "
                         "emblem/icon-shaped ones (diagnostic)")
    args = ap.parse_args(argv)

    record = get_record(args.image, args.record)
    result = classify_image(args.image, record, classify_all=args.all)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
