---
workflow: general-video
flow: automation
storyboard: no
message: "The Max Headroom Hijacking: Who was behind the mask?"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "011"
---

## Intent

Hollow Truth File 011: The Max Headroom Hijacking. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "WHO WAS BEHIND THE MASK?"

## Script (voiceover)

1. In 1987, someone hijacked a Chicago TV broadcast.
2. A man in a Max Headroom mask appeared on screen for a few seconds.
3. Two hours later, he did it again, on another channel.
4. This time for ninety seconds, laughing and moaning.
5. The FCC never found out who he was.

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS (am_michael, 1.05x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
