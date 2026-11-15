# motion — real animation frames (injected CSS animation on live page)

Last dark-corner probe: video-like frame sequences on real captures.
Two attempts, both honest:

1. **Smooth-scroll capture**: headless Chrome produced ZERO intermediate
   frames — all 6 screenshots identical (changed_pct 0.0, static_pairs
   everywhere). scroll-behavior:smooth doesn't animate without
   compositor frames in headless. Documented limitation.
2. **Injected CSS animation** (blue dot translating across example.com,
   real Chrome rendering): 6 frames at 400ms — changed_pct ~1.15%/frame,
   static_pairs EMPTY, scroll dy=None (correct — translation isn't
   scroll). eyes reel sees real animation motion correctly.

## Verdict

Reel handles genuine motion sequences: pixel diffs fire on real
animation, static detection doesn't false-positive, scroll estimator
correctly abstains (dy=None — no vertical scroll). The honest gaps:
headless smooth-scroll yields no intermediates (needs CDP screencast
or headed mode for true video), and injected animation is semi-synthetic
(real renderer, scripted motion) — labeled as such.
