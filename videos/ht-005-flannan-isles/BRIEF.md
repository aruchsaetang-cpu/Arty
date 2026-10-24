---
workflow: general-video
flow: automation
storyboard: no
message: "The Lighthouse Keepers Who Vanished: Where did they go?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "005"
---

## Intent

Hollow Truth File 005: The Lighthouse Keepers Who Vanished. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHERE DID THEY GO?"

## Script (voiceover)

1. In December 1900, three lighthouse keepers vanished from a remote Scottish island.
2. The light had gone dark. The door and the gate were shut.
3. Two sets of oilskins were gone. The third was still on its hook.
4. So one man went out into the storm without his coat.
5. None of them were ever found.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
