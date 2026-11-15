# Quick-start for the DeepSeek harness

## If you can run shell commands on this machine

`eyes` is installed globally (symlinked to the repo venv, works from
any directory as this user):

```
eyes interrogate <image> --json   # fact sheet
eyes score <ref> <candidate.png>  # 0-100 similarity
eyes pixdiff <ref> <candidate.png>
eyes zoom <image> --bbox x,y,w,h --analyze describe
```

Source repo (for reading implementation): `/Users/larsde/src/6digit-vision`

With-eyes arm becomes a measured loop: render -> score -> pixdiff ->
zoom the hottest diff region -> targeted edit -> repeat. Record every
score in `trace.jsonl`.

## If you cannot run commands there

Arm B still works: `facts/*.json` are precomputed interrogate sheets —
feed them to yourself as text context alongside the image. You lose
the iteration-time measurement loop but keep the perception facts.
That is the honest comparison: facts-in-context vs tools-in-loop.
