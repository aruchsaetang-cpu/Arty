#!/usr/bin/env bash
# Render a built project and master the audio to the reference loudness (~ -17 LUFS).
# usage: render.sh <project-dir> <out.mp4>
set -euo pipefail
p="$(cd "$1" && pwd)"; out="$(realpath -m "$2")"
command -v hyperframes >/dev/null || npm install -g hyperframes
hyperframes browser ensure >/dev/null
(cd "$p" && hyperframes render -o "$p/_raw.mp4" --fps 30)
ffmpeg -v error -y -i "$p/_raw.mp4" -c:v copy -af "loudnorm=I=-17:TP=-1:LRA=3" -ar 48000 -c:a aac -b:a 192k -movflags +faststart "$out"
rm -f "$p/_raw.mp4"
ffprobe -v error -show_entries format=duration:stream=width,height,avg_frame_rate -of compact "$out"
