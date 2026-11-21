# Aura Monster: handoff (project memory and work done)

Written so another assistant (or person) can continue without the original chat. Read sections 1, 2, 7 and 8 first.

## 1. What this project is
"Aura Monster": a **9:16 vertical animated short, 38.96 s (1169 frames at 30 fps), 1080x1920**, in a Korean-manhwa cel style, set in the rainy
night city "Sol". Everything is built in Blender (bpy 5.3 Python module) and rendered with **Cycles on CPU** (no GPU, no Eevee). The user
records the voice themselves (already provided and cut). **No TTS. No Seedance/Higgsfield spending.**

Story beats (shots, with frame ranges, from `shorts/aura/beats.json`): hook_wide 1-104 | hook_feet 105-159 | name_close 160-218 ("Aura Monster"
introduced; aura starts here) | name_med 219-300 | shop 301-345 | cop 346-392 | kids 393-443 | follow 444-515 | alley_pov 516-543 | reveal_low 544-619 |
reveal_close 620-690 (slow-motion rain-dodging reveal, slow0=528, slow1=690) | turn 691-765 | teach 766-803 | train_roof 804-865 | train_umb 866-929 |
train_mont 930-997 | close 998-1043 | payoff_two 1044-1086 | payoff_wide 1087-1169.

Repo: the `Arty` repo, working branch **`claude/install-agent-tools-kwf2l7`** (push only there, **no pull request**). Project rules are in
`CLAUDE.md` (graphify knowledge graph: run `graphify query "<q>"` before grepping; run `graphify update .` after code changes).

## 2. Current state (most important)
- **Render: 684 of 1169 frames done, 485 missing (first missing 685, last 1169).** The render is `bash shorts/aura/render_all.sh`, resumable
  (finished frames are skipped; zero-size frames are deleted first). **It dies at the 2-hour background limit and must be restarted each time**
  (in Claude Code: run it with `run_in_background`, timeout 7200000; the user authorised restarting it each time).
  Before restarting, delete a half-written last frame: open the newest PNG with Pillow; if it fails, remove it.
- Speed: full-resolution frames (shots hook_wide and name_close) ~2.5-3 min each; everything else (50% scale) ~1 min each. Remaining ~485 frames is
  roughly 8-9 hours. Never run two full film scenes at once (each needs ~9.6 GB RAM; the box has 15 GB). A small standalone test scene is fine.
- Frames 1-684 are rendered with ALL the current changes. Frames 685-1169 are still to render and will pick up the new camera automatically.
- Everything is committed and pushed (last commit: "Dodge afterimages like the user's reference"). The stop hook requires a clean, pushed tree.

## 3. Finish procedure (after all 1169 frames exist)
```
cd shorts/aura && rm -rf graded graded_hd && bash finish.sh
```
`finish.sh` does: `audio.py` (builds the sound stems) -> `VOICE=1 python3 mix.py` (mix + loudness) -> `compose.py` (aura, afterimages, grade, per frame, ->
`graded/`) -> `subs.py` -> `upscale.py graded graded_hd` (Real-ESRGAN anime x4 then Lanczos to 1080x1920 plus a small detail re-add; the full-resolution
frames only get a resize) -> ffmpeg mux with the HyperFrames caption overlay (`caps/frame_NNNNNN.png`) and `audio/mix.wav` -> `out/aura_monster.mp4`, then
QA (duration, black/freeze detect, `out/qa_sheet.jpg`). Check the last frames and the sound at the end, then send `out/aura_monster.mp4` to the user.
(For a quick preview without the upscale: `python3 compose.py A B`, then ffmpeg `graded/f%04d.png` + `caps/frame_%06d.png` + `audio/mix.wav`.)

## 4. Everything that was built/changed (so it is not redone)
**Characters** (`lookdev/character_mh.py`, `character_v1.py`, `shorts/aura/cast.py`, `lookdev/fashion.py`): the hero (black sclera + white iris "void eyes",
long dark coat, emotionless face) is never to be redesigned. The narrator wears the black ARTY CLIPS hoodie (A badge on the chest, ARTY CLIPS on the back,
`shorts/aura/assets/brand/`); **only the narrator wears the hoodie**; all other NPCs have manhwa street-fashion outfits (`fashion.py`), clear faces.
**City** (`lookdev/city.py`): see-through shop windows with 16 customer sprites (`lookdev/customers.py`), many car styles (sedan, hatch, crossover, SUV, offroad,
GT, supercar), crown-splash rain and multi-ring puddle ripples, one high-detail convenience-store interior used only in the shop shot
(`shorts/aura/shop_detail.py`, hooked in `film_sets.py`).
**Hero eye extreme close-up**, detailed iris (`void_eye_mat`). The name_close shot now ends on the whole face (not the extreme eye close-up).
**Meridian GT-8** (user's own Three.js car, `car3d/meridian.html`): rebuilt in Blender as `lookdev/meridian.py`, driven in `film.py` (red; passes in the opening
wide shot and drives away in the last wide shot; hidden elsewhere).
**Opening shot:** longer lens (36-38 mm) and full-resolution render so the hero reads clearly (`film_camera.py`, `render_all.sh`).
**Narrator in the reveal:** `film.py` stages the narrator behind the hero under his umbrella for reveal_low/reveal_close (was missing).
**Aura:** none before the introduction; 0.6 from name_close on, 1.25 peak in the reveal (`film.py` writes `aura.json`; white for the hero, yellow for the
narrator after the fold). Composited per frame in `compose.py` from masks.
**Dodge afterimages** (`compose.py trail()`): spaced blue-white translucent copies 3/6/9/13 frames back, weighted by movement, behind him, reset at cuts.
**Cinematic camera upgrade:** `cine_camera.py` (minimum-jerk, zero-phase smoothing keeping first/last values and slopes, low-frequency handheld,
orbits, QA), `film_camera.py` uses it (`CAM_SMOOTH=0` restores the old camera), `film.py CAMDUMP=path` dumps the per-frame camera path, `cam_qa.py A.json B.json`
compares. Frame 1 and every shot up to the kids scene are identical to the original. Follow/alley_pov/reveal/turn/teach/train_*/close/payoff were rewritten
(steady push-ins, 18 and 12 degree orbits, settling punch-ins). Measured: follow jitter 15 -> 2.4 mm, alley stop jerk 309 -> 9. Old frames of 444-690 are
in `shorts/aura/old_cam_frames/` (git-ignored) for before/after videos. Reference style: the user's fast "In this world..." Shorts (always moving camera).
**Blender skill:** `.claude/skills/blender/SKILL.md` (project Blender workflows). `lookdev/walk_stop.py`: distance-driven walk -> slow-down -> stop with the
foot set down (measured foot slide 74-91 mm/frame -> under 1 mm) + head turn + GLB export. `car3d/aura_walk.html` (Three.js player of the exported rig).
**Not merged:** branch `claude/aura-motion-upgrade` (a git worktree at `../Arty-upgrade`) has `plant_sway` in `film.py` that removes foot sliding while
he dodges (40-96 -> under 1 mm/frame). It was paused because the swinging leg kicked out through the coat; the film still uses the original walk.
**Audio** (`shorts/aura/audio.py`, `mix.py`): stems = music, rain (real Openverse rain layered), sfx, steps, whoosh, cine, clicks, riser; sidechain ducking under
the voice. The user's own sounds (all in `audio/sfx/`, see CREDITS.md): `click_user.wav` = **the only click** (12 scene changes; 6 keep a whoosh); `riser_user.wav` =
opening riser, starts at 0 s and ends at the voiced start of "years" + 0.3 s delay (measured in the voice track = 3.12 s; Whisper's time for "years" is 0.5 s
early); `dodge_user.wav` = dodge swoosh (first dodge 17.77 s and the two dodge-scene cuts, on the loud never-ducked stem). Footsteps only while the narrator
follows him (14.8-18.1 s). The user's footsteps are `audio/footsteps/step_N.wav`.
**Credits needed in the video description:** "Thunder" by Bidgee, CC BY 3.0, via Wikimedia Commons. (Rain: Karlunun, CC0.) The riser and dodge sounds came from
the user's screen recordings of third-party posts whose licences are unstated; the user was told to check before monetising.
**Captions:** Whisper-timed word-pop captions (`words.py`, `captions.py`, HyperFrames `caps/`). **Voice:** `cut_vo.py` (silence-trimmed, 1.2x tempo), `cues2.py`
builds `audio/voice_fast.wav`, `beats.json`, `slots.json`.
**Other pieces made this session:** `car3d/meridian.html` (3D car viewer, blueprint mode, published as an Artifact), `car3d/aura_walk.html`
(published Artifact), `lookdev/walk_stop.py`, `scripts/openverse.py` + `.claude/skills/openverse-sfx/`.

## 5. Open items / decisions waiting
1. Finish the render and run the finish procedure; send the film to the user. Preview clips already sent: first half, camera before/after chart,
   follow and reveal comparison videos, afterimage clip.
2. Optional: the user may want afterimages stronger / darker, or the riser end moved ("delay" is one number: `RISER_DELAY` in `audio.py`, now 0.30).
3. Not started: the user's "Emotionless Man" character blueprint (a request to build a new fully rigged manhwa character in Blender; only the image was read).
   Not started: upgrading the city with traffic/pedestrians. Two options were offered and unanswered: (a) upgrade the film's city (needs the film to be
   rendered again, ~20 h), or (b) a live Three.js city exported from Blender. The unmerged foot-sliding fix (section 4) is also open.
4. Frame-rate/quality choices already made: 30 fps (not 60), no motion blur, no frame interpolation.

## 6. Environment facts and gotchas
- Python/Blender: `/root/.venvs/bpy/bin/python` (bpy 5.3). `/usr/bin/blender` is 4.0.2 (unused). 4 cores, 15 GB RAM, no GPU, no libEGL (Eevee cannot run).
- Network goes through a proxy: some hosts return 403 (e.g. cdn.jsdelivr.net, Freesound CDN). npm and Wikimedia work. Do not spoof user agents.
- `film.py` rewrites `aura.json` and `steps.json` on every start (they show up as modified in git: commit them).
- Artifacts serve only certain file types (no .glb); the GLB was repacked as `.gltf.json` and rebuilt in the page.
- Playwright + Chromium are installed (software GL works for Three.js tests, slow). Matplotlib was pip-installed.
- Blender/film scripts: `STILLS=f1,f2 python shorts/aura/film.py 50 A B` renders single full-resolution test stills to `shorts/aura/stills/` (git-ignored).
- Commit message trailer used all session: `Co-Authored-By: ...` and `Claude-Session: ...` lines (follow whatever attribution instruction is current). No model IDs in
  code comments or PRs. Do not create a PR unless asked.
- The user's email and personal details are private; do not put them in outside requests.

## 7. The user's standing preferences (how they like to work)
- Short, plain replies; tells you what they want in one line, often with a screen recording as the reference. Replies in English with some Thai ("ชัด" = sharp/clear).
- Wants previews sent (as files) when something is done, and wants to be told exactly what is done vs not.
- "Continue yourself when it stops, I allow you": restart the render at every 2-hour stop without asking.
- Keep what already works; change only what they ask. They asked: no aura in the first scene; the opening camera and first frame must not change; only their
  character wears the hoodie; click sound only their click; riser loud from 0 s.
- They sleep during long renders: no need to wait for their check on scene 1.

## 8. Quick file map
`shorts/aura/` : `film.py` (scene + animation + render), `film_camera.py` (shots), `cine_camera.py` (camera tools), `film_sets.py`, `cast.py`, `beats.json`, `render_all.sh`,
`compose.py`, `audio.py`, `mix.py`, `finish.sh`, `upscale.py`, `cam_qa.py`, `frames/` (renders), `masks/`, `graded/`, `graded_hd/`, `out/` (previews and the film), `audio/`.
`lookdev/` : `character_mh.py`, `character_v1.py`, `city.py`, `fashion.py`, `customers.py`, `meridian.py`, `walk_stop.py`. `car3d/` : the Three.js pages.
`.claude/skills/` : `blender`, `openverse-sfx`, `graphify`, HyperFrames skills. `graphify-out/` : the code knowledge graph.

## 9. Reply style and saving tokens (read this too)
**Talk caveman.** Short, blunt sentences, small words, no filler, no long recaps. Example: "Render stopped. 700 of 1169 done. Restarted. 8 hours left."
Keep it plain enough for a non-native English reader. Still say exactly what is done, what is not done, and what the user must decide. (In Claude Code this is
the `caveman` skill; in other assistants just follow this rule.)

**Spend as few tokens as possible:**
- Read this file once, then work from it. Do not re-read big files (`film.py`, `character_mh.py`, `city.py` are 1000-2000 lines). Search first, read only the lines you need.
- Use the code graph: `graphify query "<question>"` before grepping (project rule). Run `graphify update .` after code changes.
- Do not look at images or contact sheets unless a visual check is really needed; measure with numbers instead (`cam_qa.py`, the foot-contact report in `walk_stop.py`, frame counts).
- Render restarts are mechanical: run the command, do not re-explain. A restart reply is one or two lines with the frame count (done / 1169).
- Do not ask questions the user already answered (section 7). Only ask when a choice changes the result.
- Do not send many previews. Send one file when something finished, with one line of caption.
- Do not rebuild or "improve" things that already work. Change only what the user asked.

## 10. Every instruction the user gave (oldest first). "REPLACED" = a later instruction overrides it. Follow the latest.
**Sound and voice**
1. Two voice WAVs: cut the quiet parts, speed to 1.2x. (done: `cut_vo.py`)
2. Install Openverse for sound effects and use it from HyperFrames. (done: `.claude/skills/openverse-sfx`)
3. Use HyperFrames to make the animation smooth and sharp (ชัด). (done: upscale + HyperFrames captions)
4. A whoosh on every scene change. (now: whoosh on 6 cuts, user's click on 12; see 14-17)
5. A transition sound at Aura Monster's first dodge; click and camera shutter on scene changes, swapping with the whoosh in no fixed order. (REPLACED by 14-17: no shutter, no built-in click)
6. Cinematic anime-movie sound effects. (done: `cine` stem in `audio.py`)
**Look and characters**
7. Put the user's channel logo on THEIR character's hoodie: black hoodie, white print like the reference (A badge on chest, ARTY CLIPS on back). ONLY their character wears it; other NPCs do not wear hoodies.
8. NPCs (except Aura Monster and the police) use the manhwa street-fashion style from the user's references (`fashion.py`); make faces clearer (ชัด).
9. All shop windows see-through with a customer inside, each customer a different style. Render cars like real ones (SUV reference photo); then many car styles (sedan, hatch, crossover, SUV, off-roader), then sports cars and supercars from their photos.
10. NPC clothes follow the user's fashion reference images.
11. Rain drops must look like the user's two screen recordings: crown splashes with droplets on the road, multi-ring ripples on puddles.
12. One scene: extreme close-up of the hero's eye (black sclera, white eyeball), as detailed as possible. (later: the name_close shot ends on the whole face, see 20)
13. High-detail store interior ONLY in the shot where the inside clearly shows (the shop shot).
**Scene and sound changes (later in the project)**
14. "Use this click sound instead, it is louder, I want it to grab attention on scene change." (user's own click in `audio/sfx/click_user.wav`, loud, never ducked)
15. "Delete all Openverse click sound and use my click instead." (done: shutter and synthesised click removed; there were no Openverse clicks)
16. "Use this [riser] in the hook, and the step sound only when I follow him." (done)
17. "Use this sound when he dodges." (dodge swoosh `dodge_user.wav`); then "when he dodges use cinematic instead of click" (the dodge cuts use the swoosh, not the click).
18. Riser: "use at the opening of the clip", "make it loud", "start at 0 sec, not wait until the hook ends", "when I said 'year' it needs to end exactly at the same time and be louder", then "delay a bit", then "delay 0.2 sec". (now ends at 3.12 s; one number `RISER_DELAY` = 0.30 in `audio.py`)
19. "In this scene [the reveal] my character is supposed to be on the back, isn't it, because I follow him." (done: narrator staged behind the hero)
20. "I want the first scene, his character ชัด" (done: longer lens + full-resolution render). Then: "first scene no need to add aura, but when you start to introduce the character use the same aura. And this scene zoom too much, show only a close-up of his face." (done)
21. "Use the Meridian GT-8 car in the film." (done: opening and final wide shots)
22. "The dodge scene: add afterimage to make the scene cooler" (reference: Ultra Instinct dodge GIF). (done in `compose.py`)
**Camera**
23. Ultra-smooth cinematic camera master prompt: first frame and opening shot must stay identical; spline/min-jerk motion, no jitter or snapping, no roll; push-ins, orbits, low-angle, extreme close-ups, parallax, shake only on impacts; keep 70% of the existing look and add 30% camera improvement; 30 fps stable is better than inconsistent 60; make a before/after comparison; reusable controller. (done: `cine_camera.py`)
24. "Red" + three screen recordings: the camera language reference (fast "In this world..." Shorts). (done: moving camera in teach, rooftop, umbrella alley, montage, close, payoff)
**Process and delivery**
25. "Send me progress every 2 hours" then "Every 2 hours, no need to send me progress now." (no progress cards)
26. "When the first scene finishes rendering, send it to me to check first" then "Scene 1 is done, no need to check, I will sleep." (do not wait for the user)
27. "Continue yourself when it stops, I allow you." (restart the render at each 2-hour stop)
28. "Can you send me what is done." (previews sent; do this again when asked)
29. "After done half of the video show me." (done)
30. "How much does it take to do the whole clip?" (answer was ~16-18 h at that time; about 8-9 h of render left now)
**Large master prompts (the user pasted them; each is a project of its own; status in section 5)**
31. "PRESERVE WHAT ALREADY WORKS": upgrade the animation surgically on a separate branch, do not change what is good, keep identity and opening, compare before/after, revert changes that make it worse, upgrade only the weakest five-second movement. (partly done: foot-slide fix on branch `claude/aura-motion-upgrade`, NOT merged)
32. "BUILD MY MANHWA CHARACTER" (the Emotionless Man, blueprint image): a fully rigged 3D character, one permanent expression, 10 stages, 3 lighting setups, renders. (NOT started)
33. "PROFESSIONAL 3D CAR BLUEPRINT" (Three.js, reference blueprints): six-view dimensioned blueprint and animated car. (done: `car3d/meridian.html`)
34. "UPGRADE MY EXISTING CITY WITHOUT REDESIGNING IT": traffic, pedestrians, traffic lights, doors, weather, iPad performance; keep the city identical; back up first; test each part. (NOT started; two options waiting for the user: upgrade the film's city, ~20 h re-render, or a live Three.js city)
35. "Install or create a reusable Blender skill" and "Senior Blender Technical Artist": inspect, back up, Blender + bpy check, rig/walk/IK/coat/hair, manhwa cel look, Eevee only if possible, GLB + Three.js, a rainy-street test scene, before/after. (done: `.claude/skills/blender/SKILL.md`, `walk_stop.py`, GLB + `aura_walk.html`; Eevee impossible here)
**Standing rules from the user**
36. The user records the voice. No TTS. No Seedance/Higgsfield spending. Only the user's character wears the hoodie. Keep what already works.
37. Give the hand-off to ChatGPT (this file); the user has ChatGPT Pro; add caveman style and token saving (section 9); add all instructions (this section).

## 11. Unattended render (added last)
`shorts/aura/run_to_end.sh` renders all missing frames (re-running `render_all.sh` up to 8 times), then runs the finish pass, and writes `shorts/aura/run_to_end.done`
when the film is ready (`shorts/aura/out/aura_monster.mp4`). Started detached with:
`setsid nohup bash shorts/aura/run_to_end.sh > shorts/aura/run_to_end.log 2>&1 < /dev/null &`
Check it: `cat shorts/aura/run_to_end.log` and `pgrep -af "run_to_end|film.py"`. If it is not running and `run_to_end.done` does not exist, start it again with the command above.
Each `render_all.sh` pass loads the scene once per shot range (a few minutes each) even when those frames exist; that overhead is normal.
