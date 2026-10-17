---
workflow: general-video
flow: automation
storyboard: no
message: "รถที่กระโดดเก่งที่สุดในโลก แต่ยังไม่ใช่รถบิน"
destination: social-vertical
aspect: 1080x1920
language: th
length: 30s
angle: myth-vs-reality news short
---

## Intent

A 30-second Thai short about the new Tesla Roadster "flying" demo, built from the
user's script: hook (0–3s), context (3–15s), "แต่" turn (15–18s), reveal (18–30s).
A-roll and B-roll of the Tesla Roadster carry the visuals.

## Assets

- No user photos supplied. Image hosts are blocked by the environment's network
  policy, so the Roadster, Cybertruck and launch tower are drawn as SVG
  illustrations in `index.html`. Real photos can replace them later.

## Customizations

- User tip: a half-second pause before "แต่" (15.0–15.5s is held empty).
- User tip: the car-jump visual plays during the context section (9.4–15s).

## Notes

- No voiceover: the local TTS has no Thai voice and online TTS hosts are blocked.
  All script lines appear as on-screen Thai text timed to the script beats.
- Fonts (Kanit, Thai + Latin) and GSAP are vendored under `assets/` because the
  CDN is blocked.
