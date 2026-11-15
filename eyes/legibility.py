"""Legibility signals — can the content actually be read?

Two facts per text region, both pure pixel math:

- contrast: WCAG-style ratio between the lightest and darkest deciles
  inside the text bbox. Glyph pixels are the extremes; background fills
  the middle. <3.0 fails WCAG AA even for large text.
- ocr_score: Mirage's own read confidence — a floor signal, since low
  contrast degrades OCR confidence before it degrades content.

Facts, not verdicts: a low ratio on a decorative watermark may be fine;
the reasoning layer judges intent.
"""

from __future__ import annotations

from .color import _open, denorm

_MIN_RATIO = 3.0
_LOW_OCR = 0.6


def _luma(px) -> float:
    r, g, b = px[0], px[1], px[2]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def text_legibility(image, record: dict,
                    min_ratio: float = _MIN_RATIO,
                    low_ocr: float = _LOW_OCR) -> list[dict]:
    """Per-text-region legibility facts from a compact Mirage record."""
    img = _open(image).convert("RGB")
    gray = img.convert("L")
    findings = []
    for t in record.get("text", []):
        if "bbox" not in t:
            continue
        x0, y0, x1, y1 = denorm(t["bbox"], img.width, img.height)
        crop = gray.crop((x0, y0, x1, y1))
        w, h = crop.size
        if w < 2 or h < 2:
            continue
        px = sorted(crop.getdata())
        n = len(px)
        # 2nd/98th percentile: glyph cores vs background. A 10% decile is
        # diluted by anti-aliased edges on thin text and underestimates
        # true contrast (measured: 3.28 for black-on-white at n//10).
        k = max(1, n // 50)
        lo = sum(px[:k]) / k / 255.0
        hi = sum(px[-k:]) / k / 255.0
        ratio = (hi + 0.05) / (lo + 0.05)
        score = t.get("score")
        flags = []
        if ratio < min_ratio:
            flags.append("low_contrast")
        if score is not None and score < low_ocr:
            flags.append("low_ocr_confidence")
        findings.append({
            "string": (t.get("string") or "")[:48],
            "bbox": t["bbox"],
            "contrast": round(ratio, 2),
            "ocr_score": score,
            "flags": flags,
        })
    return findings
