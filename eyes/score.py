"""Decomposed similarity score: candidate vs reference.

Every component is a pure function over compact Mirage records plus
palette stats, so it is unit-testable without the model. The composite
is a weighted sum — weights are v0 heuristics, tuned by use.
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

WEIGHTS = {
    "palette": 0.25,
    "objects": 0.30,
    "layout": 0.20,
    "text": 0.15,
    "scene": 0.10,
}

_COLOR_WORDS = {
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown",
    "black", "white", "gray", "grey", "cyan", "teal", "navy", "gold",
    "silver", "beige", "maroon", "olive", "coral", "lavender", "violet",
    "indigo", "turquoise", "magenta", "crimson", "khaki", "tan", "cream",
}
_SHAPE_WORDS = {
    "circle", "square", "rectangle", "rectangular", "triangle", "oval",
    "ellipse", "round", "rounded", "square", "circular", "triangular",
    "diamond", "hexagon", "pentagon", "sphere", "cube", "box", "banner",
    "button", "card", "icon", "logo", "text", "label", "title", "heading",
    "background", "border", "frame", "panel", "bar", "line",
}


_SYNONYMS = {
    "circular": "circle", "round": "circle",
    "rectangular": "rectangle", "square": "rectangle",
    "triangular": "triangle",
    "oval": "ellipse",
}

# Location-first matching: on UI imagery Mirage's names are unstable
# ("blue app icon" vs "orange light" for the same element), so identity
# is POSITION. radius in normalized [0,1] center-distance units —
# generous enough for detection jitter, tight enough that adjacent
# elements don't cross-claim.
_MATCH_RADIUS = 0.15


def _tokens(name: str) -> set[str]:
    return {_SYNONYMS.get(t, t) for t in re.findall(r"[a-z]+", name.lower())}


def _obj_signature(obj: dict) -> tuple[frozenset, frozenset]:
    """(color tokens, shape/other tokens) from name + description."""
    words = _tokens(obj.get("name", ""))
    desc = obj.get("description") or {}
    words |= _tokens(str(desc.get("color", ""))) | _tokens(str(desc.get("shape", "")))
    return frozenset(words & _COLOR_WORDS), frozenset(words - _COLOR_WORDS)


def _center01(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2000.0, (bbox[1] + bbox[3]) / 2000.0)


def _match_by_location(ref_objs: list[dict], cand_objs: list[dict],
                       radius: float = _MATCH_RADIUS
                       ) -> tuple[dict[int, int], set[int]]:
    """Greedy nearest-center matching. Returns (ref_idx->cand_idx, used_cand).

    Objects without bboxes cannot be located — excluded from matching
    (they surface as missing/extra).
    """
    loc = []
    for i, o in enumerate(ref_objs):
        if "bbox" in o:
            loc.append((i, _center01(o["bbox"])))
    cand_loc = [(j, _center01(c["bbox"])) for j, c in enumerate(cand_objs)
                if "bbox" in c]
    cand_idx_of = {j: c for j, c in enumerate(cand_objs)}
    pairs: list[tuple[float, int, int]] = []
    for i, rc in loc:
        for j, cc in cand_loc:
            d = ((rc[0] - cc[0]) ** 2 + (rc[1] - cc[1]) ** 2) ** 0.5
            if d <= radius:
                pairs.append((d, i, j))
    pairs.sort(key=lambda p: (p[0], p[1], p[2]))
    used_r: set[int] = set()
    used_c: set[int] = set()
    out: dict[int, int] = {}
    for _, i, j in pairs:
        if i in used_r or j in used_c:
            continue
        used_r.add(i)
        used_c.add(j)
        out[i] = j
    return out, used_c


def _pixel_aspect(bbox: list[float], size: tuple[int, int]) -> float:
    w, h = size
    bw = (bbox[2] - bbox[0]) / 1000.0 * w
    bh = (bbox[3] - bbox[1]) / 1000.0 * h
    return bw / max(bh, 1e-6)


def _aspect_sim(o: dict, b: dict,
                ref_size: tuple[int, int] | None,
                cand_size: tuple[int, int] | None) -> float:
    """1.0 identical aspect -> 0.0 at 2x ratio. Needs image sizes;
    neutral 1.0 when unknown (records carry no dimensions)."""
    if not ref_size or not cand_size or "bbox" not in o or "bbox" not in b:
        return 1.0
    try:
        ra = _pixel_aspect(o["bbox"], ref_size)
        ca = _pixel_aspect(b["bbox"], cand_size)
    except (KeyError, TypeError, ZeroDivisionError):
        return 1.0
    if ra <= 0 or ca <= 0:
        return 1.0
    return max(0.0, 1.0 - abs(math.log(ca / ra)) / math.log(2.0))


def _attr_sim(o: dict, b: dict,
              ref_size: tuple[int, int] | None,
              cand_size: tuple[int, int] | None) -> float:
    """Attribute agreement for a location-matched pair: token jaccard
    (color+shape+name words) blended with pixel-space aspect fidelity."""
    co, so = _obj_signature(o)
    cb, sb = _obj_signature(b)
    inter = len(co & cb) * 2.0 + len(so & sb)
    union = len(co | cb) * 2.0 + len(so | sb)
    tok = inter / union if union else 1.0
    asp = _aspect_sim(o, b, ref_size, cand_size)
    return 0.6 * tok + 0.4 * asp


def score_objects(ref_objs: list[dict], cand_objs: list[dict],
                  ref_size: tuple[int, int] | None = None,
                  cand_size: tuple[int, int] | None = None) -> dict:
    """Location-first object score: F1 over position-matched pairs,
    scaled by attribute agreement. Attribute diffs are reported as
    named facts, not match failures."""
    if not ref_objs and not cand_objs:
        return {"score": 1.0, "matched": 0, "missing": [], "extra": []}
    pairs, used_c = _match_by_location(ref_objs, cand_objs)
    matched = len(pairs)
    matched_cand = set(used_c)
    missing = [o.get("name") for i, o in enumerate(ref_objs) if i not in pairs]
    extra = [o.get("name") for j, o in enumerate(cand_objs) if j not in matched_cand]
    recall = matched / max(len(ref_objs), 1)
    precision = matched / max(len(cand_objs), 1)
    f1 = 2 * recall * precision / max(recall + precision, 1e-9)
    sims = []
    attr_changes = []
    for i, j in pairs.items():
        s = _attr_sim(ref_objs[i], cand_objs[j], ref_size, cand_size)
        sims.append(s)
        if s < 0.8:
            attr_changes.append({
                "ref": ref_objs[i].get("name"),
                "cand": cand_objs[j].get("name"),
                "attr_sim": round(s, 3),
            })
    attr = sum(sims) / len(sims) if sims else 0.0
    return {
        "score": round(f1 * attr, 4),
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "attr_sim": round(attr, 4),
        "attr_changes": attr_changes,
    }


def _center(bbox: list[float]) -> tuple[float, float]:
    return _center01(bbox)


def score_layout(ref_objs: list[dict], cand_objs: list[dict],
                 radius: float = _MATCH_RADIUS) -> dict:
    """Positional similarity: mean center distance over location-matched
    pairs; unmatched ref objects count as worst-case distance. Location
    matching bounds pair distances by `radius`, so this measures both
    'same elements' (matches) and 'same places' (distances)."""
    if not ref_objs:
        return {"score": 1.0 if not cand_objs else 0.0, "pairs": 0}
    pairs, _ = _match_by_location(ref_objs, cand_objs, radius)
    dists = []
    for i, o in enumerate(ref_objs):
        if i in pairs:
            ox, oy = _center(o["bbox"])
            bx, by = _center(cand_objs[pairs[i]]["bbox"])
            dists.append(((ox - bx) ** 2 + (oy - by) ** 2) ** 0.5)
        else:
            dists.append(1.0)
    mean_d = sum(dists) / len(dists)
    # 0 distance -> 1.0; ~0.35 normalized units (a third of frame) -> 0.0
    score = max(0.0, 1.0 - mean_d / 0.35)
    return {"score": round(score, 4), "mean_center_dist": round(mean_d, 4),
            "pairs": len(pairs)}


def score_palette(ref_pal: list[dict], cand_pal: list[dict]) -> dict:
    """Histogram intersection over quantized palette fractions."""
    ref = {p["hex"]: p["frac"] for p in ref_pal}
    cand = {p["hex"]: p["frac"] for p in cand_pal}
    keys = set(ref) | set(cand)
    inter = sum(min(ref.get(k, 0.0), cand.get(k, 0.0)) for k in keys)
    return {"score": round(inter, 4)}


def score_text(ref_strings: list[str], cand_strings: list[str]) -> dict:
    """Best-match string similarity between OCR outputs."""
    ref_n = [re.sub(r"\s+", "", s).lower() for s in ref_strings]
    cand_n = [re.sub(r"\s+", "", s).lower() for s in cand_strings]
    if not ref_n and not cand_n:
        return {"score": 1.0}
    if not ref_n or not cand_n:
        return {"score": 0.0}
    total = 0.0
    for r in ref_n:
        total += max(SequenceMatcher(None, r, c).ratio() for c in cand_n)
    return {"score": round(total / len(ref_n), 4)}


# Mirage's scene.style is a small-vocabulary categorical label that
# churns on near-identical images ("screenshot" -> "digital interface"
# -> "software interface" for the same UI). These tokens carry no
# discriminative information for UI-vs-UI comparison — strip them so
# the component measures scene CONTENT, not label luck. Genuine scene
# changes (letterbox bars, photo vs UI) survive: their tokens aren't
# in this list.
_SCENE_GENERIC = {
    "screenshot", "screen", "screenshots", "interface", "digital",
    "software", "website", "webpage", "web", "page", "application",
    "app", "window", "display", "ui", "gui", "desktop", "mobile",
    "photo", "image", "picture", "graphic", "graphics", "icon",
    "icons", "logo", "text", "button", "buttons", "menu", "view",
}


def _scene_content_tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]+", s) if t not in _SCENE_GENERIC}


def score_scene(ref_rec: dict, cand_rec: dict) -> dict:
    """Scene similarity on discriminative tokens only: generic
    UI-category labels are stripped before jaccard + string ratio so
    Mirage label churn can't crater the component on correct edits."""
    def flat(rec):
        scene = rec.get("scene") or {}
        return " ".join(str(v) for v in scene.values()).lower()
    r, c = flat(ref_rec), flat(cand_rec)
    rt, ct = _scene_content_tokens(r), _scene_content_tokens(c)
    if not rt and not ct:
        return {"score": 1.0}
    if not rt or not ct:
        return {"score": 0.0}
    jaccard = len(rt & ct) / max(len(rt | ct), 1)
    # ratio on the filtered token stream, not raw strings — generic
    # label churn can't dilute the content comparison
    rs = " ".join(sorted(rt))
    cs = " ".join(sorted(ct))
    ratio = SequenceMatcher(None, rs, cs).ratio()
    return {"score": round(0.5 * jaccard + 0.5 * ratio, 4)}


def score_pair(
    ref_rec: dict,
    cand_rec: dict,
    ref_pal: list[dict] | None = None,
    cand_pal: list[dict] | None = None,
    weights: dict | None = None,
    ref_size: tuple[int, int] | None = None,
    cand_size: tuple[int, int] | None = None,
) -> dict:
    """Full decomposed score. Returns components + weighted composite 0..1.
    ref_size/cand_size are (w,h) pixel dims — needed for aspect fidelity;
    omit and aspect scoring stays neutral."""
    w = weights or WEIGHTS
    ref_objs = ref_rec.get("objects", [])
    cand_objs = cand_rec.get("objects", [])
    components = {
        "palette": score_palette(ref_pal or [], cand_pal or []),
        "objects": score_objects(ref_objs, cand_objs, ref_size, cand_size),
        "layout": score_layout(ref_objs, cand_objs),
        "text": score_text(
            [t.get("string", "") for t in ref_rec.get("text", [])],
            [t.get("string", "") for t in cand_rec.get("text", [])],
        ),
        "scene": score_scene(ref_rec, cand_rec),
    }
    total_w = sum(w.values())
    composite = sum(components[k]["score"] * w[k] for k in components) / total_w
    return {
        "score": round(composite * 100, 1),
        "components": components,
        "weights": w,
    }
