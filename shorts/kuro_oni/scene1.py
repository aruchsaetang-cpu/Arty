"""Kuro Oni ep 1, REAL SCENE 1 v3 (the 3 s hook, manhwa cut): a ring of street fighters (real men, faces, own clothes) round
the hero on a burning street (no rain). ONE enemy lunges with a right haymaker; the hero ducks under it, plants, turns hips
then spine then shoulder and drives a gyaku-zuki (right reverse punch) into the man's face. Hit-stop, head snaps, face caves,
eyes go white, blood flies; he is launched, tumbles diagonally through the air and slams the road. The others flinch back.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/scene1.py [scale%]
v3 renders JOBS: static manhwa-panel cameras (no camera animation at all), each a list of source frames, to
shorts/kuro_oni/frames_s1v3/<shot>_<frame>.png (existing files skipped, so it resumes) + proj.json (screen positions of the
contact point, the enemy's eyes/mouth, the fist, for the 2D post). env: SAMPLES (12), ONLY="shot,shot" render those shots,
STILLS="shot:frame,..." -> stills_s1v3/, NORENDER=1 build only, CHECK=1 print contact distances.
Post (manhwa ink grade, split panels, SFX, sound): shorts/kuro_oni/scene1_compose.py
v2 frames (frames_s1v2/) are reused for the hero eyes ECU (unchanged shot)."""
import math, os, random, sys, time, resource
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
FPS, DUR = 30, 3.0; NF = int(DUR * FPS)
os.environ["FRAMES"] = str(NF + 6); os.environ["PEOPLE"] = "0"; os.environ.setdefault("SEED", "7")
sys.path.insert(0, HERE)
import cast_kuro as CK                      # imports city (resets the scene), character_mh, cast, kimono
import bpy, bmesh
from mathutils import Vector as V, Quaternion as Q, Matrix
import city as C
import character_mh as ch
scn = C.scn; prefs = C.prefs; P = C.PEOPLE_C
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 50
FIRST = int(sys.argv[2]) if len(sys.argv) > 2 else 1
LAST = int(sys.argv[3]) if len(sys.argv) > 3 else NF
SAMPLES = int(os.environ.get("SAMPLES", 12))
RAD = math.radians
def F(t): return int(round(t * FPS)) + 1
def T_(f): return (f - 1) / FPS
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0
T0 = time.time()
HC = V((0.0, 40.0, 0.0))                    # ring centre; the hero stands here and faces +x (the attacker)
T_HIT = 2.10; F_HIT = F(T_HIT)              # fist meets face (frame 64)
T_SNAP = 2.23                               # hit-stop ends, the head snaps
F_ONES = set(range(F(1.85), F_HIT + 1))     # rendered on ones (the punch itself); everything else on twos
RENDER = sorted(set(range(1, NF + 1, 2)) | F_ONES)

# ------------------------------------------------------------------ pose solver + moves: shorts/kuro_oni/moves.py
import moves as MV
from moves import ez, stance_feet, GUARD_L, GUARD_R, HIKITE_L, HIKITE_R
def Rig(g): return MV.Rig(g, origin=HC)

def on_ground(g):
    """contact-shadow discs would float with a tilted body: hide them."""
    for c in g.children:
        if c.name.startswith("contact_shadow"): c.hide_render = True

# ------------------------------------------------------------------ cast (built before the city: cheap pose solves)
NEAR = [(3.4, 106), (3.55, 134), (3.35, 163), (3.5, -156), (3.6, 72), (3.4, -126)]   # (radius, angle deg) of the full-rig ring men
NEAR_ST = [0, 1, 2, 3, 4, 5]                                                    # FIGHTERS styles; the attacker is FIGHTER_7 (red jacket)
TEMP_ST = [6, 8, 9, 10, 11]                                                    # extra looks, baked to static men then deleted
names = ["HERO", "FIGHTER_7"] + [f"FIGHTER_{i}" for i in NEAR_ST] + [f"FIGHTER_{i}" for i in TEMP_ST]
locs = {n: (HC.x + 30 + 2 * i, HC.y + 30, 0) for i, n in enumerate(names)}
arms_ = CK.build_cast(P, names, locs=locs, hero_cloak=True, heading=0.0)
hero = arms_["HERO"]; att = arms_["FIGHTER_7"]
near = [arms_[f"FIGHTER_{i}"] for i in NEAR_ST]; temps = [arms_[f"FIGHTER_{i}"] for i in TEMP_ST]
for g in arms_.values(): ch.grip(g, "L"); ch.grip(g, "R")
print(f"cast built {time.time() - T0:.0f}s rss {rss():.2f} GB", flush=True)
for g in [att] + near + temps: print(g.name, [c.name for c in g.children_recursive if c.type == "MESH"][:30])
FR_ALL = list(range(1, NF + 7))

def heading_to(frm, to):
    d = V(to) - V(frm); return math.degrees(math.atan2(d.x, -d.y))

# ---- the attacker (FIGHTER_7): stance at x=+1.95 facing -x, lunge + right haymaker, takes the punch, spins, crumples, slams down
A = Rig(att)
fa = stance_feet(1.95, 0.0, -118, front=(0.12, -0.36), back=(-0.14, 0.30), fy=(26, -22))
A.key(0.0, x=1.95, y=0.0, yaw=-118, drop=0.10, twist=20, lean=6, hy=8, footL=fa[0], footR=fa[1], fistL=("c", GUARD_L), fistR=("c", GUARD_R))
A.key(0.55, drop=0.13); A.key(1.1, drop=0.09); A.key(1.55, drop=0.12)
A.key(1.62, x=1.92, twist=20, fistR=("c", GUARD_R), footL=fa[0])
A.key(1.80, x=1.70, yaw=-112, twist=-22, lean=10, drop=0.12, fistR=("c", (-0.46, 0.28, 1.50)), hy=18)     # wind up: right fist back
A.key(1.84, footL=(1.30, -0.15, -95, 0.10), footR=fa[1])
A.key(1.90, footL=(0.92, -0.14, -96, 0.0), ease="in")                                                  # front foot lands
A.key(1.88, fistR=("w", (0.85, 0.62, 1.72)))
A.key(1.95, x=1.30, y=-0.02, yaw=-96, twist=34, lean=18, drop=0.14, hy=0, hp=8, fistR=("w", (0.28, 0.12, 1.74)), footR=(1.92, 0.20, -128, 0.03))
A.key(2.04, x=1.05, y=-0.02, yaw=-88, twist=40, lean=22, side=4, drop=0.16, hp=12, fistR=("w", (0.30, -0.62, 1.52)),
      fistL=("c", (0.16, -0.22, 1.22)), footR=(1.62, 0.18, -120, 0.0))
A.key(T_HIT, x=1.04, twist=40, lean=22, hp=12, hy=0, hr=0, hs=(1.0, 1.0, 1.0), fistR=("w", (0.34, -0.66, 1.48)))
A.key(T_HIT + 0.02, hs=(0.78, 0.93, 1.12), ease="snap")                                  # face caves in on contact
A.key(T_SNAP, x=1.05, twist=40, lean=22, hp=12, hy=-4, hr=-3, hs=(0.76, 0.93, 1.13), yaw=-88, drop=0.16, side=4)   # hit-stop: frozen
A.key(T_SNAP + 0.09, hy=-58, hr=-30, hp=-26, x=1.14, tilt=(-4.0, 0.4, 0.0), ease="snap")   # (tilt held at v2's -4 deg until here)                        # head snaps to his right, chin up
A.key(2.50, x=1.46, y=0.04, yaw=-122, twist=-28, lean=-12, side=-12, drop=0.02, tilt=(-22.0, 2.2, 0.0), hs=(0.84, 0.95, 1.08),
      fistR=("c", (-0.58, 0.12, 1.46)), fistL=("c", (0.48, -0.18, 1.12)), hy=-50, hr=-28, hp=-30, ease="out")       # launched: feet leave the road
A.key(2.62, x=1.64, y=0.16, yaw=-150, twist=-30, drop=-0.06, tilt=(-52.0, 5.2, 0.0), lean=-16, side=-6,
      fistR=("c", (-0.50, -0.32, 1.80)), fistL=("c", (0.50, -0.25, 1.75)), hp=-24, ease="lin")                         # flying, arched, arms up
A.key(2.73, x=1.72, y=0.30, tilt=(-77.6, 7.8, 0.0), drop=0.36, lean=0, hs=(1.0, 1.0, 1.0), hy=-30, hr=-10, hp=20, ease="in")   # slams down
A.key(2.79, tilt=(-70.0, 7.0, 0.0), ease="out")                                                       # bounce
A.key(2.88, tilt=(-78.6, 7.9, 0.0), fistR=("c", (-0.42, -0.45, 1.30)), fistL=("c", (0.40, -0.40, 1.25)), ease="in")
A.key(3.2, tilt=(-78.6, 7.9, 0.0))
A.finalize()
A.bake(FR_ALL); on_ground(att)
# the attacker's face at the contact frame: where the fist must land (his left cheek)
scn.frame_set(F_HIT); bpy.context.view_layer.update()
def bone_w(g, n, at="head"):
    pb = g.pose.bones[n]; return g.matrix_world @ (pb.head if at == "head" else pb.tail)
def head_frame(g):
    """-> head joint (world), face forward, up, his left: the rest-pose body axes carried by the head bone's pose rotation."""
    pb = g.pose.bones["head"]; Rr = g.matrix_world.to_3x3().normalized() @ pb.matrix.to_3x3() @ g.data.bones["head"].matrix_local.to_3x3().inverted()
    return (g.matrix_world @ pb.head), (Rr @ V((0, -1, 0))).normalized(), (Rr @ V((0, 0, 1))).normalized(), (Rr @ V((1, 0, 0))).normalized()
hp_, hfw, hup, hlt = head_frame(att)
FACE = hp_ + hup * 0.085 + hfw * 0.095 + hlt * 0.03      # his left cheek
print("attacker head", tuple(round(c, 3) for c in hp_), "fwd", tuple(round(c, 2) for c in hfw), "up", tuple(round(c, 2) for c in hup))

# ---- the hero: bladed stance facing +x, duck under the swing, rise: rear-foot pivot, hips, spine, shoulder, then the arm
H = Rig(hero)
PUNCH = FACE + V((-0.04, 0.0, 0.0))                 # fist centre just short of the cheek surface: knuckles touch
MV.stance_idle(H, 0.0, 1.75, 0.0, 0.0, 90, seed=3)  # kamae, bouncing on the balls of the feet
MV.slip_turn(H, 1.75, 0.15, hold=0.07)              # ducks under the haymaker, rear hip loaded (ends 1.97)
MV.gyaku_zuki(H, 1.97, T_HIT - 1.97, PUNCH)         # heel pivot -> hips -> spine -> shoulder -> fist, contact at T_HIT
H.finalize()
for it in range(3):                         # close the loop: measure the fist against the cheek, correct the target, re-key
    hero.animation_data_clear(); H.bake(FR_ALL); scn.frame_set(F_HIT); bpy.context.view_layer.update()
    fist = bone_w(hero, "wrist.R", "tail"); err = PUNCH - fist
    print(f"fist {tuple(round(c, 3) for c in fist)} target {tuple(round(c, 3) for c in PUNCH)} err {err.length * 100:.1f} cm", flush=True)
    if err.length < 0.015: break
    for t, d, e in H.keys:
        if "fistR" in d and t >= T_HIT - 1e-6: d["fistR"] = ("w", tuple(V(d["fistR"][1]) + err))
scn.frame_set(F_HIT - 6); bpy.context.view_layer.update(); print("fist at 1.93 s (chamber)", tuple(round(c, 2) for c in bone_w(hero, "wrist.R", "tail")))

# ---- cloak follow-through: the back panel (rigid, on spine01) hinges at its top edge. It trails back while the body drives
# in (1.97-2.10), whips forward past rest when the body stops dead on the hit (kime), swings back and settles.
def swing_deg(t):
    ks = [(0.0, 0.0), (1.80, 0.0), (1.97, -6.0), (2.10, 24.0), (2.24, -18.0), (2.40, 9.0), (2.56, -4.0), (2.75, 1.5), (2.95, 0.0)]
    for (t0, a0), (t1, a1) in zip(ks, ks[1:]):
        if t0 <= t <= t1: return a0 + (a1 - a0) * ez((t - t0) / (t1 - t0), "io")
    return 0.0
_cl = [o for o in hero.children_recursive if o.type == "MESH" and o.data.materials and o.data.materials[0] and o.data.materials[0].name.startswith("cloak")]
if _cl:
    pan = max(_cl, key=lambda o: o.dimensions.z); MW = {}
    for f in FR_ALL:
        scn.frame_set(f); bpy.context.view_layer.update(); MW[f] = pan.matrix_world.copy()
    pan.parent = None; pan.animation_data_clear(); pan.rotation_mode = "QUATERNION"
    prefs.keyframe_new_interpolation_type = "LINEAR"
    for f in FR_ALL:
        M = MW[f]; top = M @ V((0, 0, 0.5)); a = RAD(swing_deg(T_(f)))      # cube is unit size: +0.5 local z = the top edge
        R = Matrix.Translation(top) @ Matrix.Rotation(a, 4, "Y") @ Matrix.Translation(-top)
        pan.matrix_world = R @ M
        pan.keyframe_insert("location", frame=f); pan.keyframe_insert("rotation_quaternion", frame=f); pan.keyframe_insert("scale", frame=f)
    print("cloak follow-through keyed on", pan.name)

# ---- the ring men: guard, small bob; after the hit they flinch, raise the guard and step back (nobody flies)
NR = []
for i, (g, (r, a)) in enumerate(zip(near, NEAR)):
    R_ = Rig(g); x, y = r * math.cos(RAD(a)), r * math.sin(RAD(a)); yaw = heading_to((x, y, 0), (0.6, 0, 0)) - 25
    ff = stance_feet(x, y, yaw); rng = random.Random(40 + i)
    out = V((x - 0.9, y, 0)).normalized() * rng.uniform(0.28, 0.42)
    R_.key(0.0, x=x, y=y, yaw=yaw, drop=0.09, twist=22, lean=5, hy=6, footL=ff[0], footR=ff[1], fistL=("c", GUARD_L), fistR=("c", GUARD_R))
    for k in range(4): R_.key(0.3 + 0.5 * k + rng.uniform(0, 0.2), drop=rng.uniform(0.07, 0.12), twist=22 + rng.uniform(-6, 6))
    t0 = 2.22 + rng.uniform(0, 0.08)
    R_.key(t0, x=x, y=y, lean=5, hp=0, drop=0.10, twist=22, fistL=("c", GUARD_L), fistR=("c", GUARD_R), footL=ff[0], footR=ff[1])
    fb = stance_feet(x + out.x, y + out.y, yaw)
    R_.key(t0 + 0.16, lean=-10, hp=-10, drop=0.05, fistL=("c", (0.10, -0.28, 1.62)), fistR=("c", (-0.12, -0.22, 1.60)), ease="snap")
    R_.key(t0 + 0.30, footR=(fb[1][0], fb[1][1], fb[1][2], 0.0))
    R_.key(t0 + 0.22, footR=(ff[1][0] + out.x * 0.5, ff[1][1] + out.y * 0.5, ff[1][2], 0.07))
    R_.key(t0 + 0.36, x=x + out.x, y=y + out.y, ease="io")
    R_.key(t0 + 0.34, footL=(ff[0][0] + out.x * 0.5, ff[0][1] + out.y * 0.5, ff[0][2], 0.06))
    R_.key(t0 + 0.44, footL=fb[0], lean=-6, hp=-6, drop=0.10)
    R_.finalize(); R_.bake(FR_ALL); NR.append(R_)

# ---- lookdev: the hero DIM (low glow, only a thin warm fire edge; his white eyes are the brightest thing on him);
# the enemies lit by the fire (brighter, warm orange rim) so the contrast reads
def brighten(g, glow, rim, blend, extra=()):
    done = {}
    for ob in list(g.children_recursive) + list(extra):
        if ob.type not in ("MESH", "CURVE"): continue
        mats = ob.data.materials
        for i, m in enumerate(mats):
            if not m or not m.use_nodes or m.name in ("ink",) or "eye" in m.name: continue
            if m.name not in done:
                m2 = m.copy(); nt = m2.node_tree
                for n in nt.nodes:
                    if n.type == "EMISSION": n.inputs["Strength"].default_value = glow * (0.9 if "skin" in m.name else 1.0)
                    if n.type == "LAYER_WEIGHT": n.inputs["Blend"].default_value = blend
                em = next((n for n in nt.nodes if n.type == "EMISSION"), None)
                if em and em.inputs["Color"].links:
                    mx = em.inputs["Color"].links[0].from_node
                    if mx.type == "MIX" and not mx.inputs[7].links: mx.inputs[7].default_value = rim
                done[m.name] = m2
            mats[i] = done[m.name]
brighten(hero, 0.62, (2.2, 0.95, 0.32, 1.0), 0.10, extra=[pan] if _cl else [])          # v3: dim body, a thin but clearly bright fire rim
for g in [att] + near + temps: brighten(g, 1.12, (1.0, 0.55, 0.2, 1.0), 0.30)
# ---- extra looks: pose the temp rigs in a guard, bake them (and the near men) to static meshes for the back rows, then delete the temps
def bake_variant(g, tag):
    dg = bpy.context.evaluated_depsgraph_get(); coll = bpy.data.collections.new(f"VAR_{tag}"); inv = g.matrix_world.inverted()
    for o in g.children_recursive:
        if o.type not in ("MESH", "CURVE") or o.hide_render or o.name.startswith("contact_shadow"): continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); n = bpy.data.objects.new(f"v{tag}_{o.name}", me)
        n.matrix_world = inv @ o.matrix_world; coll.objects.link(n)
    return coll
VARS = []
for i, g in enumerate(temps):
    R_ = Rig(g); ff = stance_feet(30 + 2 * i, 30, 0, fy=(8, -38))
    R_.key(0.0, x=30 + 2 * i, y=30, yaw=0, drop=0.09, twist=20 + 4 * i, lean=5 + i, hy=4, footL=ff[0], footR=ff[1],
           fistL=("c", GUARD_L if i % 2 == 0 else (0.16, -0.30, 1.30)), fistR=("c", GUARD_R if i % 3 else (-0.2, -0.1, 1.2)))
    R_.finalize(); R_.bake([1])
scn.frame_set(1); bpy.context.view_layer.update()
for i, g in enumerate(temps + near): VARS.append((bake_variant(g, i), g["base_z"]))
for g in temps:
    for o in list(g.children_recursive) + [g]: bpy.data.objects.remove(o, do_unlink=True)
for me in [m for m in bpy.data.meshes if m.users == 0]: bpy.data.meshes.remove(me)
print(f"variants baked {len(VARS)}  {time.time() - T0:.0f}s rss {rss():.2f} GB", flush=True)

# ---- back rows: instanced baked men (faces, colours), facing the fight; they flinch and lean back after the hit
CAMS_XY = [V((0.7, -3.5)), V((2.9, 0.45)), V((0.6, -3.5)), V((0.4, -2.2)), V((0.9, -3.6)), V((3.5, 0.2)), V((0.9, -2.9))]
BACK = []; rng = random.Random(9)
occupied = [V((r * math.cos(RAD(a)), r * math.sin(RAD(a)))) for r, a in NEAR] + [V((1.95, 0)), V((0, 0))]
for r, n in ((4.4, 26), (5.3, 30), (6.3, 34)):
    for k in range(n):
        a = 360.0 * k / n + rng.uniform(-4, 4) + (6 if r > 5 else 0)
        p = V((r * math.cos(RAD(a)) * rng.uniform(0.95, 1.05), r * math.sin(RAD(a)) * rng.uniform(0.95, 1.05)))
        if abs(p.x) > 5.0 or abs(p.y) > 7.6: continue
        if any((p - c).length < 1.3 for c in CAMS_XY) or any((p - c).length < 0.75 for c in occupied): continue
        occupied.append(p); BACK.append(p)
prefs.keyframe_new_interpolation_type = "BEZIER"
for i, p in enumerate(BACK):
    coll, bz = VARS[i % len(VARS)]
    e = bpy.data.objects.new(f"man_{i}", None); e.instance_type = "COLLECTION"; e.instance_collection = coll; P.objects.link(e)
    yaw = heading_to((p.x, p.y, 0), (0.6, 0, 0)) + rng.uniform(-25, 25); sc = rng.uniform(0.94, 1.06)
    e.location = HC + V((p.x, p.y, bz * sc)); e.rotation_euler = (0, 0, RAD(yaw)); e.scale = (sc, sc, sc)
    e.keyframe_insert("location", frame=1); e.keyframe_insert("rotation_euler", frame=1)
    t0 = 2.24 + 0.012 * (p - V((1.15, 0))).length + rng.uniform(0, 0.06); f0 = F(t0)
    e.keyframe_insert("location", frame=f0); e.keyframe_insert("rotation_euler", frame=f0)
    u = V((p.x - 1.0, p.y, 0)).normalized(); back = rng.uniform(0.15, 0.35); tb = RAD(rng.uniform(5, 10))
    e.location = HC + V((p.x + u.x * back, p.y + u.y * back, bz * sc)); e.rotation_euler = (u.y * tb, -u.x * tb, RAD(yaw))  # lean away
    e.keyframe_insert("location", frame=f0 + 10); e.keyframe_insert("rotation_euler", frame=f0 + 10)
print("back-row men", len(BACK), flush=True)

# eyes: the hero's go full white at 1.5 s; the attacker's roll white on the hit
wm = bpy.data.materials.new("eye_white"); wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); e_ = nt.nodes.new("ShaderNodeEmission")
e_.inputs["Color"].default_value = (1, 1, 1, 1); e_.inputs["Strength"].default_value = 6.0; nt.links.new(e_.outputs[0], o_.inputs[0])
prefs.keyframe_new_interpolation_type = "CONSTANT"
def white_eyes(g, t, grow=1.04):
    eyes = [c for c in g.children_recursive if c.type == "MESH" and c.name.lower().startswith(("eye_", "eye."))]
    for o in eyes:
        v = o.copy(); v.data = o.data.copy(); v.animation_data_clear(); v.name = o.name + "_white"; v.scale = tuple(grow * s for s in o.scale)
        for c_ in o.users_collection: c_.objects.link(v)
        v.data.materials.clear(); v.data.materials.append(wm)
        o.hide_render = False; o.keyframe_insert("hide_render", frame=1); o.hide_render = True; o.keyframe_insert("hide_render", frame=F(t))
        v.hide_render = True; v.keyframe_insert("hide_render", frame=1); v.hide_render = False; v.keyframe_insert("hide_render", frame=F(t))
    return len(eyes)
print("white eyes hero", white_eyes(hero, 1.5), "attacker", white_eyes(att, T_HIT + 0.04, 1.06))

# ---- the street (reuse the city; no people, NO rain), then the fires
C.build_scene(with_hero=False, avoid=[], rain_box=(0.0, 38.0, 1.0, 1.0, 1.0, 1, 10))
for ob in [o for o in bpy.data.objects if o.name.startswith("rain")]: bpy.data.objects.remove(ob, do_unlink=True)
# v3: a dry road (no rain): the mirror puddles reflected bright blobs; flatten them to a dull asphalt sheen, no ripples
for m_ in [m for m in bpy.data.materials if m.name.startswith("asphalt") and m.use_nodes]:
    for n_ in m_.node_tree.nodes:
        if n_.type == "BSDF_PRINCIPLED":
            for l_ in list(n_.inputs["Roughness"].links): m_.node_tree.links.remove(l_)
            n_.inputs["Roughness"].default_value = 0.55
        if n_.type == "BUMP": n_.inputs["Strength"].default_value = 0.12
print(f"city built {time.time() - T0:.0f}s rss {rss():.2f} GB", flush=True)
# a burning-city sky: red-black smoke above, an orange glow low down
_w = scn.world.node_tree; _cr = next(n for n in _w.nodes if n.type == "VALTORGB"); _e = _cr.color_ramp.elements
_e[0].color = (0.55, 0.12, 0.02, 1); _e[-1].color = (0.012, 0.004, 0.004, 1)
for el in _e[1:-1]: el.color = (0.16, 0.03, 0.01, 1)
RIGS = set([hero, att] + near)
def _rig_child(ob):
    while ob is not None:
        if ob in RIGS: return True
        ob = ob.parent
    return False
CLEAR = []
for ob in bpy.data.objects:
    if ob.type != "MESH" or ob.name in ("road", "fog") or ob.name.startswith(("v", "walk", "curb", "paint", "fire", "smoke", "ember", "wreck")): continue
    if _rig_child(ob) or ob.users_collection and ob.users_collection[0].name.startswith("VAR_"): continue
    c = ob.matrix_world @ (sum((V(b) for b in ob.bound_box), V()) / 8); d = ob.dimensions
    if abs(c.x - HC.x) < 5.6 and abs(c.y - HC.y) < 8.6 and c.z < 3.0 and d.z < 5.0 and d.x < 6.0 and d.y < 8.0: CLEAR.append(ob.name)
    elif abs(c.x - HC.x) < 6.6 and abs(c.y - HC.y) < 12.0 and c.z < 8.0 and max(d) < 6.0: CLEAR.append(ob.name)      # street trees, lamps
for n_ in CLEAR: bpy.data.objects[n_].hide_render = True
print("hidden props in the ring area:", len(CLEAR), CLEAR[:10])

def emissive(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*col, 1); e.inputs["Strength"].default_value = strength; nt.links.new(e.outputs[0], o.inputs[0]); return m, e
M_EMB, _ = emissive("ember", (1.0, 0.55, 0.15), 30.0)
# Flame and smoke CARDS: a vertical quad (origin at its bottom centre, UV u across, v up). The shader draws tapered tongues from
# scrolling noise and posterises them into anime colour bands: white-yellow core -> yellow -> orange -> red -> clear. The noise
# clock is keyed on twos, so the flames change shape per drawing; each card offsets the noise by its random id.
CLOCK = []
def card_mat(name, smoke=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links; N.clear()
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    def mth(op, a, b=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
    oi = N.new("ShaderNodeObjectInfo"); clk = N.new("ShaderNodeValue"); CLOCK.append(clk); u, v = sep.outputs[0], sep.outputs[1]
    rnd = mth("MULTIPLY", oi.outputs["Random"], 37.0)
    cv = N.new("ShaderNodeCombineXYZ")
    L.new(mth("ADD", mth("MULTIPLY", u, 1.6 if smoke else 3.4), rnd), cv.inputs[0])            # flames: narrow across, long up = licks
    L.new(mth("SUBTRACT", mth("MULTIPLY", v, 1.3 if smoke else 1.1), mth("MULTIPLY", clk.outputs[0], 0.5 if smoke else 2.2)), cv.inputs[1])
    L.new(mth("ADD", rnd, mth("MULTIPLY", clk.outputs[0], 0.25 if smoke else 0.9)), cv.inputs[2])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6 if smoke else 2.2; nz.inputs["Detail"].default_value = 4.0
    nz.inputs["Roughness"].default_value = 0.6; L.new(cv.outputs[0], nz.inputs["Vector"])
    if "Distortion" in nz.inputs: nz.inputs["Distortion"].default_value = 0.0 if smoke else 0.6
    cv2_ = N.new("ShaderNodeVectorMath"); cv2_.operation = "SCALE"; cv2_.inputs["Scale"].default_value = 3.1; L.new(cv.outputs[0], cv2_.inputs[0])
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 2.6; nz2.inputs["Detail"].default_value = 6.0; nz2.inputs["Roughness"].default_value = 0.65
    L.new(cv2_.outputs[0], nz2.inputs["Vector"])
    nzs = mth("ADD", mth("MULTIPLY", nz.outputs["Fac"], 0.7), mth("MULTIPLY", nz2.outputs["Fac"], 0.3))      # big licks + fine flicker
    taper = mth("SUBTRACT", 1.0, mth("MULTIPLY", mth("ABSOLUTE", mth("SUBTRACT", u, 0.5)), 2.0))
    if not smoke:      # tongue field: wide and hot at the bottom centre, torn into tapered licks by the noise toward the top
        body = mth("MULTIPLY", mth("POWER", taper, 0.9), mth("POWER", mth("MAXIMUM", mth("SUBTRACT", 1.12, v), 0.0), 1.3))
        fld = mth("ADD", mth("MULTIPLY", body, 1.35), mth("MULTIPLY", mth("SUBTRACT", nzs, 0.5), mth("ADD", 0.7, mth("MULTIPLY", v, 1.1))))
        fld = mth("SUBTRACT", fld, 0.06)
        ramp = N.new("ShaderNodeValToRGB"); L.new(fld, ramp.inputs[0]); cr = ramp.color_ramp; cr.interpolation = "LINEAR"
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.0, 0.0, 0.0, 1)
        for pos, col in ((0.20, (0.30, 0.025, 0.005, 1)), (0.30, (0.85, 0.12, 0.02, 1)), (0.46, (1.0, 0.36, 0.05, 1)), (0.66, (1.0, 0.66, 0.18, 1)),
                         (0.88, (1.0, 0.92, 0.70, 1))):
            el = cr.elements.new(pos); el.color = col
        cr.elements[-1].position = 1.0; cr.elements[-1].color = (1.0, 0.96, 0.85, 1)
        alpha = mth("MINIMUM", mth("MAXIMUM", mth("MULTIPLY", mth("SUBTRACT", fld, 0.20), 7.0), 0.0), 1.0)      # soft torn edge
        em = N.new("ShaderNodeEmission"); L.new(ramp.outputs["Color"], em.inputs["Color"])
        L.new(mth("ADD", 2.5, mth("MULTIPLY", fld, 4.0)), em.inputs["Strength"])                                # hot core brighter
    else:              # smoke: heavy dark billows, only the underside catches the fire
        body = mth("MULTIPLY", mth("POWER", taper, 0.5), mth("MINIMUM", mth("MULTIPLY", v, 5.0), 1.0))
        body = mth("MULTIPLY", body, mth("SUBTRACT", 1.05, mth("POWER", v, 2.0)))
        fld = mth("ADD", mth("MULTIPLY", body, 1.15), mth("MULTIPLY", mth("SUBTRACT", nzs, 0.5), 1.5))
        alpha = mth("MULTIPLY", mth("MINIMUM", mth("MAXIMUM", mth("MULTIPLY", mth("SUBTRACT", fld, 0.32), 2.6), 0.0), 1.0), 0.96)
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; L.new(mth("MINIMUM", mth("MULTIPLY", v, 4.0), 1.0), mix.inputs[0])
        mix.inputs[6].default_value = (0.24, 0.06, 0.012, 1); mix.inputs[7].default_value = (0.006, 0.005, 0.005, 1)
        em = N.new("ShaderNodeEmission"); L.new(mix.outputs[2], em.inputs["Color"]); em.inputs["Strength"].default_value = 1.0
    tr = N.new("ShaderNodeBsdfTransparent"); ms = N.new("ShaderNodeMixShader")
    L.new(alpha, ms.inputs[0]); L.new(tr.outputs[0], ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2]); L.new(ms.outputs[0], out.inputs[0])
    return m
M_FCARD = card_mat("fire_card"); M_SCARD = card_mat("smoke_card", smoke=True)
def card_mesh():
    bm = bmesh.new(); uv = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(p) for p in ((-0.5, 0, 0), (0.5, 0, 0), (0.5, 0, 1), (-0.5, 0, 1))]
    f = bm.faces.new(vs)
    for lp, (a, b) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): lp[uv].uv = (a, b)
    me = bpy.data.meshes.new("card"); bm.to_mesh(me); bm.free(); return me
CARD = card_mesh()
def card(name, mat, loc, yaw, w, h, tilt=0.0):
    me = CARD.copy(); me.materials.append(mat); ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (RAD(tilt), 0, RAD(yaw)); ob.scale = (w, 1, h); ob.visible_shadow = False
    return ob
def fire_light(loc, energy, rng):
    ld = bpy.data.lights.new("fire_l", "POINT"); ld.shadow_soft_size = 1.2; ld.color = (1.0, 0.42, 0.12)
    lo = bpy.data.objects.new("fire_l", ld); scn.collection.objects.link(lo); lo.location = loc
    lo.visible_glossy = False                    # v3: no specular blob of the light on the road
    for f in range(1, NF + 8, 2):
        ld.energy = energy * (0.7 + 0.6 * rng.random()); ld.keyframe_insert("energy", frame=f)
def embers(loc, n, spread, rise, rng):
    for k in range(n):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rng.uniform(0.018, 0.04)); me = bpy.data.meshes.new("ember"); bm.to_mesh(me); bm.free()
        eo = bpy.data.objects.new("ember", me); scn.collection.objects.link(eo); me.materials.append(M_EMB); eo.visible_shadow = False
        ph = rng.uniform(0, 1); sp = rng.uniform(0.25, 0.5); dx = rng.uniform(-spread, spread); dy = rng.uniform(-spread, spread); wob = rng.uniform(0, 6)
        for f in range(1, NF + 8, 2):
            t = (f / FPS * sp + ph) % 1.0
            eo.location = V(loc) + V((dx * (0.4 + t) + 0.25 * math.sin(t * 9 + wob), dy * (0.4 + t) + 0.6 * t, t * rise)); eo.scale = ((1 - t) ** 0.5,) * 3
            eo.keyframe_insert("location", frame=f); eo.keyframe_insert("scale", frame=f)
def smoke(loc, yaw, w, h, rng, drift=(0.6, 0.0)):
    for k in range(2):
        ob = card("smoke", M_SCARD, V(loc) + V((0, 0, -0.3 * k)), yaw + (0 if k == 0 else 70), w * (1 - 0.15 * k), h)
        for f in (1, NF + 8):                        # rises and leans with the wind
            ob.location = V(loc) + V((drift[0] * f / FPS, drift[1] * f / FPS, 0.5 * f / FPS - 0.3 * k)); ob.keyframe_insert("location", frame=f)
def blaze(loc, face_yaw, w, h, n=4, light=4000.0, smoke_h=16.0, seed=0, wreck=False):
    """one fire: n layered flame cards fanned round face_yaw (big at the back, small hot ones in front), smoke above, embers, a flickering light."""
    rng = random.Random(seed); loc = V(loc)
    if wreck:                                        # a burnt-out car shell under a street fire
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); me = bpy.data.meshes.new("wreck"); bm.to_mesh(me); bm.free()
        wo = bpy.data.objects.new("wreck", me); scn.collection.objects.link(wo); wo.location = loc + V((0, 0, 0.45)); wo.scale = (1.7, 3.6, 0.9)
        wo.rotation_euler = (0, 0, RAD(rng.uniform(-30, 30))); bm_ = bpy.data.materials.new("wreck_m"); bm_.diffuse_color = (0.02, 0.015, 0.015, 1); me.materials.append(bm_)
    for k in range(n):
        s = 1.0 - 0.17 * k
        card("fire", M_FCARD, loc + V((rng.uniform(-0.25, 0.25) * w, rng.uniform(-0.25, 0.25) * w * 0.4, 0.02 * k)),
             face_yaw + rng.uniform(-35, 35) + (60 * k if wreck else 0), w * s * rng.uniform(0.85, 1.1), h * s * rng.uniform(0.85, 1.1), tilt=rng.uniform(-6, 6))
    smoke(loc + V((0, 0, h * 0.65)), face_yaw, w * 2.3, smoke_h, rng, drift=(rng.uniform(0.2, 0.6), rng.uniform(-0.2, 0.3)))
    embers(loc + V((0, 0, h * 0.3)), 14, w * 0.6, h * 2.5, rng)
    fire_light(loc + V((0, 0, h * 0.45)) + V((math.sin(RAD(face_yaw)), -math.cos(RAD(face_yaw)), 0)) * 1.2, light, rng)
FX_ = 7.45                                           # building fronts stand at x = +-7.6: flames lick out of their windows
WINDOWS = [(-FX_, 40.6, 3.4, 3.0, 4.6), (-FX_, 36.8, 8.0, 2.6, 4.0), (-FX_, 46.0, 4.0, 3.2, 5.0), (-FX_, 51.5, 9.5, 3.0, 4.4),
           (FX_, 37.2, 3.6, 3.0, 4.6), (FX_, 44.8, 9.0, 2.8, 4.2), (FX_, 49.5, 4.2, 3.4, 5.2), (-FX_, 31.5, 4.0, 2.8, 4.4),
           (FX_, 31.0, 8.6, 2.6, 4.0), (-FX_, 57.0, 6.0, 3.6, 6.0), (FX_, 56.0, 5.0, 3.6, 6.0)]
for i, (x, y, z, w, h) in enumerate(WINDOWS):
    blaze((x, y, z), -90 if x < 0 else 90, w, h, n=5, light=5000.0, smoke_h=18.0, seed=100 + i)
STREET = [(0.9, 53.0, 3.2, 4.6), (-3.2, 50.5, 2.4, 3.6), (3.4, 28.5, 2.6, 3.8), (-2.8, 30.0, 2.4, 3.4), (-0.5, 62.0, 4.0, 6.0)]
for i, (x, y, w, h) in enumerate(STREET):
    blaze((x, y, 0.3), 180, w, h, n=5, light=3500.0, smoke_h=14.0, seed=200 + i, wreck=True)
prefs.keyframe_new_interpolation_type = "CONSTANT"
for clk in CLOCK:                                   # the flame clock, keyed on twos (one new flame drawing every 2 frames)
    for f in range(1, NF + 8, 2):
        clk.outputs[0].default_value = (f - 1) / FPS; clk.outputs[0].keyframe_insert("default_value", frame=f)

# ---- impact: spit / blood drops from the mouth, a small local shock ring round the face, a dust ring at his feet
prefs.keyframe_new_interpolation_type = "CONSTANT"
M_BLOOD, _ = emissive("blood", (0.45, 0.01, 0.02), 1.0); M_SPIT, _ = emissive("spit", (0.9, 0.95, 1.0), 2.0)
MOUTH = FACE - hup * 0.07 + hfw * 0.04
def warp(t):                                     # slow motion inside the held contact shot (2.1-2.5), real speed after
    if t <= T_HIT: return 0.0
    return min(t, 2.5) - T_HIT if t <= 2.5 else 0.4 + (t - 2.5) * 3.0
rng = random.Random(3)
for k in range(40):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rng.uniform(0.008, 0.024)); me = bpy.data.meshes.new("drop"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("drop", me); scn.collection.objects.link(ob); me.materials.append(M_BLOOD if k < 32 else M_SPIT); ob.visible_shadow = False
    vel = V((rng.uniform(0.3, 1.4), rng.uniform(0.8, 2.6), rng.uniform(0.2, 1.6))) * (0.6 if k < 32 else 0.9)
    ob.scale = (1, 1, 1)
    for f in FR_ALL:
        t = T_(f)
        if t < T_SNAP: ob.hide_render = True; ob.location = MOUTH
        else:
            ob.hide_render = False; tw = warp(t) - warp(T_SNAP); ob.location = MOUTH + vel * tw + V((0, 0, -4.9 * tw * tw))
            ob.scale = (1, 1 + 1.5 * min(1, tw * 6), 1)
            if ob.location.z < 0.01: ob.hide_render = True
        ob.keyframe_insert("location", frame=f); ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("scale", frame=f)
M_RING, E_RING = emissive("shock", (1.0, 1.0, 1.0), 3.0)
def ring(name, loc, rot, r0, r1, t0, t1, thick):
    bm = bmesh.new(); bmesh.ops.create_circle(bm, segments=40, radius=1.0); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob); me.materials.append(M_RING); ob.visible_shadow = False
    sk = ob.modifiers.new("skin", "WIREFRAME"); sk.thickness = thick; sk.use_relative_offset = False
    ob.location = loc; ob.rotation_euler = rot
    for f in FR_ALL:
        t = T_(f); k = (t - t0) / (t1 - t0); ob.hide_render = not (0 <= k <= 1)
        r = r0 + (r1 - r0) * (1 - (1 - min(max(k, 0), 1)) ** 2); ob.scale = (r, r, r)
        ob.keyframe_insert("scale", frame=f); ob.keyframe_insert("hide_render", frame=f)
    return ob
ring("shock_face", FACE + V((0.05, 0, 0)), (0, RAD(90), 0), 0.08, 0.55, T_HIT + 0.01, T_SNAP + 0.1, 0.012)
# v3: no dust ring on the road (it read as a bright blob in the aftermath); dust is drawn in post

# ---- cameras: v3 = manhwa PANELS. Every shot is a fixed camera (no move, no shake, no animated roll); a fixed diagonal
# (roll) is allowed as a composition. Each job: shot name, source frames, camera (loc, look, lens, roll deg, f-stop).
cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.02; cd.clip_end = 3000
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam; cam.rotation_mode = "QUATERNION"
cd.dof.use_dof = True
def eye_c(o): return o.matrix_world @ (sum((V(c) for c in o.bound_box), V()) / 8)      # eyeball centre (origins sit on the head bone)
def at(f): scn.frame_set(f); bpy.context.view_layer.update()
def eyes_of(g): return [eye_c(next(o for o in g.children_recursive if o.name.split(".")[0] == n and not o.name.endswith("_white"))) for n in ("eye_l", "eye_r")]
def place(c):
    loc, look, lens, roll, fst = c
    q = (V(look) - V(loc)).to_track_quat("-Z", "Y") @ Q((0, 0, 1), RAD(roll))
    cam.location = loc; cam.rotation_quaternion = q; cd.lens = lens; cd.dof.aperture_fstop = fst; cd.dof.focus_distance = max(0.2, (V(look) - V(loc)).length)
JOBS = {}
# A low wide: the hero in his stance, the ring behind, the attacker on the right (held)
JOBS["wide"] = (list(range(1, 17, 2)), (HC + V((0.72, -3.5, 0.36)), HC + V((0.6, 0.0, 1.30)), 22, 0, 9))
# B the enemy's furious face, low, slightly under the chin, fixed diagonal
at(F(1.3)); _el, _er = eyes_of(att); EM = (_el + _er) / 2; _hp, _fw, _up, _lt = head_frame(att)
JOBS["rage"] = (list(range(F(1.10), F(1.56), 2)), (EM + _fw * 0.62 + _lt * 0.16 - _up * 0.10, EM - _up * 0.035, 55, 9, 2.8))
# D the haymaker from behind the hero's left shoulder: the right arm winds up on the left of frame and sweeps over his head
JOBS["swing"] = ([53, 55, 57, 59, 61, 63], (HC + V((-0.75, 1.45, 1.30)), HC + V((1.30, 0.05, 1.45)), 26, -6, 6))
# E1 forced perspective: beside the enemy's cheek, looking back down the fist path (the fist huge, the hero behind it)
at(63); _e63 = sum(eyes_of(att), V()) / 2; _f63 = head_frame(att)[1]; at(F(1.0))
JOBS["p_fist"] = ([63], (_e63 + _f63 * 0.14, HC + V((0.05, -0.05, 1.50)), 18, 14, 11))   # his eyes: the fist flies at the lens
# E2 the face caving round the knuckles
JOBS["p_face"] = ([65, 67], (FACE + hfw * 0.38 + hlt * 0.30 + hup * 0.06, FACE + hup * 0.02, 40, -12, 4))
# E3 the body launched, seen from low with the frame turned past upside-down
at(F(2.40)); _ah = head_frame(att)[0]; _bc = _ah - V((0, 0, 0.45))
JOBS["p_flip"] = ([72, 74], (V((_bc.x + 0.9, _bc.y - 1.9, max(0.18, _bc.z - 0.95))), _bc, 26, 158, 5.6))
# F BAM: low behind the hero's right side, the punching arm a huge diagonal into the enemy's face (feather burst in post)
JOBS["bam"] = ([66, 68, 70, 72], (HC + V((0.02, -0.62, 1.02)), FACE + V((0.10, 0.0, 0.05)), 19, -16, 8))
# G the tumble: from the road, the man flying diagonally across a burning sky, blood drops in the air
JOBS["tumble"] = ([77, 79, 81, 82], (HC + V((3.5, 0.2, 0.22)), HC + V((1.5, 0.6, 0.95)), 22, 32, 6))
# H high aftermath: the man flat on the road, the ring stepping back, the hero still in his punch
JOBS["after"] = ([81, 83, 85, 87, 89], (HC + V((0.9, -2.9, 4.3)), HC + V((1.2, 0.5, 0.25)), 20, 0, 11))
cd.dof.use_dof = True
if os.environ.get("CHECK"):
    for f in (F(1.75), F(1.9), F(1.97), F(2.03), F_HIT, F(2.3), F(2.5), F(2.62), F(2.75)):
        at(f)
        print("CHECK", f, "fistR", tuple(round(c, 2) for c in bone_w(hero, "wrist.R", "tail")), "att head", tuple(round(c, 2) for c in head_frame(att)[0]),
              "hero feet", [tuple(round(c, 2) for c in bone_w(hero, f"foot.{s}")) for s in "LR"], "att feet", [round(bone_w(att, f"foot.{s}").z, 2) for s in "LR"])

# ------------------------------------------------------------------ render
from bpy_extras.object_utils import world_to_camera_view as w2c
C.render_settings(SCALE, SAMPLES)
scn.render.fps = FPS; scn.frame_start, scn.frame_end = 1, NF
scn.render.image_settings.file_format = "PNG"
OUT = os.path.join(HERE, "frames_s1v3"); os.makedirs(OUT, exist_ok=True)
import json
def proj(f):
    """screen positions (0..1, y down) of what the 2D post draws on: contact cheek, mouth, enemy eyes + head, fist, hero eyes."""
    hp_, fw, up, lt = head_frame(att); pts = {"face": hp_ + up * 0.085 + fw * 0.095 + lt * 0.03, "mouth": hp_ + up * 0.015 + fw * 0.135,
                                              "ahead": hp_, "fist": bone_w(hero, "wrist.R", "tail")}
    ae = eyes_of(att); he = eyes_of(hero); pts.update(ae_l=ae[0], ae_r=ae[1], he_l=he[0], he_r=he[1], att_hip=bone_w(att, "spine05"))
    out = {}
    for k, p in pts.items():
        c = w2c(scn, cam, p); out[k] = (round(c.x, 4), round(1 - c.y, 4), round(c.z, 3))
    return out
ONLY = [x for x in os.environ.get("ONLY", "").split(",") if x]
todo = [(n, f) for n, (fs, _) in JOBS.items() if not ONLY or n in ONLY for f in fs]
stills = os.environ.get("STILLS")
if stills: todo = [(x.split(":")[0], int(x.split(":")[1])) for x in stills.split(",")]
pj = os.path.join(OUT, "proj.json"); P_ = json.load(open(pj)) if os.path.exists(pj) else {}
for n, f in todo:
    at(f); place(JOBS[n][1]); bpy.context.view_layer.update(); P_[f"{n}_{f:04d}"] = proj(f)
json.dump(P_, open(pj, "w"), indent=0)
if os.environ.get("NORENDER"): print("built only", f"{time.time() - T0:.0f}s rss {rss():.2f} GB"); sys.exit(0)
if stills:
    sd = os.path.join(HERE, "stills_s1v3"); os.makedirs(sd, exist_ok=True)
    for n, f in todo:
        at(f); place(JOBS[n][1]); scn.render.filepath = os.path.join(sd, f"{n}_{f:04d}.png")
        t1 = time.time(); bpy.ops.render.render(write_still=True); print(f"STILL {n} {f} {time.time() - t1:.0f}s rss {rss():.2f} GB", flush=True)
    sys.exit(0)
done = sorted((os.path.getmtime(os.path.join(OUT, x)), x) for x in os.listdir(OUT) if x.endswith(".png"))
if done and not os.environ.get("KEEPLAST"):            # the newest frame may be half-written by a killed run: redo it
    os.remove(os.path.join(OUT, done[-1][1])); print("removed last frame", done[-1][1])
for n, f in todo:
    p = os.path.join(OUT, f"{n}_{f:04d}.png")
    if os.path.exists(p): continue
    at(f); place(JOBS[n][1]); scn.render.filepath = p; t1 = time.time(); bpy.ops.render.render(write_still=True)
    print(f"FRAME {n} {f} {time.time() - t1:.0f}s peak rss {rss():.2f} GB", flush=True)
print("DONE", f"{time.time() - T0:.0f}s")
