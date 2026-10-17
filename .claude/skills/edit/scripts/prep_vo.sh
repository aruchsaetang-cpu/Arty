#!/usr/bin/env bash
# Tighten a voiceover like the reference: no audible breaths/pauses (gaps <= ~0.08 s),
# loudness-normalised. usage: prep_vo.sh <in-audio-or-video> <out.wav>
set -euo pipefail
ffmpeg -v error -y -i "$1" -vn -ac 1 -ar 48000 -af \
 "highpass=f=70,silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.05:stop_periods=-1:stop_duration=0.15:stop_threshold=-40dB:stop_silence=0.08,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=4" "$2"
echo "$2: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$2") s"
