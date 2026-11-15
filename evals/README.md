# evals — the eyes defect catalog

Each subdirectory is one replay of `challenges/EYES_EVAL_CHALLENGE.md`:
a planted visual defect, the artifact that exhibits it, and a `VERDICT.md`
recording what the `eyes` instrument reported — CAUGHT, PARTIAL, or MISS.

A MISS is a first-class result. The catalog's value is the honest record
of where the instrument is blind, not a wall of greens.

Entry format: `evals/<case-slug>/{artifact(s), VERDICT.md}`
