"""Build the retention cut (v2) of a case-board short from topics_v2.py.

    python3 tools/hollow-truth/build_v2.py 005 [006 ...]

Payoff-first script read 12% faster (~15s), a slam-in on frame 0, a move every
~2-3s, 2-3 word captions at 84px, and a last move back to the first piece of
evidence so the short loops. Rebuilds videos/ht-<file>-<slug>/ in place.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
from build import (VOICE, POS_X, ROT, SIZE, run, captions, item_svg, fit, esc, red, SCORE,  # noqa: E402
                   scaffold, description)
from htlib import el, write_project  # noqa: E402
from topics import TOPICS  # noqa: E402
from topics_v2 import V2  # noqa: E402

TEMPO = 1.12
GAP = 0.12
VO_LIMIT = 15.6


def voice(topic, proj, work):
    for speed in (1.1, 1.16):
        clips = build.record(topic, work, speed)
        t = 0.05
        for c in clips:
            c["start"] = round(t, 3)
            t += c["dur"] + GAP
        raw_end = clips[-1]["start"] + clips[-1]["dur"]
        if raw_end / TEMPO <= VO_LIMIT:
            break
    end = round(raw_end / TEMPO + 1.4, 1)
    inputs, chains = [], []
    for i, c in enumerate(clips):
        inputs += ["-i", c["path"]]
        chains.append(f"[{i}]adelay={int(c['start'] * 1000)}:all=1[a{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(clips))) + \
        f"amix=inputs={len(clips)}:normalize=0,asetrate=48000*0.93,aresample=48000,atempo={1.0753 * TEMPO:.4f}," \
        f"aecho=0.8:0.5:60|140:0.2|0.1,lowpass=f=9000,apad=whole_dur={end},atrim=0:{end},loudnorm=I=-15:TP=-1.5:LRA=11"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-ar", "48000", "-ac", "1", f"{work}/vo.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/vo.wav", "-c:a", "aac", "-b:a", "160k", f"{proj}/assets/audio/voiceover.m4a"])
    # Everything downstream runs on the sped-up clock.
    for c in clips:
        c["start"] = round(c["start"] / TEMPO, 3)
        c["dur"] = c["dur"] / TEMPO
        c["pauses"] = [(a / TEMPO, b / TEMPO) for a, b in c["pauses"]]
    return clips, raw_end / TEMPO, end, speed


def board(topic, clips, vo_end, end, proj):
    items = [ln["item"] for ln in topic["lines"]]
    n = len(items)
    ys = [560 + i * 620 for i in range(n)]
    xs = POS_X[:n]
    H = ys[-1] + 560
    pins = [(xs[i], ys[i] - SIZE[items[i]["type"]][1] / 2 + 26) for i in range(n)]
    groups = "\n".join(
        f'          <g transform="translate({xs[i]} {ys[i]}) rotate({ROT[i]})">{item_svg(it, topic["file"])}</g>'
        for i, it in enumerate(items))
    strings = "\n".join(
        f'          <line id="board-string-{i}" x1="{pins[i][0]}" y1="{pins[i][1]}" x2="{pins[i + 1][0]}" y2="{pins[i + 1][1]}" '
        f'stroke="#b3241c" stroke-width="5" stroke-linecap="round"/>' for i in range(n - 1))
    zoom = {"photo": 1.1, "note": 1.22, "map": 1.15}
    aim = {"photo": 860, "note": 900, "map": 890}

    def focus(i, push=0.0):
        k = items[i]["type"]
        s = zoom[k] + push
        return f"cam({xs[i]}, {ys[i] + (960 - aim[k]) / s:.0f}, {s:.2f})"

    starts = [c["start"] for c in clips]
    js = []
    # Frame 0 slams in on the first piece of evidence, then keeps pushing.
    js.append(f'    tl.fromTo("#board-world", {focus(0, 0.1)}, {{ ...{focus(0)}, duration: 0.55, ease: "expo.out" }}, 0);')
    js.append(f'    tl.to("#board-world", {{ ...{focus(0, 0.06)}, duration: {starts[1] - 0.3 - 0.55:.2f}, ease: "none" }}, 0.55);')
    travel, arrive = [], [0.02]
    for i in range(1, n):
        t0 = starts[i] - 0.3
        nxt = starts[i + 1] - 0.3 if i + 1 < n else vo_end + 0.05
        travel.append(t0)
        arrive.append(t0 + 0.45)
        js.append(f'    tl.to("#board-world", {{ ...{focus(i)}, duration: 0.45, ease: "power3.inOut" }}, {t0:.2f});')
        js.append(f'    tl.to("#board-world", {{ ...{focus(i, 0.06)}, duration: {max(0.2, nxt - t0 - 0.45):.2f}, ease: "none" }}, {t0 + 0.45:.2f});')
        length = ((pins[i - 1][0] - pins[i][0]) ** 2 + (pins[i - 1][1] - pins[i][1]) ** 2) ** 0.5
        js.append(f'    tl.fromTo("#board-string-{i - 1}", {{ strokeDasharray: {length:.0f}, strokeDashoffset: {length:.0f}, opacity: 0 }}, '
                  f'{{ strokeDashoffset: 0, opacity: 1, duration: 0.4, ease: "power2.inOut" }}, {t0:.2f});')
    # Back to the first piece of evidence: the last frame leads straight into the first.
    back = vo_end + 0.05
    travel.append(back)
    js.append(f'    tl.to("#board-world", {{ ...{focus(0)}, duration: 0.7, ease: "power3.inOut" }}, {back:.2f});')
    js.append(f'    tl.to("#board-world", {{ ...{focus(0, 0.06)}, duration: {end - back - 0.7:.2f}, ease: "none" }}, {back + 0.7:.2f});')
    src = f'''<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      overflow: hidden;
      background: #120d08;
    }}
    #board-world {{
      position: absolute;
      left: 0;
      top: 0;
      width: 1080px;
      height: {H}px;
      transform-origin: 540px 960px;
    }}
    #board-world svg {{
      position: absolute;
      left: 0;
      top: 0;
      overflow: visible;
    }}
    #board-torch {{
      position: absolute;
      left: -1080px;
      top: -1920px;
      width: 3240px;
      height: 5760px;
      background: radial-gradient(
        circle at 50% 50%,
        rgba(4, 3, 2, 0) 0px,
        rgba(4, 3, 2, 0.12) 240px,
        rgba(4, 3, 2, 0.62) 450px,
        rgba(4, 3, 2, 0.88) 620px
      );
    }}
  </style>
  <div id="root" data-composition-id="board" data-width="1080" data-height="1920">
    <div id="board-world" data-layout-allow-overflow data-layout-ignore>
      <svg width="1080" height="{H}" viewBox="0 0 1080 {H}" xmlns="http://www.w3.org/2000/svg">
        <rect x="-3000" y="-3000" width="7080" height="{H + 6000}" fill="#3a2a1a"/>
        <g id="board-cork"></g>
{strings}
{groups}
      </svg>
    </div>
    <div id="board-torch" data-layout-allow-overflow data-layout-ignore></div>
  </div>
  <script>
    (function () {{
      const NS = "http://www.w3.org/2000/svg";
      let seed = {int(topic["file"]) * 7919};
      const rnd = () => {{
        seed = (seed * 16807) % 2147483647;
        return seed / 2147483647;
      }};
      const cork = document.querySelector("#board-cork");
      const tones = ["#2c1f13", "#4a3622", "#53402a", "#24190f"];
      for (let i = 0; i < 1400; i++) {{
        const c = document.createElementNS(NS, "circle");
        c.setAttribute("cx", (-700 + rnd() * 2480).toFixed(0));
        c.setAttribute("cy", (-900 + rnd() * {H + 1800}).toFixed(0));
        c.setAttribute("r", (1 + rnd() * 4).toFixed(1));
        c.setAttribute("fill", tones[Math.floor(rnd() * tones.length)]);
        cork.appendChild(c);
      }}
    }})();

    const tl = gsap.timeline({{ paused: true }});
    const cam = (px, py, s) => ({{ x: -s * (px - 540), y: -s * (py - 960), scale: s }});
    tl.fromTo("#board-torch", {{ x: 0, y: -60, scale: 0.9 }}, {{ x: 0, y: -60, scale: 1.05, duration: {end:.2f}, ease: "none" }}, 0);
    // Camera: slam in, then a fast move to each piece of evidence, then back to the first.
{chr(10).join(js)}
    window.__timelines["board"] = tl;
  </script>
</template>
'''
    open(f"{proj}/compositions/board.html", "w").write(src)
    return travel, arrive


def titles(topic, v2, clips, vo_end, end):
    hook_end = round(clips[1]["start"] - 0.3, 2)
    l1, l2 = v2["hook"]
    plain = lambda s: s.replace("*", "")
    K = "top: 178px; font-weight: 400; font-size: 32px; letter-spacing: 0.42em; color: #ddd3b4;"
    hook = ("hook", 0, hook_end, "", "\n".join([
        el("hook-kicker", "t-body", 0, hook_end, f"HOLLOW TRUTH · FILE {topic['file']}", K),
        el("hook-l1", "t-display", 0, hook_end, red(l1), f"top: 230px; font-size: {fit(plain(l1), 920, 150)}px;"),
        el("hook-l2", "t-display", 0, hook_end, red(l2), f"top: 385px; font-size: {fit(plain(l2), 920, 150)}px;"),
    ]), f'''    tl.fromTo(["#hook-l1-in", "#hook-l2-in"], {{ scale: 1.08 }}, {{ scale: 1, duration: 0.5, ease: "expo.out" }}, 0);
    tl.to(["#hook-kicker-in", "#hook-l1-in", "#hook-l2-in"], {{ opacity: 0, duration: 0.12, ease: "power2.in" }}, {hook_end - 0.14:.2f});''')
    qs = round(vo_end + 0.1, 2)
    q = v2["question"]
    ask = ("ask", qs, round(end - qs, 2), "", el("ask-l", "t-display", 0, round(end - qs, 2), esc(q), f"top: 280px; font-size: {fit(q, 940, 170)}px;"),
           '''    tl.fromTo("#ask-l-in", { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, duration: 0.14, ease: "power4.out" }, 0.02);''')
    return [hook, ask], qs


def build_v2(file):
    base = next(t for t in TOPICS if t["file"] == file)
    v2 = V2[file]
    topic = dict(base, lines=v2["lines"], question=v2["question"])
    proj = scaffold(topic)
    work = os.path.join("/tmp", f"ht-work-{file}-v2")
    os.makedirs(work, exist_ok=True)
    clips, vo_end, end, speed = voice(topic, proj, work)
    travel, arrive = board(topic, clips, vo_end, end, proj)
    scenes, q_time = titles(topic, v2, clips, vo_end, end)
    write_project(proj, "board", "The case board: slam in, one fast move per line, back to the start so it loops", "#120d08",
                  scenes, captions(topic, clips, size=3), [round(x, 2) for x in travel])
    cp = f"{proj}/compositions/captions.html"
    s = open(cp).read().replace("font-size: 66px;", "font-size: 84px;").replace("-webkit-text-stroke: 12px", "-webkit-text-stroke: 14px").replace("top: 1190px;", "top: 1150px;")
    open(cp, "w").write(s)
    ip = f"{proj}/index.html"
    s = open(ip).read().replace('data-duration="20"', f'data-duration="{end}"')
    open(ip, "w").write(s)
    src = (SCORE.replace("N = int(SR * 20.0)", f"N = int(SR * {end})")
           .replace("20s case-board bed", f"{end}s case-board retention cut")
           .replace("SEED", str(int(file) + 900))
           .replace("TRAVEL_TIMES", str([round(x, 2) for x in travel]))
           .replace("ARRIVE_TIMES", str([round(x, 2) for x in arrive]))
           .replace("QUESTION_TIME", f"{q_time:.2f}"))
    open(f"{proj}/scripts/score.py", "w").write(src)
    run([sys.executable, f"{proj}/scripts/score.py", f"{work}/bed.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/bed.wav", "-af", "loudnorm=I=-22:TP=-2", "-ar", "48000",
         "-c:a", "aac", "-b:a", "192k", f"{proj}/assets/audio/bed.m4a"])
    script = "\n".join(f"{i + 1}. {ln.get('cap', ln['say'])}" for i, ln in enumerate(v2["lines"]))
    open(f"{proj}/BRIEF.md", "w").write(f'''---
workflow: general-video
flow: automation
storyboard: no
message: "{topic['title']}: {v2['question'].capitalize()}"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: {end}s
angle: mystery short, retention cut (v2)
channel: Hollow Truth
file: "{file}"
---

## Intent

Retention cut of Hollow Truth File {file}: {topic['title']}. File 001's first upload kept 33.8% of
viewers past the swipe, so this version opens on the payoff, slams in on frame 0, moves every 2-3s,
shows 2-3 word captions, and returns to the first piece of evidence so it loops.

## Script (voiceover)

{script}

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS ({VOICE}, {speed}x, then sped up {TEMPO}x), pitched down 7%, -15 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py, -22 LUFS.

## Notes

- Built by tools/hollow-truth/build_v2.py from tools/hollow-truth/topics_v2.py.
''')
    open(f"{proj}/DESCRIPTION.md", "w").write(description(base))
    print(f"{file} v2: voice ends {vo_end:.2f}s at {speed}x/{TEMPO}, film {end}s -> {proj}")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        build_v2(f)
