"""gloss — local-VLM reproduction descriptions for diff regions.

The chrome-ceiling fix: pixdiff/fdiff/region_map localize WHERE pixels
differ, but regions that aren't CSS-addressable (images, canvas,
graphical chrome) dead-end at "unmatched". gloss crops the region
(+padding), asks the local VLM (mlx-vlm Qwen3-VL on :8080,
OpenAI-compatible) for a REPRODUCTION description — element type,
style, colors, icon semantics, text — not generic captioning. The
description is what a critic needs to recreate the region in HTML/CSS
or name it honestly as non-reproducible.

SCENE.md escalation order: local VLM first; hosted API only if local
fails the eval bar.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ENDPOINT = "http://localhost:8080/v1/chat/completions"
MODEL = "mlx-community/Qwen3-VL-8B-Instruct-4bit"

PROMPT = """You are reverse-engineering a UI screenshot region for HTML/CSS reproduction.
Describe precisely what is here — this is NOT a caption. Report:
1. ELEMENT TYPE: what UI element(s) — button, icon, chart, image, text block, decoration, chart type if data viz
2. TEXT: transcribe ALL visible text verbatim
3. STYLE: colors (approx hex), backgrounds, borders, corner radius, shadows, gradients
4. LAYOUT: position/size relationships within the crop, alignment
5. SEMANTICS: what the element likely represents (nav icon, status badge, avatar, chart series)
Be concrete and terse. If it's a photo/illustration that can't be reproduced in CSS, say IMAGE and describe content."""


def _crop(image_path, bbox, pad_frac: float = 0.12):
    """Crop region + padding, return base64 PNG data URL."""
    img = Image.open(str(image_path)).convert("RGB")
    W, H = img.size
    x, y, w, h = bbox
    px = int(w * pad_frac); py = int(h * pad_frac)
    x0 = max(0, int(x) - px); y0 = max(0, int(y) - py)
    x1 = min(W, int(x + w) + px); y1 = min(H, int(y + h) + py)
    crop = img.crop((x0, y0, x1, y1))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def gloss(image_path, bbox, endpoint: str = ENDPOINT,
          model: str = MODEL, timeout: int = 120) -> dict:
    """One region -> VLM reproduction description."""
    data_url = _crop(image_path, bbox)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
        "max_tokens": 400,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        endpoint, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read())
        text = resp["choices"][0]["message"]["content"]
        return {"bbox": list(bbox), "description": text, "model": model}
    except Exception as e:
        return {"bbox": list(bbox), "description": None,
                "error": str(e)[:200]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--bbox", required=True,
                    help="x,y,w,h in pixels")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    bbox = [int(v) for v in args.bbox.split(",")]
    r = gloss(args.image, bbox)
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        if r.get("description"):
            print(r["description"])
        else:
            print(f"ERROR: {r.get('error')}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
