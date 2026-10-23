# Back to the Future III: hanging-scene Short

- `broll/m01–m03.mp4`: the movie picture cropped from the iPad screen recordings (source: YouTube @MOVIECLIPS)
- `src/f04, f06–f10.mp4`: Voice Memos takes #68, #75, #81, #86, #102, #109 (f05 was a duplicate of f04). Script order is #68 → #102 → #75 → #81 → #86 → #109
- `work/voice_tight.wav`: the 6 takes joined in script order, with pauses removed (`tighten.py --db -32`)
- `work/script.txt`: script, one line per take; `/` = caption break, `~n` = syllable count
- `work/edit.json`: shots + captions + credit; rebuild with
  `python3 .claude/skills/my-edit-style/scripts/build_composition.py videos/bttf-hanging-short/work/edit.json videos/bttf-hanging-short/out`

Captions: text per speech chunk from Whisper small (ONNX build via sherpa-onnx, downloaded from GitHub because
HuggingFace is blocked) in `work/asr_segments.json`, checked against the script, then each chunk was timed with
`align_script.py`. The voiceover matches the script.
