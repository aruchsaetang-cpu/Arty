---
name: arty
description: Lessons and setup for animated-short projects built in Blender (bpy) + Three.js + ffmpeg on a CPU-only cloud box, learned on the Aura Monster film. Use at the START of any new animation, film, render, camera, sound-mix or Blender/Three.js project, and whenever a render, preview, or user-supplied sound/reference is involved. Read before planning so the same mistakes are not repeated.
---

# Aura pipeline: setup, mistakes to avoid, token rules

## 1. Setup that exists (do not reinstall)
- Blender = Python module `bpy` 5.3: `/root/.venvs/bpy/bin/python`. Cycles CPU only (no GPU, no libEGL, Eevee impossible). 4 cores, 15 GB RAM.
- Project skills in `.claude/skills/`: `blender`, `openverse-sfx`, `graphify`, HyperFrames set, `threejs-*` (7, from cesartevisual/threejs-skills, MIT, text only), this one.
- Tools: ffmpeg, Playwright+Chromium (software GL ok), Real-ESRGAN upscaler (`upscale.py`), Whisper timings, graphify graph (`graphify query` before grep).
- Network: proxy blocks some hosts (cdn.jsdelivr.net, Freesound CDN). `npm pack three@<ver>` works for local Three.js tests. Never spoof user agents.
- Model routing: `CLAUDE.md`. Subagent `model`: haiku = search/logs, sonnet = default code, opus = hard physics / pipeline. Main model is the user's `/model` choice.

## 2. Mistakes made, and the rule that prevents each
1. **Background jobs die.** Tool background tasks stop at 2 h; detached `nohup` jobs also died (container restart). Rule: keep frames in git-safe form early, check `pgrep` + frame count at every wake, restart the resumable render. Never promise "runs by itself".
2. **Render before approval = wasted days.** Many changes (car lane, eye direction, umbrellas, camera) needed re-renders of 500+ frames. Rule: render 3-4 test stills of EVERY shot type first, show them, only then render. Fix whole classes of bug (eyes, collisions, props) before the long render.
3. **Frames not backed up.** Frames/masks are git-ignored and live only on the box; a restart can lose them. Rule: back up or push chunks (<100 MB) early on a separate branch; push the final video from a script.
4. **Wrong timing source.** Whisper word times were 0.5 s off ("years"). Rule: measure the real onset in the audio waveform before syncing sound to a word.
5. **head_yaw turns the head but not the eyes** (irises point away, eyes look white). Rule: turn the body (`heading`), keep `head_yaw=0` for eye-visible characters; look at close-ups.
6. **Parked-object clipping.** Moving car lane overlapped parked cars (bodies reach +-2.3 m, lane was +-2.2). Rule: check lane width vs object extents numerically before placing anything that moves.
7. **Consistency sweeps.** "Everyone has an umbrella" had to be applied to crowd, standers and named NPCs. Rule: when the user states a global rule, grep every place characters are created.
8. **Edits under a running render.** Changing `film.py` while a render runs, or two full scenes at once (9.6 GB each) = OOM or mixed frames. Rule: stop render, edit, delete only affected frames, restart. Use `git worktree` for experiments.
9. **Re-render everything for a small change.** Rule: post effects (aura, afterimages, grade, sound) live in `compose.py` / `audio.py` and cost no re-render; put changes there when possible. Delete only affected frame ranges.
10. **Misreading references.** Asked-for effect came from a screen-recorded GIF/video; look at 1-2 contact sheets of it before building. Ask once if the target is ambiguous ("delay 0.2": extra or total?), state the assumption.
11. **Over-reporting.** Do not claim done without a measurement (foot-slide mm, jitter mm, frame counts, overlap check). Say what was NOT tested.
12. **File type limits.** Artifacts do not serve `.glb`; repack as `.gltf.json` with embedded buffer and rebuild a GLB in the page.
13. **Credits/licences.** Record every sound source in `audio/sfx/CREDITS.md`; flag unknown licences to the user.

## 3. New-project checklist
1. Read `HANDOFF.md`-style notes + `graphify query`. Do not read big files whole.
2. Write the shot list + frame budget; estimate render hours (full-res ~3 min/frame, 50% ~1 min/frame).
3. Build smallest test scene, measure, then scale up. Keep a before/after number for each fix.
4. Stills for review -> approval -> render in resumable ranges (`render_all.sh`) -> post (`compose.py`) -> finish (`finish.sh`).
5. Commit + push each step (stop hook needs a clean tree); keep `HANDOFF.md` current.

## 4. Token-saving rules (the user asked for this)
- Caveman replies: short words, 1-3 lines. No recaps, no option lists, no repeated status.
- Search the graph, read only needed lines; measure with numbers instead of viewing many images; one contact sheet per check.
- One preview per finished thing. Batch tool calls. Do not re-explain decisions already made.
- Render restarts: run command, 1-2 line report with frames done / total.
