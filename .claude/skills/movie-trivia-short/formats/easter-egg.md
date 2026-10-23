# Format B: "จุดที่คุณไม่เคยสังเกต" (Easter-egg list)

From the reference the user sent on 2026-10-23: TikTok @OFFSCRIPTYTS "Did You Notice These Things in Animated
Movies" (iPhone screen recording, 10.7 s captured, loudness about −14.5 LUFS, trending sound "Cantina Afternoon").
Measured from the recording; values are approximate [ไม่แน่ใจ ±5%].

| Item | Reference |
| --- | --- |
| Frame | Footage fills the whole 9:16 frame (cropped and zoomed from 16:9), no blurred band, no presenter |
| Pace | One easter egg every ~2.5–5 s; cuts at 2.8 s and 7.95 s inside 10.7 s |
| Title | Film name at the top (~18% from the top), white, bold condensed **italic caps**, black outline; stays for the whole egg |
| Captions | **One word at a time**, centre (~45% from the top), big bold italic caps, white with a thick black outline, changing every ~0.3–0.5 s |
| Pointer | Big **red arrow with a white outline** pointing at the detail; it bobs and moves to each new detail |
| Transition | Torn-paper white edges at the top/bottom while the shot zooms in; quick whip/zoom between eggs |
| Voice | Fast English voiceover (sounds like TTS) [ไม่แน่ใจ] |
| Music | Trending sound under the voice |

Thai version rules:
- Thai has no spaces, so show **1–2 words (one short phrase) at a time**, not single syllables.
- Title = film name in Thai or English, top. Arrow on the detail for each egg, appearing with a pop and bobbing.
- 20 s: hook (~2 s) + 3 eggs × ~6 s.
- Animated films are low-risk on TikTok (no masking); Disney and Pixar Content ID is strict, so use short shots
  and always talk over them.

## Variant C: "ความผิดพลาดในการ์ตูนที่คุณไม่เคยสังเกต" (animation mistakes)

From the second reference the user sent (TikTok/Shorts @TheMovieByteYTS "Movie Animation Mistakes You Didn't
Notice!", two recordings, 10.7 s and 7.8 s). Same visual system as Format B, with these differences:

| Item | Reference |
| --- | --- |
| Frame | Footage band fills ~85% of the height with **white torn-paper edges** top and bottom for the whole clip |
| Hook | Big red arrow on the character's face for the first ~2.5 s while the hook is spoken, then it goes |
| Captions | One word at a time, centre (~45% from the top), bold italic caps with a black outline, the same as B |
| Story per mistake | Show the "before" shot → show the "after" shot where the detail changed (pizza still there / backpack back) |
| Pace | One mistake every ~3–5 s; the clip loops straight into the next topic (Big Hero 6) |

Thai version: the same 20 s, 3 mistakes. Each mistake needs **two shots** (before/after) so the viewer can
see the change; the arrow points at the detail in both. Only use mistakes listed by at least one goofs source
(IMDb goofs, MovieMistakes.com, Looper) — fan claims without a source are left out.

## User rule: one fact per clip

Don't list 3 facts in one clip. Each easter egg or mistake gets its **own ~20 s clip** written in the usual
ฮุก → บริบท → แต่ → เฉลย structure. Formats B/C only lend the **look** (full-frame footage, torn-paper edges,
red arrow on the detail, 1–2 word captions) and the **topic ideas**:

| Part | Easter egg | Mistake |
| --- | --- | --- |
| ฮุก | "เพื่อนๆ รู้มั้ยว่า ในหนัง X มี … ซ่อนอยู่" | "เพื่อนๆ รู้มั้ยว่า ในหนัง X มีจุดผิดพลาดที่ไม่มีใครสังเกต" |
| บริบท | the scene and what happens in it | the "before" shot (the detail as it should be) |
| แต่ | "แต่ถ้าดูดีๆ …", where the arrow appears | "แต่ช็อตต่อมา …", the "after" shot, arrow on the change |
| เฉลย | who it is or where it comes from, and why the animators hid it | why it happened, or a funny closing line |

## Build

`scripts/build_easteregg.py edit.json out/` makes the Format B/C composition: footage window y 70–1650 between
torn-paper edges, film title at y≈190, 1–2 word captions (Kanit Black Italic, white with an 8 px outline) centred
at y≈870 with a 4-frame pop, and red arrows (`arrows`: tip x/y, angle) that pop in and bob. Captions:
`chunk_captions.py words.json caps.json --max-base 6 --target 0.4`. Crop film footage tightly
(`cropdetect=limit=0.12`) so letterbox bars don't show inside the window.
