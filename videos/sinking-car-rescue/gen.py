# generator for videos/keke-driver-kindness/index.html (dog-rescue style)
import sys
old=open('index.html').read()
head=old.split('<body>')[0]
helpers=old.split('<script>\n')[1].split('      // ---------- HOOK')[0]
def row(*parts): return '<div class="row">'+''.join(f'<span class="t{(" "+c) if c else ""}" id="{i}">{t}</span>' for i,c,t in parts)+'</div>'
IMG='style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"'
D=3.0; HOOK=2.43
# (shot id, footage, caption rows [(id,color,text)...], typing offsets per span, cap top)
SHOTS=[
 ("w2","s2-look.mp4",[[("w2a","","*HIS CAR")],[("w2b","","WAS"),("w2c","r","BROKEN*")]],1230),
 ("w7","s7-work.mp4",[[("k1","","*HE WORKS"),("k1b","y","HARD")],[("k2","","FOR HIS"),("k3b","g","FAMILY*")]],1230),
 ("w3","s3-speak.mp4",[[("a1","","*HE WANTED")],[("a2","","TO GO BACK"),("a2b","g","HOME*")]],1230),
 ("w4","s4-money.mp4",[[("b1","","*BUT HE HAD")],[("b2","r","NO MONEY*")]],1230),
 ("w6","s6-ride.mp4",[[("d1","","*THE DRIVER SAID")],[("d2","","IT WAS"),("d2b","g","OK"),("d2c","","AND LET")],[("d3","","HIM RIDE"),("d3b","y","FOR FREE*")]],1190),
 ("w5","s5-cash.mp4",[[("p1","","*HE PAID HIM BACK")],[("p2","","WITH A"),("p2b","y","LARGE AMOUNT")],[("p3","","OF"),("p3b","g","MONEY*")]],1190),
]
E=HOOK+D*len(SHOTS); T=round(E+2.57,2); IMP=round(E+0.05,2); Ed=round(T-E,2)
vids=[]; caps=[]; tlines=[]; sfx=[]
for k,(w,src,rows,top) in enumerate(SHOTS):
    s=round(HOOK+D*k,2)
    vids.append(f'<div class="shot" id="{w}"><video id="v{w[1:]}" class="clip" src="assets/footage/{src}" data-start="{s}" data-duration="{D}" data-track-index="0" muted playsinline></video></div>')
    caps.append(f'<div id="c{w[1:]}" class="clip ov" data-start="{s}" data-duration="{D}" data-track-index="2"><div class="cap" style="top: {top}px">'+''.join(row(*r) for r in rows)+'</div></div>')
    t=s+0.12; types=[]; first=t
    for r in rows:
        for (i,c,txt) in r:
            types.append(f'type("#{i}", {t:.2f});'); t+=len(txt)/24+0.08
        t+=0.15
    tlines.append(f'flash({s}, {0.5 if k else 0.35}); push("#{w}", {s}, {D});\n      '+' '.join(types))
    sfx.append(f'<audio id="sfx-t{k}" src="assets/audio/keyboard-typing.m4a" data-start="{first:.2f}" data-duration="{min(t-first,2.2):.2f}" data-track-index="5" data-volume="0.7"></audio>')
J='\n      '
body=f'''<body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{T}" data-width="1080" data-height="1920">
      {J.join(vids)}
      <div id="frz" class="clip" data-start="0" data-duration="2.43" data-track-index="1"><img id="frz-img" src="assets/img/freeze.jpg" alt="" {IMG} /></div>
      <div id="wend" class="clip shot" data-start="{E}" data-duration="{Ed}" data-track-index="0"><div class="shot" id="wendi"><img id="end-img" src="assets/img/freeze-end.jpg" alt="" {IMG} /></div></div>
      <div id="wendg" class="clip shot" data-start="{IMP}" data-duration="1.4" data-track-index="1" style="opacity: 0"><img src="assets/img/freeze-end.jpg" alt="" {IMG} /></div>
      <div id="grade" class="clip" data-start="0" data-duration="{T}" data-track-index="1"><div class="vig"></div></div>
      <div id="c1" class="clip ov" data-start="0" data-duration="2.43" data-track-index="2"><div class="cap" style="top: 600px"><div class="row" id="h1" style="gap: 26px"><span class="t g xl" style="font-size: 106px">*BROKEN</span><span class="t r xl" style="font-size: 106px">CAR*</span></div></div></div>
      {J.join(caps)}
      <div id="o5" class="clip ov" data-start="{IMP}" data-duration="{T-IMP:.2f}" data-track-index="2">
        <div class="cap" style="top: 1230px" id="o5-cap2"><span class="t g xl" id="o5-c">*RESPECT*</span>{row(("h2","y","THE"),("h2b","r","KINDNESS*"))}</div>
        <img id="heart" src="assets/img/mending-heart.png" alt="" style="left: 70px; top: 250px" />
      </div>
      <div id="circ" class="clip ov" data-start="0" data-duration="2.43" data-track-index="2">
        <svg class="draw" viewBox="0 0 1080 1920"><circle id="ring" cx="315" cy="1100" r="250" fill="none" stroke="#39ff14" stroke-width="13" style="filter: drop-shadow(0 0 12px #39ff14) drop-shadow(0 0 26px rgba(57,255,20,0.6))" stroke-dasharray="1572" stroke-dashoffset="1572" /></svg>
      </div>
      <div id="arr" class="clip ov" data-start="0" data-duration="2.43" data-track-index="2">
        <div id="arrow" style="position:absolute;left:525px;top:805px;width:290px;height:290px;opacity:0;filter:drop-shadow(3px 0 0 #fff) drop-shadow(-3px 0 0 #fff) drop-shadow(0 3px 0 #fff) drop-shadow(0 -3px 0 #fff) drop-shadow(0 0 16px rgba(255,46,59,0.85))"><div style="width:100%;height:100%;background:#ff1f2e;-webkit-mask:url(assets/img/arrow-mask.png) center/contain no-repeat;mask:url(assets/img/arrow-mask.png) center/contain no-repeat"></div></div>
      </div>
      {J.join(sfx)}
      <audio id="sfx-tend" src="assets/audio/keyboard-typing.m4a" data-start="{IMP+0.42:.2f}" data-duration="0.6" data-track-index="5" data-volume="0.7"></audio>
      <audio id="sfx-shutter1" src="assets/audio/camera-shutter.m4a" data-start="0.93" data-duration="0.36" data-track-index="4" data-volume="1"></audio>
      <audio id="sfx-ding-hook" src="assets/audio/ding.m4a" data-start="0.93" data-duration="1.4" data-track-index="6" data-volume="0.7"></audio>
      <audio id="sfx-shutter3" src="assets/audio/camera-shutter.m4a" data-start="{IMP}" data-duration="0.36" data-track-index="4" data-volume="1"></audio>
      <audio id="sfx-bell" src="assets/audio/bell-ding.m4a" data-start="{IMP+0.05:.2f}" data-duration="1.13" data-track-index="6" data-volume="0.6"></audio>
      <div id="fx" class="clip" data-start="0" data-duration="{T}" data-track-index="3">
        <div class="wm">LIFE IN FRAME</div><div id="flash"></div><div id="leak"></div><div id="fade"></div><div id="loop"></div>
      </div>
    </div>
'''
I=IMP
tl='<script>\n'+helpers+f'''      // ---------- HOOK ----------
      const HIT = 0.93;
      flash(HIT, 0.95);
      // frame 0 = the finished hook picture: zoomed wheel + green circle + red arrow + BROKEN CAR
      tl.set("#h1", {{ opacity: 1 }}, 0);
      tl.set("#ring", {{ strokeDashoffset: 0 }}, 0);
      tl.set("#arrow", {{ opacity: 1 }}, 0);
      tl.fromTo("#frz-img", {{ scale: 1.2, transformOrigin: "32% 55%" }}, {{ scale: 1.3, transformOrigin: "32% 55%", duration: 2.43, ease: "none" }}, 0);
      tl.fromTo("#frz", {{ scale: 1.07 }}, {{ scale: 1.0, duration: 0.3, ease: "power3.out", immediateRender: false }}, HIT);
      tl.to(["#ring", "#arrow"], {{ opacity: 0, duration: 0.15 }}, 2.3);
      // ---------- STORY (a cut every 3s) ----------
      {J.join(tlines)}
      // ---------- ENDING: RESPECT THE KINDNESS ----------
      tl.fromTo("#end-img", {{ scale: 1.0, transformOrigin: "55% 40%" }}, {{ scale: 1.12, transformOrigin: "55% 40%", duration: {Ed}, ease: "none" }}, {E});
      flash({I}, 0.95);
      tl.fromTo("#wendi", {{ scale: 1.0, filter: "blur(0px) brightness(1)" }}, {{ scale: 1.45, filter: "blur(18px) brightness(2.1)", duration: 0.07, ease: "power4.out" }}, {I-0.02:.2f});
      tl.to("#wendi", {{ scale: 1.0, filter: "blur(0px) brightness(1)", duration: 0.6, ease: "power3.out" }}, {I+0.05:.2f});
      tl.fromTo("#leak", {{ opacity: 0, x: 0, scale: 1.3 }}, {{ opacity: 1, x: 0, scale: 1.3, duration: 0.06 }}, {I-0.02:.2f});
      tl.to("#leak", {{ opacity: 0, x: 300, duration: 0.7, ease: "power2.out" }}, {I+0.08:.2f});
      tl.fromTo("#wendg", {{ opacity: 0, x: 0, scale: 1.0 }}, {{ opacity: 0.5, x: 70, scale: 1.18, duration: 0.08, ease: "none" }}, {I});
      tl.to("#wendg", {{ opacity: 0, x: 18, scale: 1.04, duration: 1.0, ease: "power2.out" }}, {I+0.1:.2f});
      tl.fromTo("#wend", {{ x: 0, y: 0 }}, {{ keyframes: [{{ x: -26, y: 14, duration: 0.05 }}, {{ x: 22, y: -12, duration: 0.05 }}, {{ x: -14, y: 8, duration: 0.06 }}, {{ x: 9, y: -5, duration: 0.07 }}, {{ x: -4, y: 2, duration: 0.08 }}, {{ x: 0, y: 0, duration: 0.09 }}], ease: "none", immediateRender: false }}, {I+0.02:.2f});
      tl.fromTo("#o5-c", {{ scale: 2.6, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.18, ease: "expo.out" }}, {I});
      tl.fromTo("#heart", {{ scale: 3.2, rotation: -18, opacity: 0, filter: "blur(10px) brightness(1.8)", transformOrigin: "50% 60%" }}, {{ scale: 1, rotation: 0, opacity: 1, filter: "blur(0px) brightness(1)", transformOrigin: "50% 60%", duration: 0.22, ease: "expo.out" }}, {I});
      tl.fromTo("#heart", {{ x: 0, y: 0 }}, {{ keyframes: [{{ x: -18, y: 10, duration: 0.05 }}, {{ x: 15, y: -8, duration: 0.05 }}, {{ x: -9, y: 5, duration: 0.06 }}, {{ x: 5, y: -3, duration: 0.07 }}, {{ x: 0, y: 0, duration: 0.08 }}], ease: "none", immediateRender: false }}, {I+0.22:.2f});
      tl.fromTo("#heart", {{ scale: 1 }}, {{ scale: 1.1, duration: 0.3, yoyo: true, repeat: 1, ease: "sine.inOut", transformOrigin: "50% 60%", immediateRender: false }}, {I+0.7:.2f});
      type("#h2", {I+0.42:.2f}); type("#h2b", {I+0.62:.2f});
      // blur out -> black -> first frame (loop)
      tl.to("#wendi", {{ scale: 1.35, filter: "blur(16px) brightness(0.8)", duration: 0.45, ease: "power2.in" }}, {T-0.7:.2f});
      tl.to(["#o5-cap2", "#heart"], {{ opacity: 0, scale: 1.3, duration: 0.35, ease: "power2.in" }}, {T-0.65:.2f});
      tl.fromTo("#fade", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2, ease: "power1.in" }}, {T-0.45:.2f});
      tl.fromTo("#loop", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, ease: "power1.out" }}, {T-0.25:.2f});

      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
'''
open('index.html','w').write(head+body+tl)
print("T",T,"E",E)
