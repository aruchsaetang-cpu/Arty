---
name: my-edit-style
description: Edit raw footage into a Thai commentator-style vertical Short (9:16) in the user's reference style — use when the user hands over footage to edit (a talking-head recording plus B-roll clips) or says "ตัดต่อ", "ตัดคลิปนี้", "ทำคลิปสไตล์เดิม", "my-edit-style". Produces a blurred-fill B-roll frame with a sharp centre band, a round presenter cam bottom-left, one-phrase pop captions at the top, tight no-pause speech, and hard cuts snapped to phrases; renders with HyperFrames.
---

# my-edit-style

Turns the user's footage into a Short that looks like the reference. Every number comes from
[`style-guide.md`](style-guide.md); read it before changing anything. Don't guess values that
aren't in it.

## What you need from the user

1. **Talking-head clip** (`talk.mp4`): the presenter speaking Thai. Any orientation; the face is
   cropped into a circle.
2. **B-roll clips** (one or more), plus the order they should appear in. Ask which clip goes with
   which topic and write it into `keywords`.
3. Background music (optional): a quiet bed with no vocals. Use only music the user has the rights to.

If the user doesn't give B-roll, ask for it. The style needs B-roll 100% of the time; don't use
the talking head full-screen.

## Tools (install them yourself if missing, don't ask)

```bash
ffmpeg -version                      # apt-get install -y ffmpeg
python3 -c "import whisper" || pip install openai-whisper      # or faster-whisper
npx --yes hyperframes --version      # HyperFrames CLI (Node 22+)
```

Whisper downloads its model on the first run. It needs to reach `huggingface.co` or
`openaipublic.azureedge.net`.

## Steps

Work in a project folder such as `videos/<name>/`. `S=.claude/skills/my-edit-style/scripts`.

```bash
# 1) Check the source files
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact talk.mp4

# 2) Cut every pause out of the speech (style: no gap > 60 ms)
python3 $S/tighten.py talk.mp4 work/talk_tight.mp4 --cuts work/cuts.json
#    Words clipped → reduce --db (e.g. -40) or increase --pad (default 0.025 → 0.04)

# 3) Transcribe to word timestamps
python3 $S/transcribe.py work/talk_tight.mp4 work/words.json --model medium
#    Open words.json and fix wrong words (names, English words). Or use --fix later

# 4) Group into caption cards (1 phrase, ~0.74 s, ≤13 base Thai characters)
python3 $S/chunk_captions.py work/words.json work/captions.json [--fix fixes.json]
#    Read captions.json and check that no card splits in the middle of a word. Edit the text or times directly if needed

# 5) Write broll.json (in story order) then plan cuts on phrase boundaries
#    [{"src":"broll/a.mp4","in":0,"out":8,"keywords":["avatar"]}, ...]
python3 $S/plan_broll.py work/captions.json broll.json work/edit.json \
  --facecam work/talk_tight.mp4 [--music music/bed.m4a --music-volume 0.12]
#    The first shot should be the strongest image (the most iconic one in the topic), about 0.6–1.0 s

# 6) Build the HyperFrames composition
python3 $S/build_composition.py work/edit.json out --cam-pos "50% 40%"
#    --cam-pos sets where the face sits in the circle (move the % until the face is centred)

# 7) Check, preview, then render
cd out && npx hyperframes check
npx hyperframes snapshot --at 1,5,10     # check frames: face in the circle, captions not clipped
npx hyperframes render -o renders/draft.mp4

# 8) Set loudness to -14 LUFS for upload
bash ../$S/finish.sh renders/draft.mp4 renders/final.mp4

# 9) Measure against the reference and report the score
python3 ../$S/measure_style.py renders/final.mp4 --json renders/style-report.json
```

## No talking-head clip / Whisper can't run

- **Voice only (e.g. Voice Memos):** extract the audio from each take, concatenate them in order, then run
  `tighten.py raw.wav voice_tight.wav` (supports audio-only files). In `plan_broll.py`, use `--voice voice_tight.wav`
  instead of `--facecam`. `build_composition.py` leaves out the presenter circle, and
  `measure_style.py --no-cam` skips the circle checks.
- **No Whisper:** write `script.txt` with one line per take, words separated by `|` and caption-card breaks marked
  with `/`, then run
  `align_script.py script.txt words.json --anchors <start of each take> --end <end>`. Use the
  `--cuts` output from `tighten.py` to find where each take starts. The timing is an estimate, so always check it in preview.

## Style rules the scripts don't cover (do these yourself)

- **Script structure ฮุก → บริบท → แต่ → เฉลย** (1 / 3–4 / 1 / 3–4 sentences): see
  [`script-structure.md`](script-structure.md). After step 3, label each part of the transcript. If a part is
  missing or too long, tell the user and suggest a fix. Don't rewrite their words without asking.
- **Hook:** "เพื่อนๆ รู้มั้ยว่า + ในหนัง [ชื่อเรื่อง] + [เหตุการณ์ที่น่าสงสัย]", about 3–5 s long (reference 4.5 s).
- **B-roll shows what's being said:** use `keywords` in `broll.json` so the shot changes when the
  matching noun is spoken (a person's name → that person, a thing → that thing), and change the
  footage every time the script moves to a new part.
- **Ending:** close on a longer shot (about 3–4 s) of the real person or thing being discussed.
- **Footage credit:** when B-roll comes from someone else's channel, put `"credit": "ที่มาคลิป: YouTube @<channel>"` in
  `edit.json`. It shows as a small line under the sharp band, on the right, for the whole clip. The reference doesn't have one; add it at the user's request.
- **Don't add** transitions, zooms, stickers, emoji, arrows, colour highlights or caption boxes.
  The reference has none. Hard cuts only. A whip-blur can be used at most once, to change place or person.
- Captions are **plain white with a black outline**. The colour never changes, there is never more
  than 1 line, and they sit in the top area above the sharp band.

## Report back to the user

After rendering, tell the user:
- the path of the final file,
- the score table from `measure_style.py` (match %),
- the parts that still differ and why (for example, the font is a close match, not the exact one;
  see style-guide §3).

## Files

| File | What it does |
| --- | --- |
| `style-guide.md` | The 10-part analysis, with numbers and hex codes, of the reference |
| `script-structure.md` | Script structure ฮุก/บริบท/แต่/เฉลย from the creator's slides, mapped onto the reference |
| `test-report.md` | Results of the test run on a 21 s clip (99% match) and what still differs |
| `scripts/tighten.py` | Cuts pauses (silencedetect + select/aselect) |
| `scripts/transcribe.py` | Whisper → `words.json` |
| `scripts/align_script.py` | Fallback without Whisper: known script + start time of each take → `words.json` |
| `scripts/chunk_captions.py` | Words → caption cards like the reference |
| `scripts/plan_broll.py` | Places B-roll cuts on caption boundaries → `edit.json` |
| `scripts/build_composition.py` | `edit.json` → HyperFrames `index.html` (blurred fill, sharp band, cam circle, pop captions) |
| `scripts/finish.sh` | Loudness normalisation to -14 LUFS |
| `scripts/measure_style.py` | Measures the output against the reference → match % |
| `assets/fonts/` | Itim (OFL), the closest free font to the reference |
| `assets/vendor/gsap.min.js` | GSAP for the caption animation |
