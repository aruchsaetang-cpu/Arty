"""Kuro Oni ep 1, REAL SCENE 1 (the 3 s hook): a hundred men in black suits ring one man in a black cloak on a burning
rainy Korean street; one straight punch (gyaku-zuki), a shockwave, the ring is blasted outward.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/scene1.py [scale%] [first] [last] [step]
Renders PNGs to shorts/kuro_oni/frames_s1/ (existing frames skipped, so it resumes). Defaults: 50%, 1..90, step 2 (on twos).
env: SAMPLES (default 12), STILLS="t1,t2" seconds -> stills_s1/ (one process), NORENDER=1 to only build.
Post (white flash frame, red fear grade, speed lines, subtitle, sound): shorts/kuro_oni/scene1_compose.py"""
import math, os, random, sys, time, resource
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
FPS, DUR = 30, 3.0; NF = int(DUR * FPS)
os.environ["FRAMES"] = str(NF + 6); os.environ["PEOPLE"] = "0"; os.environ.setdefault("SEED", "7")
sys.path.insert(0, HERE)
import cast_kuro as CK                      # imports city (resets the scene), character_mh, cast, kimono
import bpy, bmesh
from mathutils import Vector as V, Quaternion, Matrix
import city as C
import character_mh as ch
scn = C.scn; prefs = C.prefs; P = C.PEOPLE_C
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 50
FIRST = int(sys.argv[2]) if len(sys.argv) > 2 else 1
LAST = int(sys.argv[3]) if len(sys.argv) > 3 else NF
STEP = int(sys.argv[4]) if len(sys.argv) > 4 else 2
SAMPLES = int(os.environ.get("SAMPLES", 12))
RAD = math.radians
def F(t): return int(round(t * FPS)) + 1
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0
T0 = time.time()

HC = V((0.0, 40.0, 0.0))                    # centre of the ring (the hero stands here, facing -y = the camera side)
F_BLAST = F(2.2) + 1                        # frame the shockwave starts (t = 2.233 s)
RNG = random.Random(11)

# ------------------------------------------------------------------ poses (copied from film.py, plus a low stance)
def pose(g, f, name):
    """Key a named pose on every animated bone at frame f. Forward is -Y in armature space."""
    scn.frame_set(f); ch.posed(g, "stand"); aim = ch._aimer(g)
    def arms(side, d, lo=None):
        for b in ("upperarm01", "upperarm02"): aim(f"{b}.{side}", d)
        for b in ("lowerarm01", "lowerarm02", "wrist"): aim(f"{b}.{side}", lo or d)
    def legs(side, up, lo):
        for b in ("upperleg01", "upperleg02"): aim(f"{b}.{side}", up)
        for b in ("lowerleg01", "lowerleg02"): aim(f"{b}.{side}", lo)
    GL = ((0.25, -0.35, -0.8), (0.1, -0.8, 0.7)); GR = ((-0.25, -0.35, -0.8), (-0.1, -0.8, 0.7))
    if name == "guard": arms("L", *GL); arms("R", *GR)
    elif name == "stance":             # Kyokushin zenkutsu-dachi: left leg forward and bent, right leg back and straight; fists up
        legs("L", (0.16, -0.88, -0.45), (0.05, 0.28, -1.0)); legs("R", (-0.32, 0.62, -0.78), (-0.33, 0.55, -0.83))
        arms("L", (0.3, -0.55, -0.6), (0.12, -0.9, 0.6)); arms("R", (-0.3, -0.5, -0.65), (-0.1, -0.6, 0.85))
    elif name == "chamber":            # rear fist pulled to the hip, front hand extended
        legs("L", (0.16, -0.88, -0.45), (0.05, 0.28, -1.0)); legs("R", (-0.32, 0.62, -0.78), (-0.33, 0.55, -0.83))
        arms("L", (0.25, -0.9, -0.1)); arms("R", (-0.2, 0.55, -0.6), (-0.1, -0.9, 0.2))
    elif name == "punch":              # gyaku-zuki: right fist straight out at chest height, front hand pulled back
        legs("L", (0.16, -0.88, -0.45), (0.05, 0.28, -1.0)); legs("R", (-0.32, 0.62, -0.78), (-0.33, 0.55, -0.83))
        arms("L", (0.3, 0.25, -0.9), (0.2, -0.3, -0.9)); arms("R", (-0.05, -1.0, 0.08))
    elif name == "calm":
        arms("L", (0.12, -0.05, -1.0)); arms("R", (-0.12, -0.05, -1.0))
        legs("L", (0.1, -0.1, -1.0), (0.1, 0.0, -1.0)); legs("R", (-0.1, -0.1, -1.0), (-0.1, 0.0, -1.0))
    elif name == "flail":              # flung: arms thrown up and out, legs kicked apart
        arms("L", (0.9, 0.1, 0.5)); arms("R", (-0.9, 0.2, 0.6))
        legs("L", (0.5, -0.4, -0.8), (0.3, 0.3, -1.0)); legs("R", (-0.5, 0.3, -0.8), (-0.4, 0.6, -0.8))
    bpy.context.view_layer.update()
    for b in ch.ANIM_BONES: g.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f)
def foot_low(g):
    bpy.context.view_layer.update()
    return min((g.matrix_world @ g.pose.bones[f"foot.{s}"].tail).z for s in "LR")
def linear_all(ob):
    ad = ob.animation_data
    if not ad or not ad.action: return
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for fc in cb.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

# ------------------------------------------------------------------ cast (built before the city: cheap pose solves)
NFIGHT = 6
FANG = [-150, -122, -58, -30, 12, 160]          # real fighters in the front of the ring (degrees round the ring, -90 = south = camera side)
names = ["HERO"] + [f"FIGHTER_{i}" for i in range(NFIGHT)]
locs = {"HERO": tuple(HC)}
for i, a in enumerate(FANG): locs[f"FIGHTER_{i}"] = (HC.x + 3.0 * math.cos(RAD(a)), HC.y + 3.0 * math.sin(RAD(a)), 0)
arms_ = CK.build_cast(P, names, locs=locs, hero_cloak=True, heading=0.0)
hero = arms_["HERO"]; fighters = [arms_[f"FIGHTER_{i}"] for i in range(NFIGHT)]
print(f"cast built {time.time() - T0:.0f}s rss {rss():.2f} GB")
def heading_to(frm, to):
    d = V(to) - V(frm); return math.atan2(d.x, -d.y)
for g, a in zip(fighters, FANG):
    g.rotation_euler = (0, 0, heading_to(g.location, HC))

# ------------------------------------------------------------------ the hero: low stance, chamber, one punch, calm
prefs.keyframe_new_interpolation_type = "LINEAR"
scn.frame_set(1); ch.posed(hero, "stand"); z_stand = foot_low(hero)
hero_z0 = hero.location.z
def key_hero(f, name, yaw=0.0, push=0.0):
    pose(hero, f, name)
    hero.location = (HC.x, HC.y + push, hero_z0); hero.rotation_euler = (0, 0, yaw)
    low = foot_low(hero); hero.location.z = hero_z0 + (z_stand - low)       # drop the root so the lowest foot touches the ground
    hero.keyframe_insert("location", frame=f); hero.keyframe_insert("rotation_euler", frame=f)
key_hero(1, "stance"); key_hero(F(1.9), "stance")
key_hero(F(2.13), "chamber", yaw=RAD(-14))                  # hips turned back (reverse punch loads the rear hip)
key_hero(F_BLAST, "punch", yaw=RAD(16), push=-0.12)         # hips snap through, a half-step of drive
key_hero(F_BLAST + 14, "punch", yaw=RAD(16), push=-0.12)
key_hero(F(2.9), "calm", yaw=0.0, push=-0.12)
linear_all(hero)
HEADZ = 1.62                                                # head height in the low stance (measured below)
scn.frame_set(1)
HEAD = hero.matrix_world @ hero.pose.bones["head"].head
print("hero head", tuple(round(c, 2) for c in HEAD), "stance drop", round(hero_z0 - hero.location.z, 3))
HEAD = V(HEAD)

# face in black shadow during the enemy-POV fear shots (1.0-1.7 s): the hero's skin materials mix to black, keyed
for ob in hero.children_recursive:
    for i, m in enumerate(ob.data.materials if ob.type == "MESH" else []):
        if m and "skin" in m.name.lower():
            m2 = m.copy(); ob.data.materials[i] = m2; nt = m2.node_tree
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); src = out.inputs["Surface"].links[0].from_socket
            blk = nt.nodes.new("ShaderNodeEmission"); blk.inputs["Color"].default_value = (0.004, 0.004, 0.006, 1)
            mx = nt.nodes.new("ShaderNodeMixShader"); vn = nt.nodes.new("ShaderNodeValue")
            nt.links.new(vn.outputs[0], mx.inputs[0]); nt.links.new(src, mx.inputs[1]); nt.links.new(blk.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs["Surface"])
            prefs.keyframe_new_interpolation_type = "CONSTANT"
            for f, v in ((1, 0.0), (F(1.0), 0.93), (F(1.7), 0.0)):
                vn.outputs[0].default_value = v; vn.outputs[0].keyframe_insert("default_value", frame=f)
# the eyes go full white at 1.95 s: white emissive copies of the void eyes replace them
wm = bpy.data.materials.new("eye_white"); wm.use_nodes = True; nt = wm.node_tree; nt.nodes.clear()
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); e_ = nt.nodes.new("ShaderNodeEmission")
e_.inputs["Color"].default_value = (1, 1, 1, 1); e_.inputs["Strength"].default_value = 9.0; nt.links.new(e_.outputs[0], o_.inputs[0])
prefs.keyframe_new_interpolation_type = "CONSTANT"
for o in [c for c in hero.children_recursive if c.name.startswith("eye_")]:
    v = o.copy(); v.data = o.data.copy(); v.animation_data_clear(); v.name = o.name + "_white"; v.scale = tuple(1.04 * s for s in o.scale)
    for c_ in o.users_collection: c_.objects.link(v)
    v.data.materials.clear(); v.data.materials.append(wm)
    o.hide_render = False; o.keyframe_insert("hide_render", frame=1); o.hide_render = True; o.keyframe_insert("hide_render", frame=F(1.95))
    v.hide_render = True; v.keyframe_insert("hide_render", frame=1); v.hide_render = False; v.keyframe_insert("hide_render", frame=F(1.95))

# ------------------------------------------------------------------ the army: 94 silhouettes in four rings + 6 real fighters
def gap(a, r):
    """angles kept clear of silhouettes so the cameras stand in the ring: south POV x2 and the east side-on shot."""
    a = (a + 180) % 360 - 180
    return (abs(a + 90) < 15 and r < 4.6) or (abs(a + 40) < 11 and r < 4.6) or abs(a) < 13 or (abs(a + 90) < 7) or (92 < a < 132)
RINGS = [(3.5, 20), (4.3, 28), (5.1, 38), (5.9, 50)]
sil = CK.make_silhouette_crowd(P, 94, area=((-1, 1), (0, 1)), seed=4)
slots = []
for r, n in RINGS:
    for k in range(n):
        a = 360.0 * k / n + RNG.uniform(-4, 4) + (7 if r > 4 else 0)
        if gap(a, r): continue
        if any(abs(((a - fa) + 180) % 360 - 180) < 11 and r < 4.0 for fa in FANG): continue
        slots.append((r + RNG.uniform(-0.2, 0.2), a))
RNG.shuffle(slots); slots = slots[:len(sil)]
extra = 94 - len(slots)
for o in sil[len(slots):]: o.hide_render = True; o.hide_viewport = True
sil = sil[:len(slots)]
print("silhouettes", len(sil), "(wanted 94; skipped", extra, "for camera gaps)")

# ------------------------------------------------------------------ the shockwave: everybody flung outward, tumbling
def blast(ob, pos, heading, pivot, vz, w, spd, key_pose=None, sign=1):
    """Key a ballistic flight from F_BLAST on: pos = ring position (x,y), pivot = local offset to tumble about."""
    rad = V((pos[0] - HC.x, pos[1] - HC.y, 0)); r = rad.length; u = rad.normalized()
    axis = V((-u.y, u.x, 0)) * sign
    base = Quaternion((0, 0, 1), heading)
    ob.rotation_mode = "QUATERNION"
    L0 = V((pos[0], pos[1], ob.location.z)); p = V(pivot)
    ob.location = L0; ob.rotation_quaternion = base
    ob.keyframe_insert("location", frame=1); ob.keyframe_insert("rotation_quaternion", frame=1)
    ob.keyframe_insert("location", frame=F_BLAST - 1); ob.keyframe_insert("rotation_quaternion", frame=F_BLAST - 1)
    for f in range(F_BLAST, NF + 7):
        t = (f - F_BLAST + 1) / FPS
        vel = V((u.x * spd * 0.5, u.y * spd * 1.1, 0))          # the street is narrow: x is held back, the blast runs along the street
        zt = vz * t - 0.5 * 9.8 * t * t * 0.85
        q = Quaternion(axis, w * t) @ base
        cm = L0 + base @ p + vel * t + V((0, 0, zt))
        ob.rotation_quaternion = q; ob.location = cm - q @ p      # tumble about the pivot, not the root
        ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_quaternion", frame=f)
    linear_all(ob)

prefs.keyframe_new_interpolation_type = "LINEAR"
for i, o in enumerate(sil):
    r, a = slots[i]; x, y = HC.x + r * math.cos(RAD(a)), HC.y + r * math.sin(RAD(a))
    o.location = (x, y, 0); o.rotation_euler = (0, 0, heading_to((x, y, 0), HC))
    o.rotation_mode = "QUATERNION"
    inner = (6.4 - r) / 2.9
    spd = RNG.uniform(11, 16) * (0.8 + 0.4 * inner); vz = RNG.uniform(5.5, 10.0) * (0.9 + 0.3 * inner)
    blast(o, (x, y), o.rotation_euler.z, (0, 0, 0.75 * o.scale[2]), vz, RNG.uniform(5, 13) * RNG.choice((-1, 1)), spd)
for g, a in zip(fighters, FANG):
    x, y = g.location.x, g.location.y; hd = g.rotation_euler.z; z0 = g.location.z
    pose(g, 1, "guard"); pose(g, F_BLAST - 1, "guard"); pose(g, F_BLAST, "flail"); pose(g, NF + 6, "flail")
    linear_all(g)
    g.location = (x, y, z0)
    blast(g, (x, y), hd, (0, 0, 0), RNG.uniform(7.5, 10.5), RNG.uniform(6, 11) * RNG.choice((-1, 1)), RNG.uniform(11, 15))
    for c in g.children:                              # contact shadow discs must not float with the flung body
        if c.name.startswith("contact_shadow"): c.hide_render = True

# ------------------------------------------------------------------ the street (reuse the city; no people), then the fires
C.build_scene(with_hero=False, avoid=[], rain_box=(0.0, 38.0, 22.0, 34.0, 9.0, 24, 15000))
print(f"city built {time.time() - T0:.0f}s rss {rss():.2f} GB")
# the ring stands on bare road: hide parked cars / props that stand inside it
CLEAR = []
RIGS = set(arms_.values())
def _rig_child(ob):
    while ob is not None:
        if ob in RIGS: return True
        ob = ob.parent
    return False
for ob in bpy.data.objects:
    if ob.type != "MESH" or ob.name in ("road", "rain", "fog") or ob.name.startswith(("sil_", "walk", "curb", "paint", "flame", "ember", "barrel")): continue
    if _rig_child(ob): continue
    c = ob.matrix_world @ (sum((V(b) for b in ob.bound_box), V()) / 8)
    d = ob.dimensions
    if abs(c.x - HC.x) < 5.8 and abs(c.y - HC.y) < 8.5 and c.z < 3.0 and d.z < 5.0 and d.x < 6.0 and d.y < 8.0:
        CLEAR.append(ob.name)
for n_ in CLEAR: bpy.data.objects[n_].hide_render = True
print("hidden props in the ring area:", len(CLEAR), CLEAR[:12])

def emissive(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*col, 1); e.inputs["Strength"].default_value = strength; nt.links.new(e.outputs[0], o.inputs[0]); return m
BARREL = bpy.data.materials.new('barrel_m'); BARREL.diffuse_color = (0.03, 0.025, 0.025, 1)
M_FIRE = emissive("fire_o", (1.0, 0.16, 0.01), 2.2); M_CORE = emissive("fire_y", (1.0, 0.45, 0.06), 4.0); M_EMB = emissive("ember", (1.0, 0.5, 0.12), 60.0)
FIRES = [(-6.3, 33.0, 1.0), (6.4, 35.0, 1.15), (-6.4, 43.0, 1.2), (6.2, 46.0, 1.0), (-6.0, 51.0, 0.9), (6.0, 29.0, 0.9), (0.0, 56.0, 1.4)]
def flame(x, y, s):
    parts = []
    for k, (col_m, h, w) in enumerate(((M_FIRE, 2.0, 0.45), (M_FIRE, 1.5, 0.32), (M_FIRE, 1.8, 0.28), (M_FIRE, 1.2, 0.3), (M_CORE, 0.9, 0.22))):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0); me = bpy.data.meshes.new("flame"); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new("flame", me); scn.collection.objects.link(ob); me.materials.append(col_m); ob.visible_shadow = False
        rng = random.Random(int(x * 10 + y + k))
        base = V((x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.4, 0.4), 0.0))
        for f in range(1, NF + 8, 2):
            fl = 0.75 + 0.5 * rng.random()
            ob.scale = (w * s * (0.85 + 0.3 * rng.random()), w * s * (0.85 + 0.3 * rng.random()), h * s * fl)
            ob.location = base + V((rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07), h * s * fl * 0.9))
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("scale", frame=f)
        linear_all(ob); parts.append(ob)
    # a burning wreck / barrel under the flame
    bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=10, radius1=0.5 * s, radius2=0.42 * s, depth=0.9 * s, matrix=Matrix.Translation((0, 0, 0.45 * s)))
    me = bpy.data.meshes.new("barrel"); bm.to_mesh(me); bm.free(); bo = bpy.data.objects.new("barrel", me); scn.collection.objects.link(bo)
    bo.location = (x, y, 0); me.materials.append(BARREL)
    ld = bpy.data.lights.new("fire_l", "POINT"); ld.shadow_soft_size = 0.8; ld.color = (1.0, 0.45, 0.14)
    lo = bpy.data.objects.new("fire_l", ld); scn.collection.objects.link(lo); lo.location = (x, y, 1.6 * s)
    rng = random.Random(int(x * 3 + y * 7))
    for f in range(1, NF + 8, 2):
        ld.energy = 1500 * s * (0.65 + 0.7 * rng.random()); ld.keyframe_insert("energy", frame=f)
    ch.set_interp(ld, "LINEAR")
    # embers drifting up
    for k in range(10):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.03); me = bpy.data.meshes.new("ember"); bm.to_mesh(me); bm.free()
        eo = bpy.data.objects.new("ember", me); scn.collection.objects.link(eo); me.materials.append(M_EMB); eo.visible_shadow = False
        ph = rng.uniform(0, 1); sp = rng.uniform(1.5, 3.0); dx = rng.uniform(-0.6, 0.6); dy = rng.uniform(-0.6, 0.6); ox, oy = rng.uniform(-.3, .3), rng.uniform(-.3, .3)
        for f in range(1, NF + 8, 3):
            t = (f / FPS * sp * 0.4 + ph) % 1.0
            eo.location = (x + ox + dx * t * 2, y + oy + dy * t * 2, 1.0 * s + t * 4.5); eo.scale = (1 - t,) * 3
            eo.keyframe_insert("location", frame=f); eo.keyframe_insert("scale", frame=f)
        linear_all(eo)
for x, y, s in FIRES: flame(x, y, s)
# cool rim light behind and above the hero (so his silhouette and cloak read against the fire), and a dim fill
def lamp(name, kind, loc, energy, col, rot=None, size=1.0):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = col
    if kind == "AREA": ld.size = size
    lo = bpy.data.objects.new(name, ld); scn.collection.objects.link(lo); lo.location = loc
    if rot: lo.rotation_euler = rot
    return lo
lamp("rim", "AREA", (0.0, 44.5, 4.5), 1800, (0.55, 0.65, 1.0), rot=(RAD(120), 0, 0), size=3.0)
lamp("rim2", "AREA", (3.0, 34.0, 3.0), 500, (1.0, 0.55, 0.3), rot=(RAD(60), 0, RAD(20)), size=2.0)

# ------------------------------------------------------------------ camera: hand-held, low, tilted, cut every 0.3-0.7 s
cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05; cd.clip_end = 3000
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam; cam.rotation_mode = "QUATERNION"
cd.dof.use_dof = True; cd.dof.aperture_fstop = 5.6
def ell(a, rx, ry, z): return V((HC.x + rx * math.cos(RAD(a)), HC.y + ry * math.sin(RAD(a)), z))
def lerp(a, b, k): return a + (b - a) * k
def vl(a, b, k): return V(a).lerp(V(b), k)
def ease(k): return k * k * (3 - 2 * k)
HLOOK = V((HC.x, HC.y, 1.15)); HF_ = V((HC.x, HC.y, HEAD.z))
SHOTS = []
def shot(t0, t1, fn): SHOTS.append((t0, t1, fn))
# wide low orbits: the hero small in the middle, fires left and right (cam, look, lens, roll deg, fstop)
shot(0.0, 0.5, lambda t, k: (ell(lerp(-112, -84, k), 5.8, 10.8, lerp(0.45, 0.6, k)), HLOOK + V((0, 0, 0.1)), 27, 5, 8))
shot(0.5, 1.0, lambda t, k: (ell(lerp(98, 124, k), 5.4, 9.2, lerp(0.4, 0.6, k)), HLOOK + V((0, 0, 0.25)), 24, -7, 8))
# enemy POV fear shots: extreme low, looking up at him (one white eye)
shot(1.0, 1.35, lambda t, k: (V((HC.x - 0.1, HC.y - 2.4, 0.2)), V((HC.x, HC.y, HEAD.z + 0.05)) + V((0, 0, lerp(0, 0.1, k))), 19, 9, 4))
shot(1.35, 1.7, lambda t, k: (ell(-40, 3.4, 3.4, 0.2), HEAD + V((0, 0, 0.0)), 24, -10, 4))
# extreme close-up of the face, pushing in to the eyes
shot(1.7, 2.2, lambda t, k: (HEAD + V((lerp(0.22, 0.12, k), lerp(-0.95, -0.55, k), lerp(-0.12, -0.02, k))), HEAD + V((0, 0, 0.02)), 60, 8 + 4 * k, 2.0))
# the punch, side-on from the east, then the ring bursting (low, from the south), then the high wide
shot(2.2, 2.38, lambda t, k: (V((HC.x + 4.3, HC.y - 0.2, 0.75)), V((HC.x, HC.y - 0.75, 1.15)), 28, -8, 8))
shot(2.38, 2.55, lambda t, k: (V((HC.x + 0.8, HC.y - 12.0, 0.35)), V((HC.x, HC.y - 5.0, 2.6)), 20, 9, 8))
shot(2.55, 3.01, lambda t, k: (vl((HC.x + 0.6, HC.y - 15.0, 9.0), (HC.x + 1.6, HC.y - 8.5, 3.4), k), vl((HC.x, HC.y - 2.0, 2.0), (HC.x, HC.y, 1.7), k), lerp(25, 30, k), -5, 11))
if os.environ.get("CAMTEST"):
    _ts = [float(x) for x in os.environ["STILLS"].split(",")]; SHOTS[:] = []       # CAMTEST="x,y,z,lx,ly,lz,lens;..." one camera per still (offsets from the ring centre)
    for _i, _c in enumerate(os.environ["CAMTEST"].split(";")):
        _v = [float(x) for x in _c.split(",")]
        SHOTS.append((_ts[_i] - 0.02, _ts[_i] + 0.03 if _i < len(_ts) - 1 else 99, (lambda v: lambda t, k: (HC + V(v[0:3]), HC + V(v[3:6]), v[6], 0, 8))(_v)))
    SHOTS.append((-1, 99, SHOTS[0][2])); SHOTS.sort(key=lambda s_: -s_[0] if s_[0] < 0 else s_[0])
def key_cam(f):
    t = (f - 1) / FPS
    s = next((s for s in SHOTS if s[0] <= t < s[1]), SHOTS[-1]); k = min(1.0, max(0.0, (t - s[0]) / (s[1] - s[0])))
    loc, look, lens, roll, fst = s[2](t, k)
    amp = 0.35 if len(SHOTS) > 4 and s[2] is SHOTS[4][2] else 1.0
    sh = V((math.sin(f * 1.7) * 0.012 + math.sin(f * 0.53 + 1) * 0.02, math.sin(f * 1.3 + 2) * 0.012, math.sin(f * 1.9) * 0.01 + math.sin(f * 0.61) * 0.015)) * amp
    lk = V((math.sin(f * 0.37) * 0.05 + math.sin(f * 1.31) * 0.025, math.sin(f * 0.41 + 1) * 0.04, math.sin(f * 0.43 + 2) * 0.04 + math.sin(f * 1.7) * 0.02)) * amp
    loc = V(loc) + sh; look = V(look) + lk
    q = (look - loc).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), RAD(roll + 1.2 * math.sin(f * 0.29) * amp))
    cam.location = loc; cam.rotation_quaternion = q; cd.lens = lens; cd.dof.aperture_fstop = fst; cd.dof.focus_distance = max(0.3, (look - loc).length)
    cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f)
    cd.keyframe_insert("lens", frame=f); cd.dof.keyframe_insert("aperture_fstop", frame=f); cd.dof.keyframe_insert("focus_distance", frame=f)
prefs.keyframe_new_interpolation_type = "CONSTANT"
for f in range(1, NF + 7): key_cam(f)
if os.environ.get("NEARCAM"):                  # QA: which props sit within 2.5 m of the camera
    for f in range(1, NF + 1, 3):
        scn.frame_set(f); cp = cam.matrix_world.translation; near = []
        for ob in bpy.data.objects:
            if ob.type == "MESH" and not ob.hide_render and not ob.name.startswith(("sil_", "rain")):
                bb = [ob.matrix_world @ V(b) for b in ob.bound_box]
                lo = V((min(b.x for b in bb), min(b.y for b in bb), min(b.z for b in bb))); hi = V((max(b.x for b in bb), max(b.y for b in bb), max(b.z for b in bb)))
                if all(lo[i] - 2.5 < cp[i] < hi[i] + 2.5 for i in range(3)) and ob.name not in ("road",): near.append(ob.name)
        print("NEAR", f, [round(c, 1) for c in cp], near[:8])

# ------------------------------------------------------------------ render
C.render_settings(SCALE, SAMPLES)
scn.render.fps = FPS; scn.frame_start, scn.frame_end = 1, NF
scn.render.image_settings.file_format = "PNG"
OUT = os.path.join(HERE, "frames_s1"); os.makedirs(OUT, exist_ok=True)
if os.environ.get("NORENDER"): print("built only", f"{time.time() - T0:.0f}s rss {rss():.2f} GB"); sys.exit(0)
stills = os.environ.get("STILLS")
if stills:
    sd = os.environ.get("STILLDIR") or os.path.join(HERE, "stills_s1"); os.makedirs(sd, exist_ok=True)
    for s in stills.split(","):
        f = F(float(s)); scn.frame_set(f); scn.render.filepath = os.path.join(sd, f"t{float(s):05.2f}.png")
        t1 = time.time(); bpy.ops.render.render(write_still=True); print(f"STILL t={s} f={f} {time.time() - t1:.0f}s rss {rss():.2f} GB", flush=True)
    sys.exit(0)
for f in range(FIRST, min(LAST, NF) + 1, STEP):
    p = os.path.join(OUT, f"f{f:04d}.png")
    if os.path.exists(p): continue
    scn.frame_set(f); scn.render.filepath = p; t1 = time.time(); bpy.ops.render.render(write_still=True)
    print(f"FRAME {f} {time.time() - t1:.0f}s peak rss {rss():.2f} GB", flush=True)
print("DONE", f"{time.time() - T0:.0f}s")
