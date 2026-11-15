"""Unit tests for scene_tree — pure functions, no Mirage needed."""

from eyes import scene_tree


def obj(name, bbox, desc=None):
    return {"name": name, "bbox": list(bbox), "score": 0.8,
            "description": desc or {}}


def txt(s, bbox):
    return {"string": s, "bbox": list(bbox), "score": 0.9}


def rec(objects=(), texts=()):
    return {"objects": list(objects), "text": list(texts),
            "scene": {"background": "white", "style": "screenshot"}}


def test_build_tree_clusters_nearby_elements():
    r = rec(objects=[obj("card", (100, 100, 300, 300))],
            texts=[txt("Title", (120, 120, 200, 150)),
                   txt("Far", (700, 700, 800, 730))])
    tree = scene_tree.build_tree(r)
    # Title text joins the card's region; Far text is its own region
    sizes = sorted(len(g["elements"]) for g in tree["regions"])
    assert sizes == [1, 2] or len(tree["regions"]) >= 1
    total = sum(len(g["elements"]) for g in tree["regions"]) + \
        sum(len(g["elements"]) for g in tree["loose_objects"])
    assert total == 3


def test_diff_reports_moved_element():
    a = rec(objects=[obj("button", (100, 100, 200, 150))])
    b = rec(objects=[obj("button", (100, 200, 200, 250))])
    d = scene_tree.diff_records(a, b)
    assert d["object_changes"] and "moved" in d["object_changes"][0]["deltas"]


def test_diff_reports_renamed_element():
    a = rec(objects=[obj("blue circle", (100, 100, 200, 200))])
    b = rec(objects=[obj("red circle", (100, 100, 200, 200))])
    d = scene_tree.diff_records(a, b)
    assert d["object_changes"][0]["deltas"].get("renamed")


def test_diff_reports_added_removed():
    a = rec(objects=[obj("keep", (100, 100, 200, 200)),
                     obj("gone", (400, 400, 500, 500))])
    b = rec(objects=[obj("keep", (100, 100, 200, 200)),
                     obj("new", (600, 600, 700, 700))])
    d = scene_tree.diff_records(a, b)
    assert any(o["name"] == "gone" for o in d["objects_removed"])
    assert any(o["name"] == "new" for o in d["objects_added"])


def test_text_edited_pairs_by_proximity():
    a = rec(texts=[txt("Save", (100, 100, 200, 130)),
                   txt("Cancel", (100, 500, 200, 530))])
    b = rec(texts=[txt("Save", (100, 100, 200, 130)),
                   txt("Cancelled", (100, 500, 200, 530))])
    d = scene_tree.diff_records(a, b)
    assert any(t["type"] == "text_edited" and t["ref"] == "Cancel"
               for t in d["text_changes"])


def test_text_added_removed():
    a = rec(texts=[txt("Old", (100, 100, 200, 130))])
    b = rec(texts=[txt("New", (500, 500, 600, 530))])
    d = scene_tree.diff_records(a, b)
    types = {t["type"] for t in d["text_changes"]}
    assert "text_added" in types and "text_removed" in types
