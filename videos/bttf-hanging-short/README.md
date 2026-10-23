# Back to the Future III: hanging-scene Short

- `broll/m01–m03.mp4`: the movie picture cropped from the iPad screen recordings (source: YouTube @MOVIECLIPS)
- `src/f04, f06–f10.mp4`: Voice Memos takes #68, #75, #81, #86, #102, #109, in order (f05 was a duplicate of f04)
- `work/voice_tight.wav`: the 6 takes joined, with pauses removed (`tighten.py --db -32`)
- `work/script.txt`: script, one line per take; `/` = caption break, `~n` = syllable count
- `work/edit.json`: shots + captions + credit; rebuild with
  `python3 .claude/skills/my-edit-style/scripts/build_composition.py videos/bttf-hanging-short/work/edit.json videos/bttf-hanging-short/out`

To do: captions were timed with `align_script.py` (estimated). Once Whisper can download its model, run
`transcribe.py work/voice_tight.wav work/words.json`, then `chunk_captions.py` and rebuild. The last ~3 s
(26.9–30 s) has speech that isn't in the script.
