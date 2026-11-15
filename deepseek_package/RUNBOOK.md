# Quick-start for the DeepSeek harness

## If you can run shell commands on this machine

The full `eyes` toolkit lives at `/Users/larsde/src/6digit-vision`:

```
cd /Users/larsde/src/6digit-vision
.venv/bin/python -m eyes.cli interrogate <image> --json   # fact sheet
.venv/bin/python -m eyes.cli score <ref> <candidate.png>  # 0-100 similarity
.venv/bin/python -m eyes.cli pixdiff <ref> <candidate.png>
.venv/bin/python -m eyes.cli zoom <image> --bbox x,y,w,h --analyze describe
```

With-eyes arm becomes a measured loop: render -> score -> pixdiff ->
zoom the hottest diff region -> targeted edit -> repeat. Record every
score in `trace.jsonl`.

## If you cannot run commands there

Arm B still works: `facts/*.json` are precomputed interrogate sheets —
feed them to yourself as text context alongside the image. You lose
the iteration-time measurement loop but keep the perception facts.
That is the honest comparison: facts-in-context vs tools-in-loop.
