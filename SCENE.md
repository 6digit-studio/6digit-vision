# SCENE — 6digit-vision

*read-many, write-rarely · two clocks — the scene is slow and sticky, the
existing scene is fast and live · scouts get the ideal-user, NEVER this file ·
the scene condenses from the membrane.*

## north star (seed — condenses from the membrane as the corpus grows)

**Give text-only models eyes.** A cheap, local, structured vision
instrument — screenshots in, facts out — so SWE-2 / DeepSeek-class agents
can see and verify visual work without a frontier multimodal model in the
loop.

## ideal user(s)

A text-only coding agent inside an agentic dev loop, handed a rendered
artifact (web page, canvas, Metal framebuffer) and asked "is this right?"
It cannot see pixels; it can run commands and read JSON. The instrument
must hand it measurable facts it can reason over — never a black box,
never a required prompt, never a hosted API it can't reach.

## loose directions (beds, not blueprints)

- backend-agnostic core: image in → record/score/facts out; web, canvas,
  and Metal/Omni renderers are adapters, not special cases
- screenshots-only operation — no prompt, no reference required
- overflow/layout detection as a first-class signal (the stated pain:
  bugs that slip past code-driven checks)
- iterative score loops for design approximation
- challenger-generated evals once the methodology is walking

## what it says no to

- vision that requires a prompt or a reference image to function
- per-call hosted VLM dependency as the default path (escalation, yes;
  substrate, no)
- verdicts from the instrument — it reports facts; judgment belongs to
  the reasoning layer
- silent degradation: if the instrument can't measure something, it says
  so, it doesn't guess

## tending log

- 2026-11-15 · planted by arbiters-init · seed stage — north star and
  ideal-user captured from session intake; corpus empty, scene thin by
  design
