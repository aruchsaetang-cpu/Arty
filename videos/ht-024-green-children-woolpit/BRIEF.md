---
workflow: general-video
flow: automation
storyboard: no
message: "The Green Children of Woolpit: Where did they come from?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "024"
---

## Intent

Hollow Truth File 024: The Green Children of Woolpit. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHERE DID THEY COME FROM?"

## Script (voiceover)

1. In 12th-century England, two children appeared in the village of Woolpit.
2. Their skin was green.
3. They spoke a language no one knew, and at first would only eat raw beans.
4. The girl later said they came from a land where the sun never shone.
5. Historians still argue about what really happened.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
