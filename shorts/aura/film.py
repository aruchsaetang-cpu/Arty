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

WALKS = []      # every walk_path: heel-strike timing for the footstep sounds (steps.json)
def walk_path(arm, pts, f0, f1, cycle=34, stride=0.62, phase=0.0, prop=None, sway=None):
    """Walk along a polyline at constant speed from f0 (keys to f1). sway(f) -> sideways offset (m)."""
    lib, lift, step, speed = ch.walk_keys(arm, prop, cycle, stride); keys = len(lib)   # planted-foot IK walk
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
        side = V((-dirv.y, dirv.x, 0)) * (sway(f) if sway else 0.0)
        arm.location = p + side + V((0, 0, lift[j])); arm.keyframe_insert("location", frame=f); ch.key_ground(arm, f, lift[j])
        arm.rotation_euler = (0, 0, h); arm.keyframe_insert("rotation_euler", index=2, frame=f)
        f += step
    ch.set_interp(arm, "LINEAR", "location"); ch.set_interp(arm, "LINEAR", "rotation_euler")
    total_f = f0 + int(total / speed * 30.0)
    WALKS.append(dict(rig=arm, f0=f0, f1=min(f1, total_f), step=step, n=keys, off=off))
    ch.cloth_walk(arm, f0, min(f1, total_f), keys * step, phase)           # coat hem trails and swings with the walk
    return speed, (lambda f: at(min(total, speed * (f - f0) / 30.0)))

HOLD = {}       # rig name -> frames whose keys must hold (CONSTANT): rigs jump between sets at cuts
def stand_at(arm, f, pos, heading_deg, pose="stand"):
    """From frame f the rig stands at pos facing heading (0 = toward -y), held until the next key."""
    HOLD.setdefault(arm.name, set()).add(f)
    scn.frame_set(f); ch.posed(arm, pose)
    for b in ch.ANIM_BONES:
        arm.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f)
    arm.location = V(pos) + V((0, 0, arm["ground_rest"])); arm.keyframe_insert("location", frame=f)
    ch.key_ground(arm, f, arm["ground_rest"])
    arm.rotation_euler = (0, 0, math.radians(heading_deg)); arm.keyframe_insert("rotation_euler", index=2, frame=f)

# ------------------------------------------------------------------ cast (built before the city: cheap pose solves)
P = C.PEOPLE_C
# the hero on the main street: down the middle of the road, then left into the lantern alley
TURN_IN = fr("follow") + 30
hero_s, _ = ch.build_v1(P, (HERO_X, 60, 0), K.HERO_V1, pose_mode="walk", void_eyes=True); hero_s.name = "HERO_street"
spd = (2 * 0.62 * hero_s.scale[0] / 0.83) / (34 / 30.0)
y_start = AL_Y + spd * (TURN_IN + 40) / 30.0
_, hero_s_at = walk_path(hero_s, [(HERO_X, y_start, 0), (HERO_X, AL_Y, 0), (-30, AL_Y, 0)], -40, fr("follow", 1) + 2,
                        prop="pockets")
visible(hero_s, [(1, fr("follow", 1))])

# the hero in the alley: walking (weaving between the drops in slow motion), stops, turns round
TURN = fr("turn") + 10
def weave(f):   # side-steps between drops while the storm crawls
    if f < SLOW0 or f > SLOW1: return 0.0
    k = min(1.0, (f - SLOW0) / 12.0) * min(1.0, (SLOW1 - f) / 12.0)
    return k * (0.15 * math.sin(2 * math.pi * f / 17.0) + 0.06 * math.sin(2 * math.pi * f / 7.3))
hero_a, _ = ch.build_v1(P, (-11, AL_Y, 0), K.HERO_V1, pose_mode="walk", void_eyes=True); hero_a.name = "HERO_alley"
_, hero_a_at = walk_path(hero_a, [(-11.0, AL_Y, 0), (-40.0, AL_Y, 0)], fr("alley_pov"), TURN, sway=weave, prop="pockets")
STOP = hero_a_at(TURN)[0].copy(); STOP.z = 0
stand_at(hero_a, TURN + 6, STOP, -90, "pockets")                       # stands, still facing down the alley
prefs.keyframe_new_interpolation_type = "BEZIER"
hero_a.rotation_euler = (0, 0, math.radians(-90)); hero_a.keyframe_insert("rotation_euler", index=2, frame=TURN + 10)
hero_a.rotation_euler = (0, 0, math.radians(90)); hero_a.keyframe_insert("rotation_euler", index=2, frame=TURN + 26)
visible(hero_a, [(fr("alley_pov"), fr("teach", 1))])

# the narrator, before: skinny, black hoodie, umbrella (he can't dodge yet). One rig, moved between sets.
NARR_T = STOP + V((1.35, 0, 0))                                # facing the hero in the alley
narr_a, _ = ch.build(P, tuple(NARR_T), K.NARR_A, pose_mode="umbrella"); narr_a.name = "NARR_before"
umb_a = ch.add_umbrella(narr_a, P, "#1d2230")
# the hero teaching (rooftop / training alley): another rig of the same man, moved between the two sets
hero_t, _ = ch.build_v1(P, tuple(ROOF), K.HERO_V1, pose_mode="pockets", void_eyes=True); hero_t.name = "HERO_train"
narr_m, _ = ch.build(P, (16, AL2_Y, 0), dict(K.NARR_A, body="m_lean"), pose_mode="umbrella"); narr_m.name = "NARR_mid"
umb_m = ch.add_umbrella(narr_m, P, "#1d2230")
narr_b, _ = ch.build(P, tuple(ROOF), K.NARR_B, pose_mode="umbrella"); narr_b.name = "NARR_after"
umb_b = ch.add_umbrella(narr_b, P, "#1d2230")
# the payoff: the two of them walking up the street together, nothing in their hands
hero_p, _ = ch.build_v1(P, (0.0, 64, 0), K.HERO_V1, pose_mode="walk", void_eyes=True); hero_p.name = "HERO_payoff"
narr_p, _ = ch.build(P, (1.25, 64, 0), dict(K.NARR_B, void_eyes=True), pose_mode="walk"); narr_p.name = "NARR_payoff"
PAY0 = fr("payoff_two") - 20
_, hero_p_at = walk_path(hero_p, [(0.0, 62.5, 0), (0.0, 30.0, 0)], PAY0, N + 4, cycle=34, prop="pockets")
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
# the reveal: he followed the hero into the alley and stopped dead ("Then I saw it"), so he stands behind him under
# his umbrella, where the first-person camera stood (film_camera.pov_alley), held still (constant keys) until "teach"
POV_P = V((hero_a_at(fr("alley_pov") + 16)[0].x + 3.6, AL_Y + 0.25, 0))
prefs.keyframe_new_interpolation_type = "CONSTANT"
stand_at(narr_a, fr("reveal_low"), POV_P, deg_to(POV_P, POV_P - V((1, 0, 0))), "umbrella")
prefs.keyframe_new_interpolation_type = "BEZIER"
stand_at(hero_t, fr("train_roof"), RT, deg_to(RT, RN), "pockets")
stand_at(hero_t, fr("train_umb"), UT, deg_to(UT, UN), "pockets")
stand_at(hero_t, MONT[0][0], RT, deg_to(RT, RN), "pockets")
stand_at(hero_t, MONT[1][0], UT, deg_to(UT, UN), "pockets")
stand_at(hero_t, MONT[2][0], RT, deg_to(RT, RN), "pockets")
for h_ in (hero_s, hero_a, hero_t, hero_p):        # his hands live in his trouser pockets
    ch.hands_in_pockets(h_)
stand_at(narr_m, 1, UN, deg_to(UN, UT), "umbrella")
stand_at(narr_b, 1, RN, deg_to(RN, RT), "umbrella")
stand_at(narr_b, fr("close"), CLOSE_P, 0, "umbrella")
visible(narr_a, [(fr("reveal_low"), fr("reveal_close", 1)), (fr("teach"), fr("train_umb", 1)), MONT[0]], umb_a)
visible(hero_t, [(fr("train_roof"), MONT[2][1])])
visible(narr_m, [MONT[1]], umb_m)
visible(narr_b, [MONT[2], (fr("close"), fr("close", 1))], umb_b)
def eyes_turn(rig, f, f_end):
    """From frame f the rig has the hero's eyes (black sclera, white irises): void-eyed copies swap in."""
    for o in [c for c in rig.children_recursive if c.name.startswith("eye_")]:
        v = o.copy(); v.data = o.data.copy(); v.animation_data_clear(); v.name = o.name + "_void"
        for c_ in o.users_collection: c_.objects.link(v)
        v.data.materials[0] = ch.void_eye_mat(sum(p_.co.length for p_ in o.data.vertices) / len(o.data.vertices))
        prefs.keyframe_new_interpolation_type = "CONSTANT"
        o.hide_render = True; o.keyframe_insert("hide_render", frame=f)
        visible(v, [(f, f_end)])

# dodge attempts under the umbrella: quick side-steps and ducks (keyed on top of the held stands)
def attempts(arm, f0, f1, base, heading, amp=0.22, rate=11.0):
    h = math.radians(heading); side = V((math.cos(h), math.sin(h), 0))
    for f in range(f0 + 2, f1, 3):
        s_ = math.sin(2 * math.pi * (f - f0) / rate)
        arm.location = base + side * amp * s_ + V((0, 0, arm["ground_rest"]))     # side-steps, feet stay on the ground
        arm.keyframe_insert("location", frame=f)
    arm.location = base + V((0, 0, arm["ground_rest"])); arm.keyframe_insert("location", frame=f1)   # settle, then hold
    HOLD.setdefault(arm.name, set()).add(f1)

def hold_jumps(arm):
    """Keys at HOLD frames are CONSTANT (a cut to another set never slides across the city); the rest ease."""
    from bpy_extras import anim_utils
    ad = arm.animation_data
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    hold = HOLD.get(arm.name, set())
    for fc in cb.fcurves:
        if fc.data_path.startswith(("location", "rotation_euler", "pose.bones")):
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT" if round(k.co.x) in hold else "BEZIER"
attempts(narr_a, fr("train_roof") + 6, fr("train_roof", 1), RN, deg_to(RN, RT))
attempts(narr_a, fr("train_umb") + 4, fr("train_umb", 1), UN, deg_to(UN, UT), amp=0.16, rate=9.0)
attempts(narr_a, MONT[0][0] + 2, MONT[0][1], RN, deg_to(RN, RT), amp=0.28, rate=8.0)
attempts(narr_m, MONT[1][0] + 2, MONT[1][1], UN, deg_to(UN, UT), amp=0.3, rate=7.0)
attempts(narr_b, MONT[2][0] + 2, MONT[2][1], RN, deg_to(RN, RT), amp=0.34, rate=6.0)
stand_at(narr_b, fr("close"), CLOSE_P, 0, "umbrella")       # (re-key the close-shot stand after the attempts)
for r_ in (narr_a, narr_m, narr_b, hero_t):
    hold_jumps(r_)

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
# (head_yaw turns the head but not the eyes: the irises pointed away and read as white. Turn the body instead.)
cop, _ = ch.build_v1(P, (-5.5, 49.0, 0.15), dict(K.COP_V1, head_yaw=0), pose_mode="umbrella", heading=66)
ch.add_umbrella(cop, P, "#121214"); ch.add_cap(cop, P, "#18213a", "#d8b24a")
kid1, _ = ch.build(P, (5.35, 45.1, 0.15), dict(K.KID1, head_yaw=0), pose_mode="umbrella", heading=-90)
kid2, _ = ch.build(P, (5.9, 44.3, 0.15), K.KID2, pose_mode="umbrella", heading=-90)
ch.add_umbrella(kid1, P, "#c9475a"); ch.add_umbrella(kid2, P, "#2c4a8a")     # everyone but Aura Monster carries one
for k_ in (kid1, kid2):                       # children: larger head for their height
    k_.pose.bones["head"].scale = (1.16, 1.16, 1.16)
mom, _ = ch.build(P, (6.25, 45.75, 0.15), dict(K.W1, head_yaw=0), pose_mode="umbrella", heading=-140)   # waiting with the kids
ch.add_umbrella(mom, P, "#6b1d24")
for st_, (cx, cy), hd, pm in ((K.W2, (9.4, 54.2), 180, "phone"), (K.MAN_LONG, (8.5, 55.5), 120, "stand"),
                              (K.MAN_DIAMOND, (10.2, 56.4), -120, "stand")):    # shop customers behind the glass
    c_, _ = ch.build(P, (cx, cy, 0.15), st_, pose_mode=pm, heading=hd)
    if pm == "phone":
        ch.add_phone(c_, P)
w_al, _ = ch.build(P, (-15.5, AL_Y + 1.9, 0.0), dict(K.W4, head_yaw=0), pose_mode="umbrella", heading=145)   # by an alley awning
ch.add_umbrella(w_al, P, "#3c3f44")
w_st, _ = ch.build(P, (-2.6, 70, 0), K.W3, pose_mode="walk"); w_st.name = "W3_walker"      # walks past the hero
walk_path(w_st, [(-2.6, 70, 0), (-2.6, 20, 0)], -40, N, cycle=30, stride=0.55, prop="umbrella")
scn.frame_set(1); ch.add_umbrella(w_st, P, "#24405e", clear=True)

# ------------------------------------------------------------------ the city + the extra sets
C.build_scene(with_hero=False, avoid=[(6.9, 53), (-5.5, 49), (5.6, 44.8), (HERO_X, 40), (-2.6, 60)],
              rain_box=(0.0, 45.0, 18.0, 62.0, 9.0, 24, 17000))
rain_main = bpy.data.objects["rain"]

exec(open(os.path.join(HERE, "film_sets.py")).read())        # shop interior, rooftop set, alley dressing, extra rain

# ------------------------------------------------------------------ the Meridian GT-8 (lookdev/meridian.py, same car as car3d/meridian.html)
# drives toward the camera in the opening wide shot, and away down the street past the pair in the last wide shot;
# hidden in every other shot so it never pops in or out of a shot
import meridian as MER
mer, mer_wheels = MER.build(C.PROPS, "#9c1418", lights=True, name="meridian")
hw0, hw1, pw0, pw1 = fr("hook_wide"), fr("hook_wide", 1), fr("payoff_wide"), N
MER.drive(mer, mer_wheels, [(hw0, (-1.15, 100.0), 180), (hw1, (-1.15, 38.0), 180)])   # lane clear of the parked cars (x=-3.3)    # passes him, then the camera
MER.drive(mer, mer_wheels, [(pw0 - 1, (-1.15, 82.0), 180), (pw0, (-1.15, 81.4), 180), (pw1, (-1.15, 30.0), 180)])
mer_spot = bpy.data.lights.new("meridian_beam", "SPOT"); mer_spot.energy = 900; mer_spot.spot_size = math.radians(55); mer_spot.spot_blend = 0.4
mer_spot.color = (0.92, 0.95, 1.0); ms = bpy.data.objects.new("meridian_beam", mer_spot); C.PROPS.objects.link(ms); ms.parent = mer
ms.location = (0, 2.3, 0.62); ms.rotation_euler = (math.radians(85), 0, 0)    # forward (+y), slightly down
visible(mer, [(hw0, hw1), (pw0, pw1)])

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

# ------------------------------------------------------------------ splashes + ripples where drops hit the ground
import random as _rnd
def splash_mat(name, crown):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N_, L_ = nt.nodes, nt.links; N_.clear()
    out = N_.new("ShaderNodeOutputMaterial"); uvn = N_.new("ShaderNodeUVMap"); sp = N_.new("ShaderNodeSeparateXYZ")
    L_.new(uvn.outputs[0], sp.inputs[0]); geo = N_.new("ShaderNodeNewGeometry")
    clock = N_.new("ShaderNodeValue"); clock.name = "rain_clock"
    def M(op, a, b=None, clamp=False):
        n = N_.new("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L_.new(v, n.inputs[i])
        return n.outputs[0]
    phase = M("FRACT", M("ADD", M("DIVIDE", clock.outputs[0], 7.0), geo.outputs["Random Per Island"]))
    X, Y = sp.outputs["X"], sp.outputs["Y"]
    if crown:   # the drop lands: a crown sheet rises and opens, its spikes throw droplets up and out, then it all falls
        LIFE = 0.36; p = M("DIVIDE", phase, LIFE); live = M("LESS_THAN", phase, LIFE)
        s_ = M("MULTIPLY", M("ABSOLUTE", M("SUBTRACT", X, 0.5)), 2.0)
        Hc = M("MULTIPLY", M("SINE", M("MULTIPLY", M("MINIMUM", p, 1.0), 3.1416)), 0.5)
        yc = M("MULTIPLY", Hc, M("ADD", 0.12, M("MULTIPLY", M("MULTIPLY", s_, s_), 0.88)))
        width = M("MULTIPLY", 0.75, M("ADD", 0.35, M("MULTIPLY", p, 0.65)))
        sheet = M("MULTIPLY", M("LESS_THAN", M("ABSOLUTE", M("SUBTRACT", Y, yc)), 0.03), M("LESS_THAN", s_, width))
        spikes = M("MULTIPLY", M("GREATER_THAN", M("SINE", M("MULTIPLY", X, 38.0)), 0.55),
                   M("MULTIPLY", M("LESS_THAN", M("SUBTRACT", Y, yc), 0.08), M("GREATER_THAN", M("SUBTRACT", Y, yc), 0.0)))
        sheet = M("MAXIMUM", sheet, M("MULTIPLY", spikes, M("LESS_THAN", s_, width)))
        blob = M("MULTIPLY", M("LESS_THAN", Y, M("MULTIPLY", 0.07, M("SUBTRACT", 1.0, p))), M("LESS_THAN", s_, M("ADD", 0.15, M("MULTIPLY", p, 0.5))))
        a = M("MAXIMUM", sheet, blob)
        for i, (side, spread, vel) in enumerate(((-1, 0.36, 1.25), (1, 0.42, 1.1), (-1, 0.2, 1.55), (1, 0.26, 1.45), (-1, 0.47, 0.9), (1, 0.12, 1.7))):
            xi = M("ADD", 0.5, M("MULTIPLY", p, side * spread)); yi = M("SUBTRACT", M("MULTIPLY", p, vel * 0.55), M("MULTIPLY", M("MULTIPLY", p, p), 0.45))
            dxi = M("SUBTRACT", X, xi); dyi = M("SUBTRACT", Y, M("ADD", yi, 0.05))
            d = M("SQRT", M("ADD", M("MULTIPLY", dxi, dxi), M("MULTIPLY", dyi, dyi)))
            a = M("MAXIMUM", a, M("LESS_THAN", d, M("MULTIPLY", 0.028, M("SUBTRACT", 1.0, M("MULTIPLY", p, 0.4)))))
        a = M("MULTIPLY", M("MULTIPLY", a, live), M("MULTIPLY", M("SUBTRACT", 1.0, M("POWER", M("MINIMUM", p, 1.0), 3.0)), 0.9))
    else:       # three wavelets spreading out from the impact, the outer one strongest, all fading as they grow
        dx = M("SUBTRACT", X, 0.5); dy = M("SUBTRACT", Y, 0.5)
        r = M("MULTIPLY", M("SQRT", M("ADD", M("MULTIPLY", dx, dx), M("MULTIPLY", dy, dy))), 2.0)
        a = None
        for k, amp in enumerate((1.0, 0.6, 0.35)):
            band = M("SUBTRACT", 1.0, M("DIVIDE", M("ABSOLUTE", M("SUBTRACT", r, M("SUBTRACT", phase, 0.1 * k))), 0.035), clamp=True)
            band = M("MULTIPLY", band, amp)
            a = band if a is None else M("MAXIMUM", a, band)
        a = M("MULTIPLY", M("MULTIPLY", a, M("POWER", M("SUBTRACT", 1.0, phase), 1.5)), 0.32)
    tr = N_.new("ShaderNodeBsdfTransparent"); em = N_.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = C.lin("#d6e6ff"); em.inputs["Strength"].default_value = 1.1
    mx = N_.new("ShaderNodeMixShader"); L_.new(a, mx.inputs[0]); L_.new(tr.outputs[0], mx.inputs[1])
    L_.new(em.outputs[0], mx.inputs[2]); L_.new(mx.outputs[0], out.inputs[0])
    prefs.keyframe_new_interpolation_type = "CONSTANT"
    for f in range(1, N + 1):                 # same clock as the rain (crawls in the slow-motion reveal)
        clock.outputs[0].default_value = ph[f]; clock.outputs[0].keyframe_insert("default_value", frame=f)
    ch.set_interp(nt, "CONSTANT")
    return m
SPL_R, SPL_C = splash_mat("splash_ripple", False), splash_mat("splash_crown", True)
for _m in bpy.data.materials:   # the puddle ripples in the street/pavement shaders run on the same (slow-motion) clock
    if not _m.node_tree or _m.name.startswith("splash_"): continue
    for _n in _m.node_tree.nodes:
        if _n.name == "rain_clock":
            _n.outputs[0].driver_remove("default_value")
            for f in range(1, N + 1):
                _n.outputs[0].default_value = ph[f]; _n.outputs[0].keyframe_insert("default_value", frame=f)
            ch.set_interp(_m.node_tree, "CONSTANT")
def splashes(name, cx, cy, w, dep, z, n, dry):
    rng = _rnd.Random(name); bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap"); crowns = []
    def quad(vs, crown):
        f = bm.faces.new([bm.verts.new(v) for v in vs])
        for l_, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            l_[uv].uv = (u, v)
        if crown: crowns.append(f)
    for _ in range(n):
        x = rng.uniform(cx - w / 2, cx + w / 2); y = rng.uniform(cy - dep / 2, cy + dep / 2)
        if dry(V((x, y, 0))):
            continue
        r = rng.uniform(0.06, 0.12); zz = z + 0.005
        quad([(x - r, y - r, zz), (x + r, y - r, zz), (x + r, y + r, zz), (x - r, y + r, zz)], False)
        h = rng.uniform(0.07, 0.11); c_ = 0.055
        quad([(x - c_, y, zz), (x + c_, y, zz), (x + c_, y, zz + h), (x - c_, y, zz + h)], True)
        quad([(x, y - c_, zz), (x, y + c_, zz), (x, y + c_, zz + h), (x, y - c_, zz + h)], True)
    me = bpy.data.meshes.new(name); me.materials.append(SPL_R); me.materials.append(SPL_C)
    for f in crowns: f.material_index = 1
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); C.FX.objects.link(ob); ob.visible_shadow = False
    ob.visible_diffuse = ob.visible_glossy = ob.visible_transmission = False   # camera only: no dark squares on the floor
    return ob
# the street's splashes in two sets, so a patch is only kept dry while someone dry is actually standing in it:
# before the payoff only the hero's line stays dry; from the payoff only the walking pair's
_P0 = fr("payoff_two") - 1
def _dry_early(p):
    return ((abs(p.x - HERO_X) < 0.3 and AL_Y - 0.6 < p.y < y_start + 2) or (p.x < HERO_X and abs(p.y - AL_Y) < 0.3)
            or any((p.xy - u.xy).length < 0.6 for u in UMBS))
def _dry_late(p):
    return (-1.3 < p.x < 2.4 and 28 < p.y < 66) or any((p.xy - u.xy).length < 0.6 for u in UMBS)
visible(splashes("splash_main", 0.0, 45.0, 18.0, 62.0, 0.0, 4200, _dry_early), [(1, _P0)])
visible(splashes("splash_main_late", 0.0, 45.0, 18.0, 62.0, 0.0, 4200, _dry_late), [(_P0 + 1, N)])
# the low shot at his feet (like the user's reference): a dense carpet of crowns all around, just not under his shoes
_hf0, _hf1 = fr("hook_feet"), fr("hook_feet", 1)
_hy = [hero_s_at(f)[0].y for f in (_hf0, _hf1)]
visible(splashes("splash_feet", HERO_X, sum(_hy) / 2, 3.2, abs(_hy[1] - _hy[0]) + 3.0, 0.0,
                 int(3.2 * (abs(_hy[1] - _hy[0]) + 3.0) * 38), lambda p: abs(p.x - HERO_X) < 0.34), [(_hf0, _hf1)])
splashes("splash_alley", -22.0, AL_Y, 28.0, 5.0, 0.0, 1000,
         lambda p: (abs(p.y - AL_Y) < 0.5 and p.x > STOP.x - 1.0) or (p.xy - NARR_T.xy).length < 0.62)
splashes("splash_alley2", 18.0, AL2_Y, 20.0, 5.0, 0.0, 700, lambda p: (p.xy - UT.xy).length < 0.6)
splashes("splash_roof", ROOF.x, ROOF.y + 2.0, 15.0, 12.0, ROOF.z, 1000, lambda p: (p.xy - RT.xy).length < 0.6)

# ------------------------------------------------------------------ aura: the hero always; the kid once he closes it
def aura(owner, f_on, f_full, f_off=None, watts=70, color=(0.55, 0.92, 1.0)):
    ld = bpy.data.lights.new("aura", "POINT"); ld.color = color; ld.shadow_soft_size = 0.6
    ob = bpy.data.objects.new("aura", ld); C.FX.objects.link(ob); ob.parent = owner; ob.location = (0, 0, 1.15 / owner.scale[0])
    prefs.keyframe_new_interpolation_type = "BEZIER"
    for f, e in ((1, 0), (f_on, 0), (f_full, watts)) + (((f_off - 1, watts), (f_off, 0)) if f_off else ()):
        ld.energy = e; ld.keyframe_insert("energy", frame=f)
    return ob
aura(hero_a, SLOW0 - 4, SLOW0 + 20, None, 60)
aura(narr_b, FOLD + 4, FOLD + 26, None, 40, color=(1.0, 0.82, 0.3))          # his aura is yellow
eyes_turn(narr_b, FOLD + 4, fr("close", 1))                                     # ...and he has the hero's eyes now
aura(narr_p, 1, 2, None, 40, color=(1.0, 0.82, 0.3)); aura(hero_p, 1, 2, None, 50)
# white aura composited from a per-frame mask (compose.py): heroes always, the narrator only after he can dodge
for rig, idx in ((hero_s, 7), (hero_a, 7), (hero_t, 7), (hero_p, 7), (narr_p, 8), (narr_b, 8)):   # 7 white, 8 yellow
    for o in [rig] + list(rig.children_recursive):
        o.pass_index = 0 if o.get("no_mask") else idx            # the ground shadow never glows
for o in umb_b:
    o.pass_index = 0
json.dump({"keys": [[1, 0.0], [fr("name_close") - 1, 0.0], [fr("name_close"), 0.6], [SLOW0, 0.6],   # no aura until he is introduced
           [SLOW0 + 16, 1.25], [SLOW1, 1.2], [SLOW1 + 8, 0.7], [N, 0.8]],
           "keys_y": [[1, 0.0], [FOLD, 0.0], [FOLD + 18, 1.15], [N, 1.0]],
           "trail": [SLOW0, SLOW1]}, open(os.path.join(HERE, "aura.json"), "w"))

# ------------------------------------------------------------------ camera
exec(open(os.path.join(HERE, "film_camera.py")).read())
if os.environ.get("CAMDUMP"):   # QA: per-frame camera / look-target path from the keyed curves, then stop
    from bpy_extras import anim_utils
    def _fc(ob):
        cb = anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, ob.animation_data.action_slot)
        return {(c.data_path, c.array_index): c for c in cb.fcurves}
    _c, _t = _fc(cam), _fc(tgt)
    json.dump([[f] + [_c[("location", i)].evaluate(f) for i in range(3)] + [_t[("location", i)].evaluate(f) for i in range(3)]
               for f in range(1, N + 1)], open(os.environ["CAMDUMP"], "w"))
    print("CAMDUMP", os.environ["CAMDUMP"]); sys.exit(0)

# footsteps: a heel strike every half cycle of each walk (left at key 0, right at key n/2), where the walker is on
# screen; gain falls off with the distance to the camera. Read by audio.py.
def _fc(ob, path, idx, f, default):
    from bpy_extras import anim_utils
    ad = ob.animation_data
    if not ad or not ad.action: return default
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    fc = cb.fcurves.find(path, index=idx) if cb else None
    return fc.evaluate(f) if fc else default
def _loc(ob, f):
    return V(tuple(_fc(ob, "location", i, f, ob.location[i]) for i in range(3)))
STEPS = []
try:
    for w in WALKS:
        rig = w["rig"]; k = 0
        while True:
            t = w["f0"] + w["step"] * (k * w["n"] / 2 - w["off"]); k += 1
            if t > w["f1"]: break
            if t < max(1, w["f0"]) or _fc(rig, "hide_render", 0, t, 0.0) > 0.5: continue
            d = max(0.5, (_loc(cam, t) - _loc(rig, t)).length)
            STEPS.append(dict(t=round((t - 1) / 30.0, 3), rig=rig.name, gain=round(min(1.0, 2.2 / d), 3)))
    json.dump(sorted(STEPS, key=lambda e: e["t"]), open(os.path.join(HERE, "steps.json"), "w"), indent=0)
except Exception as e_:                       # never let the sound bookkeeping stop a render
    print("footsteps export failed:", repr(e_))
print("footsteps:", len(STEPS))

# ------------------------------------------------------------------ render
C.render_settings(SCALE, SAMPLES)
scn.cycles.transparent_max_bounces = 48       # stacked splash crowns at grazing angles must not turn black
scn.frame_start, scn.frame_end = FIRST, LAST
scn.frame_step = int(os.environ.get("STEP", 1))       # STEP=2 renders on twos (held frames at encode)
out_dir = os.path.join(HERE, "frames"); os.makedirs(out_dir, exist_ok=True)
scn.render.image_settings.file_format = "PNG"
scn.render.compositor_device = "CPU"
scn.view_layers[0].use_pass_object_index = True
ng = bpy.data.node_groups.new("comp", "CompositorNodeTree"); scn.compositing_node_group = ng
rl = ng.nodes.new("CompositorNodeRLayers"); idm = ng.nodes.new("CompositorNodeIDMask"); idm.inputs["Index"].default_value = 7
idm.inputs["Anti-Alias"].default_value = True                                          # soft mask edges (no stair-steps in the aura)
go = ng.nodes.new("NodeGroupOutput"); ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
ng.links.new(rl.outputs["Image"], go.inputs[0]); ng.links.new(rl.outputs["Object Index"], idm.inputs["ID value"])
fo = ng.nodes.new("CompositorNodeOutputFile"); fo.directory = os.path.join(HERE, "masks"); fo.file_name = "mask_"
fo.format.media_type = "IMAGE"; fo.format.file_format = "PNG"; fo.format.color_mode = "BW"
fo.file_output_items.new("FLOAT", ""); ng.links.new(idm.outputs["Alpha"], fo.inputs[0])
idy = ng.nodes.new("CompositorNodeIDMask"); idy.inputs["Index"].default_value = 8      # the narrator (yellow aura)
idy.inputs["Anti-Alias"].default_value = True
ng.links.new(rl.outputs["Object Index"], idy.inputs["ID value"])
fy = ng.nodes.new("CompositorNodeOutputFile"); fy.directory = os.path.join(HERE, "masks_y"); fy.file_name = "mask_"
fy.format.media_type = "IMAGE"; fy.format.file_format = "PNG"; fy.format.color_mode = "BW"
fy.file_output_items.new("FLOAT", ""); ng.links.new(idy.outputs["Alpha"], fy.inputs[0])
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
