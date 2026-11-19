""""Aura Monster" v2: the man who dodges the rain, and the kid he trains. Staged in the city of Sol.

    /root/.venvs/bpy/bin/python shorts/aura/film.py [scale%] [first] [last]
Renders PNG frames to shorts/aura/frames/ (existing frames are skipped, so it can resume).
env: SAMPLES (default 16), NORENDER=1 to only build, STILLS="f1,f2,..." to render single frames.
Shot timing comes from beats.json (python3 shorts/aura/cues2.py). Cast in cast.py.

Sets: the main street (hook, theories, follow, payoff), the lantern alley off it at y~32 (pursuit, the reveal,
"teach me"), a second alley at y~48 and a rooftop south of the street (training)."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BEATS = json.load(open(os.path.join(HERE, "beats.json")))
N = BEATS["frames"]
os.environ["FRAMES"] = str(N)
os.environ.setdefault("PEOPLE", "24"); os.environ.setdefault("LIGHT_EXTRAS", "1"); os.environ.setdefault("SEED", "7")
sys.path.insert(0, os.path.join(ROOT, "lookdev")); sys.path.insert(0, HERE)
import bpy, bmesh
from mathutils import Vector, Matrix
import city as C                     # importing resets the scene and defines the city builders
import character_mh as ch
import cast as K

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 50
FIRST = int(sys.argv[2]) if len(sys.argv) > 2 else 1
LAST = int(sys.argv[3]) if len(sys.argv) > 3 else N
SAMPLES = int(os.environ.get("SAMPLES", 16))
scn = C.scn; prefs = C.prefs
B = {b["id"]: b for b in BEATS["shots"]}
def fr(shot, k=0): return B[shot]["f0" if k == 0 else "f1"]
SLOW0, SLOW1 = BEATS["slow0"], BEATS["slow1"]
V = Vector
# the montage is cut into three nights inside one shot
m0, m1 = fr("train_mont"), fr("train_mont", 1); mlen = (m1 - m0 + 1) // 3
MONT = [(m0, m0 + mlen - 1), (m0 + mlen, m0 + 2 * mlen - 1), (m0 + 2 * mlen, m1)]

# ------------------------------------------------------------------ places
AL_Y = 32.5                       # lantern alley (side -1, opening at y=30): centreline, runs toward -x
AL2_Y = 48.5                      # training alley (side +1, opening at y=46): runs toward +x
ROOF = V((0.0, -24.0, 18.0))      # a rooftop south of the street, looking north up the neon canyon
HERO_X = 0.6

def visible(rig, windows, extra=()):
    """hide_render keys: rig (and its children) render only inside the frame windows [(f0, f1), ...]."""
    obs = [rig] + list(rig.children_recursive) + list(extra)
    prefs.keyframe_new_interpolation_type = "CONSTANT"
    marks = {1: True}
    for a, b in windows:
        marks[max(1, a - 1)] = marks.get(max(1, a - 1), True); marks[a] = False; marks[b + 1] = True
    for o in obs:
        for f in sorted(marks):
            o.hide_render = marks[f]; o.keyframe_insert("hide_render", frame=f)

def walk_path(arm, pts, f0, f1, cycle=34, stride=0.62, phase=0.0, prop=None, sway=None):
    """Walk along a polyline at constant speed from f0 (keys to f1). sway(f) -> sideways offset (m)."""
    lib = ch.walk_library(arm, prop); keys = len(lib); step = cycle // keys
    speed = (2 * stride * arm.scale[0] / 0.83) / (cycle / 30.0)
    P = [V(p) for p in pts]; seg = [(P[i + 1] - P[i]).length for i in range(len(P) - 1)]
    def at(d):
        for i, L in enumerate(seg):
            if d <= L or i == len(seg) - 1:
                u = min(1.0, d / L); dirv = (P[i + 1] - P[i]).normalized()
                h = math.atan2(dirv.x, -dirv.y)
                if i > 0 and d < 0.9:          # ease the heading round the corner
                    pv = (P[i] - P[i - 1]).normalized(); h0 = math.atan2(pv.x, -pv.y)
                    dh = (h - h0 + math.pi) % (2 * math.pi) - math.pi; h = h0 + dh * (0.5 + 0.5 * d / 0.9)
                elif i < len(seg) - 1 and L - d < 0.9:
                    nv = (P[i + 2] - P[i + 1]).normalized(); h1 = math.atan2(nv.x, -nv.y)
                    dh = (h1 - h + math.pi) % (2 * math.pi) - math.pi; h = h + dh * 0.5 * (1 - (L - d) / 0.9)
                return P[i].lerp(P[i + 1], u), h, dirv
            d -= L
    off = int(round(phase * keys)); f = f0; total = sum(seg)
    while f <= f1 + step:
        j = ((f - f0) // step + off) % keys
        for b, q in lib[j].items():
            pb = arm.pose.bones[b]; pb.rotation_quaternion = q; pb.keyframe_insert("rotation_quaternion", frame=f)
        p, h, dirv = at(min(total, speed * (f - f0) / 30.0))
        bob = 0.022 * (1 - math.cos(4 * math.pi * j / keys)) / 2
        side = V((-dirv.y, dirv.x, 0)) * (sway(f) if sway else 0.0)
        arm.location = p + side + V((0, 0, arm["ground"] + bob)); arm.keyframe_insert("location", frame=f)
        arm.rotation_euler = (0, 0, h); arm.keyframe_insert("rotation_euler", index=2, frame=f)
        f += step
    ch.set_interp(arm, "LINEAR", "location"); ch.set_interp(arm, "LINEAR", "rotation_euler")
    return speed, (lambda f: at(min(total, speed * (f - f0) / 30.0)))

def stand_at(arm, f, pos, heading_deg, pose="stand"):
    """From frame f the rig stands at pos facing heading (0 = toward -y), held until the next key."""
    prefs.keyframe_new_interpolation_type = "CONSTANT"
    scn.frame_set(f); ch.posed(arm, pose)
    for b in ch.ANIM_BONES:
        arm.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f)
    arm.location = V(pos) + V((0, 0, arm["ground"])); arm.keyframe_insert("location", frame=f)
    arm.rotation_euler = (0, 0, math.radians(heading_deg)); arm.keyframe_insert("rotation_euler", index=2, frame=f)

# ------------------------------------------------------------------ cast (built before the city: cheap pose solves)
P = C.PEOPLE_C
# the hero on the main street: down the middle of the road, then left into the lantern alley
TURN_IN = fr("follow") + 30
hero_s, _ = ch.build(P, (HERO_X, 60, 0), ch.HERO, pose_mode="walk"); hero_s.name = "HERO_street"
spd = (2 * 0.62 * hero_s.scale[0] / 0.83) / (34 / 30.0)
y_start = AL_Y + spd * (TURN_IN + 40) / 30.0
_, hero_s_at = walk_path(hero_s, [(HERO_X, y_start, 0), (HERO_X, AL_Y, 0), (-30, AL_Y, 0)], -40, fr("follow", 1) + 2)
visible(hero_s, [(1, fr("follow", 1))])

# the hero in the alley: walking (weaving between the drops in slow motion), stops, turns round
TURN = fr("turn") + 10
def weave(f):   # side-steps between drops while the storm crawls
    if f < SLOW0 or f > SLOW1: return 0.0
    k = min(1.0, (f - SLOW0) / 12.0) * min(1.0, (SLOW1 - f) / 12.0)
    return k * (0.15 * math.sin(2 * math.pi * f / 17.0) + 0.06 * math.sin(2 * math.pi * f / 7.3))
hero_a, _ = ch.build(P, (-11, AL_Y, 0), ch.HERO, pose_mode="walk"); hero_a.name = "HERO_alley"
_, hero_a_at = walk_path(hero_a, [(-11.0, AL_Y, 0), (-40.0, AL_Y, 0)], fr("alley_pov"), TURN, sway=weave)
STOP = hero_a_at(TURN)[0].copy(); STOP.z = 0
stand_at(hero_a, TURN + 6, STOP, -90)                       # stands, still facing down the alley
prefs.keyframe_new_interpolation_type = "BEZIER"
hero_a.rotation_euler = (0, 0, math.radians(-90)); hero_a.keyframe_insert("rotation_euler", index=2, frame=TURN + 10)
hero_a.rotation_euler = (0, 0, math.radians(90)); hero_a.keyframe_insert("rotation_euler", index=2, frame=TURN + 26)
visible(hero_a, [(fr("alley_pov"), fr("teach", 1))])

# the narrator, before: skinny, black hoodie, umbrella (he can't dodge yet). One rig, moved between sets.
NARR_T = STOP + V((1.35, 0, 0))                                # facing the hero in the alley
narr_a, _ = ch.build(P, tuple(NARR_T), K.NARR_A, pose_mode="umbrella"); narr_a.name = "NARR_before"
umb_a = ch.add_umbrella(narr_a, P, "#1d2230")
# the hero teaching (rooftop / training alley): another rig of the same man, moved between the two sets
hero_t, _ = ch.build(P, tuple(ROOF), ch.HERO, pose_mode="stand"); hero_t.name = "HERO_train"
narr_m, _ = ch.build(P, (16, AL2_Y, 0), dict(K.NARR_A, body="m_fit", vtaper=True), pose_mode="umbrella"); narr_m.name = "NARR_mid"
umb_m = ch.add_umbrella(narr_m, P, "#1d2230")
narr_b, _ = ch.build(P, tuple(ROOF), K.NARR_B, pose_mode="umbrella"); narr_b.name = "NARR_after"
umb_b = ch.add_umbrella(narr_b, P, "#1d2230")
# the payoff: the two of them walking up the street together, nothing in their hands
hero_p, _ = ch.build(P, (0.0, 64, 0), ch.HERO, pose_mode="walk"); hero_p.name = "HERO_payoff"
narr_p, _ = ch.build(P, (1.25, 64, 0), K.NARR_B, pose_mode="walk"); narr_p.name = "NARR_payoff"
PAY0 = fr("payoff_two") - 20
_, hero_p_at = walk_path(hero_p, [(0.0, 62.5, 0), (0.0, 30.0, 0)], PAY0, N + 4, cycle=34)
walk_path(narr_p, [(1.25, 62.5, 0), (1.25, 30.0, 0)], PAY0, N + 4, cycle=34, stride=0.6, phase=0.25)
visible(hero_p, [(fr("payoff_two"), N)]); visible(narr_p, [(fr("payoff_two"), N)])

# where the training rigs stand in each shot
RT = ROOF + V((-1.0, 3.0, 0)); RN = ROOF + V((1.0, 1.6, 0))        # roof: hero, narrator
UT = V((19.0, AL2_Y, 0)); UN = V((16.4, AL2_Y + 0.3, 0))            # training alley: hero, narrator
CLOSE_P = V((HERO_X, 66.0, 0))                                      # "Then one night, I closed it." on the main street
def deg_to(a, b): d = b - a; return math.degrees(math.atan2(d.x, -d.y))
stand_at(narr_a, fr("teach"), NARR_T, deg_to(NARR_T, STOP), "umbrella")
stand_at(narr_a, fr("train_roof"), RN, deg_to(RN, RT), "umbrella")
stand_at(narr_a, fr("train_umb"), UN, deg_to(UN, UT), "umbrella")
stand_at(narr_a, MONT[0][0], RN, deg_to(RN, RT), "umbrella")
stand_at(hero_t, fr("train_roof"), RT, deg_to(RT, RN))
stand_at(hero_t, fr("train_umb"), UT, deg_to(UT, UN))
stand_at(hero_t, MONT[0][0], RT, deg_to(RT, RN))
stand_at(hero_t, MONT[1][0], UT, deg_to(UT, UN))
stand_at(hero_t, MONT[2][0], RT, deg_to(RT, RN))
stand_at(narr_m, 1, UN, deg_to(UN, UT), "umbrella")
stand_at(narr_b, 1, RN, deg_to(RN, RT), "umbrella")
stand_at(narr_b, fr("close"), CLOSE_P, 0, "umbrella")
visible(narr_a, [(fr("teach"), fr("train_umb", 1)), MONT[0]], umb_a)
visible(hero_t, [(fr("train_roof"), MONT[2][1])])
visible(narr_m, [MONT[1]], umb_m)
visible(narr_b, [MONT[2], (fr("close"), fr("close", 1))], umb_b)

# dodge attempts under the umbrella: quick side-steps and ducks (keyed on top of the held stands)
def attempts(arm, f0, f1, base, heading, amp=0.22, rate=11.0):
    prefs.keyframe_new_interpolation_type = "BEZIER"
    h = math.radians(heading); side = V((math.cos(h), math.sin(h), 0))
    for f in range(f0 + 2, f1, 3):
        s_ = math.sin(2 * math.pi * (f - f0) / rate)
        arm.location = base + side * amp * s_ + V((0, 0, arm["ground"] - 0.05 * abs(s_)))
        arm.keyframe_insert("location", frame=f)
attempts(narr_a, fr("train_roof") + 6, fr("train_roof", 1), RN, deg_to(RN, RT))
attempts(narr_a, fr("train_umb") + 4, fr("train_umb", 1), UN, deg_to(UN, UT), amp=0.16, rate=9.0)
attempts(narr_a, MONT[0][0] + 2, MONT[0][1], RN, deg_to(RN, RT), amp=0.28, rate=8.0)
attempts(narr_m, MONT[1][0] + 2, MONT[1][1], UN, deg_to(UN, UT), amp=0.3, rate=7.0)
attempts(narr_b, MONT[2][0] + 2, MONT[2][1], RN, deg_to(RN, RT), amp=0.34, rate=6.0)
stand_at(narr_b, fr("close"), CLOSE_P, 0, "umbrella")       # (re-key the close-shot stand after the attempts)

# "Then one night, I closed it.": the canopy folds shut and drops away
can = next(o for o in umb_b if o.name.startswith("umbrella"))
bpy.context.view_layer.update()
tip_w = max((can.matrix_world @ v.co for v in can.data.vertices), key=lambda p: p.z)
tip_l = can.matrix_world.inverted() @ tip_w
can.data.transform(Matrix.Translation(-tip_l)); can.matrix_basis = can.matrix_basis @ Matrix.Translation(tip_l)
prefs.keyframe_new_interpolation_type = "BEZIER"
FOLD = fr("close") + int(0.45 * (fr("close", 1) - fr("close")))
for f, sxy, sz in ((FOLD - 1, 1.0, 1.0), (FOLD + 10, 0.09, 1.25)):
    can.scale = (sxy, sxy, sz)                     # local axes = world axes of the bind pose: canopy axis is +z
    can.keyframe_insert("scale", frame=f)

# the three theories: a shopkeeper, a police officer, two kids (and the women of Sol around them)
shop, _ = ch.build(P, (6.9, 53.0, 0.15), K.SHOP, pose_mode="stand", heading=-90)
cop, _ = ch.build(P, (-5.5, 49.0, 0.15), K.COP, pose_mode="umbrella", heading=90)
ch.add_umbrella(cop, P, "#121214"); ch.add_cap(cop, P, "#18213a", "#d8b24a")
kid1, _ = ch.build(P, (5.35, 45.1, 0.15), K.KID1, pose_mode="stand", heading=-90)
kid2, _ = ch.build(P, (5.9, 44.3, 0.15), K.KID2, pose_mode="phone", heading=-90)
ch.add_phone(kid2, P)
for k_ in (kid1, kid2):                       # children: larger head for their height
    k_.pose.bones["head"].scale = (1.16, 1.16, 1.16)
mom, _ = ch.build(P, (6.25, 45.75, 0.15), dict(K.W1, head_yaw=-20), pose_mode="umbrella", heading=-120)   # waiting with the kids
ch.add_umbrella(mom, P, "#6b1d24")
for st_, (cx, cy), hd, pm in ((K.W2, (9.4, 54.2), 180, "phone"), (K.MAN_LONG, (8.5, 55.5), 120, "stand"),
                              (K.MAN_DIAMOND, (10.2, 56.4), -120, "stand")):    # shop customers behind the glass
    c_, _ = ch.build(P, (cx, cy, 0.15), st_, pose_mode=pm, heading=hd)
    if pm == "phone":
        ch.add_phone(c_, P)
w_al, _ = ch.build(P, (-15.5, AL_Y + 1.9, 0.0), dict(K.W4, head_yaw=35), pose_mode="phone", heading=180)   # under an alley awning
ch.add_phone(w_al, P)
w_st, _ = ch.build(P, (-2.6, 70, 0), K.W3, pose_mode="walk"); w_st.name = "W3_walker"      # walks past the hero
walk_path(w_st, [(-2.6, 70, 0), (-2.6, 20, 0)], -40, N, cycle=30, stride=0.55, prop="umbrella")
scn.frame_set(1); ch.add_umbrella(w_st, P, "#24405e", clear=True)

# ------------------------------------------------------------------ the city + the extra sets
C.build_scene(with_hero=False, avoid=[(6.9, 53), (-5.5, 49), (5.6, 44.8), (HERO_X, 40), (-2.6, 60)],
              rain_box=(0.0, 45.0, 18.0, 62.0, 9.0, 24, 17000))
rain_main = bpy.data.objects["rain"]

exec(open(os.path.join(HERE, "film_sets.py")).read())        # shop interior, rooftop set, alley dressing, extra rain

# ------------------------------------------------------------------ rain: one clock for every rain object
# normal speed, a crawl in the slow-motion reveal ("Then I saw it" -> "too fast for the storm to touch him")
H, T = 9.0, 24
phase = 0.0; ph = {}
for f in range(1, N + 1):
    phase += 0.07 if SLOW0 + 6 <= f <= SLOW1 else (0.4 if SLOW0 <= f < SLOW0 + 6 else 1.0)
    ph[f] = phase
prefs.keyframe_new_interpolation_type = "CONSTANT"
for r in RAINS:
    r.animation_data_clear()
    z0 = r.location.z
    for f in range(1, N + 1):
        r.location.z = z0 - H * ((ph[f] % T) / T); r.keyframe_insert("location", index=2, frame=f)
    ch.set_interp(r, "CONSTANT")

def carve(robj, test):
    """Delete the drops for which test(world_xy, z) is true: nobody dry ever has a drop pass through them."""
    bm = bmesh.new(); bm.from_mesh(robj.data); mw = robj.matrix_world.copy(); mw.translation.z = 0
    kill = [fc for fc in bm.faces if test(mw @ fc.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context="FACES"); bm.to_mesh(robj.data); bm.free()
UMBS = [NARR_T, RN, UN, CLOSE_P, V((-5.5, 49.0, 0)), V((6.25, 45.75, 0))]
def dry_main(p):
    if abs(p.x - HERO_X) < 0.75 and AL_Y - 0.6 < p.y < y_start + 2: return True          # hero down the street
    if -1.3 < p.x < 2.4 and 28 < p.y < 66: return True                                   # the payoff pair
    if p.x < HERO_X and abs(p.y - AL_Y) < 0.75: return True                              # the turn into the alley
    return any((p.xy - u.xy).length < 0.6 for u in UMBS)
carve(rain_main, dry_main)
carve(rain_alley, lambda p: (abs(p.y - AL_Y) < 0.5 and p.x > STOP.x - 1.0) or (p.xy - NARR_T.xy).length < 0.62
      or (p.xy - STOP.xy).length < 0.6)
carve(rain_alley2, lambda p: (p.xy - UT.xy).length < 0.6 or (p.xy - UN.xy).length < 0.75)
carve(rain_roof, lambda p: (p.xy - RT.xy).length < 0.6 or (p.xy - RN.xy).length < 0.8)

# ------------------------------------------------------------------ aura: the hero always; the kid once he closes it
def aura(owner, f_on, f_full, f_off=None, watts=70):
    ld = bpy.data.lights.new("aura", "POINT"); ld.color = (0.55, 0.92, 1.0); ld.shadow_soft_size = 0.6
    ob = bpy.data.objects.new("aura", ld); C.FX.objects.link(ob); ob.parent = owner; ob.location = (0, 0, 1.15 / owner.scale[0])
    prefs.keyframe_new_interpolation_type = "BEZIER"
    for f, e in ((1, 0), (f_on, 0), (f_full, watts)) + (((f_off - 1, watts), (f_off, 0)) if f_off else ()):
        ld.energy = e; ld.keyframe_insert("energy", frame=f)
    return ob
aura(hero_a, SLOW0 - 4, SLOW0 + 20, None, 60)
aura(narr_b, FOLD + 4, FOLD + 26, None, 40)
aura(narr_p, 1, 2, None, 40); aura(hero_p, 1, 2, None, 50)
# white aura composited from a per-frame mask (compose.py): heroes always, the narrator only after he can dodge
for rig in (hero_s, hero_a, hero_t, hero_p, narr_p, narr_b):
    for o in [rig] + list(rig.children_recursive):
        o.pass_index = 7
for o in umb_b:
    o.pass_index = 0
json.dump({"keys": [[1, 0.6], [SLOW0, 0.6], [SLOW0 + 16, 1.25], [SLOW1, 1.2], [SLOW1 + 8, 0.7],
                    [MONT[2][0], 0.0], [FOLD, 0.0], [FOLD + 18, 1.15], [N, 1.1]],
           "trail": [SLOW0, SLOW1]}, open(os.path.join(HERE, "aura.json"), "w"))

# ------------------------------------------------------------------ camera
exec(open(os.path.join(HERE, "film_camera.py")).read())

# ------------------------------------------------------------------ render
C.render_settings(SCALE, SAMPLES)
scn.frame_start, scn.frame_end = FIRST, LAST
scn.frame_step = int(os.environ.get("STEP", 1))       # STEP=2 renders on twos (held frames at encode)
out_dir = os.path.join(HERE, "frames"); os.makedirs(out_dir, exist_ok=True)
scn.render.image_settings.file_format = "PNG"
scn.render.compositor_device = "CPU"
scn.view_layers[0].use_pass_object_index = True
ng = bpy.data.node_groups.new("comp", "CompositorNodeTree"); scn.compositing_node_group = ng
rl = ng.nodes.new("CompositorNodeRLayers"); idm = ng.nodes.new("CompositorNodeIDMask"); idm.inputs["Index"].default_value = 7
go = ng.nodes.new("NodeGroupOutput"); ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
ng.links.new(rl.outputs["Image"], go.inputs[0]); ng.links.new(rl.outputs["Object Index"], idm.inputs["ID value"])
fo = ng.nodes.new("CompositorNodeOutputFile"); fo.directory = os.path.join(HERE, "masks"); fo.file_name = "mask_"
fo.format.media_type = "IMAGE"; fo.format.file_format = "PNG"; fo.format.color_mode = "BW"
fo.file_output_items.new("FLOAT", ""); ng.links.new(idm.outputs["Alpha"], fo.inputs[0])
if os.environ.get("NORENDER"):
    print("built only"); sys.exit(0)
if os.environ.get("STILLS"):
    os.makedirs(os.path.join(HERE, "stills"), exist_ok=True)
    for f in [int(x) for x in os.environ["STILLS"].split(",")]:
        scn.frame_set(f); scn.render.filepath = os.path.join(HERE, "stills", f"s{f:04d}.png")
        bpy.ops.render.render(write_still=True); print("WROTE still", f)
else:
    scn.render.filepath = os.path.join(out_dir, "f")
    scn.render.use_overwrite = False; scn.render.use_placeholder = True    # resumable; parallel-safe
    bpy.ops.render.render(animation=True)
    print("WROTE frames", FIRST, LAST)
