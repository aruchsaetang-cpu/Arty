"""Combat pose solver: authored key-pose LAYERS (one per move) cross-faded with easing, then per-frame passes:
anatomical joint limits -> foot locking (plant / pivot / step detection) -> leg reach -> two-bone IK solve ->
forward kinematics -> centre-of-mass balance over the planted feet (hips shift = weight transfer) -> re-solve.

Built on shorts/kuro_oni/moves.py (Rig channels + the named moves), which stays untouched: every moves.py function
runs unchanged against a Layer (it duck-types moves.Rig: .key, .ctx, .state, .chest_to_world).

    R = CombatRig(arm, "hero")
    L = R.layer("slip", s=0.63, e=0.80, blend_in=0.05, ease="snap", balance="enforce", kind="dodge")
    moves.slip_turn(L, 0.63, 0.17, pocket=True)
    R.finalize(); ev = R.evaluate(story_frames, fps)      # per story frame: state, quats, FK, plants, balance
    R.bake(timemap, ev)                                   # keys Blender on OUTPUT frames (hit-stop = held frames)

Channels are moves.py's (x y yaw drop twist lean side hp hy hr hs tilt footL footR fistL fistR). Foot channels stay
authored as (x, y, yaw, lift[, pitch]); the foot-lock pass turns them into ankle targets that keep the BALL of each
planted foot fixed in the world (pivots rotate about the ball, as a real heel turn does), and converts any authored
"slide while lift = 0" into a short lifted step, so a planted foot cannot slide.
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); KO = os.path.dirname(HERE); ROOT = os.path.dirname(os.path.dirname(KO))
for p in (KO, os.path.join(ROOT, "lookdev")):
    if p not in sys.path: sys.path.insert(0, p)
import bpy
from mathutils import Vector as V, Quaternion as Q, Matrix
import moves as MV
import character_mh as ch
import physics as PH

RAD = math.radians
ez = MV.ez
CHANNELS = [n for n in MV.DEF] + ["footL", "footR"]
SCALAR = [n for n in MV.DEF if n not in ("hs", "tilt")]
# anatomical limits on the channels (degrees, metres). Spine twist/lean/side are totals over 5 vertebrae
# (thoracolumbar ROM: rotation ~ +-50, flexion ~ 60, extension ~ 30, lateral ~ 35); head = neck ROM in the chest frame.
LIMITS = dict(twist=(-50.0, 50.0), lean=(-30.0, 60.0), side=(-35.0, 35.0), hp=(-50.0, 60.0), hy=(-75.0, 75.0), hr=(-40.0, 40.0),
              drop=(-0.10, 0.62))
KNEE_TORSION = 70.0          # max |hip yaw - planted foot yaw| before the knee would have to twist (deg)
ELBOW_MIN, KNEE_MIN = 8.0, 3.0   # minimum flexion (deg): the IK never locks a joint straight (no hyperextension)
# segment masses (Winter 2009, fraction of body mass) and centre-of-mass position along the segment (from proximal)
SEGMENTS = [("head", "head", "head_tail", 0.081, 0.50), ("trunk", "spine05", "neck01", 0.497, 0.50)]
for _s in "LR":
    SEGMENTS += [(f"uarm{_s}", f"upperarm01.{_s}", f"lowerarm01.{_s}", 0.028, 0.436), (f"farm{_s}", f"lowerarm01.{_s}", f"wrist.{_s}_tail", 0.022, 0.682),
                 (f"thigh{_s}", f"upperleg01.{_s}", f"lowerleg01.{_s}", 0.100, 0.433), (f"shank{_s}", f"lowerleg01.{_s}", f"foot.{_s}", 0.061, 0.606)]
FK_BONES = ["spine05", "spine03", "spine02", "spine01", "neck01", "neck02", "head"] + [f"{b}.{s}" for s in "LR" for b in (
    "upperleg01", "upperleg02", "lowerleg01", "lowerleg02", "foot", "upperarm01", "lowerarm01", "lowerarm02", "wrist")]


class Layer:
    """One move's keys. Duck-types moves.Rig for the move functions (key / ctx / state / chest_to_world)."""
    def __init__(self, rig, name, s, e, blend_in, blend_out_prev, ease, balance, kind, first):
        self.rig, self.name, self.s, self.e = rig, name, s, e
        self.bin, self.bout, self.ease, self.balance, self.kind, self.first = blend_in, blend_out_prev, ease, balance, kind, first
        self.keys = []; self._has = set()
    @property
    def ctx(self): return self.rig.ctx
    def key(self, t, ease="io", **chans):
        self.keys.append((t, chans, ease)); self._has.update(chans)
        self.keys.sort(key=lambda k: k[0])
    def has(self, name): return name in self._has
    def chan(self, name, t):
        ks = [(tk, d[name], e) for tk, d, e in self.keys if name in d]
        val = lambda v: v[1] if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str) else v
        if t <= ks[0][0]: return val(ks[0][1])
        for (t0, v0, _), (t1, v1, e1) in zip(ks, ks[1:]):
            if t0 <= t <= t1: return MV._lerp(val(v0), val(v1), ez((t - t0) / max(1e-6, t1 - t0), e1))
        return val(ks[-1][1])
    def chan_fist(self, name, t):
        ks = [(tk, d[name], e) for tk, d, e in self.keys if name in d]
        if t <= ks[0][0]: return ks[0][1], ks[0][1], 0.0
        for (t0, v0, _), (t1, v1, e1) in zip(ks, ks[1:]):
            if t0 <= t <= t1: return v0, v1, ez((t - t0) / max(1e-6, t1 - t0), e1)
        return ks[-1][1], ks[-1][1], 0.0
    def weight(self, t):
        if self.first: return 1.0
        a, b = self.s - self.bin, self.s + self.bout
        if b - a < 1e-6: return 1.0 if t >= self.s - 1e-9 else 0.0
        return ez((t - a) / (b - a), self.ease if self.ease != "lin" else "io")
    def state(self, t, skip_fists=False):
        return self.rig.blend_state(t, upto=self, skip_fists=skip_fists)
    def chest_to_world(self, st, p):
        return self.rig.chest_to_world(st, p)


class CombatRig(MV.Rig):
    def __init__(self, g, name, origin=(0, 0, 0), pockets=False):
        super().__init__(g, origin)
        self.name = name; self.layers = []; self.pockets = pockets; self.flags = []     # (t0, t1, "fall"|"react")
        B = g.data.bones
        self.rest4 = {b.name: b.matrix_local.copy() for b in B}
        self.rest4i = {n: m.inverted() for n, m in self.rest4.items()}
        self.blen = {b.name: b.length for b in B}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in B}
        for sd in "LR":
            gl = self.leg[sd]; gl["zb0"] = gl["ah"] * self.s + gl["fdir"].z * gl["flen"] * self.s    # rest ball height
        self.parts = {}            # body-part / effector rest points (filled by contact.calibrate)
        self.limit_hits = {}
    # ------------------------------------------------------------ layers + blending
    def layer(self, name, s, e, blend_in=0.0, ease="io", balance="enforce", kind="idle"):
        prev = self.layers[-1] if self.layers else None
        L = Layer(self, name, s, e, blend_in, getattr(prev, "_bout_next", 0.0), ease, balance, kind, first=not self.layers)
        self.layers.append(L); return L
    def set_blend_out(self, L, bout): L._bout_next = bout
    def blend_state(self, t, upto=None, skip_fists=False):
        st = {n: (tuple(v) if isinstance(v, tuple) else v) for n, v in MV.DEF.items()}
        st["footL"] = st["footR"] = None
        fist_layers = []
        for L in self.layers:
            w = L.weight(t)
            if w > 1e-6:
                for n in CHANNELS:
                    if L.has(n):
                        v = L.chan(n, t)
                        st[n] = v if st[n] is None or w >= 1.0 else MV._lerp(st[n], v, w)
                for sd in "LR":
                    if L.has("fist" + sd): fist_layers.append((L, sd, w))
            if L is upto: break
        if st["footL"] is None: raise ValueError(f"{self.name}: no foot keys before t={t:.3f} (start with an idle move)")
        if skip_fists: return st
        _, _, M = self.objmat(st); Mi = M.inverted()
        for sd in "LR":
            p = None
            for L, s_, w in fist_layers:
                if s_ != sd: continue
                v0, v1, k = L.chan_fist("fist" + sd, t)
                q = self._to_local(st, Mi, v0).lerp(self._to_local(st, Mi, v1), k)
                p = q if p is None or w >= 1.0 else p.lerp(q, w)
            if p is None: p = V(MV.POCKET_L if sd == "L" else MV.POCKET_R)
            st["fist" + sd] = (("h", tuple(p)), ("h", tuple(p)), 0.0)
        return st
    def _to_local(self, st, Mi, v):
        if v[0] == "h": return V(v[1])
        if v[0] == "w": return Mi @ V(v[1])
        return Mi @ self.chest_to_world(st, v[1])       # 'c' not finalized yet
    def finalize(self):
        """chest-space fist keys ('c') -> world at their key time (straight world paths between keys), per layer."""
        for L in self.layers:
            for t, d, _ in L.keys:
                for sd in "LR":
                    v = d.get("fist" + sd)
                    if v is not None and v[0] == "c":
                        d["fist" + sd] = ("w", tuple(self.chest_to_world(self.blend_state(t, skip_fists=True), v[1])))
    def state(self, t, skip_fists=False):       # moves.Rig API (used by moves called on the rig itself)
        return self.blend_state(t, skip_fists=skip_fists)
    def key(self, t, ease="io", **chans):
        (self.layers[-1] if self.layers else self.layer("base", t, t)).key(t, ease, **chans)
    def flag(self, t, name):
        return any(a <= t <= b and n == name for a, b, n in self.flags)
    def balance_mode(self, t, st=None):
        """'enforce' = static balance required (both feet planted, or single support during a strike);
        'report' = dynamic (steps, lunges, reactions, falls): measured only, a step is a controlled fall by nature."""
        if self.flag(t, "fall") or self.flag(t, "react"): return "report"
        m = "enforce"; kind = "idle"
        for L in self.layers:
            if L.s - 1e-9 <= t: m = L.balance; kind = L.kind
        if st is not None and m == "enforce":
            n = sum(st.get("_cls" + sd) == "plant" for sd in "LR")
            if n == 0 or (n == 1 and kind != "attack"): return "report"
        return m
    # ------------------------------------------------------------ feet
    def foot_dir(self, sd, yaw, pitch):
        gl = self.leg[sd]; h = gl["fdir"].to_2d().length
        d = V((math.sin(RAD(yaw)) * h, -math.cos(RAD(yaw)) * h, gl["fdir"].z))
        if pitch:
            # heel up = the toes point further DOWN (rotation about the foot's side axis). moves.Rig.solve uses the
            # opposite sign (its "heel up" tips the toes up and floats the ball 5-7 cm); corrected here.
            ax = V((math.cos(RAD(yaw)), math.sin(RAD(yaw)), 0)); d = Matrix.Rotation(RAD(pitch), 3, ax) @ d
        return d.normalized()
    def ankle_auth(self, sd, ft):
        """authored (x, y, yaw, lift[, pitch]) -> world ankle, the same reading as moves.Rig.solve (heel lift ~ 0.8 flen sin)."""
        gl = self.leg[sd]; fx, fy, fyaw, lift = ft[:4]; pitch = ft[4] if len(ft) > 4 else 0.0
        if pitch: lift = lift + gl["flen"] * self.s * math.sin(RAD(pitch)) * 0.8
        return self.O + V((fx, fy, lift + gl["ah"] * self.s))
    def ball_of(self, sd, ank, yaw, pitch):
        return ank + self.foot_dir(sd, yaw, pitch) * self.leg[sd]["flen"] * self.s
    def foot_lock(self, sts, fps):
        """Plant / pivot / step detection on the authored feet, then lock: in every plant run the ball of the foot stays
        on its landing spot (pivots turn about it); authored lift-0 slides become lifted steps; swing paths blend from
        one locked spot to the next. Writes st['_ankX'] (world ankle) and st['_fdX'] (foot direction)."""
        n = len(sts); plants = []; steps = []
        for sd in "LR":
            ft = [st["foot" + sd] for st in sts]
            pitch = [max(0.0, f[4] if len(f) > 4 else 0.0) for f in ft]
            ank = [self.ankle_auth(sd, f) for f in ft]
            ball = [self.ball_of(sd, a, f[2], p) for a, f, p in zip(ank, ft, pitch)]
            fall = [self.flag(st["_t"], "fall") for st in sts]
            floor = self.O.z + self.leg[sd]["zb0"]
            lifted = [b.z - floor > 0.008 for b in ball]
            cls = []
            for i in range(n):
                if fall[i]: cls.append("free"); continue
                if lifted[i]: cls.append("swing"); continue
                if i == 0: cls.append("plant"); continue
                mv = min((ball[i] - ball[i - 1]).to_2d().length, (ank[i] - ank[i - 1]).to_2d().length)
                cls.append("plant" if mv < 0.0025 else "shuffle")
            runs = []; i = 0                               # plant runs [a, b]
            while i < n:
                if cls[i] == "plant":
                    j = i
                    while j + 1 < n and cls[j + 1] == "plant": j += 1
                    runs.append((i, j)); i = j + 1
                else: i += 1
            d = [None] * n
            for a, b in runs:
                anchor = ball[a].copy(); anchor.z = self.O.z + self.leg[sd]["zb0"]
                for k in range(a, b + 1):
                    d[k] = anchor - ball[k]
                yaws = [ft[k][2] for k in range(a, b + 1)]; ps = pitch[a:b + 1]
                kind = "pivot" if (max(yaws) - min(yaws) > 4 or max(ps) - min(ps) > 4) else "plant"
                plants.append(dict(side=sd, a=a, b=b, kind=kind, anchor=tuple(anchor)))
            for (a0, b0), (a1, b1) in zip(runs, runs[1:]):       # transitions between plant runs: blend the correction
                dz0, dz1 = d[b0], d[a1]
                for k in range(b0 + 1, a1):
                    u = ez((k - b0) / (a1 - b0), "io"); d[k] = dz0.lerp(dz1, u)
                    if cls[k] == "shuffle" or (all(c != "swing" for c in cls[b0 + 1:a1]) and (ball[a1] - ball[b0]).to_2d().length > 0.01):
                        hgt = min(0.045, 0.35 * (ball[a1] - ball[b0]).to_2d().length + 0.012)
                        d[k] = d[k] + V((0, 0, hgt * math.sin(math.pi * (k - b0) / (a1 - b0))))
                kinds = set(cls[b0 + 1:a1])
                steps.append(dict(side=sd, a=b0 + 1, b=a1 - 1, kind="auto_step" if "swing" not in kinds else "step"))
            if runs:
                for k in range(0, runs[0][0]): d[k] = d[runs[0][0]] if cls[k] != "free" else V()
                for k in range(runs[-1][1] + 1, n): d[k] = d[runs[-1][1]] if cls[k] != "free" else V()
            for k in range(n):
                dk = d[k] if d[k] is not None else V()
                if cls[k] in ("plant",):
                    b_ = ball[k] + dk
                    fd = self.foot_dir(sd, ft[k][2], pitch[k]); a_ = b_ - fd * self.leg[sd]["flen"] * self.s
                elif cls[k] == "free":
                    fd = self.foot_dir(sd, ft[k][2], pitch[k]); a_ = ank[k]
                else:
                    fd = self.foot_dir(sd, ft[k][2], pitch[k]); a_ = ank[k] + dk
                    if not lifted[k]:   # shuffle frame: keep the ball on/above the ground
                        b_ = a_ + fd * self.leg[sd]["flen"] * self.s; floor = self.O.z + self.leg[sd]["zb0"]
                        if b_.z < floor + dk.z: a_ = a_ + V((0, 0, floor + dk.z - b_.z))
                sts[k]["_ank" + sd] = a_; sts[k]["_fd" + sd] = fd; sts[k]["_cls" + sd] = cls[k]
        return plants, steps
    def reach_fix(self, sts):
        """lower the hips just enough that a planted leg can reach its ankle target (no straight-knee pop / foot pull)."""
        need = []
        for st in sts:
            loc, q, M = self.objmat(st); dz = 0.0
            for sd in "LR":
                if st.get("_cls" + sd) != "plant" or self.flag(st["_t"], "fall"): continue
                gl = self.leg[sd]; hip = M @ gl["hip"]; T = st["_ank" + sd]; R = 0.985 * (gl["Lt"] + gl["Ls"]) * self.s
                dxy = (hip - T).to_2d().length
                if dxy < R: dz = max(dz, hip.z - T.z - math.sqrt(R * R - dxy * dxy))
            need.append(max(0.0, dz))
        win = [max(need[max(0, i - 2):i + 3]) for i in range(len(need))]
        sm = PH.smooth(win, 2)
        for st, v, raw in zip(sts, sm, need):
            st["drop"] = st["drop"] + max(v, raw); st["_reach_dz"] = max(v, raw)
    def apply_limits(self, st):
        for n, (lo, hi) in LIMITS.items():
            v = st[n]
            if v < lo - 1e-6 or v > hi + 1e-6:
                self.limit_hits[n] = self.limit_hits.get(n, 0) + 1; st[n] = min(hi, max(lo, v))
    # ------------------------------------------------------------ solve (moves.Rig.solve with world ankle targets)
    def solve(self, st):
        loc, q, M = self.objmat(st); Mi = M.inverted(); R3i = Mi.to_3x3()
        A, Rc = self.chest(st)
        Rh = Rc @ Matrix.Rotation(RAD(st["hy"]), 3, "Z") @ Matrix.Rotation(RAD(st["hp"]), 3, "X") @ Matrix.Rotation(RAD(st["hr"]), 3, "Y") @ Rc.inverted()
        half = Q().slerp(Rh.to_quaternion(), 0.5).to_matrix()
        A.final["neck02"] = half @ A.rot("neck02"); A.final["head"] = half @ A.rot("head")
        B = self.B
        def pos(n):
            b = B[n]
            if b.parent is None: return b.head_local.copy()
            p = b.parent
            return pos(p.name) + A.rot(p.name) @ self.rest[p.name].inverted() @ (b.head_local - p.head_local)
        for sd, sx in (("L", 1), ("R", -1)):
            v0, v1, kk = st["fist" + sd]
            T = V(v0[1]).lerp(V(v1[1]), kk) if v0[0] == "h" else Mi @ V(v0[1])
            S = pos(f"upperarm01.{sd}"); Wt = T - (T - S).normalized() * 0.075
            Lu, Lf = self.arm[sd]; v = Wt - S
            dmax = math.sqrt(Lu * Lu + Lf * Lf + 2 * Lu * Lf * math.cos(RAD(ELBOW_MIN)))
            d = max(abs(Lu - Lf) + 0.03, min(v.length, dmax)); vn = v.normalized()
            a = math.acos(max(-1.0, min(1.0, (Lu * Lu + d * d - Lf * Lf) / (2 * Lu * d))))
            pole = Rc @ V((sx * 0.35, 0.3, -1.0)); w = (pole - vn * pole.dot(vn)).normalized()
            up = vn * math.cos(a) + w * math.sin(a); elbow = S + up * Lu; fore = (S + vn * d - elbow).normalized()
            for b in ("upperarm01", "upperarm02"): A(f"{b}.{sd}", up)
            for b in ("lowerarm01", "lowerarm02", "wrist"): A(f"{b}.{sd}", fore)
        for sd in "LR":
            gl = self.leg[sd]
            T = Mi @ st["_ank" + sd]; fd = (R3i @ st["_fd" + sd]).normalized()
            fwd = V((fd.x, fd.y, 0.0)).normalized() if fd.to_2d().length > 1e-3 else V((0, -1, 0))
            Lt, Ls = gl["Lt"], gl["Ls"]; v = T - gl["hip"]
            dmax = math.sqrt(Lt * Lt + Ls * Ls + 2 * Lt * Ls * math.cos(RAD(KNEE_MIN)))
            d = min(v.length, dmax); vn = v.normalized()
            a = math.acos(max(-1.0, min(1.0, (Lt ** 2 + d * d - Ls ** 2) / (2 * Lt * d))))
            w = (fwd - vn * fwd.dot(vn)).normalized()
            th = vn * math.cos(a) + w * math.sin(a); knee = gl["hip"] + th * Lt; sh = (gl["hip"] + vn * d - knee).normalized()
            A(f"upperleg01.{sd}", th); A(f"upperleg02.{sd}", th); A(f"lowerleg01.{sd}", sh); A(f"lowerleg02.{sd}", sh)
            A(f"foot.{sd}", fd)
        out = A.quats()
        for n, _ in MV.SPINE + [("neck02", 0), ("head", 0)]:
            b = B[n]; inh = A.rot(b.parent.name) @ self.rest[b.parent.name].inverted() @ self.rest[n]
            out[n] = (inh.inverted() @ A.final[n]).to_quaternion()
        return loc, q, out
    # ------------------------------------------------------------ forward kinematics (exactly Blender's pose maths)
    def fk(self, M, quats, hs=(1, 1, 1)):
        pose = {}
        def P(n):
            if n in pose: return pose[n]
            q = quats.get(n); basis = q.to_matrix().to_4x4() if q is not None else Matrix.Identity(4)
            if n == "head": basis = basis @ Matrix.Diagonal((hs[0], hs[1], hs[2], 1.0))
            par = self.parent[n]
            m = self.rest4[n] @ basis if par is None else P(par) @ (self.rest4i[par] @ self.rest4[n]) @ basis
            pose[n] = m; return m
        out = {}
        for n in FK_BONES:
            m = M @ P(n); out[n] = m
        return out
    def joint(self, fkm, name):
        """world point: 'bone' = head, 'bone_tail' = tail"""
        if name.endswith("_tail"): b = name[:-5]; return fkm[b] @ V((0, self.blen[b], 0))
        return fkm[name].translation.copy()
    def xform(self, fkm, bone):
        """bone's rigid world transform: rest armature-space point -> posed world point"""
        return fkm[bone] @ self.rest4i[bone]
    def com(self, fkm):
        c = V(); m = 0.0
        for _, a, b, w, r in SEGMENTS:
            pa = self.joint(fkm, a) if a != "head" else self.joint(fkm, "head")
            pb = self.joint(fkm, b)
            c += (pa.lerp(pb, r)) * w; m += w
        return c / m
    def support(self, st, fkm):
        """support polygon points (world xy) of the planted feet: heel + ball, +-4 cm wide; heel-up feet only the ball."""
        pts = []
        for sd in "LR":
            if st.get("_cls" + sd) != "plant": continue
            ank = self.joint(fkm, f"foot.{sd}"); ball = self.joint(fkm, f"foot.{sd}_tail")
            f = (ball - ank).to_2d(); f = f.normalized() if f.length > 1e-6 else V((0, -1)); sdv = V((-f.y, f.x))
            heel = ank.to_2d() - f * 0.06
            pitch = st["foot" + sd][4] if len(st["foot" + sd]) > 4 else 0.0
            toe = ball.to_2d() + f * 0.04
            for base in ([toe, ball.to_2d()] + ([] if pitch > 6 else [heel])):
                pts += [tuple(base + sdv * 0.04), tuple(base - sdv * 0.04)]
        return pts
    # ------------------------------------------------------------ whole-timeline evaluation
    def evaluate(self, story_frames, fps, balance=True):
        sts = []
        for s in range(story_frames):
            t = s / fps; st = self.blend_state(t); st["_t"] = t; st["_s"] = s
            self.apply_limits(st); sts.append(st)
        plants, steps = self.foot_lock(sts, fps)
        bal_log = []
        base_xy = [(st["x"], st["y"]) for st in sts]
        for it in range(4 if balance else 1):
            if it == 0: self.reach_fix(sts)
            res = [self.solve(st) for st in sts]
            fks = [self.fk(r[2] if False else self.objmat(st)[2], r[2], st["hs"]) for st, r in zip(sts, res)]
            out = []
            for st, fkm in zip(sts, fks):
                if not balance or self.balance_mode(st["_t"], st) != "enforce": out.append((0.0, 0.0, None)); continue
                sup = self.support(st, fkm)
                if len(sup) < 3: out.append((0.0, 0.0, None)); continue
                hull = PH.hull2d(sup); c = self.com(fkm).to_2d(); d, qp = PH.outside_dist(tuple(c), hull)
                if d <= 0.0: out.append((0.0, 0.0, 0.0)); continue
                sh = (V(qp) - c) * ((d + 0.012) / d) / 0.72
                if sh.length > 0.05: sh = sh.normalized() * 0.05       # weight transfer, not teleport: big misses are authoring errors (reported)
                out.append((sh.x, sh.y, d))
            bal_log.append(max([o[2] or 0.0 for o in out] + [0.0]))
            if not balance or it == 3 or bal_log[-1] < 0.002: break
            sx = PH.smooth([o[0] for o in out], 3); sy = PH.smooth([o[1] for o in out], 3)
            for st, a, b, (bx, by) in zip(sts, sx, sy, base_xy):
                nx, ny = st["x"] + a, st["y"] + b; dx, dy = nx - bx, ny - by; L_ = math.hypot(dx, dy)
                if L_ > 0.08: dx, dy = dx * 0.08 / L_, dy * 0.08 / L_          # total balance shift capped at 8 cm
                st["x"], st["y"] = bx + dx, by + dy
        ev = dict(states=sts, solved=res, fk=fks, plants=plants, steps=steps, balance_iters=bal_log,
                  shift=[(st["x"] - bx, st["y"] - by) for st, (bx, by) in zip(sts, base_xy)])
        self.ev = ev
        return ev
    def balance_report(self, ev):
        rows = []
        for st, fkm in zip(ev["states"], ev["fk"]):
            sup = self.support(st, fkm)
            if len(sup) < 3: rows.append(None); continue
            d, _ = PH.outside_dist(tuple(self.com(fkm).to_2d()), PH.hull2d(sup))
            rows.append((d, self.balance_mode(st["_t"], st)))
        enf = [r[0] for r in rows if r and r[1] == "enforce"]; rep = [r[0] for r in rows if r and r[1] != "enforce"]
        return dict(frames_enforced=len(enf), max_outside_cm_enforced=round(100 * max(enf + [0.0]), 2),
                    frames_dynamic=len(rep), max_outside_cm_dynamic=round(100 * max(rep + [0.0]), 2),
                    max_hip_shift_cm=round(100 * max([math.hypot(*s) for s in ev["shift"]] + [0.0]), 2))
    # ------------------------------------------------------------ bake to Blender on output frames
    def bake(self, tm, ev):
        g = self.g; pbs = g.pose.bones
        for n in list(ch.ANIM_BONES) + [n for n, _ in MV.SPINE]:
            if n in pbs: pbs[n].rotation_mode = "QUATERNION"
        g.animation_data_clear()
        for f in tm.frames():
            s = tm.story(f); st = ev["states"][s]; loc, q, qm = ev["solved"][s]
            g.location = loc; g.rotation_quaternion = q
            g.keyframe_insert("location", frame=f); g.keyframe_insert("rotation_quaternion", frame=f)
            for n, qq in qm.items():
                pbs[n].rotation_quaternion = qq; pbs[n].keyframe_insert("rotation_quaternion", frame=f)
            pbs["head"].scale = st["hs"]; pbs["head"].keyframe_insert("scale", frame=f)
            if self.pockets:                       # hand hidden inside the pocket (character_mh.hands_in_pockets), shown when out
                for sd in "LR":
                    P0 = V(MV.POCKET_L if sd == "L" else MV.POCKET_R); fp = V(st["fist" + sd][0][1])
                    k = min(1.0, max(0.0, ((fp - P0).length - 0.03) / 0.05)); sc = 0.02 + 0.98 * ez(k, "io")
                    pbs[f"wrist.{sd}"].scale = (sc, sc, sc); pbs[f"wrist.{sd}"].keyframe_insert("scale", frame=f)
        ad = g.animation_data
        if ad and ad.action:
            for fc in _fcurves(ad.action):
                for kp in fc.keyframe_points: kp.interpolation = "LINEAR"


def _fcurves(action):
    """F-curves of an action (Blender 5 layered actions keep them in layers/strips/channelbags)."""
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for ly in getattr(action, "layers", []):
        for sp in ly.strips:
            for cb in getattr(sp, "channelbags", []):
                out += list(cb.fcurves)
    return out
