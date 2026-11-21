"""Walk -> natural stop -> head turn for the existing rigs (character_mh / character_v1), plus a small rainy-street
test scene with Aura Monster and a foot-contact report.

    /root/.venvs/bpy/bin/python lookdev/walk_stop.py after  [R0 R1]   # the upgraded stop
    /root/.venvs/bpy/bin/python lookdev/walk_stop.py before [R0 R1]   # the film's current stop (walk, then stand_at)
    env: RENDER=1 renders frames R0..R1 to lookdev/renders/walk_stop_<mode>/ ; SCALE (% of 1080x1920), SAMPLES

What the upgrade does, on top of character_mh.walk_keys (planted-foot IK walk, unchanged):
  * the walk cycle is driven by distance, not by time, so the walk can slow down without any foot sliding
    (cadence slows with speed; the planted foot stays exactly where it landed);
  * the stop is timed so the last step ends with one foot planted under the body while the other is passing;
    that free foot is then set down beside it (it only moves down, never sideways), so the stop has no slide;
  * the coat hem keeps swinging after the stop and settles (damped follow-through);
  * then the head turns with a small anticipation, an overshoot and a settle, while the face stays as built.
"""
import bpy, os, sys, json, math
from mathutils import Vector, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "shorts", "aura"))
args = [a for a in sys.argv[1:] if not a.startswith("-")]
MODE = args[0] if args and args[0] in ("before", "after") else "after"
os.environ.setdefault("FRAMES", "230"); os.environ.setdefault("PEOPLE", "0")
sys.argv = sys.argv[:1]                       # city.py reads its own CLI args at import
import city as C                              # resets the scene, defines the city builders
import character_mh as ch
import cast as K

LEG_BONES = ("upperleg01", "upperleg02", "lowerleg01", "lowerleg02", "foot", "toe1-1", "toe")
def _slerp_pose(lib, q):
    n = len(lib); j0 = int(math.floor(q)) % n; j1 = (j0 + 1) % n; t = q - math.floor(q)
    return {b: lib[j0][b].slerp(lib[j1][b], t) for b in lib[j0]}

def walk_to_stop(arm, start, heading_deg, f0, dist, prop="pockets", cycle=34, stride=0.62, dec_dist=1.1, settle=10):
    """Walk from `start` along heading (0 = toward -y) about `dist` metres, slowing down over the last dec_dist
    metres and stopping with both feet planted. Keys every frame. Returns the frames {stop, settled}."""
    lib, lift, step, speed = ch.walk_keys(arm, prop, cycle, stride); n = len(lib)
    cyc_dist = speed * n * step / 30.0                     # metres per full cycle (two steps)
    pstar = ch.DUTY / 2                                    # left foot mid-stance (under the hips), right foot passing
    total = (max(1, round(dist / cyc_dist - pstar)) + pstar) * cyc_dist
    d1 = total - dec_dist; t1 = d1 / speed; Tdec = 2 * dec_dist / speed   # constant speed, then linear slow-down
    h = math.radians(heading_deg); fwd = Vector((math.sin(h), -math.cos(h), 0))
    def dist_at(t):
        if t <= t1: return speed * t
        u = min(1.0, (t - t1) / Tdec); return d1 + speed * Tdec * (u - u * u / 2)
    f_stop = f0 + int(math.ceil((t1 + Tdec) * 30))
    for f in range(f0, f_stop + 1):
        d = dist_at((f - f0) / 30.0); q = (d / cyc_dist) * n
        pose = _slerp_pose(lib, q)
        for b, quat in pose.items():
            pb = arm.pose.bones[b]; pb.rotation_quaternion = quat; pb.keyframe_insert("rotation_quaternion", frame=f)
        lf = lift[int(math.floor(q)) % n] * (1 - (q % 1)) + lift[(int(math.floor(q)) + 1) % n] * (q % 1)
        arm.location = Vector(start) + fwd * d + Vector((0, 0, lf)); arm.keyframe_insert("location", frame=f)
        arm.rotation_euler = (0, 0, h); arm.keyframe_insert("rotation_euler", index=2, frame=f)
        ch.key_ground(arm, f, lf)
    # set the passing (right) foot down beside the planted one: blend its leg to its own mid-stance pose
    qs = (total / cyc_dist) * n; end = _slerp_pose(lib, qs); tgt = _slerp_pose(lib, qs + n / 2)
    for k in range(1, settle + 1):
        u = ch._smooth(k / settle); f = f_stop + k
        for b, quat in end.items():
            if b.endswith(".R") and b.split(".")[0] in LEG_BONES:
                quat = quat.slerp(tgt[b], u)
            pb = arm.pose.bones[b]; pb.rotation_quaternion = quat; pb.keyframe_insert("rotation_quaternion", frame=f)
        arm.keyframe_insert("location", frame=f); ch.key_ground(arm, f, lift[int(qs) % n])
    ch.set_interp(arm, "LINEAR", "location")
    ch.cloth_walk(arm, f0, f_stop, n * step, 0.0)
    coat_settle(arm, f_stop)
    return dict(stop=f_stop, settled=f_stop + settle, speed=speed, total=total)

def coat_settle(arm, f_stop, amp=0.05, decay=9.0, rate=0.42):
    """Follow-through: when the walker stops, the hem swings on and settles (added to cloth_walk's trail driver)."""
    for ob in arm.children_recursive:
        if "cm_trail" not in ob.modifiers: continue
        fc = None
        ad = ob.animation_data
        if ad:
            for d in ad.drivers:
                if d.data_path == 'modifiers["cm_trail"].strength': fc = d
        if fc is None: continue
        base = fc.driver.expression
        fc.driver.expression = (f"{base}+{amp}*clamp(frame-{f_stop},0,1)*exp(-(frame-{f_stop})/{decay})"
                                f"*sin((frame-{f_stop})*{rate})")

def head_turn(arm, f, yaw_deg, frames=16):
    """Head + neck turn with anticipation, overshoot and settle; the face itself is untouched."""
    scn = bpy.context.scene; scn.frame_set(f)
    base = {b: arm.pose.bones[b].rotation_quaternion.copy() for b in ("neck02", "head")}
    keys = ((0, 0.0), (4, -0.12), (frames, 1.08), (frames + 4, 0.97), (frames + 9, 1.0))
    for df, k in keys:
        for b, q in base.items():
            pb = arm.pose.bones[b]; pb.rotation_quaternion = q @ Quaternion((0, 1, 0), math.radians(yaw_deg * k) / 2)
            pb.keyframe_insert("rotation_quaternion", frame=f + df)
    return f + frames + 9

def film_stop(arm, start, heading_deg, f0, dist, prop="pockets", cycle=34, stride=0.62):
    """The film's current way (film.walk_path + stand_at): constant-speed walk, cut to a standing pose 6 frames later."""
    lib, lift, step, speed = ch.walk_keys(arm, prop, cycle, stride); n = len(lib)
    h = math.radians(heading_deg); fwd = Vector((math.sin(h), -math.cos(h), 0))
    f1 = f0 + int(dist / speed * 30); f = f0
    while f <= f1:
        j = ((f - f0) // step) % n
        for b, q in lib[j].items():
            pb = arm.pose.bones[b]; pb.rotation_quaternion = q; pb.keyframe_insert("rotation_quaternion", frame=f)
        arm.location = Vector(start) + fwd * (speed * (f - f0) / 30) + Vector((0, 0, lift[j])); arm.keyframe_insert("location", frame=f)
        arm.rotation_euler = (0, 0, h); arm.keyframe_insert("rotation_euler", index=2, frame=f); ch.key_ground(arm, f, lift[j])
        f += step
    stop_pos = arm.location.copy(); fs = f1 + 6
    bpy.context.scene.frame_set(fs); ch.posed(arm, prop)
    for b in ch.ANIM_BONES:
        if b in arm.pose.bones: arm.pose.bones[b].keyframe_insert("rotation_quaternion", frame=fs)
    arm.location = Vector((stop_pos.x, stop_pos.y, arm["ground_rest"])); arm.keyframe_insert("location", frame=fs)
    ch.set_interp(arm, "LINEAR", "location"); ch.cloth_walk(arm, f0, f1, n * step, 0.0)
    return dict(stop=f1, settled=fs, speed=speed, total=dist)

def foot_report(arm, f0, f1):
    """Per-frame world position of both ankles: sideways/forward slide while planted, and float above the ground."""
    scn = bpy.context.scene; rows = []
    for f in range(f0, f1 + 1):
        scn.frame_set(f); m = arm.matrix_world
        rows.append([f] + [c for s in ("L", "R") for c in (m @ arm.pose.bones[f"foot.{s}"].head)])
    out = {}
    for k, s in ((1, "L"), (4, "R")):
        z = [r[k + 2] for r in rows]; zmin = min(z)
        planted = [i for i in range(1, len(rows)) if z[i] < zmin + 0.012 and z[i - 1] < zmin + 0.012]
        slide = [math.hypot(rows[i][k] - rows[i - 1][k], rows[i][k + 1] - rows[i - 1][k + 1]) * 1000 for i in planted]
        out[s] = dict(planted_frames=len(planted), mean_slide_mm=round(sum(slide) / max(1, len(slide)), 2),
                      max_slide_mm=round(max(slide) if slide else 0, 2), ground_z=round(zmin, 4))
    return out, rows

def scene(mode):
    t0 = __import__("time").time()
    C.ground(); C.street_side(-1); C.street_side(1); C.poles_and_wires()
    for name, b in list(C._B.items()): b.done(C.CITY)
    C._B.clear()
    C.rain(0.6, 6.0, 9.0, 12.0, n=5000); C.world()
    if not os.environ.get("NOFOG"): C.fog()
    hero, objs = ch.build_v1(C.PEOPLE_C, (0.6, 11.0, 0), K.HERO_V1, pose_mode="walk", void_eyes=True)
    ch.hands_in_pockets(hero)
    f0 = 1
    info = (walk_to_stop if mode == "after" else film_stop)(hero, (0.6, 11.0, 0), 0, f0, 5.2)
    end = head_turn(hero, info["settled"] + 8, 18) if mode == "after" else info["settled"] + 8 + 25
    ch.hands_in_pockets(hero)
    # camera: slow pull-back in front of him that eases to a stop just after he does, then a slight push-in
    cam, tgt, cd = C.make_camera(); cd.lens = 42; cd.dof.focus_object = tgt; cd.dof.aperture_fstop = 2.4
    scn = bpy.context.scene; scn.frame_start, scn.frame_end = 1, end + 20
    stop_y = hero.location.y
    for f, y, z, ty in ((1, 3.6, 1.35, 9.0), (info["stop"] - 30, 2.0, 1.38, stop_y + 0.6), (info["stop"] + 6, 1.9, 1.40, stop_y),
                        (end + 20, 2.25, 1.42, stop_y)):
        cam.location = (0.15, y, z); cam.keyframe_insert("location", frame=f)
        tgt.location = (0.6, ty, 1.45); tgt.keyframe_insert("location", frame=f)
    # rim light behind him, cool key from the street side (the city keeps its own lights)
    C.area("rim", C.Matrix.Identity(4), (0.2, stop_y + 2.2, 2.6), (0.6, stop_y, 1.5), 1.2, 260, "#bcd6ff")
    C.area("key", C.Matrix.Identity(4), (-2.2, stop_y - 2.0, 2.4), (0.6, stop_y, 1.4), 1.6, 120, "#ffd9b0")
    print("SCENE", mode, json.dumps(info), "end", end, "build", round(__import__("time").time() - t0, 1), "s", flush=True)
    return hero, info, end

if __name__ == "__main__":
    hero, info, end = scene(MODE)
    rep, rows = foot_report(hero, 1, end + 20)
    os.makedirs(os.path.join(HERE, "renders"), exist_ok=True)
    json.dump(dict(mode=MODE, info=info, feet=rep, rows=rows), open(os.path.join(HERE, "renders", f"walk_stop_{MODE}.json"), "w"))
    print("FEET", MODE, json.dumps(rep), flush=True)
    if os.environ.get("RENDER"):
        r0 = int(args[1]) if len(args) > 1 else 1; r1 = int(args[2]) if len(args) > 2 else end + 20
        C.render_settings(int(os.environ.get("SCALE", 33)), int(os.environ.get("SAMPLES", 10)))
        scn = bpy.context.scene; out = os.path.join(HERE, "renders", f"walk_stop_{MODE}"); os.makedirs(out, exist_ok=True)
        import time
        for f in range(r0, r1 + 1):
            t = time.time(); scn.frame_set(f); scn.render.filepath = os.path.join(out, f"f{f:04d}.png")
            bpy.ops.render.render(write_still=True); print("FRAME", f, round(time.time() - t, 1), "s", flush=True)
    if os.environ.get("GLB"):
        bpy.ops.object.select_all(action="DESELECT")
        for o in [hero] + list(hero.children_recursive):
            if o.type in ("ARMATURE", "MESH"): o.select_set(True)
        bpy.context.view_layer.objects.active = hero
        p = os.environ["GLB"]
        bpy.ops.export_scene.gltf(filepath=p, export_format="GLB", use_selection=True, export_apply=True, export_animations=True,
                                  export_frame_range=True, export_force_sampling=True, export_yup=True, export_skins=True,
                                  export_morph=False, export_materials="EXPORT", export_image_format="JPEG")
        print("GLB", p, os.path.getsize(p), flush=True)
        # artifacts do not serve .glb: also write glTF JSON with the buffer embedded (car3d/aura_walk.html rebuilds a GLB from it)
        import struct, base64
        b = open(p, "rb").read(); n = struct.unpack("<I", b[12:16])[0]; J = json.loads(b[20:20 + n]); o = 20 + n
        BIN = b[o + 8:o + 8 + struct.unpack("<I", b[o:o + 4])[0]]
        J["buffers"] = [{"byteLength": len(BIN), "uri": "data:application/octet-stream;base64," + base64.b64encode(BIN).decode()}]
        json.dump(J, open(p.replace(".glb", ".gltf.json"), "w"), separators=(",", ":"))
