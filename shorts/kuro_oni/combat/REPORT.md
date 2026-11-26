# combat_test report (2026-11-26)
Output: shorts/kuro_oni/out/combat_test.mp4, 540x960, 150 frames, 5.0 s, 30 fps, silent, no manhwa effects.

Scene: HERO (hands in pockets, face unchanged) vs A (FIGHTER_7) and B (FIGHTER_4). Clips: ct_slip_punch_a (slip, gyaku-zuki to A cheek), ct_turn_punch_b (turn, slip, punch to B solar plexus), ct_low_kick_a (right gedan mawashi to A thigh, A falls).

| Check | Result | Target |
|---|---|---|
| Foot slide, worst planted foot | hero 0.41 cm, A 0.18, B 0.26 | < 1 cm |
| Contact error | 0.046 / 0.044 / 0.041 cm | < 1 cm |
| Balance, static frames | worst 0.03 cm | < 2 cm |
| Kinetic chain | hips, then shoulder, then fist/shin, correct order on all hits | in order |
| Consistency, 4 builds | bone lengths 0.0 mm, face vertices 0.001 mm | equal |
| Camera | 3 cuts, roll 0, pitch <= 7.9 deg, no shake | steady |
| Render | 71 frames, 669 s (9.3 s/frame), peak RAM 2.05 GB | - |

Tests: unit 6/6; Playwright preview 0 console errors (cdnjs blocked by proxy, vendored copy used).

Still looks fake: (1) wide-kneed squat in the slip; (2) low kick reads as knee lift from the side, coat hides hip turn; (3) A's fall flat, slides ~1 m; (4) coat hem swings as one rigid sheet; (5) hair rigid, cloak rigid boxes; (6) head snap maybe too strong (try head_gain 0.5); (7) bruise decal too small at 540 px; (8) grey set hard horizon; (9) B's punch passes hero head by 3.6 cm; (10) enemy idles stiff.

Known bug: moves.Rig.solve heel-lift sign is wrong (ball of foot floats 5-7 cm in scene1_v4 pivots). combat solver uses the corrected sign.

Left to do: items 1-5, remaining moves (mae_geri, hiza_geri, hook, irimi-nage, blocks), secondary motion in GLB, city set, upscale.
