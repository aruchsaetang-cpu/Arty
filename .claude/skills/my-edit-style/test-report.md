# Skill test report — my-edit-style

Date: 2026-10-23. We ran the whole skill (steps 2–9 in SKILL.md) on a 21 s test clip.

## Test inputs

| Input | Source | Note |
| --- | --- | --- |
| Talking head | The presenter circle cropped out of the reference (350×350, 21.3 s), with **3 pauses added** (0.6 + 0.7 + 0.5 s) so it behaves like a raw recording | Used only to test locally. Not stored in the skill and not committed |
| B-roll | 8 clips from `videos/tesla-roadster-short/assets/footage/` (the user's own footage) | No `keywords`, so the clips are used in order |
| Transcript | **Whisper could not run in this environment** (the network blocks model downloads from huggingface.co / openaipublic). We used the text read off the reference's on-screen captions instead, split into 85 words with even timing inside each phrase | `transcribe.py` itself was not tested here |
| Music | None | |

## Results by step

| Step | Result |
| --- | --- |
| `tighten.py` | Removed 1.68 s of the 1.80 s of pauses added (it keeps 25 ms either side of each cut). Longest remaining gap in the output: **66 ms** |
| `chunk_captions.py` | 28 cards, mean 0.77 s (min 0.47, max 1.11). The phrasing matches the reference on 24 of 28 cards. The ones that differ: "ทำให้การ / เสียเวลา" (reference has one card), "ถ้าโทรศัพท์ใครดัง" (reference has two), "ให้ดู / ต่อหน้าทุกคน", "เขาจะเอาปืน / ยิงตะปู" |
| `plan_broll.py` | 13 shots, mean 1.65 s. Cuts land on caption boundaries 13/13 |
| `build_composition.py` + `hyperframes check` | **0 errors**. 19 `line_unread` warnings are expected: the reference cards stay up 0.43–1.47 s, shorter than HyperFrames' reading guideline |
| `hyperframes render` | 1080×1920, 30 fps, 21.5 s, about 4.8 minutes on this machine |
| `finish.sh` | −14.0 LUFS |

## Match against the reference (`measure_style.py`)

The meter was calibrated on the reference first and scored it **100%**. It was then run on the test output:

| Item | Measured | Reference | Score |
| --- | --- | --- | --- |
| Frame size | 1080x1920 | 1080x1920 | 100% |
| Mean shot length | 1.69 s | 1.70 s | 100% |
| Shortest/longest shot | 1.27/2.13 s | 1.06/2.77 s | 84% |
| Longest speech gap | 66 ms | ≤60 ms | 100% (within tolerance) |
| Mean time per card | 0.77 s | 0.74 s | 100% |
| Caption vertical centre | 298 px | 300 px | 100% |
| Caption text height | 104 px | 100 px | 100% |
| Pop: first-frame scale | 0.46 | 0.40 | 100% |
| Pop: peak | 1.038 | 1.055 | 100% |
| Pop: frames to settle | 5 | 5 | 100% |
| Sharp band top/bottom edge | 545/1371 | 545/1371 | 100% |
| Presenter circle (left edge at y1450 / bottom edge) | 67/1524 | 67/1523 | 100% |
| **Overall** | | | **99%** |

## What the meter doesn't cover, and what still differs (honest assessment)

1. **Font:** Itim is close but not the same. The reference letters are spaced a little wider and the
   strokes are slightly heavier (visible when the frames sit side by side). Estimated visual match for
   this part is about 80% [ไม่แน่ใจ].
2. **B-roll content:** the test footage has nothing to do with what is being said (no `keywords`
   were used), so the "show what you're talking about" technique wasn't tested. On a real job, fill
   in `keywords` in `broll.json`.
3. **First shot:** 0.47 s, against 0.67 s in the reference (the first caption boundary falls at 0.47 s).
4. **Longest shot** in the test is 2.13 s (reference 2.77 s), because the clips are 2.6–4.0 s long and each one is used in two parts.
5. **Background music / whip-blur / hook:** not tested. The skill doesn't add these automatically (see SKILL.md).
6. **Whisper:** not tested in this environment. Run it once on your own machine.
