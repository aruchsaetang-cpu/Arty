#!/usr/bin/env python3
"""Write a HyperFrames project (index.html + assets) from edit.json in the reference style.

usage: build_composition.py edit.json PROJECT_DIR [--cam-pos "50% 40%"]

Layout (style-guide.md §4, 1080x1920):
  blurred B-roll fill (whole frame) -> sharp B-roll band y=545..1371 ->
  presenter circle d=350 centred (210,1349) -> caption centred y=300, 5-frame pop.
Then:  cd PROJECT_DIR && npx hyperframes check && npx hyperframes render -o renders/out.mp4
"""
import argparse
import html
import json
import math
import os
import shutil
import subprocess

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
# 24 hard shadows 7px out = the reference outline
RING = ", ".join(
    f"{7 * math.cos(math.radians(a)):.1f}px {7 * math.sin(math.radians(a)):.1f}px 0 #111311" for a in range(0, 360, 15)
)

TEMPLATE = """<!doctype html>
<html lang="th">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>my-edit-style</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      @font-face {
        font-family: "Itim";
        src: url("assets/fonts/itim-thai-400-normal.woff2") format("woff2");
        unicode-range: U+0E01-0E5B, U+200C-200D, U+25CC;
      }
      @font-face {
        font-family: "Itim";
        src: url("assets/fonts/itim-latin-400-normal.woff2") format("woff2");
        unicode-range: U+0000-00FF, U+2000-206F, U+20AC, U+2122;
      }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #101010; }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; background: #101010; font-family: "Itim", sans-serif; }
      .clip { position: absolute; }
      /* blurred fill: same shot, cover the frame, about 10% darker */
      .fill { inset: 0; width: 100%; height: 100%; object-fit: cover; filter: blur(40px) brightness(0.9); transform: scale(1.15); z-index: 0; }
      /* sharp band: full width, y 545-1371 */
      .band { left: 0; top: 545px; width: 1080px; height: 826px; object-fit: cover; z-index: 1; }
      /* presenter circle: d=350, centre (210,1349), no border */
      #cam { position: absolute; left: 35px; top: 1175px; width: 350px; height: 350px; border-radius: 50%; overflow: hidden; z-index: 2; }
      #cam video { inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: __CAMPOS__; }
      /* caption card: centred x, centre y=300 */
      .cap { left: 0; top: 0; width: 1080px; height: 600px; display: flex; align-items: center; justify-content: center; z-index: 3; }
      .cap .t { display: block; white-space: nowrap; font-size: 120px; line-height: 1.3; letter-spacing: 1px; color: #ffffff;
        /* 7px #111311 outline as a ring of hard shadows (text-stroke does not render in the capture browser), then the soft drop shadow */
        text-shadow: __RING__, 0 4px 12px rgba(0, 0, 0, 0.55); padding: 0 12px; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="__DUR__" data-width="1080" data-height="1920" data-fps="30">
__SHOTS__
      <div id="cam">
        <video id="v-cam" class="clip" src="__CAM__" data-start="0" data-duration="__DUR__" data-track-index="2" muted playsinline></video>
      </div>
__CAPS__
      <audio id="voice" src="__VOICE__" data-start="0" data-duration="__DUR__" data-track-index="5" data-volume="1"></audio>
__MUSIC__
    </div>
    <script>
      document.fonts.ready.then(() => {
        // long cards shrink to fit 1000px instead of wrapping (1 line per card)
        document.querySelectorAll(".cap .t").forEach((el) => {
          const w = el.scrollWidth;
          if (w > 1000) el.style.fontSize = Math.floor((120 * 1000) / w) + "px";
        });
        const tl = gsap.timeline({ paused: true });
        const f = 1 / __FPS__;
        // pop measured on the reference: linear 0.30 -> 1.055 over 4 frames, then 1.0 on frame 5
        document.querySelectorAll(".cap").forEach((cap) => {
          const t = parseFloat(cap.dataset.start);
          const el = cap.querySelector(".t");
          tl.fromTo(el, { scale: 0.3 }, { scale: 1.055, duration: 4 * f, ease: "none", immediateRender: false }, t);
          tl.to(el, { scale: 1, duration: f, ease: "none" }, t + 4 * f);
        });
        tl.set({}, {}, __DUR__);
        window.__timelines["main"] = tl;
      });
    </script>
  </body>
</html>
"""


def copy_asset(src, project, sub, cache):
    if src in cache:
        return cache[src]
    name = os.path.basename(src)
    rel = f"assets/{sub}/{name}"
    os.makedirs(os.path.join(project, "assets", sub), exist_ok=True)
    dst = os.path.join(project, rel)
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)
    cache[src] = rel
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("project")
    ap.add_argument("--cam-pos", default="50% 40%", help="object-position of the face inside the circle")
    a = ap.parse_args()
    edit = json.load(open(a.edit))
    base = os.path.dirname(os.path.abspath(a.edit))

    def path(p):
        return p if os.path.isabs(p) else os.path.join(base, p)

    proj = a.project
    os.makedirs(os.path.join(proj, "assets", "fonts"), exist_ok=True)
    os.makedirs(os.path.join(proj, "assets", "vendor"), exist_ok=True)
    os.makedirs(os.path.join(proj, "renders"), exist_ok=True)
    for f in ("itim-thai-400-normal.woff2", "itim-latin-400-normal.woff2"):
        shutil.copy2(os.path.join(SKILL, "assets", "fonts", f), os.path.join(proj, "assets", "fonts", f))
    shutil.copy2(os.path.join(SKILL, "assets", "vendor", "gsap.min.js"), os.path.join(proj, "assets", "vendor", "gsap.min.js"))

    cache = {}
    dur = edit["duration"]
    cam = copy_asset(path(edit["facecam"]), proj, "talk", cache)
    voice_rel = "assets/talk/voice.m4a"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", path(edit["facecam"]), "-vn", "-c:a", "aac", "-b:a", "192k",
         os.path.join(proj, voice_rel)],
        check=True,
    )

    shots = []
    for i, s in enumerate(edit["shots"]):
        src = copy_asset(path(s["src"]), proj, "broll", cache)
        attrs = f'data-start="{s["start"]}" data-duration="{s["dur"]}" data-media-start="{s["media_start"]}"'
        shots.append(f'      <video id="fill-{i}" class="clip fill" src="{src}" {attrs} data-track-index="0" muted playsinline></video>')
        shots.append(f'      <video id="band-{i}" class="clip band" src="{src}" {attrs} data-track-index="1" muted playsinline></video>')

    caps = []
    for i, c in enumerate(edit["captions"]):
        d = round(max(c["end"] - c["start"] - 1 / FPS, 2 / FPS), 3)  # 1 blank frame between cards
        if c["start"] >= dur:
            continue
        d = min(d, round(dur - c["start"], 3))
        caps.append(
            f'      <div id="cap-{i}" class="clip cap" data-start="{c["start"]}" data-duration="{d}" data-track-index="3">'
            f'<span class="t">{html.escape(c["text"])}</span></div>'
        )

    music = ""
    if edit.get("music"):
        m = copy_asset(path(edit["music"]), proj, "audio", cache)
        music = (f'      <audio id="music" src="{m}" data-start="0" data-duration="{dur}" data-track-index="6" '
                 f'data-volume="{edit.get("music_volume", 0.12)}"></audio>')

    out = (TEMPLATE.replace("__SHOTS__", "\n".join(shots)).replace("__CAPS__", "\n".join(caps))
           .replace("__MUSIC__", music).replace("__CAM__", cam).replace("__VOICE__", voice_rel)
           .replace("__CAMPOS__", a.cam_pos).replace("__RING__", RING).replace("__DUR__", str(dur)).replace("__FPS__", str(FPS)))
    open(os.path.join(proj, "index.html"), "w").write(out)
    if not os.path.exists(os.path.join(proj, "hyperframes.json")):
        json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                   "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
                   "media": {"autoProxy": True}}, open(os.path.join(proj, "hyperframes.json"), "w"), indent=2)
    print(f"wrote {proj}/index.html: {len(edit['shots'])} shots, {len(caps)} captions, {dur}s")


if __name__ == "__main__":
    main()
