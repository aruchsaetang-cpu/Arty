# Style guide — my-edit-style

Measured from 1 reference: the YouTube Short by @micrubik, "รู้มั้ยว่าใน Avatar #shorts"
(`youtube.com/shorts/0VNzREtkHsU`). We got it as an iPad screen recording: 2732×2048 HEVC, 21.7 s.
The Short sits in the middle of the recording. It was cropped back out at x=830, y=0, 1072×1906,
which is 9:16, then scaled to 1080×1920 for measuring. The recording stops at 21.7 s while the clip
is still running (the last caption "พลาดเลย" is cut off), so the ending is **not** measured.

The second link (`4F3AvGJk2z4`) has **not** been analysed yet: the environment blocked YouTube
and only one recording was uploaded. Until it has been, everything below comes from a single clip.

Tags: **[วัดได้]** = measured with FFmpeg or pixel analysis. **[ไม่แน่ใจ]** = an estimate or a
guess. Treat it as a guess.

All coordinates are on a **1080×1920** canvas.

---

## 1. Basic video properties

| Item | Value |
| --- | --- |
| Frame size / ratio | 1080×1920, 9:16 [วัดได้: the cropped area 1072×1906 = 0.5624 ≈ 0.5625] |
| Frame rate | Render at **30 fps**. The source fps is [ไม่แน่ใจ]: the screen recording is VFR at about 27 fps on average, and over 2 s of the band 154 of 219 frames were unique, which points to a 30 or 60 fps source. |
| Duration | ≥ 21.7 s (the recording is cut off). Short-form clip, about 20–30 s [ไม่แน่ใจ] |
| Original bitrate / file type | Can't tell from a screen recording [ไม่แน่ใจ]. Recommended output: H.264 High, CRF 16–18, AAC 48 kHz 192 kbps, `.mp4` |

## 2. Cutting pace

**B-roll cuts** (detected in the sharp band, FFmpeg `scdet`, then checked frame by frame) [วัดได้]:
`0.67, 1.67, 3.20, 4.83, 7.03, 9.30, 11.00, 13.77, 14.83, 16.07, 17.67` → 12 shots in 21.7 s

| Item | Value |
| --- | --- |
| Shots | 12 (11 cuts) → **30.4 cuts/minute** |
| Mean length of a complete shot (shots 2–11) | **1.70 s** |
| Shortest / longest | **1.00 s** / **2.77 s** |
| Opening (0–3 s) | First shot 0.67 s (Na'vi close-up, the most iconic image) → 1.00 s (aerial of the sea) → 1.53 s (ship). **3 shots in 3 s**, faster than the middle |
| Middle | 1.06–2.77 s, mean 1.8 s |
| Ending | The last shot runs ≥ 4.0 s (interview with the person being discussed). The pace slows at the end so the subject can speak [ไม่แน่ใจ because it is cut off] |
| Cutting speech | **No pause > 60 ms** below −30 dBFS in the whole clip [วัดได้: silencedetect]. Every breath gap is cut out. Speech rate is about **5.1 syllables/second** (109 syllables / 21.3 s) |
| Cuts land on phrases | 6 of 11 cuts fall within ±0.1 s of a caption change (3.20, 7.03, 13.77, 14.83, 16.07, 17.67). B-roll cuts **snap to the start of a new phrase** in most cases |

## 3. Text and captions (the HTML layer)

Caption change times (read off the frames, 30 fps) [วัดได้]:

| # | in–out (s) | Text |
| --- | --- | --- |
| 1 | 0.00–0.47 | เพื่อนๆ รู้มั้ยว่า (the recording started mid-caption) |
| 2 | 0.47–0.90 | ในหนัง |
| 3 | 0.90–1.43 | Avatar |
| 4 | 1.43–2.10 | ถ้าโทรศัพท์ |
| 5 | 2.10–2.77 | เผลอดังขึ้นมา |
| 6 | 2.77–3.27 | เพื่อนๆ รู้มั้ยว่า |
| 7 | 3.27–3.90 | เตรียมซื้อ |
| 8 | 3.90–4.47 | เครื่องใหม่ได้เลย |
| 9 | 4.47–5.43 | ในเรื่องนี้ |
| 10 | 5.43–6.33 | มีคนหลายร้อยชีวิต |
| 11 | 6.33–6.97 | ที่ต้องทำงาน |
| 12 | 6.97–7.53 | พร้อมกัน |
| 13 | 7.53–8.63 | ทำให้การเสียเวลา |
| 14 | 8.63–9.67 | แม้แต่นิดเดียว |
| 15 | 9.67–10.77 | เป็นเรื่องใหญ่มาก |
| 16 | 10.77–11.30 | ผู้กำกับ |
| 17 | 11.30–12.00 | James cameron |
| 18 | 12.00–12.87 | จึงตั้งกฎเหล็ก |
| 19 | 12.87–13.77 | ขึ้นมาว่า |
| 20 | 13.77–14.27 | ถ้าโทรศัพท์ |
| 21 | 14.27–14.77 | ใครดัง |
| 22 | 14.77–15.77 | ระหว่างถ่ายทำ |
| 23 | 15.77–16.30 | เขาจะเอา |
| 24 | 16.30–17.27 | ปืนยิงตะปู |
| 25 | 17.27–17.77 | ตอนมันติด |
| 26 | 17.77–18.33 | กำแพง |
| 27 | 18.33–19.80 | ให้ดูต่อหน้าทุกคน |
| 28 | 19.80–20.83 | ซึ่งได้ผลดีมาก |
| 29 | 20.83–21.30 | เพราะไม่มีใคร |
| 30 | 21.30– | พลาดเลย (cut off) |

| Item | Value |
| --- | --- |
| Captions per card | **1 phrase, 1 line**: 1–4 words, about **3.8 syllables/card**, at most 13 base Thai characters (ไม่นับสระบน/ล่าง/วรรณยุกต์; "มีคนหลายร้อยชีวิต" = 13) or 13 Latin characters |
| Time on screen | Mean **0.74 s**, shortest **0.43 s**, longest **1.47 s**. Follows the speech closely |
| Swap style | A card **replaces** the previous one (no word-by-word build-up). There is often a 1-frame (33 ms) gap with no text between cards |
| Position | Centred horizontally (x=540). **Vertical centre y ≈ 300 px (15.6% from the top)**, the median across 31 cards, inside the **top** blur area, never over the sharp band or the face |
| Size | Median white-text height **100 px** (up to about 160 px when there are upper and lower marks). Width 300–890 px, depending on length. "เครื่องใหม่ได้เลย" = 788 px |
| Keywords | **No highlighting**: every card is plain white, with no colour change, box or size change [วัดได้] |
| Entry animation | **Linear pop, 5 frames (≈0.17 s)**: scale **0.30 → 0.49 → 0.68 → 0.86 → 1.055** (overshoot peak) → **1.00** on frame 5. Grows about 0.19/frame, no easing [วัดได้: bbox width 248→412→568→724→884→840 px at 7.53–7.77 s; 400→556→708→868→820 px at 18.37–18.53 s] |
| Exit | Hard cut, no animation |

### Font

| Item | Value |
| --- | --- |
| Look | Thai **with loops**, rounded, monoline, informal/handwritten (kid-like), medium-to-bold weight, **upright**, fairly wide letter spacing. Latin in the same rounded family (single-storey `a`) |
| Fill | **#FFFFFF** [วัดได้] |
| Outline | **#111311**, about **7 px visible** outside the letters [วัดได้: stroke colour; thickness estimated from the image] |
| Shadow | Soft dark shadow, blur about 12 px, offset down about 3–4 px, around 55% opacity [ไม่แน่ใจ] |
| Background box | None |
| Exact font | **[ไม่แน่ใจ]** Probably a Thai font bundled with an app such as CapCut. The 3 closest free, commercially usable fonts (OFL, Google Fonts): |
| | 1. **Itim** (closest: same loop and stroke weight; default in this skill: 120 px, letter-spacing 1 px) |
| | 2. **Mali** 600 (round like the reference but heavier and taller) |
| | 3. **Sriracha** (handwritten, but it slants, which the reference does not) |

## 4. Colour and visual identity

Main tones taken from 13 frames (8-colour quantise, 16-step rounding) [วัดได้]:
`#101010`, `#202020`, `#302020`, `#605050`, `#404040`, `#B0B0A0`, `#907060`

| Role | HEX | Note |
| --- | --- | --- |
| Primary (text) | **#FFFFFF** | caption fill |
| Secondary (outline) | **#111311** | caption stroke |
| Accent | **#C4160A** | the presenter's red jacket in the circle, the only steady colour in every frame [ไม่แน่ใจ whether it is intended as a brand colour] |
| Background | **#101010–#303030** | dark, from the blurred footage |
| Text | **#FFFFFF** | |

- **Overall tone:** follows the footage. Mostly dark and low-key, medium contrast, no extra grade [ไม่แน่ใจ]
- **Logo / watermark / channel graphic:** none
- **Frame layout (the core of this style)** [วัดได้]:
  - **Background:** the same B-roll scaled to fill 1080×1920 and heavily blurred. It looks about 10% darker than the band (mean ratio 0.9) [ไม่แน่ใจ]
  - **Sharp band:** the full width, **y = 545 → 1371** (1080×826, ratio 1.31:1, centre y=958). B-roll is scaled to fill (16:9 sources get their sides cropped). The band edge is a hard line with no border
  - **Presenter circle:** diameter **349 px**, centre **(210, 1349)** (left 35, top 1175, bottom 1523). **No border.** It overlaps the bottom edge of the band. The presenter's room background is kept (no cut-out)

## 5. Transitions

- **Hard cuts: 10 of 11** [วัดได้]. No fade, slide, wipe, zoom or glitch.
- **1 of 11 looks like a whip-blur** at 17.53–17.67 s (about 4 frames): the shot of someone running with motion blur goes into a fully blurred frame, then the interview shot [ไม่แน่ใจ whether it is in the source or added by the editor]. If you use it, only use it to jump to a different place or person.
- Other blur or speed comes from the source footage (for example at 15.1–16.0 s).
- Captions also swap with hard cuts plus the pop.

## 6. Camera and image motion

- **No punch-in zoom** and no added Ken Burns [วัดได้: face size in the 11.0–13.7 s interview shot stays constant].
- B-roll is scaled to fill the band (from 16:9: about **1.36×**, crop the sides).
- Pans and tilts come from the source only. The presenter circle does not move.

## 7. Animation and graphics

- Nothing besides the captions: no icons, arrows, stickers, emoji or extra boxes.
- B-roll fills **100%** of the frame: the presenter only ever appears in the PiP circle.

## 8. Audio

| Item | Value |
| --- | --- |
| Voice | Continuous, **no pause > 60 ms**, LRA **2.4 LU** (heavily compressed) [วัดได้] |
| Loudness | **−18.5 LUFS** integrated [วัดได้, but ไม่แน่ใจ: it went through a screen recording, which can change the level]. Use **−14 LUFS** for export (the Shorts/TikTok standard) |
| Background music | A quiet bed that holds steady tones around **~700 Hz and ~1.2 kHz** all the way through (spectrogram), about 20 dB under the voice [ไม่แน่ใจ which genre]. Default in this skill: `data-volume` 0.12 |
| SFX | None found [ไม่แน่ใจ] |
| Voice processing | Gaps cut tight, compressed, no audible reverb [ไม่แน่ใจ] |

## 9. Signature techniques

1. **Hook as a question:** "เพื่อนๆ รู้มั้ยว่า + ในหนัง [X] + ถ้า [เหตุการณ์]…" and repeat "เพื่อนๆ รู้มั้ยว่า" again inside the first 3 s.
2. **B-roll shows exactly the noun just spoken:** "ผู้กำกับ / James cameron" → James Cameron. "ระหว่างถ่ายทำ" → the shooting rig. "ปืนยิงตะปู" → the action scene.
3. **The first shot is the strongest image in the topic** (a close-up of the main character), cut at 0.67 s.
4. **Commentator format:** a small presenter circle in the bottom left, with footage carrying the visuals the whole time.
5. **End with the real person talking** (a long interview shot) to add credibility.
6. **Speech packed tight** with no pauses, at about 5 syllables/second.

## 10. What we don't know / not yet measured

- The exact font (see the 3 candidates above).
- The ending (the recording stops at 21.7 s).
- The source frame rate and the original file's bitrate.
- Genre and level of the background music, and whether the voice had EQ.
- The second reference clip (`4F3AvGJk2z4`) has not been analysed: we don't yet know which parts the two clips share.
