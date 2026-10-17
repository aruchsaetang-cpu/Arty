#!/usr/bin/env bash
# Measure a reference clip: metadata, cuts, caption changes, silences, loudness, contact sheet.
# usage: analyze.sh <video> <outdir>
set -euo pipefail
v="$1"; o="$2"; mkdir -p "$o/frames"
echo "## metadata"
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels -of compact "$v"
echo "## hard cuts (scene>0.35, UI band excluded)"
ffmpeg -i "$v" -vf "crop=iw:ih*0.6:0:ih*0.1,scale=320:-2,select='gt(scene,0.35)',showinfo" -an -f null - 2>&1 \
  | grep -o 'pts_time:[0-9.]*' | cut -d: -f2 | awk '{if(NR==1||$1-p>0.15)printf "%.2f ",$1; p=$1} END{print ""}' || true
echo "## caption-band changes (approx. caption swap times)"
ffmpeg -i "$v" -vf "crop=iw*0.7:ih*0.055:iw*0.15:ih*0.685,format=gray,select='gt(scene,0.12)',showinfo" -an -f null - 2>&1 \
  | grep -o 'pts_time:[0-9.]*' | cut -d: -f2 | awk '{if(NR==1||$1-p>0.15)printf "%.2f ",$1; p=$1} END{print ""}' || true
echo "## silences (-35 dB, >0.15 s)"
ffmpeg -i "$v" -af silencedetect=n=-35dB:d=0.15 -f null - 2>&1 | grep -oE 'silence_(start|end): [0-9.]+' | tr '\n' ' ' || true; echo
echo "## loudness"
ffmpeg -i "$v" -af ebur128 -f null - 2>&1 | grep -E '^\s+(I|LRA|Peak):' | tr -s ' ' || true
ffmpeg -v error -y -i "$v" -vf "fps=4,scale=320:-2" "$o/frames/%03d.jpg"
ffmpeg -v error -y -i "$v" -vf "fps=4,scale=214:-2,tile=8x6:padding=4" -frames:v 1 "$o/sheet.jpg"
ffmpeg -v error -y -i "$v" -vn -ac 1 -ar 16000 "$o/audio.wav"
echo "frames -> $o/frames (4 fps), contact sheet -> $o/sheet.jpg, audio -> $o/audio.wav"
