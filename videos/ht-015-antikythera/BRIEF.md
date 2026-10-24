---
workflow: general-video
flow: automation
storyboard: no
message: "The Antikythera Mechanism: Who built it?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "015"
---

## Intent

Hollow Truth File 015: The Antikythera Mechanism. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHO BUILT IT?"

## Script (voiceover)

1. In 1901, divers pulled a lump of corroded bronze from an ancient shipwreck.
2. Inside were dozens of tiny, precise gears.
3. It tracked the sun and the moon, and predicted eclipses.
4. It's over two thousand years old.
5. Nothing this complex appears again for more than a thousand years.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.12x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
