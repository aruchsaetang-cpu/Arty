"""Kuro Oni ep 1, REAL SCENE 1 v4: a CLEAN plain 3D render. No white eyes, normal even light, no 2D manhwa effects, no audio.
Same story as v2/v3: a ring of street fighters round the hero on a burning street (no rain). ONE enemy lunges with a right
haymaker; the hero ducks under it and drives a gyaku-zuki into his face; he snaps back, is launched and falls; the others flinch.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/scene1_v4.py [scale%] [first] [last]
Renders PNGs to shorts/kuro_oni/frames_s1v4/f####.png (existing frames skipped, so it resumes): odd frames (on twos) + every
frame of the punch. env: SAMPLES (12), STILLS="t1,t2" -> stills_s1v4/, NORENDER=1 build only, CHECK=1 contact distances.
Five level, steady cuts: 0-0.8 low wide | 0.8-1.35 over the attacker's shoulder | 1.35-1.75 hero medium close-up |
1.75-2.5 side-on, push-in to the contact | 2.5-3.0 high aftermath. Post: scene1_compose_v4.py (upscale, subtitle, silent mp4)."""
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
THIT = [0.95, 1.60, 2.25]                   # fist meets face: enemy A, B, C (0.65 s apart)
FHIT = [F(t) for t in THIT]
ANG = [0.0, 180.0, -55.0]                   # where each enemy stands round the hero (deg, CCW from +x)
FACING = [90.0, -90.0, 35.0]                # hero hip facing toward each (0 = -y, 90 = +x)
SNAP = 0.13                                 # hit-stop length after contact
F_ONES = set(); [F_ONES.update(range(F(t - 0.25), F(t) + 1)) for t in THIT]    # the punches on ones; everything else on twos
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
NEAR = [(3.4, 106), (3.55, 134), (3.6, 72), (3.4, -126)]   # (radius, angle deg) of the full-rig ring men
NEAR_ST = [2, 3, 4, 5]                                                    # FIGHTERS styles; the attacker is FIGHTER_7 (red jacket)
TEMP_ST = [6, 8, 9, 10, 11]                                                    # extra looks, baked to static men then deleted
names = ["HERO", "FIGHTER_7", "FIGHTER_0", "FIGHTER_1"] + [f"FIGHTER_{i}" for i in NEAR_ST] + [f"FIGHTER_{i}" for i in TEMP_ST]
locs = {n: (HC.x + 30 + 2 * i, HC.y + 30, 0) for i, n in enumerate(names)}
arms_ = CK.build_cast(P, names, locs=locs, hero_cloak=True, heading=0.0)
hero = arms_["HERO"]; ATT = [arms_["FIGHTER_7"], arms_["FIGHTER_0"], arms_["FIGHTER_1"]]; att = ATT[0]
near = [arms_[f"FIGHTER_{i}"] for i in NEAR_ST]; temps = [arms_[f"FIGHTER_{i}"] for i in TEMP_ST]
for g in arms_.values(): ch.grip(g, "L"); ch.grip(g, "R")
print(f"cast built {time.time() - T0:.0f}s rss {rss():.2f} GB", flush=True)
for g in ATT + near + temps: print(g.name, [c.name for c in g.children_recursive if c.type == "MESH"][:30])
FR_ALL = list(range(1, NF + 7))

def heading_to(frm, to):
    d = V(to) - V(frm); return math.degrees(math.atan2(d.x, -d.y))

def rot2(x, y, phi): c, s_ = math.cos(RAD(phi)), math.sin(RAD(phi)); return (x * c - y * s_, x * s_ + y * c)
_fa = stance_feet(1.95, 0.0, -118, front=(0.12, -0.36), back=(-0.14, 0.30), fy=(26, -22))
# template of one enemy (enemy A, hero at the origin facing +x), times relative to the contact; each enemy is this rotated by ANG
TPL = [
    (-0.48, dict(x=1.92, twist=20, fistR=("c", GUARD_R), footL=_fa[0]), "io"),
    (-0.30, dict(x=1.70, yaw=-112, twist=-22, lean=10, drop=0.12, fistR=("c", (-0.50, 0.22, 1.50)), hy=18), "io"),     # wind up: right fist back
    (-0.26, dict(footL=(1.30, -0.15, -95, 0.10), footR=_fa[1]), "io"),
    (-0.22, dict(fistR=("c", (0.05, -0.40, 1.80))), "io"),
    (-0.20, dict(footL=(0.92, -0.14, -96, 0.0)), "in"),                                                              # front foot lands
    (-0.15, dict(x=1.30, y=-0.02, yaw=-96, twist=34, lean=18, drop=0.14, hy=0, hp=8, fistR=("c", (0.20, -0.62, 1.72)), footR=(1.92, 0.20, -128, 0.03)), "io"),
    (-0.06, dict(x=1.05, y=-0.02, yaw=-88, twist=40, lean=22, side=4, drop=0.16, hp=12, fistR=("c", (0.28, -0.80, 1.50)), fistL=("c", (0.16, -0.22, 1.22)),
                 footR=(1.62, 0.18, -120, 0.0)), "io"),
    (0.0, dict(x=1.04, twist=40, lean=22, hp=12, hy=0, hr=0, hs=(1.0, 1.0, 1.0), fistR=("c", (0.28, -0.82, 1.48))), "io"),
    (0.02, dict(hs=(0.78, 0.93, 1.12)), "snap"),                                                                     # face caves in on contact
    (SNAP, dict(x=1.05, twist=40, lean=22, hp=12, hy=-4, hr=-3, hs=(0.76, 0.93, 1.13), yaw=-88, drop=0.16, side=4), "io"),   # hit-stop
    (SNAP + 0.09, dict(hy=-58, hr=-30, hp=-26, x=1.14, tilt=(-4.0, 0.4, 0.0)), "snap"),                               # head snaps to his right
    (0.40, dict(x=1.46, y=0.04, yaw=-122, twist=-28, lean=-12, side=-12, drop=0.02, tilt=(-22.0, 2.2, 0.0), hs=(0.84, 0.95, 1.08),
                fistR=("c", (-0.58, 0.12, 1.46)), fistL=("c", (0.48, -0.18, 1.12)), hy=-50, hr=-28, hp=-30), "out"),   # launched
    (0.52, dict(x=1.64, y=0.16, yaw=-150, twist=-30, drop=-0.06, tilt=(-52.0, 5.2, 0.0), lean=-16, side=-6,
                fistR=("c", (-0.50, -0.32, 1.80)), fistL=("c", (0.50, -0.25, 1.75)), hp=-24), "lin"),
    (0.63, dict(x=1.72, y=0.30, tilt=(-77.6, 7.8, 0.0), drop=0.36, lean=0, hs=(1.0, 1.0, 1.0), hy=-30, hr=-10, hp=20), "in"),   # slams down
    (0.69, dict(tilt=(-70.0, 7.0, 0.0)), "out"),
    (0.78, dict(tilt=(-78.6, 7.9, 0.0), fistR=("c", (-0.42, -0.45, 1.30)), fistL=("c", (0.40, -0.40, 1.25))), "in"),
    (1.10, dict(tilt=(-78.6, 7.9, 0.0)), "io"),
]
def enemy(g, T, phi, off=(0.0, 0.0)):
    R_ = Rig(g); last = dict(x=1.95, y=0.0)
    def xyz(f): x_, y_ = rot2(f[0], f[1], phi); return (x_ + off[0], y_ + off[1], f[2] + phi) + tuple(f[3:])
    x0, y0 = rot2(1.95, 0.0, phi); x0 += off[0]; y0 += off[1]; fa0 = [xyz(f) for f in _fa]
    R_.key(0.0, x=x0, y=y0, yaw=-118 + phi, drop=0.10, twist=20, lean=6, hy=8, footL=fa0[0], footR=fa0[1], fistL=("c", GUARD_L), fistR=("c", GUARD_R))
    for k in range(1, 6):
        if 0.55 * k < T - 0.55: R_.key(0.55 * k, drop=0.13 if k % 2 else 0.09)
    for tr, kw, ease in TPL:
        kw = dict(kw)
        if "x" in kw or "y" in kw:
            last.update({k: kw[k] for k in ("x", "y") if k in kw}); kw["x"], kw["y"] = (v_ + o_ for v_, o_ in zip(rot2(last["x"], last["y"], phi), off))
        if "yaw" in kw: kw["yaw"] += phi
        for k in ("footL", "footR"):
            if k in kw: kw[k] = xyz(kw[k])
        if "tilt" in kw:
            tx, ty = rot2(kw["tilt"][0], kw["tilt"][1], phi); kw["tilt"] = (tx, ty, 0.0)
        R_.key(T + tr, ease=ease, **kw)
    R_.finalize(); R_.bake(FR_ALL); on_ground(g); return R_
OFFS = [(0.0, 0.0), (0.08, 0.0), (0.0, 0.0)]          # the hero drifts 8 cm into each punch: the next man stands where he can be reached
for g_, T_h, ph, of_ in zip(ATT, THIT, ANG, OFFS): enemy(g_, T_h, ph, of_)
def bone_w(g, n, at="head"):
    pb = g.pose.bones[n]; return g.matrix_world @ (pb.head if at == "head" else pb.tail)
def head_frame(g):
    """-> head joint (world), face forward, up, his left: the rest-pose body axes carried by the head bone's pose rotation."""
    pb = g.pose.bones["head"]; Rr = g.matrix_world.to_3x3().normalized() @ pb.matrix.to_3x3() @ g.data.bones["head"].matrix_local.to_3x3().inverted()
    return (g.matrix_world @ pb.head), (Rr @ V((0, -1, 0))).normalized(), (Rr @ V((0, 0, 1))).normalized(), (Rr @ V((1, 0, 0))).normalized()
FACES = []                                   # where each fist must land: the enemy's left cheek at the contact frame
for g_, fh in zip(ATT, FHIT):
    scn.frame_set(fh); bpy.context.view_layer.update(); hp_, hfw, hup, hlt = head_frame(g_)
    FACES.append(dict(P=hp_ + hup * 0.085 + hfw * 0.095 + hlt * 0.03, up=hup, fw=hfw, lt=hlt, head=hp_))
    print("enemy head", g_.name, tuple(round(c, 2) for c in hp_), flush=True)
FACE = FACES[0]["P"]; hup, hfw, hlt = FACES[0]["up"], FACES[0]["fw"], FACES[0]["lt"]

# ---- the hero: HANDS IN HIS POCKETS. Relaxed slouch, small breathing; he slips each swing with a loose body turn and only the
# punching hand leaves the pocket (hip-led reverse punch: heel pivot -> hips -> spine -> shoulder -> fist), then goes back in.
H = Rig(hero)
HC_ = HC
PUNCH = []
for fc, ph in zip(FACES, ANG):
    u = V((math.cos(RAD(ph)), math.sin(RAD(ph)), 0)); PUNCH.append(fc["P"] - u * 0.04)
MV.pocket_idle(H, 0.0, THIT[0] - 0.35, 0.0, 0.0, FACING[0], seed=3)
for i, (T_h, f_) in enumerate(zip(THIT, FACING)):
    if i: MV.turn_to(H, THIT[i - 1] + 0.08, 0.17, f_)
    MV.slip_turn(H, T_h - 0.35, 0.15, hold=0.07, pocket=True)              # loose duck + hip turn under the swing, hands stay in
    MV.gyaku_zuki(H, T_h - 0.13, 0.13, PUNCH[i], pocket=True)
MV.pocket_idle(H, THIT[-1] + 0.5, THIT[-1] + 0.9, H.ctx["x"], H.ctx["y"], FACING[-1], seed=4) if False else None
H.finalize()
for it in range(7):                         # close the loop: measure each fist against its cheek, correct the targets, re-key
    hero.animation_data_clear(); H.bake(FR_ALL); worst = 0.0
    for i, T_h in enumerate(THIT):
        scn.frame_set(F(T_h)); bpy.context.view_layer.update()
        fist = bone_w(hero, "wrist.R", "tail"); err = PUNCH[i] - fist; worst = max(worst, err.length)
        print(f"hit {i} fist {tuple(round(c, 3) for c in fist)} target {tuple(round(c, 3) for c in PUNCH[i])} err {err.length * 100:.1f} cm", flush=True)
        for t, d, _ in H.keys:
            if "fistR" in d and T_h - 1e-6 <= t < T_h + 0.2 and d["fistR"][0] == "w": d["fistR"] = ("w", tuple(V(d["fistR"][1]) + err))
    if worst < 0.015: break

# ---- cloak follow-through: the back panel (rigid, on spine01) hinges at its top edge. One whip pulse per punch.
def swing_deg(t):
    tot = 0.0
    for T_h in THIT:
        ks = [(-0.30, 0.0), (-0.13, -6.0), (0.0, 24.0), (0.14, -18.0), (0.30, 9.0), (0.46, -4.0), (0.65, 1.5), (0.85, 0.0)]
        for (t0, a0), (t1, a1) in zip(ks, ks[1:]):
            if T_h + t0 <= t <= T_h + t1: tot += a0 + (a1 - a0) * ez((t - T_h - t0) / (t1 - t0), "io")
    return tot
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
    t0 = THIT[0] + 0.12 + rng.uniform(0, 0.08)
    R_.key(t0, x=x, y=y, lean=5, hp=0, drop=0.10, twist=22, fistL=("c", GUARD_L), fistR=("c", GUARD_R), footL=ff[0], footR=ff[1])
    fb = stance_feet(x + out.x, y + out.y, yaw)
    R_.key(t0 + 0.16, lean=-10, hp=-10, drop=0.05, fistL=("c", (0.10, -0.28, 1.62)), fistR=("c", (-0.12, -0.22, 1.60)), ease="snap")
    R_.key(t0 + 0.30, footR=(fb[1][0], fb[1][1], fb[1][2], 0.0))
    R_.key(t0 + 0.22, footR=(ff[1][0] + out.x * 0.5, ff[1][1] + out.y * 0.5, ff[1][2], 0.07))
    R_.key(t0 + 0.36, x=x + out.x, y=y + out.y, ease="io")
    R_.key(t0 + 0.34, footL=(ff[0][0] + out.x * 0.5, ff[0][1] + out.y * 0.5, ff[0][2], 0.06))
    R_.key(t0 + 0.44, footL=fb[0], lean=-6, hp=-6, drop=0.10)
    R_.finalize(); R_.bake(FR_ALL); NR.append(R_)

# ---- lookdev (v4): hero and enemies get the SAME glow + warm fire rim, so everyone reads clearly
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
LIT = dict(glow=float(os.environ.get("GLOW", 1.12)), rim=(1.0, 0.55, 0.2, 1.0), blend=0.30)     # v4: everyone lit the same way
brighten(hero, LIT["glow"], LIT["rim"], LIT["blend"], extra=[pan] if _cl else [])
for g in ATT + near + temps: brighten(g, LIT["glow"], LIT["rim"], LIT["blend"])
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
CAMS_XY = [V((0.7, -3.5)), V((0.6, -3.5)), V((-2.7, -1.0)), V((0.14, 1.4)), V((0.0, -3.9)), V((0.9, -2.9))]
BACK = []; rng = random.Random(9)
occupied = [V((r * math.cos(RAD(a)), r * math.sin(RAD(a)))) for r, a in NEAR] + [V((1.95, 0)), V((0, 0)), V((-1.95, 0)), V((1.12, -1.6)), V((1.7, 1.0)), V((-1.7, -1.0)), V((1.4, -0.8)), V((-1.1, 0.0))]
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
    t0 = THIT[0] + 0.14 + 0.012 * (p - V((1.15, 0))).length + rng.uniform(0, 0.06); f0 = F(t0)
    e.keyframe_insert("location", frame=f0); e.keyframe_insert("rotation_euler", frame=f0)
    u = V((p.x - 1.0, p.y, 0)).normalized(); back = rng.uniform(0.15, 0.35); tb = RAD(rng.uniform(5, 10))
    e.location = HC + V((p.x + u.x * back, p.y + u.y * back, bz * sc)); e.rotation_euler = (u.y * tb, -u.x * tb, RAD(yaw))  # lean away
    e.keyframe_insert("location", frame=f0 + 10); e.keyframe_insert("rotation_euler", frame=f0 + 10)
print("back-row men", len(BACK), flush=True)

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
RIGS = set([hero] + ATT + near)
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

# ---- impact: PUNCH MARK + a few spit drops per hit. The mark is a soft red-purple bruise with a swollen rim (two flat ellipsoids
# along the knuckle line) parented to the enemy's head bone: it appears at contact, swells over 3 frames and darkens red -> purple.
prefs.keyframe_new_interpolation_type = "CONSTANT"
M_SPIT, _ = emissive("spit", (0.9, 0.95, 1.0), 2.0)
def bruise_mat(name, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord"); vm = N.new("ShaderNodeVectorMath"); vm.operation = "LENGTH"
    L.new(tc.outputs["Object"], vm.inputs[0])
    rp = N.new("ShaderNodeMapRange"); rp.inputs[1].default_value = 0.35; rp.inputs[2].default_value = 1.0; rp.inputs[3].default_value = 1.0; rp.inputs[4].default_value = 0.0
    L.new(vm.outputs["Value"], rp.inputs[0]); rp.clamp = True
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6.0; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    al = N.new("ShaderNodeMath"); al.operation = "MULTIPLY"; L.new(rp.outputs[0], al.inputs[0]); al.inputs[1].default_value = 0.85
    em = N.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    rgb = N.new("ShaderNodeRGB"); L.new(rgb.outputs[0], em.inputs["Color"])
    tr = N.new("ShaderNodeBsdfTransparent"); ms = N.new("ShaderNodeMixShader")
    L.new(al.outputs[0], ms.inputs[0]); L.new(tr.outputs[0], ms.inputs[1]); L.new(em.outputs[0], ms.inputs[2]); L.new(ms.outputs[0], out.inputs[0])
    return m, rgb
def bruise(g, fc, T_h, cheek_dir):
    pb = g.pose.bones["head"]; scn.frame_set(F(T_h)); bpy.context.view_layer.update()
    ks = []
    for k, (dx, dy, dz, sx, sy, sz) in enumerate(((0.0, 0.0, 0.0, 0.060, 0.030, 0.046), (0.0, 0.02, -0.035, 0.038, 0.030, 0.030))):
        m, rgb = bruise_mat(f"bruise{k}_{g.name}", 1.0)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0); me = bpy.data.meshes.new("bruise"); bm.to_mesh(me); bm.free(); me.materials.append(m)
        ob = bpy.data.objects.new(f"bruise_{g.name}_{k}", me); scn.collection.objects.link(ob); ob.visible_shadow = False
        ob.parent = g; ob.parent_type = "BONE"; ob.parent_bone = "head"
        ob.matrix_basis = Matrix.Identity(4); bpy.context.view_layer.update(); Pm = ob.matrix_world.copy(); ob.matrix_parent_inverse = Pm.inverted()
        z = fc["up"] * dz + fc["lt"] * dx + fc["fw"] * dy
        zz = fc["fw"].cross(fc["up"]).normalized() if False else fc["lt"]
        Rm = Matrix((zz, fc["fw"], fc["up"])).transposed() if False else Matrix(((zz.x, fc["fw"].x, fc["up"].x), (zz.y, fc["fw"].y, fc["up"].y), (zz.z, fc["fw"].z, fc["up"].z)))
        ob.matrix_world = Matrix.Translation(fc["P"] - fc["fw"] * 0.012 + z) @ Rm.to_4x4() @ Matrix.Diagonal((sx, sy, sz, 1.0))
        base = ob.matrix_basis.copy(); loc0, rot0, sc0 = base.decompose(); ob.rotation_mode = "QUATERNION"
        for f in FR_ALL:
            t = T_(f); vis = t >= T_h + 0.005
            ob.hide_render = not vis
            kk = min(1.0, max(0.0, (t - T_h) / 0.10)); sw = 0.55 + 0.45 * kk if vis else 0.0       # swells over 3 frames
            ob.scale = tuple(c * sw for c in sc0); ob.location = loc0; ob.rotation_quaternion = rot0
            d = min(1.0, max(0.0, (t - T_h) / 0.9))                                                  # red -> purple
            rgb.outputs[0].default_value = (0.50 - 0.22 * d, 0.07, 0.07 + 0.14 * d, 1.0)
            ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("scale", frame=f); rgb.outputs[0].keyframe_insert("default_value", frame=f)
        ks.append(ob)
    return ks
rng = random.Random(3)
def warp(t, T_h):                                 # slight slow motion inside the held contact, real speed after
    return 0.0 if t <= T_h else min(t - T_h, 0.4) + max(0.0, t - T_h - 0.4) * 3.0
for g_, fc, T_h, ph in zip(ATT, FACES, THIT, ANG):
    bruise(g_, fc, T_h, None)
    hp_h, hfw_h, hup_h, hlt_h = fc["head"], fc["fw"], fc["up"], fc["lt"]; MOUTH = fc["P"] - hup_h * 0.07 + hfw_h * 0.04
    for k in range(6):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rng.uniform(0.008, 0.016)); me = bpy.data.meshes.new("drop"); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("drop", me); scn.collection.objects.link(ob); me.materials.append(M_SPIT); ob.visible_shadow = False
        ux, uy = math.cos(RAD(ph)), math.sin(RAD(ph))
        vel = V((rng.uniform(0.2, 1.0) * ux - rng.uniform(0.8, 1.8) * uy, rng.uniform(0.2, 1.0) * uy + rng.uniform(0.8, 1.8) * ux, rng.uniform(0.2, 1.2))) * 0.7
        for f in FR_ALL:
            t = T_(f)
            if t < T_h + SNAP: ob.hide_render = True; ob.location = MOUTH
            else:
                ob.hide_render = False; tw = warp(t, T_h) - warp(T_h + SNAP, T_h); ob.location = MOUTH + vel * tw + V((0, 0, -4.9 * tw * tw))
                if ob.location.z < 0.01: ob.hide_render = True
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("hide_render", frame=f)

# ---- camera: five clean cuts, level horizon (no roll), no shake; one slow move per shot, a push before the hit
cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.03; cd.clip_end = 3000
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam; cam.rotation_mode = "QUATERNION"
cd.dof.use_dof = True
def lerp(a, b, k): return a + (b - a) * k
def vl(a, b, k): return V(a).lerp(V(b), k)
def eye_c(o): return o.matrix_world @ (sum((V(c) for c in o.bound_box), V()) / 8)      # eyeball centre (origins sit on the head bone)
def cp(i): return FACES[i]["P"] + (V((math.cos(RAD(ANG[i])), math.sin(RAD(ANG[i])), 0)) * -0.12)       # frame centre at a hit: between fist and face
CP1, CP2, CP3 = cp(0), cp(1), cp(2)
SHOTS = []
def shot(t0, t1, fn, ease="io"): SHOTS.append((t0, t1, fn, ease))
# 1 low wide: the hero relaxed, hands in his pockets, the ring behind, enemy A on the right; slow push-in
shot(0.0, 0.60, lambda k: (vl(HC + V((0.75, -3.7, 0.42)), HC + V((0.7, -3.3, 0.46)), k), HC + V((0.6, 0.0, 1.25)), 22, 9))
# 2 hit 1, pure side-on: both full bodies, a push to fist + face, held through the contact, a slow drift back
def s2(k):
    t = 0.60 + k * 0.70
    wl, wc = HC + V((0.55, -3.5, 1.15)), HC + V((0.55, 0.0, 1.10))
    nl, nc = V((CP1.x - 0.38, HC.y - 2.15, CP1.z)), V((CP1.x - 0.33, HC.y, CP1.z - 0.04))
    a0, a1, a2 = THIT[0] - 0.20, THIT[0] - 0.07, THIT[0] + 0.15
    if t < a0: return wl, wc, 30, 8
    if t < a1: u = ez((t - a0) / (a1 - a0), "in"); return vl(wl, nl, u), vl(wc, nc, u), lerp(30, 32, u), 8
    if t < a2: return nl, nc, 32, 8
    u = ez((t - a2) / 0.25, "io"); return vl(nl, nl + V((0.25, -0.6, -0.15)), u), vl(nc, nc + V((0.25, 0, -0.2)), u), 32, 8
shot(0.60, 1.30, s2, "lin")
# 3 hit 2, over enemy B's shoulder (he comes from the left): fist and his face in profile, the hero behind
shot(1.30, 1.95, lambda k: (vl(V((CP2.x - 1.50, HC.y - 1.05, 1.62)), V((CP2.x - 1.30, HC.y - 1.0, 1.60)), k), V((CP2.x + 0.60, HC.y, 1.42)), 36, 5))
# 4 hit 3, low behind the hero's shoulder looking up at enemy C's face
shot(1.95, 2.65, lambda k: (vl(V((0.14, HC.y + 1.40, 0.55)), V((0.10, HC.y + 1.28, 0.58)), k), V((CP3.x, CP3.y, 1.45)), 32, 5))
# 5 high wide aftermath: three men down, the ring stepping back, the hero hands back in his pockets
shot(2.65, 3.01, lambda k: (vl(HC + V((0.0, -3.9, 3.0)), HC + V((0.0, -4.1, 3.3)), k), HC + V((0.0, 0.0, 0.5)), 20, 11))
def key_cam(f):
    t = T_(f); s = next((s for s in SHOTS if s[0] <= t < s[1]), SHOTS[-1])
    k = ez((t - s[0]) / (s[1] - s[0]), s[3]); loc, look, lens, fst = s[2](k)
    q = (V(look) - V(loc)).to_track_quat("-Z", "Y")             # level: no roll, no wobble
    cam.location = loc; cam.rotation_quaternion = q; cd.lens = lens; cd.dof.aperture_fstop = fst; cd.dof.focus_distance = max(0.2, (V(look) - V(loc)).length)
    cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f)
    cd.keyframe_insert("lens", frame=f); cd.dof.keyframe_insert("aperture_fstop", frame=f); cd.dof.keyframe_insert("focus_distance", frame=f)
prefs.keyframe_new_interpolation_type = "CONSTANT"
for f in FR_ALL: key_cam(f)
if os.environ.get("CHECK"):
    for f in FHIT + [F(1.2), F(2.9)]:
        scn.frame_set(f); bpy.context.view_layer.update()
        print("CHECK", f, "fistR", tuple(round(c, 2) for c in bone_w(hero, "wrist.R", "tail")), "att head", tuple(round(c, 2) for c in head_frame(att)[0]))

# ------------------------------------------------------------------ render
C.render_settings(SCALE, SAMPLES)
scn.view_settings.look = "None"; scn.view_settings.exposure = float(os.environ.get("EXPO", 0.0))      # v4: normal exposure
scn.render.fps = FPS; scn.frame_start, scn.frame_end = 1, NF
scn.render.image_settings.file_format = "PNG"
OUT = os.path.join(HERE, "frames_s1v4"); os.makedirs(OUT, exist_ok=True)
if os.environ.get("NORENDER"): print("built only", f"{time.time() - T0:.0f}s rss {rss():.2f} GB"); sys.exit(0)
stills = os.environ.get("STILLS")
if stills:
    sd = os.environ.get("STILLDIR") or os.path.join(HERE, "stills_s1v4"); os.makedirs(sd, exist_ok=True)
    for s_ in stills.split(","):
        f = F(float(s_)); scn.frame_set(f); scn.render.filepath = os.path.join(sd, f"t{float(s_):05.2f}.png")
        t1 = time.time(); bpy.ops.render.render(write_still=True); print(f"STILL t={s_} f={f} {time.time() - t1:.0f}s rss {rss():.2f} GB", flush=True)
    sys.exit(0)
done = sorted(int(n[1:5]) for n in os.listdir(OUT) if n.startswith("f") and n.endswith(".png"))
if done and not os.environ.get("KEEPLAST"):            # the newest frame may be half-written by a killed run: redo it
    os.remove(os.path.join(OUT, f"f{done[-1]:04d}.png")); print("removed last frame", done[-1])
for f in RENDER:
    if f < FIRST or f > LAST: continue
    p = os.path.join(OUT, f"f{f:04d}.png")
    if os.path.exists(p): continue
    scn.frame_set(f); scn.render.filepath = p; t1 = time.time(); bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} {time.time() - t1:.0f}s peak rss {rss():.2f} GB", flush=True)
print("DONE", f"{time.time() - T0:.0f}s")
