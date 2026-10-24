"""Build the 2:30 landscape version of a Hollow Truth case file from topics_long.py.

    python3 tools/hollow-truth/build_long.py 005 [006 ...]

Writes videos/ht-<file>-<slug>-long/ (1920x1080, 150s): voiceover with chapter
breaks, captions, a wall of evidence the torch searches along a red string,
chapter cards, a closing question, sound bed, BRIEF.md and DESCRIPTION.md.
"""
import json
import math
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
from build import REPO, TEMPLATE, VOICE, SIZE, run, captions, item_svg, fit, esc, red, SCORE  # noqa: E402
from htlib import FLICK  # noqa: E402
from topics import TOPICS  # noqa: E402
from topics_long import LONG  # noqa: E402

W, H, DUR = 1920, 1080, 150.0
CH_GAP = 2.3          # silence held for a chapter card
END_LIMIT = 144.0     # voice must finish by here, leaving the closing card
COLS = 4


def record_long(beats, work, speed):
    return build.record({"lines": beats}, work, speed)


def place(beats, clips, gap):
    t, cards = 0.15, []
    for i, (b, c) in enumerate(zip(beats, clips)):
        if b.get("chapter") and i > 0:
            cards.append((round(t + 0.05, 2), b["chapter"]))
            t += CH_GAP
        c["start"] = round(t, 2)
        t += c["dur"] + gap
    return clips[-1]["start"] + clips[-1]["dur"], cards


def voice(topic, beats, proj, work):
    for speed in (1.0, 1.05, 1.1, 1.15):
        clips = record_long(beats, work, speed)
        # Spread the slack as breathing room between passages, aiming to finish near 142s.
        speech = sum(c["dur"] for c in clips) + CH_GAP * sum(1 for b in beats[1:] if b.get("chapter"))
        gap = min(1.3, max(0.4, (142.0 - 0.15 - speech) / (len(clips) - 1)))
        end, cards = place(beats, clips, gap)
        if end <= END_LIMIT:
            break
    else:
        raise SystemExit(f"{topic['file']} long: voiceover runs {end:.1f}s, trim the script")
    inputs, chains = [], []
    for i, c in enumerate(clips):
        inputs += ["-i", c["path"]]
        chains.append(f"[{i}]adelay={int(c['start'] * 1000)}:all=1[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(clips)))
    graph = ";".join(chains) + f";{mix}amix=inputs={len(clips)}:normalize=0,apad=whole_dur={DUR},atrim=0:{DUR}," \
        "asetrate=48000*0.93,aresample=48000,atempo=1.0753,aecho=0.8:0.5:60|140:0.22|0.12," \
        "lowpass=f=9000,loudnorm=I=-16:TP=-1.5:LRA=11"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-ar", "48000", "-ac", "1", f"{work}/vo.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/vo.wav", "-t", str(DUR), "-c:a", "aac", "-b:a", "160k",
         f"{proj}/assets/audio/voiceover.m4a"])
    return clips, end, cards, speed


# ---------------------------------------------------------------- the wall

def layout(n):
    pos = []
    for i in range(n):
        r, c = divmod(i, COLS)
        if r % 2:
            c = COLS - 1 - c
        pos.append((420 + c * 640, 500 + r * 720))
    return pos


def wall(topic, beats, clips, end_t, proj):
    items = [b["item"] for b in beats]
    n = len(items)
    pos = layout(n)
    rows = math.ceil(n / COLS)
    WW, WH = 420 * 2 + (COLS - 1) * 640, 500 * 2 + (rows - 1) * 720
    rot = [((i * 37) % 9 - 4) * 0.6 for i in range(n)]
    pins = [(pos[i][0], pos[i][1] - SIZE[items[i]["type"]][1] / 2 + 26) for i in range(n)]
    groups = "\n".join(
        f'          <g transform="translate({pos[i][0]} {pos[i][1]}) rotate({rot[i]:.1f})">{item_svg(it, topic["file"])}</g>'
        for i, it in enumerate(items))
    strings = "\n".join(
        f'          <line id="wall-string-{i}" x1="{pins[i][0]}" y1="{pins[i][1]}" x2="{pins[i + 1][0]}" y2="{pins[i + 1][1]}" '
        f'stroke="#b3241c" stroke-width="5" stroke-linecap="round"/>' for i in range(n - 1))
    zoom = {"photo": 1.0, "note": 1.25, "map": 1.12}

    def cam(i, push=0.0, sx=960, sy=470):
        s = zoom[items[i]["type"]] + push
        px, py = pos[i]
        return f"{{ x: {sx - 960 - s * (px - 960):.0f}, y: {sy - 540 - s * (py - 540):.0f}, scale: {s:.3f} }}"

    starts = [c["start"] for c in clips]
    js = []
    first_move = starts[1] - 0.7
    js.append(f'    tl.fromTo("#wall-world", {cam(0, 0.05, 1340, 500)}, {{ ...{cam(0, 0.1, 1340, 500)}, duration: {first_move:.2f}, ease: "none" }}, 0);')
    js.append(f'    tl.fromTo("#wall-torch", {{ x: 380, y: -40, scale: 1 }}, {{ x: 390, y: -30, scale: 1.02, duration: {first_move:.2f}, ease: "sine.inOut" }}, 0);')
    travel = []
    for i in range(1, n):
        t0 = starts[i] - 0.7
        nxt = starts[i + 1] - 0.7 if i + 1 < n else end_t + 0.1
        travel.append(t0)
        js.append(f'    tl.to("#wall-world", {{ ...{cam(i)}, duration: 0.8, ease: "power3.inOut" }}, {t0:.2f});')
        js.append(f'    tl.to("#wall-world", {{ ...{cam(i, 0.1)}, duration: {max(0.2, nxt - t0 - 0.8):.2f}, ease: "none" }}, {t0 + 0.8:.2f});')
        js.append(f'    tl.to("#wall-torch", {{ x: 0, y: -70, scale: 1, duration: 0.8, ease: "power3.inOut" }}, {t0:.2f});')
        length = math.dist(pins[i - 1], pins[i])
        js.append(f'    tl.fromTo("#wall-string-{i - 1}", {{ strokeDasharray: {length:.0f}, strokeDashoffset: {length:.0f}, opacity: 0 }}, '
                  f'{{ strokeDashoffset: 0, opacity: 1, duration: 0.7, ease: "power2.inOut" }}, {t0:.2f});')
    pull = end_t + 0.1
    s_end = round(min(0.6, 1700 / WW, 540 / WH), 3)
    ty = 790 - 540 - s_end * (WH / 2 - 540)
    tx = 960 - 960 - s_end * (WW / 2 - 960)
    js.append(f'    tl.to("#wall-world", {{ x: {tx:.0f}, y: {ty:.0f}, scale: {s_end}, duration: 1.2, ease: "power3.inOut" }}, {pull:.2f});')
    js.append(f'    tl.to("#wall-world", {{ x: {tx:.0f}, y: {ty:.0f}, scale: {s_end * 0.97:.3f}, duration: {DUR - pull - 1.2:.2f}, ease: "none" }}, {pull + 1.2:.2f});')
    js.append(f'    tl.to("#wall-torch", {{ x: -260, y: 220, scale: 1.9, duration: 1.2, ease: "power3.inOut" }}, {pull:.2f});')
    # The torch keeps sweeping the wall while the question holds.
    js.append(f'    tl.to("#wall-torch", {{ x: 260, y: 240, scale: 1.95, duration: {DUR - pull - 1.2:.2f}, ease: "sine.inOut" }}, {pull + 1.2:.2f});')
    html = f'''<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
      overflow: hidden;
      background: #120d08;
    }}
    #wall-world {{
      position: absolute;
      left: 0;
      top: 0;
      width: {WW}px;
      height: {WH}px;
      transform-origin: 960px 540px;
    }}
    #wall-world svg {{
      position: absolute;
      left: 0;
      top: 0;
      overflow: visible;
    }}
    #wall-torch {{
      position: absolute;
      left: -1920px;
      top: -1080px;
      width: 5760px;
      height: 3240px;
      background: radial-gradient(
        circle at 50% 50%,
        rgba(4, 3, 2, 0) 0px,
        rgba(4, 3, 2, 0.12) 260px,
        rgba(4, 3, 2, 0.66) 520px,
        rgba(4, 3, 2, 0.9) 760px
      );
    }}
  </style>
  <div id="root" data-composition-id="wall" data-width="{W}" data-height="{H}">
    <div id="wall-world" data-layout-allow-overflow data-layout-ignore>
      <svg width="{WW}" height="{WH}" viewBox="0 0 {WW} {WH}" xmlns="http://www.w3.org/2000/svg">
        <rect x="-4000" y="-4000" width="{WW + 8000}" height="{WH + 8000}" fill="#3a2a1a"/>
        <g id="wall-cork"></g>
{strings}
{groups}
      </svg>
    </div>
    <div id="wall-torch" data-layout-allow-overflow data-layout-ignore></div>
  </div>
  <script>
    (function () {{
      const NS = "http://www.w3.org/2000/svg";
      let seed = {int(topic["file"]) * 104729};
      const rnd = () => {{
        seed = (seed * 16807) % 2147483647;
        return seed / 2147483647;
      }};
      const cork = document.querySelector("#wall-cork");
      const tones = ["#2c1f13", "#4a3622", "#53402a", "#24190f"];
      for (let i = 0; i < 3200; i++) {{
        const c = document.createElementNS(NS, "circle");
        c.setAttribute("cx", (-1500 + rnd() * {WW + 3000}).toFixed(0));
        c.setAttribute("cy", (-1500 + rnd() * {WH + 3000}).toFixed(0));
        c.setAttribute("r", (1 + rnd() * 4).toFixed(1));
        c.setAttribute("fill", tones[Math.floor(rnd() * tones.length)]);
        cork.appendChild(c);
      }}
    }})();

    const tl = gsap.timeline({{ paused: true }});
    // Camera: along the red string, one piece of evidence per passage, then the whole wall.
{chr(10).join(js)}
    window.__timelines["wall"] = tl;
  </script>
</template>
'''
    open(f"{proj}/compositions/wall.html", "w").write(html)
    return travel, [s + 0.1 for s in starts[1:]], pull


# ---------------------------------------------------------------- titles and cards

CSS = '''    #root {
      position: absolute;
      inset: 0;
    }
    #root span {
      display: inline-block;
    }
    .t-display {
      position: absolute;
      font-family: var(--font-display, "League Gothic"), sans-serif;
      line-height: 1;
      color: var(--bone, #ddd3b4);
      text-shadow: 0 6px 0 rgba(0, 0, 0, 0.6);
    }
    .t-body {
      position: absolute;
      font-family: var(--font-body, "Oswald"), sans-serif;
      font-weight: 600;
      color: #ffffff;
      text-shadow: 0 3px 0 rgba(0, 0, 0, 0.7);
    }
'''


def tel(id, cls, start, dur, text, style):
    return (f'    <div id="{id}" class="{cls} clip" data-start="{start}" data-duration="{dur}" style="{style}">\n'
            f'      <span id="{id}-in">{text}</span>\n    </div>')


def comp(id, css, body, script):
    return f'''<template>
  <style>
{CSS}{css}  </style>
  <div id="root" data-composition-id="{id}" data-width="{W}" data-height="{H}">
{body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{FLICK}{script}
    window.__timelines["{id}"] = tl;
  </script>
</template>
'''


def scenes(topic, long, clips, cards, end_t, proj):
    out = []
    plain = lambda s: s.replace("*", "")
    hook_end = round(clips[1]["start"] - 0.7, 2)
    l1, l2 = long["hook"]
    out.append(("hook", 0, hook_end, comp("hook", "    #hook-k-in { opacity: 0.75; }\n", "\n".join([
        tel("hook-k", "t-body", 0, hook_end, f"HOLLOW TRUTH · FILE {topic['file']}",
            "left: 110px; top: 250px; font-weight: 400; font-size: 30px; letter-spacing: 0.42em; color: #ddd3b4;"),
        tel("hook-l1", "t-display", 0, hook_end, red(l1), f"left: 104px; top: 310px; font-size: {fit(plain(l1), 760, 150)}px;"),
        tel("hook-l2", "t-display", 0, hook_end, red(l2), f"left: 104px; top: 470px; font-size: {fit(plain(l2), 760, 150)}px;"),
    ]), f'''    flick(["#hook-l1-in", "#hook-l2-in"], 2.4);
    tl.to(["#hook-k-in", "#hook-l1-in", "#hook-l2-in"], {{ opacity: 0, duration: 0.25, ease: "power2.in" }}, {hook_end - 0.3:.2f});''')))
    # Chapter cards: a black frame, the chapter flickers on.
    for k, (t, name) in enumerate(cards, 1):
        cid = f"chapter{k}"
        d = round(CH_GAP - 0.2, 2)
        out.append((cid, t, d, comp(cid, f'''    #{cid}-bg {{ position: absolute; inset: 0; background: #050403; }}
    #{cid}-k-in, #{cid}-t-in {{ opacity: 0; }}
''', "\n".join([
            f'    <div id="{cid}-bg" class="clip" data-start="0" data-duration="{d}"></div>',
            tel(f"{cid}-k", "t-body", 0, d, f"CHAPTER {k}", "left: 0; width: 1920px; text-align: center; top: 400px; font-size: 40px; letter-spacing: 0.4em; color: #e0352b;"),
            tel(f"{cid}-t", "t-display", 0, d, esc(name), f"left: 0; width: 1920px; text-align: center; top: 470px; font-size: {fit(name, 1500, 170)}px;"),
        ]), f'''    flick("#{cid}-k-in", 0.15);
    flick("#{cid}-t-in", 0.35);
    tl.to("#{cid}-bg", {{ opacity: 0, duration: 0.25, ease: "power2.in" }}, {d - 0.3:.2f});
    tl.to(["#{cid}-k-in", "#{cid}-t-in"], {{ opacity: 0, duration: 0.2, ease: "power2.in" }}, {d - 0.35:.2f});''')))
    # Running chapter label, top left.
    marks = [(hook_end, "THE CASE")] + [(t + CH_GAP - 0.2, name) for t, name in cards]
    label_body, label_js = [], []
    for k, (t, name) in enumerate(marks):
        stop = cards[k][0] if k < len(cards) else end_t + 0.1
        txt = f"FILE {topic['file']} · {name}" if k == 0 else f"CHAPTER {k} · {name}"
        label_body.append(tel(f"label-{k}", "t-body", round(t, 2), round(stop - t, 2), esc(txt),
                              "left: 80px; top: 64px; font-weight: 400; font-size: 28px; letter-spacing: 0.3em; color: #ddd3b4;"))
        label_js.append(f'    tl.fromTo("#label-{k}-in", {{ opacity: 0 }}, {{ opacity: 0.8, duration: 0.4, ease: "power2.out" }}, {t + 0.1:.2f});')
    out.append(("labels", 0, DUR, comp("labels", "", "\n".join(label_body), "\n".join(label_js))))
    # The closing card.
    es = round(end_t + 0.1, 2)
    ed = round(DUR - es, 2)
    q = long["question"]
    out.append(("end", es, ed, comp("end", "    #end-k-in, #end-q-in, #end-m-in, #end-c-in { opacity: 0; }\n", "\n".join([
        tel("end-k", "t-body", 0, ed, f"CASE {topic['file']} · UNSOLVED", "left: 0; width: 1920px; text-align: center; top: 110px; font-size: 40px; letter-spacing: 0.22em;"),
        tel("end-q", "t-display", 0, ed, esc(q), f"left: 0; width: 1920px; text-align: center; top: 170px; font-size: {fit(q, 1500, 170)}px;"),
        tel("end-m", "t-body", 0, ed, "HOLLOW TRUTH", "left: 0; width: 1920px; text-align: center; top: 360px; font-size: 38px; letter-spacing: 0.5em; color: #ddd3b4;"),
        tel("end-c", "t-body", 0, ed, "COMMENT YOUR THEORY · SUBSCRIBE FOR MORE CASE FILES",
            "left: 0; width: 1920px; text-align: center; top: 418px; font-size: 30px; letter-spacing: 0.14em;"),
    ]), '''    flick("#end-k-in", 0.3);
    flick("#end-q-in", 0.8);
    tl.fromTo("#end-m-in", { opacity: 0 }, { opacity: 1, duration: 0.4, ease: "power2.out" }, 1.1);
    flick("#end-c-in", 2.0);''')))
    for id, *_rest, html in out:
        open(f"{proj}/compositions/{id}.html", "w").write(html)
    return out, es + 0.8


def write_index(proj, scenes_, caps, dips):
    def host(id, st, d, ti, kind, z):
        return f'''      <div
        id="{id}"
        data-composition-id="{id}"
        data-composition-src="compositions/{id}.html"
        data-start="{st}"
        data-duration="{d}"
        data-track-index="{ti}"
        data-track-kind="{kind}"
        data-width="{W}"
        data-height="{H}"
        style="z-index: {z}"
      ></div>
'''
    hosts = "".join(host(id, st, d, 2, "graphics", 3) for id, st, d, _ in scenes_)
    open(f"{proj}/index.html", "w").write(f'''<!doctype html>
<html
  lang="en"
  data-resolution="landscape"
  data-composition-variables='[
    {{"id":"accent","type":"color","label":"Accent (warning red)","default":"#e0352b"}},
    {{"id":"bone","type":"color","label":"Title ink","default":"#ddd3b4"}}
  ]'
>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      :root {{
        --accent: #e0352b;
        --bone: #ddd3b4;
        --font-display: "League Gothic", sans-serif;
        --font-body: "Oswald", sans-serif;
      }}
      * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }}
      html,
      body {{
        margin: 0;
        width: {W}px;
        height: {H}px;
        overflow: hidden;
        background: #120d08;
      }}
      #root {{
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: #120d08;
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{DUR:g}"
      data-width="{W}"
      data-height="{H}"
    >
      <!-- The evidence wall: one corkboard the torch searches for the whole film -->
{host("wall", 0, f"{DUR:g}", 1, "graphics", 1)}
      <!-- Night mood: fog, vignette, grain, projector dips at each move -->
{host("mood", 0, f"{DUR:g}", 6, "graphics", 2)}
      <!-- Hook, chapter cards, running chapter label, closing card -->
{hosts}
      <!-- Burned-in captions -->
{host("captions", 0, f"{DUR:g}", 3, "captions", 4)}
      <audio id="voiceover" class="clip" src="assets/audio/voiceover.m4a" data-start="0" data-duration="{DUR:g}" data-track-index="4" data-volume="1"></audio>
      <audio id="bed" class="clip" src="assets/audio/bed.m4a" data-start="0" data-duration="{DUR:g}" data-track-index="5" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
''')
    divs = "\n".join(f'    <div id="cap-{i}" class="cap clip" data-start="{s}" data-duration="{round(e - s, 2)}"><span id="cap-{i}-in">{esc(t)}</span></div>'
                     for i, (s, e, t) in enumerate(caps))
    tw = "\n".join(f'    pop("#cap-{i}-in", {s});' for i, (s, e, t) in enumerate(caps))
    open(f"{proj}/compositions/captions.html", "w").write(f'''<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
    }}
    .cap {{
      position: absolute;
      left: 0;
      top: 905px;
      width: {W}px;
      text-align: center;
      overflow: visible;
    }}
    .cap span {{
      display: inline-block;
      font-family: var(--font-body, "Oswald"), sans-serif;
      font-weight: 600;
      font-size: 56px;
      line-height: 1.1;
      color: #ffffff;
      -webkit-text-stroke: 11px #050e10;
      paint-order: stroke fill;
    }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
{divs}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const pop = (sel, at) =>
      tl.fromTo(sel, {{ opacity: 0, y: 8 }}, {{ opacity: 1, y: 0, duration: 0.12, ease: "power3.out" }}, at);
{tw}
    window.__timelines["captions"] = tl;
  </script>
</template>
''')
    mood = open(os.path.join(TEMPLATE, "compositions/mood.html")).read()
    mood = (mood.replace('data-width="1080" data-height="1920"', f'data-width="{W}" data-height="{H}"')
            .replace("left: -540px;\n      top: -960px;\n      width: 2160px;\n      height: 3840px;",
                     "left: -960px;\n      top: -540px;\n      width: 3840px;\n      height: 2160px;")
            .replace("top: 1000px;", "top: 500px;")
            .replace("x: 900, y: -120, duration: 20", "x: 1500, y: -100, duration: 150")
            .replace("x: -800, y: -200, duration: 20", "x: -1400, y: -150, duration: 150")
            .replace("for (let f = 0; f < 300; f++)", "for (let f = 0; f < 2250; f++)"))
    mood = re.sub(r"\[[0-9., ]+\]\.forEach\(\(at\)", f"[{', '.join(f'{d:.2f}' for d in dips)}].forEach((at)", mood)
    open(f"{proj}/compositions/mood.html", "w").write(mood)


def score(topic, proj, work, travel, arrive, cards, q_time):
    src = (SCORE.replace("N = int(SR * 20.0)", f"N = int(SR * {DUR})")
           .replace("20s case-board bed", "150s case-wall bed")
           .replace("SEED", str(int(topic["file"]) + 500))
           .replace("TRAVEL_TIMES", json.dumps([round(x, 2) for x in travel] + [round(q_time - 1.0, 2)]))
           .replace("ARRIVE_TIMES", json.dumps([round(x, 2) for x in arrive]))
           .replace("QUESTION_TIME", f"{q_time:.2f}")
           .replace("n = at(1.3); tt = np.arange(n) / SR\nriser",
                    f"# Each chapter card lands with a low hit.\nfor ch in {json.dumps([c for c, _ in cards])}:\n"
                    "    add(hit(1.4, 90, 40), ch + 0.15, 0.7)\nn = at(1.3); tt = np.arange(n) / SR\nriser"))
    open(f"{proj}/scripts/score.py", "w").write(src)
    run([sys.executable, f"{proj}/scripts/score.py", f"{work}/bed.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/bed.wav", "-af", "loudnorm=I=-23:TP=-2", "-ar", "48000",
         "-c:a", "aac", "-b:a", "192k", f"{proj}/assets/audio/bed.m4a"])


def stamp(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def docs(topic, long, proj, cards, speed):
    chapters = ["00:00 The case"] + [f"{stamp(t)} {name.title()}" for t, name in cards]
    body = "\n".join(ln for ln in long["yt_body"].split("\n") if not re.match(r"^\d\d:\d\d ", ln))
    body = re.sub(r"\n{3,}", "\n\n", body.replace("\n\nWhat", "\n\n" + "\n".join(chapters) + "\n\nWhat", 1))
    desc = (f"**Title:** {long['yt_title']}\n\n{body}\n\n"
            f"📖 Learn more: {topic['wiki']}\n"
            f"🔔 Subscribe to Hollow Truth for more strange events, unsolved mysteries and places you were never meant to see.\n\n"
            f"{topic['tags'].replace(' #Shorts', '')}\n\n"
            f"**Cover image prompt:**\n\n{long['cover']}\n")
    open(f"{proj}/DESCRIPTION.md", "w").write(desc)
    script = "\n".join(f"{i + 1}. {('[' + b['chapter'] + '] ') if b.get('chapter') else ''}{b.get('cap', b['say'])}"
                       for i, b in enumerate(long["beats"]))
    open(f"{proj}/BRIEF.md", "w").write(f'''---
workflow: general-video
flow: automation
storyboard: no
message: "{topic['title']}: {long['question'].capitalize()}"
destination: youtube
aspect: 1920x1080
language: en
audience: US
length: 150s
angle: mystery / unexplained long-form (case-wall series)
channel: Hollow Truth
file: "{topic['file']}"
---

## Intent

The 2:30 version of Hollow Truth File {topic['file']}: {topic['title']}. A torch searches a wall of
evidence; each passage of the voiceover lands on one piece, a red string pulled to the next.
Chapter cards split it into the case, what happened, the clues and the theories. It ends on the
whole wall and "{long['question']}"

## Script (voiceover)

{script}

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS ({VOICE}, {speed}x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py, -23 LUFS.

## Notes

- Built by tools/hollow-truth/build_long.py from tools/hollow-truth/topics_long.py.
- Cover prompt for the thumbnail is in DESCRIPTION.md.
''')


def build_long(file):
    topic = next(t for t in TOPICS if t["file"] == file)
    long = LONG[file]
    name = f"ht-{file}-{topic['slug']}-long"
    proj = os.path.join(REPO, "videos", name)
    if os.path.exists(proj):
        shutil.rmtree(proj)
    for d in ("assets/audio", "assets/vendor", "compositions", "scripts", "renders"):
        os.makedirs(f"{proj}/{d}", exist_ok=True)
    for f in ("hyperframes.json", "CLAUDE.md", "AGENTS.md", ".gitignore", "assets/vendor/gsap.min.js"):
        shutil.copy(os.path.join(TEMPLATE, f), f"{proj}/{f}")
    pkg = json.load(open(os.path.join(TEMPLATE, "package.json")))
    pkg["name"] = name
    json.dump(pkg, open(f"{proj}/package.json", "w"), indent=2)
    json.dump({"id": name, "name": name}, open(f"{proj}/meta.json", "w"), indent=2)
    work = os.path.join("/tmp", f"ht-work-{file}-long")
    os.makedirs(work, exist_ok=True)
    beats = long["beats"]
    clips, end_t, cards, speed = voice(topic, beats, proj, work)
    travel, arrive, pull = wall(topic, beats, clips, end_t, proj)
    sc, q_time = scenes(topic, long, clips, cards, end_t, proj)
    caps = captions({"lines": beats}, clips, size=6)
    write_index(proj, [(id, st, d, None) for id, st, d, _ in sc], caps, sorted(travel + [c for c, _ in cards] + [pull]))
    score(topic, proj, work, travel, arrive, cards, q_time)
    docs(topic, long, proj, cards, speed)
    print(f"{file} long: voice ends {end_t:.1f}s at {speed}x, {len(cards)} chapters at "
          f"{', '.join(stamp(t) for t, _ in cards)} -> {proj}")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        build_long(f)
