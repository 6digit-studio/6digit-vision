"""eyes — cheap structured vision instrument.

Mirage (Cactus Compute, ~22MB CPU) produces scene/object/text/relation
records; this package compacts them, adds quantitative color stats, and
scores candidate images against references.

Mirage emits bbox/mask coordinates normalized per-axis to [0, 1000]
(x' = x/W*1000, y' = y/H*1000), verified empirically 2026-11-15.
"""
