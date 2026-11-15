"""Tests for the temporal layer — pure PIL images, no Mirage needed."""

import pytest
from PIL import Image, ImageDraw

from eyes import temporal


def _img(fn=None, size=(100, 100), bg="white"):
    img = Image.new("RGB", size, bg)
    if fn:
        ImageDraw.Draw(img).__class__  # noqa
        d = ImageDraw.Draw(img)
        fn(d)
    return img


def test_frame_diff_identical():
    img = _img(lambda d: d.rectangle([10, 10, 50, 50], fill="black"))
    r = temporal.frame_diff(img, img)
    assert r["changed_pct"] == 0.0
    assert "diff_bbox" not in r


def test_frame_diff_detects_change_region():
    a = _img()
    b = _img(lambda d: d.rectangle([60, 60, 90, 90], fill="red"))
    r = temporal.frame_diff(a, b)
    assert r["changed_pct"] > 0
    # change is bottom-right quadrant -> bbox should sit there
    x0, y0, x1, y1 = r["diff_bbox"]
    assert x0 > 400 and y0 > 400


def test_label_stability():
    ra = {"objects": [{"name": "red circle"}, {"name": "blue square"}]}
    rb = {"objects": [{"name": "red circle"}, {"name": "green triangle"}]}
    r = temporal.label_stability(ra, rb)
    assert 0 < r["score"] < 1
    assert r["only_a"] == ["blue square"]
    assert r["only_b"] == ["green triangle"]


def test_ocr_overlap():
    ra = {"text": [{"string": "HELLO 42"}, {"string": "MON"}]}
    rb = {"text": [{"string": "HELLO43"}, {"string": "TUE"}]}
    r = temporal.ocr_overlap(ra, rb)
    assert r["score"] == 0.5
    assert r["unmatched"] == ["mon"]


def test_reel_report_pixel_only(tmp_path):
    a = _img()
    b = _img(lambda d: d.rectangle([10, 10, 50, 50], fill="black"))
    pa, pb = tmp_path / "a.png", tmp_path / "b.png"
    a.save(pa); b.save(pb)
    rep = temporal.reel_report([str(pa), str(pb)], with_records=False)
    assert rep["frames"] == 2
    assert rep["pairs"][0]["pixel"]["changed_pct"] > 0
    assert "labels" not in rep["pairs"][0]


def test_reel_report_directory_input(tmp_path):
    for i, fill in enumerate([None, "black"]):
        img = _img(lambda d, f=fill: d.rectangle([5, 5, 20, 20], fill=f) if f else None)
        img.save(tmp_path / f"f{i}.png")
    rep = temporal.reel_report([str(tmp_path)], with_records=False)
    assert rep["frames"] == 2
