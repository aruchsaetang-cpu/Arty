#!/usr/bin/env bash
# Aura + grade every frame, upscale to 1080x1920, burn subtitles, mux the mix, QA.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
python3 mix.py
python3 compose.py
python3 subs.py
if [ -f caps/frame_000001.png ]; then   # HyperFrames word-pop captions (captions.py), Whisper-timed
  IN=(-framerate 30 -i 'graded/f%04d.png' -framerate 30 -i 'caps/frame_%06d.png' -i audio/mix.wav)
  VF=(-filter_complex "[0]scale=1080:1920:flags=lanczos,unsharp=5:5:0.6:5:5:0.0,noise=alls=5:allf=t[v];[v][1]overlay=format=auto[o]" -map "[o]" -map 2:a)
else                                     # fallback: burned-in ASS sentence subtitles
  IN=(-framerate 30 -i 'graded/f%04d.png' -i audio/mix.wav)
  VF=(-vf "scale=1080:1920:flags=lanczos,unsharp=5:5:0.6:5:5:0.0,noise=alls=5:allf=t,ass=subs.ass")
fi
ffmpeg -v error -y "${IN[@]}" "${VF[@]}" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart \
  "out/aura_monster.mp4"
echo "--- QA"
ffprobe -v error -show_entries format=duration -of csv=p=0 out/aura_monster.mp4
ffmpeg -hide_banner -i out/aura_monster.mp4 -vf "blackdetect=d=0.2:pix_th=0.06,freezedetect=n=-60dB:d=0.6" -an -f null - 2>&1 \
  | grep -E "black_start|freeze_start" || echo "no black or frozen spans"
ffmpeg -v error -y -i out/aura_monster.mp4 -vf "fps=1/3,scale=216:384,tile=7x2" -frames:v 1 out/qa_sheet.jpg && echo "qa sheet: out/qa_sheet.jpg"
