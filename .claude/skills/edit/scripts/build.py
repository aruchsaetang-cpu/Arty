#!/usr/bin/env python3
"""Build a HyperFrames project in the Zack-D-Films short-explainer style.

Inputs:  voiceover audio + word-level transcript (Whisper JSON) + footage clips
         (+ optional music bed and a plan.json with shots / graphics).
Output:  a HyperFrames project directory (index.html + assets) ready for
         `hyperframes render`.

Usage:
  build.py --vo vo.wav --words vo.json --clips a.mp4 b.mp4 ... --out proj
           [--music bed.mp3] [--plan plan.json] [--duration SEC]
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")

W, H = 1080, 1920
# --- Style constants measured from the reference clips (see references/style-analysis.md)
CAP_MAX_WORDS = 3          # captions show 1-3 words at a time (mean ~2)
CAP_MAX_CHARS = 20         # widest reference chunk ~ "the air is hitting less" fits ~90% width
CAP_MAX_THAI_CHARS = 14
CAP_GAP_HIDE = 0.40        # hide caption if speech gap is longer than this
CAP_MIN_DUR = 0.25
SHOT_MIN, SHOT_TARGET, SHOT_MAX = 1.0, 1.3, 2.2   # reference avg shot ~1.5 s
BREAK_BEFORE = {"and", "but", "which", "while", "that", "so", "because", "or",
                "if", "when", "then", "until", "who", "where"}
NO_END = {"the", "a", "an", "of", "to", "your", "my", "his", "her", "its", "their",
          "in", "on", "at", "for", "with", "from", "this", "these"}   # never leave these dangling
THAI = re.compile(r"[฀-๿]")


def load_words(path):
    d = json.load(open(path, encoding="utf-8"))
    words = []
    if isinstance(d, dict) and "segments" in d:          # openai-whisper / faster-whisper
        for s in d["segments"]:
            for w in s.get("words", []):
                words.append((w["word"].strip(), float(w["start"]), float(w["end"])))
    elif isinstance(d, list):                             # hyperframes transcript / generic
        for w in d:
            t = w.get("word", w.get("text", "")).strip()
            words.append((t, float(w["start"]), float(w["end"])))
    else:
        sys.exit("Unrecognised transcript format: " + path)
    return [w for w in words if w[0]]


def clean(tok):
    # keep ? and ! (reference keeps "run faster?"), drop trailing , . ; :
    return re.sub(r"[,.;:…\"“”]+$", "", re.sub(r"^[\"“”…]+", "", tok))


def chunk_captions(words):
    chunks, cur = [], []

    def flush():
        if cur:
            thai = any(THAI.search(w[0]) for w in cur)
            text = ("" if thai else " ").join(clean(w[0]) for w in cur).strip()
            chunks.append({"text": text, "start": cur[0][1], "end": cur[-1][2]})
            cur.clear()

    for w in words:
        tok = w[0]
        thai = bool(THAI.search(tok))
        limit = CAP_MAX_THAI_CHARS if thai else CAP_MAX_CHARS
        cur_len = sum(len(clean(x[0])) + 1 for x in cur)
        if cur and (re.search(r"[.,!?;:…]$", cur[-1][0])
                    or tok.lower().strip(",.") in BREAK_BEFORE
                    or w[1] - cur[-1][2] > CAP_GAP_HIDE):
            flush()
        elif cur and (len(cur) >= CAP_MAX_WORDS or cur_len + len(clean(tok)) > limit):
            carry = cur.pop() if len(cur) > 1 and clean(cur[-1][0]).lower() in NO_END else None
            flush()
            if carry:
                cur.append(carry)
        cur.append(w)
    flush()
    # display windows: hold until the next chunk unless there's a real pause
    for i, c in enumerate(chunks):
        nxt = chunks[i + 1]["start"] if i + 1 < len(chunks) else None
        end = nxt if nxt is not None and nxt - c["end"] <= CAP_GAP_HIDE else c["end"] + 0.15
        c["dur"] = max(CAP_MIN_DUR, end - c["start"])
    return chunks


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return float(out.strip())


def auto_shots(chunks, words, clips, total):
    """Cut on caption boundaries (~1.3-1.5 s shots); cut mid-caption on a word if a shot runs long."""
    cap = sorted({round(c["start"], 3) for c in chunks})
    wrd = sorted({round(w[1], 3) for w in words})
    cuts = [0.0]
    while total - cuts[-1] > SHOT_MAX:
        last, aim = cuts[-1], cuts[-1] + SHOT_TARGET
        for pool in (cap, wrd, [aim]):
            cand = [b for b in pool if last + SHOT_MIN <= b <= last + SHOT_MAX]
            if cand:
                cuts.append(min(cand, key=lambda b: abs(b - aim)))
                break
    if total - cuts[-1] < SHOT_MIN and len(cuts) > 1:
        cuts.pop()
    cuts.append(total)
    cursor = {c: 0.0 for c in clips}
    durs = {c: probe_dur(c) for c in clips}
    shots = []
    for i in range(len(cuts) - 1):
        src = clips[i % len(clips)]
        d = cuts[i + 1] - cuts[i]
        if cursor[src] + d > durs[src]:
            cursor[src] = 0.0
        shots.append({"src": src, "in": cursor[src], "start": cuts[i], "dur": d})
        cursor[src] += d
    return shots


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def burst_svg(seed, n=46):
    # deterministic anime speed lines (no Math.random in compositions)
    import math
    x = seed
    lines = []
    for k in range(n):
        x = (x * 1103515245 + 12345) & 0x7fffffff
        a = 2 * math.pi * (k + (x % 100) / 100) / n
        x = (x * 1103515245 + 12345) & 0x7fffffff
        r0 = 420 + x % 260
        w = 3 + (x >> 8) % 7
        cx, cy = W / 2, H * 0.42
        lines.append(f'<line x1="{cx + math.cos(a) * r0:.0f}" y1="{cy + math.sin(a) * r0:.0f}" '
                     f'x2="{cx + math.cos(a) * 1700:.0f}" y2="{cy + math.sin(a) * 1700:.0f}" '
                     f'stroke="white" stroke-width="{w}" stroke-linecap="round"/>')
    return f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(lines)}</svg>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", required=True, help="voiceover audio (or video with the narration)")
    ap.add_argument("--words", required=True, help="Whisper JSON with word timestamps")
    ap.add_argument("--clips", nargs="*", default=[], help="footage clips, used in order")
    ap.add_argument("--music", help="optional music bed")
    ap.add_argument("--music-volume", type=float, default=0.16, help="~ -16 dB under the VO")
    ap.add_argument("--plan", help="optional plan.json (shots, graphics)")
    ap.add_argument("--duration", type=float, help="override total duration")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8")) if a.plan else {}
    words = load_words(a.words)
    chunks = plan.get("captions") or chunk_captions(words)   # plan.captions = hand-edited override
    total = a.duration or round(max(probe_dur(a.vo), chunks[-1]["start"] + chunks[-1]["dur"]), 3)

    os.makedirs(os.path.join(a.out, "media"), exist_ok=True)
    for f in ("gsap.min.js", "montserrat-latin-800-normal.woff2", "kanit-thai-700-normal.woff2"):
        shutil.copy(os.path.join(ASSETS, f), os.path.join(a.out, f))

    def media(p):
        dst = os.path.join("media", os.path.basename(p))
        if not os.path.exists(os.path.join(a.out, dst)):
            shutil.copy(p, os.path.join(a.out, dst))
        return dst

    if plan.get("shots"):
        shots, t = [], 0.0
        for s in plan["shots"]:
            d = float(s["dur"])
            shots.append({"src": s["src"], "in": float(s.get("in", 0)), "start": t, "dur": d,
                          "move": s.get("move")})
            t += d
    elif a.clips:
        shots = auto_shots(chunks, words, a.clips, total)
    else:
        sys.exit("Need --clips or plan.shots")

    els, js = [], []
    # --- footage: every shot keeps moving (reference camera is never static)
    for i, s in enumerate(shots):
        sid = f"shot{i}"
        els.append(f'<video id="{sid}" class="clip shot" src="{media(s["src"])}" muted playsinline '
                   f'data-start="{s["start"]:.3f}" data-duration="{s["dur"]:.3f}" '
                   f'data-media-start="{s["in"]:.3f}" data-track-index="0"></video>')
        move = s.get("move") or ("in" if i % 2 == 0 else "out")
        a0, a1 = (1.0, 1.09) if move == "in" else (1.09, 1.0)
        js.append(f'tl.fromTo("#{sid}",{{scale:{a0}}},{{scale:{a1},duration:{s["dur"]:.3f},ease:"none"}},{s["start"]:.3f});')

    # --- graphics from plan
    for gi, g in enumerate(plan.get("graphics", [])):
        gid, at, d = f"g{gi}", float(g["at"]), float(g.get("dur", 1.2))
        typ = g["type"]
        if typ == "stat":       # flip-counter tiles (ref: "2000 HOURS")
            to, frm = int(g["to"]), int(g.get("from", 0))
            n = len(str(to))
            tiles = "".join(f'<span class="tile" id="{gid}d{k}">0</span>' for k in range(n))
            label = f'<div class="stat-label">{esc(g.get("label", ""))}</div>' if g.get("label") else ""
            els.append(f'<div id="{gid}" class="clip stat" data-start="{at:.3f}" data-duration="{d:.3f}" '
                       f'data-track-index="2"><div class="tiles">{tiles}</div>{label}</div>')
            js.append(f'(function(){{const o={{v:{frm}}},n={n};const draw=()=>{{const s=String(Math.round(o.v)).padStart(n,"0");'
                      f'for(let k=0;k<n;k++)document.getElementById("{gid}d"+k).textContent=s[k];}};'
                      f'tl.fromTo("#{gid}",{{y:-60,opacity:0}},{{y:0,opacity:1,duration:0.18,ease:"back.out(2)"}},{at:.3f});'
                      f'tl.fromTo(o,{{v:{frm}}},{{v:{to},duration:{max(0.3, d * 0.75):.3f},ease:"power1.inOut",onUpdate:draw,onStart:draw}},{at + 0.1:.3f});}})();')
        elif typ == "glow":     # glowing cyan words that step (ref: "2 Times / 3 Times / 5 Times")
            steps = g.get("steps") or [g["text"]]
            step = d / len(steps)
            for k, txt in enumerate(steps):
                sid = f"{gid}s{k}"
                els.append(f'<div id="{sid}" class="clip glow" data-start="{at + k * step:.3f}" '
                           f'data-duration="{step:.3f}" data-track-index="2" style="top:{g.get("y", 1160)}px">{esc(txt)}</div>')
                js.append(f'tl.fromTo("#{sid}",{{scale:0.6,opacity:0}},{{scale:1,opacity:1,duration:0.14,ease:"back.out(3)"}},{at + k * step:.3f});')
        elif typ == "burst":    # anime speed-line burst (ref: "run faster?", "a tad quicker")
            els.append(f'<div id="{gid}" class="clip burst" data-start="{at:.3f}" data-duration="{d:.3f}" data-track-index="3">'
                       f'<div id="{gid}a">{burst_svg(7 + gi)}</div><div id="{gid}b">{burst_svg(91 + gi)}</div></div>')
            t, k = at, 0
            while t < at + d:   # flicker between two line sets every 2 frames @30fps
                js.append(f'tl.set("#{gid}a",{{opacity:{1 if k % 2 == 0 else 0}}},{t:.3f});tl.set("#{gid}b",{{opacity:{0 if k % 2 == 0 else 1}}},{t:.3f});')
                t += 2 / 30; k += 1
        elif typ == "flash":    # white flash on a hard cut
            els.append(f'<div id="{gid}" class="clip flash" data-start="{at:.3f}" data-duration="{d:.3f}" data-track-index="3"></div>')
            js.append(f'tl.fromTo("#{gid}",{{opacity:0.85}},{{opacity:0,duration:{d:.3f},ease:"power2.out"}},{at:.3f});')
        elif typ == "highlight":  # yellow glow box over an object (ref: highlighted body bag / hair)
            x, y, w_, h_ = g["box"]
            els.append(f'<div id="{gid}" class="clip hl" data-start="{at:.3f}" data-duration="{d:.3f}" data-track-index="2" '
                       f'style="left:{x}px;top:{y}px;width:{w_}px;height:{h_}px"></div>')
            js.append(f'tl.fromTo("#{gid}",{{opacity:0}},{{opacity:1,duration:0.2,yoyo:true,repeat:{max(1, int(d / 0.4)) | 1},ease:"sine.inOut"}},{at:.3f});')
        else:
            sys.exit("unknown graphic type: " + typ)

    # --- captions: hard swap, no entrance animation (as in every reference clip)
    for i, c in enumerate(chunks):
        els.append(f'<div id="cap{i}" class="clip cap" data-start="{c["start"]:.3f}" data-duration="{c["dur"]:.3f}" '
                   f'data-track-index="4"><span>{esc(c["text"])}</span></div>')

    # --- audio
    els.append(f'<audio id="vo" class="clip" src="{media(a.vo)}" data-start="0" data-duration="{total:.3f}" '
               f'data-has-audio="true" data-track-index="5"></audio>')
    if a.music:
        els.append(f'<audio id="music" class="clip" src="{media(a.music)}" data-start="0" data-duration="{total:.3f}" '
                   f'data-volume="{a.music_volume}" data-fade-out="0.6" data-track-index="6"></audio>')

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="gsap.min.js"></script>
<style>
@font-face {{ font-family: "Montserrat"; font-weight: 800; src: url(montserrat-latin-800-normal.woff2) format("woff2"); }}
@font-face {{ font-family: "Kanit"; font-weight: 800; src: url(kanit-thai-700-normal.woff2) format("woff2"); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
#root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
.shot {{ position: absolute; inset: 0; width: {W}px; height: {H}px; object-fit: cover; transform-origin: 50% 45%; }}
/* caption: white heavy sans, thin dark outline + soft drop shadow, centred, ~78% down */
.cap {{ position: absolute; left: 40px; right: 40px; top: 1420px; height: 160px; z-index: 10;
       display: flex; align-items: center; justify-content: center; }}
.cap span {{ font-family: "Montserrat", "Kanit", sans-serif; font-weight: 800; font-size: 84px;
       line-height: 1; color: #fff; white-space: nowrap; letter-spacing: -0.5px;
       text-shadow: -3px -3px 0 #111, 3px -3px 0 #111, -3px 3px 0 #111, 3px 3px 0 #111,
                    0 -3px 0 #111, 0 3px 0 #111, -3px 0 0 #111, 3px 0 0 #111,
                    0 8px 14px rgba(0,0,0,.55); }}
.stat {{ position: absolute; left: 0; right: 0; top: 330px; z-index: 6; display: flex;
        flex-direction: column; align-items: center; font-family: "Montserrat", sans-serif; }}
.tiles {{ display: flex; gap: 10px; }}
.tile {{ width: 150px; height: 210px; border-radius: 14px; display: flex; align-items: center;
        justify-content: center; font-size: 170px; font-weight: 800; color: #f2f2f2;
        background: linear-gradient(#2a2c30 0 49.5%, #0e0f11 49.5% 50.5%, #202226 50.5%);
        box-shadow: 0 10px 30px rgba(0,0,0,.6), inset 0 0 0 3px #3a3d42; }}
.stat-label {{ margin-top: 12px; padding: 6px 30px; border-radius: 12px; background: #16171a;
        color: #f2f2f2; font-size: 120px; font-weight: 800; letter-spacing: 4px;
        box-shadow: 0 10px 30px rgba(0,0,0,.6), inset 0 0 0 3px #3a3d42; }}
.glow {{ position: absolute; left: 0; right: 0; z-index: 6; text-align: center;
        font-family: "Montserrat", "Kanit", sans-serif; font-weight: 800; font-size: 150px; color: #8ff3ff;
        text-shadow: 0 0 18px #19d3ff, 0 0 40px #0aa8ff, 0 6px 0 #0b5d88; }}
.burst {{ position: absolute; inset: 0; z-index: 7; }}
.burst > div {{ position: absolute; inset: 0; }}
.flash {{ position: absolute; inset: 0; z-index: 8; background: #fff; }}
.hl {{ position: absolute; z-index: 5; border-radius: 40%; background: rgba(255,232,0,.35);
      box-shadow: 0 0 60px 30px rgba(255,232,0,.45); mix-blend-mode: screen; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}">
{chr(10).join(els)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
"""
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(html)
    json.dump({"captions": chunks, "shots": shots, "duration": total},
              open(os.path.join(a.out, "edit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for f in ("hyperframes.json", "meta.json"):
        p = os.path.join(a.out, f)
        if not os.path.exists(p):
            json.dump({"id": os.path.basename(os.path.abspath(a.out)), "name": "edit"} if f == "meta.json" else {},
                      open(p, "w"))
    n = len(chunks)
    print(f"built {a.out}: {total:.2f}s, {len(shots)} shots (avg {total / len(shots):.2f}s), "
          f"{n} captions (avg {sum(len(c['text'].split()) for c in chunks) / n:.1f} words)")


if __name__ == "__main__":
    main()
