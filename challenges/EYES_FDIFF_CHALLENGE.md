# EYES_FDIFF_CHALLENGE — frequency-domain diff contestants

Commissioned by arbiter-seat t3k (Lars's directive): FFT/low-pass and
phase correlation are the missing channels — low frequencies carry
structure (missing card, shifted block, color fields) while AA edges,
compression, and subpixel text jitter live in high frequencies.
Phase correlation is THE classic alignment estimator — kills the
"1px global shift = massive edge diffs" blindness pixdiff has.

## Rules

- Standalone under `fdiff/<slug>/` — do NOT touch `eyes/` or other
  contestants' dirs. Model-free, numpy/scipy/PIL only.
- API contract: `fdiff(a_path, b_path) -> dict` returning at minimum
  `{"score": float 0..1, "regions": [...], "notes": [...]}` —
  score ~1.0 for identical, regions = localized change bboxes
  (pixel coords of the COMMON canvas size).
- Every claim needs measured output on the shared bar below.
- Honest VERDICT.md per contestant: CAUGHT/PARTIAL/MISS per criterion.

## Seeded field (propose more if you see a better mechanism)

- `fft-lowband` — FFT magnitude low-band diff
- `phasecorr` — phase-correlation alignment + residual diff
- `dct-phash` — DCT/pHash-style perceptual distance
- `pyramid` — Gaussian-pyramid multi-scale diff

## Shared falsifiable bar

1. identical images -> score ~1.0 / zero diff
2. planted 20px block shift -> localized diff regions (pixdiff: 0.983)
3. 1px GLOBAL translation -> must NOT produce massive edge diffs
   (pixdiff's documented blindness; alignment-equipped entries should
   fix it, others document residual honestly)
4. dense-text AA/compression noise -> low false-positive diff
5. ui1 login pair (evals/web-real/corpus/github_com_login.png vs
   loop_runs/ui1/candidate.png) -> fine-edit signal that semantic
   score couldn't see above Mirage jitter

Judged by orchestrator; winner integrates into eyes/ or honest
no-winner verdict with measured reasons.
