---
workflow: general-video
flow: automation
storyboard: no
message: "The Dancing Plague of 1518: What made them dance?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "013"
---

## Intent

Hollow Truth File 013: The Dancing Plague of 1518. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT MADE THEM DANCE?"

## Script (voiceover)

1. In 1518, a woman in Strasbourg started dancing in the street.
2. She didn't stop for days.
3. Within weeks, dozens of people had joined her.
4. Officials decided more dancing would cure it, so they built a stage and hired musicians.
5. No one knows what made them dance.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
