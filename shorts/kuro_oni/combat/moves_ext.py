"""Combat moves on top of shorts/kuro_oni/moves.py (which is reused unchanged: pocket_idle, stance_idle, slip_turn,
gyaku_zuki, step_in). New here: mawashi_geri_low, kick_recover, pocket_recover, turn_step (ball pivot + step round),
guard_recover, hook_r and lunge_punch (enemy attacks), hurt_idle, uchi_uke, plus pivot_keys (heel turn about the ball).

Key poses are authored from real full-contact Kyokushin footage (local only, never committed):
  local_refs/kyo/6c78c241-...21-42-29_1.png  (sheet) / uploads .../6c78c241-ScreenRecording_11-25-2569_21-42-29_1.mp4
      t = 1.9-3.5 s: mawashi geri. Chamber 0.13-0.27 s, contact ~0.40 s after the knee starts up, support foot turns out
      ~70 deg on its ball, hips roll over, shoulders stay square and level, guard / head do not move; defender's head
      snaps back at +0.2 s, re-planted by +0.4 s.
  local_refs/kyo/1801077b-...21-42-56_1.png  (sheet) / uploads .../1801077b-ScreenRecording_11-25-2569_21-42-56_1.mp4
      t = 4.3-4.5 s: close-range gyaku-zuki to the body (hips square into it, rear heel up, ~0.13 s), t = 4.8-4.95 s:
      gedan mawashi (low kick) with the shin into the outer thigh, ~0.2 s from lift to contact; upright posture, small
      steps, no bounce between strikes.
Every move signature: fn(r, t0, dur, ease, params, W) where r is a solver.Layer (moves.Rig API) and W the world
(other actors' positions / body parts for aiming). Times are seconds of story time.
"""
import math
from mathutils import Vector as V, Matrix
import moves as MV

RAD = math.radians
PR, PL = ("h", MV.POCKET_R), ("h", MV.POCKET_L)


def heading(frm, to):
    d = V(tuple(to)[:2]) - V(tuple(frm)[:2]); return math.degrees(math.atan2(d.x, -d.y))


def _look(facing, yaw, twist, lim=60.0):
    return max(-lim, min(lim, facing - (yaw + twist)))


def _lift_for(r, side, z, pitch=0.0):
    """authored lift that puts the ankle at world height z (the solver reads heel pitch as +0.8 flen sin(pitch))."""
    gl = r.rig.leg[side]; return z - r.rig.O.z - gl["ah"] * r.rig.s - (gl["flen"] * r.rig.s * math.sin(RAD(pitch)) * 0.8 if pitch else 0.0)


def pivot_keys(r, side, t0, t1, yaw0, yaw1, pitch0=0.0, pitch1=0.0, ease="io", n=6):
    """heel turn about the BALL of a planted foot: keys whose ankle moves on the arc that keeps the ball still."""
    R = r.rig; c = r.ctx; ft = c["foot" + side]
    ank = R.ankle_auth(side, ft); ball = R.ball_of(side, ank, ft[2], ft[4] if len(ft) > 4 else 0.0)
    for k in range(n + 1):
        u = k / n; e = MV.ez(u, ease); yw = yaw0 + (yaw1 - yaw0) * e; pt = pitch0 + (pitch1 - pitch0) * e
        fd = R.foot_dir(side, yw, pt); a = ball - fd * R.leg[side]["flen"] * R.s
        lift = a.z - R.O.z - R.leg[side]["ah"] * R.s - (R.leg[side]["flen"] * R.s * math.sin(RAD(pt)) * 0.8 if pt else 0.0)
        r.key(t0 + (t1 - t0) * u, "lin", **{"foot" + side: (a.x - R.O.x, a.y - R.O.y, yw, max(0.0, lift), pt)})
    a = ball - R.foot_dir(side, yaw1, pitch1) * R.leg[side]["flen"] * R.s
    c["foot" + side] = (a.x - R.O.x, a.y - R.O.y, yaw1, 0.0, pitch1)


def step_foot(r, side, t0, t1, target, lift=0.05, ease="io"):
    """lift a foot on a low arc and set it down on target (x, y, yaw[, 0, pitch])."""
    c = r.ctx; f0 = c["foot" + side]; tg = tuple(target) + (0.0,) * (4 - len(target)) if len(target) < 4 else tuple(target)
    r.key(t0, **{"foot" + side: f0})
    mid = ((f0[0] + tg[0]) / 2, (f0[1] + tg[1]) / 2, (f0[2] + tg[2]) / 2, lift, 6.0)
    r.key(t0 + (t1 - t0) * 0.5, "out", **{"foot" + side: mid})
    r.key(t1, "in", **{"foot" + side: (tg[0], tg[1], tg[2], 0.0, tg[4] if len(tg) > 4 else 0.0)})
    c["foot" + side] = (tg[0], tg[1], tg[2], 0.0, tg[4] if len(tg) > 4 else 0.0)


# ------------------------------------------------------------------ idles
def m_pocket_idle(r, t0, dur, ease, p, W):
    c = r.ctx; MV.pocket_idle(r, t0, t0 + dur, c["x"], c["y"], c["facing"], seed=p.get("seed", 0))

def m_guard_idle(r, t0, dur, ease, p, W):
    c = r.ctx; MV.stance_idle(r, t0, t0 + dur, c["x"], c["y"], c["facing"], seed=p.get("seed", 0), bounce=p.get("bounce", 0.018))

def m_hurt_idle(r, t0, dur, ease, p, W):
    """winded after a body shot: hunched over the stomach, guard low, heavy slow breaths (no bounce)."""
    import random
    c = r.ctx; rng = random.Random(p.get("seed", 5)); f = c["facing"]
    base = dict(lean=c.get("lean", 22), drop=c.get("drop", 0.16), twist=c.get("twist", 10), hp=c.get("hp", 14))
    r.key(t0, x=c["x"], y=c["y"], yaw=c["yaw"], footL=c["footL"], footR=c["footR"], fistL=("c", (0.14, -0.30, 1.22)), fistR=("c", (-0.10, -0.26, 1.18)), **base)
    t = t0; k = 0
    while t < t0 + dur - 0.3:
        t += 0.55 * rng.uniform(0.9, 1.15); k += 1
        r.key(t, lean=base["lean"] + (3.0 if k % 2 else -1.0), drop=base["drop"] + (0.012 if k % 2 else -0.004), hp=base["hp"] + (3 if k % 2 else 0))
    r.key(t0 + dur, **base)


# ------------------------------------------------------------------ hero moves (reuse moves.py)
def m_slip_turn(r, t0, dur, ease, p, W):
    hold = p.get("hold", dur * 0.3); MV.slip_turn(r, t0, max(0.06, dur - hold), hold=hold, pocket=p.get("pocket", False))

def m_gyaku_zuki(r, t0, dur, ease, p, W):
    tgt = W.hit_target(p["hit"])
    MV.gyaku_zuki(r, t0, dur, tgt, drive=p.get("drive", 0.08), pocket=p.get("pocket", False))
    if p.get("pocket", False):     # from the pocket the fist goes straight from the hip to the target, accelerating all the way
        for tk, d, _ in r.keys:
            if "fistR" in d and abs(tk - (t0 + dur * 0.25)) < 1e-6 and d["fistR"][0] == "c": del d["fistR"]
    W.mark_effector_keys(r, p["hit"], "fistR", t0 + dur)

def m_uchi_uke(r, t0, dur, ease, p, W):
    """inside block: forearm sweeps outward across the face, hips turn a little into it."""
    c = r.ctx; sd = p.get("side", "L"); sx = 1 if sd == "L" else -1
    r.key(t0, twist=c["twist"], **{"fist" + sd: ("c", MV.GUARD_L if sd == "L" else MV.GUARD_R)})
    r.key(t0 + dur * 0.6, "snap", twist=c["twist"] - 10 * sx, **{"fist" + sd: ("c", (sx * 0.20, -0.38, 1.50))})
    r.key(t0 + dur, twist=c["twist"] - 6 * sx, **{"fist" + sd: ("c", (sx * 0.16, -0.36, 1.48))})

def _pocket_stance(c, x, y, f):
    fl, fr = MV.pocket_feet(x, y, f); return fl, fr, f - 14

def m_pocket_recover(r, t0, dur, ease, p, W):
    """settle back into the hands-in-pockets stance: step whichever foot is off its spot (rear first), restore the slouch."""
    c = r.ctx; f = c["facing"]; fl, fr, yaw = _pocket_stance(c, c["x"], c["y"], f)
    r.key(t0, yaw=c["yaw"], twist=c["twist"], drop=c.get("drop", 0.05), lean=c.get("lean", 4), side=c.get("side", 0), hp=c.get("hp", 3))
    order = sorted((("L", fl), ("R", fr)), key=lambda sf: -(V(sf[1][:2]) - V(c["foot" + sf[0]][:2])).length)
    tt = t0
    for sd, tg in order:
        if (V(tg[:2]) - V(c["foot" + sd][:2])).length > 0.03 or abs(tg[2] - c["foot" + sd][2]) > 8:
            step_foot(r, sd, tt, tt + dur * 0.5, tg, lift=0.035); tt += dur * 0.35
        else:
            r.key(t0, **{"foot" + sd: c["foot" + sd]}); r.key(t0 + dur, **{"foot" + sd: tg}); c["foot" + sd] = tg
    r.key(t0 + dur, ease, yaw=yaw, twist=6, drop=0.05, lean=4, side=0, hp=3, hy=_look(f, yaw, 6, 35), fistL=PL, fistR=PR)
    c.update(yaw=yaw, twist=6, drop=0.05, lean=4, side=0, hp=3)


def _stance_template(pocket, x, y, f):
    if pocket:
        fl, fr = MV.pocket_feet(x, y, f); return fl, fr, f - 14
    fl, fr = MV.kamae_feet(x, y, f); return fl, fr, f - 28


def m_turn_step(r, t0, dur, ease, p, W):
    """Turn to a new facing the Kyokushin way: eyes and head first, then shoulders, hips; the foot nearer the new direction
    pivots on its ball (heel turn), the other foot steps round on a low arc. Keeps the stance shape."""
    c = r.ctx; R = r.rig; pocket = p.get("pocket", R.pockets)
    nf = p["facing"] if "facing" in p else heading((c["x"], c["y"]), W.pos(p["face"], t0 + dur))
    while nf - c["facing"] > 180: nf -= 360
    while nf - c["facing"] < -180: nf += 360
    fwd, left = MV.basis(nf)
    def proj(sd): return V(c["foot" + sd][:2]).dot(fwd)
    piv = "L" if proj("L") >= proj("R") else "R"; oth = "R" if piv == "L" else "L"
    tl, tr, yaw = _stance_template(pocket, 0.0, 0.0, nf)
    tpl = dict(L=tl, R=tr)
    ft = c["foot" + piv]; ank = R.ankle_auth(piv, ft); ball = R.ball_of(piv, ank, ft[2], ft[4] if len(ft) > 4 else 0.0)
    na = ball - R.foot_dir(piv, tpl[piv][2], 0.0) * R.leg[piv]["flen"] * R.s
    hx, hy = na.x - R.O.x - tpl[piv][0], na.y - R.O.y - tpl[piv][1]
    tgt_o = (tpl[oth][0] + hx, tpl[oth][1] + hy, tpl[oth][2], 0.0, 0.0)
    hy0 = c.get("hy", 0.0) if "hy" in c else _look(c["facing"], c["yaw"], c["twist"])
    tw_end = 6 if pocket else 18
    r.key(t0, x=c["x"], y=c["y"], yaw=c["yaw"], twist=c["twist"], hy=hy0, drop=c.get("drop", 0.05))
    r.key(t0 + dur * 0.30, "out", hy=_look(nf, c["yaw"], c["twist"], 70))                       # eyes/head lead
    r.key(t0 + dur * 0.45, twist=max(-35.0, min(35.0, c["twist"] + 0.25 * (nf - c["facing"]))), drop=c.get("drop", 0.05) + 0.02)   # shoulders before hips
    r.key(t0 + dur * 0.85, "io", yaw=yaw, x=hx, y=hy)
    r.key(t0 + dur, "out", twist=tw_end, hy=_look(nf, yaw, tw_end, 35), drop=0.05 if pocket else 0.11, lean=4 if pocket else 7, side=0)
    pivot_keys(r, piv, t0 + dur * 0.10, t0 + dur * 0.80, ft[2], tpl[piv][2], ft[4] if len(ft) > 4 else 0.0, 0.0, "io")
    step_foot(r, oth, t0 + dur * 0.20, t0 + dur * 0.95, tgt_o, lift=0.06)
    if pocket: r.key(t0, fistL=PL, fistR=PR); r.key(t0 + dur, fistL=PL, fistR=PR)
    else: r.key(t0 + dur, fistL=("c", MV.GUARD_L), fistR=("c", MV.GUARD_R))
    c.update(facing=nf, yaw=yaw, twist=tw_end, x=hx, y=hy, drop=0.05 if pocket else 0.11, lean=4 if pocket else 7, side=0)


def m_guard_recover(r, t0, dur, ease, p, W):
    q = dict(p); q.setdefault("pocket", False); m_turn_step(r, t0, dur, ease, q, W)


def m_step_in(r, t0, dur, ease, p, W):
    c = r.ctx
    if "face" in p:
        nf = heading((c["x"], c["y"]), W.pos(p["face"], t0))
        if abs(((nf - c["facing"]) + 180) % 360 - 180) > 3: c["facing"] = nf
    MV.step_in(r, t0, dur, p.get("dist", 0.25))


# ------------------------------------------------------------------ kick
def m_mawashi_geri_low(r, t0, dur, ease, p, W):
    """Gedan mawashi geri (low roundhouse), rear leg, shin into the outer thigh; hands can stay in the pockets.
    0-30 %  weight onto the front (support) foot, hips drift over it, knees soft
    20-55 % kicking heel rises then the knee lifts and turns over (chamber), support foot starts its heel turn on the ball
    55-100% hips roll over (~60 deg), shoulders counter-turn to stay square, upper body leans a little back and away,
            the shin whips on a flat arc into the target (contact at t0+dur); head level, eyes on the man."""
    c = r.ctx; R = r.rig; sd = p.get("side", "R"); sup = "L" if sd == "R" else "R"; sx = -1 if sd == "R" else 1
    tgt = V(W.hit_target(p["hit"])); tc = t0 + dur
    f = heading((c["x"], c["y"]), tgt); fwd, left = MV.basis(f); fwd = V((fwd.x, fwd.y, 0)); left = V((left.x, left.y, 0)); side_v = left * (-sx)
    tname = next(h["target"] for h in W.hits if h["id"] == p["hit"])
    fe = heading((c["x"], c["y"]), W.pos(tname, tc))                 # the eyes stay on the man (chest height), not on his leg      # side_v: toward the kicking leg's side
    fs = c["foot" + sup]; fk = c["foot" + sd]
    pocket = p.get("pocket", R.pockets)
    sx0, sy0 = c["x"], c["y"]
    sup_xy = V(fs[:2]); hip_xy = V((sx0, sy0))
    over = hip_xy.lerp(sup_xy, 0.55) + fwd.to_2d() * 0.04                                         # hips over the support foot
    yaw0 = c["yaw"]; yaw_c = f + (50 if sd == "R" else -50)
    r.key(t0, x=sx0, y=sy0, yaw=yaw0, twist=c["twist"], drop=c.get("drop", 0.05), lean=c.get("lean", 4), side=c.get("side", 0),
          hy=_look(fe, yaw0, c["twist"]), hp=c.get("hp", 3), **{"foot" + sd: fk})
    r.key(t0 + dur * 0.30, "io", x=over.x, y=over.y, drop=0.075, side=4 * (-sx))
    r.key(t0 + dur * 0.55, "in", yaw=f + (12 if sd == "R" else -12), twist=c["twist"] - 8 * (-sx), hy=_look(fe, f + (12 if sd == "R" else -12), c["twist"] - 8 * (-sx), 70))
    r.key(tc, "snap", yaw=yaw_c, twist=-28 * (-sx), lean=-5, side=11 * (-sx), drop=0.085, hp=6, hy=_look(fe, yaw_c, -28 * (-sx), 70))
    # kicking leg: heel up (push), chamber (knee up and turning over), whip to the contact
    r.key(t0 + dur * 0.18, "io", **{"foot" + sd: (fk[0], fk[1], fk[2] + 10 * (-sx), 0.0, 26.0)})        # heel up: push off
    st_c = r.state(t0 + dur * 0.45, skip_fists=True); _, _, Mc = R.objmat(st_c); hipc = Mc @ R.leg[sd]["hip"]
    ch_pt = hipc + fwd * 0.06 + side_v * 0.26                                                # chamber: knee up, foot out to the side
    zc = 0.42
    r.key(t0 + dur * 0.45, "io", **{"foot" + sd: (ch_pt.x - R.O.x, ch_pt.y - R.O.y, f + 35 * (-sx), _lift_for(r, sd, zc, 40.0), 40.0)})
    st = r.state(tc, skip_fists=True); _, _, M = R.objmat(st); hip = M @ R.leg[sd]["hip"]
    dvec = (tgt - hip); dvec.z *= 0.6; dvec.normalize()
    ank = hip + dvec * (R.leg[sd]["Lt"] + R.leg[sd]["Ls"]) * R.s * 0.97 + side_v * (-0.05)
    yk = f + 85 * (-sx)
    pre = ch_pt.lerp(ank, 0.30)                                                              # slow start of the whip ...
    r.key(t0 + dur * 0.78, "io", **{"foot" + sd: (pre.x - R.O.x, pre.y - R.O.y, f + 60 * (-sx), _lift_for(r, sd, max(zc, pre.z), 42.0), 42.0)})
    r.key(tc, "in", **{"foot" + sd: (ank.x - R.O.x, ank.y - R.O.y, yk, _lift_for(r, sd, ank.z, 45.0), 45.0)})   # ... fastest at contact
    thr = ank - side_v * 0.10 + V((0, 0, -0.03))                                           # drives through the thigh
    r.key(tc + 0.07, "out", **{"foot" + sd: (thr.x - R.O.x, thr.y - R.O.y, yk + 5 * (-sx), _lift_for(r, sd, thr.z, 45.0), 45.0)})
    r.key(tc + 0.07, "out", yaw=yaw_c + 6 * (-sx), twist=-30 * (-sx), hy=_look(fe, yaw_c + 6 * (-sx), -30 * (-sx), 70))
    # support foot: heel turn on the ball, toes out toward the kick direction
    r.ctx["foot" + sup] = fs
    pivot_keys(r, sup, t0 + dur * 0.25, tc, fs[2], fs[2] + 62 * (-sx), fs[4] if len(fs) > 4 else 0.0, 0.0, "io")
    if pocket: r.key(t0, fistL=PL, fistR=PR); r.key(tc + 0.25, fistL=PL, fistR=PR)
    W.mark_effector_keys(r, p["hit"], "foot" + sd, tc)
    c.update(x=over.x, y=over.y, yaw=yaw_c + 6 * (-sx), twist=-30 * (-sx), lean=-5, side=11 * (-sx), drop=0.085, hp=6, facing=fe, kick_side=sd,
             **{"foot" + sd: (thr.x - R.O.x, thr.y - R.O.y, yk, _lift_for(r, sd, thr.z, 45.0), 45.0)})


def m_kick_recover(r, t0, dur, ease, p, W):
    """retract the kicking leg (knee folds back in), turn the support heel back on its ball, set the foot down in stance."""
    c = r.ctx; R = r.rig; sd = p.get("side", c.get("kick_side", "R")); sup = "L" if sd == "R" else "R"; f = c["facing"]
    pocket = R.pockets
    fs = c["foot" + sup]; fk = c["foot" + sd]
    tl, tr, yaw = _stance_template(pocket, 0.0, 0.0, f); tpl = dict(L=tl, R=tr)
    ank = R.ankle_auth(sup, fs); ball = R.ball_of(sup, ank, fs[2], fs[4] if len(fs) > 4 else 0.0)
    na = ball - R.foot_dir(sup, tpl[sup][2], 0.0) * R.leg[sup]["flen"] * R.s
    hx, hy = na.x - R.O.x - tpl[sup][0], na.y - R.O.y - tpl[sup][1]
    land = (tpl[sd][0] + hx, tpl[sd][1] + hy, tpl[sd][2], 0.0, 0.0)
    st = r.state(t0 + dur * 0.35, skip_fists=True); _, _, M = R.objmat(st); hip = M @ R.leg[sd]["hip"]
    fwd, left = MV.basis(f); fwd = V((fwd.x, fwd.y, 0))
    fold = hip + fwd * 0.10 + V((0, 0, -0.45))
    r.key(t0, **{"foot" + sd: fk})
    r.key(t0 + dur * 0.35, "out", **{"foot" + sd: (fold.x - R.O.x, fold.y - R.O.y, f + 20, _lift_for(r, sd, max(0.22, fold.z), 30.0), 30.0)})
    r.key(t0 + dur * 0.80, "in", **{"foot" + sd: (land[0], land[1], land[2], 0.0, 0.0)})
    c["foot" + sd] = land
    r.ctx["foot" + sup] = fs
    pivot_keys(r, sup, t0 + dur * 0.15, t0 + dur * 0.85, fs[2], tpl[sup][2], fs[4] if len(fs) > 4 else 0.0, 0.0, "io")
    r.key(t0, x=c["x"], y=c["y"], yaw=c["yaw"], twist=c["twist"], lean=c.get("lean", 0), side=c.get("side", 0), drop=c.get("drop", 0.08))
    r.key(t0 + dur * 0.45, "out", yaw=0.5 * (c["yaw"] + yaw), twist=0.4 * c["twist"], side=0.4 * c.get("side", 0), lean=2)
    r.key(t0 + dur, "io", x=hx, y=hy, yaw=yaw, twist=6 if pocket else 18, lean=4 if pocket else 7, side=0, drop=0.05 if pocket else 0.11, hp=3,
          hy=_look(f, yaw, 6, 35))
    if pocket: r.key(t0 + dur, fistL=PL, fistR=PR)
    c.update(x=hx, y=hy, yaw=yaw, twist=6 if pocket else 18, lean=4 if pocket else 7, side=0, drop=0.05 if pocket else 0.11, hp=3)


# ------------------------------------------------------------------ enemy attacks (they miss: the hero slips them)
def _aim(W, name, t):
    return V(W.part(name, "nose", t))

def m_hook_r(r, t0, dur, ease, p, W):
    """right haymaker: wind-up (fist back, shoulders turned away), front foot steps in, hips then shoulders whip round,
    the fist travels a flat arc through where the target's head was at the start of the swing, and on across."""
    c = r.ctx; R = r.rig; aim = _aim(W, p["aim"], t0); f = heading((c["x"], c["y"]), aim); fwd, left = MV.basis(f)
    step = p.get("step", 0.28); fl = c["footL"]; fr = c["footR"]
    nl = (fl[0] + fwd.x * step, fl[1] + fwd.y * step, f + 4, 0.0, 0.0)
    r.key(t0, x=c["x"], y=c["y"], yaw=c["yaw"], twist=c["twist"], lean=c.get("lean", 7), drop=c.get("drop", 0.11), hp=c.get("hp", 6),
          fistR=("c", MV.GUARD_R), fistL=("c", MV.GUARD_L))
    r.key(t0 + dur * 0.28, "out", twist=-20, yaw=f - 36, lean=10, drop=0.13, fistR=("c", (-0.46, 0.20, 1.50)), hy=_look(f, f - 36, -20))
    step_foot(r, "L", t0 + dur * 0.15, t0 + dur * 0.48, nl, lift=0.05)
    r.key(t0 + dur * 0.55, "in", x=c["x"] + fwd.x * step * 0.75, y=c["y"] + fwd.y * step * 0.75, fistR=("c", (0.02, -0.46, 1.70)), twist=8)
    r.ctx["footR"] = fr
    pivot_keys(r, "R", t0 + dur * 0.40, t0 + dur * 0.78, fr[2], fr[2] + 32, fr[4] if len(fr) > 4 else 0.0, 22.0, "in")
    r.key(t0 + dur * 0.75, "in", fistR=("w", tuple(aim)), twist=38, yaw=f - 4, lean=14, side=4, drop=0.15, hy=_look(f, f - 4, 38), hp=2,
          fistL=("c", (0.16, -0.22, 1.30)))
    r.key(t0 + dur, "out", fistR=("c", (0.34, -0.40, 1.40)), twist=46, yaw=f + 2, lean=15)
    W.note_attack(R.name, p["aim"], t0 + dur * 0.55, t0 + dur, "fistR")
    c.update(x=c["x"] + fwd.x * step * 0.75, y=c["y"] + fwd.y * step * 0.75, yaw=f + 2, twist=46, lean=15, side=4, drop=0.15, facing=f)


def m_lunge_punch(r, t0, dur, ease, p, W):
    """straight right (oi-zuki style lunge): front foot slides in, hips square, the rear fist drives straight at the head."""
    c = r.ctx; R = r.rig; aim = _aim(W, p["aim"], t0); f = heading((c["x"], c["y"]), aim); fwd, left = MV.basis(f)
    step = p.get("step", 0.45); fl = c["footL"]; fr = c["footR"]
    nl = (fl[0] + fwd.x * step, fl[1] + fwd.y * step, f + 2, 0.0, 0.0)
    r.key(t0, x=c["x"], y=c["y"], yaw=c["yaw"], twist=c["twist"], lean=c.get("lean", 7), drop=c.get("drop", 0.11),
          fistR=("c", MV.GUARD_R), fistL=("c", MV.GUARD_L))
    r.key(t0 + dur * 0.25, "out", drop=0.14, twist=c["twist"] + 4, fistR=("c", (-0.15, -0.20, 1.40)))        # load
    step_foot(r, "L", t0 + dur * 0.10, t0 + dur * 0.50, nl, lift=0.04)
    r.key(t0 + dur * 0.70, "io", x=c["x"] + fwd.x * step * 0.85, y=c["y"] + fwd.y * step * 0.85)
    r.ctx["footR"] = fr
    pivot_keys(r, "R", t0 + dur * 0.45, t0 + dur * 0.80, fr[2], fr[2] + 24, fr[4] if len(fr) > 4 else 0.0, 24.0, "in")
    r.key(t0 + dur * 0.80, "in", fistR=("w", tuple(aim)), yaw=f - 2, twist=16, lean=14, drop=0.14, hy=_look(f, f - 2, 16), fistL=("c", (0.18, -0.10, 1.25)))
    r.key(t0 + dur, "out", fistR=("c", (-0.15, -0.34, 1.40)), twist=12, lean=12)          # snaps back (a fighter retracts)
    W.note_attack(R.name, p["aim"], t0 + dur * 0.5, t0 + dur, "fistR")
    c.update(x=c["x"] + fwd.x * step * 0.85, y=c["y"] + fwd.y * step * 0.85, yaw=f - 2, twist=19, lean=16, drop=0.14, facing=f)


MOVES = dict(pocket_idle=m_pocket_idle, guard_idle=m_guard_idle, hurt_idle=m_hurt_idle, slip_turn=m_slip_turn, gyaku_zuki=m_gyaku_zuki,
             mawashi_geri_low=m_mawashi_geri_low, uchi_uke=m_uchi_uke, pocket_recover=m_pocket_recover, kick_recover=m_kick_recover,
             guard_recover=m_guard_recover, turn_step=m_turn_step, step_in=m_step_in, hook_r=m_hook_r, lunge_punch=m_lunge_punch)
