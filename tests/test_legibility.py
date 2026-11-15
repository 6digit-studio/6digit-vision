"""Tests for legibility + interior-edge detectors."""

from PIL import Image, ImageDraw

from eyes import layout, legibility


def _rec_with_text(bbox, string="HELLO", score=0.9):
    return {"text": [{"string": string, "bbox": bbox, "score": score}]}


def test_legibility_flags_low_contrast():
    # white bg, near-white text -> ratio ~1.2
    img = Image.new("RGB", (200, 100), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 40), "FINE PRINT", fill=(214, 214, 214))
    # bbox covering the text area in Mirage 1000-space
    rec = _rec_with_text([100, 400, 600, 500])
    findings = legibility.text_legibility(img, rec)
    assert findings and findings[0]["contrast"] < 3.0
    assert "low_contrast" in findings[0]["flags"]


def test_legibility_passes_black_on_white():
    img = Image.new("RGB", (200, 100), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 40), "READABLE", fill="black")
    rec = _rec_with_text([80, 380, 700, 520])
    findings = legibility.text_legibility(img, rec)
    assert findings[0]["contrast"] > 10
    assert findings[0]["flags"] == []


def test_legibility_low_ocr_flag():
    img = Image.new("RGB", (200, 100), "white")
    d = ImageDraw.Draw(img)
    d.text((20, 40), "DIM", fill="black")
    rec = _rec_with_text([80, 380, 700, 520], score=0.4)
    findings = legibility.text_legibility(img, rec)
    assert "low_ocr_confidence" in findings[0]["flags"]


def test_interior_edge_lines_finds_card_edge():
    # dark card on light bg -> strong vertical edges at card borders
    img = Image.new("RGB", (200, 200), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([50, 50, 150, 150], fill=(30, 30, 30))
    lines = layout.interior_edge_lines(img, min_strength=20, min_gap=8)
    assert any(abs(x - 50) <= 3 or abs(x - 150) <= 3 for x in lines["vertical"])


def test_text_edge_flush_detects_clip():
    # card with a hard right edge; text bbox ending flush against it
    img = Image.new("RGB", (200, 200), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 120, 120], fill=(240, 240, 240))
    d.rectangle([120, 20, 121, 120], fill="black")  # 1px edge line at x=120
    rec = _rec_with_text([50, 300, 600, 400])  # ends at x=120px (600/1000*200)
    findings = layout.text_edge_flush(img, rec, tol_px=10, min_strength=10)
    assert findings, "expected a flush finding"
    assert findings[0]["flush"][0]["side"] == "right"
