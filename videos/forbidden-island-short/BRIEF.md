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
channel: Hollow Truth
---

## Intent

A 20-second narrated vertical short for a US audience in the mystery and
unexplained stories niche: "The Island Where Nobody Is Allowed to Visit."
It opens on the hook title, then gives four facts and ends on a question
to the viewer ("Would you go?") to get comments.

## Customizations

- Branded for the Hollow Truth channel: "HOLLOW TRUTH · FILE 001" over the hook,
  the channel name typed in under "WOULD YOU GO?" at the end.
- Darker look for the channel: night chart, fog, vignette, film grain, titles that
  flicker like a failing light, the picture dipping dark at each cut, the no-go ring pulsing.
- Voice pitched down 7% with a short reverb tail. The bed drops to E1 and adds a
  high tone a half-step apart.

- Real footage replaces the drawn chart for 0–17.3s: five screen recordings the
  user made of the Air India AI549 flight over North Sentinel (YouTube, Jerin G,
  https://youtu.be/R1VbbpjYkc4). They're cropped to 9:16 clear of YouTube's cards
  and graded dark and cold (exposure -0.45, saturation -0.45). The drawn chart stays
  for the "?" ending. The drawn helicopter and canoe were removed, since drawings
  over real footage would read as fake.

## Script (voiceover)

1. There's an island where just visiting is a crime.
2. North Sentinel. In the Indian Ocean.
3. Its people have refused contact, for maybe sixty thousand years.
4. In 2004, one aimed his bow at a helicopter.
5. In 2018, an American went ashore. He never came back.
6. No one knows how many live there.

## Assets

- assets/audio/voiceover.m4a: local Kokoro TTS (am_michael, 1.08x), one phrase
  per line with the silences trimmed, pitched down, -16 LUFS.
- assets/audio/bed.m4a: drone, surf, rotor and hits made by scripts/score.py, -23 LUFS.

## Notes

- Footage rights: the uploader licenses this footage (the contact email is in the
  video description). Clear it before monetizing.
- assets/footage/shoreline-high.mp4 is a tighter crop (511px wide, scaled up 2.1x)
  to avoid two YouTube cards, so it's softer than the others.
- No Whisper model was available offline. Caption timings come from where each
  phrase is placed plus the pauses silencedetect found inside it.
- GSAP is vendored under assets/vendor because the CDN is blocked.
