#!/usr/bin/env bash
# Unattended: render every missing frame (restarting render_all.sh if it exits early), then the finish pass.
# Start detached so it survives the 2-hour tool limit:
#   setsid nohup bash shorts/aura/run_to_end.sh > shorts/aura/run_to_end.log 2>&1 < /dev/null &
cd "$(dirname "$0")/../.."
missing() { python3 - <<'PY'
import os, glob
from PIL import Image
fs = sorted(glob.glob('shorts/aura/frames/f*.png'), key=os.path.getmtime)[-2:]
for p in fs:
    try: Image.open(p).load()
    except Exception: os.remove(p)                      # a half-written frame is redone
ok = lambda f: os.path.exists(f'shorts/aura/frames/f{f:04d}.png') and os.path.getsize(f'shorts/aura/frames/f{f:04d}.png') > 0
print(sum(not ok(f) for f in range(1, 1170)))
PY
}
for i in 1 2 3 4 5 6 7 8; do
  m=$(missing); echo "$(date +%H:%M) pass $i: $m frames missing"
  [ "$m" = "0" ] && break
  bash shorts/aura/render_all.sh
done
m=$(missing)
if [ "$m" = "0" ]; then
  echo "$(date +%H:%M) all frames done: finish pass"
  cd shorts/aura && rm -rf graded graded_hd && bash finish.sh && echo "$(date +%H:%M) FILM DONE: shorts/aura/out/aura_monster.mp4" && touch run_to_end.done
else
  echo "$(date +%H:%M) gave up: $m frames still missing"
fi
