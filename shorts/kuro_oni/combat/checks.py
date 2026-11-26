"""Verification measured in BLENDER (evaluated pose bones after baking), not in the solver:
  foot slide per planted foot segment (cm), contact error per hit (cm), balance (solver FK), kinetic-chain order of
  each strike, slip clearance of the enemy attacks, joint-limit clamps, proportion/face fingerprint, camera steadiness.
    rep = checks.run(W)          # dict, also written to combat/out/<seq>_checks.json
Thresholds (assert): planted-foot slide < 1 cm, contact error < 1 cm, enforced balance outside support < 2 cm,
camera roll = 0, hero head scale = 1 (no face change).
"""
import hashlib, json, math, os
import bpy
from mathutils import Vector as V
import contact as CT

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
FACE_PREFIX = ("eye_", "brows", "lash_", "skin")


def _eval_frames(W, frames):
    """{f: {actor: {"ball": {L,R}, "ank": {L,R}}}} from Blender's evaluated pose."""
    scn = bpy.context.scene; res = {}
    for f in frames:
        scn.frame_set(f); row = {}
        for n, R in W.actors.items():
            g = R.g; M = g.matrix_world; pb = g.pose.bones
            row[n] = dict(ball={sd: M @ pb[f"foot.{sd}"].tail for sd in "LR"}, ank={sd: M @ pb[f"foot.{sd}"].head for sd in "LR"})
        res[f] = row
    return res


def foot_report(W, ev_frames):
    tm = W.tm; out = {}
    for n, R in W.actors.items():
        segs = []
        for p in R.ev["plants"]:
            fa, fb = tm.out_of(p["a"]), tm.out_last(p["b"])
            if fb - fa < 1: continue
            b0 = ev_frames[fa][n]["ball"][p["side"]]; a0 = ev_frames[fa][n]["ank"][p["side"]]
            flat = all((R.ev["states"][s]["foot" + p["side"]][4] if len(R.ev["states"][s]["foot" + p["side"]]) > 4 else 0.0) < 3.0 for s in range(p["a"], p["b"] + 1))
            slide = 0.0; zs = []
            for f in range(fa, fb + 1):
                b = ev_frames[f][n]["ball"][p["side"]]; a = ev_frames[f][n]["ank"][p["side"]]
                d = (b - b0).to_2d().length
                if flat and p["kind"] == "plant": d = max(d, (a - a0).to_2d().length)
                slide = max(slide, d); zs.append(b.z)
            segs.append(dict(side=p["side"], frames=[fa, fb], kind=p["kind"], slide_cm=round(slide * 100, 3), ball_z_range_mm=round((max(zs) - min(zs)) * 1000, 2)))
        per = {}
        for sd in "LR":
            ss = [s for s in segs if s["side"] == sd]
            per[sd] = dict(segments=len(ss), max_slide_cm=round(max([s["slide_cm"] for s in ss] + [0.0]), 3),
                           planted_frames=sum(s["frames"][1] - s["frames"][0] + 1 for s in ss))
        steps = [dict(side=s["side"], frames=[tm.out_of(s["a"]), tm.out_last(s["b"])], kind=s["kind"]) for s in R.ev["steps"]]
        out[n] = dict(per_foot=per, segments=segs, steps=steps, independent=_independent_slide(W, n, ev_frames))
    return out


def _independent_slide(W, n, ev_frames):
    """walk_stop.foot_report-style detector with no solver knowledge: a foot is planted when its ball is within 8 mm of
    its lowest height on two consecutive frames (excluding fall frames); reports mm/frame slide while planted."""
    R = W.actors[n]; fr = sorted(ev_frames); res = {}
    for sd in "LR":
        z = [ev_frames[f][n]["ball"][sd].z for f in fr]; zmin = min(z); sl = []
        for i in range(1, len(fr)):
            t = W.tm.story(fr[i]) / W.fps
            if R.flag(t, "fall"): continue
            if z[i] < zmin + 0.008 and z[i - 1] < zmin + 0.008:
                sl.append((ev_frames[fr[i]][n]["ball"][sd] - ev_frames[fr[i - 1]][n]["ball"][sd]).to_2d().length * 1000)
        res[sd] = dict(planted_frames=len(sl), mean_mm_per_frame=round(sum(sl) / max(1, len(sl)), 3), max_mm_per_frame=round(max(sl + [0.0]), 3))
    return res


def contact_report(W):
    scn = bpy.context.scene; out = []
    for h in W.hits:
        f = W.tm.out_of(h["_s"]); scn.frame_set(f)
        A = W.actors[h["attacker"]]; D = W.actors[h["target"]]
        e = CT.point_blender(A, h["effector"]); t = CT.point_blender(D, h["part"]); err = (t - e).length * 100
        out.append(dict(id=h["id"], frame=f, attacker=h["attacker"], target=h["target"], part=h["part"], effector=h["effector"],
                        error_cm=round(err, 3), solver_error_cm=h["_err_solver_cm"], hip_drive_cm=h.get("_drive_cm", 0.0),
                        reaction=h.get("_reaction"), hitstop=h["hitstop"]))
    return out


def chain_report(W):
    """hip -> shoulder -> fist/foot: frames of peak angular / linear speed in the last 0.3 s before each contact."""
    out = []
    for h in W.hits:
        A = W.actors[h["attacker"]]; ev = A.ev; s1 = h["_s"]; s0 = max(1, s1 - 9)
        def peak(vals):
            sp = [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]; return s0 + sp.index(max(sp))
        hip = [ev["states"][s]["yaw"] for s in range(s0 - 1, s1 + 1)]
        sho = [ev["states"][s]["yaw"] + ev["states"][s]["twist"] for s in range(s0 - 1, s1 + 1)]
        eff = [CT.point(A, ev["fk"][s], h["effector"]) for s in range(s0 - 1, s1 + 1)]
        es = [(eff[i] - eff[i - 1]).length for i in range(1, len(eff))]; pe = s0 + es.index(max(es))
        ph, ps = peak(hip), peak(sho)
        out.append(dict(id=h["id"], hip_peak=ph - s1, shoulder_peak=ps - s1, effector_peak=pe - s1, order_ok=ph <= ps <= pe,
                        effector_speed_ms=round(max(es) * W.fps, 2)))
    return out


def clearance_report(W):
    out = []
    for a in W.attacks:
        A = W.actors[a["attacker"]]; T = W.actors[a["target"]]; best = (9.0, None)
        for s in range(int(a["t0"] * W.fps), min(W.S, int(a["t1"] * W.fps) + 1)):
            fist = A.joint(A.ev["fk"][s], ("wrist.R" if a["chan"] == "fistR" else "wrist.L") + "_tail")
            hc = T.joint(T.ev["fk"][s], "head").lerp(T.joint(T.ev["fk"][s], "head_tail"), 0.45)    # skull centre
            d = (fist - hc).length - 0.105 - 0.045                                                    # skull + fist radii: surface gap
            if d < best[0]: best = (d, s)
        out.append(dict(attacker=a["attacker"], target=a["target"], fist_to_head_surface_gap_cm=round(best[0] * 100, 1), story_frame=best[1]))
    return out


def _hash(vals):
    return hashlib.sha1(json.dumps(vals).encode()).hexdigest()[:16]


def fingerprint(W, frames=None):
    """proportions (rest bone lengths), posed bone lengths (no stretch), face (eye/brow/lash/skin rest geometry in head space,
    materials, shape keys), per actor style."""
    scn = bpy.context.scene; out = {}
    frames = frames or list(range(1, W.tm.n_out + 1, 5))
    for n, R in W.actors.items():
        g = R.g; inv = g.matrix_world.inverted()
        bl = {b.name: round(b.length, 6) for b in g.data.bones}
        Hm = g.data.bones["head"].matrix_local.inverted()
        face = {}
        for o in W.objs[n]:
            base = o.name.split(".")[0]
            if o.type != "MESH" or not base.startswith(FACE_PREFIX): continue
            M = Hm @ inv @ o.matrix_world
            co = [M @ v.co for v in o.data.vertices]
            if base == "skin": co = [p for p in co if p.length < 0.16][::3]          # the face region of the skin, every 3rd vertex
            sk = {k.name: round(k.value, 4) for k in o.data.shape_keys.key_blocks} if o.data.shape_keys else {}
            face[base] = dict(verts=len(o.data.vertices), coords=[round(c, 6) for p in co for c in p],
                              mats=[m.name.split(".")[0] for m in o.data.materials if m], shape_keys=sk)
        dev = 0.0; hs_max = 0.0
        for f in frames:
            scn.frame_set(f)
            for pb in g.pose.bones:
                if pb.name.startswith(("wrist", "finger", "metacarpal", "thumb")) or pb.name == "head" or pb.bone.parent and pb.bone.parent.name == "head": continue
                if pb.parent and pb.parent.name.startswith(("wrist", "finger", "metacarpal")): continue
                dev = max(dev, abs((pb.tail - pb.head).length - pb.bone.length))
            hs_max = max(hs_max, max(abs(c - 1.0) for c in g.pose.bones["head"].scale))
        out[n] = dict(style=W.seq["clip_data"][0]["actors"][n]["style"], bones=len(bl), bone_hash=_hash(sorted(bl.items())),
                      height_m=round(max(b.head_local.z for b in g.data.bones) * g.scale[0], 4), bone_lengths=bl, face=face,
                      max_posed_bone_stretch_mm=round(dev * 1000, 4), max_head_scale_dev=round(hs_max, 5))
    return out


def run(W, write=True, strict=True):
    frames = W.tm.frames()
    evf = _eval_frames(W, frames)
    rep = dict(seq=W.seq["id"], frames=W.tm.n_out, fps=W.fps, build_s=getattr(W, "build_s", None), rss_gb=getattr(W, "rss", None))
    rep["feet"] = foot_report(W, evf)
    rep["contacts"] = contact_report(W)
    rep["balance"] = {n: R.balance_report(R.ev) for n, R in W.actors.items()}
    rep["chain"] = chain_report(W)
    rep["clearance"] = clearance_report(W)
    rep["limits_clamped_frames"] = {n: dict(R.limit_hits) for n, R in W.actors.items()}
    rep["camera"] = {k: v for k, v in getattr(W, "cam_info", {}).items() if k != "motion_blur"}
    rep["secondary"] = getattr(W, "secondary", {})
    fp = fingerprint(W); rep["consistency"] = {n: {k: v for k, v in d.items() if k != "bone_lengths"} for n, d in fp.items()}
    fails = []
    for n, d in rep["feet"].items():
        for sd, p in d["per_foot"].items():
            if p["max_slide_cm"] >= 1.0: fails.append(f"{n} foot {sd} slides {p['max_slide_cm']} cm while planted")
    for c in rep["contacts"]:
        if c["error_cm"] >= 1.0: fails.append(f"hit {c['id']} contact error {c['error_cm']} cm")
    for n, b in rep["balance"].items():
        if b["max_outside_cm_enforced"] >= 2.0: fails.append(f"{n} centre of mass {b['max_outside_cm_enforced']} cm outside support (static frames)")
    if rep["camera"].get("max_roll_deg", 0) > 1e-3: fails.append("camera roll")
    for n, d in fp.items():
        if W.seq["clip_data"][0]["actors"][n].get("role") == "hero" and d["max_head_scale_dev"] > 1e-6: fails.append("hero face scaled")
        if d["max_posed_bone_stretch_mm"] > 0.5: fails.append(f"{n} bones stretch {d['max_posed_bone_stretch_mm']} mm")
    rep["fails"] = fails; rep["pass"] = not fails
    if write:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, f"{W.seq['id']}_checks.json"), "w") as fh: json.dump(rep, fh, indent=1, default=str)
        os.makedirs(os.path.join(OUT, "consistency"), exist_ok=True)
        with open(os.path.join(OUT, "consistency", f"{W.seq['id']}.json"), "w") as fh: json.dump(fp, fh, indent=1)
    return rep


def summary(rep):
    L = [f"CHECKS {rep['seq']}: {'PASS' if rep['pass'] else 'FAIL'}  ({rep['frames']} frames)"]
    for n, d in rep["feet"].items():
        L.append(f"  feet {n}: " + "  ".join(f"{sd} max {p['max_slide_cm']} cm over {p['segments']} plants/{p['planted_frames']} f" for sd, p in d["per_foot"].items())
                 + f"   (independent detector max {max(v['max_mm_per_frame'] for v in d['independent'].values())} mm/frame)")
    for c in rep["contacts"]:
        L.append(f"  hit {c['id']} {c['attacker']}->{c['target']}.{c['part']} ({c['effector']}) frame {c['frame']}: error {c['error_cm']} cm  reaction {c['reaction']}")
    for n, b in rep["balance"].items(): L.append(f"  balance {n}: {b}")
    for c in rep["chain"]: L.append(f"  chain {c}")
    for c in rep["clearance"]: L.append(f"  slip clearance {c}")
    L.append(f"  camera {rep['camera']}"); L.append(f"  secondary {rep['secondary']}"); L.append(f"  limits clamped {rep['limits_clamped_frames']}")
    for n, d in rep["consistency"].items(): L.append(f"  consistency {n}: {d['style']} bones {d['bones']} hash {d['bone_hash']} stretch {d['max_posed_bone_stretch_mm']} mm head-scale dev {d['max_head_scale_dev']} face {sorted(d['face'])}")
    for f in rep["fails"]: L.append("  FAIL " + f)
    return "\n".join(L)
