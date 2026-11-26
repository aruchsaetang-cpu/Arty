# KURO ONI Ep 1: the real version (30 s): plan

The prototype (simple boxes, dummies, flat colours) only tested the story. The real version is built like Aura Monster.

## Look
- Manhwa cel style of the Aura Monster film: three-band cel shading, ink outlines, the same Blender (bpy 5.3, Cycles CPU) pipeline, 1080x1920 final (render at 50%, then AI upscale).
- Sets and characters all in that style (the prototype had plain materials).
- Animated "on twos and threes" (12 drawings per second) in the fights for the anime feel; smooth ones for the camera moves; effect frames (ink silhouettes, comic grid, speed lines, impact words) added in post.

## Phases
1. **Yamazaki house set (agent, sonnet):** the hall, the gate and courtyard, the dojo with a veranda, the night bedroom, the lantern-lit stone stairway with the red torii, the black-tiled main hall (from the user's two house images). New file lookdev/yamazaki.py.
2. **Cast (me):** lean boy, teen and adult hero (with the father's black cloak), the mother in a dark kimono with two white crests and a bun, the father (long hair, black haori, forearm stripes), the master (white topknot and beard, checkered kimono), clan of 30 (about 8 unique rigs reused with variations), about 12 fighter rigs and a cheap crowd, the vassal elder (tattoos, glasses, sword).
3. **Choreography (agent, opus):** the war barrage (slips, wrist throws, shin checks, straight punch), the slap, the master's throw, the kata, the stab and the slump, with planted feet. Impact frames for every big hit.
4. **Shots and camera (me):** the 30 s shot list from the approved voice script; side-on, over-the-shoulder, low angles, tilts, shake, the first-person ending.
5. **Render and finish:** render at 50% (on twos in fights), upscale, grade, the manga effects, a sound track (the user's impact references plus synthesised sound), subtitles for the voice lines (no voice actor yet).
6. **Previews:** the first half (0-15 s) as soon as its frames are done, then the second half.

## Honest time estimate (estimates, not measurements)
- Build: phases 1-4, about a working day of my time (parallel agents help).
- Render: about 100 s per frame at 50%; the first half on twos is about 225 frames, so about 6 hours; the second half the same.
- First half preview: about 1 to 1.5 days from now. The full film: about 2 to 3 days.

## Open points (my assumptions, tell me if wrong)
- Final size 1080x1920, 30 fps, 30 s.
- No voice actor: the narrator and character lines show as subtitles for now. Send a recording (or tell me to use a text-to-speech voice) when you want a voice.
