---
workflow: general-video
flow: automation
storyboard: no
message: "Göbekli Tepe: Who built it?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "020"
---

## Intent

Hollow Truth File 020: Göbekli Tepe. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHO BUILT IT?"

## Script (voiceover)

1. On a hill in Turkey stand giant carved stone pillars.
2. They're about eleven thousand years old.
3. That's around six thousand years before Stonehenge.
4. Built by people who had no writing, and no wheel.
5. And most of the site still hasn't been dug up.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
