---
challenge: eyes-evals
kind: generator
status: standing
yields: one new eval case + recorded eyes verdict appended to the evals catalog
catalog: ../evals
family: eyes
description: Grow the defect catalog — typical visual bugs agents ship, each replayed against the eyes instrument.
---

*Walker context: this generator exists because "does eyes actually catch
real bugs" is the question the whole repo stands on, and it can only be
answered by an accumulating catalog of planted defects with recorded
verdicts — including misses. A miss is a valid entry; it is the most
valuable kind. Recurrence earned this brief: every session so far has
invented its own one-off test cases, and none of them accumulate.*

---

## The brief (sealed — you are the contestant)

You ARE the contestant. Do not ask which direction to take; pick one,
name it, ship it. You have carte blanche on technology — HTML/CSS,
Canvas, PIL, anything that produces the artifact.

**Mission:** invent ONE typical visual defect that text-only coding
agents actually ship, build the smallest artifact that exhibits it, run
the `eyes` instrument against it, and record the verdict.

### Step 0 — self-ground

Read `evals/` first. Do not reproduce a case shape already catalogued.
Bring something not already there. The catalog is the long-running
artifact; your entry is one slice through it. Variance across replays is
the single most important measure of success — a catalog of near-dupes
has stopped growing.

### Step 1 — pick the defect

Typical classes (seed, not exhaustive — invent your own):

- layout overflow: content clipped at frame edge, container overflow,
  text truncation, overlapping elements
- dead/frozen frames in animation, or chaotic uncontrolled motion
- theme/palette inconsistency across states of one design
- object dropouts: element present in one state, silently gone in next
- OCR-hostile text: low contrast, stylized type, text-as-image
- aspect-ratio abuse: extreme portrait/ultrawide/square distortions
- contrast failures: content unreadable against its background
- semantic surprises: plausible-looking but wrong content (wrong icon,
  mirrored text, off-by-one date)

The bar: **typical**, not adversarial. This is the defect your
bread-and-butter models ship on an ordinary Tuesday — not a puzzle
built to break the instrument. If you find yourself constructing
something no real UI would contain, you have left the brief.

### Step 2 — build the repro

Smallest artifact that exhibits the defect: a PNG, an HTML file, a
directory of frames — your choice. It must actually render/produce the
claimed defect; a case whose defect you cannot demonstrate is not a
case.

### Step 3 — run eyes

From the repo root:

```
uv run eyes describe <artifact> [--stats]
uv run eyes layout <artifact> [--describe]
uv run eyes score <artifact> <clean-variant>   # if you built a pair
uv run eyes reel <frame-dir-or-files>          # if temporal
```

Record exactly what the instrument said — the JSON, not your
interpretation of it.

### Step 4 — verdict + append

Create `evals/<case-slug>/` containing:

- the artifact(s)
- `VERDICT.md` — what defect was planted, the exact eyes output, and
  the honest call: **CAUGHT** (instrument surfaced it), **PARTIAL**
  (surfaced ambiguously — say what was missing), or **MISSED** (instrument
  saw nothing wrong). A MISS is a first-class result — report it
  plainly, do not soften it into a partial.

Zero-friction append: the directory IS the catalog entry. No index to
update, no registration step.

### Done-gates (self-check before you finish)

- [ ] `evals/` was read first; this case shape is not already present
- [ ] the artifact demonstrably exhibits the claimed defect
- [ ] every `eyes` command you cite actually ran — paste real output,
      never narrated output
- [ ] VERDICT.md names the defect, quotes the instrument output, and
      renders an honest CAUGHT / PARTIAL / MISS
- [ ] the case is *typical* — a defect real agentic code ships, not a
      contrivance built to fool the instrument

The human taste-gate sits after you: whether this defect class is worth
cataloguing and whether the verdict reads honest is judged on the walk,
not by you.
