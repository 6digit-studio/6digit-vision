# ab_runs — controlled test of `eyes` on screenshot→HTML

Experiment for `deepseek_package/`. Same model, same four references, same
renderer, same iteration brief (3-5 looks); only the sensing mode differs.

| dir | arm |
|---|---|
| `A/<ref>/` | **vision only** — no facts, no measurement tools |
| `B/<ref>/` | **vision + `eyes interrogate` fact sheet** (`facts.json`) — no live tools |
| `C/<ref>/` | **vision + live `eyes score`/`pixdiff`/`zoom` loop** — no fact sheet |
| `A2/<ref>/`, `B2/<ref>/` | clean facts-only pair (ref1, ref3): identical perception-only rules, `facts.json` the only difference |

Each cell is isolated: `reference.png`, `SIZE_W`/`SIZE_H`, `render.sh`,
`TASK.md`, then `candidate.html`, `candidate.png`, `VERDICT.md` (and
`trace.jsonl` for C).

## Read

- `REPORT.md` — design, fact-sheet audit, scorer calibration, results, verdict.
- `gallery.html` / `gallery.png` — reference vs arms, per reference.
- `results.json` / `results.md` — every metric per cell.

## Re-score

```bash
python3 score_all.py     # A/B/C -> results.json / results.md
python3 score_clean.py   # A2/B2 -> clean_results.json
python3 gallery.py       # -> gallery.png
python3 clean_pair.py    # -> clean_pair.png
python3 gallery_html.py  # -> gallery.html
```

## Metric note

`eyes score` is semantic and caps below 100 even for an identical image
(palette term = top-8 bin coverage). `results.json` carries each reference's
self-ceiling; `ssim_mean`, `mismatch_frac`, and full-res `rmse` are the honest
pixel metrics. See REPORT.md "Scorer calibration".
