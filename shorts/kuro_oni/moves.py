"""Kuro Oni motion library: a pose solver for the character_mh rigs and named fighting moves (Kyokushin + aikido) that key it.

    import moves as MV
    r = MV.Rig(arm, origin=HC)                       # one per rig; keys are collected on r, then r.bake(frames)
    MV.stance_idle(r, 0.0, 1.75, x=0, y=0, facing=90, seed=1)
    MV.slip_turn(r, 1.75, 0.15)
    MV.gyaku_zuki(r, 1.97, 0.13, target=world_point)
    r.finalize(); r.bake(range(1, 97))

SOLVER (Rig). Every frame is solved from channels, then keyed (pure maths, no depsgraph):
  x, y      hips (armature origin) position, metres, relative to `origin`; yaw = hip facing in degrees (0 = -y, 90 = +x)
  drop      how far the hips sink below standing height (knees bend through the leg IK)
  twist / lean / side   spine rotation over spine05..spine01 (shoulders turn past the hips, bend forward, bend sideways)
  hp / hy / hr          head pitch (+ = chin down) / yaw (+ = turn to his left) / roll (+ = toward his left shoulder),
                        split over neck02 + head, measured in the chest frame
  hs        head bone scale (face squash on impact)
  tilt      a whole-body rotation (axis * degrees, world) about the point between the feet: falls
  footL/R   (x, y, yaw, lift[, pitch]) ankle target on the ground (two-bone leg IK, knee toward the toes); pitch + = heel up
  fistL/R   ("c", chest-space point) or ("w", world point): two-bone arm IK, elbow down and out
Channels interpolate independently between the keys that set them, each key with its own ease
("io" smooth, "in" accelerate, "out" decelerate, "snap" fast-out, "lin"), so hips, spine, shoulder and fist can
start and land on different frames (overlapping action, the whip of a real strike).

MOVES (implemented). Each reads/updates r.ctx (position, facing, feet) so moves chain:
  stance_idle(r, t0, t1, x, y, facing, seed)   Kyokushin kamae: upright, a little bladed, feet a bit wider than the
        shoulders, knees soft, both fists high at the chin, elbows tucked, chin down; small bounce on the balls of the feet
        and a breathing rise every ~0.3 s; head level.
  step_in(r, t0, dur, dist)       yori-ashi: front foot slides first (low arc), hips follow, rear foot catches up.
  slip_turn(r, t0, dur)           duck/slip under a swing with a hip turn (tai-sabaki): sink, lean, load the rear hip
        (spine twisted back), rear fist chambers at the hip, front hand stays out as a guard, eyes on the target.
  gyaku_zuki(r, t0, dur, target)  reverse punch, kinetic chain: rear heel lifts and pivots, hips fire first, spine
        follows, shoulder last, the fist travels in a straight line from the hip and accelerates into the target; the
        front fist pulls back to the hip (hikite); weight drives forward; small overshoot/settle (kime).
  return_to_guard(r, t0, dur)     back to kamae (fists to the chin, hips back to bladed).
NOT YET (to add): mae_geri, mawashi_geri_low, hiza_geri, hook, uchi_uke, irimi_nage.
"""
import math
import bpy
from mathutils import Vector as V, Quaternion as Q, Matrix
import character_mh as ch

RAD = math.radians
FPS = 30
SPINE = [("spine05", 0.10), ("spine04", 0.20), ("spine03", 0.25), ("spine02", 0.25), ("spine01", 0.20)]
DEF = dict(x=0.0, y=0.0, yaw=0.0, drop=0.0, twist=0.0, lean=0.0, side=0.0, hp=0.0, hy=0.0, hr=0.0, hs=(1.0, 1.0, 1.0),
           tilt=(0.0, 0.0, 0.0))
GUARD_L = (0.12, -0.36, 1.52); GUARD_R = (-0.13, -0.24, 1.44)       # chest space: front fist at the chin, rear at the jaw
HIKITE_L = (0.21, 0.02, 1.06); HIKITE_R = (-0.21, 0.02, 1.06)       # fist pulled to the hip
POCKET_L = (0.215, -0.045, 0.80); POCKET_R = (-0.215, -0.045, 0.80)  # hand inside the front pants pocket (armature-local, follows the hips)

def ez(k, kind):
    k = max(0.0, min(1.0, k))
    if kind == "lin": return k
    if kind == "in": return k * k
    if kind == "out": return 1 - (1 - k) ** 2
    if kind == "snap": return 1 - (1 - k) ** 3
    return k * k * (3 - 2 * k)
def _lerp(a, b, k):
    if isinstance(a, (int, float)): return a + (b - a) * k
    if len(a) != len(b): a, b = tuple(a) + (0.0,) * (len(b) - len(a)), tuple(b) + (0.0,) * (len(a) - len(b))
    return tuple(x + (y - x) * k for x, y in zip(a, b))
def T_(f): return (f - 1) / FPS

class Rig:
    def __init__(self, g, origin=(0, 0, 0)):
        self.g = g; self.O = V(origin); B = g.data.bones; self.B = B; self.s = g.scale[0]; self.base_z = g["base_z"]; zg = g["sole_rest"]
        self.rest = {b.name: b.matrix_local.to_3x3() for b in B}
        self.leg = {}
        for sd in "LR":
            hip = B[f"upperleg01.{sd}"].head_local; knee = B[f"lowerleg01.{sd}"].head_local
            ank = B[f"foot.{sd}"].head_local; tip = B[f"foot.{sd}"].tail_local
            self.leg[sd] = dict(hip=hip.copy(), Lt=(knee - hip).length, Ls=(ank - knee).length, fdir=(tip - ank).normalized(), ah=ank.z - zg,
                                flen=(tip - ank).length)
        self.arm = {sd: ((B[f"lowerarm01.{sd}"].head_local - B[f"upperarm01.{sd}"].head_local).length,
                         (B[f"wrist.{sd}"].head_local - B[f"lowerarm01.{sd}"].head_local).length) for sd in "LR"}
        self.piv = B["spine05"].head_local.copy()
        g.rotation_mode = "QUATERNION"
        for n in ch.ANIM_BONES + [n for n, _ in SPINE]:
            if n in g.pose.bones: g.pose.bones[n].rotation_mode = "QUATERNION"
        self.keys = []; self.ctx = {}
    # ---- solver
    def objmat(self, st):
        qy = Q((0, 0, 1), RAD(st["yaw"])); loc = self.O + V((st["x"], st["y"], self.base_z - st["drop"]))
        tv = V(st["tilt"]); q = qy
        if tv.length > 1e-6:
            qt = Q(tv.normalized(), RAD(tv.length)); pivot = self.O + V((st["x"], st["y"], 0.0))
            loc = pivot + qt @ (loc - pivot); q = qt @ qy
        return loc, q, Matrix.LocRotScale(loc, q, V((self.s,) * 3))
    def chest(self, st):
        A = ch._MathAim(self.g)
        tw, ln, sd = RAD(st["twist"]), RAD(st["lean"]), RAD(st["side"])
        for n, fr in SPINE:
            R = Matrix.Rotation(tw * fr, 3, "Z") @ Matrix.Rotation(ln * fr, 3, "X") @ Matrix.Rotation(sd * fr, 3, "Y")
            A.final[n] = R @ A.rot(n)
        return A, A.final["spine01"] @ self.rest["spine01"].inverted()
    def chest_to_world(self, st, p):
        _, Rc = self.chest(st); _, _, M = self.objmat(st)
        return M @ (self.piv + Rc @ (V(p) - self.piv))
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
        for sd, sx in (("L", 1), ("R", -1)):                      # arms: fist targets -> two-bone IK, elbows down and tucked
            v0, v1, kk = st["fist" + sd]
            loc_ = lambda v: V(v[1]) if v[0] == "h" else Mi @ V(v[1])
            T = loc_(v0).lerp(loc_(v1), kk); S = pos(f"upperarm01.{sd}")
            Wt = T - (T - S).normalized() * 0.075
            Lu, Lf = self.arm[sd]; v = Wt - S
            d = max(abs(Lu - Lf) + 0.03, min(v.length, 0.999 * (Lu + Lf))); vn = v.normalized()
            a = math.acos(max(-1.0, min(1.0, (Lu * Lu + d * d - Lf * Lf) / (2 * Lu * d))))
            pole = Rc @ V((sx * 0.35, 0.3, -1.0)); w = (pole - vn * pole.dot(vn)).normalized()
            up = vn * math.cos(a) + w * math.sin(a); elbow = S + up * Lu; fore = (S + vn * d - elbow).normalized()
            for b in ("upperarm01", "upperarm02"): A(f"{b}.{sd}", up)
            for b in ("lowerarm01", "lowerarm02", "wrist"): A(f"{b}.{sd}", fore)
        for sd in "LR":                                            # legs: ankle targets -> two-bone IK, knee over the toes
            gl = self.leg[sd]; ft = st["foot" + sd]; fx, fy, fyaw, lift = ft[:4]; pitch = ft[4] if len(ft) > 4 else 0.0
            h = gl["fdir"].to_2d().length
            fdw = V((math.sin(RAD(fyaw)) * h, -math.cos(RAD(fyaw)) * h, gl["fdir"].z))
            if pitch:                                              # heel up: the foot rolls over its toes
                ax = V((math.cos(RAD(fyaw)), math.sin(RAD(fyaw)), 0)); fdw = Matrix.Rotation(-RAD(pitch), 3, ax) @ fdw
                lift = lift + gl["flen"] * self.s * math.sin(RAD(pitch)) * 0.8
            T = Mi @ (self.O + V((fx, fy, lift + gl["ah"] * self.s)))
            fd = (R3i @ fdw).normalized()
            fwd = V((fd.x, fd.y, 0.0)).normalized() if fd.to_2d().length > 1e-3 else V((0, -1, 0))
            v = T - gl["hip"]; d = min(v.length, 0.999 * (gl["Lt"] + gl["Ls"])); vn = v.normalized()
            a = math.acos(max(-1.0, min(1.0, (gl["Lt"] ** 2 + d * d - gl["Ls"] ** 2) / (2 * gl["Lt"] * d))))
            w = (fwd - vn * fwd.dot(vn)).normalized()
            th = vn * math.cos(a) + w * math.sin(a); knee = gl["hip"] + th * gl["Lt"]; sh = (gl["hip"] + vn * d - knee).normalized()
            A(f"upperleg01.{sd}", th); A(f"upperleg02.{sd}", th); A(f"lowerleg01.{sd}", sh); A(f"lowerleg02.{sd}", sh)
            A(f"foot.{sd}", fd)
        out = A.quats()
        for n, _ in SPINE + [("neck02", 0), ("head", 0)]:
            b = B[n]; inh = A.rot(b.parent.name) @ self.rest[b.parent.name].inverted() @ self.rest[n]
            out[n] = (inh.inverted() @ A.final[n]).to_quaternion()
        return loc, q, out
    # ---- timeline
    def key(self, t, ease="io", **ch_):
        self.keys.append((t, ch_, ease))
    def finalize(self):
        """Convert chest-space fists ('c', p) to world at their key time (fist paths are then straight lines in the world)."""
        self.keys.sort(key=lambda k: k[0])
        for t, d, _ in self.keys:
            for sd in "LR":
                v = d.get("fist" + sd)
                if v is not None and v[0] == "c": d["_c" + sd] = v
        for t, d, _ in self.keys:
            for sd in "LR":
                if "_c" + sd in d:
                    st = self.state(t, skip_fists=True); d["fist" + sd] = ("w", tuple(self.chest_to_world(st, d["_c" + sd][1])))
    def chan(self, name, t):
        ks = [(tk, d[name], e) for tk, d, e in self.keys if name in d]
        if not ks: return DEF[name]
        val = lambda v: v[1] if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str) else v
        if t <= ks[0][0]: return val(ks[0][1])
        for (t0, v0, _), (t1, v1, e1) in zip(ks, ks[1:]):
            if t0 <= t <= t1: return _lerp(val(v0), val(v1), ez((t - t0) / max(1e-6, t1 - t0), e1))
        return val(ks[-1][1])
    def state(self, t, skip_fists=False):
        st = {n: self.chan(n, t) for n in list(DEF) + ["footL", "footR"]}
        if not skip_fists:
            for sd in "LR": st["fist" + sd] = self.chan_fist("fist" + sd, t)
        return st
    def chan_fist(self, name, t):
        """-> (v0, v1, k): two raw keys ((\"w\", world pt) or (\"h\", armature-local pt)) and the blend 0..1, resolved in solve()."""
        ks = [(tk, d[name], e) for tk, d, e in self.keys if name in d]
        if not ks: return (("h", (0, 0, 0)),) * 2 + (0.0,)
        if t <= ks[0][0]: return ks[0][1], ks[0][1], 0.0
        for (t0, v0, _), (t1, v1, e1) in zip(ks, ks[1:]):
            if t0 <= t <= t1: return v0, v1, ez((t - t0) / max(1e-6, t1 - t0), e1)
        return ks[-1][1], ks[-1][1], 0.0
    def bake(self, frames):
        g = self.g; pbs = g.pose.bones
        for f in frames:
            st = self.state(T_(f)); loc, q, qm = self.solve(st)
            g.location = loc; g.rotation_quaternion = q
            g.keyframe_insert("location", frame=f); g.keyframe_insert("rotation_quaternion", frame=f)
            for n, qq in qm.items():
                pbs[n].rotation_quaternion = qq; pbs[n].keyframe_insert("rotation_quaternion", frame=f)
            pbs["head"].scale = st["hs"]; pbs["head"].keyframe_insert("scale", frame=f)

# ------------------------------------------------------------------ helpers
def basis(facing):
    f = RAD(facing); fwd = V((math.sin(f), -math.cos(f))); left = V((-fwd.y, fwd.x)); return fwd, left
def kamae_feet(x, y, facing, width=1.0):
    """orthodox stance, left foot forward: front foot 0.38 m ahead and 0.10 m to the left of the hips, rear foot 0.36 m back
    and 0.20 m right (feet a bit wider than the shoulders), front toes to the target, rear foot turned out ~50 deg."""
    fwd, left = basis(facing); p = V((x, y))
    a = p + fwd * 0.38 * width + left * 0.10; b = p - fwd * 0.36 * width - left * 0.20
    return (a.x, a.y, facing + 2, 0.0, 0.0), (b.x, b.y, facing - 50, 0.0, 6.0)      # rear heel a little light
def stance_feet(x, y, yaw, front=(0.13, -0.30), back=(-0.15, 0.27), fy=(8, -38), shift=(0.0, 0.0)):
    """feet for hips at (x, y) with hip yaw (deg); offsets in the body frame (+x = his left, -y = forward). For the ring men."""
    R = Matrix.Rotation(RAD(yaw), 3, "Z")
    out = []
    for (ox, oy), dy in ((front, fy[0]), (back, fy[1])):
        p = R @ V((ox, oy, 0)); out.append((x + p.x + shift[0], y + p.y + shift[1], yaw + dy, 0.0))
    return out
def _look(ctx, yaw, twist):
    """head yaw that keeps the eyes on the target while hips and shoulders turn (head stays level and still)."""
    return max(-35.0, min(35.0, ctx["facing"] - (yaw + twist)))

# ------------------------------------------------------------------ moves
def stance_idle(r, t0, t1, x, y, facing, seed=0, bounce=0.022, period=0.34):
    """Kamae with a live bounce: hips bob on the balls of the feet, breathing lifts the guard a touch, shoulders breathe."""
    import random
    rng = random.Random(seed); fl, fr = kamae_feet(x, y, facing); yaw = facing - 28; tw = 18
    r.ctx.update(x=x, y=y, facing=facing, yaw=yaw, twist=tw, footL=fl, footR=fr, drop=0.11)
    r.key(t0, x=x, y=y, yaw=yaw, drop=0.11, twist=tw, lean=7, side=0, hp=6, hy=_look(r.ctx, yaw, tw), hr=0, footL=fl, footR=fr,
          fistL=("c", GUARD_L), fistR=("c", GUARD_R), tilt=(0, 0, 0), hs=(1, 1, 1))
    t = t0 + period * rng.uniform(0.4, 0.7); up = True
    while t < t1 - 0.05:
        d = 0.11 - bounce * 0.5 if up else 0.11 + bounce * 0.5
        br = 0.012 if up else -0.006
        r.key(t, drop=d, twist=tw + rng.uniform(-2.5, 2.5), lean=7 + rng.uniform(-1, 1),
              fistL=("c", (GUARD_L[0], GUARD_L[1], GUARD_L[2] + br)), fistR=("c", (GUARD_R[0], GUARD_R[1], GUARD_R[2] + br * 0.7)))
        t += period * rng.uniform(0.85, 1.15); up = not up
    r.key(t1, x=x, y=y, yaw=yaw, drop=0.11, twist=tw, lean=7, side=0, hp=6, hy=_look(r.ctx, yaw, tw), footL=fl, footR=fr,
          fistL=("c", GUARD_L), fistR=("c", GUARD_R))

def step_in(r, t0, dur, dist):
    """yori-ashi: front foot first (low slide, 3 cm clearance), hips follow, rear foot catches up; stance keeps its shape."""
    c = r.ctx; fwd, _ = basis(c["facing"]); dv = fwd * dist
    fl, fr = c["footL"], c["footR"]
    nl = (fl[0] + dv.x, fl[1] + dv.y) + tuple(fl[2:]); nr = (fr[0] + dv.x, fr[1] + dv.y) + tuple(fr[2:])
    r.key(t0, footL=fl, footR=fr, x=c["x"], y=c["y"])
    r.key(t0 + dur * 0.3, footL=(fl[0] + dv.x * 0.5, fl[1] + dv.y * 0.5, fl[2], 0.03, 0.0))
    r.key(t0 + dur * 0.6, footL=nl, ease="in")
    r.key(t0 + dur * 0.85, x=c["x"] + dv.x, y=c["y"] + dv.y)
    r.key(t0 + dur * 0.5, footR=fr)
    r.key(t0 + dur * 0.78, footR=(fr[0] + dv.x * 0.6, fr[1] + dv.y * 0.6, fr[2], 0.025, 10.0))
    r.key(t0 + dur, footR=nr, ease="out")
    c.update(x=c["x"] + dv.x, y=c["y"] + dv.y, footL=nl, footR=nr)

def slip_turn(r, t0, dur=0.15, hold=0.07, pocket=False):
    """Duck under a swing with a hip turn: sink, bend forward and away, load the rear hip (shoulders twisted back), rear fist
    chambers at the hip, front hand out as a shield, eyes on the man. 1-frame anticipation (a tiny rise) before the sink."""
    c = r.ctx; yaw = c["facing"] - 35; tw = -12
    if pocket:      # nonchalant slip: the body drops and turns away from the swing, both hands stay in the pockets
        PR, PL = ("h", POCKET_R), ("h", POCKET_L)
        r.key(t0, drop=c.get("drop", 0.11), lean=c.get("lean", 4), side=0, twist=c["twist"], yaw=c["yaw"], hp=c.get("hp", 0), fistR=PR, fistL=PL)
        r.key(t0 + dur, drop=0.24, lean=20, side=-8, twist=tw, yaw=yaw, hy=_look(c, yaw, tw) * 0.8, hp=-10, fistR=PR, fistL=PL, ease="snap")
        r.key(t0 + dur + hold, drop=0.21, lean=17, side=-6, twist=tw - 2, yaw=yaw + 2, hp=-9, fistR=PR, fistL=PL)
        c.update(yaw=yaw + 2, twist=tw - 2, drop=0.21)
        return
    r.key(t0, drop=c.get("drop", 0.11), lean=7, side=0, twist=c["twist"], yaw=c["yaw"], hp=6, fistR=("c", GUARD_R), fistL=("c", GUARD_L))
    r.key(t0 + 0.035, drop=c.get("drop", 0.11) - 0.015, ease="out")                     # anticipation
    r.key(t0 + dur, drop=0.25, lean=24, side=-8, twist=tw, yaw=yaw, hy=_look(c, yaw, tw) * 0.8, hp=-14,
          fistR=("c", HIKITE_R), fistL=("c", (0.10, -0.42, 1.44)), ease="snap")
    r.key(t0 + dur + hold, drop=0.22, lean=20, side=-6, twist=tw - 2, yaw=yaw + 2, hp=-12, fistR=("c", HIKITE_R))
    c.update(yaw=yaw + 2, twist=tw - 2, drop=0.22)

def gyaku_zuki(r, t0, dur, target, drive=0.08, overshoot=0.035, pocket=False):
    """Reverse punch with the rear (right) hand, contact at t0 + dur. Kinetic chain with overlap:
    rear heel lifts + pivots (0-60%) -> hips fire (10-75%, then square at 100%) -> spine/shoulder (35-100%, snap) ->
    fist leaves the hip late (25%) and accelerates in a straight line into the target; hikite pulls the front fist back;
    weight drives forward by `drive`; after contact the twist overshoots a touch and settles (kime)."""
    c = r.ctx; f = c["facing"]; fwd, _ = basis(f); fr = c["footR"]; tgt = V(target)
    nx, ny = c["x"] + fwd.x * drive, c["y"] + fwd.y * drive
    r.key(t0, x=c["x"], y=c["y"], footR=fr, fistR=("h", POCKET_R) if pocket else ("c", HIKITE_R))
    r.key(t0 + dur * 0.6, footR=(fr[0], fr[1], f - 22, 0.0, 24.0), ease="out")                 # heel up, pivot on the ball
    r.key(t0 + dur, footR=(fr[0], fr[1], f - 12, 0.0, 30.0), ease="out")
    r.key(t0 + dur * 0.75, yaw=f - 6, ease="in"); r.key(t0 + dur, yaw=f + 2, ease="out")       # hips lead
    r.key(t0 + dur * 0.35, twist=c["twist"])
    r.key(t0 + dur, twist=14, ease="in")                                                         # shoulder whips through
    r.key(t0 + dur, x=nx, y=ny, drop=0.08, lean=8, side=0, hp=-4, hy=_look(c, f + 2, 14), ease="io")
    r.key(t0 + dur * 0.25, fistR=("c", HIKITE_R))                                              # out of the pocket up to the hip
    r.key(t0 + dur, fistR=("w", tuple(tgt)), ease="in")                                         # fist accelerates
    if pocket: r.key(t0, fistL=("h", POCKET_L)); r.key(t0 + dur + 0.2, fistL=("h", POCKET_L))   # the other hand stays in its pocket
    else:
        r.key(t0 + dur * 0.2, fistL=("c", (0.10, -0.42, 1.44)))
        r.key(t0 + dur, fistL=("c", HIKITE_L), ease="snap")                                      # hikite
    d = (tgt - r.chest_to_world(r.state(t0 + dur, skip_fists=True), (-0.2, 0.0, 1.45))).normalized()
    r.key(t0 + dur + 0.05, twist=17, fistR=("w", tuple(tgt + d * overshoot)), ease="out")        # drives through
    r.key(t0 + dur + 0.16, twist=15, fistR=("w", tuple(tgt + d * overshoot * 0.7)), ease="io")   # settles: kime
    if pocket:
        r.key(t0 + dur + 0.30, fistR=("h", POCKET_R), ease="io")                                 # the fist goes back into the pocket
        c.update(x=nx, y=ny, yaw=f + 2, twist=15, drop=0.08, footR=(fr[0], fr[1], f - 12, 0.0, 30.0), fistR=("h", POCKET_R), fistL=("h", POCKET_L))
        return
    c.update(x=nx, y=ny, yaw=f + 2, twist=15, drop=0.08, footR=(fr[0], fr[1], f - 12, 0.0, 30.0),
             fistR=("w", tuple(tgt + d * overshoot * 0.7)), fistL=("c", HIKITE_L))

def return_to_guard(r, t0, dur=0.25):
    c = r.ctx; f = c["facing"]; fl, fr = kamae_feet(c["x"], c["y"], f); yaw = f - 28
    r.key(t0, yaw=c["yaw"], twist=c["twist"], drop=c["drop"], fistR=c.get("fistR", ("c", GUARD_R)), fistL=c.get("fistL", ("c", GUARD_L)))
    r.key(t0 + dur * 0.4, fistR=("c", (-0.16, -0.30, 1.30)), ease="snap")                      # fist snaps back first
    r.key(t0 + dur, yaw=yaw, twist=18, drop=0.11, lean=7, side=0, hp=6, hy=_look(c, yaw, 18), footL=fl, footR=fr,
          fistL=("c", GUARD_L), fistR=("c", GUARD_R), ease="io")
    c.update(yaw=yaw, twist=18, drop=0.11, footL=fl, footR=fr)


def pocket_feet(x, y, facing):
    """relaxed stance: feet about shoulder width, front foot a little ahead, toes slightly out."""
    fwd, left = basis(facing); p = V((x, y))
    a = p + fwd * 0.20 + left * 0.12; b = p - fwd * 0.16 - left * 0.14
    return (a.x, a.y, facing + 8, 0.0, 0.0), (b.x, b.y, facing - 25, 0.0, 0.0)

def pocket_idle(r, t0, t1, x, y, facing, seed=0):
    """Nonchalant stance, both hands in the front pants pockets (hands_in_pockets): shoulders relaxed, a slight slouch (a little
    forward lean, chin down), a slow weight shift side to side and a small breath every ~1.3 s. No guard, no bounce."""
    import random
    rng = random.Random(seed); fl, fr = pocket_feet(x, y, facing); yaw = facing - 14; tw = 6
    PR, PL = ("h", POCKET_R), ("h", POCKET_L)
    r.ctx.update(x=x, y=y, facing=facing, yaw=yaw, twist=tw, footL=fl, footR=fr, drop=0.05, lean=4, hp=3)
    r.key(t0, x=x, y=y, yaw=yaw, drop=0.05, twist=tw, lean=4, side=0, hp=3, hy=_look(r.ctx, yaw, tw), hr=0, footL=fl, footR=fr,
          fistL=PL, fistR=PR, tilt=(0, 0, 0), hs=(1, 1, 1))
    fwd, left = basis(facing); t = t0; k = 0
    while t < t1 - 0.2:
        t += 0.65 * rng.uniform(0.9, 1.1); k += 1; sh = 0.012 * (1 if k % 2 else -1)
        r.key(t, drop=0.05 + (0.008 if k % 2 else -0.004), side=1.5 * (1 if k % 2 else -1), twist=tw + rng.uniform(-1.5, 1.5), lean=4 + (0.8 if k % 2 else 0),
              x=x + left.x * sh, y=y + left.y * sh, fistL=PL, fistR=PR)
    r.key(t1, x=x, y=y, yaw=yaw, drop=0.05, twist=tw, lean=4, side=0, hp=3, hy=_look(r.ctx, yaw, tw), footL=fl, footR=fr, fistL=PL, fistR=PR)

def turn_to(r, t0, dur, newf):
    """turn on the spot to a new facing (pivot via small stepping arcs), ending in the pocket stance; hands stay in the pockets."""
    c = r.ctx; x, y = c["x"], c["y"]; fl0, fr0 = c["footL"], c["footR"]; fl, fr = pocket_feet(x, y, newf); yaw = newf - 14
    PR, PL = ("h", POCKET_R), ("h", POCKET_L)
    r.key(t0, footL=fl0, footR=fr0, yaw=c["yaw"], twist=c["twist"], drop=c["drop"], fistL=PL, fistR=PR, x=x, y=y)
    mid_f = 0.5 * (fl0[2] + fl[2]); mid_r = 0.5 * (fr0[2] + fr[2])
    r.key(t0 + dur * 0.45, footL=(x, y - 0.28, mid_f, 0.07), footR=(x, y + 0.28, mid_r, 0.05), yaw=0.5 * (c["yaw"] + yaw), drop=0.08)   # feet swing past each other
    r.key(t0 + dur, footL=fl, footR=fr, yaw=yaw, twist=6, drop=0.05, lean=4, side=0, hp=3, hy=_look(r.ctx | dict(facing=newf), yaw, 6), fistL=PL, fistR=PR, ease="out")
    c.update(facing=newf, yaw=yaw, twist=6, footL=fl, footR=fr, drop=0.05, lean=4, hp=3)
