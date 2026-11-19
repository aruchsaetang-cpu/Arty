#!/usr/bin/env bash
# Render every frame range (resumable: finished frames are skipped, empty placeholders are cleared first).
# On twos (STEP 2) except the hand-held pursuit and the slow-motion reveal (follow .. reveal_close), which run on ones.
cd "$(dirname "$0")/../.."
find shorts/aura/frames -size 0 -name "*.png" -delete 2>/dev/null
read A B N < <(python3 -c "
import json; b=json.load(open('shorts/aura/beats.json')); S={s['id']:s for s in b['shots']}
print(S['follow']['f0'], S['reveal_close']['f1'], b['frames'])")
for r in "1 $((A-1)) 2" "$A $B 1" "$((B+1)) $N 2"; do
  set -- $r
  STEP=$3 SAMPLES=16 /root/.venvs/bpy/bin/python shorts/aura/film.py 33 $1 $2 2>&1 | grep -E "WROTE|Error|Traceback"
  find shorts/aura/frames -size 0 -name "*.png" -delete
done
echo "frames: $(ls shorts/aura/frames | wc -l)"
