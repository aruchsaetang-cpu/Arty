---
workflow: general-video
flow: automation
storyboard: no
message: "D.B. Cooper: Who was he?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "007"
---

## Intent

Hollow Truth File 007: D.B. Cooper. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHO WAS HE?"

## Script (voiceover)

1. In 1971, a man hijacked a plane, saying his briefcase held a bomb.
2. He got $200,000, and four parachutes.
3. Then he jumped out the back, into the night.
4. In 1980, a boy found some of the cash by a river.
5. The man himself was never found.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
