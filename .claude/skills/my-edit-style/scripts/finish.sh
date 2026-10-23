#!/usr/bin/env bash
# Final delivery: two-pass loudnorm to -14 LUFS (Shorts/TikTok), video stream copied.
# usage: finish.sh IN.mp4 OUT.mp4 [LUFS]
set -euo pipefail
in="$1"; out="$2"; target="${3:--14}"
stats=$(ffmpeg -hide_banner -i "$in" -af "loudnorm=I=${target}:TP=-1.5:LRA=7:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
get() { echo "$stats" | grep "\"$1\"" | sed -E 's/.*: "([^"]+)".*/\1/'; }
ffmpeg -v error -y -i "$in" -c:v copy -af "loudnorm=I=${target}:TP=-1.5:LRA=7:measured_I=$(get input_i):measured_TP=$(get input_tp):measured_LRA=$(get input_lra):measured_thresh=$(get input_thresh):offset=$(get target_offset):linear=true" -ar 48000 -c:a aac -b:a 192k "$out"
echo "wrote $out at ${target} LUFS"
