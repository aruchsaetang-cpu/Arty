---
workflow: general-video
flow: automation
storyboard: no
message: "The Kentucky Meat Shower: Where did it come from?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "019"
---

## Intent

Hollow Truth File 019: The Kentucky Meat Shower. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHERE DID IT COME FROM?"

## Script (voiceover)

1. In 1876, it rained meat in Kentucky.
2. Chunks of red flesh fell from a clear sky over a farm.
3. Some pieces were up to four inches across.
4. Two men tasted it. They said it was mutton, or venison.
5. The best guess? Vultures, throwing up as they flew over.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
