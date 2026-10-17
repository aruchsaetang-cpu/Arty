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

- Two screen recordings of the Roadster demo (ramp, launch, thrusters, landing)
  and an Instagram Reel (car reveal, cabin view, drive-away), cut into
  `assets/footage/`.
- User voiceover (Voice Memos screen recording), denoised and leveled to
  -14 LUFS in `assets/audio/voiceover.m4a`; scene cues follow its pauses.

## Customizations

- User tip: a pause before "แต่" — the voiceover pauses 13.6–14.3s and the screen holds empty until "แต่" lands at 14.3s.
- User tip: the car-jump visual plays during the context section (9.7–13.7s).

## Notes

- Fonts (Kanit, Thai + Latin) and GSAP are vendored under `assets/` because the
  CDN is blocked.
