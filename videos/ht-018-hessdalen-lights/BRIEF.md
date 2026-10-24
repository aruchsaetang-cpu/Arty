---
workflow: general-video
flow: automation
storyboard: no
message: "The Hessdalen Lights: What are they?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "018"
---

## Intent

Hollow Truth File 018: The Hessdalen Lights. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT ARE THEY?"

## Script (voiceover)

1. In a quiet valley in Norway, strange lights appear in the sky.
2. Some hover for over an hour. Some shoot across the valley.
3. In the early 1980s, people saw them up to twenty times a week.
4. Scientists built a station in the valley to record them.
5. They still can't fully explain them.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
