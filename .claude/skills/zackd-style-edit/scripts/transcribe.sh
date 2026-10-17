#!/usr/bin/env bash
# Word-level transcript. usage: transcribe.sh <audio> <outdir> [lang=en] [model=small]
# Writes <outdir>/<name>.json (Whisper format with segments[].words[]).
set -euo pipefail
a="$1"; o="$2"; lang="${3:-en}"; model="${4:-small}"
command -v whisper >/dev/null || pip install -q openai-whisper
[ "$lang" = en ] && [[ "$model" != *.en ]] && [[ "$model" != large* ]] && model="$model.en"
whisper "$a" --model "$model" --language "$lang" --word_timestamps True \
  --output_format json --output_dir "$o" --fp16 False
