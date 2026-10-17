#!/usr/bin/env python3
"""Generate the 2D animated scenes for the Tesla Roadster short as HyperFrames projects.

Each scene is a 1080x1920 composition with constant camera motion; render.sh in
scenes/ turns them into clips/<name>.mp4 that the edit skill cuts together.
"""
import os, shutil, math

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "..", ".claude", "skills", "edit", "assets")
OUT = os.path.join(HERE, "scenes")
W, H = 1080, 1920

RED, RED_D, GLASS = "#d3122c", "#8e0a1c", "#14222f"

CAR_SIDE = f"""<svg viewBox="0 0 600 210" width="600" height="210">
 <ellipse cx="300" cy="200" rx="270" ry="10" fill="rgba(0,0,0,.25)"/>
 <path d="M28,150 C26,124 58,108 112,102 L205,96 C245,62 300,46 360,49 C410,51 452,72 482,97 L560,107
          C586,112 597,128 594,148 L590,166 L30,166 Z" fill="{RED}"/>
 <path d="M30,140 L594,140 L590,166 L30,166 Z" fill="{RED_D}"/>
 <path d="M218,96 C252,67 300,58 355,60 C394,62 424,75 448,96 Z" fill="{GLASS}"/>
 <path d="M240,92 C262,74 292,67 318,66 L300,92 Z" fill="rgba(255,255,255,.18)"/>
 <path d="M60,120 L560,124" stroke="rgba(255,255,255,.35)" stroke-width="4"/>
 <ellipse cx="578" cy="124" rx="12" ry="6" fill="#fff6c8"/>
 <g><circle cx="140" cy="164" r="40" fill="#0d0d0f"/><circle cx="140" cy="164" r="23" fill="#a7b0ba"/><circle cx="140" cy="164" r="8" fill="#333"/></g>
 <g><circle cx="480" cy="164" r="40" fill="#0d0d0f"/><circle cx="480" cy="164" r="23" fill="#a7b0ba"/><circle cx="480" cy="164" r="8" fill="#333"/></g>
</svg>"""

CAR_TOP = f"""<svg viewBox="0 0 360 760" width="360" height="760">
 <rect x="20" y="20" width="320" height="720" rx="150" fill="{RED}"/>
 <rect x="40" y="200" width="280" height="330" rx="70" fill="{GLASS}"/>
 <rect x="70" y="300" width="95" height="150" rx="28" fill="#2c3a48"/>
 <rect x="195" y="300" width="95" height="150" rx="28" fill="#2c3a48"/>
 <rect x="80" y="280" width="75" height="34" rx="14" fill="#3a4a5a"/>
 <rect x="205" y="280" width="75" height="34" rx="14" fill="#3a4a5a"/>
 <circle cx="235" cy="250" r="34" fill="none" stroke="#5b6b7b" stroke-width="10"/>
 <rect x="60" y="40" width="240" height="40" rx="20" fill="#fff6c8" opacity=".8"/>
</svg>"""

HEAD = """<!doctype html><html lang="th"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=1080, height=1920"/>
<script src="gsap.min.js"></script>
<style>
@font-face { font-family: "Kanit"; font-weight: 800; src: url(kanit-thai-700-normal.woff2) format("woff2"); }
@font-face { font-family: "Montserrat"; font-weight: 800; src: url(montserrat-latin-800-normal.woff2) format("woff2"); }
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:1080px; height:1920px; overflow:hidden; background:#000; }
#root { position:relative; width:1080px; height:1920px; overflow:hidden; }
#cam { position:absolute; inset:0; transform-origin:50% 45%; }
.abs { position:absolute; }
.sky { position:absolute; inset:0; background:linear-gradient(#0a8fd6 0%, #36b6ee 45%, #8fe3ff 100%); }
.ground { position:absolute; left:-200px; right:-200px; top:1380px; bottom:-200px; background:linear-gradient(#5f6670, #3d434b); }
.ground::after { content:""; position:absolute; left:0; right:0; top:120px; height:14px;
  background:repeating-linear-gradient(90deg,#f2f2f2 0 120px,transparent 120px 220px); opacity:.8; }
.puff { position:absolute; width:120px; height:120px; border-radius:50%;
  background:radial-gradient(circle,#fff 0 40%,rgba(255,255,255,.6) 60%,rgba(255,255,255,0) 72%); }
.th { font-family:"Kanit","Montserrat",sans-serif; font-weight:800; color:#fff; }
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="1080" data-height="1920">
<div id="cam">
"""

TAIL = """
</div></div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
tl.fromTo("#cam", {{scale:{c0}}}, {{scale:{c1}, duration:{dur}, ease:"none"}}, 0);
{js}
window.__timelines["main"] = tl;
tl.seek(0);
</script></body></html>"""


def lcg(seed):
    x = seed
    while True:
        x = (x * 1103515245 + 12345) & 0x7fffffff
        yield x / 0x7fffffff


def puffs(prefix, n, cx, cy, spread, t0, t1, seed, size=1.0, drift=(0, -60)):
    """Deterministic expanding smoke/gas puffs."""
    r = lcg(seed); html, js = [], []
    for i in range(n):
        x = cx + (next(r) - .5) * spread; y = cy + (next(r) - .5) * spread * .4
        t = t0 + (t1 - t0) * i / n
        s = size * (1.2 + next(r) * 2)
        html.append(f'<div id="{prefix}{i}" class="puff" style="left:{x - 60:.0f}px;top:{y - 60:.0f}px;opacity:0"></div>')
        js.append(f'tl.fromTo("#{prefix}{i}",{{scale:.2,opacity:.95,x:0,y:0}},{{immediateRender:false,scale:{s:.2f},opacity:0,x:{drift[0] * (next(r) - .5) * 2:.0f},y:{drift[1]:.0f},duration:1.1,ease:"power2.out"}},{t:.2f});')
    return "".join(html), "".join(js)


def speedlines(prefix, t0, t1):
    r = lcg(5); html, js = [], []
    for i in range(16):
        y = 200 + next(r) * 1400; w = 300 + next(r) * 500
        html.append(f'<div id="{prefix}{i}" class="abs" style="left:1100px;top:{y:.0f}px;width:{w:.0f}px;height:6px;border-radius:3px;background:rgba(255,255,255,.85)"></div>')
        js.append(f'tl.fromTo("#{prefix}{i}",{{x:0}},{{x:-2600,duration:.45,ease:"none",repeat:{int((t1 - t0) / .45)}}},{t0 + next(r) * .4:.2f});')
    return "".join(html), "".join(js)


def loop_ramp(cx, cy, r, sweep_from=180, sweep_to=360):
    """SVG half-loop ramp (track drawn on an arc)."""
    a0, a1 = math.radians(sweep_from), math.radians(sweep_to)
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    return (f'<svg class="abs" style="left:0;top:0" width="{W}" height="{H}">'
            f'<path d="M{x0:.0f},{y0:.0f} A{r},{r} 0 0 1 {x1:.0f},{y1:.0f}" fill="none" stroke="#c9ced6" stroke-width="70"/>'
            f'<path d="M{x0:.0f},{y0:.0f} A{r},{r} 0 0 1 {x1:.0f},{y1:.0f}" fill="none" stroke="#e9ecf0" stroke-width="18" stroke-dasharray="60 40"/>'
            f'<rect x="{cx - r - 40}" y="{cy}" width="80" height="{H - cy}" fill="#8b929c"/>'
            f'<rect x="{cx + r - 40}" y="{cy}" width="80" height="{H - cy}" fill="#8b929c"/></svg>')


SCENES = {}

# 1. HOOK: car leaves the inverted ramp, upside down mid-air
h_sl, j_sl = speedlines("sl", 0, 4)
SCENES["s1_hook"] = dict(dur=4, c0=1.12, c1=1.0, html=f"""
<div class="sky"></div>{loop_ramp(260, 1250, 520, 200, 300)}
<div id="car" class="abs" style="left:240px;top:620px">{CAR_SIDE}</div>{h_sl}""",
    js=j_sl + 'tl.fromTo("#car",{x:-120,y:-60,rotation:185},{x:220,y:120,rotation:150,duration:4,ease:"none"},0);')

# 2. CONTEXT: SpaceX-style test site in Texas (generic, no logos)
SCENES["s2_site"] = dict(dur=4, c0=1.0, c1=1.1, html="""
<div class="abs" style="inset:0;background:linear-gradient(#f2a65a 0%,#f6d08a 40%,#bfe6f2 70%)"></div>
<div class="abs" style="left:-100px;right:-100px;top:1150px;bottom:0;background:linear-gradient(#d8b07e,#b98a58)"></div>
<div id="tower" class="abs" style="left:160px;top:640px;width:90px;height:520px;background:#5a6370"></div>
<div class="abs" style="left:110px;top:600px;width:190px;height:60px;background:#46505c"></div>
<div id="tank" class="abs" style="left:700px;top:880px;width:220px;height:280px;border-radius:110px 110px 10px 10px;background:#e7ecf1"></div>
<div class="abs" style="left:380px;top:1080px;width:280px;height:80px;border-radius:140px 140px 0 0;border:22px solid #9aa2ad;border-bottom:none"></div>
<div id="sun" class="abs" style="left:640px;top:300px;width:220px;height:220px;border-radius:50%;background:#fff3c4;box-shadow:0 0 120px 60px rgba(255,220,140,.7)"></div>
<div class="abs th" style="left:0;right:0;top:1290px;text-align:center;font-size:64px;color:#5b3a1a;opacity:.85">TEXAS</div>""",
    js='tl.fromTo("#sun",{y:20},{y:-30,duration:4,ease:"none"},0);')

# 3. CONTEXT: car drives up the half-loop and sticks upside down
SCENES["s3_loop"] = dict(dur=5, c0=1.0, c1=1.08, html=f"""
<div class="sky"></div><div class="ground"></div>{loop_ramp(540, 900, 380, 180, 360)}
<div id="orbit" class="abs" style="left:540px;top:900px;width:0;height:0">
 <div class="abs" style="left:-300px;top:{380 - 35 - 180}px;transform:scale(.6);transform-origin:300px 180px">{CAR_SIDE}</div></div>""",
    js='tl.fromTo("#orbit",{rotation:75},{rotation:182,duration:4.2,ease:"power1.inOut"},0);')

# 4. CONTEXT: SpaceX cold-gas thrusters flip the car upright
p4h, p4j = puffs("p4_", 14, 540, 760, 260, 0.2, 3.2, 11, 1.4, (0, -40))
SCENES["s4_thrusters"] = dict(dur=4, c0=1.15, c1=1.02, html=f"""
<div class="sky"></div>
<div id="car" class="abs" style="left:240px;top:780px;transform-origin:300px 105px">{CAR_SIDE}</div>{p4h}""",
    js=p4j + 'tl.fromTo("#car",{rotation:180,y:-40},{rotation:0,y:60,duration:3.2,ease:"power2.inOut"},0.3);')

# 5. CONTEXT: brief hover, then lands in a cloud of smoke
p5h, p5j = puffs("p5_", 22, 540, 1400, 900, 2.3, 4.6, 23, 2.2, (300, -120))
SCENES["s5_land"] = dict(dur=5, c0=1.0, c1=1.1, html=f"""
<div class="sky"></div><div class="ground"></div>
<div id="car" class="abs" style="left:240px;top:700px">{CAR_SIDE}</div>{p5h}""",
    js=p5j + 'tl.fromTo("#car",{y:-40},{y:20,duration:.6,yoyo:true,repeat:3,ease:"sine.inOut"},0);'
              'tl.to("#car",{y:520,duration:.5,ease:"power3.in"},2.4);')

# 6. CONTEXT: "flying cars are real" quote on stage (no likeness of any real person)
SCENES["s6_quote"] = dict(dur=4, c0=1.0, c1=1.12, html="""
<div class="abs" style="inset:0;background:radial-gradient(ellipse at 50% 30%,#2a3b55 0%,#0b0f18 70%)"></div>
<div class="abs" style="left:240px;top:-100px;width:600px;height:1700px;background:linear-gradient(rgba(255,255,230,.35),rgba(255,255,230,0));clip-path:polygon(40% 0,60% 0,100% 100%,0 100%)"></div>
<div class="abs" style="left:-50px;right:-50px;top:1380px;bottom:0;background:#141a24"></div>
<div id="q" class="abs" style="left:90px;right:90px;top:640px;padding:60px 50px;border-radius:30px;background:rgba(255,255,255,.95);text-align:center">
 <div style="font-family:Montserrat;font-weight:800;font-size:150px;line-height:.6;color:#d3122c">&ldquo;</div>
 <div style="font-family:Montserrat;font-weight:800;font-size:96px;line-height:1.05;color:#111">Flying cars<br/>are real</div>
 <div class="th" style="margin-top:28px;font-size:44px;color:#666">— อีลอน มัสก์</div></div>""",
    js='tl.fromTo("#q",{scale:.7,opacity:0},{scale:1,opacity:1,duration:.25,ease:"back.out(2.5)"},0.15);')

# 7. BUT: nobody in the driver's seat
SCENES["s7_empty"] = dict(dur=4, c0=1.18, c1=1.0, html=f"""
<div class="abs" style="inset:0;background:#4b525c"></div>
<div class="abs" style="left:520px;top:0;width:40px;height:1920px;background:repeating-linear-gradient(#f2f2f2 0 120px,transparent 120px 220px);opacity:.7"></div>
<div id="car" class="abs" style="left:360px;top:560px">{CAR_TOP}</div>
<div id="hl" class="abs" style="left:415px;top:840px;width:150px;height:200px;border-radius:40%;background:rgba(255,232,0,.6);box-shadow:0 0 80px 40px rgba(255,232,0,.7)"></div>""",
    js='tl.fromTo("#hl",{opacity:0},{opacity:1,duration:.3,yoyo:true,repeat:5,ease:"sine.inOut"},0.5);')

# 8. REVEAL: remote-controlled, spectators far away
SCENES["s8_remote"] = dict(dur=4, c0=1.0, c1=1.1, html=f"""
<div class="sky"></div><div class="ground" style="top:1000px"></div>
<div class="abs" style="left:700px;top:880px;transform:scale(.28);transform-origin:0 0">{CAR_SIDE}</div>
<div id="pad" class="abs" style="left:120px;top:1180px;width:840px;height:520px;border-radius:120px;background:#1d2128;box-shadow:0 30px 60px rgba(0,0,0,.5)">
 <div id="stick" class="abs" style="left:150px;top:170px;width:180px;height:180px;border-radius:50%;background:#3b414c;box-shadow:inset 0 -10px 0 #2a2f37"></div>
 <div class="abs" style="left:560px;top:150px;width:90px;height:90px;border-radius:50%;background:#d3122c"></div>
 <div class="abs" style="left:640px;top:260px;width:90px;height:90px;border-radius:50%;background:#2bb3ff"></div></div>
<div class="abs th" style="left:0;right:0;top:600px;text-align:center;font-size:60px;color:#0b3a5a">← ระยะปลอดภัย →</div>""",
    js='tl.fromTo("#stick",{x:-25},{x:25,duration:.5,yoyo:true,repeat:7,ease:"sine.inOut"},0);')

# 9. REVEAL: not approved for road use / no flight certification
SCENES["s9_stamp"] = dict(dur=4, c0=1.0, c1=1.08, html=f"""
<div class="abs" style="inset:0;background:linear-gradient(#5aa9d6,#9fd8ef)"></div><div class="ground" style="top:1200px"></div>
<div class="abs" style="left:240px;top:880px">{CAR_SIDE}</div>
<div id="stamp" class="abs th" style="left:110px;right:110px;top:560px;padding:30px 20px;text-align:center;border:16px solid #e01b2f;border-radius:30px;color:#e01b2f;font-size:92px;line-height:1.1;background:rgba(255,255,255,.85);transform:rotate(-8deg)">ไม่ได้รับอนุญาต<br/>ให้วิ่งบนถนน</div>""",
    js='tl.fromTo("#stamp",{scale:2.4,opacity:0},{scale:1,opacity:1,duration:.22,ease:"power4.in"},0.4);')

# 10. ENDING: the car flies off — "not yet"
h10, j10 = speedlines("s10", 0, 3)
SCENES["s10_end"] = dict(dur=3, c0=1.0, c1=1.15, html=f"""
<div class="sky"></div>
<div id="car" class="abs" style="left:240px;top:900px">{CAR_SIDE}</div>
<div id="qm" class="abs" style="left:0;right:0;top:420px;text-align:center;font-family:Montserrat;font-weight:800;font-size:320px;color:#fff;text-shadow:0 10px 30px rgba(0,0,0,.35)">?</div>{h10}""",
    js=j10 + 'tl.fromTo("#car",{x:0,y:0,rotation:0},{x:300,y:-700,rotation:-18,scale:.4,duration:3,ease:"power1.in"},0);'
              'tl.fromTo("#qm",{scale:0},{scale:1,duration:.3,ease:"back.out(3)"},1.2);')


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, s in SCENES.items():
        d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
        for f in ("gsap.min.js", "kanit-thai-700-normal.woff2", "montserrat-latin-800-normal.woff2"):
            shutil.copy(os.path.join(ASSETS, f), d)
        html = HEAD.replace("{dur}", str(s["dur"])) + s["html"] + TAIL.format(dur=s["dur"], c0=s["c0"], c1=s["c1"], js=s["js"])
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(html)
        open(os.path.join(d, "meta.json"), "w").write('{"id":"%s","name":"%s"}' % (name, name))
        open(os.path.join(d, "hyperframes.json"), "w").write("{}")
    print("scenes:", ", ".join(SCENES))


if __name__ == "__main__":
    main()
