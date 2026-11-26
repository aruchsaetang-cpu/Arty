"""Secondary motion on the CPU: verlet spring chains driven by the solved skeleton (no cloth sim, no Python drivers).

* cloak panels (bone-parented boxes on spine01): each hinges at its top edge by the angle of its own chain
* coat skirt: one hem chain from the pelvis; its lag (rig-local) keys the existing cm_trail / cm_sway Displace strengths
* hair: a chain from the crown; its offset (head frame) keys three Displace modifiers placed BEFORE the Armature
  modifier, weighted toward the hair tips, so the offset rides with the head (the hero's 3 lock curves stay rigid on
  the head bone: not simulated yet).
Hit-stop: the chains step with story time, so they freeze with the freeze-frame and follow through after it.
"""
import math
import bpy
from mathutils import Vector as V, Matrix, Quaternion as Q
import physics as PH

HAIR_MESHES = ("hair", "hair_locks", "hair_strands")


def _clip_phys(seq, s):
    c = next(c for c in seq["clip_data"] if c["_story0"] <= s < c["_story0"] + c["story_frames"]); return c["physics"]


def _hair_setup(ob, R):
    """displace X/Y/Z (rest space) before the armature, weight = how far the vertex hangs from the crown."""
    if "sec_hx" in ob.modifiers: return
    g = R.g; H = g.data.bones["head"].head_local; inv = g.matrix_world.inverted() @ ob.matrix_world
    vg = ob.vertex_groups.new(name="hair_spring")
    for v in ob.data.vertices:
        p = inv @ v.co; d = (p - H).length
        w = max(0.0, min(1.0, (d - 0.10) / 0.10)) ** 1.5 * (1.0 if p.z < H.z + 0.22 else 0.6)
        vg.add([v.index], w, "REPLACE")
    for k, ax in enumerate("XYZ"):
        m = ob.modifiers.new(f"sec_h{ax.lower()}", "DISPLACE"); m.direction = ax; m.space = "LOCAL"; m.mid_level = 0.0; m.strength = 0.0
        m.vertex_group = "hair_spring"
        ob.modifiers.move(ob.modifiers.find(m.name), k)


def setup_and_simulate(W, seq):
    tm = W.tm; out = {}
    for name, R in W.actors.items():
        g = R.g; ev = R.ev; kids = [o for o in g.children_recursive]
        cloak = [o for o in kids if o.type == "MESH" and o.parent_type == "BONE" and o.data.materials and o.data.materials[0]
                 and o.data.materials[0].name.startswith("cloak")]
        coat = [o for o in kids if o.type == "MESH" and "cm_trail" in o.modifiers]
        hair = [o for o in kids if o.type == "MESH" and o.name.split(".")[0] in HAIR_MESHES]
        locks = [o for o in kids if o.type == "CURVE" and o.parent_type == "BONE" and o.parent_bone == "head"]
        for o in hair: _hair_setup(o, R)
        p0 = _clip_phys(seq, 0)
        chains = []
        for o in cloak:                                   # top edge -> bottom edge, rest in the spine01 bone frame (tail-based)
            bb = [V(c) for c in o.bound_box]; ztop = max(c.z for c in bb); zbot = min(c.z for c in bb)
            loc_top = V((0, 0, ztop)); loc_mid = V((0, 0, (ztop + zbot) / 2)); loc_bot = V((0, 0, zbot))
            B = o.matrix_parent_inverse @ o.matrix_basis
            base_basis = o.matrix_basis.copy()
            rest = [B @ loc_top, B @ loc_mid, B @ loc_bot]
            q = p0["cloak"]; chains.append(("cloak", o, PH.VerletChain(rest, q["stiffness"], q["damping"], q["gravity"]), base_basis, (loc_top,)))
        if coat:
            sp = g.data.bones["spine05"]; H = sp.head_local
            rest = [V((0, 0, 0)), V((0, 0.03, -0.28)), V((0, 0.05, -0.55))]
            q = p0["coat"]; chains.append(("coat", coat, PH.VerletChain(rest, q["stiffness"], q["damping"], q["gravity"]), None, None))
        if hair or locks:
            hb = g.data.bones["head"]
            rest = [V((0, 0.10, 0)), V((0, 0.14, 0.04)), V((0, 0.17, 0.06))]          # head bone frame (+y along the bone = up)
            q = p0["hair"]; chains.append(("hair", hair + locks, PH.VerletChain(rest, q["stiffness"], q["damping"], q["gravity"]), None, None))
        stats = {}
        for f in tm.frames():
            s = tm.story(f); fkm = ev["fk"][s]; ph = _clip_phys(seq, s)
            dt = 0.0 if f == 1 else (s - tm.story(f - 1)) / W.fps
            loc, qrig, _ = ev["solved"][s]
            for kind, obj, chn, base, extra in chains:
                q = ph[kind]; chn.k, chn.d, chn.g = q["stiffness"], q["damping"], q["gravity"]
                if kind == "cloak":
                    Pm = fkm["spine01"] @ Matrix.Translation((0, R.blen["spine01"], 0))
                    pts = chn.step(Pm, dt); goal = chn.goal(Pm)
                    rd = (goal[-1] - goal[0]).normalized(); sd = (pts[-1] - pts[0]).normalized()
                    rot = rd.rotation_difference(sd); ang = math.degrees(rot.angle)
                    if ang > q["max_deg"]: rot = Q(rot.axis, math.radians(q["max_deg"]))
                    W0 = Pm @ obj.matrix_parent_inverse @ base; top = W0 @ extra[0]
                    desired = Matrix.Translation(top) @ rot.to_matrix().to_4x4() @ Matrix.Translation(-top) @ W0
                    obj.matrix_basis = (Pm @ obj.matrix_parent_inverse).inverted() @ desired
                    obj.keyframe_insert("location", frame=f); obj.keyframe_insert("scale", frame=f)
                    obj.keyframe_insert("rotation_quaternion" if obj.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)
                    stats["cloak_max_deg"] = max(stats.get("cloak_max_deg", 0.0), min(ang, q["max_deg"]))
                elif kind == "coat":
                    Pm = Matrix.Translation(fkm["spine05"].translation) @ qrig.to_matrix().to_4x4()
                    chn.step(Pm, dt); off = chn.offsets(Pm)[-1]
                    loc_off = qrig.to_matrix().inverted() @ off
                    mx = q["max_offset"]; ox = max(-mx, min(mx, loc_off.x)); oy = max(-mx, min(mx, loc_off.y))
                    for o in obj:
                        o.modifiers["cm_sway"].strength = ox; o.modifiers["cm_trail"].strength = oy
                        o.modifiers["cm_sway"].keyframe_insert("strength", frame=f); o.modifiers["cm_trail"].keyframe_insert("strength", frame=f)
                    stats["coat_max_cm"] = max(stats.get("coat_max_cm", 0.0), 100 * math.hypot(ox, oy))
                else:
                    Pm = fkm["head"]
                    chn.step(Pm, dt); off = chn.offsets(Pm)[-1]
                    Rh = R.xform(fkm, "head").to_3x3().normalized(); o_rest = Rh.inverted() @ off
                    mx = q["max_offset"]; o_rest = V([max(-mx, min(mx, c)) for c in o_rest])
                    for o in obj:
                        if o.type == "MESH":
                            for ax, val in zip("xyz", o_rest):
                                m = o.modifiers[f"sec_h{ax}"]; m.strength = val; m.keyframe_insert("strength", frame=f)
                    stats["hair_max_cm"] = max(stats.get("hair_max_cm", 0.0), 100 * o_rest.length)
        for kind, obj, chn, base, extra in chains:
            objs = obj if isinstance(obj, list) else [obj]
            for o in objs:
                ad = o.animation_data
                if ad and ad.action:
                    import solver
                    for fc in solver._fcurves(ad.action):
                        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
        out[name] = {k: round(v, 2) for k, v in stats.items()}
        out[name]["chains"] = [c[0] for c in chains]
    return out
