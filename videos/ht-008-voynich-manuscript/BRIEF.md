---
workflow: general-video
flow: automation
storyboard: no
message: "The Voynich Manuscript: What does it say?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "008"
---

## Intent

Hollow Truth File 008: The Voynich Manuscript. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT DOES IT SAY?"

## Script (voiceover)

1. This book is about six hundred years old.
2. It's full of plants that don't exist, and star charts no one can match.
3. And it's written in a script that nobody can read.
4. Codebreakers have tried for over a century.
5. No one has ever proven they can read it.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
