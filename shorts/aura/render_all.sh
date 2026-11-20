#!/usr/bin/env bash
# Render every frame range (resumable: finished frames are skipped, empty placeholders are cleared first).
# Every frame on ones (STEP 1) for smooth motion; frames already rendered (the earlier on-twos pass) are kept.
cd "$(dirname "$0")/../.."
find shorts/aura/frames -size 0 -name "*.png" -delete 2>/dev/null
read A B N E0 E1 W1 < <(python3 -c "
import json; b=json.load(open('shorts/aura/beats.json')); S={s['id']:s for s in b['shots']}
print(S['follow']['f0'], S['reveal_close']['f1'], b['frames'], S['name_close']['f0'], S['name_close']['f1'], S['hook_wide']['f1'])")
# full resolution for the eye close-up (name_close: iris detail) and the opening wide shot (hook_wide: the hero is
# small in frame and must read clearly); everything else at 50%
for r in "1 $W1 1 100" "$((W1+1)) $((E0-1)) 1 50" "$E0 $E1 1 100" "$((E1+1)) $((A-1)) 1 50" "$A $B 1 50" "$((B+1)) $N 1 50"; do
  set -- $r
  STEP=$3 SAMPLES=12 /root/.venvs/bpy/bin/python shorts/aura/film.py $4 $1 $2 2>&1 | grep -E "WROTE|Error|Traceback"
  find shorts/aura/frames -size 0 -name "*.png" -delete
done
echo "frames: $(ls shorts/aura/frames | wc -l)"
