---
workflow: general-video
flow: automation
storyboard: no
message: "The Phaistos Disc: What does it say?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "023"
---

## Intent

Hollow Truth File 023: The Phaistos Disc. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT DOES IT SAY?"

## Script (voiceover)

1. In 1908, archaeologists in Crete found a clay disc covered in symbols.
2. It's around thirty seven hundred years old.
3. The symbols were stamped into the clay, like an early printing press.
4. 242 of them, spiraling to the center.
5. No one has ever deciphered it.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
