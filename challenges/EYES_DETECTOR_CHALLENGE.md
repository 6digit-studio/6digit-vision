---
challenge: eyes-detectors
kind: generator
status: standing
yields: one new runnable detector in the detectors catalog, verified against the eval case that named the gap
catalog: ../detectors
family: eyes
description: Fill the dark regions — contestants invent instrumentation (OpenCV, CV models, heuristics, anything) for defects the eval catalog proved eyes cannot see.
---

*Walker context: evals find the dark regions; this challenge fills them.
Each detector brief below was written by the contestant who hit the wall —
the problem statement is proven, the solution space is open. A detector
that flips a PARTIAL/MISS to CAUGHT is the catalog's highest-value
output; a detector that doesn't is still a catalog entry if it's honest
about what it can't do.*

---

## The brief (sealed — you are the contestant)

You ARE the contestant. Do not ask which direction; pick one open
problem, name it, ship it. Carte blanche on technology — OpenCV, numpy,
a small model, pure PIL, whatever actually works.

**Mission:** build ONE detector for a defect class the `eyes` instrument
currently cannot catch, and prove it against the eval case that exposed
the gap.

### Step 0 — self-ground

Read `evals/` — every VERDICT.md. Each PARTIAL/MISS names a gap and,
usually, a contestant's sketch of what would fill it. Read
`detectors/` — do not rebuild something already catalogued. The open
problems as of planting:

1. **entity-lifecycle diffing** (from `evals/object-dropout`): diff
   per-frame object sets + OCR strings across a reel; emit
   "element X present frames a–b, absent c–d" as a named fact. All
   inputs already exist in `reel --json` `frames_detail` — zero new
   model calls needed.
2. **glyph-classification pass** (from `evals/semantic-surprise`):
   crop emblem/icon regions (Mirage bboxes are in the record), classify
   the interior symbol against a small vocabulary (check/x/warning/
   spinner/download/trash). Turns "logo" from semantic black hole into
   `status_icon: check`.
3. **accent-hue census** (from `evals/theme-drift`): RGB→HSV, mask
   saturated pixels, histogram hue in ~15° bins, flag ≥2 hue families.
   Contestant prototype already showed state B splitting into two
   families — verify and productize it.

New gaps discovered by later eval replays belong here too — check the
catalog before assuming the list is complete.

### Step 1 — build the detector

Standalone module under `detectors/<slug>/` — a script or module that
consumes `eyes` outputs (records, reels, images) and emits findings.
**Do NOT modify `eyes/` or `tests/`** — detectors live beside the
instrument, integration is a later walk decision. Runnable from repo
root via `uv run`.

### Step 2 — prove it

Run your detector against the eval case that named the gap AND at least
one control (the eval's control image, or a clean variant you build).
Report: does it fire on the defect, stay silent on the control?

### Step 3 — catalog entry

`detectors/<slug>/` contains: the detector code, `VERDICT.md` naming the
gap it fills, the real command output on defect + control, and an honest
CAUGHT / PARTIAL / MISS for the detector itself. A detector that fires
on both defect and control is a MISS — report it plainly.

### Done-gates

- [ ] `evals/` and `detectors/` read first; not a rebuild
- [ ] detector runs from repo root, output is real pasted JSON/text
- [ ] fires on the defect case, documented behavior on control
- [ ] VERDICT.md honest about what it catches AND what it can't
- [ ] standalone — no edits to `eyes/` or `tests/`

The human taste-gate sits after you: whether the detector is worth
integrating into `eyes/` is judged on the walk.
