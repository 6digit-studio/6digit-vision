"""Unit tests for the score module — pure functions, no Mirage needed."""

from eyes import score


def obj(name, bbox=(100, 100, 300, 300), color=None, shape=None):
    desc = {}
    if color:
        desc["color"] = color
    if shape:
        desc["shape"] = shape
    return {"id": 1, "name": name, "bbox": list(bbox), "description": desc}


def test_identical_records_score_perfect():
    rec = {
        "scene": {"background": "white"},
        "objects": [obj("red circle", color="red", shape="circle")],
        "text": [{"string": "HELLO"}],
    }
    r = score.score_pair(rec, rec, ref_pal=[{"hex": "#ff0000", "frac": 1.0}],
                         cand_pal=[{"hex": "#ff0000", "frac": 1.0}])
    assert r["score"] == 100.0


def test_missing_object_lowers_score():
    ref = {"objects": [obj("red circle", color="red", shape="circle"),
                       obj("blue square", color="blue", shape="square")]}
    cand = {"objects": [obj("red circle", color="red", shape="circle")]}
    comp = score.score_objects(ref["objects"], cand["objects"])
    assert comp["matched"] == 1
    assert comp["missing"] == ["blue square"]
    assert comp["score"] < 1.0


def test_wrong_color_does_not_match():
    ref = [obj("circle", color="red", shape="circle")]
    cand = [obj("circle", color="blue", shape="circle")]
    comp = score.score_objects(ref, cand)
    assert comp["matched"] == 0
    assert comp["score"] == 0.0


def test_layout_prefers_same_position():
    a = [obj("red circle", bbox=(100, 100, 200, 200), color="red", shape="circle")]
    same = [obj("red circle", bbox=(100, 100, 200, 200), color="red", shape="circle")]
    moved = [obj("red circle", bbox=(700, 700, 800, 800), color="red", shape="circle")]
    s_same = score.score_layout(a, same)["score"]
    s_moved = score.score_layout(a, moved)["score"]
    assert s_same > s_moved


def test_text_similarity():
    assert score.score_text(["HELLO42"], ["HELLO42"])["score"] == 1.0
    assert score.score_text(["HELLO"], ["WORLD"])["score"] < 0.5
    assert score.score_text([], ["X"])["score"] == 0.0


def test_palette_intersection():
    a = [{"hex": "#ff0000", "frac": 0.5}, {"hex": "#0000ff", "frac": 0.5}]
    b = [{"hex": "#ff0000", "frac": 1.0}]
    comp = score.score_palette(a, b)
    assert comp["score"] == 0.5
