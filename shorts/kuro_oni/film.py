"""Kuro Oni ep 1: ROUGH 3D PROTOTYPE v2 (throwaway), storyboard v3. Real Gojo rig (Aura Monster hero), simple sets, anime camera.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/film.py [scale%] [first] [last] [step]
Renders PNGs to shorts/kuro_oni/frames/ (existing frames skipped). env: SAMPLES (default 8), STILLS="t1,t2" seconds -> stills/.
Timing and shots follow docs/superpowers/specs/2026-11-25-kuro-oni-design.md (storyboard v3)."""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
FPS, DUR = 30, 60.0; NF = int(DUR * FPS)
os.environ["FRAMES"] = str(NF); os.environ.setdefault("PEOPLE", "0"); os.environ.setdefault("SEED", "7")
sys.path.insert(0, os.path.join(ROOT, "lookdev")); sys.path.insert(0, os.path.join(ROOT, "shorts", "aura"))
import bpy, bmesh
from mathutils import Vector as V, Quaternion, Matrix
import city as C
import character_mh as ch
import cast as K
scn = C.scn; prefs = C.prefs
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 25
FIRST = int(sys.argv[2]) if len(sys.argv) > 2 else 1
LAST = int(sys.argv[3]) if len(sys.argv) > 3 else NF
STEP = int(sys.argv[4]) if len(sys.argv) > 4 else 2
SAMPLES = int(os.environ.get("SAMPLES", 8))
def F(t): return int(round(t * FPS)) + 1
P = C.PEOPLE_C
RNG = random.Random(5)
RAD = math.radians

# ------------------------------------------------------------------ cast styles
KID = dict(K.KID2, body="kid_lean", height=1.3, tie=None, backpack=None, legs="trousers", leg_col=("#1c1a20", "#0c0b10"), coat=None,
           top=("#d8d4cc", "#8a867e"), turtleneck=False, hair="bangs", void_eyes=True)
MOM = dict(K.W1, coat=("#4a4256", "#221e2a"), hem=1.0, open_skirt=False, open_coat=False, lapels=True, coat_flare=(0.02, 0.05),
           top=("#3a3446", "#1a1620"), turtleneck=False, legs="skirt", leg_col=("#3a3446", "#1a1620"), skirt_hem=1.0, bag=None,
           hair="long", hair_len=0.12, hair_col="#0c0a0a", lips="#8a4a52")
MASTER = dict(K.MAN_LONG, coat=("#8a8a90", "#4a4a52"), hair_col="#bdbdc4", legs="trousers", leg_col=("#2a2a32", "#14141a"))
def fighter(v):
    return dict(K.MAN_LONG, vary=200 + v, coat=("#1b1b22", "#0a0a10"), hair_col="#0e0e12", legs="trousers", leg_col=("#16161c", "#08080c"),
                top=("#202028", "#0c0c12"), clear_face=False)
KNIGHT = dict(K.MAN_DIAMOND, vary=230, coat=("#5a2a78", "#2a1038"), hair_col="#d8c060")

# ------------------------------------------------------------------ small helpers
_mats = {}
def mat(name, col, emit=0.0):
    k = (name, col, emit)
    if k not in _mats:
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        if emit:
            e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (*col, 1); e.inputs["Strength"].default_value = emit
            nt.links.new(e.outputs[0], out.inputs[0])
        else:
            b = nt.nodes.new("ShaderNodeBsdfDiffuse"); b.inputs["Color"].default_value = (*col, 1); nt.links.new(b.outputs[0], out.inputs[0])
        _mats[k] = m
    return _mats[k]
def box(name, c, size, m):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob); ob.location = c; ob.scale = size; ob.data.materials.append(m); return ob
def ball(name, c, r, m):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scn.collection.objects.link(ob); ob.location = c; ob.data.materials.append(m); return ob
def light(name, loc, power, col=(1, 1, 1), kind="POINT", size=0.3):
    ld = bpy.data.lights.new(name, kind); ld.energy = power; ld.color = col
    if kind == "POINT": ld.shadow_soft_size = size
    lo = bpy.data.objects.new(name, ld); lo.location = loc; scn.collection.objects.link(lo); return lo
def key(ob, f, loc=None, rot=None, scale=None):
    if loc is not None: ob.location = loc; ob.keyframe_insert("location", frame=f)
    if rot is not None: ob.rotation_euler = rot; ob.keyframe_insert("rotation_euler", frame=f)
    if scale is not None: ob.scale = scale; ob.keyframe_insert("scale", frame=f)
def constant(ob):
    ad = ob.animation_data
    if not ad or not ad.action: return
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for fc in cb.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"
def ground(c, size, col):
    return box("ground", (c[0], c[1], -0.05), (size, size, 0.1), mat("gr" + str(col), col))

# ------------------------------------------------------------------ rigs and poses
def rig(style, loc, heading=0.0, adult=True, scale=1.0, void=False):
    st = dict(style)
    if void: st["void_eyes"] = True
    if adult: g, _ = ch.build_v1(P, (0, 0, 0), st, pose_mode="stand", void_eyes=void)
    else: g, _ = ch.build(P, (0, 0, 0), st, pose_mode="stand", heading=0)
    g.location = V(loc) + V((0, 0, g["ground_rest"] * scale)); g.scale = (scale,) * 3
    g.rotation_euler = (0, 0, RAD(heading)); g["base_z"] = g["ground_rest"] * scale
    return g
def pose(g, f, name, phase=0.0):
    """Key a named pose on every animated bone at frame f. Forward is -Y in armature space."""
    scn.frame_set(f); ch.posed(g, "stand"); aim = ch._aimer(g)
    def arms(side, d, lo=None):
        for b in ("upperarm01", "upperarm02"): aim(f"{b}.{side}", d)
        for b in ("lowerarm01", "lowerarm02", "wrist"): aim(f"{b}.{side}", lo or d)
    GL = ((0.25, -0.35, -0.8), (0.1, -0.8, 0.7)); GR = ((-0.25, -0.35, -0.8), (-0.1, -0.8, 0.7))
    if name == "guard": arms("L", *GL); arms("R", *GR)
    elif name == "punch_R": arms("L", *GL); arms("R", (-0.05, -1.0, 0.08))
    elif name == "punch_L": arms("R", *GR); arms("L", (0.05, -1.0, 0.08))
    elif name == "wrist": arms("L", (0.15, -1.0, -0.25)); arms("R", (-0.15, -1.0, -0.25))
    elif name == "slap": arms("R", (-0.9, -0.5, 0.1)); arms("L", (0.1, -0.3, -1))
    elif name == "kick_R":
        arms("L", *GL); arms("R", *GR)
        for b in ("upperleg01", "upperleg02"): aim(f"{b}.R", (-0.05, -1.0, 0.05))
        for b in ("lowerleg01", "lowerleg02"): aim(f"{b}.R", (-0.05, -1.0, -0.15))
    elif name == "walk": ch._walk_phase(g, aim, phase)
    elif name == "kneel":
        arms("L", (0.05, -0.3, -1)); arms("R", (-0.05, -0.3, -1))
        for side, sx in (("L", 1), ("R", -1)):
            for b in ("upperleg01", "upperleg02"): aim(f"{b}.{side}", (sx * 0.1, -1.0, -0.1))
            for b in ("lowerleg01", "lowerleg02"): aim(f"{b}.{side}", (sx * 0.1, 0.1, -1.0))
    bpy.context.view_layer.update()
    for b in ch.ANIM_BONES: g.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f)
def linear_bones(g):
    ad = g.animation_data
    if not ad or not ad.action: return
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for fc in cb.fcurves:
        if fc.data_path.startswith("pose.bones"):
            for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

DUMMY_ME = None
def dummy(name, loc, col=(0.03, 0.03, 0.045), h=1.0, w=1.0):
    global DUMMY_ME
    if DUMMY_ME is None:
        bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=10, radius1=0.26, radius2=0.2, depth=1.1, matrix=Matrix.Translation((0, 0, 0.62)))
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.13, matrix=Matrix.Translation((0, 0, 1.4)))
        DUMMY_ME = bpy.data.meshes.new("dummy"); bm.to_mesh(DUMMY_ME); bm.free()
    ob = bpy.data.objects.new(name, DUMMY_ME); scn.collection.objects.link(ob); ob.location = loc
    if not ob.data.materials: ob.data.materials.append(mat("dum", col))
    ob.scale = (w, w, h); return ob

# ------------------------------------------------------------------ sets (each far from the others)
O_HALL, O_COURT, O_DOJO, O_WAR, O_GATE, O_FANT, O_DARK, O_BAN = [V((x, 0, 0)) for x in (0, 100, 200, 300, 400, 500, 600, 700)]
CLAN = []; CROWD = []; FIGHTERS = []

def build_all():
    global hall_kid, hall_mom, hall_boy, father
    # ---- hall (1-6 s): the clan of 30 in three rows, lean kid Gojo in front of them
    ground(O_HALL, 40, (0.18, 0.12, 0.08)); box("hwall", O_HALL + V((0, 8, 3)), (30, 0.3, 6), mat("hw", (0.14, 0.09, 0.07)))
    for r_ in range(3):
        for k in range(10):
            col = (0.04, 0.04, 0.06) if (k + r_) % 3 else (0.07, 0.05, 0.05)
            d = dummy(f"clan{r_}{k}", O_HALL + V((-4.5 + k * 1.0 + (0.4 if r_ % 2 else 0), 3.4 + r_ * 1.3, 0)), col, RNG.uniform(0.92, 1.08))
            d.rotation_euler = (0, 0, math.pi); CLAN.append(d)
    for k in range(6): light(f"hl{k}", O_HALL + V((-5 + k * 2.0, 4.5, 3.4)), 700, (1, 0.7, 0.4))
    light("hkey", O_HALL + V((0, -2.5, 2.4)), 700, (1, 0.8, 0.6)); light("hkey2", O_HALL + V((0, 1.5, 2.8)), 500, (1, 0.85, 0.7))
    hall_kid = rig(KID, O_HALL + V((0, 0.6, 0)), 180, adult=False, void=True)
    hall_mom = rig(MOM, O_HALL + V((-1.3, 0.4, 0)), 180, adult=False)
    father = dummy("father", O_HALL + V((3.2, 0.2, 0)), (0.01, 0.01, 0.015), 1.12); father.rotation_euler = (0, 0, math.pi)
    hall_boy = dummy("boy", O_HALL + V((0.2, 1.7, 0)), (0.2, 0.2, 0.25), 0.95)
    # ---- courtyard (6-10 s): bright day, a gate, normal kids playing outside
    ground(O_COURT, 60, (0.55, 0.5, 0.4)); box("sky", O_COURT + V((0, 20, 5)), (50, 0.3, 14), mat("sk", (1, 0.9, 0.75), 1.4))
    for s in (-1, 1): box(f"cgp{s}", O_COURT + V((s * 2.6, 6.0, 2.0)), (0.6, 0.6, 4.0), mat("cgp", (0.2, 0.08, 0.06)))
    box("cgb", O_COURT + V((0, 6.0, 4.1)), (6.2, 0.7, 0.4), mat("cgb", (0.2, 0.08, 0.06)))
    light("csun", O_COURT + V((-2, -5, 8)), 14000, (1, 0.95, 0.85), size=2)
    global court_kid, court_mom, play
    court_kid = rig(KID, O_COURT + V((0, -1.0, 0)), 180, adult=False, void=True)
    court_mom = rig(MOM, O_COURT + V((-4.0, 3.9, 0)), 90, adult=False)
    play = [dummy(f"pl{k}", O_COURT + V((-2 + k * 1.3, 10.5, 0)), c, 0.62) for k, c in enumerate(((0.9, 0.2, 0.2), (0.2, 0.5, 0.9), (0.95, 0.8, 0.2), (0.3, 0.8, 0.4)))]
    # ---- dojo (10-15 s)
    ground(O_DOJO, 40, (0.3, 0.2, 0.13)); box("dwall", O_DOJO + V((0, 7, 3)), (30, 0.3, 6), mat("dw", (0.22, 0.15, 0.1)))
    light("dl", O_DOJO + V((0, 1, 4.5)), 2200, (1, 0.85, 0.7)); light("dl2", O_DOJO + V((-3, 1, 2)), 800, (1, 0.8, 0.6))
    box("verandaD", O_DOJO + V((4.5, 5.2, 0.25)), (3.5, 2.5, 0.5), mat("vd", (0.25, 0.17, 0.1)))
    global teen, master, d_mom, bat1, bat2
    teen = rig(K.HERO_V1, O_DOJO + V((0, 0, 0)), 180, adult=True, scale=0.88, void=True)
    master = rig(MASTER, O_DOJO + V((0, 2.4, 0)), 0, adult=False)
    d_mom = rig(MOM, O_DOJO + V((4.5, 5.2, 0.5)), 0, adult=False)
    bat1 = box("bat1", O_DOJO + V((0, 1.5, -40)), (0.07, 0.9, 0.07), mat("bat", (0.4, 0.4, 0.45)))
    bat2 = box("bat2", O_DOJO + V((0, 1.5, -40)), (0.07, 0.9, 0.07), mat("bat", (0.4, 0.4, 0.45)))
    # ---- cloak and banners (15-17 s)
    ground(O_BAN, 60, (0.04, 0.035, 0.03)); light("bl", O_BAN + V((0, -3, 6)), 3000, (0.6, 0.7, 1))
    global cloak, banners, ban_g
    cloak = box("cloak", O_BAN + V((0, 1.5, 0.03)), (1.3, 1.9, 0.05), mat("cloak", (0.02, 0.02, 0.025)))
    banners = [box(f"ban{k}", O_BAN + V((-4.2 + k * 1.2, 5.5, 1.2)), (0.7, 0.06, 2.4), mat("ban", (0.65, 0.05, 0.05))) for k in range(8)]
    ban_g = rig(K.HERO_V1, O_BAN + V((0, 0.3, 0)), 180, adult=True, void=True)
    # ---- war street (17-37 s)
    ground(O_WAR, 90, (0.05, 0.045, 0.05))
    for s in (-1, 1):
        for k in range(8):
            box(f"bld{s}{k}", O_WAR + V((s * 9, -8 + k * 6.5, 4.5)), (5, 5.5, 9 + (k % 3) * 2.5), mat("bl", (0.08, 0.06, 0.06)))
            box(f"win{s}{k}", O_WAR + V((s * 6.4, -8 + k * 6.5, 3 + (k % 3))), (0.05, 3, 1.2), mat("win", (1, 0.55, 0.15), 6))
    box("glow", O_WAR + V((0, -12, 5)), (30, 0.3, 14), mat("glow", (1, 0.4, 0.1), 3))
    global fires
    fires = []
    for k, (x, y) in enumerate(((-4.5, -4), (4.5, -3), (-5.5, 6), (5.5, 9), (-3, 18), (4, 20))):
        fires.append(light(f"fire{k}", O_WAR + V((x, y, 1.8)), 3500, (1, 0.45, 0.12), size=1.0))
        ball(f"fb{k}", O_WAR + V((x, y, 1.0)), 0.9, mat("fb", (1, 0.45, 0.1), 5))
    light("wrim", O_WAR + V((0, 6, 6)), 2500, (0.6, 0.6, 1.0), size=1.0)
    global war_g, war_mom, war_cup
    war_g = rig(K.HERO_V1, O_WAR + V((0, 0, 0)), 180, adult=True, void=True)
    war_mom = rig(MOM, O_WAR + V((0, 14, 0)), 0, adult=False)
    war_cup = box("wcup", O_WAR + V((0, 14, 1.2)), (0.08, 0.08, 0.1), mat("cup", (0.9, 0.85, 0.6)))
    for k in range(9): FIGHTERS.append(rig(fighter(k), O_WAR + V((RNG.uniform(-5, 5), 9 + k * 0.8, 0)), 0, adult=False))
    for k in range(100): CROWD.append(dummy(f"c{k}", O_WAR + V((RNG.uniform(-7, 7), RNG.uniform(7, 26), 0)), h=RNG.uniform(0.95, 1.12)))
    # ---- gate (37-41 s)
    ground(O_GATE, 60, (0.03, 0.035, 0.05)); light("gl", O_GATE + V((0, 6, 5)), 3000, (0.5, 0.6, 1)); light("gw", O_GATE + V((-3, 1, 2.5)), 700, (1, 0.6, 0.3))
    for s in (-1, 1): box(f"gp{s}", O_GATE + V((s * 2.2, 3, 2.4)), (0.7, 0.7, 4.8), mat("gp", (0.1, 0.04, 0.04)))
    box("gb", O_GATE + V((0, 3, 4.9)), (5.6, 0.8, 0.5), mat("gb", (0.1, 0.04, 0.04)))
    global gate_g, gate_mom
    gate_g = rig(K.HERO_V1, O_GATE + V((0, -3, 0)), 0, adult=True, void=True)
    gate_mom = rig(MOM, O_GATE + V((1.6, 3.4, 0)), 0, adult=False)
    # ---- fantasy (41-60 s)
    ground(O_FANT, 90, (0.25, 0.4, 0.2)); ball("sky", O_FANT, 60, mat("sky", (1.0, 0.78, 0.55), 1.6))
    ball("moon1", O_FANT + V((-14, 30, 22)), 3.0, mat("m1", (1, 1, 0.95), 6)); ball("moon2", O_FANT + V((10, 34, 26)), 1.6, mat("m2", (0.8, 0.85, 1), 6))
    for k in range(5): box(f"cs{k}", O_FANT + V((14 + k * 1.2, 40, 3 + k * 0.6)), (1.4, 1.4, 6 + k * 1.2), mat("cs", (0.3, 0.3, 0.45)))
    for k in range(16): ball(f"fl{k}", O_FANT + V((RNG.uniform(-8, 8), RNG.uniform(1, 14), RNG.uniform(0.5, 5))), 0.07, mat("fl", (1, 1, 0.7), 8))
    light("fs", O_FANT + V((0, -4, 12)), 12000, (1, 0.9, 0.8), size=2)
    global fant_g, knight, fireball, fl_l
    fant_g = rig(K.HERO_V1, O_FANT + V((0, 0, 0)), 180, adult=True, void=True)
    knight = rig(KNIGHT, O_FANT + V((0, 9, 0)), 0, adult=False)
    fireball = ball("fireball", O_FANT + V((0, 9, -60)), 0.4, mat("fb2", (1, 0.5, 0.1), 12))
    fl_l = light("fbl", O_FANT + V((0, 9, -60)), 2500, (1, 0.5, 0.15), size=0.5)
    # ---- dark close-up set
    global d_kid, d_adult, d_human
    d_kid = rig(KID, O_DARK + V((-3, 0, 0)), 0, adult=False, void=True)
    d_adult = rig(K.HERO_V1, O_DARK + V((0, 0, 0)), 0, adult=True, void=True)
    d_human = rig(K.HERO_V1, O_DARK + V((3, 0, 0)), 0, adult=True, void=False)
    for p in (-3, 0, 3): light(f"dk{p}", O_DARK + V((p + 0.5, -1.3, 2.0)), 110, (0.9, 0.9, 1)); light(f"dkb{p}", O_DARK + V((p - 0.7, -1.0, 1.5)), 60, (1, 0.6, 0.4))

# ------------------------------------------------------------------ action
HITS_BIG = [8.2, 13.2, 19.8, 22.6, 23.5, 29.0, 52.0]
HITS_SMALL = [17.8, 18.3, 18.8, 19.3, 22.0, 22.3, 22.9, 23.2, 26.0]
HITS = sorted(HITS_BIG + HITS_SMALL)

def walk(g, t0, t1, p0, p1, hz=2.0, base_z=None):
    """Walk-pose shuffle from p0 to p1 over [t0, t1] (feet slide; rough)."""
    bz = g["base_z"] if base_z is None else base_z
    key(g, F(t0), V(p0) + V((0, 0, bz))); key(g, F(t1), V(p1) + V((0, 0, bz)))
    n = max(2, int((t1 - t0) * hz * 2))
    for k in range(n + 1): pose(g, F(t0 + (t1 - t0) * k / n), "walk", phase=(k % 2) * 0.5)

def animate():
    ALL = [hall_kid, hall_mom, court_kid, court_mom, teen, master, d_mom, ban_g, war_g, war_mom, gate_g, gate_mom, fant_g, knight, d_kid, d_adult, d_human] + FIGHTERS
    for g in ALL: pose(g, 1, "stand")
    # ---- 1-6 hall: the boy lies at his feet; at 4.2 the mother kneels and takes his hand
    key(hall_boy, F(0), O_HALL + V((0.2, 1.7, 0.2)), (RAD(-88), 0, 0.5)); key(hall_boy, F(6), O_HALL + V((0.2, 1.7, 0.2)), (RAD(-88), 0, 0.5))
    key(hall_mom, F(3.8), O_HALL + V((-1.3, 0.4, hall_mom["base_z"])), (0, 0, math.pi)); key(hall_mom, F(4.6), O_HALL + V((-0.45, 0.5, hall_mom["base_z"] - 0.45)), (0, 0, math.pi))
    pose(hall_mom, F(3.8), "stand"); pose(hall_mom, F(4.6), "kneel")
    pose(hall_kid, F(2.0), "guard"); pose(hall_kid, F(3.0), "stand")
    # ---- 6-10 courtyard: he walks to the kids, mother steps in and slaps him at 8.2, he goes back
    walk(court_kid, 6.0, 7.9, (0, -1.0, 0), (0, 3.2, 0), 2.2)
    key(court_kid, F(8.2), V(O_COURT) + V((0, 3.2, court_kid["base_z"])), (0, 0, math.pi)); key(court_kid, F(8.35), O_COURT + V((-0.25, 3.15, court_kid["base_z"])), (0, 0, math.pi + RAD(38)))
    pose(court_kid, F(8.2), "stand"); pose(court_kid, F(8.35), "stand")
    key(court_kid, F(8.9), O_COURT + V((-0.25, 3.15, court_kid["base_z"])), (0, 0, math.pi + RAD(38))); key(court_kid, F(9.1), O_COURT + V((-0.2, 3.1, court_kid["base_z"])), (0, 0, 0))
    walk(court_kid, 9.1, 10.0, (-0.2, 3.1, 0), (0, 1.2, 0), 2.0)
    key(court_mom, F(6.8), V(O_COURT) + V((-4.0, 4.2, court_mom["base_z"])), (0, 0, RAD(-90))); key(court_mom, F(7.9), O_COURT + V((-0.1, 4.25, court_mom["base_z"])), (0, 0, RAD(-90)))
    key(court_mom, F(8.0), O_COURT + V((-0.1, 4.25, court_mom["base_z"])), (0, 0, 0))
    for k, t in enumerate([6.8 + i * 0.28 for i in range(5)]): pose(court_mom, F(t), "walk", phase=(k % 2) * 0.5)
    pose(court_mom, F(8.0), "wrist"); pose(court_mom, F(8.12), "slap"); pose(court_mom, F(8.2), "slap"); pose(court_mom, F(8.6), "stand")
    key(court_mom, F(10.0), O_COURT + V((-0.1, 4.25, court_mom["base_z"])), (0, 0, 0))
    for k, d in enumerate(play):
        for i in range(16):
            a = i * 0.7 + k; key(d, F(6 + i * 0.25), O_COURT + V((-2 + k * 1.3 + math.sin(a) * 0.8, 10.5 + math.cos(a) * 0.8, 0)))
    # ---- 10-15 dojo: the master attacks, is thrown (aikido), kata, the bat breaks on the shin at 13.2
    pose(teen, F(10.0), "guard"); pose(teen, F(10.45), "wrist"); pose(teen, F(10.7), "wrist"); pose(teen, F(11.3), "guard")
    key(teen, F(10.0), O_DOJO + V((0, 0, teen["base_z"])), (0, 0, math.pi)); key(teen, F(10.45), O_DOJO + V((0.6, 0, teen["base_z"])), (0, 0, math.pi + RAD(-35))); key(teen, F(11.2), O_DOJO + V((0.4, 0, teen["base_z"])), (0, 0, math.pi))
    pose(master, F(10.0), "guard"); pose(master, F(10.35), "punch_R"); pose(master, F(10.7), "stand")
    key(master, F(10.0), O_DOJO + V((0, 2.4, master["base_z"])), (0, 0, 0)); key(master, F(10.4), O_DOJO + V((0.2, 1.1, master["base_z"])), (0, 0, 0))
    key(master, F(10.75), O_DOJO + V((0.9, 0.3, 1.4)), (RAD(-100), 0, 0)); key(master, F(11.1), O_DOJO + V((1.2, -0.6, 0.25)), (RAD(-88), 0, 0))
    key(master, F(12.0), O_DOJO + V((1.2, -0.6, 0.25)), (RAD(-88), 0, 0)); key(master, F(12.6), O_DOJO + V((1.5, 2.2, master["base_z"])), (0, 0, 0))
    for t, p in ((11.8, "guard"), (12.2, "punch_R"), (12.45, "punch_L"), (12.7, "guard"), (13.2, "kick_R"), (13.7, "guard"), (14.5, "stand")): pose(teen, F(t), p)
    key(bat1, F(12.5), O_DOJO + V((1.0, 1.4, -40))); key(bat1, F(12.6), O_DOJO + V((0, 1.5, 0.62)), (0, 0, 0)); key(bat1, F(13.15), O_DOJO + V((0, 1.5, 0.62)), (0, 0, 0)); key(bat1, F(13.6), O_DOJO + V((-1.2, 2.5, 0.2)), (0.3, 0, 1.1))
    key(bat2, F(12.5), O_DOJO + V((1.0, 1.4, -40))); key(bat2, F(12.6), O_DOJO + V((0, 1.4, 0.55)), (0, 0, 0)); key(bat2, F(13.15), O_DOJO + V((0, 1.4, 0.55)), (0, 0, 0)); key(bat2, F(13.6), O_DOJO + V((1.4, 2.7, 0.15)), (0.2, 0, -1.2))
    # ---- 15-17 cloak and banners
    key(cloak, F(15), O_BAN + V((0, 1.5, 0.03)), (0, 0, 0)); key(cloak, F(15.8), O_BAN + V((0, 1.5, 0.03)), (0, 0, 0)); key(cloak, F(16.2), O_BAN + V((0.0, 0.5, 1.45)), (RAD(-80), 0, 0), (1.3, 1.9, 0.05))
    pose(ban_g, F(15), "stand"); pose(ban_g, F(15.8), "wrist"); pose(ban_g, F(16.3), "stand")
    for k, b in enumerate(banners):
        t = 15.6 + k * 0.17
        key(b, F(t), None, (0, 0, 0)); key(b, F(t + 0.3), None, (math.pi / 2 * (1 if k % 2 else -1), 0, 0))
    war_action(); gate_action(); fant_action()
    for fl in fires:
        for t in range(F(17), F(37), 3):
            fl.data.energy = 3500 * RNG.uniform(0.7, 1.3); fl.data.keyframe_insert("energy", frame=t)
    for ht in HITS_BIG:
        for fr_, v in ((F(ht) - 1, 0.3), (F(ht), 3.0), (F(ht) + 2, 0.3)):
            scn.view_settings.exposure = v; scn.view_settings.keyframe_insert("exposure", frame=fr_)
    for g in ALL: linear_bones(g)

def war_action():
    base = O_WAR; wg = war_g; bz = wg["base_z"]
    key(wg, F(15), base + V((0, 0, bz)), (0, 0, math.pi)); pose(wg, F(16.9), "stand")
    t0s = (17.4, 17.9, 18.4, 18.9, 19.4, 19.5)
    for i, (f_, t0) in enumerate(zip(FIGHTERS[:6], t0s)):
        x = (-0.4, 0.5, -0.3, 0.4, -0.5, 0.3)[i]
        key(f_, 1, base + V((x * 3, 9 + i, f_["base_z"])), (0, 0, 0)); key(f_, F(t0 - 0.9), base + V((x * 3, 9 + i, f_["base_z"])), (0, 0, 0))
        key(f_, F(t0), base + V((x, 1.5, f_["base_z"])), (0, 0, 0)); key(f_, F(t0 + 0.3), base + V((x, 1.4, f_["base_z"])), (0, 0, 0))
        for k, t in enumerate([t0 - 0.9 + j * 0.3 for j in range(3)]): pose(f_, F(t), "walk", phase=(k % 2) * 0.5)
        pose(f_, F(t0 - 0.05), "guard"); pose(f_, F(t0), "punch_R" if i % 2 == 0 else "punch_L"); pose(f_, F(t0 + 0.3), "stand")
        key(f_, F(t0 + 0.75), base + V((x * 2.5, 4.2 + i * 0.4, 0.2 + f_["base_z"])), (RAD(-85), 0, 0.6 * (-1) ** i))
        key(f_, F(25), base + V((x * 2.5, 4.2 + i * 0.4, 0.2 + f_["base_z"])), (RAD(-85), 0, 0.6 * (-1) ** i))
    for t, p in ((17.65, "punch_R"), (18.15, "punch_L"), (18.65, "kick_R"), (19.15, "punch_R"), (19.65, "punch_R")):
        pose(wg, F(t - 0.2), "guard"); pose(wg, F(t), p); pose(wg, F(t + 0.2), "guard")
    pose(wg, F(19.8), "punch_L"); pose(wg, F(20.1), "stand")
    for j, f_ in enumerate(FIGHTERS[6:9]):
        sx = (-0.9, 0.0, 0.9)[j]; ta = 21.7 + j * 0.15
        key(f_, 1, base + V((sx * 3, 12 + j, f_["base_z"])), (0, 0, 0)); key(f_, F(21.0), base + V((sx * 3, 12 + j, f_["base_z"])), (0, 0, 0))
        key(f_, F(ta), base + V((sx, 1.4, f_["base_z"])), (0, 0, 0)); key(f_, F(ta + 0.5), base + V((sx, 1.3, f_["base_z"])), (0, 0, 0))
        pose(f_, F(21.1), "stand"); pose(f_, F(ta - 0.1), "guard"); pose(f_, F(ta), "punch_R" if j != 1 else "kick_R"); pose(f_, F(ta + 0.5), "stand")
        th = (22.3, 22.6, 23.5)[j]
        key(f_, F(th), base + V((sx, 1.3, f_["base_z"])), (0, 0, 0)); key(f_, F(th + 0.6), base + V((sx * 3, 5 + j, 0.2 + f_["base_z"])), (RAD(-85), 0, 0.5 * (j - 1)))
        key(f_, F(25), base + V((sx * 3, 5 + j, 0.2 + f_["base_z"])), (RAD(-85), 0, 0.5 * (j - 1)))
    for t, p, xo in ((21.8, "guard", 0), (22.0, "punch_R", -0.2), (22.3, "punch_L", 0.1), (22.6, "kick_R", 0.0), (22.9, "punch_R", 0.2), (23.2, "punch_L", 0), (23.5, "punch_R", 0.0)):
        pose(wg, F(t), p); key(wg, F(t), base + V((xo, 0, bz)), (0, 0, math.pi))
    pose(wg, F(24.0), "stand")
    walk(wg, 24.0, 28.0, (0, 0, 0), (0, 3.5, 0), 1.8)
    key(wg, F(24.0), base + V((0, 0, bz)), (0, 0, math.pi))
    pose(wg, F(28.4), "guard"); pose(wg, F(29.0), "punch_R"); pose(wg, F(29.8), "stand")
    key(wg, F(28.0), base + V((0, 3.5, bz)), (0, 0, math.pi)); key(wg, F(29.8), base + V((0, 3.5, bz)), (0, 0, math.pi))
    key(wg, F(31.0), base + V((0, 0, bz)), (0, 0, math.pi))
    c = CROWD; pre, g1, g2, g3 = c[:20], c[20:50], c[50:80], c[80:]
    for ob in pre:
        p = ob.location.copy(); p.z = 0.18; key(ob, 1, p, (RAD(-88), 0, RNG.uniform(0, 6.28)))
    for grp, th in ((g1, 22.6), (g2, 23.5), (g3, 29.0)):
        for k, ob in enumerate(grp):
            p0 = ob.location.copy(); tx = base + V((RNG.uniform(-1.4, 1.4) + (k - len(grp) / 2) * 0.12, 1.7 + RNG.uniform(0, 1.2), 0))
            key(ob, 1, p0, (0, 0, math.pi)); key(ob, F(th - 0.9), p0, (0, 0, math.pi)); key(ob, F(th - 0.05), tx, (0, 0, math.pi)); key(ob, F(th), tx, (0, 0, math.pi))
            key(ob, F(th + 0.5), base + V((RNG.uniform(-5, 5), 6 + RNG.uniform(0, 5), 0.15)), (RAD(-88), 0, RNG.uniform(-1, 1)))
    for k, ob in enumerate(c):
        a = k / len(c) * math.tau; r = 3.5 + (k % 4) * 1.2
        p = base + V((r * math.cos(a), r * math.sin(a), 0)); yaw = math.atan2(-(p.x - base.x), p.y - base.y) + math.pi
        key(ob, F(30.95), None, (RAD(-88), 0, 0)); key(ob, F(31.0), p, (0, 0, yaw), (1, 1, 0.62)); key(ob, F(37.0), p, (0, 0, yaw), (1, 1, 0.62))
    for ob in c: constant(ob)
    mm = war_mom
    key(mm, 1, base + V((0, 10, -60)), (0, 0, 0)); key(mm, F(33.9), base + V((0, 10, -60)), (0, 0, 0)); key(war_cup, 1, base + V((0.1, 10, -60))); key(war_cup, F(33.9), base + V((0.1, 10, -60)))
    key(mm, F(34), base + V((0, 9, mm["base_z"])), (0, 0, 0)); key(mm, F(36.0), base + V((0, 1.5, mm["base_z"])), (0, 0, 0))
    for k, t in enumerate([34 + i * 0.3 for i in range(7)]): pose(mm, F(t), "walk", phase=(k % 2) * 0.5)
    pose(mm, F(36.0), "wrist")
    key(war_cup, F(34), base + V((0.1, 9, 1.15))); key(war_cup, F(36.0), base + V((0.1, 1.4, 1.1))); key(war_cup, F(36.4), base + V((0.1, 1.4, 1.1))); key(war_cup, F(36.9), base + V((0.0, 0.25, 1.65)))
    pose(wg, F(32.0), "guard"); pose(wg, F(33.0), "stand"); pose(wg, F(36.0), "wrist"); pose(wg, F(36.9), "wrist"); pose(wg, F(37.0), "stand")

def gate_action():
    gg = gate_g
    walk(gg, 37.0, 39.0, (0, -1.5, 0), (0, 0.8, 0), 1.4, gg["base_z"])
    pose(gg, F(39.1), "stand"); pose(gg, F(40.0), "kneel")
    key(gg, F(39.1), O_GATE + V((0, 0.9, gg["base_z"]))); key(gg, F(40.0), O_GATE + V((0, 1.0, gg["base_z"] - 0.55)))
    pose(gate_mom, F(37), "wrist")

def fant_action():
    fg = fant_g; bz = fg["base_z"]
    key(fg, F(43), O_FANT + V((0, 0, 0.25)), (RAD(-85), 0, math.pi)); key(fg, F(44.8), O_FANT + V((0, 0, 0.25)), (RAD(-85), 0, math.pi)); key(fg, F(46.2), O_FANT + V((0, 0, bz)), (0, 0, math.pi))
    pose(fg, F(46.2), "stand"); pose(fg, F(46.6), "guard")
    key(fireball, F(46.0), O_FANT + V((0, 9, -60))); key(fl_l, F(46.0), O_FANT + V((0, 9, -60)))
    key(fireball, F(46.5), O_FANT + V((0, 9, 1.5))); key(fireball, F(49.0), O_FANT + V((0.2, 1.3, 1.5))); key(fireball, F(49.2), O_FANT + V((0.2, -3, 1.5)))
    key(fl_l, F(46.5), O_FANT + V((0, 9, 1.5))); key(fl_l, F(49.0), O_FANT + V((0.2, 1.3, 1.5))); key(fl_l, F(49.2), O_FANT + V((0.2, -3, 1.5)))
    key(fg, F(48.6), O_FANT + V((0, 0, bz))); key(fg, F(49.1), O_FANT + V((-0.9, 0.2, bz))); key(fg, F(50.0), O_FANT + V((-0.9, 0.2, bz))); key(fg, F(52.0), O_FANT + V((-0.4, 7.4, bz)))
    pose(fg, F(49.1), "guard"); pose(fg, F(51.5), "guard"); pose(fg, F(52.0), "punch_R"); pose(fg, F(53.0), "guard")
    pose(knight, F(46.0), "wrist")
    key(knight, F(52.0), O_FANT + V((0, 9, knight["base_z"])), (0, 0, 0)); key(knight, F(53.0), O_FANT + V((0.5, 13, knight["base_z"])), (RAD(-70), 0, 0))
    key(knight, F(54.0), O_FANT + V((0.5, 12.5, knight["base_z"])), (0, 0, 0)); key(knight, F(56.0), O_FANT + V((0.5, 12.5, knight["base_z"])), (0, 0, 0))

# ------------------------------------------------------------------ camera
cam = None
def make_cam():
    global cam, cd
    cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05; cd.clip_end = 3000; cd.dof.use_dof = False
    cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam; cam.rotation_mode = "QUATERNION"
def lerp(a, b, u): return a + (b - a) * u
def vlerp(a, b, u): return V(a) + (V(b) - V(a)) * u
def ease(u): return u * u * (3 - 2 * u)
def head_pos(g):
    scn.frame_set(1); bpy.context.view_layer.update(); return V(g.matrix_world @ g.pose.bones["head"].head)
HEADP = {}

def shots():
    S = []
    def add(t0, t1, fn): S.append((t0, t1, fn))
    def lin(a, b, t0, t1, t): return vlerp(a, b, ease(min(1, max(0, (t - t0) / (t1 - t0)))))
    H, Co, D, W_, G, Fa, Dk, B = O_HALL, O_COURT, O_DOJO, O_WAR, O_GATE, O_FANT, O_DARK, O_BAN
    add(0, 1.6, lambda t: (lin(H + V((-3.5, -4.5, 0.6)), H + V((-2.5, -3.5, 0.8)), 0, 1.6, t), H + V((0, 3, 1.1)), 26, -3))
    add(1.6, 3, lambda t: (lin(H + V((2.4, -0.4, 0.9)), H + V((1.4, -0.2, 1.0)), 1.6, 3, t), H + V((0, 0.6, 1.0)), 50, 5))
    add(3, 4.2, lambda t: (H + V((-3.2, 0.5, 1.0)), H + V((0, 1.0, 0.7)), 32, -6))
    add(4.2, 5.0, lambda t: (H + V((-0.9, -1.0, 0.8)), H + V((-0.5, 0.5, 0.75)), 65, 8))
    add(5.0, 6, lambda t: (H + V((0.9, -0.4, 1.15)), H + V((0.0, 0.7, 1.05)), 80, -4))
    add(6, 7.7, lambda t: (Co + V((4.2, lerp(-1, 2.8, (t - 6) / 1.7), 1.2)), Co + V((0, lerp(0, 3.2, (t - 6) / 1.7), 1.0)), 32, 0))
    add(7.7, 8.1, lambda t: (Co + V((0.2, 2.2, 1.0)), Co + V((0, 4.25, 1.0)), 28, -9))
    add(8.1, 8.6, lambda t: (Co + V((2.2, 3.7, 1.0)), Co + V((-0.1, 3.7, 1.0)), 85, 12))
    add(8.6, 10, lambda t: (Co + V((-2.0, 0.2, 0.4)), Co + V((0, 3.0, 0.9)), 30, -7))
    add(10, 11.0, lambda t: (D + V((-4.2, 1.4, 1.2)), D + V((0.4, 1.2, 1.0)), 32, 0))
    add(11.0, 11.7, lambda t: (D + V((1.6, -2.0, 0.4)), D + V((1.0, -0.6, 0.4)), 30, 14))
    add(11.7, 12.9, lambda t: (D + V((-3.6, 0.2, 1.1)), D + V((0, 0.3, 1.0)), 38, -5))
    add(12.9, 13.5, lambda t: (D + V((0.9, 0.3, 0.55)), D + V((0, 1.5, 0.6)), 55, 15))
    add(13.5, 14.2, lambda t: (D + V((-2.5, 3.0, 1.3)), D + V((-0.6, 2.2, 0.4)), 40, -10))
    add(14.2, 15, lambda t: (D + V((-4, 0.3, 1.3)), D + V((4.5, 5.2, 1.5)), 40, 0))
    add(15, 15.9, lambda t: (B + V((0.8, 0.4, 0.5)), B + V((0, 1.5, 0.05)), 45, -12))
    add(15.9, 16.4, lambda t: (B + V((-1.6, 0.8, 1.2)), B + V((0, 0.4, 1.3)), 45, 8))
    add(16.4, 17, lambda t: (B + V((lerp(-5, 5, (t - 16.4) / 0.6), -2.5, 1.0)), B + V((0, 5.5, 1.2)), 32, lerp(-6, 6, (t - 16.4) / 0.6)))
    def GP(t):
        if t < 24: return V((0, 0, 0))
        if t < 28: return V((0, lerp(0, 3.5, (t - 24) / 4), 0))
        return V((0, 3.5, 0))
    def setup(name, t):
        g = W_ + GP(t)
        return {
            "side": (g + V((-3.2, 0.6, 1.4)), g + V((0, 0.5, 1.3)), 45, 0),
            "side_low": (g + V((3.0, 0.4, 0.5)), g + V((0, 0.7, 1.2)), 35, -14),
            "over_enemy": (g + V((0.55, 2.4, 1.7)), g + V((0, 0, 1.5)), 50, 8),
            "over_gojo": (g + V((-0.45, -1.3, 1.75)), g + V((0, 3, 1.3)), 50, -6),
            "fist": (g + V((-1.0, 0.2, 1.35)), g + V((0.1, 1.0, 1.4)), 85, 12),
            "face": (g + V((0.9, 1.4, 1.75)), g + V((0, 0, 1.75)), 90, -10),
            "fear": (g + V((0.2, 1.8, 0.25)), g + V((0, 0, 1.8)), 28, 0),
            "wide": (g + V((-2.6, -3.0, 1.2)), g + V((0, 6, 1.4)), 30, 0),
            "head_on": (g + V((0, 6.5, 0.9)), g + V((0, 0, 1.5)), 34, 0),
        }[name]
    add(17, 17.4, lambda t: setup("fear", t))
    def cuts(t0, t1, names, dts):
        t = t0; k = 0
        while t < t1:
            dt = dts[k % len(dts)]; nm = names[k % len(names)]
            add(t, min(t1, t + dt), (lambda n: (lambda tt: setup(n, tt)))(nm)); t += dt; k += 1
    cuts(17.4, 20.0, ["side", "over_enemy", "fist", "side_low", "over_gojo", "face", "side", "fist"], [0.3, 0.4])
    add(20, 21.5, lambda t: (lin(HEADP["adult"] + V((0.03, -0.62, 0)), HEADP["adult"] + V((0.02, -0.4, 0)), 20, 21.5, t), HEADP["adult"], 95, 0))
    cuts(21.5, 24.0, ["fist", "face", "side_low", "over_enemy", "side", "fist", "over_gojo", "face"], [0.17])
    cuts(24.0, 28.0, ["head_on", "side_low", "head_on", "side", "fist"], [0.5, 0.35])
    add(28, 28.7, lambda t: setup("side", t)); add(28.7, 29.0, lambda t: setup("fist", t)); add(29.0, 29.25, lambda t: setup("over_enemy", t))
    add(29.25, 30.1, lambda t: setup("side_low", t)); add(30.1, 31, lambda t: setup("wide", t))
    def s7(t):
        a = lerp(-0.7, 0.7, (t - 31) / 3); return (W_ + V((9 * math.sin(a), -9 * math.cos(a) + 0.5, 3.2)), W_ + V((0, 0, 1.2)), 28, lerp(-4, 4, (t - 31) / 3))
    add(31, 33, s7); add(33, 34, lambda t: (W_ + V((3.0, 2.0, 1.2)), W_ + V((0, 1.5, 1.4)), 38, -8))
    add(34, 35.6, lambda t: (W_ + V((3.6, lerp(8, 4, (t - 34) / 1.6), 1.3)), W_ + V((0, lerp(10, 2, (t - 34) / 1.6), 1.2)), 35, 0))
    add(35.6, 36.3, lambda t: (W_ + V((0.5, 0.15, 1.7)), W_ + V((0, 1.5, 1.6)), 70, 4))
    add(36.3, 37, lambda t: (W_ + V((0.35, 1.5, 1.75)), W_ + V((0, 0, 1.7)), 85, -4))
    add(37, 38.8, lambda t: (lin(G + V((3.2, -4.5, 1.3)), G + V((2.4, -2.4, 1.3)), 37, 38.8, t), G + V((0, 0.5, 1.2)), 35, lerp(0, -8, (t - 37) / 1.8)))
    add(38.8, 40, lambda t: (lin(G + V((1.6, -0.6, 0.9)), G + V((1.0, 0.0, 0.8)), 38.8, 40, t), G + V((0, 1.0, 1.0)), 50, -14))
    add(40, 41, lambda t: (lin(HEADP["adult"] + V((0.03, -0.7, 0)), HEADP["adult"] + V((0.03, -0.5, 0)), 40, 41, t), HEADP["adult"], 95, 0))
    add(41, 43, lambda t: (lin(HEADP["human"] + V((0.03, -0.7, 0)), HEADP["human"] + V((0.03, -0.5, 0)), 41, 43, t), HEADP["human"], 95, 0))
    add(43, 46, lambda t: (lin(Fa + V((0.5, -1.6, 0.9)), Fa + V((2.5, -6.5, 2.2)), 43, 46, t), Fa + V((0, 1, 0.9)), lerp(60, 30, (t - 43) / 3), 0))
    add(46, 47.6, lambda t: (Fa + V((3.4, 3.5, 1.4)), Fa + V((0, 4.5, 1.3)), 32, -6))
    add(47.6, 48.6, lambda t: (Fa + V((-0.5, -0.4, 1.75)), Fa + V((0, 4, 1.5)), 75, 10))
    add(48.6, 49.4, lambda t: (Fa + V((-2.6, 1.0, 0.9)), Fa + V((-0.5, 1.0, 1.4)), 28, -14))
    add(49.4, 50, lambda t: (Fa + V((1.6, 0.1, 1.6)), Fa + V((-0.9, 0.3, 1.6)), 70, 6))
    add(50, 51.0, lambda t: (Fa + V((-3.4, lerp(1, 6, (t - 50) / 1.0), 1.2)), Fa + V((-0.7, lerp(1, 6.5, (t - 50) / 1.0), 1.4)), 34, -8))
    add(51.0, 51.8, lambda t: (Fa + V((1.2, 8.4, 0.5)), Fa + V((-0.4, 6.8, 1.4)), 28, 14))
    add(51.8, 52.2, lambda t: (Fa + V((1.4, 7.6, 1.5)), Fa + V((-0.4, 7.4, 1.5)), 75, -12))
    add(52.2, 53.0, lambda t: (Fa + V((-1.4, 5.8, 1.85)), Fa + V((0.1, 9.5, 1.4)), 45, 6))
    add(53.0, 54, lambda t: (Fa + V((-0.5, 8.2, 0.3)), Fa + V((-0.4, 7.4, 1.8)), 26, 0))
    add(54, 56, lambda t: (lin(Fa + V((0.5, 7.0, 1.7)), Fa + V((0.5, 7.6, 1.7)), 54, 56, t), Fa + V((0.5, 13, 1.7)), 100, 0))
    add(56, 60, lambda t: (lin(HEADP["adult"] + V((0.03, -0.8, 0)), HEADP["adult"] + V((0.03, -0.45, 0)), 56, 60, t), HEADP["adult"], 95, 0))
    return S

def shake_amp(t):
    a = 0.0
    for h in HITS:
        if h <= t < h + 0.3: a = max(a, (0.14 if h in HITS_BIG else 0.05) * (1 - (t - h) / 0.3))
    return a

def key_camera(S):
    prefs.keyframe_new_interpolation_type = "LINEAR"
    for f in range(1, NF + 1):
        t = (f - 1) / FPS
        seg = next((s for s in S if s[0] <= t < s[1]), S[-1])
        loc, look, lens, roll = seg[2](t)
        a = shake_amp(t); r = random.Random(f)
        loc = V(loc) + V((r.uniform(-a, a), r.uniform(-a, a), r.uniform(-a, a))); look = V(look) + V((r.uniform(-a, a) * 0.5, 0, r.uniform(-a, a) * 0.5))
        fwd = (look - loc).normalized()
        q = fwd.to_track_quat("-Z", "Y"); q = q @ Quaternion((0, 0, 1), RAD(roll))
        cam.location = loc; cam.rotation_quaternion = q; cd.lens = lens
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f); cd.keyframe_insert("lens", frame=f)
    scn.frame_start, scn.frame_end = 1, NF

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    wd = scn.world or bpy.data.worlds.new("w"); scn.world = wd; wd.use_nodes = True
    bg = wd.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.004, 0.004, 0.006, 1); bg.inputs[1].default_value = 1.0
    build_all()
    for k_, g_ in (("kid", d_kid), ("adult", d_adult), ("human", d_human)): HEADP[k_] = head_pos(g_)
    animate(); make_cam(); key_camera(shots())
    C.render_settings(SCALE, SAMPLES); scn.view_settings.exposure = 0.3
    scn.render.fps = FPS
    out = os.path.join(HERE, "frames"); os.makedirs(out, exist_ok=True)
    stills = os.environ.get("STILLS")
    if stills:
        sd = os.path.join(HERE, "stills"); os.makedirs(sd, exist_ok=True)
        for s in stills.split(","):
            f = F(float(s)); scn.frame_set(f); scn.render.filepath = os.path.join(sd, f"t{float(s):05.2f}.png"); bpy.ops.render.render(write_still=True)
        sys.exit(0)
    for f in range(FIRST, LAST + 1, STEP):
        p = os.path.join(out, f"f{f:04d}.png")
        if os.path.exists(p): continue
        scn.frame_set(f); scn.render.filepath = p; bpy.ops.render.render(write_still=True)
