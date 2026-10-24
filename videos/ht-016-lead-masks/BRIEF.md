---
workflow: general-video
flow: automation
storyboard: no
message: "The Lead Masks Case: What were they waiting for?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "016"
---

## Intent

Hollow Truth File 016: The Lead Masks Case. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT WERE THEY WAITING FOR?"

## Script (voiceover)

1. In 1966, two men were found dead on a hill in Brazil.
2. They wore suits, raincoats, and lead masks.
3. A notebook said: 4:30 PM, be at the agreed place.
4. 6:30 PM, swallow capsules, protect metals, wait for mask signal.
5. No cause of death was ever found.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.12x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
