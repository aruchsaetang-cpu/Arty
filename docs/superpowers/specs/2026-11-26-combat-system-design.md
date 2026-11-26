# Kuro Oni combat animation system (design, approved "Yes" 2026-11-26)

## Intent
Reusable, professional-quality combat animation for the Kuro Oni hero (the Aura Monster rig, emotionless, minimal wasted movement, hands-in-pockets style) and enemies. Built on shorts/kuro_oni/moves.py + lookdev/character_mh.py. Preserve all working features (scene 1 v4 pipeline, cast_kuro, city set).

## Goals
- Anatomical joint limits, hip-led chain (hips > spine > shoulder > arm), weight transfer, balance, momentum.
- IK + foot locking in fights (no sliding); plant/pivot/step logic.
- Action clips as independent editable data (JSON): start/end, easing, blend-in/out, hit events (frame, attacker, target, body part, force vector), camera track, physics settings.
- Blending between attack/dodge/block/recovery.
- Contact sync: attacker fist/foot reaches target body part at the hit event (measured error < 1 cm); defender reaction driven by force direction/momentum (keyed + damped physics, not ragdoll).
- Secondary motion: hair, coat/cloak (spring/verlet, CPU).
- Selective motion blur, hit-stop, impact frames, cinematic camera tracks (steady).
- Consistent proportions and face (no per-clip changes to rig).
- Preview each sequence alone (render by sequence id and frame range); Three.js real-time preview from Blender-exported GLB animation clips; CPU-only.
- Reference: real full-contact Kyokushin clips (local only), human anatomy.

## Non-goals / anti-goals
- No pure sine-wave procedural motion, no uncontrolled ragdoll, no GPU requirement, no change of character designs, no committing user reference clips.

## Approaches considered
1. Pure Blender keyframes in code (current moves.py extended): simplest, but no real-time preview, clips not editable as data.
2. Data-driven clips (JSON) solved in Python on the rig, exported to GLB for Three.js preview and rendered in Blender Cycles (CHOSEN): editable, previewable, reuses the rig and Blender render.
3. Three.js-only animation engine: fast preview but loses the cel/Cycles look and rig work.
Picked 2 (user approved the plan: build on moves.py/character_mh.py, Three.js preview, 5 s test with hero + 2 enemies first).

## Deliverables (phase 1)
- shorts/kuro_oni/combat/ package: clip schema + loader, solver (IK, foot lock, chain), blending, hit events/contact sync, reactions, secondary motion, camera tracks, CLI `render_seq.py <seq> [--frames a-b]`, GLB exporter, preview/ (Three.js viewer).
- 5 s test scene "combat_test": hero (hands in pockets) vs 2 enemies, 3 moves (slip + punch, turn + punch, low kick), verified by foot-slide report, contact error report, proportion/face consistency check, stills review. Full-episode rendering only after the test passes.

## Left to builder
Exact schema fields, spring constants, IK solver details, viewer UI.
