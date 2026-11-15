# luminance-theme — detector verdict

Spec: flag coherent opposite-luminance regions on a claimed theme —
light cards on dark theme or dark islands on light. Born from
evals/web-theme-drift (real Chrome render): hue_census correctly saw
no hue split; the drift was luminance.

## Results

| image | verdict | evidence |
|-------|---------|----------|
| web-theme-drift/defect | **luminance_theme_split** | 5.2% opposite-lum, 78 coherent rows, dark theme |
| web-theme-drift/control | single_luminance_theme | 0.5% island frac |
| github login | clean | 0.4% |
| HN | clean | 2.5% frac but 1 coherent row (coherence gate) |
| wikipedia | clean | 6.6% frac, 17 rows < 40-row floor |
| MDN | clean | 2.7%, 7 rows |
| example.com, web-real ctrl/lc | clean | <2.2%, 0 rows |
| theme-drift state-a/b | clean | 2.3%, 6 rows |
| **BBC News** | **luminance_theme_split** | 22.0%, 272 coherent rows, light theme |

## The BBC finding — honest boundary

BBC fires hard: 22% opposite-luminance in 272 coherent rows. Its
homepage has a large dark masthead on a light page — real luminance
mixing, but INTENTIONAL design, not drift. Same lesson as hue_census
pre-balance-gate: the detector measures the fact (luminance mixing
exists, coherently), reasoning judges intent (masthead vs drifted
cards). Documented as candidate-level signal; not threshold-fished.
Consumers should read luminance_theme_split as "investigate", same as
accent_hue_split was before its balance gate — a future balance/spatial
gate could separate edge-anchored chrome (masthead) from interior
islands (drifted cards) if real cases demand it.
