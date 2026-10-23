---
name: movie-trivia-short
description: Plan and deliver a Thai "เพื่อนๆ รู้มั้ยว่า…" movie behind-the-scenes Short (YouTube Shorts / TikTok) end to end — pick a verified trivia topic, write the ฮุก/บริบท/แต่/เฉลย script, give YouTube links for every B-roll scene, check TikTok/YouTube safety and copyright risk, cut it with my-edit-style, and write the Thai description with credits. Use when the user wants a clip about a film ("อยากทำคลิปเกี่ยวกับหนัง", "next vid", "เรื่องเบื้องหลังหนัง", a movie name) or asks about a clip being masked/claimed on TikTok or YouTube.
---

# movie-trivia-short

The workflow behind the user's movie Shorts. The editing itself is the `my-edit-style` skill; this
skill covers everything around it: topic, facts, script, footage links, platform safety, description.
Talk to the user in Thai.

## 1. Topic

Offer 4–5 behind-the-scenes stories from foreign films that fit the hook "เพื่อนๆ รู้มั้ยว่า ในหนัง X …":
an actor nearly died or was hurt for real, an accident or improvisation that became a famous scene,
an on-set romance **only if the people involved confirmed it publicly**. Never spread rumours about
real people. Mark one ⭐ recommended, and for each give the **safety risk** (section 4) up front.

## 2. Verify before writing

Search the web for the chosen story. Prefer the person's own account (memoir, interview) plus a
fact-check (Snopes) or a major outlet. Drop details the sources disagree on (take number, how many
seconds, money) instead of guessing. List the sources at the end of the reply. Say plainly if a
detail is from memory and not yet checked.

## 3. Script: ฮุก → บริบท → แต่ → เฉลย

Follow `my-edit-style/script-structure.md`: ฮุก 1 sentence (3–5 s), บริบท 3–4, แต่ 1, เฉลย 3–4 sentences,
about 25–30 s spoken. End on the source ("…เล่าเองในหนังสือ…") or the real person. Ask the user to
record the voice **as one file** (or number the files) — recording order mix-ups broke the captions once.

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
| Raiders of the Lost Ark — "shoot the swordsman" came from Ford's dysentery | `videos/raiders-sword-short/` | B-roll ready, waiting for the voiceover |
