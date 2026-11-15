// stickkit: a small posable stick figure for HyperFrames shorts.
// A pose is joint angles (degrees). Angle 0 points down, 90 points forward (+x), 180 points up.
// aF/aB = front/back arm [shoulder, elbow bend], lF/lB = front/back leg [hip, knee bend].
const SK = (() => {
  const D2R = Math.PI / 180, dir = (a) => [Math.sin(a * D2R), Math.cos(a * D2R)];
  const walkLeg = (ph, base, amp, bend) => [base + amp * Math.sin(ph), 18 + bend * Math.max(0, Math.cos(ph))];
  const swingArm = (ph, amp) => [amp * Math.sin(ph), 30];
  const POSE = {
    stand: () => ({ lean: 0, head: 0, aF: [10, 8], aB: [-8, 8], lF: [8, 0], lB: [-8, 0] }),
    walk: (t, ph) => ({ lean: 4, head: 0, aF: swingArm(ph + Math.PI, 30), aB: swingArm(ph, 30), lF: walkLeg(ph, 0, 28, 30), lB: walkLeg(ph + Math.PI, 0, 28, 30) }),
    run: (t, ph) => ({ lean: 14, head: -4, aF: [-50 * Math.sin(ph), 95], aB: [50 * Math.sin(ph), 95], lF: walkLeg(ph, 4, 48, 80), lB: walkLeg(ph + Math.PI, 4, 48, 80), dy: -14 * Math.abs(Math.sin(ph)) }),
    limp: (t, ph) => ({ lean: 10 + 6 * Math.sin(ph), head: 16, aF: [20, 30], aB: [-30, 10], lF: walkLeg(ph, 0, 12, 10), lB: [-6, 0] }),
    cheer: (t) => ({ lean: -4, head: -12, aF: [158, 8], aB: [-158, -8], lF: [10, 0], lB: [-10, 0], dy: -26 * Math.abs(Math.sin(t * Math.PI)) }),
    tired: (t) => ({ lean: 66 + 3 * Math.sin(t * 3), head: 18, aF: [-30, -10], aB: [-40, -6], lF: [14, 24], lB: [-10, 22] }),
    slump: () => ({ lean: 24, head: 40, aF: [40, 50], aB: [30, 56], lF: [82, 128], lB: [72, 118] }),
    shock: (t) => ({ lean: -6, head: 8, aF: [160, 150], aB: [150, 150], lF: [14, 0], lB: [-14, 0], dy: -6 * Math.abs(Math.sin(t * 6)) }),
    shrug: (t) => ({ lean: 0, head: 10 * Math.sin(t * 3), aF: [60, -110], aB: [-60, 110], lF: [8, 0], lB: [-8, 0], dy: -4 * Math.abs(Math.sin(t * 4)) }),
    phone: () => ({ lean: 2, head: 34, aF: [38, 104], aB: [-8, 8], lF: [8, 0], lB: [-8, 0] }),
    selfie: (t) => ({ lean: -6, head: -10, aF: [140, -20], aB: [-10, 10], lF: [10, 0], lB: [-10, 0] }),
    flex: (t) => ({ lean: -8, head: -8, aF: [92, 112 + 12 * Math.sin(t * 9)], aB: [-25, 95], lF: [10, 0], lB: [-10, 0], dy: -10 * Math.abs(Math.sin(t * Math.PI * 2)) }),
    toss: (t, ph) => ({ lean: 4, head: -6, aF: [70 + 70 * Math.max(0, Math.sin(ph)), 20], aB: [-12, 10], lF: [10, 0], lB: [-8, 0] }),
    scratch: (t) => ({ lean: 4, head: 20, aF: [44, 96 + 14 * Math.sin(t * 20)], aB: [30, 100], lF: [8, 0], lB: [-8, 0] }),
    sitFloor: (t) => ({ lean: -10, head: 20, aF: [60, 30], aB: [40, 60], lF: [86, 6], lB: [80, 70] }),
    sleep: (t) => ({ lean: 0, rot: -88, head: 8, aF: [-150, 30], aB: [-120, 30], lF: [10, 20], lB: [0, 30], dy: 2 * Math.sin(t * 2) }),
    // lying on a bench, head to the left, pressing a bar straight up. e = 0 bar down, 1 arms locked out
    bench: (t, ph, e = 0.5) => ({ lean: 0, rot: -90, head: 0, aF: [90 - 42 * (1 - e), 84 * (1 - e)], aB: [86 - 42 * (1 - e), 80 * (1 - e)], lF: [0, 90], lB: [12, 96] }),
    benchSit: (t) => ({ lean: 6, head: 22, aF: [150, 160], aB: [20, 40], lF: [84, 88], lB: [76, 92] }),
  };
  const NUM = ["lean", "head", "rot", "dx", "dy"], ARR = ["aF", "aB", "lF", "lB"];
  const mix = (a, b, k) => { const o = { face: b.face || a.face || 1 }; NUM.forEach((n) => { o[n] = (a[n] || 0) + ((b[n] || 0) - (a[n] || 0)) * k; }); ARR.forEach((n) => { o[n] = [a[n][0] + (b[n][0] - a[n][0]) * k, a[n][1] + (b[n][1] - a[n][1]) * k]; }); return o; };
  // modes: [[beat, poseName, extraArg?], ...]. Blends into each new pose over B beats.
  const modeIndex = (modes, t) => { let i = 0; while (i + 1 < modes.length && modes[i + 1][0] <= t) i++; return i; };
  const poseAt = (modes, t, ph, B = 0.3) => {
    const i = modeIndex(modes, t), get = (j) => POSE[modes[j][1]](t, ph, modes[j][2]), cur = get(i);
    if (i > 0 && t < modes[i][0] + B) { const k = (t - modes[i][0]) / B, e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; return mix(get(i - 1), cur, e); }
    return mix(cur, cur, 1);
  };
  const solve = (p, pin = true) => {
    const S = [150 * Math.sin(p.lean * D2R), -150 * Math.cos(p.lean * D2R)], hd = (p.lean + p.head) * D2R, HC = [S[0] + 66 * Math.sin(hd), S[1] - 66 * Math.cos(hd)];
    const limb = (o, a, b, l) => { const d1 = dir(a), j = [o[0] + l * d1[0], o[1] + l * d1[1]], d2 = dir(b); return [o, j, [j[0] + l * d2[0], j[1] + l * d2[1]]]; };
    const pts = { to: [[0, 0], S], aF: limb(S, p.aF[0], p.aF[0] + p.aF[1], 82), aB: limb(S, p.aB[0], p.aB[0] + p.aB[1], 82), lF: limb([0, 0], p.lF[0], p.lF[0] - p.lF[1], 105), lB: limb([0, 0], p.lB[0], p.lB[0] - p.lB[1], 105), hc: [HC] };
    const r = (p.rot || 0) * D2R, c = Math.cos(r), s = Math.sin(r); let maxY = -1e9;
    Object.keys(pts).forEach((n) => { pts[n] = pts[n].map(([x, y]) => [x * c - y * s, x * s + y * c]); pts[n].forEach((q) => { maxY = Math.max(maxY, q[1] + (n === "hc" ? 46 : n === "to" ? 34 : 20)); }); });
    const oy = (pin ? -maxY : 0) + (p.dy || 0); Object.keys(pts).forEach((n) => { pts[n] = pts[n].map(([x, y]) => [x, y + oy]); });
    pts.lean = (p.lean || 0) + (p.head || 0) + (p.rot || 0); pts.dx = p.dx || 0; pts.face = p.face || 1;
    return pts;
  };
  // style: { layers: [{ c, w, back, dx, dy }], torso: 1.6, head: [{ r, fill, stroke, sw, dx, dy }], acc: "<svg markup on the head>" }
  const PARTS = ["aB", "lB", "to", "lF", "aF"];
  const svg = (id, st) => `<g id="${id}">${PARTS.map((p) => st.layers.map((L, i) => `<polyline id="${id}-${p}-${i}" fill="none" stroke="${p[1] === "B" && L.back ? L.back : L.c}" stroke-width="${p === "to" ? L.w * (st.torso || 1) : L.w}" stroke-linecap="round" stroke-linejoin="round"${L.dx || L.dy ? ` transform="translate(${L.dx || 0} ${L.dy || 0})"` : ""}${L.extra || ""}/>`).join("")).join("")}<g id="${id}-hd">${st.head.map((h) => `<circle cx="${h.dx || 0}" cy="${h.dy || 0}" r="${h.r}" fill="${h.fill}" stroke="${h.stroke || "none"}" stroke-width="${h.sw || 0}"/>`).join("")}${st.acc || ""}</g>${st.after || ""}</g>`;
  const fmt = (a) => a.map((q) => q[0].toFixed(1) + "," + q[1].toFixed(1)).join(" ");
  const draw = (id, pts, st, x, y, s) => {
    PARTS.forEach((p) => { const v = fmt(pts[p]); st.layers.forEach((L, i) => document.getElementById(`${id}-${p}-${i}`).setAttribute("points", v)); });
    document.getElementById(`${id}-hd`).setAttribute("transform", `translate(${pts.hc[0][0].toFixed(1)} ${pts.hc[0][1].toFixed(1)}) rotate(${pts.lean.toFixed(1)})`);
    document.getElementById(id).setAttribute("transform", `translate(${(x + pts.dx * s * pts.face).toFixed(1)} ${y.toFixed(1)}) scale(${(s * pts.face).toFixed(3)} ${s.toFixed(3)})`);
  };
  // figure-space point -> world point for a figure drawn at (x, y) with scale s
  const world = (pts, q, x, y, s) => [x + (pts.dx + q[0]) * s * pts.face, y + q[1] * s];
  const kf = (a, t) => { for (let i = 1; i < a.length; i++) if (t <= a[i][0]) { const [t0, v0] = a[i - 1], [t1, v1, e] = a[i], k = (t - t0) / (t1 - t0); return v0 + (v1 - v0) * (e ? gsap.parseEase(e)(k) : k); } return a[a.length - 1][1]; };
  return { POSE, mix, modeIndex, poseAt, solve, svg, draw, world, kf, D2R };
})();
