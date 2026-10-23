#!/usr/bin/env python3
"""HyperFrames project for Format B/C (easter egg / mistake): full-frame footage between torn-paper edges,
film title at the top, 1–2 word pop captions in the centre, a bouncing red arrow on the detail.

usage: build_easteregg.py edit.json PROJECT_DIR

edit.json:
  {"duration": 20.2, "voice": "voice_tight.wav", "music": null, "music_volume": 0.12,
   "title": "FROZEN",
   "shots":    [{"src": "broll/m01.mp4", "start": 0, "dur": 2.1, "media_start": 3.0,
                 "zoom": [1.0, 1.08], "pos": "50% 50%"}],
   "captions": [{"start": 0.0, "end": 0.4, "text": "เพื่อนๆ"}],
   "arrows":   [{"start": 9.2, "end": 12.0, "x": 300, "y": 900, "angle": 0, "x2": 420, "y2": 900}],
   "caption_y": 870}
x2/y2 (optional): where the tip is at the arrow's end time, to follow a moving character.
caption_y: centre of the caption line (default 870); move it up (e.g. 480) when the detail sits mid-frame.
x/y = where the arrow TIP points, on the 1080x1920 canvas; angle in degrees (0 = pointing down,
positive turns it clockwise, e.g. -30 comes in from the upper right).
Make the 1–2 word cards with my-edit-style/scripts/chunk_captions.py --max-base 6 --target 0.4.
Then: cd PROJECT_DIR && npx hyperframes check && npx hyperframes render -o renders/out.mp4
"""
import argparse
import html
import json
import math
import os
import random
import shutil
import subprocess

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
TOP_EDGE, BOTTOM_EDGE = 70, 1650  # footage window between the torn edges


def ring(px, color="#0b0b0b", step=20):
    return ", ".join(
        f"{px * math.cos(math.radians(a)):.1f}px {px * math.sin(math.radians(a)):.1f}px 0 {color}" for a in range(0, 360, step)
    )


def torn_path(y, down, seed):
    """jagged white paper strip along y; down=True tears downward (top edge)"""
    rnd = random.Random(seed)
    pts, x = [], 0
    while x <= 1080:
        pts.append((x, y + (rnd.uniform(4, 22) if down else -rnd.uniform(4, 22))))
        x += rnd.uniform(14, 34)
    pts.append((1080, y))
    base = 0 if down else 1920
    d = f"M0,{base} L0,{y} " + " ".join(f"L{px:.0f},{py:.0f}" for px, py in pts) + f" L1080,{base} Z"
    return d


TEMPLATE = """<!doctype html>
<html lang="th">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>movie-trivia-short</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      @font-face { font-family: "KanitBI"; src: url("assets/fonts/kanit-thai-900-italic.woff2") format("woff2");
        font-style: italic; font-weight: 900; unicode-range: U+0E01-0E5B, U+200C-200D, U+25CC; }
      @font-face { font-family: "KanitBI"; src: url("assets/fonts/kanit-latin-900-italic.woff2") format("woff2");
        font-style: italic; font-weight: 900; unicode-range: U+0000-00FF, U+2000-206F, U+20AC, U+2122; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #0b0b0b; }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; background: #0b0b0b;
        font-family: "KanitBI", sans-serif; font-style: italic; font-weight: 900; }
      .win { position: absolute; left: 0; top: __TOP__px; width: 1080px; height: __H__px; overflow: hidden; z-index: 0; }
      .zoom { position: absolute; inset: 0; }
      .zoom video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
      #paper { position: absolute; inset: 0; z-index: 1; }
      #title { position: absolute; left: 0; top: 190px; width: 1080px; display: flex; justify-content: center; z-index: 3; }
      #title span { display: block; font-size: 72px; line-height: 1.25; color: #fff; text-transform: uppercase;
        text-shadow: __RING5__; padding: 0 20px; white-space: nowrap; }
      .cap { left: 0; top: __CAPTOP__px; width: 1080px; height: 220px; display: flex; align-items: center; justify-content: center; z-index: 4; position: absolute; }
      .cap .t { display: block; font-size: 128px; line-height: 1.3; color: #fff; text-transform: uppercase; white-space: nowrap;
        text-shadow: __RING8__, 0 6px 14px rgba(0,0,0,.6); padding: 0 24px; }
      .arrow { position: absolute; width: 200px; height: 230px; z-index: 5; }
      .arrow .m, .arrow .a { position: absolute; inset: 0; }
      .arrow .a { transform-origin: 50% 100%; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="1080" data-height="1920" data-fps="30">
__SHOTS__
      <svg id="paper" viewBox="0 0 1080 1920" width="1080" height="1920">
        <path d="__TOPEDGE__" fill="#f4f1ea"/><path d="__BOTEDGE__" fill="#f4f1ea"/>
        <path d="__TOPFILL__" fill="#0b0b0b"/><path d="__BOTFILL__" fill="#0b0b0b"/>
      </svg>
__TITLE__
__CAPS__
__ARROWS__
      <audio id="voice" src="__VOICE__" data-start="0" data-duration="__DUR__" data-track-index="8" data-volume="1"></audio>
__MUSIC__
    </div>
    <script>
      document.fonts.ready.then(() => {
        document.querySelectorAll(".cap .t, #title span").forEach((el) => {
          const max = el.parentElement.id === "title" ? 1000 : 1020, w = el.scrollWidth;
          if (w > max) el.style.fontSize = Math.floor(parseFloat(getComputedStyle(el).fontSize) * max / w) + "px";
        });
        const tl = gsap.timeline({ paused: true });
        const f = 1 / __FPS__;
        // slow push-in per shot
        document.querySelectorAll(".zoom").forEach((z) => {
          const t = parseFloat(z.dataset.t), d = parseFloat(z.dataset.d);
          tl.fromTo(z, { scale: parseFloat(z.dataset.z0) }, { scale: parseFloat(z.dataset.z1), duration: d, ease: "none", immediateRender: false }, t);
        });
        // caption pop: 0.6 -> 1.08 -> 1 over 4 frames
        document.querySelectorAll(".cap").forEach((cap) => {
          const t = parseFloat(cap.dataset.start), el = cap.querySelector(".t");
          tl.fromTo(el, { scale: 0.6 }, { scale: 1.08, duration: 3 * f, ease: "none", immediateRender: false }, t);
          tl.to(el, { scale: 1, duration: f, ease: "none" }, t + 3 * f);
        });
        // arrow: pop in, then bob toward the target until it leaves
        document.querySelectorAll(".arrow").forEach((ar) => {
          const t = parseFloat(ar.dataset.start), d = parseFloat(ar.dataset.duration), el = ar.querySelector(".a");
          const dx = parseFloat(ar.dataset.dx || 0), dy = parseFloat(ar.dataset.dy || 0);
          if (dx || dy) tl.fromTo(ar.querySelector(".m"), { x: 0, y: 0 }, { x: dx, y: dy, duration: d, ease: "none", immediateRender: false }, t);
          tl.fromTo(el, { scale: 0, y: -40 }, { scale: 1.12, y: 0, duration: 5 * f, ease: "power2.out", immediateRender: false }, t);
          tl.to(el, { scale: 1, duration: 2 * f }, t + 5 * f);
          const n = Math.max(1, Math.floor((d - 7 * f) / 0.36));
          tl.fromTo(el, { y: 0 }, { y: -18, duration: 0.18, ease: "sine.inOut", yoyo: true, repeat: n * 2 - 1, immediateRender: false }, t + 7 * f);
        });
        tl.set({}, {}, __DUR__);
        window.__timelines["main"] = tl;
      });
    </script>
  </body>
</html>
"""

ARROW_SVG = ('<svg viewBox="0 0 200 230" width="200" height="230"><path d="M70,10 L130,10 L130,120 L185,120 L100,220 '
             'L15,120 L70,120 Z" fill="#e3161c" stroke="#ffffff" stroke-width="12" stroke-linejoin="round"/></svg>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("project")
    a = ap.parse_args()
    e = json.load(open(a.edit))
    base = os.path.dirname(os.path.abspath(a.edit))

    def path(p):
        return p if os.path.isabs(p) else os.path.join(base, p)

    proj = a.project
    for sub in ("assets/fonts", "assets/vendor", "assets/broll", "assets/audio", "renders"):
        os.makedirs(os.path.join(proj, sub), exist_ok=True)
    for fn in ("kanit-thai-900-italic.woff2", "kanit-latin-900-italic.woff2"):
        shutil.copy2(os.path.join(SKILL, "assets", "fonts", fn), os.path.join(proj, "assets", "fonts", fn))
    shutil.copy2(os.path.join(SKILL, "assets", "vendor", "gsap.min.js"), os.path.join(proj, "assets", "vendor", "gsap.min.js"))
    dur = e["duration"]
    voice = "assets/audio/voice.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path(e["voice"]), "-vn", "-c:a", "aac", "-b:a", "192k",
                    os.path.join(proj, voice)], check=True)

    copied, shots = {}, []
    for i, s in enumerate(e["shots"]):
        src = path(s["src"])
        if src not in copied:
            copied[src] = f"assets/broll/{os.path.basename(src)}"
            shutil.copy2(src, os.path.join(proj, copied[src]))
        z0, z1 = s.get("zoom", [1.0, 1.06])
        pos = s.get("pos", "50% 50%")
        shots.append(
            f'      <div class="win"><div class="zoom" data-t="{s["start"]}" data-d="{s["dur"]}" data-z0="{z0}" data-z1="{z1}">'
            f'<video id="v-{i}" class="clip" src="{copied[src]}" data-start="{s["start"]}" data-duration="{s["dur"]}" '
            f'data-media-start="{s["media_start"]}" data-track-index="0" muted playsinline style="object-position:{pos}">'
            f"</video></div></div>"
        )

    caps = []
    for i, c in enumerate(e.get("captions", [])):
        if c["start"] >= dur:
            continue
        d = round(min(max(c["end"] - c["start"] - 1 / FPS, 2 / FPS), dur - c["start"]), 3)
        caps.append(f'      <div id="cap-{i}" class="clip cap" data-start="{c["start"]}" data-duration="{d}" data-track-index="4">'
                    f'<span class="t">{html.escape(c["text"])}</span></div>')

    arrows = []
    for i, ar in enumerate(e.get("arrows", [])):
        d = round(ar["end"] - ar["start"], 3)
        left, top = ar["x"] - 100, ar["y"] - 230  # tip of the arrow sits at (x, y)
        arrows.append(
            f'      <div id="arrow-{i}" class="clip arrow" data-start="{ar["start"]}" data-duration="{d}" data-track-index="5" '
            f'data-dx="{ar.get("x2", ar["x"]) - ar["x"]}" data-dy="{ar.get("y2", ar["y"]) - ar["y"]}" '
            f'style="left:{left}px;top:{top}px"><div class="m">'
            f'<div style="position:absolute;inset:0;transform:rotate({ar.get("angle", 0)}deg);transform-origin:100px 230px">'
            f'<div class="a">{ARROW_SVG}</div></div></div></div>'
        )

    title = ""
    if e.get("title"):
        title = (f'      <div id="title" class="clip" data-start="0" data-duration="{dur}" data-track-index="3">'
                 f'<span>{html.escape(e["title"])}</span></div>')
    music = ""
    if e.get("music"):
        m = f"assets/audio/{os.path.basename(e['music'])}"
        shutil.copy2(path(e["music"]), os.path.join(proj, m))
        music = (f'      <audio id="music" src="{m}" data-start="0" data-duration="{dur}" data-track-index="9" '
                 f'data-volume="{e.get("music_volume", 0.12)}"></audio>')

    top_edge = torn_path(TOP_EDGE, True, 7)
    bot_edge = torn_path(BOTTOM_EDGE, False, 11)
    out = (TEMPLATE.replace("__SHOTS__", "\n".join(shots)).replace("__CAPS__", "\n".join(caps))
           .replace("__ARROWS__", "\n".join(arrows)).replace("__TITLE__", title).replace("__MUSIC__", music)
           .replace("__VOICE__", voice).replace("__DUR__", str(dur)).replace("__FPS__", str(FPS))
           .replace("__TOP__", str(TOP_EDGE)).replace("__CAPTOP__", str(int(e.get("caption_y", 870)) - 110)).replace("__H__", str(BOTTOM_EDGE - TOP_EDGE))
           .replace("__RING5__", ring(5)).replace("__RING8__", ring(8))
           .replace("__TOPFILL__", f"M0,0 L1080,0 L1080,{TOP_EDGE - 14} L0,{TOP_EDGE - 14} Z")
           .replace("__BOTFILL__", f"M0,{BOTTOM_EDGE + 14} L1080,{BOTTOM_EDGE + 14} L1080,1920 L0,1920 Z")
           .replace("__TOPEDGE__", top_edge).replace("__BOTEDGE__", bot_edge))
    open(os.path.join(proj, "index.html"), "w").write(out)
    if not os.path.exists(os.path.join(proj, "hyperframes.json")):
        json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                   "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
                   "media": {"autoProxy": True}}, open(os.path.join(proj, "hyperframes.json"), "w"), indent=2)
    print(f"wrote {proj}/index.html: {len(shots)} shots, {len(caps)} captions, {len(arrows)} arrows, {dur}s")


if __name__ == "__main__":
    main()
