---
workflow: general-video
flow: automation
storyboard: no
message: "The Nazca Lines: Who were they for?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "021"
---

## Intent

Hollow Truth File 021: The Nazca Lines. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHO WERE THEY FOR?"

## Script (voiceover)

1. In the desert of Peru are hundreds of giant drawings.
2. A hummingbird, a monkey, a spider. Some are longer than a football field.
3. They were made about two thousand years ago.
4. Most of them are best seen from the air.
5. So who were they made for?

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
