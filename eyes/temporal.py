"""Temporal layer — frame differencing and cross-frame coherence.

Screenshots-only operation: given a sequence of frames (or a directory of
numbered frames), report what changed between consecutive frames and
whether the semantic record stayed coherent. No prompt, no reference —
just pixels and Mirage records.

- frame_diff: pixel-level change fraction, mean abs diff, change bbox.
- label_stability: object-name-set Jaccard between two records.
- ocr_overlap: fraction of frame A's strings still present in frame B.
- reel_report: per-frame summaries + pairwise diffs for a sequence.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from PIL import Image

from .color import _open, palette

_MAX_DIM = 256


def _prep_pair(a, b, max_dim: int = _MAX_DIM):
    """Load two images resized to a common canvas (first image's aspect)."""
    ia, ib = _open(a), _open(b)
    scale = min(1.0, max_dim / max(ia.width, ia.height))
    w, h = round(ia.width * scale), round(ia.height * scale)
    return ia.resize((w, h)).convert("RGB"), ib.resize((w, h)).convert("RGB"), (w, h)


def frame_diff(a, b, tol: int = 24, max_dim: int = _MAX_DIM) -> dict:
    """Pixel diff between two frames.

    changed_pct: fraction of pixels whose max channel delta > tol.
    mean_abs_diff: mean per-channel absolute difference (0-255).
    diff_bbox: bounding box of changed pixels, normalized to [0,1000]
    per axis (same space as Mirage) so it composes with records.
    """
    ia, ib, (w, h) = _prep_pair(a, b, max_dim)
    pa, pb = ia.load(), ib.load()
    minx, miny, maxx, maxy = w, h, -1, -1
    changed = total_diff = n = 0
    for y in range(h):
        for x in range(w):
            da = pa[x, y]
            db = pb[x, y]
            d = max(abs(da[0] - db[0]), abs(da[1] - db[1]), abs(da[2] - db[2]))
            total_diff += d
            n += 1
            if d > tol:
                changed += 1
                if x < minx: minx = x
                if y < miny: miny = y
                if x > maxx: maxx = x
                if y > maxy: maxy = y
    out = {
        "changed_pct": round(changed / n, 4) if n else 0.0,
        "mean_abs_diff": round(total_diff / n, 2) if n else 0.0,
        "size": [w, h],
    }
    if maxx >= 0:
        out["diff_bbox"] = [
            round(minx / w * 1000), round(miny / h * 1000),
            round((maxx + 1) / w * 1000), round((maxy + 1) / h * 1000),
        ]
    return out


def _name_set(record: dict) -> set[str]:
    names = set()
    for obj in record.get("objects", []):
        names.add(re.sub(r"\s+", " ", (obj.get("name") or "").strip().lower()))
    return names


def label_stability(rec_a: dict, rec_b: dict) -> dict:
    """Jaccard similarity of object-name sets between two records."""
    a, b = _name_set(rec_a), _name_set(rec_b)
    if not a and not b:
        return {"score": 1.0, "only_a": [], "only_b": []}
    inter = a & b
    union = a | b
    return {
        "score": round(len(inter) / len(union), 4) if union else 1.0,
        "only_a": sorted(a - b),
        "only_b": sorted(b - a),
    }


def ocr_overlap(rec_a: dict, rec_b: dict, thresh: float = 0.8) -> dict:
    """Fraction of A's OCR strings with a fuzzy match in B."""
    sa = [re.sub(r"\s+", "", t.get("string", "")).lower()
          for t in rec_a.get("text", []) if t.get("string")]
    sb = [re.sub(r"\s+", "", t.get("string", "")).lower()
          for t in rec_b.get("text", []) if t.get("string")]
    if not sa:
        return {"score": 1.0 if not sb else 0.0, "unmatched": []}
    unmatched = []
    for s in sa:
        if not any(SequenceMatcher(None, s, t).ratio() >= thresh for t in sb):
            unmatched.append(s)
    return {"score": round(1 - len(unmatched) / len(sa), 4),
            "unmatched": unmatched[:20]}


def frame_summary(image, record: dict | None = None) -> dict:
    """Compact per-frame facts: palette top-3, OCR strings, object names."""
    out = {"palette": palette(image, n=3)}
    if record is not None:
        out["objects"] = sorted(_name_set(record))
        out["text"] = [t.get("string", "") for t in record.get("text", [])]
        out["scene"] = record.get("scene") or {}
    return out


def _resolve(inputs: list[str]) -> list[Path]:
    """Expand dirs (sorted image files) and keep explicit file order."""
    paths: list[Path] = []
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            paths.extend(sorted(f for f in p.iterdir()
                                if f.suffix.lower() in exts))
        else:
            paths.append(p)
    return paths


def reel_report(inputs: list[str], *, with_records: bool = True,
                tol: int = 24) -> dict:
    """Coherence report over a frame sequence.

    inputs: image paths and/or directories (sorted). Consecutive pairs get
    frame_diff always; label_stability + ocr_overlap when records are on.
    """
    from . import mirage

    paths = _resolve(inputs)
    if len(paths) < 2:
        raise ValueError("reel needs at least 2 frames")

    frames = []
    records = []
    for p in paths:
        rec = mirage.describe(p) if with_records else None
        records.append(rec)
        frames.append({"file": str(p), **frame_summary(p, rec)})

    pairs = []
    for i in range(len(paths) - 1):
        pair = {
            "pair": [paths[i].name, paths[i + 1].name],
            "pixel": frame_diff(paths[i], paths[i + 1], tol=tol),
        }
        if with_records:
            pair["labels"] = label_stability(records[i], records[i + 1])
            pair["ocr"] = ocr_overlap(records[i], records[i + 1])
        pairs.append(pair)

    return {
        "frames": len(paths),
        "with_records": with_records,
        "frames_detail": frames,
        "pairs": pairs,
    }
