# Arty style: cinematic manhwa in Neon Harbor

Our shorts put **cel-shaded manhwa characters with ink outlines** into a **realistic 3D night city**
(Neon Harbor), lit by neon, rain and wet reflections. Earlier the guide described a paper-diorama
look; that direction is retired (its look test stays in `lookdev/paper_diorama.py`).

| Piece | Where it lives |
|---|---|
| City generator (buildings, props, crowd, rain, traffic, cameras) | `lookdev/city.py` |
| Characters (body, outfits, faces, walk cycle, umbrella/phone) | `lookdev/character_mh.py` (CC0 MakeHuman base in `lookdev/assets/makehuman`) |
| Single-street test scene | `lookdev/rain_street.py` |
| Finishing grade (bloom, split tone, vignette, grain) | `lookdev/grade.py` |

## 1. Look

| Element | Do | Don't |
|---|---|---|
| Characters | Realistic proportions, 3-tone cel shading, cool rim light, ink outline (inverted hull) | Photoreal skin, chibi proportions |
| World | Realistic materials: wet asphalt with puddles and ripples, grimy concrete, glass, metal; real-scale streets | Flat painted backdrops |
| Light | Night; neon signs, shopfront spill, cool street LEDs, warm windows, haze | Daylight flatness |
| Weather | Rain streaks, puddle ripples, steam from manholes | Dry, static streets |
| Grade | AgX Punchy, then `grade.py`: bloom, teal shadows, warm highlights, vignette, grain | Crushed blacks, oversaturated neon |

## 2. Neon Harbor (original city)

- Dense mid-rise blocks (12–42 m) along a main street, narrow alleys with lanterns, a crosswalk,
  utility poles with sagging wires, AC units, balconies, rooftop water tanks and billboards.
- A distant skyline with an original twisted tower and a hill with a broadcast tower.
- **All signage is invented and generic** (NOODLE BAR, KARAOKE, 24H MART, HOTEL...). No real
  businesses, brands, logos or landmarks, and no buildings copied from reference photos.
- Reference photos are mood references only (density, colour, layering), never traced.

## 3. Characters

- **Hero** (`character_mh.HERO`): charcoal long coat, oatmeal turtleneck, slicked-back hair with
  loose locks, dark dress shoes. Our own design; no glasses, no pink suit, nothing from an existing
  webtoon.
- **Extras**: random bodies (male, female, heavier build), heights, skin tones, hair (short, bob,
  buzz), coats or jackets or knitwear, trousers or skirts with tights, sneakers or leather shoes.
  Umbrellas for walkers in the rain, phones for people standing.
- Every person walks with a looping cycle (legs, arm swing, bob) and moves through the street.

## 4. Life in every shot

Something always moves: rain, ripples, steam, flickering or broken neon, traffic lights cycling,
cars passing with headlights, people walking past, camera dolly or crane. Never a frozen frame.

## 5. Camera

Real-lens language: 22–35 mm for streets, 50 mm+ for portraits, shallow depth of field on people,
low angles for the hero, slow dolly and crane moves. 9:16 at 1080×1920, 30 fps.

## 6. Story structure

Hook in the first sentence, setting in a line, escalation in two to four beats, a pivot, and an
ironic payoff on the last words. Narration is the user's own voice; music and SFX sit at 50 % of it.

## 7. Originality checklist (before every render)

- [ ] Story, characters and shot list are our own, not a remake of another creator's video.
- [ ] No real people, brands, logos, landmarks or copied buildings.
- [ ] Hero and extras are original designs (no existing webtoon or anime characters).
- [ ] Signage text is invented and generic.

## Rendering

```bash
/root/.venvs/bpy/bin/python lookdev/city.py hero 50     # stills: street | hero | alley | aerial
FRAMES=48 SAMPLES=10 /root/.venvs/bpy/bin/python lookdev/city.py clip 25
```

The Blender 5 Python module lives in `/root/.venvs/bpy` (install: `uv venv -p 3.13 /root/.venvs/bpy`
then `VIRTUAL_ENV=/root/.venvs/bpy uv pip install bpy`). It includes OpenImageDenoise. Freestyle
is off by default because it costs minutes per frame on the whole city (`FREESTYLE=1` enables it).
