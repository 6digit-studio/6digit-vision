"""interrogate — the question battery.

Standing + conditional probes asked of every screenshot, producing a
semantic fact sheet: {question, answer, probe, confidence}. This is
the intake questionnaire between raw perception (describe) and any
generation/critique step — the screenshot spawns its own questions.

Honesty contract: a question with no working probe reports
"unmeasured" — never a guessed answer.
"""
from __future__ import annotations

from . import color, mirage, structure, zoom


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _text_px_bbox(t, W, H):
    """Mirage text bboxes are [0,1000]-normalized per axis -> pixels."""
    x0, y0, x1, y1 = t["bbox"]
    return (x0 / 1000 * W, y0 / 1000 * H, x1 / 1000 * W, y1 / 1000 * H)


def _accent_blobs(image, grid_n=40, sat_thr=40, val_thr=80):
    """Find saturated-bright blobs (selection rings, accents, icons).

    Downsamples to grid_n x grid_n cells; a cell is 'hot' if it has
    enough saturated pixels. Returns connected hot-cell clusters with
    pixel-space centroids and mean color.
    """
    import numpy as np
    from PIL import Image

    img = image if not isinstance(image, (str,)) else Image.open(image)
    img = img.convert("RGB")
    W, H = img.size
    a = np.asarray(img).astype(int)
    mx = a.max(axis=2); mn = a.min(axis=2)
    sat = mx - mn
    hot = (sat > sat_thr) & (mx > val_thr)
    # cell aggregation
    cw, ch = W / grid_n, H / grid_n
    cells = []
    for gy in range(grid_n):
        for gx in range(grid_n):
            x0, y0 = int(gx * cw), int(gy * ch)
            x1, y1 = int((gx + 1) * cw), int((gy + 1) * ch)
            frac = hot[y0:y1, x0:x1].mean() if x1 > x0 and y1 > y0 else 0
            if frac > 0.15:
                cells.append((gx, gy, frac))
    # cluster adjacent hot cells (8-conn)
    cellset = {(gx, gy) for gx, gy, _ in cells}
    seen, clusters = set(), []
    for c in cellset:
        if c in seen:
            continue
        stack, cl = [c], []
        seen.add(c)
        while stack:
            cur = stack.pop(); cl.append(cur)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (cur[0] + dx, cur[1] + dy)
                    if nb in cellset and nb not in seen:
                        seen.add(nb); stack.append(nb)
        clusters.append(cl)
    blobs = []
    for cl in clusters:
        gxs = [c[0] for c in cl]; gys = [c[1] for c in cl]
        x0, x1 = min(gxs) * cw, (max(gxs) + 1) * cw
        y0, y1 = min(gys) * ch, (max(gys) + 1) * ch
        sub = a[int(y0):int(y1), int(x0):int(x1)]
        m = hot[int(y0):int(y1), int(x0):int(x1)]
        fill = m.mean() if m.size else 0
        mean_rgb = sub[m].mean(axis=0).round().astype(int).tolist() if m.any() else None
        blobs.append({
            "bbox_px": [round(v) for v in (x0, y0, x1 - x0, y1 - y0)],
            "centroid_px": [round((x0 + x1) / 2), round((y0 + y1) / 2)],
            "mean_rgb": mean_rgb,
            "fill": round(float(fill), 3),
            "shape": "ring-ish" if 0.1 < fill < 0.6 else ("disc-ish" if fill >= 0.6 else "sparse"),
        })
    blobs.sort(key=lambda b: -b["bbox_px"][2] * b["bbox_px"][3])
    return blobs


def interrogate(image) -> dict:
    from PIL import Image

    img = Image.open(str(image)).convert("RGB") if not hasattr(image, "size") else image
    W, H = img.size
    rec = mirage.describe(img)
    texts = [t for t in rec.get("text", []) if t.get("score", 0) > 0.4 and t.get("bbox")]
    s = structure.summarize(texts)
    pal = color.palette(img)
    gstats = color.grid_stats(img, cols=24)
    blobs = _accent_blobs(img)

    qs = []

    def add(qid, question, answer, probe, confidence="measured"):
        qs.append({"id": qid, "question": question, "answer": answer,
                   "probe": probe, "confidence": confidence})

    # --- standing battery ---
    flat = sum(1 for row in gstats for c in row if c["std"] < 15) / (len(gstats) * len(gstats[0]))
    add("background", "What kind of background?",
        ("flat dark UI" if flat > 0.8 else "mixed/textured") +
        f"; dominant {pal[0]['hex']} ({pal[0]['frac']*100:.0f}%)",
        "grid+palette")

    bright = [(x, y, c) for y, row in enumerate(gstats) for x, c in enumerate(row)]
    bright.sort(key=lambda t: -sum(t[2]["mean"]))
    if bright and sum(bright[0][2]["mean"]) > 330:
        x, y, c = bright[0]
        add("glow", "Is there a glow/gradient accent?",
            f"bright region near cell ({x},{y}) mean_rgb={c['mean']}",
            "grid")
    else:
        add("glow", "Is there a glow/gradient accent?", "none detected", "grid")

    add("text_inventory", "What text is present?",
        {"count": len(texts), "strings": [t.get("string") for t in texts]},
        "describe+structure")

    fam = s.get("inference", {}).get("kind")
    add("layout_family", "What layout family?",
        fam or f"unstructured ({s['n_rows']} rows x {s['n_cols']} cols detected)",
        "structure")

    # NOTE: structure rows/cells and Mirage bboxes are all [0,1000]
    # normalized — keep everything in that space until pixel ops.
    def _row_items(r, tol=25):
        return [t for t in texts
                if abs((t["bbox"][1] + t["bbox"][3]) / 2 - r["y"]) <= tol]

    # alignment per row: classify each row's text block vs image center
    aligns = []
    for r in s["grid"]:
        items = _row_items(r)
        if not items:
            continue
        x0 = min(t["bbox"][0] for t in items)
        x1 = max(t["bbox"][2] for t in items)
        mid = (x0 + x1) / 2
        if x1 - x0 > 700:
            a = "wide"
        elif mid < 400:
            a = "left"
        elif mid > 600:
            a = "right"
        else:
            a = "center"
        aligns.append({"y": r["y"], "alignment": a,
                       "text": " ".join(i.get("string", "") for i in items)[:40]})
    add("alignment", "How are text blocks aligned?", aligns, "structure+bboxes")

    # selection / accent state — report all blobs, map to nearest
    # day-number cell when a structure grid exists; zoom each blob
    # to OCR the label it surrounds (full-frame OCR misses small
    # digits — the tightening loop applies inside the battery too)
    if blobs:
        digit_texts = [t for t in texts if t.get("string", "").strip().isdigit()]
        for b in blobs:
            cnx = b["centroid_px"][0] / W * 1000
            cny = b["centroid_px"][1] / H * 1000
            if digit_texts:
                best = min(
                    digit_texts,
                    key=lambda t: ((t["bbox"][0] + t["bbox"][2]) / 2 - cnx) ** 2
                                  + ((t["bbox"][1] + t["bbox"][3]) / 2 - cny) ** 2)
                bx = ((best["bbox"][0] + best["bbox"][2]) / 2,
                      (best["bbox"][1] + best["bbox"][3]) / 2)
                d = ((bx[0] - cnx) ** 2 + (bx[1] - cny) ** 2) ** 0.5
                if d < 120:
                    b["nearest_day_ocr"] = best.get("string")
                    b["dist_norm"] = round(d)
            bx0, by0, bw, bh = b["bbox_px"]
            pad = int(max(bw, bh) * 0.8)
            crop = zoom.crop_zoom(
                img, (max(0, bx0 - pad), max(0, by0 - pad),
                      bw + 2 * pad, bh + 2 * pad),
                scale=4, pad_frac=0.0)[0]
            rec_b = mirage.describe(crop)
            digits = [t.get("string") for t in rec_b.get("text", [])
                      if t.get("string", "").strip().isdigit()
                      and t.get("score", 0) > 0.3]
            if digits:
                b["zoomed_label"] = digits[0]
        add("selection_state", "Is anything selected/highlighted?",
            {"blobs": blobs}, "accent-census+zoom")
    else:
        add("selection_state", "Is anything selected/highlighted?", "none detected", "accent-census")

    # --- conditional: calendar-like grid ---
    if fam == "calendar-like grid":
        wk = s["inference"]["weekday_header"]
        add("weekday_header", "Is there a weekday header row?",
            f"yes: {wk} ({s['inference']['n_weekday_labels']} labels)", "structure")

        # muted cells: day-number texts with luminance < 0.65x median
        day_items = [t for t in texts
                     if t.get("string", "").strip().isdigit()
                     and t.get("score", 0) > 0.4]
        lums = []
        for t in day_items:
            rgb = color.mean_rgb(img, t["bbox"])
            if rgb:
                lums.append((_lum(rgb), t.get("string"),
                             [round(v) for v in t["bbox"]]))
        if len(lums) >= 5:
            med = sorted(l[0] for l in lums)[len(lums) // 2]
            muted = [{"text": s_, "bbox": bb} for l, s_, bb in lums if l < med * 0.65]
            add("muted_cells", "Are some cells muted (prev/next month)?",
                muted if muted else "no muted cells detected",
                "mean_rgb+luminance")

        # weekday header: full-frame OCR misses labels — verify via zoom
        wk_row = next((r for r in s["grid"]
                       if r["cell_kinds"].count("weekday") >= 3), None)
        if wk_row is not None:
            wy_px = wk_row["y"] / 1000 * H
            band = zoom.crop_zoom(img, (0, wy_px - 30, W, 60),
                                  scale=4, pad_frac=0.0)[0]
            rec_w = mirage.describe(band)
            wk_zoom = [t.get("string") for t in rec_w.get("text", [])
                       if t.get("string", "").strip().upper() in structure.WEEKDAYS]
            add("weekday_header_zoom", "Weekday header verified at magnification?",
                sorted(set(wk_zoom)) if wk_zoom else "unmeasured",
                "zoom+describe")

        # header line above the title: zoom the band above the title row
        title_row = None
        for r in s["grid"]:
            items = _row_items(r)
            if items and max(len(i.get("string", "")) for i in items) > 8:
                title_row = r
                break
        if title_row is not None:
            ty_px = title_row["y"] / 1000 * H
            band = zoom.crop_zoom(img, (0, max(0, ty_px - 95), W, 75),
                                  scale=4, pad_frac=0.0)[0]
            rec2 = mirage.describe(band)
            # report all strings found in the band — duplicates of
            # full-frame strings are still meaningful here (position
            # is what makes them a header line, not novelty)
            extra = [t.get("string") for t in rec2.get("text", [])
                     if t.get("score", 0) > 0.4]
            add("header_line", "Is there a header line above the title?",
                "yes: " + ", ".join(extra) if extra else "none detected",
                "zoom+describe")

    return {"image": str(image), "questions": qs}
