# Kuro Oni combat system (`shorts/kuro_oni/combat/`)

Data-driven fight animation for the Kuro Oni hero (Aura Monster rig, hands in pockets) and enemies. Clips are JSON,
solved in Python on the real rigs (`lookdev/character_mh.py`), rendered in Blender Cycles per sequence, and previewed
in Three.js from an exported GLB. Design: `docs/superpowers/specs/2026-11-26-combat-system-design.md`.
`shorts/kuro_oni/moves.py` is reused unchanged (its moves run on solver layers).

| file | job |
|---|---|
| `schema.py` | JSON loader + validator, hit-stop time map (story time <-> output frames) |
| `solver.py` | `CombatRig`: one key layer per move, cross-fade with easing, joint limits, foot lock (plant/pivot/step), leg reach, IK, FK, centre-of-mass balance |
| `moves_ext.py` | move registry (`MOVES`); new moves: `mawashi_geri_low`, `kick_recover`, `pocket_recover`, `turn_step`, `guard_recover`, `hook_r`, `lunge_punch`, `hurt_idle`, `uchi_uke` + wrappers of moves.py |
| `contact.py` | body-part surface points, contact retarget (IK end effector), physics-driven keyed reactions, decal hook (`bruise`) |
| `secondary.py` | verlet chains: coat hem, hair (Displace before Armature), cloak panels |
| `camera.py` | steady camera from tracks + cuts, level (roll 0), smoothed actor tracking |
| `checks.py` | Blender-side verification (foot slide, contact error, balance, chain order, slip clearance, fingerprint) |
| `consistency.py` | builds every clip alone + the sequence and asserts identical proportions / face |
| `build.py` | builds a sequence: cast, plain set, solve, bake, secondary, camera, hooks |
| `render_seq.py` | CLI: render one sequence / clip, resume, twos, mp4 |
| `export_glb.py` | GLB (characters once, one animation per clip) + manifest for the viewer |
| `preview/index.html` | Three.js viewer (r128 from cdnjs, vendored fallback) |
| `tests/` | `test_core.py` (pure units), `preview_test.js` (Playwright), `preview_sheet.js` (motion contact sheet) |

## Clip schema (`clips/<id>.json`)
All frame numbers are CLIP-LOCAL STORY frames (0 = first frame, at `fps`). Hit-stop adds held OUTPUT frames, so
`duration` (output frames) must equal `story_frames + sum(hits[].hitstop)` (validated).
```jsonc
{
 "id": "ct_slip_punch_a", "fps": 30, "story_frames": 40, "duration": 43,
 "actors": { "hero": {"style": "HERO", "role": "hero", "pockets": true, "cloak": false,
                      "start": {"x": 0, "y": 0, "facing": 90}},          // facing deg: 0 = -y, 90 = +x
             "A": {"style": "FIGHTER_7", "role": "enemy", "start": {...}} },
 "moves": [ {"actor": "hero", "move": "slip_turn", "start": 19, "end": 26, "easing": "snap",
             "blend_in": 2, "blend_out": 1, "params": {"pocket": true, "hold": 0.07}} ],
 "hits": [ {"id": "h1", "frame": 32, "attacker": "hero", "target": "A", "part": "cheek_L", "effector": "fist_R",
            "force": [30, 7, 4],            // N s, attacker frame [forward, left, up]
            "hitstop": 3, "decal": "bruise", "fall": false} ],
 "camera": {"cuts": [ {"frame": 0, "motion_blur": true, "keys": [
            {"frame": 0, "pos": [x,y,z], "look_mid": ["hero","A"], "look_off": [0,0,0], "lens": 30, "fstop": 5.6, "ease": "io"} ]} ]},
 "physics": {"reaction_strength": 2.4, "mass": 74, "damping": 0.3, "freq": 2.6, "friction": 5.0, "fall_threshold": 0.45,
             "head_gain": 0.7, "coat": {"stiffness": 60, "damping": 0.12, "gravity": 1, "max_offset": 0.08},
             "cloak": {...,"max_deg": 14}, "hair": {...}},
 "impact_frame": {"exposure": 0.18, "frames": 1}
}
```
- easing: `io` smooth, `in` accelerate, `out` decelerate, `snap` fast-out, `lin`.
- blend window of a move = `[start - blend_in, start + previous move's blend_out]`, eased cross-fade per channel.
- body parts: `cheek_L/R jaw nose solar_plexus liver ribs_L thigh_L/R calf_L/R`; effectors: `fist_L/R shin_L/R foot_L/R`.
- camera look: `look` [x,y,z], or `look_actor` (+`look_part`), or `look_mid` [actors]; roll is always 0.
- sequence (`sequences/<id>.json`): `{"id", "clips": [...], "render": {"scale", "samples", "twos"}}`. The first clip's
  `start` places the actors; later clips continue from the solved state (their `start` is used when rendered alone).

Validate: `/root/.venvs/bpy/bin/python shorts/kuro_oni/combat/schema.py [id]`.

## Add a clip
1. Copy a clip JSON, give it a new `id`, set `actors` (same styles as the rest of the sequence), `story_frames`.
2. Add moves per actor (an idle first is good practice; a base pose from `start` is always there).
3. Add hits, set `duration`, camera cuts. Validate, then `render_seq.py <id> --check-only`, then stills.
4. Put it in a sequence's `clips` list if it belongs to one.

## Add a move
Write `def m_name(r, t0, dur, ease, params, W)` in `moves_ext.py` and register it in `MOVES`; add its spec to
`schema.MOVE_SPECS` (kind, balance mode, params). Inside: read `r.ctx` (x, y, facing, yaw, twist, drop, footL/R...),
key channels with `r.key(t, ease, **channels)` (fists `("c", chest pt)`, `("h", hip-local pt)` or `("w", world pt)`;
feet `(x, y, yaw, lift, heel_pitch)`), update `r.ctx` with the end pose. Use `pivot_keys` for heel turns on the ball
and `step_foot` for steps. Attacks: get the target with `W.hit_target(hid)` and call `W.mark_effector_keys(r, hid,
channel, contact_time)` so contact sync can retarget them. Aiming at a person: `W.part(name, "nose", t)`.

## Hit events
`frame` = contact (story frame); the attack move must END on it (validated). The solver moves the effector keys until
the effector surface touches the part surface (< 0.5 mm in the solver, re-measured in Blender), adding up to 12 cm of
hip drive if the limb is at full reach. The defender reaction is generated from `force` + `physics`: head snap and
torso twist (damped springs from lever x force), knockback (friction), absorbed / 1-2 steps / controlled fall.
`hitstop` holds story time for N output frames. `decal: "bruise"` calls `contact.HOOKS["bruise"]` (add your own hook
in `HOOKS`: `fn(W, hit, contact_output_frame)`).

## Camera track
Cuts start at clip-local frames; keys inside a cut are eased; actor looks are smoothed (no jitter); no roll, no noise.
`motion_blur` per cut (only the fighters' meshes blur; off on contact and hit-stop frames). `impact_frame` lifts
exposure on the contact frame(s).

## Run the preview
```
python shorts/kuro_oni/combat/export_glb.py combat_test         # -> preview/combat_test.glb + combat_test.json
cd shorts/kuro_oni/combat/preview && python3 -m http.server 8000  # open http://localhost:8000/?seq=combat_test
node shorts/kuro_oni/combat/tests/preview_test.js                 # headless check + screenshot.png (960x540)
```
Clip dropdown, play/pause, speed, scrub; red sphere = hit contact, green ring = locked planted foot, timeline strip =
plants (green), cuts (white), hits (red). Secondary motion (Displace modifiers) is not in the GLB (skeleton only).

## Render one sequence
```
python shorts/kuro_oni/combat/render_seq.py combat_test --scale 50 --samples 12 --twos      # frames + out/combat_test.mp4
python shorts/kuro_oni/combat/render_seq.py ct_low_kick_a --frames 1-40 --stills 25          # one clip / a range / stills
python shorts/kuro_oni/combat/render_seq.py combat_test --check-only                        # verification only
python shorts/kuro_oni/combat/render_seq.py combat_test --mp4-only                          # re-assemble
python shorts/kuro_oni/combat/consistency.py combat_test                                    # proportions/face across clips
```
Frames: `shorts/kuro_oni/frames_seq/<id>/f####.png` (git-ignored), resumable. Never run two renders at once.
