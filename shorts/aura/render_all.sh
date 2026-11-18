#!/usr/bin/env bash
# Render every frame range (resumable: finished frames are skipped, empty placeholders are cleared first).
cd "$(dirname "$0")/../.."
find shorts/aura/frames -size 0 -name "*.png" -delete 2>/dev/null
for r in "1 390 1" "391 574 2" "575 1190 1"; do
  set -- $r
  STEP=$3 SAMPLES=16 /root/.venvs/bpy/bin/python shorts/aura/film.py 33 $1 $2 2>&1 | grep -E "WROTE|Error|Traceback"
  find shorts/aura/frames -size 0 -name "*.png" -delete
done
echo "frames: $(ls shorts/aura/frames | wc -l)"
