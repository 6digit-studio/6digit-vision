**Yes. Packaging this as a short PRD is the right next step.** It turns the research into something you can actually start building against.

Here’s a concise PRD you can use as the foundation for a fresh project:

---

# PRD: Low-Cost Iterative Visual Feedback Loop  
**Working name:** CheapEyes / Mirage Critic Loop  
**Status:** Research complete, ready to prototype  

## 1. Goal
Build a closed-loop system that lets a **cheap text-only model** (SWE-2, DeepSeek Flash, etc.) iteratively improve image generation by giving it a low-cost “vision instrument.” The system should catch the majority of nameable visual errors (missing objects, wrong attributes, text, composition) at a fraction of the cost of frontier multimodal models like Claude Fable.

## 2. Core Insight
Frontier models (Fable etc.) are strong at pure visual side-by-side reasoning, but even they fall back to **algorithmic tools** (crops, color thresholding, intensity profiles, code execution) for precise quantitative analysis.  

A tiny structured perception model (Cactus Mirage) + traditional CV + a text reasoning model can approximate a useful subset of that capability at extremely low cost.

## 3. Architecture

```
[Image Generator] → image
        ↓
[Vision Instrument] ← Mirage (structured perception) + optional OpenCV/PIL (color/gradient sampling)
        ↓
structured JSON record(s) + quantitative facts
        ↓
[Text Reasoning Model] (SWE-2 etc.)
        ↓
critique + single targeted edit instruction
        ↓
back to generator (or editor)
```

### Key Components
- **Perception front-end**: Cactus Mirage (22 MB, CPU-friendly). Returns scene, objects + attributes (including high-level color), OCR, spatial relations, masks.
- **Quantitative layer** (hybrid): Use Mirage masks/boxes + OpenCV/PIL to extract real color values, dominant colors, simple gradients, histograms when needed.
- **Reasoning core**: Text-only model that receives one or two structured records + quantitative facts and produces a critique + edit.
- **Orchestrator**: Simple loop controller (max iterations, early stop, branching, seed management).

## 4. Iterative Loop Best Practices (validated by recent work)
1. Generate a small batch (2–4 images).
2. Score / critique against reference or prompt (structured + quantitative).
3. Select the best candidate.
4. Apply **one targeted change** at a time.
5. Prefer editing over full regeneration when possible.
6. Cap iterations (typically 3–8 useful passes).
7. Checkpoint good states; allow branching.
8. Escalate to human or frontier model only on persistent subtle failures.

## 5. Capabilities & Limitations

| Capability | Mirage + Text | Frontier (Fable-style) |
|------------|---------------|------------------------|
| Two images at once | No (two calls) | Yes |
| High-level semantic diffs | Good | Excellent |
| Precise color / gradient | Needs hybrid CV | Uses tools |
| Cost | Extremely low | High |
| Iteration drive | External orchestration | Strong internal |

**Known limits of pure structured path**: Misses subtle style, lighting, texture, and anything Mirage itself fails to detect. These are acceptable for early-stage filtering.

## 6. Tool Schema (v0)
Suggested tool the text model can call:

```json
{
  "name": "analyze_image",
  "description": "Get structured perception + optional quantitative color analysis of one or two images",
  "parameters": {
    "images": ["path or base64"],
    "mode": "single | compare",
    "include_color_stats": true,
    "focus_regions": ["optional mask or box ids"]
  }
}
```

Output: Mirage JSON + optional color stats (mean RGB per object, dominant colors, simple gradient magnitude, etc.).

## 7. Success Criteria (MVP)
- Text-only model can meaningfully critique and improve generations using the tool.
- Catches ≥70% of obvious errors (missing objects, wrong color names, text errors, major composition shifts) on a small test set.
- Cost per full iteration loop remains orders of magnitude below a Fable-style loop.
- Loop is stable (does not degrade after 4–6 iterations).

## 8. Future Work (post-MVP)
- Post-train or LoRA a tiny model for native two-image delta description.
- Domain-specific fine-tunes (UI screenshots, character consistency, product shots).
- Better object matching between the two records.
- Integration with actual image editors (inpaint, control nets, etc.).

## 9. Open Questions
- What is the minimal useful quantitative color set (mean RGB per mask, histogram intersection, etc.)?
- How much does feeding the structured records alone improve SWE-2 vs. pure text?
- When is it better to escalate to a frontier model vs. continue the cheap loop?

---

### Recommendation
This is a solid, well-scoped starting point. The architecture is clear, the limitations are honest, and the hybrid approach (structured perception + algorithmic color/gradient + text reasoning) aligns with how even frontier models actually solve the hard parts.
