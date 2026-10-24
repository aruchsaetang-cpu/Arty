#!/usr/bin/env bash
# Render case-board shorts and re-encode them small enough to keep in git (~9 MB each).
#   tools/hollow-truth/render.sh videos/ht-005-flannan-isles [more project dirs...]
set -euo pipefail
for proj in "$@"; do
  name=$(basename "$proj")
  file=${name#ht-}; num=${file%%-*}; slug=${file#*-}
  raw=$(mktemp -d)/raw.mp4
  out="$proj/renders/hollow-truth-$num-$slug-20s.mp4"
  (cd "$proj" && npx --yes hyperframes@0.8.191 render -o "$raw" >/dev/null 2>&1)
  ffmpeg -y -loglevel error -i "$raw" -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p \
    -c:a copy -movflags +faststart "$out"
  rm -rf "$(dirname "$raw")" "$proj"/renders/work-* "$proj"/renders/.*transaction* 2>/dev/null || true
  echo "$out $(du -h "$out" | cut -f1)"
done
