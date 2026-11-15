---
name: 6digit-vision-toolchain
description: Orientation map for the 6digit-vision repo — how to build, test, run the eyes CLI, and where the conventions live. Read this first before touching the code.
---

# 6digit-vision toolchain

Cheap structured vision instrument (`eyes`): Mirage perception + PIL
quantitative layer + deterministic scoring, so text-only models get
eyes. Spec: `PRD.md` (repo root). Scene: `SCENE.md`.

## Commands

- Sync env: `uv sync` (creates `.venv`, installs `cactus-compute`, `pillow`, `pytest`)
- Test: `uv run pytest -q` — unit tests are pure functions, no model needed
- CLI (all emit JSON with flags, human-readable by default):
  - `uv run eyes describe <img> [--stats] [--masks]` — compact Mirage record
  - `uv run eyes score <ref> <cand> [--json]` — decomposed 0–100 similarity
  - `uv run eyes layout <img> [--describe]` — edge contact / edge objects / bbox overlaps
  - `uv run eyes palette <img> [-n 8]` — dominant color histogram
- First `describe`/`score`/`layout --describe` run downloads ~22MB Mirage
  weights from HF (unauthenticated warning is fine).

## Layout

- `eyes/mirage.py` — lazy `cactus.Mirage()` wrapper + record compaction
- `eyes/color.py` — palette histogram, per-object mean RGB (`denorm` maps
  Mirage coords → pixels)
- `eyes/score.py` — pure scoring functions over records (no model calls)
- `eyes/layout.py` — edge_contact, objects_at_edge, bbox_overlaps
- `eyes/cli.py` — argparse entry (`eyes` script via pyproject)
- `tests/` — pytest; score/layout tests run without the model

## Conventions / canonical standard

- Tests in `tests/` are the executable standard; `PRD.md` is the spec.
- Instrument reports **facts, not verdicts** — interpretation is the
  reasoning model's job (see SCENE.md "what it says no to").
- Compact records by default: masks stripped unless `--masks`.

## Things that will bite you

- **Never pass `sections=None`/`language=None` to `cactus.describe`** —
  explicit None is rejected ("sections must be a list of names");
  `eyes/mirage.py` already filters Nones, keep it that way.
- Mirage bbox/mask coords are **normalized per-axis to [0,1000]**, not
  pixels — always go through `color.denorm` or treat as fractions.
- Mirage shape/color labels are **inconsistent on flat synthetic shapes
  and dense UI screenshots** (same element named "app icon"/"icon"/"light"
  across variants). Object-F1 scores are noisy; palette/text/layout are
  the reliable components.
- `cactus` API: `describe(image, sections=[...], language=..., width=,
  height=)`; `extract` exists for structured forms; `width`/`height`
  require packed RGB bytes, not paths.
