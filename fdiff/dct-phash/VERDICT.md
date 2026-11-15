# dct-phash — verdict

Mechanism: 32x32 thumbnail -> per-channel 2D DCT-II (ortho) -> keep the
low 8x8 band (DC excluded). Score = `1 - max(band_rel_l2, color_rel)`.
Localization: ~150px cells, per-cell band distance in absolute units of
global band energy, threshold 0.35, 8-connected merge, then bbox
tightened by gaussian-blurred low-pass residual clusters.

Bar run: `uv run python3 tools/fdiff_bar.py fdiff/dct-phash/fdiff.py`

```
criterion                     score  regions
identical->~1.0                 1.0        0
block-shift->localized       0.9491        3
1px-translate->low-diff       0.995        0
same-img sanity                 1.0        0
ui1-pair signal              0.7453        4
```

## Per-criterion

1. **identical -> ~1.0 — CAUGHT.** score exactly 1.0, 0 regions.
   control.png vs itself also 1.0 / 0.

2. **planted 20px block shift -> localized — CAUGHT.** score 0.9491
   (band_rel_l2=0.051), 3 regions: main [483,293,722,385] plus edge
   strips [439,293,482,340] and [739,293,781,340]. Planted edit was
   rows 300-420, content shifted +20px inside x360-780 — detected boxes
   sit inside that band and hug the right edge (x~781); the smooth
   left portion of the band produces weaker low-freq residual and is
   partially missed. Localization is real but coarse-grained by the
   cell/residual pipeline.

3. **1px global translation -> low diff — CAUGHT (suppression, not
   alignment).** score 0.995, 0 regions. The 1px shift is ~0.03 thumb
   pixels and ~0.007 cell-DCT pixels; max cell distance 0.33 vs
   threshold 0.35 — it lands just under the noise floor. Honest
   gradient measured on the same image: 2px -> 0.991/6 regions,
   4px -> 0.981/2, 8px -> 0.964/5, 16px -> 0.927/2. Suppression holds
   at 1px only; larger global shifts DO register (correctly — they are
   real structural changes at this band's resolution). No alignment
   step is claimed.

4. **dense-text AA/compression noise -> low false-positive — CAUGHT.**
   The bar's literal test is identical-vs-itself (1.0/0). Real-noise
   probes on ui1 candidate: gaussian sigma=5 -> 0.987/0 regions,
   sigma=15 (heavy) -> 0.983/0 regions, JPEG q70 -> 0.986/0 regions.
   Noise elevates cell distances uniformly (~0.04-0.13, below the
   0.35 threshold everywhere) while real edits are sparse and large —
   that uniform-vs-sparse separation is what the threshold exploits.

5. **ui1 login pair -> fine-edit signal — CAUGHT.** score 0.7453
   (band_rel_l2=0.255, phash_hamming=0.095), 4 regions:
   [435,97,702,194], [434,216,510,268], [422,287,778,379] in the
   center column and [216,757,977,800] footer band — matching the
   pixel-diff heatmap's changed zones (center card column + footer).
   Coarser than pixdiff's 12 pixel-level regions by construction: this
   channel sees low-frequency structure, so adjacent fine edits merge
   into structural blobs.

## Extra probes (not bar criteria)

- solid 200x200 red patch -> 0.617, 1 region [592,392,808,608] tightly
  on the patch. Color-field edits register via both band coeffs and
  the mean-color term.
- local 3px shift of a text band -> score 1.0, 0 regions. **MISS by
  design**: sub-band-resolution motion is invisible — documented
  limit, not a bug.
- RGBA vs RGB of same image -> 1.0 (alpha dropped, correctly
  identical); L vs RGB -> 0.80 with region on saturated areas;
  480x800 vs 1200x800 -> 0.149 whole-canvas region (genuinely
  different renders; b resized to a's canvas).
- runtime ~0.04-0.16s per pair on 1200x800.

## Honest limits

- Score is structural, not pixel fidelity: a small sharp edit (block
  shift 0.949) scores higher than a broad structural difference (ui1
  0.745) because the metric is global low-band distance, not
  pixel-match fraction. Do not compare absolute values against
  pixdiff's SSIM blend; the scales differ.
- DC excluded from the band -> pure global brightness/contrast shifts
  are only caught by the weak mean-color term, not the structure band.
- Cell threshold 0.35 is calibrated on this corpus; a differently
  textured corpus may need retuning (notes field exposes it).
