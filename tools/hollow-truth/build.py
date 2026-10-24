"""Build a Hollow Truth "case board" short from a topic in topics.py.

    python3 tools/hollow-truth/build.py 005 [006 ...]   # or: all

Writes videos/ht-<file>-<slug>/: voiceover, captions, evidence board, titles,
sound bed, BRIEF.md and DESCRIPTION.md. Render with render.sh.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from htlib import el, write_project  # noqa: E402
from icons import icon  # noqa: E402
from topics import TOPICS  # noqa: E402

CLI = ["npx", "--yes", "hyperframes@0.8.191"]
TEMPLATE = os.path.join(REPO, "videos", "dyatlov-pass-short")
VOICE = "am_michael"
GAP = 0.32
VO_LIMIT = 17.45


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout)


def pauses(path):
    err = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=noise=-35dB:d=0.12", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    return list(zip(starts, ends))


# ---------------------------------------------------------------- voice

def record(topic, work, speed):
    clips = []
    for i, line in enumerate(topic["lines"]):
        raw, cut = f"{work}/p{i}.wav", f"{work}/t{i}.wav"
        run(CLI + ["tts", line["say"], "-v", VOICE, "-s", str(speed), "-o", raw, "--json"])
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
             "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
             "silenceremove=start_periods=1:start_threshold=-45dB,areverse", "-ar", "48000", cut])
        d = duration(cut)
        clips.append({"path": cut, "dur": d, "pauses": [p for p in pauses(cut) if p[1] < d - 0.05]})
    return clips


def place(clips, gap):
    t = 0.15
    for c in clips:
        c["start"] = round(t, 2)
        t += c["dur"] + gap
    return clips[-1]["start"] + clips[-1]["dur"]


def voice(topic, proj, work):
    for speed in (1.05, 1.12, 1.18):
        clips = record(topic, work, speed)
        for gap in (GAP, 0.24):
            end = place(clips, gap)
            if end <= VO_LIMIT:
                break
        if end <= VO_LIMIT:
            break
    else:
        raise SystemExit(f"{topic['file']}: voiceover runs {end:.2f}s, trim the script")
    inputs, chains = [], []
    for i, c in enumerate(clips):
        inputs += ["-i", c["path"]]
        chains.append(f"[{i}]adelay={int(c['start'] * 1000)}:all=1[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(clips)))
    graph = ";".join(chains) + f";{mix}amix=inputs={len(clips)}:normalize=0,apad=whole_dur=20,atrim=0:20," \
        "asetrate=48000*0.93,aresample=48000,atempo=1.0753,aecho=0.8:0.5:60|140:0.22|0.12," \
        "lowpass=f=9000,loudnorm=I=-16:TP=-1.5:LRA=11"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-ar", "48000", "-ac", "1", f"{work}/vo.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/vo.wav", "-t", "20", "-c:a", "aac", "-b:a", "160k",
         f"{proj}/assets/audio/voiceover.m4a"])
    return clips, end, speed


# ---------------------------------------------------------------- captions

def weight(word):
    w = word.strip(".,?!:;“”\"")
    if re.fullmatch(r"[$0-9,.:%~×²+–-]+", w) and any(ch.isdigit() for ch in w):
        return 5 * len(re.sub(r"\D", "", w)) + 2
    return len(w) + 1


def chunks(words, size=4):
    if len(words) <= size:
        return [words]
    n = math.ceil(len(words) / size)
    per = math.ceil(len(words) / n)
    return [words[i:i + per] for i in range(0, len(words), per)]


def captions(topic, clips):
    out = []
    for line, c in zip(topic["lines"], clips):
        text = line.get("cap", line["say"])
        phrases = [p.strip() for p in re.split(r"(?<=[,.?!:])\s+", text) if p.strip()]
        inner = c["pauses"]
        if len(phrases) - 1 == len(inner):
            bounds = [0.0] + [p for pair in inner for p in pair] + [c["dur"]]
            spans = [(bounds[2 * k], bounds[2 * k + 1]) for k in range(len(phrases))]
        else:
            ws = [sum(weight(w) for w in p.split()) for p in phrases]
            tot, acc, spans = sum(ws), 0.0, []
            for w in ws:
                spans.append((c["dur"] * acc / tot, c["dur"] * (acc + w) / tot))
                acc += w
        for phrase, (a, b) in zip(phrases, spans):
            groups = chunks(phrase.split())
            ws = [sum(weight(w) for w in g) for g in groups]
            tot, acc = sum(ws), 0.0
            for g, w in zip(groups, ws):
                s = c["start"] + a + (b - a) * acc / tot
                e = c["start"] + a + (b - a) * (acc + w) / tot
                out.append((round(s, 2), round(e + 0.05, 2), " ".join(g)))
                acc += w
    # A group never outlives the start of the next one.
    return [(s, min(e, out[k + 1][0]) if k + 1 < len(out) else e, txt) for k, (s, e, txt) in enumerate(out)]


# ---------------------------------------------------------------- board

POS_X = [400, 680, 400, 680, 400, 680]
ROT = [-2.5, 2.0, -1.5, 2.5, -2.0, 1.5]
SIZE = {"photo": (480, 560), "note": (520, 340), "map": (520, 420)}


def fit(text, width, max_px, em=0.42):
    return int(min(max_px, width / (em * max(len(text), 1))))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def item_svg(it, file):
    w, h = SIZE[it["type"]]
    shadow = f'<rect x="{-w / 2 + 10}" y="{-h / 2 + 12}" width="{w}" height="{h}" fill="#000" opacity="0.45"/>'
    if it["type"] == "photo":
        body = (f'<rect x="-240" y="-280" width="480" height="560" fill="#e7e1d1"/>'
                f'<rect x="-220" y="-260" width="440" height="420" fill="#1b1f24"/>'
                f'<g transform="translate(-220 -260)">{icon(it["icon"])}</g>'
                f'<text x="0" y="228" text-anchor="middle" font-family="Oswald, sans-serif" font-weight="600" '
                f'font-size="{fit(it["label"], 420, 34, 0.5)}" fill="#2a261f" letter-spacing="1">{esc(it["label"])}</text>')
    elif it["type"] == "note":
        body = (f'<rect x="-260" y="-170" width="520" height="340" fill="#d9d2bd"/>'
                f'<text x="-232" y="-122" font-family="IBM Plex Mono, monospace" font-size="22" fill="#7a7363">EVIDENCE · {file}</text>'
                f'<text x="0" y="30" text-anchor="middle" font-family="League Gothic, sans-serif" '
                f'font-size="{fit(it["text"], 470, 140)}" fill="#1d1a14">{esc(it["text"])}</text>'
                f'<text x="0" y="112" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="26" fill="#4a4537">{esc(it["sub"])}</text>')
    else:
        body = (f'<rect x="-260" y="-210" width="520" height="420" fill="#d6cdb2"/>'
                + "".join(f'<path d="M -240 {y} C -120 {y - 8} 0 {y + 8} 240 {y}" stroke="#b9c3be" stroke-width="2" fill="none"/>'
                          for y in range(-150, 140, 28))
                + '<path d="M -150 -90 C -60 -150 60 -120 120 -60 C 170 -10 150 70 70 100 C -10 130 -110 110 -150 40 C -180 -10 -190 -60 -150 -90 Z" '
                  'fill="#b9ab86" stroke="#6b5d41" stroke-width="4"/>'
                + '<path d="M 10 -20 L 60 30 M 60 -20 L 10 30" stroke="#c0281f" stroke-width="10" stroke-linecap="round"/>'
                + f'<text x="-232" y="-166" font-family="IBM Plex Mono, monospace" font-size="24" fill="#5d5442">{esc(it["sub"])}</text>'
                + f'<text x="0" y="180" text-anchor="middle" font-family="Oswald, sans-serif" font-weight="600" '
                  f'font-size="{fit(it["label"], 460, 38, 0.5)}" fill="#2a261f">{esc(it["label"])}</text>')
    pin = (f'<circle cx="3" cy="{-h / 2 + 30}" r="14" fill="#000" opacity="0.4"/>'
           f'<circle cx="0" cy="{-h / 2 + 26}" r="14" fill="#c0281f"/>'
           f'<circle cx="-4" cy="{-h / 2 + 22}" r="4" fill="#f08a80"/>')
    return shadow + body + pin


def board(topic, clips, end_t, proj):
    items = [ln["item"] for ln in topic["lines"]]
    n = len(items)
    ys = [560 + i * 620 for i in range(n)]
    xs = POS_X[:n]
    H = ys[-1] + 560
    pins = [(xs[i], ys[i] - SIZE[items[i]["type"]][1] / 2 + 26) for i in range(n)]
    groups = "\n".join(
        f'          <g id="board-item-{i}" transform="translate({xs[i]} {ys[i]}) rotate({ROT[i]})">{item_svg(it, topic["file"])}</g>'
        for i, it in enumerate(items))
    strings = "\n".join(
        f'          <line id="board-string-{i}" x1="{pins[i][0]}" y1="{pins[i][1]}" x2="{pins[i + 1][0]}" y2="{pins[i + 1][1]}" '
        f'stroke="#b3241c" stroke-width="5" stroke-linecap="round"/>' for i in range(n - 1))
    starts = [c["start"] for c in clips]
    cam_js, torch_js, str_js = [], [], []
    # Each print sits above the caption band: photos smaller and higher, cards a little larger.
    zoom = {"photo": 1.1, "note": 1.22, "map": 1.15}
    aim = {"photo": 860, "note": 900, "map": 890}
    def focus(i, push=0.0):
        k = items[i]["type"]
        s = zoom[k] + push
        return f"cam({xs[i]}, {ys[i] + (960 - aim[k]) / s:.0f}, {s:.2f})"
    cam_js.append(f'    tl.fromTo("#board-world", {focus(0)}, {{ ...{focus(0, 0.04)}, duration: {starts[1] - 0.45:.2f}, ease: "none" }}, 0);')
    for i in range(1, n):
        t0 = starts[i] - 0.45
        nxt = starts[i + 1] - 0.45 if i + 1 < n else end_t + 0.05
        cam_js.append(f'    tl.to("#board-world", {{ ...{focus(i)}, duration: 0.6, ease: "power3.inOut" }}, {t0:.2f});')
        cam_js.append(f'    tl.to("#board-world", {{ ...{focus(i, 0.04)}, duration: {max(0.2, nxt - t0 - 0.6):.2f}, ease: "none" }}, {t0 + 0.6:.2f});')
        length = math.dist(pins[i - 1], pins[i])
        str_js.append(f'    tl.fromTo("#board-string-{i - 1}", {{ strokeDasharray: {length:.0f}, strokeDashoffset: {length:.0f}, opacity: 0 }}, '
                      f'{{ strokeDashoffset: 0, opacity: 1, duration: 0.55, ease: "power2.inOut" }}, {t0:.2f});')
        torch_js.append(f'    tl.to("#board-torch", {{ x: 0, y: -60, scale: 1, duration: 0.6, ease: "power3.inOut" }}, {t0:.2f});')
    pull = end_t + 0.05
    # The whole case fits under the closing question (frame y 600-1880).
    top, bot = ys[0] - 300, ys[-1] + 300
    s_end = round(min(0.55, 1280 / (bot - top)), 3)
    py_end = (top + bot) / 2 - (1240 - 960) / s_end
    cam_js.append(f'    tl.to("#board-world", {{ ...cam(540, {py_end:.0f}, {s_end}), duration: 0.9, ease: "power3.inOut" }}, {pull:.2f});')
    cam_js.append(f'    tl.to("#board-world", {{ ...cam(540, {py_end:.0f}, {s_end * 0.97:.3f}), duration: {20 - pull - 0.9:.2f}, ease: "none" }}, {pull + 0.9:.2f});')
    torch_js.append(f'    tl.to("#board-torch", {{ x: 0, y: 200, scale: 2.4, duration: 0.9, ease: "power3.inOut" }}, {pull:.2f});')
    html = f'''<template>
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
        rgba(4, 3, 2, 0.12) 220px,
        rgba(4, 3, 2, 0.66) 430px,
        rgba(4, 3, 2, 0.9) 600px
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
    tl.fromTo("#board-torch", {{ x: 0, y: -60, scale: 1 }}, {{ x: 12, y: -50, scale: 1.02, duration: {starts[1] - 0.45:.2f}, ease: "sine.inOut" }}, 0);
    // Camera: from one piece of evidence to the next along the red string, then the whole case.
{chr(10).join(cam_js)}
{chr(10).join(str_js)}
{chr(10).join(torch_js)}
    window.__timelines["board"] = tl;
  </script>
</template>
'''
    open(f"{proj}/compositions/board.html", "w").write(html)
    return [s - 0.45 for s in starts[1:]] + [pull], [s + 0.15 for s in starts[1:]]


# ---------------------------------------------------------------- titles

def red(text):
    return re.sub(r"\*(.+?)\*", r'<em style="font-style: normal; color: var(--accent, #e0352b)">\1</em>', text)


def titles(topic, clips, end_t):
    hook_end = round(clips[1]["start"] - 0.45, 2)
    l1, l2 = topic["hook"]
    plain = lambda s: s.replace("*", "")
    K = "top: 178px; font-weight: 400; font-size: 32px; letter-spacing: 0.42em; color: #ddd3b4;"
    hook = ("hook", 0, hook_end, "    #hook-kicker-in { opacity: 0.75; }\n", "\n".join([
        el("hook-kicker", "t-body", 0, hook_end, f"HOLLOW TRUTH · FILE {topic['file']}", K),
        el("hook-l1", "t-display", 0, hook_end, red(l1), f"top: 230px; font-size: {fit(plain(l1), 900, 150)}px;"),
        el("hook-l2", "t-display", 0, hook_end, red(l2), f"top: 385px; font-size: {fit(plain(l2), 900, 150)}px;"),
    ]), f'''    flick(["#hook-l1-in", "#hook-l2-in"], {min(2.2, hook_end - 1.0):.2f});
    tl.to(["#hook-kicker-in", "#hook-l1-in", "#hook-l2-in"], {{ opacity: 0, duration: 0.2, ease: "power2.in" }}, {hook_end - 0.25:.2f});''')
    end_start = round(end_t + 0.05, 2)
    q_at = round(min(end_t + 0.35, 17.75) - end_start, 2)
    q = topic["question"]
    end = ("end", end_start, round(20 - end_start, 2), "    #end-k-in, #end-ask-in { opacity: 0; }\n", "\n".join([
        el("end-k", "t-body", 0, round(20 - end_start, 2), f"CASE {topic['file']} · UNSOLVED", "top: 220px; font-size: 44px; letter-spacing: 0.18em;"),
        el("end-ask", "t-display", q_at, round(20 - end_start - q_at, 2), esc(q), f"top: 300px; font-size: {fit(q, 920, 150)}px;"),
        el("end-mark", "t-body", q_at, round(20 - end_start - q_at, 2), "HOLLOW TRUTH", "top: 470px; font-size: 40px; letter-spacing: 0.5em; color: #ddd3b4;"),
    ]), f'''    flick("#end-k-in", 0.15);
    flick("#end-ask-in", {q_at + 0.02:.2f});
    tl.fromTo("#end-mark-in", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, ease: "power2.out" }}, {q_at + 0.02:.2f});''')
    return [hook, end], end_start + q_at


# ---------------------------------------------------------------- score

SCORE = '''"""Synthesise the 20s case-board bed: dark drone, eerie shimmer, room tone, pin thunks, string zips, riser and hit."""
import sys, wave
import numpy as np

SR = 48000
N = int(SR * 20.0)
t = np.arange(N) / SR
rng = np.random.default_rng(SEED)
L = np.zeros(N); R = np.zeros(N)
TRAVEL = TRAVEL_TIMES      # camera leaves for the next piece of evidence
ARRIVE = ARRIVE_TIMES      # camera lands on it
QUESTION = QUESTION_TIME   # the closing question slams in

def at(sec): return int(sec * SR)

def onepole(x, cutoff, high=False):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc; y[i] = acc
    return x - y if high else y

def env(n, attack, decay):
    e = np.ones(n)
    na = max(1, int(attack * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (decay * SR))
    return e

def add(sig, start, gain=1.0, pan=0.0):
    s = at(start); e = min(N, s + len(sig)); sig = sig[: e - s] * gain
    L[s:e] += sig * (1 - max(0, pan)); R[s:e] += sig * (1 + min(0, pan))

def fade(x, fin, fout):
    x = x.copy(); a, b = int(fin * SR), int(fout * SR)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x

# Drone, a mid pad phones can hear, and a high pair a minor second apart.
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.6 * np.sin(2 * np.pi * 61.7 * t)
         + 0.4 * np.sin(2 * np.pi * 87.3 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)) * lfo
pad = onepole(rng.standard_normal(N), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
pad += 0.25 * np.sin(2 * np.pi * 174.6 * t + 0.3 * np.sin(2 * np.pi * 0.3 * t))
pad += 0.06 * (np.sin(2 * np.pi * 932.3 * t) + np.sin(2 * np.pi * 987.8 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t - 1.2)) ** 2
add(fade(0.22 * drone + 0.5 * pad, 0.25, 1.2), 0, 0.5)
# Room tone: a quiet, dark room around the board.
add(fade(onepole(onepole(rng.standard_normal(N), 900), 120, high=True), 0.5, 1.0), 0, 0.12)

def thunk():
    n = int(0.25 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * (140 - 200 * tt) * tt) * env(n, 0.002, 0.05)
            + 0.5 * onepole(rng.standard_normal(n), 2500) * env(n, 0.001, 0.012))

def zip_(dur=0.5):
    n = int(dur * SR); x = rng.standard_normal(n)
    out = np.empty(n); acc = 0.0
    for i, v in enumerate(x):
        c = 600 + 2600 * i / n
        a = np.exp(-2 * np.pi * c / SR); acc = (1 - a) * v + a * acc; out[i] = acc
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2

def hit(dur=1.6, f0=75, f1=34):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 6)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.45) + 0.4 * onepole(rng.standard_normal(n), 3000) * env(n, 0.001, 0.03)

for k, tr in enumerate(TRAVEL[:-1]):
    add(zip_(), tr, 0.6, (-0.3 if k % 2 else 0.3))
for ar in ARRIVE:
    add(thunk(), ar, 0.7)
add(zip_(0.8), TRAVEL[-1], 0.8)
n = at(1.3); tt = np.arange(n) / SR
riser = onepole(rng.standard_normal(n), 2500) * (tt / tt[-1]) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 500 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1])
add(riser, QUESTION - 1.3, 0.5)
add(hit(), QUESTION + 0.01, 1.0)

mix = np.stack([L, R], 1)
mix /= np.abs(mix).max() / 0.85
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "bed.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
'''


def score(topic, proj, work, travel, arrive, q_time):
    src = (SCORE.replace("SEED", str(int(topic["file"])))
           .replace("TRAVEL_TIMES", json.dumps([round(x, 2) for x in travel]))
           .replace("ARRIVE_TIMES", json.dumps([round(x, 2) for x in arrive]))
           .replace("QUESTION_TIME", f"{q_time:.2f}"))
    open(f"{proj}/scripts/score.py", "w").write(src)
    run([sys.executable, f"{proj}/scripts/score.py", f"{work}/bed.wav"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{work}/bed.wav", "-af", "loudnorm=I=-23:TP=-2", "-ar", "48000",
         "-c:a", "aac", "-b:a", "192k", f"{proj}/assets/audio/bed.m4a"])


# ---------------------------------------------------------------- docs

def docs(topic, proj, speed):
    script = "\n".join(f"{i + 1}. {ln.get('cap', ln['say'])}" for i, ln in enumerate(topic["lines"]))
    open(f"{proj}/BRIEF.md", "w").write(f'''---
workflow: general-video
flow: automation
storyboard: no
message: "{topic['title']}: {topic['question'].capitalize()}"
destination: social-vertical
aspect: 1080x1920
language: en
audience: US
length: 20s
angle: mystery / unexplained short (case-board series)
channel: Hollow Truth
file: "{topic['file']}"
---

## Intent

Hollow Truth File {topic['file']}: {topic['title']}. A torch searches a corkboard in a dark
room. Each line of the voiceover lands on one piece of evidence; a red string is pulled to
the next. At the end the camera pulls back to the whole case and asks "{topic['question']}"

## Script (voiceover)

{script}

## Assets

- assets/audio/voiceover.m4a: Kokoro TTS ({VOICE}, {speed}x), pitched down 7% with a short reverb tail, -16 LUFS.
- assets/audio/bed.m4a: made by scripts/score.py (drone, high tone, room tone, pin thunks, string zips, riser, hit), -23 LUFS.

## Notes

- Built by tools/hollow-truth/build.py from tools/hollow-truth/topics.py; change copy there and rebuild.
- Everything is drawn; the evidence prints are illustrations, not photographs.
- No Whisper model offline: caption timing comes from phrase placement plus silencedetect.
''')
    open(f"{proj}/DESCRIPTION.md", "w").write(description(topic))


def description(topic):
    return (f"**Title:** {topic['yt_title']}\n\n{topic['yt_body']}\n\n"
            f"📖 Learn more: {topic['wiki']}\n"
            f"🔔 Subscribe to Hollow Truth for more strange events, unsolved mysteries and places you were never meant to see.\n\n"
            f"{topic['tags']}\n")


# ---------------------------------------------------------------- main

def scaffold(topic):
    name = f"ht-{topic['file']}-{topic['slug']}"
    proj = os.path.join(REPO, "videos", name)
    if os.path.exists(proj):
        shutil.rmtree(proj)
    for d in ("assets/audio", "assets/vendor", "compositions", "scripts", "renders"):
        os.makedirs(f"{proj}/{d}", exist_ok=True)
    for f in ("hyperframes.json", "CLAUDE.md", "AGENTS.md", ".gitignore", "assets/vendor/gsap.min.js", "compositions/mood.html"):
        shutil.copy(os.path.join(TEMPLATE, f), f"{proj}/{f}")
    pkg = json.load(open(os.path.join(TEMPLATE, "package.json")))
    pkg["name"] = name
    json.dump(pkg, open(f"{proj}/package.json", "w"), indent=2)
    json.dump({"id": name, "name": name}, open(f"{proj}/meta.json", "w"), indent=2)
    return proj


def build(topic):
    proj = scaffold(topic)
    work = os.path.join("/tmp", f"ht-work-{topic['file']}")
    os.makedirs(work, exist_ok=True)
    clips, end_t, speed = voice(topic, proj, work)
    travel, arrive = board(topic, clips, end_t, proj)
    scenes, q_time = titles(topic, clips, end_t)
    write_project(proj, "board", "The case board: one corkboard the torch searches for the whole film", "#120d08",
                  scenes, captions(topic, clips), [round(x, 2) for x in travel])
    score(topic, proj, work, travel, arrive, q_time)
    docs(topic, proj, speed)
    print(f"{topic['file']} {topic['slug']}: voice ends {end_t:.2f}s at {speed}x, question at {q_time:.2f}s -> {proj}")


if __name__ == "__main__":
    want = sys.argv[1:] or ["all"]
    for tp in TOPICS:
        if "all" in want or tp["file"] in want:
            build(tp)
