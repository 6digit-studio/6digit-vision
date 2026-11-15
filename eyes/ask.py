"""eyes ask — package an image's evidence for the reasoning layer.

The instrument reports facts; judgment belongs to the consuming text
model (SWE-2, DeepSeek, the agent running eyes). `ask` emits a compact
evidence pack — record + flagged findings only — optionally framed with
the question the reasoning layer should answer.

Measured limitation (2026-11-15): cactus.Needle().extract returned null
on a text-truncation judgment task — the on-device model is not yet a
reliable reasoning court. The pack is the deliverable; the consumer is
the court.
"""

from __future__ import annotations

import json


def evidence_pack(image, question: str | None = None) -> dict:
    from . import layout, legibility, mirage

    rec = mirage.describe(image)
    lay = layout.layout_report(image, record=rec)
    leg = legibility.text_legibility(image, rec)

    pack = {
        "scene": rec.get("scene"),
        "objects": [
            {"name": o.get("name"), "position": o.get("position"),
             "score": o.get("score"),
             "description": o.get("description")}
            for o in rec.get("objects", [])
        ],
        "text": [{"string": t.get("string"), "score": t.get("score")}
                 for t in rec.get("text", [])],
        "findings": {
            "objects_at_edge": lay.get("objects_at_edge"),
            "bbox_overlaps": lay.get("bbox_overlaps"),
            "text_edge_flush": lay.get("text_edge_flush"),
            "legibility_flagged": [l for l in leg if l["flags"]],
        },
    }
    if question:
        pack["question"] = question
        pack["instruction"] = (
            "Answer the question using ONLY the evidence above. "
            "Report facts you can cite; say 'insufficient evidence' "
            "rather than guessing."
        )
    return pack
