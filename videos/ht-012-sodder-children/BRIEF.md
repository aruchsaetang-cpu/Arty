---
workflow: general-video
flow: automation
storyboard: no
message: "The Sodder Children: What happened to them?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "012"
---

## Intent

Hollow Truth File 012: The Sodder Children. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHAT HAPPENED TO THEM?"

## Script (voiceover)

1. On Christmas Eve 1945, a fire destroyed the Sodder family home in West Virginia.
2. Five of their children were never seen again.
3. No bodies were found in the ashes.
4. Their parents believed they were still alive, and put up a billboard asking for help.
5. It stood by the road for decades.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.12x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
