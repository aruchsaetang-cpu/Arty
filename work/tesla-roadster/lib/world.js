// Shared 3D world for the Tesla Roadster short: test site, car, half-loop ramp,
// thruster gas and landing smoke. Everything is a pure function of time so
// HyperFrames can seek any frame deterministically.
import * as THREE from "three";
import { RoomEnvironment } from "./RoomEnvironment.js";

export const W = 1080, H = 1920;
const S = 4.4 / 600;                 // car profile px -> metres
const CAR_W = 1.95;

// ---------- the event timeline (seconds of "event time") ----------
export const LOOP = { cx: 0, R: 5.2, y0: 0 };       // half-loop centre at (cx, R)
export const EV = { approach: 2.0, loopEnd: 3.7, flipStart: 4.3, flipEnd: 5.6, hoverEnd: 6.7, land: 7.5 };
const ease = (t) => t * t * (3 - 2 * t);
const clamp01 = (t) => Math.min(1, Math.max(0, t));

export function rng(seed) {
  let x = seed >>> 0;
  return () => ((x = (Math.imul(x, 1103515245) + 12345) >>> 0) / 4294967296);
}

// car pose at event time e -> { x, y, rotZ } (car drives along +x, rotZ in radians)
export function carPose(e) {
  const { cx, R } = LOOP, r = R - 0.15;
  if (e < EV.approach) {                       // drive towards the loop
    const k = e / EV.approach;
    return { x: cx - 26 * (1 - k) * (1 - k * 0.35), y: 0, rotZ: 0 };
  }
  if (e < EV.loopEnd) {                        // around the loop: theta -90deg -> +100deg
    const k = (e - EV.approach) / (EV.loopEnd - EV.approach);
    const th = -Math.PI / 2 + (Math.PI + 0.17) * (k * 0.75 + 0.25 * ease(k));
    return { x: cx + r * Math.cos(th), y: R + r * Math.sin(th), rotZ: th + Math.PI / 2 };
  }
  // airborne: leaves near the top heading -x, upside down
  const th = Math.PI / 2 + 0.17;
  const x0 = cx + r * Math.cos(th), y0 = R + r * Math.sin(th);
  const ta = e - EV.loopEnd;
  const flip = ease(clamp01((e - EV.flipStart) / (EV.flipEnd - EV.flipStart)));
  let x = x0 - 7 * (1 - Math.exp(-ta * 0.9));
  let y = y0 - 2.2 * ta + 0.35 * ta * ta;      // slowed fall (thrusters)
  y = Math.max(y, 2.6);
  if (e > EV.flipEnd) y = 2.6 + 0.18 * Math.sin((e - EV.flipEnd) * 6);
  if (e > EV.hoverEnd) y = 2.6 * (1 - ease(clamp01((e - EV.hoverEnd) / (EV.land - EV.hoverEnd))));
  const rotZ = (th + Math.PI / 2) * (1 - flip) + 0;
  return { x, y, rotZ };
}

// ---------- renderer / scene ----------
export function makeStage(canvas, opts = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setSize(W, H, false);
  renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = opts.exposure ?? 1.05;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const camera = new THREE.PerspectiveCamera(opts.fov ?? 38, W / H, 0.1, 600);
  scene.add(new THREE.HemisphereLight(opts.sky ?? 0xbfe9ff, opts.groundLight ?? 0x6b5a45, opts.hemi ?? 1.0));
  const sun = new THREE.DirectionalLight(opts.sunColor ?? 0xffffff, opts.sun ?? 2.6);
  sun.position.set(12, 22, 14);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30, near: 1, far: 80 });
  sun.shadow.bias = -0.0005;
  scene.add(sun, sun.target);
  return { renderer, scene, camera, sun };
}

// desert test site: sand, runway, distant tower, tank, ramps
export function addSite(scene, { desert = true } = {}) {
  const g = new THREE.Group();
  const sand = new THREE.Mesh(new THREE.CircleGeometry(300, 64),
    new THREE.MeshStandardMaterial({ color: desert ? 0xcfa774 : 0x6a7079, roughness: 1 }));
  sand.rotation.x = -Math.PI / 2; sand.receiveShadow = true; g.add(sand);
  const run = new THREE.Mesh(new THREE.PlaneGeometry(160, 14),
    new THREE.MeshStandardMaterial({ color: 0x4f555d, roughness: 0.92 }));
  run.rotation.x = -Math.PI / 2; run.position.y = 0.01; run.receiveShadow = true; g.add(run);
  const lineMat = new THREE.MeshStandardMaterial({ color: 0xf1f1f1, roughness: 0.8 });
  for (let i = -16; i < 16; i++) {
    const l = new THREE.Mesh(new THREE.PlaneGeometry(3, 0.25), lineMat);
    l.rotation.x = -Math.PI / 2; l.position.set(i * 5, 0.02, 4.5); g.add(l);
    const l2 = l.clone(); l2.position.z = -4.5; g.add(l2);
  }
  const grey = new THREE.MeshStandardMaterial({ color: 0x5c6470, roughness: 0.6, metalness: 0.4 });
  const tower = new THREE.Mesh(new THREE.BoxGeometry(5, 46, 5), grey);
  tower.position.set(-60, 23, -90); tower.castShadow = true; g.add(tower);
  const top = new THREE.Mesh(new THREE.BoxGeometry(12, 3, 12), grey); top.position.set(-60, 46, -90); g.add(top);
  const tank = new THREE.Mesh(new THREE.CylinderGeometry(7, 7, 22, 40),
    new THREE.MeshStandardMaterial({ color: 0xe9eef3, roughness: 0.35, metalness: 0.2 }));
  tank.position.set(55, 11, -80); tank.castShadow = true; g.add(tank);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(7, 40, 20, 0, Math.PI * 2, 0, Math.PI / 2), tank.material);
  dome.position.set(55, 22, -80); g.add(dome);
  scene.add(g);
  return g;
}

// half-loop ramp in the x-y plane, track 3.4 m wide (z)
export function addLoop(scene) {
  const { cx, R } = LOOP, g = new THREE.Group();
  const deck = new THREE.MeshStandardMaterial({ color: 0xc9ced6, roughness: 0.55, metalness: 0.3 });
  const stripe = new THREE.MeshStandardMaterial({ color: 0xffd400, roughness: 0.5 });
  const N = 64, a0 = -Math.PI / 2, a1 = Math.PI / 2 + 0.25;
  for (let i = 0; i < N; i++) {
    const a = a0 + (a1 - a0) * (i + 0.5) / N, len = R * (a1 - a0) / N * 1.04;
    const seg = new THREE.Mesh(new THREE.BoxGeometry(len, 0.3, 3.4), deck);
    seg.position.set(cx + R * Math.cos(a), R + R * Math.sin(a), 0);
    seg.rotation.z = a + Math.PI / 2; seg.castShadow = seg.receiveShadow = true; g.add(seg);
    if (i % 2 === 0) for (const z of [-1.62, 1.62]) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(len * 0.9, 0.34, 0.12), stripe);
      s.position.copy(seg.position).setZ(z); s.rotation.z = seg.rotation.z; g.add(s);
    }
  }
  const steel = new THREE.MeshStandardMaterial({ color: 0x7d8590, roughness: 0.5, metalness: 0.6 });
  for (const [x, h] of [[R, R], [R * 0.7, R * 1.71], [0, R * 2], [-R * 0.24, R * 1.97]])
    for (const z of [-2, 2]) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.35, h, 0.35), steel);
      p.position.set(cx + x, h / 2, z); p.castShadow = true; g.add(p);
    }
  scene.add(g);
  return g;
}

// the Roadster: extruded side profile + glass + wheels. Origin = ground contact, centre.
export function makeCar() {
  const car = new THREE.Group(), body = new THREE.Group();
  const P = (x, y) => [(x - 310) * S, (204 - y) * S];
  const shape = new THREE.Shape();
  shape.moveTo(...P(28, 150));
  shape.bezierCurveTo(...P(26, 124), ...P(58, 108), ...P(112, 102));
  shape.lineTo(...P(205, 96));
  shape.bezierCurveTo(...P(300, 92), ...P(400, 92), ...P(482, 97));   // beltline (cabin is glass)
  shape.lineTo(...P(560, 107));
  shape.bezierCurveTo(...P(586, 112), ...P(597, 128), ...P(594, 148));
  shape.lineTo(...P(590, 166)); shape.lineTo(...P(30, 166)); shape.closePath();
  const ext = { depth: CAR_W - 0.16, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.06, bevelSegments: 4, curveSegments: 24 };
  const paint = new THREE.MeshPhysicalMaterial({ color: 0xc8102a, metalness: 0.55, roughness: 0.22, clearcoat: 1, clearcoatRoughness: 0.08 });
  const shell = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, ext), paint);
  shell.position.z = -(CAR_W - 0.16) / 2; shell.castShadow = true; body.add(shell);

  const gl = new THREE.Shape();
  gl.moveTo(...P(206, 97));
  gl.bezierCurveTo(...P(246, 62), ...P(300, 46), ...P(360, 49));
  gl.bezierCurveTo(...P(410, 51), ...P(452, 72), ...P(481, 98)); gl.closePath();
  const GW = CAR_W - 0.42;
  const glass = new THREE.Mesh(new THREE.ExtrudeGeometry(gl, { depth: GW, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.05, bevelSegments: 4, curveSegments: 24 }),
    new THREE.MeshPhysicalMaterial({ color: 0x0a141c, metalness: 0.1, roughness: 0.04, transparent: true, opacity: 0.42, clearcoat: 1, depthWrite: false }));
  glass.position.set(0, -0.01, -GW / 2); glass.renderOrder = 2; body.add(glass);
  const frame = new THREE.MeshStandardMaterial({ color: 0x111316, roughness: 0.4 });
  for (const z of [-GW / 2 - 0.07, GW / 2 + 0.07]) {          // window frame along the beltline
    const f = new THREE.Mesh(new THREE.BoxGeometry(2.05, 0.05, 0.05), frame);
    f.position.set(...P(343, 96), z); body.add(f);
  }

  // interior: two empty seats + steering wheel (visible through the glass roof)
  const seatMat = new THREE.MeshStandardMaterial({ color: 0x9a6a46, roughness: 0.6 });
  for (const z of [-0.42, 0.42]) {
    const base = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.14, 0.5), seatMat);
    base.position.set(-0.05, 0.55, z); body.add(base);
    const back = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.62, 0.5), seatMat);
    back.position.set(-0.36, 0.84, z); back.rotation.z = 0.25; body.add(back);
  }
  const wheelS = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.035, 10, 28), seatMat);
  wheelS.position.set(0.48, 0.86, 0.42); wheelS.rotation.y = Math.PI / 2; wheelS.rotation.x = 0.35; body.add(wheelS);
  body.userData.driverSeat = new THREE.Vector3(-0.05, 0.62, 0.42);

  const lamp = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff3c0, emissiveIntensity: 2 });
  for (const z of [-0.7, 0.7]) {
    const h = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.07, 0.42), lamp);
    h.position.set(...P(588, 124), z); body.add(h);
    const t = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.06, 0.5),
      new THREE.MeshStandardMaterial({ color: 0xff2030, emissive: 0xff0018, emissiveIntensity: 1.5 }));
    t.position.set(...P(30, 128), z); body.add(t);
  }
  const tire = new THREE.MeshStandardMaterial({ color: 0x0b0b0c, roughness: 0.85 });
  const rim = new THREE.MeshStandardMaterial({ color: 0xb5bdc6, metalness: 0.9, roughness: 0.25 });
  const wheels = [];
  for (const wx of [140, 480]) for (const z of [-1, 1]) {
    const w = new THREE.Group();
    const t = new THREE.Mesh(new THREE.CylinderGeometry(40 * S, 40 * S, 0.3, 36), tire);
    t.rotation.x = Math.PI / 2; t.castShadow = true; w.add(t);
    const r = new THREE.Mesh(new THREE.CylinderGeometry(24 * S, 24 * S, 0.32, 10), rim);
    r.rotation.x = Math.PI / 2; w.add(r);
    w.position.set(...P(wx, 164), z * (CAR_W / 2 - 0.12)); body.add(w); wheels.push(w);
  }
  car.add(body);
  car.userData = { body, wheels };
  return car;
}

export function placeCar(car, pose, spin = 0) {
  car.position.set(pose.x, pose.y, 0);
  car.rotation.z = pose.rotZ;
  for (const w of car.userData.wheels) w.rotation.z = -spin;
}

// ---------- particles: thruster gas and smoke ----------
function puffTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const x = c.getContext("2d"), g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.45, "rgba(255,255,255,.65)"); g.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
const TEX = { puff: null };

// emitter(t) -> {pos: Vector3, dir: Vector3} ; puffs born between t0..t1
export function makePuffs(scene, { n, t0, t1, seed, life = 1.0, size = 1.2, grow = 3, speed = 4, color = 0xffffff, opacity = 0.9 }) {
  TEX.puff ??= puffTexture();
  const r = rng(seed), list = [];
  for (let i = 0; i < n; i++) {
    const m = new THREE.SpriteMaterial({ map: TEX.puff, color, transparent: true, depthWrite: false, opacity: 0 });
    const s = new THREE.Sprite(m); s.visible = false; scene.add(s);
    list.push({ s, born: t0 + (t1 - t0) * i / n, jx: r() - 0.5, jy: r() - 0.5, jz: r() - 0.5, k: 0.7 + r() * 0.6 });
  }
  return {
    update(t, emitter) {
      for (const p of list) {
        const age = (t - p.born) / life;
        if (age < 0 || age > 1) { p.s.visible = false; continue; }
        const { pos, dir } = emitter(p.born, p);
        const d = speed * age * p.k;
        p.s.position.set(pos.x + dir.x * d + p.jx * age * 2, pos.y + dir.y * d + p.jy * age * 2, pos.z + dir.z * d + p.jz * age * 2);
        p.s.scale.setScalar(size * (0.3 + grow * age) * p.k);
        p.s.material.opacity = opacity * (1 - age) * (1 - age);
        p.s.visible = true;
      }
    },
  };
}

// helpers for camera moves
export const v3 = (x, y, z) => new THREE.Vector3(x, y, z);
export function lerpV(a, b, k) { return a.clone().lerp(b, k); }
export { THREE, ease, clamp01 };
