# gloss — local VLM reproduction descriptions: VERDICT

Substrate: mlx-vlm serving Qwen3-VL-8B-Instruct-4bit on :8080,
keyless, ~6GB. eyes/gloss.py crops diff regions (+12% pad) and asks
for REPRODUCTION descriptions (element type, verbatim text, hex
colors, layout, semantics — not captioning).

## 15-crop eval (real diff regions from ui1/ui2/ui3 packs)

Grade vocabulary: CAUGHT = reproduction-usable description;
PARTIAL = right region, imperfect detail; MISS = wrong/generic.

- ui1 login regions (7): CAUGHT — full form transcription, GitHub
  green #1DBF4B button, octocat icon semantics, footer verbatim.
- ui2 calendar (4): CAUGHT — mystery chrome identified as decorative
  carousel/constellation overlay; grid structure + highlighted date;
  "FRI · 25 DEC"/"Christmas Day" header with colors.
- ui3 December view (4): CAUGHT — complete calendar transcription,
  fireworks/dandelion graphics correctly flagged as non-CSS imagery,
  golden #f9c866 highlight on 31.

**15/15 returned; ~14 CAUGHT, 1 PARTIAL** (tiny crop, partial text).
Local VLM CLEARS THE BAR — no hosted-API escalation needed. The
chrome ceiling now has a describer: regions that dead-ended at
"unmatched" produce reproduction-grade evidence.

## Honest limits

- ~3 tok/s decode on this hardware — ~2-4min/crop; batch evals are
  slow but fine for critic-loop cadence (one region per iteration).
- Hex colors are approximations (model-estimated, not sampled) —
  good enough for critic targeting, not pixel-truth (pixdiff stays
  the pixel oracle).
- Describes, doesn't generate — reproduction still needs the critic
  to write CSS; gloss closes the "what IS this region" gap only.
