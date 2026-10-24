"""Shared builders for Hollow Truth shorts: root index, title scenes, captions, mood dips."""
import os

FLICK = '''    const flick = (sel, at) => {
      [[0, 1], [0.05, 0.15], [0.09, 1], [0.17, 0.35], [0.22, 1]].forEach(([dt, o]) => tl.set(sel, { opacity: o }, at + dt));
    };
'''
BASE_CSS = '''    #root {
      position: absolute;
      inset: 0;
    }
    #root span {
      display: inline-block;
    }
    .t-display {
      position: absolute;
      left: 0;
      width: 1080px;
      text-align: center;
      font-family: var(--font-display, "League Gothic"), sans-serif;
      line-height: 1;
      color: var(--bone, #ddd3b4);
      text-shadow: 0 6px 0 rgba(0, 0, 0, 0.6);
    }
    .t-body {
      position: absolute;
      left: 0;
      width: 1080px;
      text-align: center;
      font-family: var(--font-body, "Oswald"), sans-serif;
      font-weight: 600;
      color: #ffffff;
      text-shadow: 0 3px 0 rgba(0, 0, 0, 0.7);
    }
    .t-stamp-in {
      background: var(--accent, #e0352b);
      color: #ffffff;
      padding: 6px 22px 10px;
    }
'''


def el(id, cls, start, dur, text, style, extra=""):
    return (f'    <div id="{id}" class="{cls} clip" data-start="{start}" data-duration="{dur}" style="{style}"{extra}>\n'
            f'      <span id="{id}-in">{text}</span>\n    </div>')


def scene(id, css, body, script):
    return f'''<template>
  <style>
{BASE_CSS}{css}  </style>
  <div id="root" data-composition-id="{id}" data-width="1080" data-height="1920">
{body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{FLICK}{script}
    window.__timelines["{id}"] = tl;
  </script>
</template>
'''


def host(id, st, d, ti, kind, z):
    return f'''      <div
        id="{id}"
        data-composition-id="{id}"
        data-composition-src="compositions/{id}.html"
        data-start="{st}"
        data-duration="{d}"
        data-track-index="{ti}"
        data-track-kind="{kind}"
        data-width="1080"
        data-height="1920"
        style="z-index: {z}"
      ></div>
'''


def write_project(proj, world_id, world_comment, bg, scenes, captions, dips):
    """scenes: list of (id, start, dur, css, body, script)."""
    for id, st, d, css, body, script in scenes:
        open(os.path.join(proj, f"compositions/{id}.html"), "w").write(scene(id, css, body, script))
    hosts = "".join(host(id, st, d, 2, "graphics", 3) for id, st, d, *_ in scenes)
    index = f'''<!doctype html>
<html
  lang="en"
  data-resolution="portrait"
  data-composition-variables='[
    {{"id":"accent","type":"color","label":"Accent (warning red)","default":"#e0352b"}},
    {{"id":"bone","type":"color","label":"Title ink","default":"#ddd3b4"}}
  ]'
>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
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
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: {bg};
      }}
      #root {{
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: {bg};
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="20"
      data-width="1080"
      data-height="1920"
    >
      <!-- {world_comment} -->
{host(world_id, 0, 20, 1, "graphics", 1)}
      <!-- Night mood: fog, vignette, grain, projector dips at each beat -->
{host("mood", 0, 20, 6, "graphics", 2)}
      <!-- Beat titles, one scene per voiceover line -->
{hosts}
      <!-- Burned-in captions for muted viewers -->
{host("captions", 0, 20, 3, "captions", 4)}
      <audio
        id="voiceover"
        class="clip"
        src="assets/audio/voiceover.m4a"
        data-start="0"
        data-duration="20"
        data-track-index="4"
        data-volume="1"
      ></audio>
      <audio
        id="bed"
        class="clip"
        src="assets/audio/bed.m4a"
        data-start="0"
        data-duration="20"
        data-track-index="5"
        data-volume="1"
      ></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
'''
    open(os.path.join(proj, "index.html"), "w").write(index)
    divs = "\n".join(f'    <div id="cap-{i}" class="cap clip" data-start="{s}" data-duration="{round(e - s, 2)}"><span id="cap-{i}-in">{t}</span></div>'
                     for i, (s, e, t) in enumerate(captions))
    tw = "\n".join(f'    pop("#cap-{i}-in", {s});' for i, (s, e, t) in enumerate(captions))
    cap = f'''<template>
  <style>
    #root {{
      position: absolute;
      inset: 0;
    }}
    .cap {{
      position: absolute;
      left: 0;
      top: 1190px;
      width: 1080px;
      text-align: center;
      overflow: visible;
    }}
    .cap span {{
      display: inline-block;
      font-family: var(--font-body, "Oswald"), sans-serif;
      font-weight: 600;
      font-size: 66px;
      line-height: 1.1;
      color: #ffffff;
      -webkit-text-stroke: 12px #050e10;
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
{tw}
    window.__timelines["captions"] = tl;
  </script>
</template>
'''
    open(os.path.join(proj, "compositions/captions.html"), "w").write(cap)
    p = os.path.join(proj, "compositions/mood.html")
    s = open(p).read()
    import re
    s = re.sub(r"\[[0-9., ]+\]\.forEach\(\(at\)", f"[{', '.join(str(d) for d in dips)}].forEach((at)", s)
    open(p, "w").write(s)
