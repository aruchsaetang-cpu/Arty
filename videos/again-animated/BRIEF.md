---
workflow: general-video
flow: automation
storyboard: no
message: "You can fall. Just never quit."
destination: youtube + shorts
aspect: 1920x1080 (film), 1080x1920 (shorts)
language: en
length: 150s film + 8 × 20s shorts
angle: animated short film about discipline and struggle
---

## Intent

An original animated short in the genre of the Day One Films channel (reference:
"DISCIPLINE | An Animated Short Film", 4.8M views, mostly wordless, music-led): a
simple drawn character, dark moody rooms, sparse on-screen lines, and one emotional arc.

Story: snoozing the 5:00 alarm → phone until 3 a.m., "tomorrow" never comes → a stranger
stares back from the mirror → writes "DAY 1" → rain run and fall, failed push-ups, crossing
off days → misses days 9–11, the inner voice says "See? You can't do this." → the music
drops, 5:00 again, he wakes up anyway: "You can fall. / Just never quit." → day 23, 47, 68,
100 → the mirror again, "The stranger was gone." → AGAIN.

The character is our own design (egg head, a single curl, thick brows, navy hoodie with
orange drawstrings), not a copy of the reference channel's character.

## Look

Shaded skin and hoodie with rim light and blush, blinking and breathing, dust drifting in
light beams, rain splashes, bokeh, rotating sun rays, animated film grain, a warm/cool
grade, dips to black between story beats, flash cuts in the montage, light leaks on the
climax, and word-by-word captions. All hand-built in `scripts/gen.py`.

## Assets

- Music: generated with vidIQ (`vidiq_generate_music`, 145s cinematic piano → strings →
  climax), placed at 3s so its drop lands on the 5:00 wake-up and its climax on the
  montage. `assets/audio/score.m4a`.
- SFX: synthesised by `scripts/sfx.py` (alarm, snooze click, pen, rain, falls, heartbeat,
  door swell). `assets/audio/sfx.m4a`.
- All visuals are drawn SVG built by `scripts/gen.py` (writes `index.html`). On-screen text is English.

## Shorts

`scripts/gen_shorts.py` writes `short-ep1.html` … `short-ep8.html`: 20s vertical cuts of
the rendered film (center square crop) with a hook title and an episode bar.
Cover prompts for every clip are in `COVERS.md`.

## Notes

- Edit the film by editing `scripts/gen.py`, then `python3 scripts/gen.py`; don't hand-edit
  `index.html`.
- The shorts read `renders/again-2m30s.mp4`, so re-render the film before the shorts.
