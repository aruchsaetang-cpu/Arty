"""Contact sync and hit reactions.

* Body parts / effectors are SURFACE points found on each actor's own meshes at rest (a ray from a bone anchor, the
  farthest skin/cloth vertex near the ray), then carried by the bone's rigid transform. So a fist contact means the
  knuckle surface touches the cheek surface, not bone centres.
* retarget(): measures attacker effector vs defender part at the hit frame with the solver's exact FK and shifts the
  attack's IK end-effector keys (fist or kicking ankle) by the error until it is < 0.5 mm (drives the hips if the
  limb cannot reach). The final number is re-measured in Blender after baking (checks.contact_report).
* make_reaction(): a KEYED reaction layer on the defender driven by the hit's force vector and the clip physics:
  angular impulse (lever x force) -> head snap / torso twist as damped springs; linear momentum -> knockback with
  friction, absorbed by the stance (< 6 cm), by one or two recovery steps, or a controlled fall (inverted pendulum
  integrated to the ground, then a damped settle). No ragdoll: every frame is an authored, bounded key.
* HOOKS: per-hit callbacks after baking; "bruise" puts a punch-mark decal on the struck surface at contact.
"""
import math
import bpy, bmesh
from mathutils import Vector as V, Matrix
import physics as PH
import moves as MV

HEAD_PARTS = ("cheek_L", "cheek_R", "jaw", "nose")
BODY_MESHES = ("skin", "top", "coat_upper", "trousers", "shoe_upper")


def _parts_def(B):
    h = B["head"].head_local; s2 = B["spine02"].head_local; s3 = B["spine03"].head_local
    def thigh(sd): return B[f"upperleg01.{sd}"].head_local.lerp(B[f"lowerleg01.{sd}"].head_local, 0.55)
    def calf(sd): return B[f"lowerleg01.{sd}"].head_local.lerp(B[f"foot.{sd}"].head_local, 0.35)
    def shin(sd): return B[f"lowerleg02.{sd}"].head_local.lerp(B[f"lowerleg02.{sd}"].tail_local, 0.30)
    wt = {sd: B[f"wrist.{sd}"].tail_local for sd in "LR"}; wd = {sd: (B[f"wrist.{sd}"].tail_local - B[f"wrist.{sd}"].head_local).normalized() for sd in "LR"}
    P = {"cheek_L": ("head", h + V((0.035, 0, 0.075)), (0.30, -1, 0)), "cheek_R": ("head", h + V((-0.035, 0, 0.075)), (-0.30, -1, 0)),
         "jaw": ("head", h + V((0, 0, 0.025)), (0, -1, -0.25)), "nose": ("head", h + V((0, 0, 0.085)), (0, -1, 0)),
         "solar_plexus": ("spine02", s2.copy(), (0, -1, 0)), "liver": ("spine03", s3 + V((-0.05, 0, 0)), (-0.6, -0.8, 0)),
         "ribs_L": ("spine02", s2 + V((0.05, 0, 0)), (0.8, -0.6, 0)),
         "thigh_L": ("upperleg02.L", thigh("L"), (1.0, -0.30, 0)), "thigh_R": ("upperleg02.R", thigh("R"), (-1.0, -0.30, 0)),
         "calf_L": ("lowerleg01.L", calf("L"), (0.8, 0.6, 0)), "calf_R": ("lowerleg01.R", calf("R"), (-0.8, 0.6, 0)),
         "fist_L": ("wrist.L", wt["L"], tuple(wd["L"])), "fist_R": ("wrist.R", wt["R"], tuple(wd["R"])),
         "shin_L": ("lowerleg02.L", shin("L"), (-0.55, -0.83, 0)), "shin_R": ("lowerleg02.R", shin("R"), (0.55, -0.83, 0)),
         "foot_L": ("foot.L", B["foot.L"].tail_local, (0, 0, 1)), "foot_R": ("foot.R", B["foot.R"].tail_local, (0, 0, 1))}
    return P


def calibrate(R, objs):
    """rest-space surface points for every body part / effector of rig R (armature space)."""
    g = R.g; inv = g.matrix_world.inverted(); pts = []
    for ob in objs:
        if ob.type != "MESH" or not ob.name.split(".")[0].startswith(BODY_MESHES): continue
        M = inv @ ob.matrix_world
        pts += [M @ v.co for v in ob.data.vertices]
    out = {}
    for name, (bone, anchor, d) in _parts_def(g.data.bones).items():
        d = V(d).normalized(); best = None; rr = 0.03 if not name.startswith("fist") else 0.025
        for p in pts:
            w = p - anchor; t = w.dot(d)
            if t <= 0 or t > 0.25: continue
            if (w - d * t).length < rr and (best is None or t > best): best = t
        surf = anchor + d * (best if best is not None else 0.04)
        out[name] = (bone, surf, d)
    R.parts = out
    return out


def point(R, fkm, name):
    bone, P, _ = R.parts[name]; return R.xform(fkm, bone) @ P


def point_blender(R, name):
    """the same point from Blender's evaluated pose (for verification)."""
    bone, P, _ = R.parts[name]; g = R.g; pb = g.pose.bones[bone]
    return g.matrix_world @ pb.matrix @ g.data.bones[bone].matrix_local.inverted() @ P


EFFECTOR_KEYS = dict(fist_R=("fistR", 1.0), fist_L=("fistL", 1.0), shin_R=("footR", 1.35), shin_L=("footL", 1.35), foot_R=("footR", 1.0), foot_L=("footL", 1.0))


def retarget(W, hit, iters=12, tol=0.0005):
    A = W.actors[hit["attacker"]]; D = W.actors[hit["target"]]; s = hit["_s"]; t = s / W.fps
    evD = D.evaluate(W.S, W.fps); tgt = point(D, evD["fk"][s], hit["part"]); hit["_target"] = tuple(tgt)
    chan, gain = EFFECTOR_KEYS[hit["effector"]]; log = []; prev = None
    for it in range(iters):
        evA = A.evaluate(W.S, W.fps); eff = point(A, evA["fk"][s], hit["effector"]); err = tgt - eff; log.append(round(err.length * 100, 3))
        if err.length < tol: break
        moved = 0
        drive = it >= 2 and err.length > 0.008 and prev is not None and err.length > 0.7 * prev
        for L, ch_, tc in W.eff_keys.get(hit["id"], []):
            for tk, d, _ in L.keys:
                if ch_ in d and tc - 1e-6 <= tk <= tc + 0.12:
                    v = d[ch_]
                    if ch_.startswith("fist") and v[0] == "w": d[ch_] = ("w", tuple(V(v[1]) + err * gain)); moved += 1
                    elif ch_.startswith("foot"): d[ch_] = (v[0] + err.x * gain, v[1] + err.y * gain, v[2], max(0.0, v[3] + err.z * gain)) + tuple(v[4:]); moved += 1
            if drive:                                  # limb at full reach: carry the hips into the strike (weight forward)
                k = next((d for tk, d, _ in L.keys if abs(tk - tc) < 1e-6 and "x" in d), None)
                if k is None:
                    st = A.blend_state(tc, skip_fists=True); L.key(tc, "io", x=st["x"], y=st["y"]); k = next(d for tk, d, _ in L.keys if abs(tk - tc) < 1e-6 and "x" in d)
                if hit.get("_drive_cm", 0.0) < 12.0:   # at most 12 cm of extra hip drive, then it is reported as out of reach
                    k["x"] += err.x * 0.85; k["y"] += err.y * 0.85; hit["_drive_cm"] = round(hit.get("_drive_cm", 0.0) + 100 * err.to_2d().length * 0.85, 2)
        prev = err.length
        if not moved: break
    hit["_retarget_log"] = log; hit["_err_solver_cm"] = log[-1]
    return log


def make_reaction(W, hit):
    """keyed, physics-driven reaction layer on the defender from the hit frame on."""
    A = W.actors[hit["attacker"]]; D = W.actors[hit["target"]]; s0 = hit["_s"]; fps = W.fps; T = s0 / fps
    ph = hit["_phys"]; evD = D.ev if getattr(D, "ev", None) else D.evaluate(W.S, fps); evA = A.ev
    st = evD["states"][s0]; fkD = evD["fk"][s0]
    tgt = V(hit["_target"])
    ah = V((evA["states"][s0]["x"], evA["states"][s0]["y"], 0)); fwd = (V((tgt.x, tgt.y, 0)) - ah).normalized(); left = V((-fwd.y, fwd.x, 0))
    F = (fwd * hit["force"][0] + left * hit["force"][1] + V((0, 0, 1)) * hit["force"][2]) * ph["reaction_strength"]
    Fh = V((F.x, F.y, 0)); u = Fh.normalized() if Fh.length > 1e-6 else fwd
    v0 = Fh.length / ph["mass"]; Dk = v0 / ph["friction"]
    yaw = st["yaw"]; dfw = V((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw)), 0)); dlt = V((-dfw.y, dfw.x, 0)); up = V((0, 0, 1))
    part = hit["part"]; is_head = part in HEAD_PARTS; is_leg = part.startswith(("thigh", "calf"))
    piv = D.joint(fkD, "neck02") if is_head else (D.joint(fkD, "upperleg01." + part[-1]) if is_leg else D.joint(fkD, "spine05"))
    tau = (tgt - piv).cross(F)
    c = 15.0 * ph.get("head_gain", 0.7)                  # deg per (N m s), soft-saturated at the neck range (tanh)
    def sat(x, lim): return lim * math.tanh(c * x / lim)
    th_hy = sat(tau.dot(up), 70) if is_head else 0.0
    th_hp = sat(tau.dot(dlt), 45) if is_head else 0.0
    th_hr = sat(-tau.dot(dfw), 35) if is_head else 0.0
    body_tau = (tgt - D.joint(fkD, "spine05")).cross(F).dot(up)
    th_tw = max(-40, min(40, body_tau * 1.2))
    fall = bool(hit.get("fall")) or Dk >= ph["fall_threshold"]
    nxt = W.next_move_start(D.name, T)
    need = 0.62 if (not fall and Dk >= 0.30) else (0.42 if Dk >= 0.06 else 0.35)    # the reaction always finishes its steps
    T_end = (W.S - 1) / fps if fall else max(T + need, min(T + 1.1, (nxt if nxt is not None else T + 1.1)))
    D.busy_until = T_end
    L = D.layer(f"react_{hit['id']}", T, T_end, blend_in=0.0, ease="lin", balance="report", kind="react")
    D.flags.append((T, T_end + 0.25, "react"))
    feet0 = {}
    for sd in "LR":
        a = st["_ank" + sd]; ft = st["foot" + sd]; feet0[sd] = (a.x - D.O.x, a.y - D.O.y, ft[2], 0.0, 0.0)
    x0, y0 = st["x"], st["y"]
    base = {k: st[k] for k in ("yaw", "drop", "twist", "lean", "side", "hp", "hy", "hr")}
    # feet plan
    plan = {sd: [] for sd in "LR"}
    rel = {sd: V(feet0[sd][:2]) - V((x0, y0)) for sd in "LR"}
    if not fall and Dk >= 0.06:
        first = max("LR", key=lambda sd: rel[sd].dot(u)); second = "R" if first == "L" else "L"
        nsteps = 1 if Dk < 0.30 else 2
        for k in range(nsteps):
            frac = (k + 1) / nsteps; o = k * 0.26
            plan[first].append((0.05 + o, 0.22 + o, frac)); plan[second].append((0.15 + o, 0.36 + o, frac))
    if is_leg:                                           # the kicked leg is swept a little inward and the knee gives
        plan[part[-1]] = [(0.0, 0.12, "sweep")] + plan[part[-1]]
    t_fall0 = (0.18 if is_leg else 0.10); th = math.radians(4.0); om = v0 / 0.95 * (0.6 if is_leg else 1.0); g = 9.81; fall_curve = []
    if fall:
        tt = 0.0; dt = 1 / 240.0; landed = None
        while tt < 3.0:
            if landed is None:
                om += (g / 0.95) * math.sin(th) * 1.25 * dt; th += om * dt
                if th >= math.radians(82): th = math.radians(82); landed = tt
            fall_curve.append((tt, th, landed)); tt += dt
    def fall_angle(dt):
        if not fall or dt < t_fall0: return 0.0, None
        k = min(len(fall_curve) - 1, int((dt - t_fall0) * 240)); tt, a, landed = fall_curve[k]
        if landed is not None:
            a = a - math.radians(7) * PH.spring_impulse(tt - landed, 1.0, 3.0, 0.35)
        return math.degrees(a), landed
    axis = up.cross(u).normalized()
    n = int(round((T_end - T) * fps))
    for k in range(n + 1):
        dt = k / fps; t = T + dt
        snap = PH.spring_impulse(dt, 1.0, ph["freq"] * 1.25, ph["damping"]); res = PH.spring_step(dt, 1.0, ph["freq"] * 0.45, 0.85)
        body = PH.spring_impulse(dt - 0.025, 1.0, ph["freq"] * 0.85, ph["damping"] + 0.1)
        kb = PH.knockback(dt, v0, ph["friction"])
        ch = dict(x=x0 + u.x * kb, y=y0 + u.y * kb, yaw=base["yaw"] + 0.35 * th_tw * res,
                  twist=base["twist"] + th_tw * (0.8 * body + 0.25 * res), hy=base["hy"] + th_hy * (0.8 * snap + 0.35 * res),
                  hp=base["hp"] + th_hp * (0.8 * snap + 0.3 * res), hr=base["hr"] + th_hr * (0.8 * snap + 0.3 * res),
                  lean=base["lean"] - 10 * (F.dot(dfw) / max(1e-6, F.length)) * body * min(1.0, F.length / 30.0),
                  side=base["side"] + 8 * (F.dot(dlt) / max(1e-6, F.length)) * body * min(1.0, F.length / 30.0), drop=base["drop"] + 0.03 * body)
        if part in ("solar_plexus", "liver"):
            fold = PH.spring_step(dt, 1.0, ph["freq"] * 0.7, 0.6)
            ch.update(lean=base["lean"] + 24 * fold, drop=base["drop"] + 0.07 * fold, hp=base["hp"] + 16 * fold, twist=base["twist"] + 6 * fold)
            ch["fistL"] = ("c", (0.12, -0.24, 1.15)); ch["fistR"] = ("c", (-0.08, -0.24, 1.12))
        elif is_head:
            ch["fistL"] = ("c", (0.28 + 0.10 * snap, -0.20, 1.35 + 0.1 * snap)); ch["fistR"] = ("c", (-0.30 - 0.12 * snap, -0.10, 1.30))
        if is_leg:
            buck = PH.spring_step(dt, 1.0, ph["freq"] * 0.9, 0.55); sgn = 1 if part.endswith("L") else -1
            ch.update(drop=base["drop"] + 0.12 * buck, side=base["side"] + 10 * sgn * buck, lean=base["lean"] + 8 * buck)
            ch["fistL"] = ("c", (0.20, -0.30, 1.36)); ch["fistR"] = ("c", (-0.18, -0.26, 1.30))
        a_deg, landed = fall_angle(dt)
        if a_deg > 0:
            ch["tilt"] = tuple(axis * a_deg); ch["drop"] = ch["drop"] + 0.22 * min(1.0, a_deg / 80.0)
            ch["hp"] = ch["hp"] - 18 * min(1.0, a_deg / 40.0) * (1.0 if landed is None else 0.5)
            ch["fistL"] = ("c", (0.42, -0.30, 1.55)); ch["fistR"] = ("c", (-0.42, -0.25, 1.50))
        else:
            ch["tilt"] = (0.0, 0.0, 0.0)
        for sd in "LR":
            f0 = feet0[sd]; p0 = V(f0[:2]); pos = p0.copy(); lift = 0.0
            for a_, b_, frac in plan[sd]:
                if frac == "sweep":
                    w = min(1.0, max(0.0, (dt - a_) / (b_ - a_))); sw = u.to_2d() * 0.11 * MV.ez(w, "out"); pos = p0 + sw
                    if a_ <= dt <= b_: lift = 0.03 * math.sin(math.pi * w)
                    p0 = p0 + u.to_2d() * 0.11 if dt > b_ else p0
                    continue
                tgt_p = V(f0[:2]) + u.to_2d() * (Dk * frac + 0.02)
                w = min(1.0, max(0.0, (dt - a_) / (b_ - a_)))
                if dt >= a_: pos = p0.lerp(tgt_p, MV.ez(w, "io"))
                if a_ < dt < b_: lift = max(lift, 0.05 * math.sin(math.pi * w))
                if dt >= b_: p0 = tgt_p
            ch["foot" + sd] = (pos.x, pos.y, f0[2], lift, 0.0)
        L.key(t, "lin", **ch)
    if fall: D.flags.append((T + t_fall0, 1e9, "fall"))
    last = L.keys[-1][1]
    D.ctx.update(x=last["x"], y=last["y"], yaw=last["yaw"], twist=last["twist"], lean=last["lean"], side=last["side"], drop=last["drop"],
                 hp=last["hp"], hy=last["hy"], footL=last["footL"], footR=last["footR"], fallen=fall)
    hit["_reaction"] = dict(impulse=round(F.length, 2), v0=round(v0, 3), knockback_m=round(Dk, 3), fall=fall, head_snap_deg=round(th_hy, 1),
                            head_pitch_deg=round(th_hp, 1), torso_twist_deg=round(th_tw, 1), steps=sum(len(v) for v in plan.values()), until=round(T_end, 3))
    return L


# ------------------------------------------------------------------ decal hook (punch mark appears at contact)
def _bruise_mat():
    m = bpy.data.materials.get("combat_bruise")
    if m: return m
    m = bpy.data.materials.new("combat_bruise"); m.use_nodes = True; nt = m.node_tree; N, Lk = nt.nodes, nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord"); vm = N.new("ShaderNodeVectorMath"); vm.operation = "LENGTH"
    Lk.new(tc.outputs["Object"], vm.inputs[0])
    rp = N.new("ShaderNodeMapRange"); rp.inputs[1].default_value = 0.3; rp.inputs[2].default_value = 1.0; rp.inputs[3].default_value = 0.8; rp.inputs[4].default_value = 0.0
    rp.clamp = True; Lk.new(vm.outputs["Value"], rp.inputs[0])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.28, 0.05, 0.10, 1); em.inputs["Strength"].default_value = 0.9
    tr = N.new("ShaderNodeBsdfTransparent"); ms = N.new("ShaderNodeMixShader")
    Lk.new(rp.outputs[0], ms.inputs[0]); Lk.new(tr.outputs[0], ms.inputs[1]); Lk.new(em.outputs[0], ms.inputs[2]); Lk.new(ms.outputs[0], out.inputs[0])
    return m


def bruise_hook(W, hit, f_contact):
    D = W.actors[hit["target"]]; g = D.g; bone, P, d = D.parts[hit["part"]]
    scn = bpy.context.scene; scn.frame_set(f_contact); bpy.context.view_layer.update()
    pw = point_blender(D, hit["part"]); pb = g.pose.bones[bone]
    Rw = (g.matrix_world @ pb.matrix @ g.data.bones[bone].matrix_local.inverted()).to_3x3().normalized()
    n = (Rw @ V(d)).normalized()
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0); me = bpy.data.meshes.new("bruise"); bm.to_mesh(me); bm.free()
    me.materials.append(_bruise_mat())
    ob = bpy.data.objects.new(f"bruise_{hit['id']}", me); scn.collection.objects.link(ob); ob.visible_shadow = False
    q = V((0, 0, 1)).rotation_difference(n)
    desired = Matrix.Translation(pw - n * 0.006) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((0.024, 0.018, 0.007, 1.0))
    ob.parent = g; ob.parent_type = "BONE"; ob.parent_bone = bone
    bpy.context.view_layer.update(); ob.matrix_world = desired; bpy.context.view_layer.update()
    s0 = ob.scale.copy()
    for f in range(1, W.tm.n_out + 1):
        vis = f >= f_contact; ob.hide_render = not vis; ob.hide_viewport = False
        k = min(1.0, max(0.0, (f - f_contact + 1) / 3.0)); sc = (0.55 + 0.45 * k) if vis else 0.3
        ob.scale = s0 * sc; ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("scale", frame=f)
    return ob


HOOKS = {"bruise": bruise_hook}
