# Arty: Thai movie-fact Shorts

Instructions for any coding agent (Codex, Claude Code, …) working in this repo.

## What this repo makes
Vertical 9:16 YouTube Shorts / TikTok clips in Thai: "รู้มั้ยว่า…" behind-the-scenes movie facts, voiced by the
channel owner, cut in a blurred-fill B-roll style with Thai Itim captions at the top. No music, no AI voice.

## Read first
- `.claude/skills/movie-trivia-short/SKILL.md`: channel strategy, topic rules, script structure, the winning
  near-death structure, voice-flow rules, credits format. Sections at the top override older ones below them.
- `.claude/skills/my-edit-style/SKILL.md`: the edit style and the render pipeline.
- `videos/TOPICS.md`: topic backlog and the status of every project.
- `videos/<project>/`: one folder per clip (`script.md`, `work/edit.json`, `work/captions.json`, voice files).
  Footage (`broll/`), raw takes and renders (`out/`) are gitignored: they are not in the repo.

## Script rules (short)
Hook (1 sentence, "รู้มั้ยว่า <actor Thai viewers know> …") / Context (3 sentences, explain so a non-viewer
understands) / แต่ (1 sentence; "แต่" appears only here) / Reveal (what happened, then the "kept in the film"
payoff, "ที่พีคคือ …"). Verify every fact with a source before writing it; say plainly when a claim is not verified.

## Pipeline for one clip
1. Voice: the owner sends one .m4a per paragraph (sometimes per sentence). Convert to 48 kHz mono wav.
   `python3 .claude/skills/my-edit-style/scripts/tighten.py raw.wav tight.wav --db -24 --min-gap 0.20 --pad 0.07`,
   then trim each take's ends by energy (20 ms windows, keep first..last window above 0.12 peak, pad 50 ms / 120 ms,
   12 ms fades). Join with 0.35 s between paragraphs, 0.30 s after "แต่", 0.12 s inside a paragraph. No speed-up.
2. Script for captions: `work/script.txt`, one line per take, words split by `|`, caption cards by `/`, `~n` = syllables.
3. Captions: `python3 .claude/skills/my-edit-style/scripts/align_runs.py script.txt voice.wav captions.json --starts <take starts> --end <end>`
   then join split names (e.g. "Django" + "Unchained").
4. Footage: the owner screen-records clips (iPad/iPhone). Crop to the picture only (`ffmpeg cropdetect`, then check a
   frame): remove app UI, channel names, watermarks, play icons, burned-in subtitles and any iOS control-center frames
   at the end of a recording.
5. `work/edit.json`: shots `{src,start,dur,media_start}` snapped to caption starts, `captions`, `duration`, `voice`,
   `facecam: null`. Copy the layout keys from `videos/rocky-punch-short/work/edit_v1.json`.
6. Render: `python3 .claude/skills/my-edit-style/scripts/build_composition.py work/edit.json out`,
   `cd out && npx hyperframes render -o renders/raw.mp4`,
   `bash .claude/skills/my-edit-style/scripts/finish.sh raw.mp4 <name>.mp4` (-14 LUFS).
7. Check frames (`python3 .claude/skills/movie-trivia-short/scripts/safety_sheet.py video.mp4 sheet.png --every 2`)
   before sending: no UI, no control center, no watermark, hook frame shows the subject.
8. Give a Thai title + description with credits (film, year, director, studio, "ภาพประกอบจาก YouTube…", voice by the owner).

## Repo rules
- Never commit footage, raw takes or renders (see `.gitignore`).
- Never put a model name in repo content.
