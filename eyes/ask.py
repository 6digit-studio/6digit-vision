"""eyes ask — package an image's evidence for the reasoning layer.

The instrument reports facts; judgment belongs to the consuming text
model (SWE-2, DeepSeek, the agent running eyes). `ask` emits a compact
evidence pack — record + flagged findings only — optionally framed with
the question the reasoning layer should answer.

Measured limitation (2026-11-15): cactus.Needle is a TOOL-CALLING model
(function_calls envelope, `tools=` param, agentic `run` loop) — it is
for plumbing variables into tool calls, not a reasoning court.
Needle().extract returned null on a text-truncation judgment. The pack
is the deliverable; the call-site LLM is the court by design.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_detector(rel: str):
    spec = importlib.util.spec_from_file_location(
        rel.replace("/", "_").replace("-", "_"), _ROOT / "detectors" / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evidence_pack(image, question: str | None = None) -> dict:
    from . import layout, legibility, mirage

    rec = mirage.describe(image)
    lay = layout.layout_report(image, record=rec)
    leg = legibility.text_legibility(image, rec)

    # verified detectors/ catalog entries, lazy-loaded
    findings_extra = {}
    try:
        glyph = _load_detector("glyph-classifier/glyph_classifier.py")
        findings_extra["status_icons"] = glyph.classify_image(str(image), rec)
    except Exception as e:
        findings_extra["status_icons_error"] = str(e)[:200]
    try:
        hc = _load_detector("hue-census/hue_census.py")
        args = Namespace(s_min=hc.S_MIN, v_min=hc.V_MIN, bin_deg=hc.BIN_DEG,
                         min_family_share=hc.MIN_FAMILY_SHARE,
                         rel_to_dominant=hc.REL_TO_DOMINANT,
                         min_saturated_px=hc.MIN_SATURATED_PX)
        findings_extra["hue_census"] = hc.census(str(image), args)
    except Exception as e:
        findings_extra["hue_census_error"] = str(e)[:200]
    try:
        lex = _load_detector("lexical-screen/lexical_screen.py")
        words, sources, zipf_fn = lex.load_lexicon()
        screened = [lex.screen_string(t, words, zipf_fn)
                    for t in rec.get("text", [])]
        findings_extra["lexical_screen"] = {
            "sources": sources,
            "flagged": [s for s in screened if s.get("verdict") != "clean"],
            "frag_bands": lex.fragmented_bands(rec.get("text", [])),
        }
    except Exception as e:
        findings_extra["lexical_screen_error"] = str(e)[:200]
    try:
        an = _load_detector("anisotropy-census/anisotropy_census.py")
        findings_extra["anisotropy"] = an.census(
            str(image), Namespace(max_blobs=12))
    except Exception as e:
        findings_extra["anisotropy_error"] = str(e)[:200]

    pack = {
        "scene": rec.get("scene"),
        "objects": [
            {"name": o.get("name"), "position": o.get("position"),
             "score": o.get("score"),
             "description": o.get("description")}
            for o in rec.get("objects", [])
        ],
        "text": [{"string": t.get("string"), "score": t.get("score"),
                  "bbox": t.get("bbox")}
                 for t in rec.get("text", [])],
        "findings": {
            "objects_at_edge": lay.get("objects_at_edge"),
            "bbox_overlaps": lay.get("bbox_overlaps"),
            "text_edge_flush": lay.get("text_edge_flush"),
            "legibility_flagged": [l for l in leg if l["flags"]],
        },
        "detectors": findings_extra,
    }
    if question:
        pack["question"] = question
        pack["instruction"] = (
            "Answer the question using ONLY the evidence above. "
            "Report facts you can cite; say 'insufficient evidence' "
            "rather than guessing."
        )
    return pack
