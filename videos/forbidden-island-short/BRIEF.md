---
workflow: general-video
flow: automation
storyboard: no
message: "North Sentinel is the island where just visiting is a crime."
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (movie-trivia-short format)
---

## Intent

A 20-second narrated vertical short for a US audience in the mystery and
unexplained stories niche: "The Island Where Nobody Is Allowed to Visit."
It opens on the hook title, then gives four facts and ends on a question
to the viewer ("Would you go?") to get comments.

## Script (voiceover)

1. There's an island where just visiting is a crime.
2. North Sentinel. In the Indian Ocean.
3. Its people have refused contact, for maybe sixty thousand years.
4. In 2004, one aimed his bow at a helicopter.
5. In 2018, an American went ashore. He never came back.
6. No one knows how many live there.

## Assets

- assets/audio/voiceover.m4a: local Kokoro TTS (am_michael, 1.08x), one phrase
  per line with the silences trimmed, -16 LUFS.
- assets/audio/bed.m4a: drone, surf, rotor and hits made by scripts/score.py, -24 LUFS.

## Notes

- Map tiles and satellite imagery were blocked in this sandbox, so the island and
  the Andaman chain are drawn as a nautical chart. The chain is schematic, not to scale.
- No Whisper model was available offline. Caption timings come from where each
  phrase is placed plus the pauses silencedetect found inside it.
- GSAP is vendored under assets/vendor because the CDN is blocked.
