#!/usr/bin/env python3
"""Generate the 3D (Three.js) shots for the Tesla Roadster short as HyperFrames projects.

Every shot looks at the same continuous 3D event (lib/world.js carPose) from a
different camera, so cuts between shots stay consistent.  Render with:
  for d in shots3d/*/; do (cd $d && hyperframes render -o ../../clips3d/$(basename $d).mp4); done
"""
import os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "lib")
ASSETS = os.path.join(HERE, "..", "..", ".claude", "skills", "edit", "assets")
OUT = os.path.join(HERE, "shots3d")

PAGE = """<!doctype html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=1080, height=1920"/>
<script type="importmap">{{"imports":{{"three":"./three.module.js"}}}}</script>
<style>
@font-face {{ font-family: "Montserrat"; font-weight: 800; src: url(montserrat-latin-800-normal.woff2) format("woff2"); }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:1080px; height:1920px; overflow:hidden; background:{bg}; }}
#root {{ position:relative; width:1080px; height:1920px; overflow:hidden; background:{bg}; }}
#c {{ position:absolute; inset:0; width:1080px; height:1920px; display:block; }}
.ov {{ position:absolute; font-family:Montserrat,sans-serif; font-weight:800; }}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="1080" data-height="1920">
<canvas id="c"></canvas>
{overlay}
</div>
<script type="module">
import {{ makeStage, addSite, addLoop, makeCar, placeCar, carPose, makePuffs, EV, LOOP, v3, lerpV, ease, clamp01, THREE }} from "./world.js";
const {{ renderer, scene, camera }} = makeStage(document.getElementById("c"), {opts});
const car = makeCar(); scene.add(car);
const $ = (id) => document.getElementById(id);
{setup}
function renderAt(t) {{
{body}
  renderer.render(scene, camera);
}}
window.addEventListener("hf-seek", (ev) => renderAt(ev.detail.time));
renderAt(window.__hfThreeTime || 0);
</script></body></html>
"""

SKY = "linear-gradient(#0a8fd6 0%, #45bdf0 55%, #a6e8ff 100%)"

# thruster gas: 4 nozzles on the car's roof corners, blowing along the car's local "up"
THRUSTERS = """
const gas = makePuffs(scene, { n: 70, t0: EV.flipStart - 0.25, t1: EV.flipEnd + 0.9, seed: 7, life: 0.75, size: 1.3, grow: 3.4, speed: 5, color: 0xcfdbe4, opacity: 1 });
function gasEmit(born, p) {
  const ps = carPose(born), c = Math.cos(ps.rotZ), s = Math.sin(ps.rotZ);
  const lx = p.jx > 0 ? 1.4 : -1.4, ly = 1.1;                 // nozzle in car space
  return { pos: v3(ps.x + lx * c - ly * s, ps.y + lx * s + ly * c, p.jz > 0 ? 0.8 : -0.8),
           dir: v3(-s, c, 0) };   // blow out of the roof side (car local +y)
}
"""
SMOKE = """
const smoke = makePuffs(scene, { n: 60, t0: EV.hoverEnd + 0.35, t1: EV.land + 0.5, seed: 21, life: 1.8, size: 2.4, grow: 3.5, speed: 3.5, color: 0xf3f0ea, opacity: 0.85 });
function smokeEmit(born, p) {
  const ps = carPose(EV.land);
  return { pos: v3(ps.x + p.jx * 3, 0.4, p.jz * 3), dir: v3(p.jx * 2, 0.25, p.jz * 2).normalize() };
}
"""

SHOTS = {
    # Hook: low angle as the car leaves the loop upside down, thrusters start
    "a_hook": dict(dur=3, setup="addSite(scene); addLoop(scene);" + THRUSTERS, body="""
  const e = 3.35 + t * 0.75, ps = carPose(e);
  placeCar(car, ps, e * 9); gas.update(e, gasEmit);
  const k = t / 3;
  camera.position.copy(lerpV(v3(-1, 0.8, 13), v3(-4.5, 1.2, 11), k));
  camera.lookAt(ps.x, ps.y + 0.6, 0);"""),
    # Context: drone shot of the test site, car approaching the ramp
    "b_site": dict(dur=4, setup="addSite(scene); addLoop(scene);", body="""
  const e = t * 0.5, ps = carPose(e);
  placeCar(car, ps, e * 9);
  const k = t / 4;
  camera.position.copy(lerpV(v3(26, 24, 44), v3(18, 17, 36), k));
  camera.lookAt(-6, 3, 0);"""),
    # Context: side tracking shot around the half-loop
    "c_loop": dict(dur=4.5, setup="addSite(scene); addLoop(scene);", body="""
  const e = 1.55 + t * 0.52, ps = carPose(e);
  placeCar(car, ps, e * 9);
  camera.position.set(ps.x * 0.35 + 2, LOOP.R * 0.9, 24 - t * 0.8);
  camera.lookAt(ps.x * 0.6, LOOP.R * 0.95, 0);"""),
    # Context: close-up of the thruster flip
    "d_thrusters": dict(dur=4, setup="addSite(scene); addLoop(scene);" + THRUSTERS, body="""
  const e = 4.05 + t * 0.45, ps = carPose(e);
  placeCar(car, ps, 0); gas.update(e, gasEmit);
  const k = ease(t / 4);
  camera.position.set(ps.x + 3.2 - 1.6 * k, ps.y - 0.6 + 0.4 * k, 7.2 - 1.2 * k);
  camera.lookAt(ps.x, ps.y + 0.5, 0);"""),
    # Context: hover then land in a cloud of smoke
    "e_land": dict(dur=4.5, setup="addSite(scene); addLoop(scene);" + THRUSTERS + SMOKE, body="""
  const e = 5.45 + t * 0.62, ps = carPose(e);
  placeCar(car, ps, 0); gas.update(e, gasEmit); smoke.update(e, smokeEmit);
  const k = t / 4.5;
  camera.position.copy(lerpV(v3(ps.x + 9, 2.2, 15), v3(ps.x + 7, 1.6, 12.5), k));
  camera.lookAt(ps.x, 1.3, 0);"""),
    # Quote: dark stage, spotlight, quote card
    "f_quote": dict(dur=4, bg="radial-gradient(ellipse at 50% 35%, #263752 0%, #090c14 70%)",
        opts="{ hemi: 0.35, sun: 0.0, exposure: 1.0 }",
        overlay="""<div id="q" class="ov" style="left:90px;right:90px;top:560px;padding:56px 40px;border-radius:30px;background:rgba(255,255,255,.96);text-align:center;box-shadow:0 30px 80px rgba(0,0,0,.6)">
 <div style="font-size:150px;line-height:.6;color:#c8102a">&ldquo;</div>
 <div style="font-size:100px;line-height:1.05;color:#111">Flying cars<br/>are real</div>
 <div style="margin-top:26px;font-size:44px;color:#777">— Elon Musk</div></div>""",
        setup="""
car.visible = false;
const floor = new THREE.Mesh(new THREE.CircleGeometry(30, 48), new THREE.MeshStandardMaterial({ color: 0x15181f, roughness: 0.4, metalness: 0.3 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const spot = new THREE.SpotLight(0xfff4dc, 900, 40, 0.42, 0.5, 1.4); spot.position.set(0, 16, 2); spot.castShadow = true; scene.add(spot, spot.target);
const pod = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.65, 1.2, 32), new THREE.MeshStandardMaterial({ color: 0x2a2f3a, metalness: 0.5, roughness: 0.3 }));
pod.position.set(0, 0.6, 0); pod.castShadow = true; scene.add(pod);
const cone = new THREE.Mesh(new THREE.ConeGeometry(4.2, 16, 40, 1, true), new THREE.MeshBasicMaterial({ color: 0xfff4dc, transparent: true, opacity: 0.07, depthWrite: false, side: THREE.DoubleSide }));
cone.position.set(0, 8, 2); scene.add(cone);""", body="""
  const k = t / 4;
  camera.position.set(0, 2.2 + k * 0.4, 10 - k * 2.2); camera.lookAt(0, 3.2, 0);
  const a = clamp01((t - 0.15) / 0.25);
  $("q").style.opacity = a; $("q").style.transform = `scale(${0.7 + 0.3 * (1 - Math.pow(1 - a, 3)) + (a >= 1 ? 0.02 * (t - 0.4) : 0)})`;"""),
    # But: top-down through the glass roof, nobody inside
    "g_empty": dict(dur=4, opts="{ fov: 32 }",
        overlay="""<div id="hl" class="ov" style="width:230px;height:300px;margin:-150px 0 0 -115px;border-radius:45%;background:rgba(255,232,0,.45);box-shadow:0 0 90px 45px rgba(255,232,0,.55);mix-blend-mode:screen"></div>""",
        setup="addSite(scene);", body="""
  placeCar(car, { x: 0, y: 0, rotZ: 0 }, 0);
  const k = t / 4;
  camera.up.set(1, 0, -0.35 + 0.3 * k).normalize();
  camera.position.set(0.15, 12.5 - 2.5 * ease(k), 0.01); camera.lookAt(0, 0, 0);
  car.updateMatrixWorld(); const seat = car.userData.body.userData.driverSeat.clone().applyMatrix4(car.matrixWorld);
  camera.updateMatrixWorld(); const sp = seat.project(camera);
  const pulse = t < 0.5 ? 0 : 0.55 + 0.45 * Math.sin((t - 0.5) * 7);
  $("hl").style.left = ((sp.x + 1) / 2 * 1080) + "px"; $("hl").style.top = ((1 - sp.y) / 2 * 1920) + "px"; $("hl").style.opacity = pulse;"""),
    # Reveal: remote controller in the foreground, car far away
    "h_remote": dict(dur=4, setup="""addSite(scene); addLoop(scene);
const pad = new THREE.Group(); scene.add(pad);
const rr = new THREE.Shape(); const w = 2.4, h = 1.3, r = 0.45;
rr.moveTo(-w/2 + r, -h/2); rr.lineTo(w/2 - r, -h/2); rr.quadraticCurveTo(w/2, -h/2, w/2, -h/2 + r); rr.lineTo(w/2, h/2 - r);
rr.quadraticCurveTo(w/2, h/2, w/2 - r, h/2); rr.lineTo(-w/2 + r, h/2); rr.quadraticCurveTo(-w/2, h/2, -w/2, h/2 - r);
rr.lineTo(-w/2, -h/2 + r); rr.quadraticCurveTo(-w/2, -h/2, -w/2 + r, -h/2);
const dark = new THREE.MeshStandardMaterial({ color: 0x1b1e24, roughness: 0.45, metalness: 0.3 });
const shell = new THREE.Mesh(new THREE.ExtrudeGeometry(rr, { depth: 0.22, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.06, bevelSegments: 4 }), dark);
shell.rotation.x = -Math.PI / 2; pad.add(shell);
const stickL = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.2, 0.28, 24), new THREE.MeshStandardMaterial({ color: 0x3a404b, roughness: 0.5 }));
stickL.position.set(-0.6, 0.4, -0.1); pad.add(stickL);
const stickR = stickL.clone(); stickR.position.x = 0.15; pad.add(stickR);
for (const [x, z, c] of [[0.75, -0.25, 0xd3122c], [0.95, 0.05, 0x2bb3ff]]) {
  const b = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.12, 24), new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 0.4 }));
  b.position.set(x, 0.32, z); pad.add(b);
}
pad.position.set(-8, 2.1, 30); pad.rotation.x = 0.55;""", body="""
  const e = 6.0 + t * 0.3, ps = carPose(e);
  placeCar(car, ps, 0);
  stickL.rotation.z = 0.35 * Math.sin(t * 5); stickR.rotation.x = 0.3 * Math.sin(t * 4 + 1);
  const k = t / 4;
  camera.position.set(-8 - 0.6 * k, 3.5, 33.5 - 0.6 * k); camera.lookAt(-8, 1.2, 8);"""),
    # Reveal: not approved for road use
    "i_stamp": dict(dur=4,
        overlay="""<div id="st" class="ov" style="left:80px;right:80px;top:470px;padding:30px 10px;text-align:center;border:16px solid #e01b2f;border-radius:30px;color:#e01b2f;font-size:88px;line-height:1.05;background:rgba(255,255,255,.88);opacity:0">NOT APPROVED<br/>FOR ROAD USE</div>""",
        setup="addSite(scene);", body="""
  placeCar(car, { x: 0, y: 0, rotZ: 0 }, 0);
  const k = t / 4, a = 0.9 + 0.5 * k;
  camera.position.set(Math.cos(a) * 9, 1.4, Math.sin(a) * 9); camera.lookAt(0, 0.9, 0);
  const s = clamp01((t - 0.4) / 0.2);
  $("st").style.opacity = s; $("st").style.transform = `rotate(-8deg) scale(${2.4 - 1.4 * s})`;"""),
    # Ending: lifts off into the sky — not yet
    "j_end": dict(dur=3.5,
        overlay="""<div id="qm" class="ov" style="left:0;right:0;top:330px;text-align:center;font-size:320px;color:#fff;text-shadow:0 10px 30px rgba(0,0,0,.35);opacity:0">?</div>""",
        setup="addSite(scene);" + """
const lift = makePuffs(scene, { n: 50, t0: 0.1, t1: 3.2, seed: 33, life: 0.8, size: 1.4, grow: 3, speed: 4, color: 0xcfdbe4, opacity: 1 });""", body="""
  const k = ease(clamp01(t / 3.5)), y = 0.0 + 9 * k * k, x = 6 * k * k;
  placeCar(car, { x, y, rotZ: 0.12 * k }, 0);
  lift.update(t, (born, p) => { const yy = 9 * Math.pow(ease(clamp01(born / 3.5)), 2), xx = 6 * Math.pow(ease(clamp01(born / 3.5)), 2);
    return { pos: v3(xx + (p.jx > 0 ? 1.3 : -1.3), yy, p.jz > 0 ? 0.7 : -0.7), dir: v3(0, -1, 0) }; });
  camera.position.set(-7, 1.0, 9); camera.lookAt(x * 0.6, 1.5 + y * 0.7, 0);
  const q = clamp01((t - 1.4) / 0.25); $("qm").style.opacity = q; $("qm").style.transform = `scale(${q})`;"""),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, s in SHOTS.items():
        d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
        for f in ("three.module.js", "three.core.js", "RoomEnvironment.js", "world.js"):
            shutil.copy(os.path.join(LIB, f), d)
        shutil.copy(os.path.join(ASSETS, "montserrat-latin-800-normal.woff2"), d)
        html = PAGE.format(dur=s["dur"], bg=s.get("bg", SKY), opts=s.get("opts", "{}"),
                           overlay=s.get("overlay", ""), setup=s["setup"], body=s["body"])
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(html)
        open(os.path.join(d, "meta.json"), "w").write('{"id":"%s","name":"%s"}' % (name, name))
        open(os.path.join(d, "hyperframes.json"), "w").write("{}")
    print("shots:", ", ".join(SHOTS))


if __name__ == "__main__":
    main()
