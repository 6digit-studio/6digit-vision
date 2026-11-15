"""Hierarchical scene tree + element-level diff.

The match_loop critique trail showed the gap: ask packs carry flat
object/text lists, so a critic must infer which element changed from
label churn. The scene tree gives elements stable POSITIONAL identity
(same philosophy as the location-first score matcher): regions are
spatial clusters, elements are objects+text inside them. `eyes diff`
then reports per-element changes — moved, resized, renamed, recolored,
text-edited — as a readable change list.

Pure functions over Mirage records — unit-testable without the model.
"""

from __future__ import annotations

from .score import _center01, _match_by_location, _aspect_sim, _pixel_aspect

# region merge padding in normalized units (~3% of frame each side)
_REGION_PAD = 30.0


def _elements(record: dict) -> list[dict]:
    """Flatten objects + text into typed elements with bboxes."""
    els = []
    for o in record.get("objects", []):
        if "bbox" in o:
            els.append({"kind": "object", "name": o.get("name", "?"),
                        "bbox": o["bbox"], "score": o.get("score"),
                        "description": o.get("description") or {}})
    for t in record.get("text", []):
        if "bbox" in t:
            els.append({"kind": "text", "name": t.get("string", ""),
                        "bbox": t["bbox"], "score": t.get("score")})
    return els


def _find(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: list[int], a: int, b: int) -> None:
    ra, rb = _find(parent, a), _find(parent, b)
    if ra != rb:
        parent[rb] = ra


def build_tree(record: dict) -> dict:
    """Cluster elements into spatial regions (union-find over padded
    bboxes), then nest elements inside. Reading order: top-to-bottom,
    left-to-right within each region."""
    els = _elements(record)
    n = len(els)
    parent = list(range(n))
    boxes = []
    for e in els:
        x0, y0, x1, y1 = e["bbox"]
        boxes.append((x0 - _REGION_PAD, y0 - _REGION_PAD,
                      x1 + _REGION_PAD, y1 + _REGION_PAD))
    for i in range(n):
        for j in range(i + 1, n):
            a, b = boxes[i], boxes[j]
            if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                _union(parent, i, j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(_find(parent, i), []).append(i)

    regions = []
    loose = []
    for root, idxs in groups.items():
        members = [els[i] for i in idxs]
        x0 = min(m["bbox"][0] for m in members)
        y0 = min(m["bbox"][1] for m in members)
        x1 = max(m["bbox"][2] for m in members)
        y1 = max(m["bbox"][3] for m in members)
        members.sort(key=lambda m: (m["bbox"][1], m["bbox"][0]))
        region = {"bbox": [x0, y0, x1, y1], "elements": members}
        if len(members) == 1 and members[0]["kind"] == "object":
            loose.append(region)  # singleton objects aren't regions
        else:
            regions.append(region)
    regions.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
    return {"regions": regions, "loose_objects": loose,
            "scene": record.get("scene") or {}}


def _text_changes(ref_els: list[dict], cand_els: list[dict]) -> list[dict]:
    """Text diff: exact-string matches are unchanged; unmatched strings
    pair by bbox proximity into 'edited', rest are added/removed."""
    ref_t = [e for e in ref_els if e["kind"] == "text"]
    cand_t = [e for e in cand_els if e["kind"] == "text"]
    cand_by_str: dict[str, list[int]] = {}
    for j, c in enumerate(cand_t):
        cand_by_str.setdefault(c["name"], []).append(j)
    used: set[int] = set()
    changes = []
    unmatched_ref = []
    for r in ref_t:
        if cand_by_str.get(r["name"]):
            j = cand_by_str[r["name"]].pop(0)
            used.add(j)
        else:
            unmatched_ref.append(r)
    unmatched_cand = [c for j, c in enumerate(cand_t) if j not in used]
    # pair leftovers by proximity -> edited text
    pairs, _ = _match_by_location(unmatched_ref, unmatched_cand, radius=0.2)
    paired_c = set(pairs.values())
    for i, j in pairs.items():
        changes.append({"type": "text_edited",
                        "ref": unmatched_ref[i]["name"],
                        "cand": unmatched_cand[j]["name"],
                        "bbox": unmatched_cand[j]["bbox"]})
    for i, r in enumerate(unmatched_ref):
        if i not in pairs:
            changes.append({"type": "text_removed", "ref": r["name"],
                            "bbox": r["bbox"]})
    for j, c in enumerate(unmatched_cand):
        if j not in paired_c:
            changes.append({"type": "text_added", "cand": c["name"],
                            "bbox": c["bbox"]})
    return changes


def diff_records(ref_rec: dict, cand_rec: dict,
                 ref_size: tuple[int, int] | None = None,
                 cand_size: tuple[int, int] | None = None) -> dict:
    """Element-level change list between two records. Objects match by
    location (score.py's matcher); text diffs by string+proximity."""
    ref_els = _elements(ref_rec)
    cand_els = _elements(cand_rec)
    ref_objs = [e for e in ref_els if e["kind"] == "object"]
    cand_objs = [e for e in cand_els if e["kind"] == "object"]

    pairs, used_c = _match_by_location(ref_objs, cand_objs)
    obj_changes = []
    for i, j in pairs.items():
        r, c = ref_objs[i], cand_objs[j]
        deltas = {}
        rc, cc = _center01(r["bbox"]), _center01(c["bbox"])
        dist = ((rc[0] - cc[0]) ** 2 + (rc[1] - cc[1]) ** 2) ** 0.5
        if dist > 0.01:
            deltas["moved"] = round(dist, 4)
        asp = _aspect_sim(r, c, ref_size, cand_size)
        if asp < 0.9:
            deltas["aspect_sim"] = round(asp, 3)
        rn = set((r.get("description") or {}).keys())
        cn = set((c.get("description") or {}).keys())
        if r["name"] != c["name"]:
            deltas["renamed"] = {"ref": r["name"], "cand": c["name"]}
        if deltas:
            obj_changes.append({"element": r["name"], "bbox": c["bbox"],
                                "deltas": deltas})
    matched_c = set(used_c)
    added = [{"name": c["name"], "bbox": c["bbox"]}
             for j, c in enumerate(cand_objs) if j not in matched_c]
    removed = [{"name": r["name"], "bbox": r["bbox"]}
               for i, r in enumerate(ref_objs) if i not in pairs]
    return {
        "object_changes": obj_changes,
        "objects_added": added,
        "objects_removed": removed,
        "text_changes": _text_changes(ref_els, cand_els),
        "counts": {"ref_objects": len(ref_objs), "cand_objects": len(cand_objs),
                   "ref_text": sum(1 for e in ref_els if e["kind"] == "text"),
                   "cand_text": sum(1 for e in cand_els if e["kind"] == "text")},
    }
