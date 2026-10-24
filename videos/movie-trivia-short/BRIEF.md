---
workflow: general-video
flow: automation
storyboard: no
message: "5 เรื่องจริงหลังกองถ่าย ที่คุณอาจไม่เคยรู้"
destination: social-vertical
aspect: 1080x1920
language: th
length: 30s
angle: quiz-style "did you know" countdown
---

## Intent

A 30-second Thai movie-trivia short: hook (0–3s), five behind-the-scenes facts
at 5s each (3–28s), and a comment prompt (28–30s). Each fact opens with the film
title and a teaser, then a "ding" reveals the answer 2.4s in.

1. Jaws (1975) — the mechanical shark kept breaking, so Spielberg showed it less.
2. Titanic (1997) — the film cost about $200M; the real ship cost about $7.5M in 1912.
3. The Lord of the Rings: The Two Towers (2002) — Viggo Mortensen broke toes kicking
   a helmet; the scream in the film is real.
4. Star Wars (1977) — Darth Vader's body is David Prowse, the voice is James Earl Jones.
5. Toy Story 2 (1999) — a command wiped most of the film's files; a staffer's
   home backup saved it.

## Assets

- No footage or film stills (copyright). Every visual is drawn: SVG props per fact,
  a film-strip frame, number badges.
- Synthesised quiz score (`scripts/score.py` → `assets/audio/quiz-score.m4a`):
  120 bpm clock pulse, a whoosh into each fact, a ding on each reveal.

## Customizations

- The user skipped the brief questions, so everything here is a default: subject,
  Thai text, and a music bed with no voiceover.

## Notes

- Fonts (Kanit, Thai + Latin) and GSAP are vendored under `assets/` because the
  CDN is blocked.
