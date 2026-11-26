"""Steady cinematic camera from the clips' camera tracks: cuts, eased keys, level horizon (roll is always 0, the camera
is built with a world-up track), no handheld noise. Actor-tracking looks are smoothed (critically damped) so the frame
never jitters with the fighter's body. Per-cut motion blur flag, and the impact-frame hook (a subtle exposure lift on
the contact frame) are read by render_seq.py.
"""
import math
import bpy
from mathutils import Vector as V
import moves as MV


def _interp(keys, s):
    """keys sorted by frame: (frame, pos, look, lens, fstop, ease, look_actor, look_part, look_off) -> blended values."""
    if s <= keys[0]["frame"] or len(keys) == 1: return keys[0], keys[0], 0.0
    for a, b in zip(keys, keys[1:]):
        if a["frame"] <= s <= b["frame"]:
            return a, b, MV.ez((s - a["frame"]) / max(1e-6, b["frame"] - a["frame"]), b.get("ease", "io"))
    return keys[-1], keys[-1], 0.0


def build(scn, seq, W):
    tm = W.tm
    cd = bpy.data.cameras.new("combat_cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05; cd.clip_end = 400
    cam = bpy.data.objects.new("combat_cam", cd); scn.collection.objects.link(cam); scn.camera = cam; cam.rotation_mode = "QUATERNION"
    cd.dof.use_dof = True
    info = dict(cuts=[], motion_blur={}, max_pitch_deg=0.0, max_roll_deg=0.0, max_frame_jerk_cm=0.0)
    look_s = None; cut_prev = None; prev_pos = []
    for f in tm.frames():
        s = tm.story(f); clip = next(c for c in seq["clip_data"] if c["_story0"] <= s < c["_story0"] + c["story_frames"])
        ls = s - clip["_story0"]; cuts = clip["camera"]["cuts"]
        ci = max(i for i, cu in enumerate(cuts) if cu["frame"] <= ls); cu = cuts[ci]; cid = (clip["id"], ci)
        a, b, k = _interp(cu["keys"], ls)
        pos = V(a["pos"]).lerp(V(b["pos"]), k)
        def look_of(kk):
            if "look_mid" in kk:
                ps = [V(W.part(n, kk.get("look_part", "solar_plexus"), s / W.fps, final=True)) for n in kk["look_mid"]]
                return sum(ps, V()) / len(ps) + V(kk.get("look_off", (0, 0, 0)))
            if "look_actor" in kk:
                return V(W.part(kk["look_actor"], kk.get("look_part", "solar_plexus"), s / W.fps, final=True)) + V(kk.get("look_off", (0, 0, 0)))
            return V(kk["look"])
        look = look_of(a).lerp(look_of(b), k)
        if cid != cut_prev:
            look_s = look.copy(); info["cuts"].append(dict(clip=clip["id"], cut=ci, frame=f, motion_blur=bool(cu.get("motion_blur", False))))
            prev_pos = []
        else:
            look_s = look_s.lerp(look, 0.30)                    # critically damped follow: steady, no jitter
        cut_prev = cid
        lens = a.get("lens", 35) + (b.get("lens", 35) - a.get("lens", 35)) * k
        fst = a.get("fstop", 8) + (b.get("fstop", 8) - a.get("fstop", 8)) * k
        q = (look_s - pos).to_track_quat("-Z", "Y")
        cam.location = pos; cam.rotation_quaternion = q; cd.lens = lens; cd.dof.aperture_fstop = fst
        cd.dof.focus_distance = max(0.3, (look_s - pos).length)
        for path, obj in (("location", cam), ("rotation_quaternion", cam), ("lens", cd)):
            obj.keyframe_insert(path, frame=f)
        cd.dof.keyframe_insert("aperture_fstop", frame=f); cd.dof.keyframe_insert("focus_distance", frame=f)
        info["motion_blur"][f] = bool(cu.get("motion_blur", False))
        dv = (look_s - pos).normalized(); info["max_pitch_deg"] = max(info["max_pitch_deg"], abs(math.degrees(math.asin(max(-1, min(1, dv.z))))))
        right = q @ V((1, 0, 0)); info["max_roll_deg"] = max(info["max_roll_deg"], abs(math.degrees(math.asin(max(-1, min(1, right.z))))))
        prev_pos.append(pos.copy())
        if len(prev_pos) >= 3:                                  # second difference = jerk-free check (no shake)
            j = (prev_pos[-1] - 2 * prev_pos[-2] + prev_pos[-3]).length * 100; info["max_frame_jerk_cm"] = max(info["max_frame_jerk_cm"], j)
    for fc_owner in (cam, cd):
        ad = fc_owner.animation_data
        if ad and ad.action:
            import solver
            for fc in solver._fcurves(ad.action):
                for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"     # cuts stay clean (no motion-blur smear across a cut)
    info["max_pitch_deg"] = round(info["max_pitch_deg"], 2); info["max_roll_deg"] = round(info["max_roll_deg"], 4)
    info["max_frame_jerk_cm"] = round(info["max_frame_jerk_cm"], 3)
    return cam, info
