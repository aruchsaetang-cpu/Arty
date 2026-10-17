# Tesla Roadster "flying" demo: script (Hook → Context → But → Reveal)

Target: about 35 s at Zack D pace (~3 words/s). Send the AI voiceover reading exactly this text (also in lines.txt). Leave a short natural pause at each comma and full stop.

## Hook
This Tesla just drove up an upside-down ramp… and flew back down on its own.

## Context
On October 15th, at a SpaceX test site in Texas, Musk unveiled the new Roadster.
It shot up a curved ramp, stuck to it upside down, and launched into the air.
SpaceX thrusters flipped it upright, it hovered, then landed in a cloud of smoke.
Musk's verdict? Flying cars are real.

## But
But there was nobody inside.

## Reveal
It was remote-controlled from a safe distance, and Musk admitted success wasn't guaranteed.
The flying version isn't approved for public roads, or certified to fly.
So for now, it's a stunt, not a car you can fly to work.
At least… not yet.

---

## Shot plan (3D, Three.js)

| Line | Shot (clip) | Overlay graphic |
|------|-------------|-----------------|
| Hook | `a_hook`: low angle, car leaves the loop upside down | flash on frame 1, burst |
| "October 15th… Texas" | `b_site`: wide drone shot of the test site | stat: 15 / OCT |
| "shot up a curved ramp… upside down" | `c_loop`: side tracking shot around the loop | burst |
| "cold-gas thrusters flipped it" | `d_thrusters`: close-up, gas jets, flip | none |
| "hovered… cloud of smoke" | `e_land`: wide landing in smoke | none |
| "Flying cars are real" | `f_quote`: dark stage, quote card | none |
| **"But there was nobody inside."** | **`g_empty`: hard cut to top-down view of the empty seats** | flash + highlight on driver seat |
| "remote-controlled… safe distance" | `h_remote`: controller in foreground, car far away | none |
| "isn't approved… certification" | `i_stamp`: car on road, NOT APPROVED stamp | none |
| "not yet" | `j_end`: car lifts off into the sky, "?" | glow: "NOT YET" |

## Fact notes
- Oct 15, 2026, SpaceX test facility in Texas: inverted ramp, thrusters flipped the car, brief hover, landing in smoke, no driver, remote-controlled.
  Outlets disagree on the town (Waco vs McGregor), so the script says only "Texas".
- Musk quotes: "flying cars are real", "Success is not guaranteed".
- Flying version not approved for public road use; no aviation certification sought.
- The 0–60 in 0.81 s figure appeared in only one headline (others report 1.1 s), so it is left out.
