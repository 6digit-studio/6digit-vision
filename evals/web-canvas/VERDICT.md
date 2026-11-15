# web-canvas — non-DOM raster: canvas chart + CSS non-uniform scale

First eval where content is canvas raster, not DOM text: identical
600x300 bar chart, defect adds transform:scaleX(1.35). Headless
Chrome, 1200x800.

## Verdicts

| case | instrument | +reasoning | verdict |
|------|-----------|------------|---------|
| defect (stretched) | MISS | weak PARTIAL | non-uniform scale invisible to detectors |
| control | clean | — | baseline canvas read |

## Evidence

- Mirage reads canvas partially: control 6 objects/3 text (bars +
  labels), defect 1 object/4 text — detection itself degrades on
  non-semantic raster.
- `anisotropy`: insufficient_witnesses on BOTH — the stretched chart
  produces no qualifying blob/text witnesses; aspect-abuse's
  squash signature doesn't transfer to canvas content.
- Honest gap: non-uniform CSS transform on canvas/WebGL is a real
  defect class the instrument currently cannot see — needs either
  pixel-level aspect statistics (content bounding box vs expected
  aspect) or canvas-aware witnesses. Queued, not patched.

Boundary documented: DOM-text detectors assume semantic raster;
canvas/WebGL needs a different witness layer (this is the Omni/
Metal problem arriving early — framebuffer content has no DOM).
