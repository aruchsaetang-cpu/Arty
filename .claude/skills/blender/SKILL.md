---
name: blender
description: Blender (bpy) workflows for this project's Aura Monster pipeline. Use for any Blender/bpy task here - building or posing characters, rigging, natural walks with planted feet (IK), stops and turns, coat/hair secondary motion, manhwa cel shading, rainy-city scenes, Cycles CPU rendering (Eevee is not available in this container), GLB export and loading in Three.js. Read before editing lookdev/*.py or shorts/aura/film*.py.
---

# Blender in this project

## 0. Before anything
- Ask the graph first: `graphify query "<question>"` (project rule). The key files: `lookdev/character_mh.py`
  (rig, walk, poses, cel materials), `lookdev/character_v1.py` (the hero's look), `lookdev/city.py` (city builders),
  `shorts/aura/film.py` + `film_camera.py` + `film_sets.py` (the film), `shorts/aura/cast.py` (every character's style),
  `lookdev/walk_stop.py` (walk -> stop -> head turn, foot-contact report).
- **Never run two full film scenes at once** (each ~9.6 GB; the box has 15 GB). A small standalone scene (one or two
  characters + a street, ~1-2 GB) can run beside the film render.
- **Never change shorts/aura/film*.py while `render_all.sh` is running** without stopping it first, and say which
  frame ranges must be re-rendered (delete those frames/masks; the render resumes and fills the gaps).
- Experiments go on a branch or a git worktree (`git worktree add -b <branch> ../Arty-<name> HEAD`), so the running
  render keeps reading the original files.

## 1. Runtime
| What | Command / fact |
|---|---|
| Blender used by the project | Python module `bpy` 5.3: `/root/.venvs/bpy/bin/python script.py` |
| System Blender | `/usr/bin/blender` 4.0.2 (not used by the pipeline; scripts target 5.3 APIs) |
| Render engine | **Cycles CPU only.** `BLENDER_EEVEE` fails here: no GPU, no `libEGL.so.1`, no `/dev/dri`. Use Eevee only on a machine with a GPU. |
| Hardware | 4 Xeon cores, 15 GB RAM, no GPU |
| Check | `/root/.venvs/bpy/bin/python -c "import bpy; print(bpy.app.version_string)"` |

CPU render settings that keep quality: `city.render_settings(scale, samples)` (adaptive sampling, OIDN denoise, few
bounces, persistent data). Film: 50% of 1080x1920 at 12 samples, then `shorts/aura/upscale.py` (Real-ESRGAN anime x4).
Previews: `SCALE=33 SAMPLES=10`. Stills from the film: `STILLS=315,335 python shorts/aura/film.py 50 315 335`.

## 2. Characters (never redesign)
- Build: `arm, objs = ch.build_v1(coll, loc, K.HERO_V1, pose_mode="walk", void_eyes=True)` for Aura Monster
  (black sclera, white iris: `void_eye_mat`), `ch.build(coll, loc, K.<STYLE>)` for everyone else. Styles live in
  `shorts/aura/cast.py`; NPC outfits in `lookdev/fashion.py`; only the narrator wears the ARTY hoodie prints.
- Poses: `ch.posed(arm, "stand"|"walk"|"pockets"|"umbrella"|"phone", head_yaw=deg)`; the hero keeps
  `ch.hands_in_pockets(arm)`.
- Bones animated: `ch.ANIM_BONES`; rotations are quaternions, keyed per bone.

## 3. Walking without sliding
- `lib, lift, step, speed = ch.walk_keys(arm, prop, cycle=34, stride=0.62)` returns a planted-foot cycle solved with
  two-bone leg IK for this rig's proportions (heel strike, roll to toe, swing with clearance, pelvis bob). The planted
  foot moves back at exactly `speed`, so **the root must advance by `speed` per second, or drive the cycle by
  distance**: `q = distance / (speed * n * step / 30) * n` and slerp `lib[floor(q)]`->`lib[floor(q)+1]`.
- Slowing down / stopping: `walk_stop.walk_to_stop(arm, start, heading, f0, dist)` (distance-driven phase, linear
  slow-down, stops with the left foot mid-stance and sets the passing right foot down beside it, no slide).
  Then `walk_stop.head_turn(arm, f, yaw)` (anticipation, overshoot, settle).
- Sideways dodges while walking (`film.walk_path(..., sway=)`): moving the root sideways drags planted feet. On the
  `claude/aura-motion-upgrade` branch, `plant_sway` keeps each foot on its landing spot and rolls the leg from the hip.
- **Always measure, never eyeball:** `walk_stop.foot_report(arm, f0, f1)` gives per-foot slide (mm/frame while
  planted) and ground height. Targets: < 1 mm/frame slide while planted, no sinking below the walk's ground height.
- Avoid `stand_at` right after a walk for a visible stop: it blends to a new pose over a few frames and slides the
  feet (measured 74-91 mm/frame, 11-18 mm sink).

## 4. Coat and hair motion
- Coats/skirts get `add_cloth_motion` (hem weights + three Displace modifiers: trail, sway, flutter) and
  `ch.cloth_walk(arm, f0, f1, cycle)` drives them with simple-expression drivers (no Python drivers: they are off in
  background mode). Follow-through after a stop: `walk_stop.coat_settle(arm, f_stop)` adds a damped swing.
- No cloth simulation: too slow on 4 CPU cores and unstable over 1000+ frames. Bone/driver-based motion only.
- Hair: `locks=True` adds separate lock meshes; they are skinned to the head (no secondary bones yet).

## 5. Manhwa look (keep it)
- Materials: `ch.cel(base, shade, rim=...)` three-band cel shading with a rim term; `ch.ink_mat()` + Solidify
  (flipped normals) for outlines; `CHAR_STYLE=real` switches to `real_mat` (do not use for the film).
- City: `city.py` builders (`building`, `street_side`, `alley`, `car`, `shop_room`, `rain`, `fog`, `world`);
  wet ground ripples run on a `rain_clock` value node (film.py keys it with the slow-motion clock).
- Grade/aura are post: `shorts/aura/compose.py` (white aura from the hero mask, cinematic grade).

## 6. Rainy-street test scene
`/root/.venvs/bpy/bin/python lookdev/walk_stop.py after` builds street + rain + fog + Aura Monster, walks him toward the
camera, stops, turns his head; prints `FEET` (contact report) and writes `lookdev/renders/walk_stop_after.json`.
`RENDER=1 SCALE=33 SAMPLES=10 ... after R0 R1` renders frames; `before` builds the film's current stop for comparison.

## 7. GLB export -> Three.js
- `GLB=out.glb /root/.venvs/bpy/bin/python lookdev/walk_stop.py after` exports the hero's armature + meshes with the
  walk/stop/turn action (`export_apply=True` bakes Subsurf/Solidify/Displace before skinning; `export_force_sampling`
  bakes the quaternion keys).
- Cel node trees do not survive glTF. In Three.js, rebuild the look per material name: `MeshToonMaterial` with a
  3-step `gradientMap` (NearestFilter) using the material's base colour, plus the inverted-hull outline (the exported
  `ink` solidify shell already carries it: render those meshes with a flat dark `MeshBasicMaterial`, `side: BackSide`).
- Play with `AnimationMixer`: `mixer.clipAction(gltf.animations[0]).play()`; update with a clock delta.
- glTF is +Y up; Blender is +Z up: the exporter converts with `export_yup=True`. Units stay metres.

## 8. Checklist after any animation change
1. `foot_report` numbers (before/after) in the commit message.
2. Render the same frames before and after; compare side by side (same camera).
3. Re-run `graphify update .`; commit; never push model IDs in messages.
