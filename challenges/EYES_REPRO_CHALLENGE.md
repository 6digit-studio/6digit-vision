---
challenge: eyes-repro
kind: generator
status: standing
yields: one reproduction attempt — candidate + render + measured iteration trace + fact-sheet diff — appended to the repro catalog
catalog: ../repro
family: eyes
created: 2026-11-15
---

*Walker context: commissioned by Lars after the calendar reproduction
run (22.8 -> 46.7 through structure-spec, zoom-inspection, palette-bin,
and text-color iterations). This is the ecology's first **consumption**
challenge — every prior brief grew instruments; this one replays the
whole stack against a reference and grows attempts. Each replay is also
an instrument stress-test: whatever you cannot express or measure gets
named as an instrument gap in your VERDICT, feeding the next detector
brief. Runs identically for text-only agents (toolkit-only) and
vision-capable agents (native+toolkit) — declare your sensing mode;
the catalog then doubles as the A/B corpus.*

---

## The brief (sealed — you are the contestant)

You are reproducing a UI screenshot as HTML/CSS. Not approximately —
as close as your loop can measurably push it. You have the `eyes`
toolkit; use it. You do not ask which reference to pick or which
approach to take; pick one, name it, ship it.

### Step 0 — sensing declaration

State at the top of your VERDICT.md which sensing mode you ran:

- `toolkit-only` — you have no native image vision; all perception
  came through `eyes` commands
- `native-vision` — you saw the reference directly; `eyes` was
  verification/measurement only
- `hybrid` — both

This is data, not a disclaimer. The catalog compares modes.

### Step 1 — pick a reference, self-ground

Read `repro/` first. Choose a reference screenshot that either has
never been attempted OR take a different approach on an attempted one
(different sensing mode, different generation strategy, different
iteration depth). References live in `evals/web-real/corpus/` and the
repo root. Name your reference and approach in the attempt directory.

### Step 2 — interrogate, then build

```
uv run eyes interrogate <reference> --json
```

The fact sheet is your spec: layout family, text inventory, alignment,
selection state, palette. Build HTML/CSS from it — you may author by
hand, generate via any local model you have, or hybrid. Render through
headless Chrome at the reference's pixel dimensions (see
`tools/ui_loop.py` for the render invocation).

### Step 3 — the measured loop

Per iteration, run and record:

```
uv run eyes score <reference> <candidate.png>
uv run eyes pixdiff <reference> <candidate.png>
uv run eyes diff <reference> <candidate.png>        # if you have DOM
uv run eyes zoom <reference> --bbox x,y,w,h --analyze describe
```

Iterate while iterations add measurable value. When they stop, STOP —
a plateau honestly reported beats a score chased into noise. Every
iteration's score goes in `trace.jsonl` (one JSON object per line:
`{"iter": n, "score": x, "note": "what changed"}`).

### Step 4 — the fact-sheet diff

Run `eyes interrogate` on your FINAL candidate and diff the two fact
sheets question-by-question. Which questions does the candidate still
fail? That list IS your gap analysis — more valuable than the score.

### Step 5 — verdict + append

Create `repro/<reference-slug>/<attempt-slug>/` containing:

- `candidate.html`, `candidate.png`
- `trace.jsonl` — every iteration, honestly including regressions
- `facts_reference.json`, `facts_candidate.json` — both interrogate sheets
- `VERDICT.md` — sensing mode, score trajectory, fact-sheet diff
  summary, and the honest call: what closed, what stalled, and every
  **instrument gap** you hit (things you could see were wrong but no
  probe could measure or name). Instrument gaps are first-class
  catalog content — they seed the next detector challenge.

Zero-friction append: the directory IS the catalog entry.

### Done-gates (self-check before you finish)

- [ ] `repro/` was read first; this reference+approach is not already present
- [ ] candidate renders in headless Chrome at reference dimensions
- [ ] every score/pixdiff/interrogate claim has real command output —
      never narrated numbers
- [ ] trace.jsonl records every iteration including any that regressed
- [ ] VERDICT.md declares sensing mode and names instrument gaps plainly
- [ ] you stopped at an honest plateau, not at a round number

The human taste-gate sits after you: whether the attempt is worth
keeping and whether the verdict reads honest is judged on the walk.
