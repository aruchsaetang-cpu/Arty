---
workflow: general-video
flow: automation
storyboard: no
message: "The Lost Colony: Where did they go?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "006"
---

## Intent

Hollow Truth File 006: The Lost Colony. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHERE DID THEY GO?"

## Script (voiceover)

1. In 1587, more than a hundred English settlers landed on Roanoke Island.
2. Their governor sailed back to England for supplies.
3. When he finally returned, three years later, everyone was gone.
4. The only clue was one word carved into a post. Croatoan.
5. No one knows what happened to them.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.12x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
