---
workflow: general-video
flow: automation
storyboard: no
message: "The Oak Island Money Pit: What's down there?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "017"
---

## Intent

Hollow Truth File 017: The Oak Island Money Pit. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT'S DOWN THERE?"

## Script (voiceover)

1. In 1795, a teenager found a strange dip in the ground on a Canadian island.
2. Early diggers reported wooden platforms every ten feet down.
3. Then the pit flooded with seawater.
4. People have dug there for over two hundred years. Six have died trying.
5. No treasure has ever been found.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.12x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
