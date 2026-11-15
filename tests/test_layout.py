"""Tests for layout/overflow detectors."""

import pytest
from PIL import Image, ImageDraw

from eyes import layout


def _img(draw_fn, size=(200, 200), bg="white"):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    draw_fn(d)
    return img


def test_edge_contact_clean_margins():
    img = _img(lambda d: d.rectangle([40, 40, 160, 160], fill="black"))
    ec = layout.edge_contact(img)
    assert all(ec[s] == 0.0 for s in ("top", "right", "bottom", "left"))
    assert ec["touching"] == []


def test_edge_contact_bleed_right():
    # black bar running off the right edge
    img = _img(lambda d: d.rectangle([40, 40, 260, 160], fill="black"))
    ec = layout.edge_contact(img)
    assert ec["right"] > 0.5
    assert "right" in ec["touching"]
    assert ec["left"] == 0.0


def test_edge_contact_full_bleed_bg_not_flagged():
    # solid non-white image: dominant color IS the content, edges match bg
    img = Image.new("RGB", (200, 200), "black")
    ec = layout.edge_contact(img)
    assert all(ec[s] < 0.05 for s in ("top", "right", "bottom", "left"))


def test_objects_at_edge():
    rec = {"objects": [
        {"name": "card", "bbox": [100, 100, 500, 500]},
        {"name": "cutoff", "bbox": [850, 400, 1000, 600], "score": 0.3},
        {"name": "near-edge-ok", "bbox": [100, 920, 400, 960], "score": 0.9},
    ]}
    hits = layout.objects_at_edge(rec)
    by_name = {h["name"]: h for h in hits}
    assert "cutoff" in by_name and "right" in by_name["cutoff"]["sides"]
    assert by_name["cutoff"]["suspect"] is True
    assert by_name["near-edge-ok"]["suspect"] is False


def test_bbox_overlaps_flags_crossing_not_nesting():
    rec = {"objects": [
        {"name": "phone", "bbox": [100, 100, 900, 900]},
        {"name": "screen", "bbox": [150, 400, 850, 850]},   # contained -> skip
        {"name": "icon-a", "bbox": [200, 200, 300, 300]},
        {"name": "icon-b", "bbox": [240, 240, 340, 340]},   # overlaps icon-a
    ]}
    pairs = layout.bbox_overlaps(rec)
    assert len(pairs) == 1
    assert {pairs[0]["a"], pairs[0]["b"]} == {"icon-a", "icon-b"}


def test_layout_report_combined():
    img = _img(lambda d: d.rectangle([40, 40, 260, 160], fill="black"))
    rep = layout.layout_report(img)
    assert "edge_contact" in rep
    assert rep["edge_contact"]["right"] > 0.5
