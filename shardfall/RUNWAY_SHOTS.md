# SHARDFALL: image-to-video motion prompts (Runway)

Each picture in `src/v2` (n01–n14) becomes one clip: 16:9, 1280×720 or larger. The film then cuts these clips to the existing 180 s timeline and score (`film2.py` shot names in brackets) and keeps the impact frames, speed lines, subtitles and title/end cards.

Shared suffix for every prompt:

> Japanese TV anime motion, fluid 2D character animation, consistent character design and line art, no morphing, no new characters, camera move as described.

| Picture | Used in | Length | Motion prompt |
|---|---|---|---|
| n10 girl over dusk city | city pan | 10 s | Slow pan right across the dusk city; her long hair and green ribbons stream and ripple in the wind; she slowly lowers her eyes; window lights flicker on; birds cross the sky. |
| n02 girl at railing, tower | city detail, the white point | 5 s | Slow push toward the tower; her hair and sash flow in the wind; sun rays shimmer; birds glide; late in the clip a small white point of light appears in the sky above the tower. |
| n12 two at sunset railing | rooftop, rooftop heads, wind | 10 s | Static camera, gentle sway; their hair, her yellow ribbon and his red scarf move in the wind; Ren turns his head slightly toward the sky; the sun sinks a little. |
| n14 Ren close-up | Ren push-in, eyes, resolve | 6 s | Slow push-in; Ren blinks once, then his eyes narrow with focus; his hair lifts in a sudden gust; bokeh lights drift behind him. |
| n09 Hana smiling (flashback) | Hana flashback, smile | 8 s | Hana laughs, tilts her head and turns slightly toward the camera; ponytail and yellow ribbon swing; clouds drift; soft sparkle. |
| n01 looking up at cracked sky | sky cracks, city rain | 8 s | The glowing cracks in the sky spread outward and flicker; glass shards break off and fall; she slowly looks up with wide eyes, hair and ribbons blowing; light rays pulse. |
| n13 beast + Ren and Hana | beast reveal, roar, bind, fracture, shatter | 10 s | Slow tilt up from the two students to the crystal beast; the beast lifts its head, eyes flare white and it roars; shards shake loose from its body; lightning flickers; her ribbon whips in the shockwave. |
| n03 Hana raises the staff | Hana ready, barrier, threads, shout | 8 s | Hana thrusts the staff higher and shouts; the cyan and gold light rings spin faster around the crystal; her ponytail and ribbon whip upward in the energy wind; lightning crackles behind. |
| n11 Ren leaps | leap, blade, charge | 6 s | Ren leaps through the air toward the camera, coat and red scarf flaring; he swings the glass sword forward in an arc; crystal shards spin past; camera tracks with him. |
| n05 clash (claw left) | clash, first hit | 4 s | Ren drives his sword into the crystal claw; a burst of white light and shards explode outward; his hair and scarf blast back; heavy camera shake. |
| n06 clash (claw right) | clash, second hit | 4 s | Ren pushes through and slashes across; the claw cracks and shatters into shards; sparks and light streak toward the camera. |
| n04 mirror dive | mirror dive, contact | 6 s | Ren dives head-first down into the mirror water, sword first; the surface splashes and ripples outward in glowing rings; his reflection rises to meet him; camera follows downward. |
| n08 shard snow at night | shard snow, close | 9 s | Glowing glass shards fall slowly like snow; their hair, her yellow ribbon and his red scarf drift in a soft wind; their shoulders rise and fall as they catch their breath; city lights twinkle. |
| n07 next morning | morning | 12 s | Slow pull-back over the bright city; birds fly past; her yellow ribbon and his red scarf flutter; Ren rests his arms on the wall and Hana leans toward him; clouds drift. |

About 116 s of generated video in total, as 14 clips. Clips longer than the model allows get made as two takes and cut together.
