---
workflow: general-video
flow: automation
storyboard: no
message: "ล้มได้ แต่ห้ามล้มเลิก"
destination: youtube + shorts
aspect: 1920x1080 (film), 1080x1920 (shorts)
language: th
length: 150s film + 8 × 20s shorts
angle: animated short film about discipline and struggle
---

## Intent

An original animated short in the genre of the Day One Films channel (reference:
"DISCIPLINE | An Animated Short Film", 4.8M views, mostly wordless, music-led): a
simple drawn character, dark moody rooms, sparse on-screen lines, and one emotional arc.

Story: snoozing the 5:00 alarm → phone until 3 a.m., "tomorrow" never comes → he doesn't
recognise himself in the mirror → writes "วันที่ 1" → rain run and fall, failed push-ups,
crossing off days → misses days 9–11, the inner voice says "แกทำไม่ได้หรอก" → the music
drops, 5:00 again, he wakes up anyway: "ทุกคนล้มได้ / แต่ห้ามล้มเลิก" → day 23, 47, 68,
100 → the mirror again, now familiar → AGAIN. (อีกครั้ง).

The character is our own design (egg head, a single curl, thick brows, navy hoodie with
orange drawstrings), not a copy of the reference channel's character.

## Assets

- Music: generated with vidIQ (`vidiq_generate_music`, 145s cinematic piano → strings →
  climax), placed at 3s so its drop lands on the 5:00 wake-up and its climax on the
  montage. `assets/audio/score.m4a`.
- SFX: synthesised by `scripts/sfx.py` (alarm, snooze click, pen, rain, falls, heartbeat,
  door swell). `assets/audio/sfx.m4a`.
- All visuals are drawn SVG built by `scripts/gen.py` (writes `index.html`).

## Shorts

`scripts/gen_shorts.py` writes `short-ep1.html` … `short-ep8.html`: 20s vertical cuts of
the rendered film (center square crop) with a hook title and an episode bar.
Cover prompts for every clip are in `COVERS.md`.

## Notes

- Edit the film by editing `scripts/gen.py`, then `python3 scripts/gen.py`; don't hand-edit
  `index.html`.
- The shorts read `renders/again-2m30s.mp4`, so re-render the film before the shorts.
