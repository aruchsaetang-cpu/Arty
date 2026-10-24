"""Retention recut (v2) of a hand-built Hollow Truth short (Files 002-004).

    python3 tools/hollow-truth/recut_v2.py 002 [003 004]

1. Renders the original film's picture and sound bed, without its voiceover or captions.
2. Records a tighter, payoff-first voiceover (natural voice, fast continuous read).
3. Retimes the original scene by scene so each scene starts on its new line.
4. Builds videos/<slug>-v2/: the retimed film with a punch-in on frame 0, the new
   voiceover, 2-3 word captions, and a last frame that matches the first so it loops.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
from build import REPO, run, captions, esc  # noqa: E402

CLI = ["npx", "--yes", "hyperframes@0.8.191"]
TEMPO = 1.05  # natural read, nudged 5% faster (pitch kept)
GAP = 0.05

# anchors: where each original scene began (one per line, then the closing question if it has its own).
FILMS = {
    "002": {
        "src": "dyatlov-pass-short", "slug": "dyatlov-pass",
        "anchors": [0, 5.0, 8.75, 12.2, 13.75, 16.0],
        "lines": [
            "Nine hikers cut their tent open from the inside, and ran out into the snow.",
            "Barely dressed, at minus thirty.",
            "Some had crushed chests, but almost no wounds on the skin.",
            "One was missing her tongue.",
            "Some of their clothes were radioactive.",
            "And the mountain's name? Dead Mountain.",
        ],
    },
    "003": {
        "src": "mary-celeste-short", "slug": "mary-celeste",
        "anchors": [0, 4.15, 7.35, 11.1, 12.95, 14.65],
        "question_anchor": 17.5,
        "lines": [
            "Ten people vanished from this ship, and it was still sailing.",
            "Nobody on board. No sign of a struggle.",
            "Six months of food and water, left behind.",
            "The only lifeboat was gone.",
            "They were never seen again.",
            "So why would they abandon a perfectly good ship?",
        ],
    },
    "004": {
        "src": "wow-signal-short", "slug": "wow-signal",
        "anchors": [0, 4.95, 9.45, 10.55, 12.75, 15.55],
        "question_anchor": 17.3,
        "lines": [
            {"say": "In nineteen seventy seven, this signal came from deep space, and never came back.",
             "cap": "In 1977, this signal came from deep space, and never came back."},
            "It was so strong, the astronomer circled it, and wrote one word.",
            "Wow.",
            {"say": "It lasted seventy two seconds.", "cap": "It lasted 72 seconds."},
            "We've searched that patch of sky ever since.",
            "Nothing has come back.",
        ],
    },
}


def render_base(src, work):
    """The original film's picture and bed only: voiceover removed, captions hidden."""
    base = os.path.join(work, "base")
    shutil.copytree(os.path.join(REPO, "videos", src), base, ignore=shutil.ignore_patterns("renders", ".hyperframes", "node_modules"))
    idx = open(f"{base}/index.html").read()
    idx = re.sub(r'\s*<audio\s+id="voiceover"[^>]*>\s*</audio>', "", idx, flags=re.S)
    idx = idx.replace('id="captions"', 'id="captions"\n        data-hidden="true"', 1)
    open(f"{base}/index.html", "w").write(idx)
    run(CLI + ["render", "-o", f"{work}/base.mp4"], cwd=base)
    return f"{work}/base.mp4"


def tempo_chain(f):
    parts = []
    while f > 2.0:
        parts.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        parts.append("atempo=0.5")
        f /= 0.5
    parts.append(f"atempo={f:.4f}")
    return ",".join(parts)


def recut(file):
    cfg = FILMS[file]
    work = tempfile.mkdtemp(prefix=f"ht-recut-{file}-")
    lines = [ln if isinstance(ln, dict) else {"say": ln} for ln in cfg["lines"]]
    # Voice: fast natural read (reference pace ~4.7 syll/s), no pitch or echo effects.
    clips = build.record({"lines": lines}, work, 1.4, squeeze=True)
    t = 0.05
    for c in clips:
        c["start"] = round(t, 3)
        t += c["dur"] + GAP
    raw_end = clips[-1]["start"] + clips[-1]["dur"]
    vo_end = raw_end / TEMPO
    end = round(vo_end + 1.5, 1)
    still = 0.35
    inputs, chains = [], []
    for i, c in enumerate(clips):
        inputs += ["-i", c["path"]]
        chains.append(f"[{i}]adelay={int(c['start'] * 1000)}:all=1[a{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(clips))) + \
        f"amix=inputs={len(clips)}:normalize=0,atempo={TEMPO},highpass=f=70,equalizer=f=3000:t=q:w=1:g=2.5," \
        f"acompressor=threshold=-20dB:ratio=3:attack=5:release=80,apad=whole_dur={end},atrim=0:{end},loudnorm=I=-14:TP=-1.5:LRA=7"
    proj = os.path.join(REPO, "videos", f"{cfg['slug']}-v2")
    if os.path.exists(proj):
        shutil.rmtree(proj)
    for d in ("assets/audio", "assets/footage", "assets/vendor", "compositions", "renders"):
        os.makedirs(f"{proj}/{d}")
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-ar", "48000", "-ac", "1", f"{work}/vo.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/vo.wav", "-c:a", "aac", "-b:a", "160k", f"{proj}/assets/audio/voiceover.m4a"])
    for c in clips:
        c["start"] = c["start"] / TEMPO
        c["dur"] = c["dur"] / TEMPO
        c["pauses"] = [(a / TEMPO, b / TEMPO) for a, b in c["pauses"]]

    # Scene map: each original scene now starts just before its new line.
    old = list(cfg["anchors"])
    new = [0.0] + [max(0.2, clips[i]["start"] - 0.1) for i in range(1, len(clips))]
    if "question_anchor" in cfg:
        old.append(cfg["question_anchor"])
        new.append(vo_end + 0.1)
    old.append(20.0)
    new.append(end - still)
    base = render_base(cfg["src"], work)
    vf, af, n = [], [], len(old) - 1
    for i in range(n):
        o, w = old[i + 1] - old[i], new[i + 1] - new[i]
        vf.append(f"[0:v]trim={old[i]}:{old[i + 1]},setpts=(PTS-STARTPTS)*{w / o:.5f},fps=30[v{i}]")
        af.append(f"[0:a]atrim={old[i]}:{old[i + 1]},asetpts=PTS-STARTPTS,{tempo_chain(o / w)}[s{i}]")
    # The last 0.35s is the first frame again, so the loop is seamless.
    vf.append(f"[0:v]trim=0:0.04,setpts=PTS-STARTPTS,loop=loop={int(still * 30)}:size=1:start=0,fps=30,trim=duration={still}[vs]")
    af.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={still}[ss]")
    cat = "".join(f"[v{i}][s{i}]" for i in range(n)) + f"[vs][ss]concat=n={n + 1}:v=1:a=1[v][a]"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", base, "-filter_complex", ";".join(vf + af + [cat]),
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-g", "1", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", f"{proj}/assets/footage/retimed.mp4"])

    # The v2 project: retimed film + punch-in + new voice + big captions.
    tpl = os.path.join(REPO, "videos", cfg["src"])
    for f in ("hyperframes.json", "CLAUDE.md", "AGENTS.md", ".gitignore", "assets/vendor/gsap.min.js"):
        shutil.copy(os.path.join(tpl, f), f"{proj}/{f}")
    pkg = json.load(open(f"{tpl}/package.json"))
    pkg["name"] = f"{cfg['slug']}-v2"
    json.dump(pkg, open(f"{proj}/package.json", "w"), indent=2)
    json.dump({"id": pkg["name"], "name": pkg["name"]}, open(f"{proj}/meta.json", "w"), indent=2)
    caps = captions({"lines": [dict(ln, cap=ln.get("cap", ln["say"])) for ln in lines]}, clips, size=3)
    divs = "\n".join(f'    <div id="cap-{i}" class="cap clip" data-start="{s}" data-duration="{round(e - s, 2)}"><span id="cap-{i}-in">{esc(t)}</span></div>'
                     for i, (s, e, t) in enumerate(caps))
    pops = "\n".join(f'    pop("#cap-{i}-in", {s});' for i, (s, e, t) in enumerate(caps))
    open(f"{proj}/compositions/captions.html", "w").write(f'''<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
    }}
    .cap {{
      position: absolute;
      left: 0;
      top: 1150px;
      width: 1080px;
      text-align: center;
      overflow: visible;
    }}
    .cap span {{
      display: inline-block;
      font-family: "Oswald", sans-serif;
      font-weight: 600;
      font-size: 84px;
      line-height: 1.1;
      color: #ffffff;
      -webkit-text-stroke: 14px #050e10;
      paint-order: stroke fill;
    }}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920">
{divs}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const pop = (sel, at) =>
      tl.fromTo(sel, {{ opacity: 0, scale: 0.86, y: 10 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.14, ease: "power3.out" }}, at);
{pops}
    window.__timelines["captions"] = tl;
  </script>
</template>
''')
    open(f"{proj}/index.html", "w").write(f'''<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }}
      html,
      body {{
        margin: 0;
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: #05080f;
      }}
      #root {{
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: #05080f;
      }}
      #film-wrap {{
        position: absolute;
        inset: 0;
        transform-origin: 50% 40%;
      }}
      #film {{
        position: absolute;
        left: 0;
        top: 0;
        width: 1080px;
        height: 1920px;
        object-fit: cover;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{end}" data-width="1080" data-height="1920">
      <!-- The original film, retimed scene by scene to the new voiceover; its sound bed rides along -->
      <div id="film-wrap" data-layout-allow-overflow data-layout-ignore>
        <video id="film" class="clip" src="assets/footage/retimed.mp4" data-start="0" data-duration="{end}" data-track-index="1" data-has-audio="true" data-volume="1" playsinline></video>
      </div>
      <!-- Big 2-3 word captions -->
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{end}" data-track-index="3" data-track-kind="captions" data-width="1080" data-height="1920" style="z-index: 4"></div>
      <audio id="voiceover" class="clip" src="assets/audio/voiceover.m4a" data-start="0" data-duration="{end}" data-track-index="4" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      // Frame 0 punches in, so the first thing the feed shows is motion.
      tl.fromTo("#film-wrap", {{ scale: 1.14 }}, {{ scale: 1, duration: 0.6, ease: "expo.out" }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
''')
    script = "\n".join(f"{i + 1}. {ln.get('cap', ln['say'])}" for i, ln in enumerate(lines))
    open(f"{proj}/BRIEF.md", "w").write(f'''---
workflow: general-video
flow: automation
storyboard: no
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: {end}s
angle: retention recut (v2) of videos/{cfg["src"]}
channel: Hollow Truth
file: "{file}"
---

## Intent

Retention recut of Hollow Truth File {file}. The original film's picture and sound bed are
retimed scene by scene to a tighter, payoff-first voiceover (natural voice, fast continuous read), with a
punch-in on frame 0, 2-3 word captions at 84px, and a last frame that matches the first
so the short loops. Built by tools/hollow-truth/recut_v2.py.

## Script (voiceover)

{script}

## Notes

- assets/footage/retimed.mp4 is rendered from videos/{cfg["src"]}; scene map old -> new:
  {", ".join(f"{a:g}->{b:.2f}" for a, b in zip(old, new))}
''')
    shutil.rmtree(work, ignore_errors=True)
    print(f"{file} v2: voice ends {vo_end:.2f}s, film {end}s -> {proj}")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        recut(f)
