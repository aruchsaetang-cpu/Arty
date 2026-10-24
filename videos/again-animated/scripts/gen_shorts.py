"""Generate one vertical 20s short composition per episode, cut from renders/again-2m30s.mp4.

Run:  python3 scripts/gen_shorts.py   (writes short-ep1.html … short-ep8.html)
Render each:  npx hyperframes render -c short-epN.html -o renders/shorts/again-epN.mp4 .
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEN = 20

# (start in the film, hook line 1, hook line 2 (accent))
EPISODES = [
    (0.0, "กด snooze ไปกี่ครั้ง", "แล้ววันนี้?"),
    (22.0, "“พรุ่งนี้ค่อยเริ่ม”", "ที่ไม่เคยมาถึง"),
    (43.0, "วันที่ 1", "เริ่มแบบนี้แหละ"),
    (56.5, "ไม่มีใครบอก", "ว่ามันจะยากขนาดนี้"),
    (77.0, "วันที่เขาพลาด", "เสียงในหัวก็ดังขึ้น"),
    (103.0, "ล้มได้…", "แต่ห้ามล้มเลิก"),
    (121.0, "100 วันต่อมา", "เกิดอะไรขึ้น?"),
    (130.0, "คนในกระจก", "เริ่มคุ้นหน้าแล้ว"),
]

fonts = (ROOT / "index.html").read_text().split("<style>")[1].split("* {")[0]

for i, (start, h1, h2) in enumerate(EPISODES, 1):
    html = f'''<!doctype html>
<html lang="th">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>AGAIN. EP.{i}</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>{fonts}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #07080d; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: #07080d; color: #f6f1e7; font-family: "Kanit", sans-serif; }}
      .clip {{ position: absolute; inset: 0; }}
      .glow {{ position: absolute; left: -200px; top: -300px; width: 1480px; height: 1000px; border-radius: 50%;
               background: radial-gradient(circle, rgba(255, 210, 122, 0.16) 0%, rgba(255, 210, 122, 0) 65%); }}
      .frame {{ position: absolute; left: 0; top: 440px; width: 1080px; height: 1080px; overflow: hidden; }}
      .frame video {{ position: absolute; left: -420px; top: 0; width: 1920px; height: 1080px; inset: auto; }}
      .chip {{ position: absolute; left: 70px; top: 120px; display: flex; align-items: center; gap: 14px; font-weight: 700; font-size: 32px; letter-spacing: 0.14em; color: #d8d2c6; }}
      .chip b {{ display: block; padding: 6px 18px; border-radius: 10px; background: #ffd27a; color: #07080d; font-weight: 900; letter-spacing: 0.08em; }}
      .hook {{ position: absolute; left: 70px; right: 70px; top: 190px; display: flex; flex-direction: column; gap: 0; }}
      .hook span {{ display: block; font-weight: 900; font-size: 92px; line-height: 1.18; white-space: nowrap; }}
      .hook .acc {{ color: #ffd27a; }}
      .foot {{ position: absolute; left: 70px; right: 70px; top: 1580px; display: flex; flex-direction: column; gap: 22px; }}
      .foot-row {{ display: flex; justify-content: space-between; font-weight: 700; font-size: 36px; color: #d8d2c6; }}
      .foot-row .ep {{ color: #ffd27a; }}
      .bar {{ display: block; width: 100%; height: 12px; border-radius: 6px; background: rgba(246, 241, 231, 0.16); overflow: hidden; }}
      .bar-fill {{ display: block; width: 100%; height: 100%; background: #ffd27a; transform-origin: left center; }}
      .edge {{ position: absolute; left: 0; right: 0; height: 120px; }}
      .edge.t {{ top: 440px; background: linear-gradient(180deg, #07080d 0%, rgba(7, 8, 13, 0) 100%); }}
      .edge.b {{ top: 1400px; background: linear-gradient(0deg, #07080d 0%, rgba(7, 8, 13, 0) 100%); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{LEN}" data-width="1080" data-height="1920">
      <div id="bg" class="clip" data-start="0" data-duration="{LEN}" data-track-index="0"><div class="glow"></div></div>
      <div class="frame" id="frame">
        <video id="film" class="clip" src="renders/again-2m30s.mp4" data-start="0" data-duration="{LEN}" data-media-start="{start}" data-track-index="1" data-has-audio="true" playsinline></video>
      </div>
      <div id="ui" class="clip" data-start="0" data-duration="{LEN}" data-track-index="2">
        <div class="edge t"></div><div class="edge b"></div>
        <div class="chip" id="chip"><b>AGAIN.</b>EP.{i} / {len(EPISODES)}</div>
        <div class="hook"><span id="h1">{h1}</span><span class="acc" id="h2">{h2}</span></div>
        <div class="foot">
          <div class="foot-row"><span>ดูเต็มเรื่องได้ที่ช่อง</span><span class="ep">ตอนต่อไป →</span></div>
          <span class="bar"><span class="bar-fill" id="fill"></span></span>
        </div>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#chip", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "expo.out" }}, 0.05);
      tl.fromTo("#h1", {{ opacity: 0, y: 50 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }}, 0.15);
      tl.fromTo("#h2", {{ opacity: 0, scale: 0.8, transformOrigin: "left center" }}, {{ opacity: 1, scale: 1, transformOrigin: "left center", duration: 0.45, ease: "back.out(2)" }}, 0.55);
      tl.fromTo("#fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {LEN}, ease: "none" }}, 0);
      tl.fromTo("#frame", {{ scale: 1.0 }}, {{ scale: 1.04, duration: {LEN}, ease: "none" }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
    (ROOT / f"short-ep{i}.html").write_text(html)
print("wrote", len(EPISODES), "shorts")
