"""Decomposed similarity score: candidate vs reference.

Every component is a pure function over compact Mirage records plus
palette stats, so it is unit-testable without the model. The composite
is a weighted sum — weights are v0 heuristics, tuned by use.
"""

from __future__ import annotations

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


def _tokens(name: str) -> set[str]:
    return {_SYNONYMS.get(t, t) for t in re.findall(r"[a-z]+", name.lower())}


def _obj_signature(obj: dict) -> tuple[frozenset, frozenset]:
    """(color tokens, shape/other tokens) from name + description."""
    words = _tokens(obj.get("name", ""))
    desc = obj.get("description") or {}
    words |= _tokens(str(desc.get("color", ""))) | _tokens(str(desc.get("shape", "")))
    return frozenset(words & _COLOR_WORDS), frozenset(words - _COLOR_WORDS)


def _greedy_match(a: list[dict], b: list[dict]) -> list[tuple[dict, dict | None]]:
    """Match objects by color+shape token overlap; returns (a_obj, b_obj|None).

    Hard rule: if both objects name colors (or both name shapes) and the
    sets are disjoint, they cannot match — a red circle is not a blue
    circle, it is a missing red circle plus an extra blue one.
    """
    remaining = list(b)
    pairs = []
    for obj in a:
        ca, sa = _obj_signature(obj)
        best_i, best_score = -1, 0.0
        for i, cand in enumerate(remaining):
            cb, sb = _obj_signature(cand)
            if (ca and cb and not ca & cb) or (sa and sb and not sa & sb):
                continue
            score = len(ca & cb) * 2.0 + len(sa & sb)
            if score > best_score:
                best_i, best_score = i, score
        if best_i >= 0 and best_score > 0:
            pairs.append((obj, remaining.pop(best_i)))
        else:
            pairs.append((obj, None))
    return pairs


def score_objects(ref_objs: list[dict], cand_objs: list[dict]) -> dict:
    """Recall/precision over object identity (color+shape signature)."""
    if not ref_objs and not cand_objs:
        return {"score": 1.0, "matched": 0, "missing": [], "extra": []}
    pairs = _greedy_match(ref_objs, cand_objs)
    matched = sum(1 for _, b in pairs if b is not None)
    matched_cand_ids = {id(b) for _, b in pairs if b is not None}
    missing = [o.get("name") for o, b in pairs if b is None]
    extra = [o.get("name") for o in cand_objs if id(o) not in matched_cand_ids]
    recall = matched / max(len(ref_objs), 1)
    precision = matched / max(len(cand_objs), 1)
    f1 = 2 * recall * precision / max(recall + precision, 1e-9)
    return {
        "score": round(f1, 4),
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }


def _center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2 / 1000.0, (bbox[1] + bbox[3]) / 2 / 1000.0)


def score_layout(ref_objs: list[dict], cand_objs: list[dict]) -> dict:
    """Mean center distance over matched objects, in normalized coords."""
    pairs = [(o, b) for o, b in _greedy_match(ref_objs, cand_objs) if b is not None]
    if not pairs:
        return {"score": 0.0, "pairs": 0}
    dists = []
    for o, b in pairs:
        ox, oy = _center(o["bbox"])
        bx, by = _center(b["bbox"])
        dists.append(((ox - bx) ** 2 + (oy - by) ** 2) ** 0.5)
    mean_d = sum(dists) / len(dists)
    # 0 distance -> 1.0; ~0.35 normalized units (a third of frame) -> 0.0
    score = max(0.0, 1.0 - mean_d / 0.35)
    return {"score": round(score, 4), "mean_center_dist": round(mean_d, 4), "pairs": len(pairs)}


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


def score_scene(ref_rec: dict, cand_rec: dict) -> dict:
    """Scene background/style similarity via token overlap + string ratio."""
    def flat(rec):
        scene = rec.get("scene") or {}
        return " ".join(str(v) for v in scene.values()).lower()
    r, c = flat(ref_rec), flat(cand_rec)
    if not r and not c:
        return {"score": 1.0}
    if not r or not c:
        return {"score": 0.0}
    rt, ct = set(re.findall(r"[a-z]+", r)), set(re.findall(r"[a-z]+", c))
    jaccard = len(rt & ct) / max(len(rt | ct), 1)
    ratio = SequenceMatcher(None, r, c).ratio()
    return {"score": round(0.5 * jaccard + 0.5 * ratio, 4)}


def score_pair(
    ref_rec: dict,
    cand_rec: dict,
    ref_pal: list[dict] | None = None,
    cand_pal: list[dict] | None = None,
    weights: dict | None = None,
) -> dict:
    """Full decomposed score. Returns components + weighted composite 0..1."""
    w = weights or WEIGHTS
    ref_objs = ref_rec.get("objects", [])
    cand_objs = cand_rec.get("objects", [])
    components = {
        "palette": score_palette(ref_pal or [], cand_pal or []),
        "objects": score_objects(ref_objs, cand_objs),
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
