"""Thin wrapper over cactus.Mirage with output compaction.

The raw record carries verbose polygon masks and a free-text reasoning
field. For loop iterations we default to compact records: masks dropped
(unless requested), reasoning kept — it is small and often useful.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_model = None


def model():
    global _model
    if _model is None:
        import cactus

        _model = cactus.Mirage()
    return _model


def load_image(path: str | Path):
    """Return (width, height, packed RGB bytes) for a path or PIL image."""
    from PIL import Image

    if isinstance(path, (str, Path)):
        img = Image.open(path).convert("RGB")
    else:
        img = path.convert("RGB") if hasattr(path, "convert") else path
    return img.size[0], img.size[1], img.tobytes()


def describe(
    image: str | Path | bytes,
    *,
    sections: list[str] | None = None,
    include_masks: bool = False,
    language: str | None = None,
    **settings: Any,
) -> dict:
    """Describe one image. Accepts a path, PIL image, or packed RGB bytes.

    Packed bytes require explicit width/height in settings.
    """
    m = model()
    kwargs: dict[str, Any] = dict(settings)
    if sections is not None:
        kwargs["sections"] = sections
    if language is not None:
        kwargs["language"] = language
    if isinstance(image, (str, Path)):
        raw = m.describe(str(image), **kwargs)
    else:
        raw = m.describe(image, **kwargs)
    return compact(raw, include_masks=include_masks)


def compact(record: dict, *, include_masks: bool = False) -> dict:
    """Strip bulky fields from a raw Mirage record."""
    out = {}
    for key, val in record.items():
        if key == "objects" and isinstance(val, list):
            out[key] = [
                {k: v for k, v in obj.items() if include_masks or k != "mask"}
                for obj in val
            ]
        elif key == "regions" and isinstance(val, list) and not include_masks:
            out[key] = [
                {k: v for k, v in r.items() if k != "mask"} for r in val
            ]
        else:
            out[key] = val
    return out


def to_json(record: dict) -> str:
    return json.dumps(record, indent=2, ensure_ascii=False)
