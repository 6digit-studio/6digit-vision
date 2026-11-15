#!/bin/bash
# Canonical renderer for the A/B experiment. Do not modify.
set -euo pipefail
HTML="${1:-candidate.html}"
OUT="${2:-candidate.png}"
W=$(cat SIZE_W)
H=$(cat SIZE_H)
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --virtual-time-budget=2000 \
  --screenshot="$OUT" --window-size="$W,$H" \
  "file://$PWD/$HTML" 2>/dev/null
# fail loudly if the render is not exactly the reference size
ACT=$(sips -g pixelWidth -g pixelHeight "$OUT" | awk '/pixel/{printf "%s ", $2}')
echo "rendered $OUT at $ACT(expected ${W} ${H})"
