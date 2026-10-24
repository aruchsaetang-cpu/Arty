---
workflow: general-video
flow: automation
storyboard: no
message: "The Tunguska Event: What hit siberia?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "014"
---

## Intent

Hollow Truth File 014: The Tunguska Event. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT HIT SIBERIA?"

## Script (voiceover)

1. In 1908, a giant explosion flattened a Siberian forest.
2. About eighty million trees were knocked down.
3. Over more than two thousand square kilometers.
4. A man forty miles away said it felt like his shirt was on fire.
5. But no one ever found a crater.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
