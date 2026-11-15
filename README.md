# 6digit-vision — `eyes`

A cheap, local, structured vision instrument: **screenshots in, facts out.**

Text-only coding agents can't see pixels. `eyes` gives them measurable
facts they can reason over — object records, layout/overflow signals,
color histograms, frame-to-frame coherence — without a frontier
multimodal model in the loop and without a hosted API.

The instrument reports **facts, not verdicts.** Judgment belongs to the
reasoning layer that consumes the output.

## The CLI

```bash
uv sync                    # create .venv, install deps
uv run eyes describe img.png [--stats] [--masks]
uv run eyes score ref.png cand.png [--json]   # decomposed 0–100 similarity
uv run eyes layout img.png [--describe]       # edge contact, edge objects, overlaps, legibility
uv run eyes reel frames/                        # frame-sequence coherence
uv run eyes ask img.png -q "is the header clipped?"   # evidence pack for the reasoning layer
uv run eyes palette img.png -n 8
```

All commands emit JSON with `--json`; human-readable output by default.
`layout` and `palette` run on pure PIL with no model. The first
`describe`/`score`/`reel`/`ask` run downloads ~22 MB of Mirage weights
from Hugging Face (unauthenticated is fine).

## How it works

- **Perception:** [Cactus Mirage](https://huggingface.co/Cactus-Compute/mirage)
  via `cactus-compute` — a tiny (~22 MB, CPU-friendly) model that returns
  scene descriptions, objects + attributes, OCR text, spatial relations,
  and masks.
- **Quantitative layer:** PIL/numpy over the Mirage records — per-object
  mean RGB, dominant-color histograms, WCAG-style contrast ratios,
  edge-contact fractions, bbox overlaps.
- **Temporal:** pixel diffs + record stability across frame sequences
  (frozen frames, object dropouts, lifecycle departures).

Mirage bbox/mask coordinates are normalized per-axis to `[0, 1000]`,
not pixels — go through `eyes.color.denorm`.

## Repo layout

| Path | What it is |
|---|---|
| `eyes/` | The instrument: `mirage.py` (model wrapper + record compaction), `color.py`, `score.py`, `layout.py`, `temporal.py`, `legibility.py`, `ask.py`, `cli.py` |
| `tests/` | pytest — pure-function unit tests, no model needed |
| `evals/` | Defect catalog: planted visual bugs + recorded CAUGHT / PARTIAL / MISS verdicts |
| `detectors/` | Standalone detectors built to fill gaps the evals exposed |
| `challenges/` | Standing generator briefs that grow `evals/` and `detectors/` |
| `ab_runs/` | Controlled A/B/C experiment: does `eyes` improve screenshot→HTML? report, gallery, tool-usage audit |
| `docs/MEASUREMENT_DISCIPLINE.md` | The measure→edit→re-measure protocol distilled from that run |
| `PRD.md` | Original product spec (the closed-loop critique architecture) |
| `SCENE.md` | Project scene doc (north star, ideal user, what it says no to) |

## Evals and detectors

The repo is instrumented against its own blind spots:

- **`evals/`** — each subdirectory plants a typical visual defect
  (overflow, frozen frames, theme drift, OCR-hostile text, …), runs
  `eyes` against it, and records an honest verdict in `VERDICT.md`. A
  MISS is a first-class result — the catalog exists to map where the
  instrument is blind.
- **`detectors/`** — each subdirectory is a standalone detector for a
  defect class `eyes` can't yet catch, proven against the eval case that
  named the gap. Some have been integrated into `eyes/` (see `ask.py`,
  `reel`); the rest live beside the instrument pending a walk decision.
- **`challenges/`** — sealed generator briefs (`EYES_EVAL_CHALLENGE.md`,
  `EYES_DETECTOR_CHALLENGE.md`) that any agent can replay to grow the
  catalogs.

## Does the instrument add anything? (measured)

A controlled run on four screenshots: vision-only averaged **0.684 SSIM**,
vision + a measurement loop averaged **0.888**; the precomputed `interrogate`
fact sheet alone made no difference (clean pair: 0.785 vs 0.782 / 0.420 vs
0.375). The usable surface was `pixdiff` + `score` as a coarse gate; agents
built their own geometry/type/colour calipers because `parse` was never named.
Full write-up: [`ab_runs/REPORT.md`](ab_runs/REPORT.md) ·
gallery: [`ab_runs/gallery.html`](ab_runs/gallery.html) ·
what was actually invoked: [`ab_runs/TOOL_USAGE.md`](ab_runs/TOOL_USAGE.md) ·
the protocol: [`docs/MEASUREMENT_DISCIPLINE.md`](docs/MEASUREMENT_DISCIPLINE.md).

## Requirements

- Python ≥ 3.11, [uv](https://docs.astral.sh/uv/)
- No API keys, no GPU — Mirage runs on CPU

## Tests

```bash
uv run pytest -q
```

Score/layout/temporal unit tests are pure functions and run without the
model; model-backed paths are exercised through the eval catalog.

## Known limits

- Mirage's shape/color labels are inconsistent on flat synthetic shapes
  and dense UI screenshots — object-F1 scores are noisy; palette,
  layout, and legibility signals are the reliable components.
- Screenshots-only by design: no prompt required, no reference required.
  `eyes score` adds a reference only when you want a similarity number.
