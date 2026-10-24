---
workflow: general-video
flow: automation
storyboard: no
message: "The Taos Hum: Can you hear it?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "022"
---

## Intent

Hollow Truth File 022: The Taos Hum. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "CAN YOU HEAR IT?"

## Script (voiceover)

1. In Taos, New Mexico, some people hear a low hum that never stops.
2. Only about two percent of the people there can hear it.
3. In the 1990s, scientists from national labs investigated.
4. They couldn't find the source.
5. People around the world have reported the same hum.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
