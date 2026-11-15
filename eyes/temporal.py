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


def estimate_vshift(a_path, b_path, max_dim: int = 256) -> dict:
    """Estimate vertical scroll offset between frames via row-profile
    correlation on downsampled grayscale. Returns dy in ORIGINAL pixels
    (positive = B's content sits higher = scrolled down) plus confidence.
    """
    import numpy as np
    from PIL import Image

    ia = Image.open(str(a_path)).convert("L")
    ib = Image.open(str(b_path)).convert("L")
    w, h = ia.size
    scale = min(1.0, max_dim / max(w, h))
    tw, th = max(8, int(w * scale)), max(8, int(h * scale))
    A = np.asarray(ia.resize((tw, th)), dtype=np.float32)
    B = np.asarray(ib.resize((tw, th)), dtype=np.float32)
    best_dy, best_err = 0, float("inf")
    # full-height span: viewport scrolls move content up to ~1 viewport —
    # th//3 capped the search at ~265px original and missed 700px steps
    span = th
    for dy in range(-span, span + 1, 4):
        if dy >= 0:
            if th - dy < 8:
                continue
            err = float(np.abs(A[dy:] - B[:th - dy]).mean())
        else:
            if th + dy < 8:
                continue
            err = float(np.abs(A[:th + dy] - B[-dy:]).mean())
        if err < best_err:
            best_err, best_dy = err, dy
    # confidence: error at best vs error at dy=0 — a real shift wins big
    err0 = float(np.abs(A - B).mean())
    conf = round(max(0.0, 1.0 - best_err / max(err0, 1e-6)), 3)
    return {"dy_px": round(best_dy / scale, 1), "confidence": conf,
            "best_err": round(best_err, 2), "zero_err": round(err0, 2)}


def scroll_persistence(rec_a: dict, rec_b: dict, dy_px: float,
                       img_h: int) -> dict:
    """Scroll-compensated element persistence: shift B's bboxes down by
    the scroll offset (B content sits dy_px higher than A's frame), then
    count A objects/text with a positional match in B. Separates
    'new content scrolled in' from 'detector churn' — the reel record-
    stability upgrade the web-real reel eval named."""
    dy_norm = dy_px / img_h * 1000.0 if img_h else 0.0

    def shifted(rec):
        out = []
        for o in rec.get("objects", []):
            if "bbox" in o:
                x0, y0, x1, y1 = o["bbox"]
                out.append({"name": o.get("name"), "kind": "object",
                            "bbox": [x0, y0 + dy_norm, x1, y1 + dy_norm]})
        for t in rec.get("text", []):
            if "bbox" in t:
                x0, y0, x1, y1 = t["bbox"]
                out.append({"name": t.get("string", ""), "kind": "text",
                            "bbox": [x0, y0 + dy_norm, x1, y1 + dy_norm]})
        return out

    a_els = [{"name": o.get("name"), "kind": "object", "bbox": o["bbox"]}
             for o in rec_a.get("objects", []) if "bbox" in o]
    a_els += [{"name": t.get("string", ""), "kind": "text", "bbox": t["bbox"]}
              for t in rec_a.get("text", []) if "bbox" in t]
    b_els = shifted(rec_b)

    def center(b):
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

    persistent, departed = 0, []
    for a in a_els:
        ac = center(a["bbox"])
        hit = any(e["kind"] == a["kind"] and
                  ((center(e["bbox"])[0] - ac[0]) ** 2 +
                   (center(e["bbox"])[1] - ac[1]) ** 2) ** 0.5 < 80.0
                  for e in b_els)
        if hit:
            persistent += 1
        else:
            departed.append(a["name"])
    total = len(a_els)
    return {"dy_norm": round(dy_norm, 1), "elements_a": total,
            "persistent": persistent,
            "persistent_frac": round(persistent / total, 3) if total else 1.0,
            "departed": departed[:20]}


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
            try:
                from PIL import Image
                sh = estimate_vshift(paths[i], paths[i + 1])
                if sh["confidence"] >= 0.15:
                    ih = Image.open(str(paths[i + 1])).height
                    pair["scroll"] = scroll_persistence(
                        records[i], records[i + 1], sh["dy_px"], ih)
                    pair["scroll"]["dy_px"] = sh["dy_px"]
                    pair["scroll"]["confidence"] = sh["confidence"]
            except Exception:
                pass
        # static-pair fact: near-zero pixel change. Mid-sequence static is
        # the freeze signature; first/last holds are legitimate — the
        # reasoning layer judges position, the instrument reports the fact.
        pair["static"] = pair["pixel"]["changed_pct"] < 0.001
        pairs.append(pair)

    report = {
        "frames": len(paths),
        "with_records": with_records,
        "frames_detail": frames,
        "pairs": pairs,
        "static_pairs": [p["pair"] for p in pairs if p.get("static")],
    }
    report["lifecycle"] = _lifecycle_diff(report)
    report["strobe"] = _strobe(report, paths)
    return report


def _load_detector(rel: str):
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "detectors" / rel
    spec = importlib.util.spec_from_file_location(
        rel.replace("/", "_").replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strobe(report: dict, paths: list) -> dict:
    """Strobe/flicker + motion-coherence via detectors/strobe catalog
    entry. json_path anchors frame resolution to the input dir."""
    try:
        mod = _load_detector("strobe/strobe.py")
        strobes, alternating, stats = mod.find_strobes(
            report.get("frames_detail") or [], 3, 1)
        anchor = str(paths[0]) if paths else None
        coherence = mod.motion_coherence(report, json_path=anchor)
        return {"strobes": strobes, "alternating": alternating,
                "stats": stats, "motion_coherence": coherence}
    except Exception as e:
        return {"unavailable": type(e).__name__}


def _lifecycle_diff(report: dict) -> dict:
    """Entity-lifecycle departures via the verified detector catalog entry
    (detectors/lifecycle-diff). Lazy-loaded: detectors/ is the catalog,
    eyes/ stays import-clean without it."""
    import importlib.util

    path = (Path(__file__).resolve().parents[1]
            / "detectors" / "lifecycle-diff" / "lifecycle_diff.py")
    spec = importlib.util.spec_from_file_location("lifecycle_diff", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.detect(report, min_present=2, min_absent=2)
