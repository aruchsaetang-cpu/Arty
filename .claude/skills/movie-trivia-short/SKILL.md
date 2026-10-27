---
name: movie-trivia-short
description: Plan and deliver a Thai "เพื่อนๆ รู้มั้ยว่า…" movie behind-the-scenes Short (YouTube Shorts / TikTok) end to end — pick a verified trivia topic, write the ฮุก/บริบท/แต่/เฉลย script, give YouTube links for every B-roll scene, check TikTok/YouTube safety and copyright risk, cut it with my-edit-style, and write the Thai description with credits. Use when the user wants a clip about a film ("อยากทำคลิปเกี่ยวกับหนัง", "next vid", "เรื่องเบื้องหลังหนัง", a movie name) or asks about a clip being masked/claimed on TikTok or YouTube.
---

# movie-trivia-short

The workflow behind the user's movie Shorts. The editing itself is the `my-edit-style` skill; this
skill covers everything around it: topic, facts, script, footage links, platform safety, description.
Talk to the user in Thai.

## 00. LOCKED TEMPLATE (user, 2026-10-27) — copy `videos/jackie-chan-short/work/edit6.json` exactly

Final reference clip: `videos/jackie-chan-short` v6 (20.9 s). Every new video = same recipe, minimum tokens:
1. Topic → 1 web search to verify → script (Hook "Times <star> almost died." / Context "During the filming of <film>, …" 1–2
   sentences / But 1 sentence / Reveal 1–2 sentences, keyword in *stars*) → give user YouTube links, ask for screen recordings
   of (a) 3–4 film clips for the narration B-roll and (b) the REAL accident clip.
2. Voice: `english_tts.py` (voice {"am_puck":0.5,"am_liam":0.5}, per-sentence speeds 1.05–1.3, gap 0.1) → ~12 s.
3. Real footage after the narration: the action (jump/fall) → the result (hurt/hospital), END there (no slow-mo replays),
   no text, original audio or whoosh/crack/thud SFX if silent. Only the user's real clip.
4. edit.json like edit6.json: `layout: full`, `caption_style: comic`, `caption_y: 1020`, `pop_frames 3`, `pop_from 0.5`,
   red keywords `#FF3B30`, a cut every ~1–1.5 s. Render → finish.sh → one safety sheet → send → title + description
   (format below) in English → commit. No extra previews, no multiple variants, short replies.

## 0. Current house style (user, 2026-10-26) — overrides older notes below

- **Content:** emotional, high-curiosity movie/celebrity stories, e.g. "Times <star> almost died", "<N> times <star> wasn't
  actually acting", "The secret behind <film>'s craziest scenes". Real facts only, verified (section 2). Never use AI-made
  "behind the scenes" images or clips as if they were real.
- **Script structure (user rule, 2026-10-27 — strict):**
  - **Hook:** 1 sentence, spoken in ≤ 3 s.
  - **Context:** 3–4 sentences that set up the person / situation / what most people believe.
  - **But:** 1 sentence that flips the situation (starts with "But").
  - **Reveal:** 3–4 sentences explaining how it really went / why it's different, then the voiced lead-in to the real footage.
  One story per clip.
- **Length: 25–30 s.** 7–9 short sentences, hook → context → But → reveal, talk-like US English, no "Wait"/"Okay" opener,
  emotional beats ("He could barely even stand.", "They lost it.").
- **Voice:** young American male (user picked sample C) — `scripts/english_tts.py` with `"voice": {"am_puck": 0.5, "am_liam": 0.5}, "speed": 1.2, "gap": 0.16`.
- **Captions:** one word per card, big comic style — edit.json `"caption_style": "comic"`, `"caption_y": 1150`
  (move it if the footage has a lower-third), `"pop_frames": 3, "pop_from": 0.5`; keywords (*stars* in the script)
  coloured red `#FF3B30`.
- **Layout (user, 2026-10-26): full-frame, NO blur band** — edit.json `"layout": "full"`, `"caption_y": 1020`; set each shot's
  `"pos"` (object-position) so the subject stays in the 9:16 crop, then check the safety sheet for empty/edge framing.
- **Format (user rule, 2026-10-27, from the "Times Michael Jackson almost died" reference):** ~40% narration (~12 s; Hook/Context/But/Reveal in short, punchy sentences, no "this is the real footage" line — cut straight to it; hook = the shocking result/consequence, never a spoiler of the event itself), then ~60% (~17 s) REAL footage of the moment — must include the action itself (e.g. the jump), then the result, then a slow-mo replay — original audio, no captions. Total 25–30 s.
- **Hook/context wording (user rule):** hook = "Times <star> almost died."; context starts "During the filming of <film>, …". The real-footage half uses ONLY the clip the user gives for it (replay it in slow-mo to fill time; add whoosh/impact SFX if it has no sound) — never borrow footage from other uploads.
- **Cuts:** a new shot every 1–2 s; no music in the delivered file.
- **Voice realism:** give each sentence its own speed in the spec (`["text", 1.25]` excited, `1.0–1.1` for weight/punchlines),
  split punchlines into their own sentence, use `...` for a beat; english_tts.py applies a "creator mic" polish chain.
  Truly human-sounding needs ElevenLabs (vidIQ voiceover, credits) or the user's own voice.

## 1. Topic

Offer 4–5 behind-the-scenes stories from foreign films that fit the hook "เพื่อนๆ รู้มั้ยว่า ในหนัง X …":
an actor nearly died or was hurt for real, an accident or improvisation that became a famous scene,
an on-set romance **only if the people involved confirmed it publicly**. Never spread rumours about
real people. Mark one ⭐ recommended, and for each give the **safety risk** (section 4) up front.

Second format available: the easter-egg list, see `formats/easter-egg.md`.

## 2. Verify before writing

Search the web for the chosen story. Prefer the person's own account (memoir, interview) plus a
fact-check (Snopes) or a major outlet. Drop details the sources disagree on (take number, how many
seconds, money) instead of guessing. List the sources at the end of the reply. Say plainly if a
detail is from memory and not yet checked.

## 3. Script: ฮุก → บริบท → แต่ → เฉลย

Follow `my-edit-style/script-structure.md`, but **keep it to about 20 s** (user preference): ฮุก 1 sentence
(~3 s), บริบท 2 short sentences, แต่ 1, เฉลย 2 — roughly 90–100 Thai syllables at the user's ~5–6 syllables/s. End on the source ("…เล่าเองในหนังสือ…") or the real person. Ask the user to
record the voice **as one file** (or number the files) — recording order mix-ups broke the captions once.

## 3b. Keep it tight (user preference: don't waste the viewer's time)

- **The แต่ part always starts with the word "แต่"**, even in the shortest version (user rule).
- **Script:** cut every filler word ("ก็", "นั้น", "ที่ว่า", "จริงๆ แล้ว"). Each sentence carries one new piece of
  information. Aim for **15–20 s**; if the story fits in 15 s, stop at 15.
- **Hook starts on frame 1:** no intro, no logo, no "สวัสดีครับ". The first words are the hook.
- **Voice:** `tighten.py --min-gap 0.08 --pad 0.02` (no breath gaps). If it still drags, speed the voice up
  1.05–1.1× with `ffmpeg -af atempo=1.08` before building (pitch is kept).
- **Shots:** 0.8–1.5 s each (faster than the 1.7 s reference), so every phrase gets a new image. Hold a shot longer
  only while the arrow points at the detail.
- **Ending:** finish on the punchline. Cut within 0.3 s of the last word, with no outro and no fade-out longer than 0.3 s.

## 4. Platform safety (check every clip)

TikTok masked the Back to the Future clip as "เนื้อหาที่ละเอียดอ่อน" because of hanging shots from a PG
film. Judge each planned shot:

| Image | TikTok | YouTube Shorts |
| --- | --- | --- |
| Hanging, noose, rope/hands at the neck, strangling, choking faces | **masked** | usually fine (film context) |
| Blood, wounds, gore, realistic injury make-up | **masked** | age-restriction if graphic |
| Gun/blade pointed at a person or the camera in close-up, someone shot on screen | risky | usually fine |
| Self-harm, suicide, drugs (images or words) | **masked/removed** | limited or removed |
| Long unchanged film footage, the film's own music | — | Content ID claim (revenue to the studio, or blocked in some countries) |

Rules:
1. The **first shot is the thumbnail** — never a risky image. Open on a face, the villain or a wide shot.
2. If the story needs risky images, plan **two cuts from the start**: YouTube (`edit.json`) and TikTok
   (`edit_tiktok.json`) where each risky shot is swapped for a safe one from the same scene. Voice,
   captions and music stay the same.
3. Keep risky images under 1 s, never close-ups, on TikTok.
4. Copyright: shots 1–3 s, always voiced over, no film soundtrack (use the synthesised music bed,
   e.g. `videos/bttf-hanging-short/scripts/music.py`). No on-screen credit unless the user asks.
5. After rendering, run `scripts/safety_sheet.py OUT.mp4 sheet.png` and look at every frame of the
   sheet before sending; list any frame that hits the table above.

If a clip is already masked: suggest (a) delete and re-post the safe cut, or (b) "ส่งคำขอให้ตรวจสอบ"
explaining it is a film scene used for commentary.

## 5. B-roll links

For every scene the script needs, give a **YouTube link** (prefer the official @MOVIECLIPS upload; add
`&t=<s>s` when the moment is known), found with a web search, plus which script part it covers.
Say when a link's channel or timestamp is unconfirmed. The user screen-records the scenes on iPad;
crop the picture out with `cropdetect` before editing (see `my-edit-style`).

**Footage pitfalls:** many TikTok/Reels "behind the scenes" clips are AI-generated (look for an "AI" badge, wrong faces) — never use them as real footage. Screen-recording Netflix/Disney+ gives a black picture; use YouTube uploads of the real film. Skip topics whose key scene contains nudity.

## 5b. Music (user preference: viral / trending sound)

Trending songs are copyrighted, so never put one into the rendered file. Instead:
1. Deliver a cut **with no music** (voice only) — the user adds the trending sound inside TikTok
   ("เพิ่มเสียง" → pick a trending track, set it to ~10–15% volume under the voice) or in YouTube Shorts
   ("เพิ่มเสียง" from the Shorts audio library). Platform-licensed sounds don't trigger claims.
2. Also offer a version with a synthesised beat in a viral style (phonk / trap / upbeat), made with
   `scripts/viral_beat.py`, for when the user doesn't want to pick a sound in-app.
3. Suggest 2–3 kinds of trending sounds that fit the story's mood (tension, comedy, epic), without
   claiming a specific song is trending unless a web search this week confirms it.

Default for these Shorts (user wants energy like the references): `energy_beat.py`, a 150 bpm EDM beat with a four-on-the-floor kick, pumping supersaw chords, a pluck lead and a riser into the drop on "แต่", mixed ~8 dB under the voice (data-volume 0.24). `swing_beat.py` is the calmer lo-fi option. If the user wants the exact trending sound from a reference, tell them to tap the sound on that post in TikTok and "ใช้เสียงนี้" on the no-music cut.
Match the bed to the film's mood: `viral_beat.py` (phonk) for action/edgy topics, `magic_bed.py` (music-box
waltz + sparkle on the reveal) for animated / fairy-tale topics, the BTTF-style tension bed for near-death stories.
**Language & voice (user rules, 2026-10-24): voiceover, captions, titles and descriptions in ENGLISH.** Voice must sound natural and FAST like viral Shorts narrators (reference: ~6 syllables/s, no pauses between sentences): `scripts/english_tts.py` with `sentences` (one breath per sentence, Kokoro am_michael, speed 1.5, gap 0.05) — it writes one-word caption cards, keywords wrapped in *stars* turn yellow. In edit.json set `"pop_frames": 2, "pop_from": 0.75` so the short word cards don't flash small. Expect ~13–15 s for a 5-sentence script. Write it the way people actually talk (user rule): casual US English — "Like, …", "And honestly?", contractions, short punchy sentences — but keep the hook → context → But → reveal structure. Do NOT open with "Wait," or "Okay, so" (user: looks weird); start straight on the hook ("Did you know…", "That scene where…").
**AI voice fallback:** vidIQ `vidiq_voiceover_generate` (voice "Liam", 14 credits/1000 chars) sounds best; when credits run out use `scripts/thai_tts.py spec.json voice.wav caps.json` (offline MMS-TTS, more robotic) — it writes per-phrase captions with exact timing.
**Current defaults (user, 2026-10):** the user records the voiceover themselves (no AI voice unless asked) and the final cut has **no music / background sound** — they add a sound in-app.
No title that stays on screen the whole clip (user preference): leave `title` out of edit.json, or only show it in the hook.

## 5c. Channel look (user rule): the blur style is the main style

Every clip uses the **my-edit-style blur layout** (blurred fill, sharp band y 545–1371, captions at the top),
as in the Back to the Future clip, built with `my-edit-style/scripts/build_composition.py`. Extras go on top of it
only when the story needs them: red arrows (`arrows` in edit.json, on the "แต่" line), slow motion or a freeze
frame of the detail, and `pos` per shot to frame the subject inside the band. The torn-paper full-frame
template (`build_easteregg.py`, formats/easter-egg.md) is only for when the user asks for it.

## 6. Edit

Run the `my-edit-style` skill (voice-only mode when there is no talking-head clip). Deliver with and
without captions, and the TikTok-safe cut when section 4 calls for it.

## 7. Description (Thai, ready to paste)

Give a YouTube version and a short TikTok version:

```
<ฮุกเป็นประโยคเดียว> 😱

เรื่องเบื้องหลัง:
<3–4 บรรทัดสรุปเรื่อง ตามข้อมูลที่ยืนยันแล้ว>

เครดิต:
🎬 ภาพยนตร์: <ชื่อ> (ปี) ผู้กำกับ: <ชื่อ> | ผู้สร้าง: <สตูดิโอ>
📺 ฟุตเทจจาก: ช่อง YouTube @<ช่อง>
📖 ที่มาของเรื่อง: <หนังสือ/บทสัมภาษณ์>
🎵 เพลงประกอบ: ทำขึ้นเองสำหรับคลิปนี้

คลิปนี้ทำขึ้นเพื่อเล่าเรื่องเบื้องหลังและวิจารณ์ภาพยนตร์ ลิขสิทธิ์ภาพยนตร์เป็นของเจ้าของ

#<หนัง> #<นักแสดง> #เบื้องหลังหนัง #รู้หรือไม่ #หนัง #shorts
```

Add 2–3 title options. Remind once that a credit is good manners, not permission to use the footage.

## Done so far

| Clip | Folder | Notes |
| --- | --- | --- |
| Back to the Future III — Michael J. Fox passed out in the hanging scene | `videos/bttf-hanging-short/` | YouTube cut + TikTok-safe cut (masked on TikTok before) |
| Raiders of the Lost Ark — "shoot the swordsman" came from Ford's dysentery | `videos/raiders-sword-short/` | Done with offline Thai TTS voice (`work/edit_ai.json`), no music |
| Spider-Verse — AI only predicted ink lines on faces; next film won't use generative AI | `videos/spiderverse-ai-short/` | Final = `work/edit_hd.json`, AI voice (vidIQ), **no music** (user picks the sound in-app) |
| The Dark Knight — Ledger improvised the Joker's slow clap | `videos/darkknight-clap-short/` | Kept as rendered: AI voice, no music (`work/edit.json`); can be re-cut with the user's voice later |
| Toy Story — early 'Black Friday' Woody was so mean Disney halted production | `videos/toystory-woody-short/` | Done with offline Thai TTS voice (`work/edit_ai.json`), no music |
| Titanic — Cameron's hands drew Rose's portrait | `videos/titanic-sketch-short/` | **Dropped** by the user (footage too hard: nude scene, AI-fake BTS clips, streaming apps record black) |
