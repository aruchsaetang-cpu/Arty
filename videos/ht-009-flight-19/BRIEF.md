---
workflow: general-video
flow: automation
storyboard: no
message: "Flight 19: What took them?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "009"
---

## Intent

Hollow Truth File 009: Flight 19. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT TOOK THEM?"

## Script (voiceover)

1. In 1945, five Navy bombers left Florida on a training flight.
2. The flight leader radioed that both his compasses had failed.
3. They were never seen again. Fourteen men, gone.
4. A rescue plane went looking. It vanished too, with thirteen men.
5. No wreckage was ever found.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
