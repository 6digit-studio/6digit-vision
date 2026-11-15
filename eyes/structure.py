"""Structure induction — compose flat element/OCR lists into relational
structure: rows, columns, grids, sequences.

The layer between perception (Mirage bboxes) and comprehension (what IS
this and how is it organized). Deterministic, no model: cluster text
boxes into rows by y, infer column positions from x-spacing regularity
(gaps that are ~2x pitch imply a missed/occluded column), align rows
sharing column positions into grids, and label sequences (weekday names,
integers) where recognizable.
"""

from __future__ import annotations

WEEKDAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}


def _yc(b):
    return (b[1] + b[3]) / 2


def _xc(b):
    return (b[0] + b[2]) / 2


def _cluster_1d(values, tol):
    """Cluster sorted scalars; return list of (center, [members])."""
    groups = []
    for v in sorted(values):
        if groups and v - groups[-1][-1] <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [(sum(g) / len(g), g) for g in groups]


def induce_rows(texts, row_tol=25):
    """Cluster text items into horizontal rows by bbox y-center."""
    items = [t for t in texts if t.get("bbox")]
    rows = []
    for t in sorted(items, key=lambda t: _yc(t["bbox"])):
        y = _yc(t["bbox"])
        for r in rows:
            if abs(r["y"] - y) <= row_tol:
                r["items"].append(t)
                r["y"] = sum(_yc(i["bbox"]) for i in r["items"]) / len(r["items"])
                break
        else:
            rows.append({"y": y, "items": [t]})
    for r in rows:
        r["items"].sort(key=lambda t: _xc(t["bbox"]))
    return rows


def infer_columns(rows, pitch_tol=0.25):
    """Infer grid column x-positions across all rows.

    Collects per-row item x-centers, clusters them globally, then uses
    gap analysis to detect columns missed by OCR (a gap ~2x pitch means
    an empty/missed column between detected ones).
    """
    all_x = [_xc(t["bbox"]) for r in rows for t in r["items"]]
    if not all_x:
        return []
    # global cluster with tight tolerance (~quarter of typical pitch)
    clusters = _cluster_1d(all_x, tol=20)
    centers = sorted(c for c, _ in clusters)
    if len(centers) < 2:
        return centers
    gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
    pitch = min(gaps)  # smallest observed gap ~ unit pitch
    # expand: any gap > 1.5*pitch implies missed columns at pitch intervals
    cols = [centers[0]]
    for i, g in enumerate(gaps):
        n_missing = round(g / pitch) - 1
        for k in range(1, n_missing + 1):
            cols.append(centers[i] + k * pitch)
        cols.append(centers[i + 1])
    return sorted(set(round(c) for c in cols))


def build_grid(rows, cols, x_tol=20, y_rows=None):
    """Assign each row's items to nearest column; return cell matrix."""
    grid = []
    for r in rows:
        cells = [None] * len(cols)
        for t in r["items"]:
            x = _xc(t["bbox"])
            j = min(range(len(cols)), key=lambda k: abs(cols[k] - x))
            if abs(cols[j] - x) <= x_tol:
                cells[j] = t.get("string", "")
        grid.append({"y": round(r["y"]), "cells": cells})
    return grid


def label_sequences(grid):
    """Tag rows whose cells look like weekday names or integers."""
    for row in grid:
        tags = []
        for c in row["cells"]:
            if c is None:
                tags.append(None)
                continue
            u = c.strip().upper()
            if u in WEEKDAYS:
                tags.append("weekday")
            elif c.strip().isdigit():
                tags.append("int")
            else:
                tags.append("text")
        row["cell_kinds"] = tags
    return grid


def summarize(texts):
    """Full induction pass -> structural summary dict."""
    rows = induce_rows(texts)
    cols = infer_columns(rows)
    grid = build_grid(rows, cols)
    label_sequences(grid)

    weekday_rows = [r for r in grid if r["cell_kinds"].count("weekday") >= 3]
    int_rows = [r for r in grid if r["cell_kinds"].count("int") >= 3]

    out = {
        "n_rows": len(rows),
        "row_ys": [r["y"] for r in rows],
        "n_cols": len(cols),
        "col_xs": cols,
        "grid": grid,
    }
    if weekday_rows and int_rows:
        wk = weekday_rows[0]["cells"]
        days = [c for r in int_rows for c in r["cells"] if c and c.strip().isdigit()]
        out["inference"] = {
            "kind": "calendar-like grid",
            "weekday_header": [c for c in wk if c],
            "day_sequence": days,
            "n_weekday_labels": sum(1 for c in wk if c),
            "n_day_cells": len(days),
        }
    return out
