"""Build File 001 v2: the retention cut of "The Island You Can't Visit".

Payoff first, real footage from frame 0, a cut every ~2s, 2-3 word captions,
and a last shot that matches the first so the short loops. ~15s.

    python3 scripts/build.py <tts-work-dir>   # expects t1..t5.wav from `hyperframes tts`
"""
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "..", "..", "tools", "hollow-truth"))
from build import run, captions, SCORE, fit  # noqa: E402
from htlib import el, write_project  # noqa: E402

WORK = sys.argv[1]
TEMPO = 1.12  # the whole read sped up 12%, pitch kept
GAP = 0.12
LINES = [
    {"say": "", "cap": "In 2018, an American paddled to this island, and never came back."},
    {"say": "", "cap": "It's North Sentinel. Just visiting is illegal."},
    {"say": "", "cap": "The people here have refused contact for maybe 60,000 years."},
    {"say": "", "cap": "After the tsunami in 2004, they shot arrows at a rescue helicopter."},
    {"say": "", "cap": "Would you go?"},
]


def dur(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout)


def pauses(p, d):
    import re
    import subprocess
    err = subprocess.run(["ffmpeg", "-i", p, "-af", "silencedetect=noise=-35dB:d=0.12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    e = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    return [(a, b) for a, b in zip(s, e) if b < d - 0.25]


clips, t = [], 0.05
for i in range(5):
    p = f"{WORK}/t{i + 1}.wav"
    d = dur(p)
    clips.append({"path": p, "dur": d, "start": round(t, 2), "pauses": pauses(p, d)})
    t += d + GAP
raw_end = clips[-1]["start"] + clips[-1]["dur"]
END = round(raw_end / TEMPO + 0.4, 1)

inputs, chains = [], []
for i, c in enumerate(clips):
    inputs += ["-i", c["path"]]
    chains.append(f"[{i}]adelay={int(c['start'] * 1000)}:all=1[a{i}]")
graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(5)) + \
    f"amix=inputs=5:normalize=0,asetrate=48000*0.93,aresample=48000,atempo={1.0753 * TEMPO:.4f}," \
    f"aecho=0.8:0.5:60|140:0.2|0.1,lowpass=f=9000,apad=whole_dur={END},atrim=0:{END},loudnorm=I=-15:TP=-1.5:LRA=11"
run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-ar", "48000", "-ac", "1", f"{WORK}/vo.wav"])
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{WORK}/vo.wav", "-c:a", "aac", "-b:a", "160k", f"{PROJ}/assets/audio/voiceover.m4a"])

caps = [(round(s / TEMPO, 2), round(e / TEMPO, 2), txt) for s, e, txt in captions({"lines": LINES}, clips, size=3)]
L = [round(c["start"] / TEMPO, 2) for c in clips]          # line starts on the final clock

# Shots: (id, file, start, end, media-start). A cut every ~2s; the last shot is the first shot again.
SHOTS = [
    ("s1", "beach-close", 0.0, 1.9, 0.0),
    ("s2", "reef-coast", 1.9, L[1] - 0.05, 2.0),
    ("s3", "island-clouds", L[1] - 0.05, L[2] - 0.05, 0.0),
    ("s4", "window-engine", L[2] - 0.05, L[2] + 1.85, 0.8),
    ("s5", "reef-coast", L[2] + 1.85, L[3] - 0.05, 4.2),
    ("s6", "shoreline-high", L[3] - 0.05, L[3] + 2.2, 0.0),
    ("s7", "window-engine", L[3] + 2.2, L[4] - 0.05, 2.0),
    ("s8", "beach-close", L[4] - 0.05, END, 0.0),
]
vids, js = [], []
for k, (sid, f, a, b, ms) in enumerate(SHOTS):
    vids.append(f'''    <div id="{sid}-wrap" class="shot-wrap" data-layout-allow-overflow>
      <video id="{sid}" class="clip shot" src="assets/footage/{f}.mp4" data-start="{a:.2f}" data-duration="{b - a:.2f}" data-media-start="{ms}" muted playsinline></video>
    </div>''')
    # Every shot pushes in; odd shots also drift sideways, so the frame is never still.
    js.append(f'    tl.fromTo("#{sid}-wrap", {{ scale: 1.0, x: 0 }}, {{ scale: {1.12 if k == 0 else 1.07}, x: {0 if k % 2 == 0 else -30}, duration: {b - a:.2f}, ease: "none" }}, {a:.2f});')
open(f"{PROJ}/compositions/footage.html", "w").write(f'''<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      overflow: hidden;
      background: #05080a;
    }}
    .shot-wrap {{
      position: absolute;
      inset: 0;
      transform-origin: 50% 45%;
    }}
    .shot {{
      position: absolute;
      left: 0;
      top: 0;
      width: 1080px;
      height: 1920px;
      object-fit: cover;
    }}
  </style>
  <div id="root" data-composition-id="footage" data-width="1080" data-height="1920">
{chr(10).join(vids)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    // Real footage: Air India AI549 over North Sentinel (screen recordings by the channel).
{chr(10).join(js)}
    window.__timelines["footage"] = tl;
  </script>
</template>
''')

D = lambda a, b: round(b - a, 2)
K = "top: 178px; font-weight: 400; font-size: 32px; letter-spacing: 0.42em; color: #ddd3b4;"
R = '<em style="font-style: normal; color: #ffffff; background: var(--accent, #e0352b); padding: 0 14px; text-shadow: none">'
s3, s4, s6, s8 = SHOTS[2], SHOTS[4], SHOTS[5], SHOTS[7]
scenes = [
    ("hook", 0, 1.9, "", "\n".join([
        el("hook-k", "t-body", 0, 1.9, "HOLLOW TRUTH · FILE 001", K),
        el("hook-l1", "t-display", 0, 1.9, "HE WENT HERE.", "top: 240px; font-size: 170px;"),
        el("hook-l2", "t-display", 0, 1.9, f"{R}NEVER</em> CAME BACK.", f"top: 420px; font-size: {fit('NEVER CAME BACK.', 940, 170)}px;"),
    ]), '''    tl.fromTo(["#hook-l1-in", "#hook-l2-in"], { scale: 1.06 }, { scale: 1, duration: 0.5, ease: "expo.out" }, 0);
    tl.to(["#hook-k-in", "#hook-l1-in", "#hook-l2-in"], { opacity: 0, duration: 0.12, ease: "power2.in" }, 1.76);'''),
    ("where", s3[2], D(s3[2], s3[3]), "    #where-l2-in { opacity: 0; }\n", "\n".join([
        el("where-l1", "t-display", 0, D(s3[2], s3[3]), "NORTH SENTINEL", "top: 260px; font-size: 140px;"),
        el("where-l2", "t-body", 0, D(s3[2], s3[3]), '<span style="background: var(--accent, #e0352b); padding: 6px 22px 10px">VISITING = ILLEGAL</span>',
           "top: 430px; font-size: 64px; letter-spacing: 0.06em;"),
    ]), f'''    tl.fromTo("#where-l1-in", {{ opacity: 0, scale: 1.2 }}, {{ opacity: 1, scale: 1, duration: 0.18, ease: "power4.out" }}, 0.05);
    tl.fromTo("#where-l2-in", {{ opacity: 0, scale: 1.6 }}, {{ opacity: 1, scale: 1, duration: 0.14, ease: "power4.out" }}, {1.25:.2f});'''),
    ("years", s4[2], D(s4[2], s4[3]), "", "\n".join([
        el("years-k", "t-body", 0, D(s4[2], s4[3]), "NO OUTSIDE CONTACT", "top: 240px; font-size: 50px; letter-spacing: 0.18em;"),
        el("years-n", "t-display", 0, D(s4[2], s4[3]), "0", "top: 310px; font-size: 300px;"),
        el("years-u", "t-display", 0, D(s4[2], s4[3]), "YEARS?", "top: 620px; font-size: 110px;"),
    ]), '''    const n = document.querySelector("#years-n-in");
    const c = { v: 0 };
    tl.fromTo(c, { v: 0 }, { v: 60000, duration: 0.9, ease: "power3.out", onUpdate: () => { n.textContent = (Math.round(c.v / 100) * 100).toLocaleString("en-US"); } }, 0.05);
    tl.fromTo(["#years-k-in", "#years-u-in"], { opacity: 0 }, { opacity: 1, duration: 0.15, ease: "power2.out" }, 0.05);'''),
    ("arrows", s6[2], D(s6[2], s6[3]), "", "\n".join([
        el("arrows-y", "t-display", 0, D(s6[2], s6[3]), "2004", "top: 230px; font-size: 220px;"),
        el("arrows-l", "t-body", 0, D(s6[2], s6[3]), f'ARROWS VS. A {R}HELICOPTER</em>', "top: 470px; font-size: 58px; letter-spacing: 0.06em;"),
    ]), '''    tl.fromTo("#arrows-y-in", { opacity: 0, scale: 1.25 }, { opacity: 1, scale: 1, duration: 0.18, ease: "power4.out" }, 0.03);
    tl.fromTo("#arrows-l-in", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.2, ease: "power4.out" }, 0.25);'''),
    ("ask", s8[2], D(s8[2], s8[3]), "", el("ask-l", "t-display", 0, D(s8[2], s8[3]), f"WOULD YOU {R}GO?</em>", "top: 300px; font-size: 180px;"),
     '''    tl.fromTo("#ask-l-in", { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, duration: 0.14, ease: "power4.out" }, 0.02);'''),
]
cuts = [a for _, _, a, _, _ in SHOTS[1:]]
write_project(PROJ, "footage", "Real footage, a cut every ~2s, last shot matches the first so it loops", "#05080a", scenes, caps, cuts)

# Bigger, punchier captions for the retention cut.
cp = f"{PROJ}/compositions/captions.html"
s = open(cp).read().replace("font-size: 66px;", "font-size: 84px;").replace("-webkit-text-stroke: 12px", "-webkit-text-stroke: 14px").replace("top: 1190px;", "top: 1150px;")
open(cp, "w").write(s)
ip = f"{PROJ}/index.html"
s = open(ip).read().replace('data-duration="20"', f'data-duration="{END}"')
open(ip, "w").write(s)

score = (SCORE.replace("N = int(SR * 20.0)", f"N = int(SR * {END})")
         .replace("SEED", "1001")
         .replace("TRAVEL_TIMES", str([round(x, 2) for x in cuts]))
         .replace("ARRIVE_TIMES", str([0.02, round(s3[2] + 1.27, 2), round(s4[2] + 0.95, 2), round(s6[2] + 0.05, 2)]))
         .replace("QUESTION_TIME", f"{s8[2] + 0.02:.2f}")
         .replace("20s case-board bed", "File 001 v2 bed"))
open(f"{PROJ}/scripts/score.py", "w").write(score)
run([sys.executable, f"{PROJ}/scripts/score.py", f"{WORK}/bed.wav"])
run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{WORK}/bed.wav", "-af", "loudnorm=I=-22:TP=-2", "-c:a", "aac", "-b:a", "192k", f"{PROJ}/assets/audio/bed.m4a"])
print(f"END {END}s; lines at {L}; cuts at {[round(c, 2) for c in cuts]}")
