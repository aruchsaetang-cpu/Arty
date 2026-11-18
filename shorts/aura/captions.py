"""Build the HyperFrames caption composition (hf/index.html) from words.json + chunks.json.
Each chunk is a clip; each word pops in on its Whisper start time and glows while spoken; key words glow aura-white.
    python3 shorts/aura/captions.py && (cd shorts/aura/hf && hyperframes render --format png-sequence -o ../caps)"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
W = json.load(open(os.path.join(HERE, "words.json"))); C = json.load(open(os.path.join(HERE, "chunks.json")))
DUR = json.load(open(os.path.join(HERE, "beats.json")))["duration"]
clips, tw = [], []
for k, c in enumerate(C):
    s = max(0.0, c["s"] - 0.06)
    nxt = C[k + 1]["s"] - 0.06 if k + 1 < len(C) else DUR
    end = min(nxt, c["e"] + 0.9) if nxt - c["e"] > 0.9 else nxt
    spans = []
    for i in c["words"]:
        w = W[i]; cls = "w key" if w["key"] else "w"
        spans.append(f'<span id="w{i}" class="{cls}">{w["w"].replace("“", "").replace("”", "")}</span>')
        tw.append(f'tl.fromTo("#w{i}",{{opacity:0,scale:0.62,y:26}},{{opacity:1,scale:1,y:0,duration:0.16,ease:"back.out(2.4)"}},{w["s"]:.3f});')
        hot = "0 0 18px rgba(235,245,255,.95),0 0 46px rgba(190,220,255,.75)" if w["key"] else "0 0 14px rgba(255,255,255,.55)"
        tw.append(f'tl.fromTo("#w{i}",{{textShadow:"0 0 0px rgba(255,255,255,0)"}},{{textShadow:"{hot}",duration:0.08}},{w["s"]:.3f});')
        if not w["key"]:
            tw.append(f'tl.to("#w{i}",{{textShadow:"0 0 0px rgba(255,255,255,0)",duration:0.2}},{max(w["e"], w["s"] + 0.12):.3f});')
    clips.append(f'<section id="c{k}" class="clip cap" data-start="{s:.3f}" data-duration="{end - s:.3f}" data-track-index="1">'
                 f'<div class="line">{" ".join(spans)}</div></section>')
    tw.append(f'tl.to("#c{k} .line",{{opacity:0,duration:0.06}},{end - 0.06:.3f});')
html = f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1080, height=1920">
<title>Aura Monster captions</title>
<script src="vendor/gsap.min.js"></script>
<style>
@font-face {{ font-family: "Inter Display"; src: url("fonts/InterDisplay-Black.otf"); font-weight: 900; }}
html, body {{ margin: 0; background: transparent; }}
#root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
.cap {{ position: absolute; left: 0; right: 0; top: 1250px; height: 300px; display: flex; align-items: center; justify-content: center; }}
.line {{ display: block; width: 960px; text-align: center; font: 900 86px/1.12 "Inter Display", sans-serif; letter-spacing: -1px; }}
.w {{ display: inline-block; color: #fff; -webkit-text-stroke: 9px #0a0d14; paint-order: stroke fill; }}
.key {{ color: #f2f8ff; font-size: 104px; }}
</style></head>
<body>
<div id="root" data-composition-id="caps" data-start="0" data-width="1080" data-height="1920" data-duration="{DUR}" data-fps="30">
{chr(10).join(clips)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tw)}
window.__timelines["caps"] = tl;
</script>
</body></html>
"""
open(os.path.join(HERE, "hf", "index.html"), "w").write(html)
print("hf/index.html:", len(clips), "caption clips")
