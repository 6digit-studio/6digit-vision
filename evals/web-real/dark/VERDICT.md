# dark-mode real captures — prefers-color-scheme emulation via Playwright CDP

Four live sites captured with `color_scheme='dark'` (real
prefers-color-scheme path, not --force-dark-mode): example.com,
Wikipedia, MDN, GitHub login. 1200x800, 2026-11-15.

## Detector behavior on real dark content

| image | luminance_theme | hue_census | aniso | nonuniform_scale |
|-------|----------------|------------|-------|------------------|
| example.com (no dark mode — stayed light) | single (2.1%) | single_accent | insuff | insuff |
| github login (dark) | single (0.5%) | **dominant_with_accent** — balance gate holds on dark | insuff | insuff |
| MDN (dark) | **split** 12.7%/104 rows | single_accent | shape_cluster_anomalous (single-channel candidate) | insuff |
| wikipedia (dark) | single (6.6%/17 rows) | **accent_hue_split** blue 62% + orange 37.7% | insuff | isotropic |

## Findings — all honest boundaries, no new FP classes

- **MDN luminance split is REAL mixed luminance**: dark mode keeps
  light code blocks — intentional design, same intent-vs-fact boundary
  as BBC masthead. Detector reports the fact correctly.
- **Wikipedia hue split is REAL**: dark theme genuinely fields blue
  links + orange accents at 62/38 — competing families above the
  balance gate. Legit multi-accent design; candidate-level signal.
- **MDN aniso shape_cluster_anomalous**: single-channel candidate on
  tall thin nav elements — weak flag by design, not corroborated.
- **Dark-bg guards hold**: anisotropy's border-luminance guard,
  luminance detector's dark_bg branch, nonuniform_scale on dark text —
  all first real-dark tests, all behaved.

Verdict: floors hold on real dark-mode content; the known
intent-vs-fact boundaries reproduce identically in dark theme.
