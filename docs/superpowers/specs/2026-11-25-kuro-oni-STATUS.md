# KURO ONI Ep 1: working status (read this first after a context reset)

User approved the 30 s script (2026-11-25-kuro-oni-ep1-30s-voice-script.md) and chose the FULL REAL VERSION (wait 2-3 days).
USER UPDATE: send each SCENE as soon as it is done (no need to wait for the half). First scene = the HOOK (0-3 s, burning street, one punch, 'He defeated an army alone...'); then the next scenes in order. Do not send the prototype again.

## Source of truth
- Script: 2026-11-25-kuro-oni-ep1-30s-voice-script.md (voice lines as subtitles) and ...-30s-script.md (scene actions).
- Design/looks: 2026-11-25-kuro-oni-design.md (read "LATEST" sections first; fight look refs; mother/father/master looks; Yamazaki house).
- Plan: 2026-11-25-kuro-oni-real-version-plan.md.
- Prototype code (throwaway): shorts/kuro_oni/film.py, film30.py, compose30.py, proto.py (compose30 effects are reusable: speed lines, comic grid, ink silhouette, fear tint, impact words, vignette).

## Phases and owners
1. Yamazaki house set: sonnet agent -> lookdev/yamazaki.py (+ yamazaki_test.py). STATUS: DONE (commit 3c7944a). hall/gate_courtyard/dojo/bedroom/stairway(O,...) + set_world(); stills in /tmp/yamazaki/ (may be gone). Limits: own light cel shader ignores scene lights; bedroom dark; rough tuning.
2. Cast: sonnet agent -> shorts/kuro_oni/cast_kuro.py (+ cast_test.py). STATUS: DONE (commit 519687e). build_cast(P, which, locs, scales, hero_cloak); make_silhouette_crowd(P,n). Limits: full cast over 9 GB, build per shot only; BOY looks teen-height (scale him); father cloak shoulder pieces stick out like horns (kimono.py); crests/beard faint; no forearm stripes. lookdev/kimono.py (obi, crests, bun, topknot, beard, cloak, katana, robe) is done (lead).
3. Choreography: opus agent (to start after 1 and 2): war barrage, slap, throw, kata, stab, slump; planted feet; impact frames.
4. Shots/camera: lead; 30 s shot list; real sets; side-on/over-shoulder/low angles; first-person ending.
5. Render: 50% scale, on twos (and impact frames), 12 samples, then shorts/aura/upscale.py; resumable (delete half-written last frame; restart each 2 h; never two renders at once; one render only, background task, timeout 7200000).
6. Compose: reuse compose30.py effects; sound; subtitles for the voice lines.
7. Send first half preview, then the full film.

## Open
- Voice: no voice actor; ask the user later (text-to-speech or a recording).
- Time estimate told to user: first half about 1-1.5 days, full film 2-3 days.

## Scene 1 (hook)
Agent building shorts/kuro_oni/scene1.py + scene1_compose.py -> out/scene1.mp4 (started after the cast finished). When it reports, LOOK at the frames/stills and send scene1.mp4 to the user (they asked for each scene as it is done).
