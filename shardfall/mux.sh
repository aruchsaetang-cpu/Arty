#!/bin/sh
set -e
cd "$(dirname "$0")"
: > parts.txt
for i in $(seq 0 11); do echo "file 'parts/p$i.mp4'" >> parts.txt; done
ffmpeg -loglevel error -y -f concat -safe 0 -i parts.txt -i score.wav -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart SHARDFALL.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 SHARDFALL.mp4
