"""Kuro Oni ep 1: ROUGH 3D PROTOTYPE (throwaway). Real Gojo rig (Aura Monster hero), simple sets, dummy crowd, anime camera.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/film.py [scale%] [first] [last] [step]
Renders PNGs to shorts/kuro_oni/frames/ (existing frames skipped). env: SAMPLES (default 8), STILLS="t1,t2" seconds -> stills/.
Timing and shots follow docs/superpowers/specs/2026-11-25-kuro-oni-design.md."""
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
def key(ob, f, loc=None, rot=None, scale=None, interp=None):
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
    return box("ground", (c[0], c[1], -0.05), (size, size, 0.1), mat("gr", col))

# ------------------------------------------------------------------ rigs and poses
def rig(style, loc, heading=0.0, adult=True, scale=1.0, void=False):
    st = dict(style)
    if void: st["void_eyes"] = True
    if adult: g, _ = ch.build_v1(P, (0, 0, 0), st, pose_mode="stand", void_eyes=void)
    else: g, _ = ch.build(P, (0, 0, 0), st, pose_mode="stand", heading=0)
    g.location = V(loc) + V((0, 0, g["ground_rest"] * scale)); g.scale = (scale,) * 3
    g.rotation_euler = (0, 0, math.radians(heading)); g["base_z"] = g["ground_rest"] * scale
    return g
def pose(g, f, name, phase=0.0):
    """Key a named pose on every animated bone at frame f. Forward is -Y in armature space."""
    scn.frame_set(f); ch.posed(g, "stand"); aim = ch._aimer(g)
    def arms(side, sx, d, lo=None, bend=None):
        for b in ("upperarm01", "upperarm02"): aim(f"{b}.{side}", d)
        for b in ("lowerarm01", "lowerarm02", "wrist"): aim(f"{b}.{side}", lo or d)
    if name == "guard":
        arms("L", 1, (0.25, -0.35, -0.8), (0.1, -0.8, 0.7)); arms("R", -1, (-0.25, -0.35, -0.8), (-0.1, -0.8, 0.7))
    elif name == "punch_R":
        arms("L", 1, (0.25, -0.35, -0.8), (0.1, -0.8, 0.7)); arms("R", -1, (-0.05, -1.0, 0.08))
    elif name == "punch_L":
        arms("R", -1, (-0.25, -0.35, -0.8), (-0.1, -0.8, 0.7)); arms("L", 1, (0.05, -1.0, 0.08))
    elif name == "wrist":
        arms("L", 1, (0.15, -1.0, -0.25)); arms("R", -1, (-0.15, -1.0, -0.25))
    elif name == "kick_R":
        arms("L", 1, (0.25, -0.35, -0.8), (0.1, -0.8, 0.7)); arms("R", -1, (-0.25, -0.35, -0.8), (-0.1, -0.8, 0.7))
        for b in ("upperleg01", "upperleg02"): aim(f"{b}.R", (-0.05, -1.0, 0.05))
        for b in ("lowerleg01", "lowerleg02"): aim(f"{b}.R", (-0.05, -1.0, -0.15))
    elif name == "walk":
        ch._walk_phase(g, aim, phase)
    elif name == "kneel":
        arms("L", 1, (0.05, -0.3, -1)); arms("R", -1, (-0.05, -0.3, -1))
        for side, sx in (("L", 1), ("R", -1)):
            for b in ("upperleg01", "upperleg02"): aim(f"{b}.{side}", (sx * 0.1, -1.0, -0.1))
            for b in ("lowerleg01", "lowerleg02"): aim(f"{b}.{side}", (sx * 0.1, 0.1, -1.0))
    elif name == "pockets":
        pass
    bpy.context.view_layer.update()
    for b in ch.ANIM_BONES: g.pose.bones[b].keyframe_insert("rotation_quaternion", frame=f)
def hold(g):
    """Bone keys between poses are linear so punches snap; keep it."""
    ad = g.animation_data
    from bpy_extras import anim_utils
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    for fc in cb.fcurves:
        if fc.data_path.startswith("pose.bones"):
            for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

DUMMY_ME = None
def dummy(name, loc, col=(0.02, 0.02, 0.03), h=1.0):
    global DUMMY_ME
    if DUMMY_ME is None:
        bm = bmesh.new(); bmesh.ops.create_cone(bm, segments=10, radius1=0.26, radius2=0.2, depth=1.1, matrix=Matrix.Translation((0, 0, 0.62)))
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.13, matrix=Matrix.Translation((0, 0, 1.4)))
        DUMMY_ME = bpy.data.meshes.new("dummy"); bm.to_mesh(DUMMY_ME); bm.free()
    ob = bpy.data.objects.new(name, DUMMY_ME); scn.collection.objects.link(ob); ob.location = loc
    if not ob.data.materials: ob.data.materials.append(mat("dum", col))
    ob.scale = (1, 1, h); return ob

# ------------------------------------------------------------------ sets (each far from the others)
O_HALL, O_DOJO, O_MAP, O_WAR, O_GATE, O_FANT, O_DARK = [V((x, 0, 0)) for x in (0, 100, 200, 300, 400, 500, 600)]
ELDERS = []; CROWD = []

def build_all():
    # ---- hall: floor, back wall, elders, mother, kid
    ground(O_HALL, 40, (0.18, 0.12, 0.08)); box("hwall", O_HALL + V((0, 7, 3)), (30, 0.3, 6), mat("hw", (0.12, 0.08, 0.06)))
    for k in range(6):
        e = dummy(f"elder{k}", O_HALL + V((-5 + k * 2.0, 5.5, 0)), (0.03, 0.02, 0.02), 1.05); e.rotation_euler = (0, 0, math.pi); ELDERS.append(e)
        light(f"hl{k}", O_HALL + V((-5 + k * 2.0, 4, 3.2)), 700, (1, 0.7, 0.4))
    light("hkey", O_HALL + V((0, -2.5, 2.2)), 500, (1, 0.8, 0.6))
    global hall_mom, hall_kid, cup
    hall_mom = rig(K.W1, O_HALL + V((-0.45, 1.0, 0)), 180, adult=False, void=False)
    hall_kid = rig(K.KID2, O_HALL + V((0.2, 1.0, 0)), 180, adult=False, void=True)
    cup = box("cup", O_HALL + V((0.9, 3.8, 1.2)), (0.08, 0.08, 0.1), mat("cup", (0.9, 0.85, 0.6)))
    # ---- dojo
    ground(O_DOJO, 40, (0.25, 0.18, 0.12)); box("dwall", O_DOJO + V((0, 6, 3)), (30, 0.3, 6), mat("dw", (0.2, 0.14, 0.1)))
    light("dl", O_DOJO + V((0, 0, 4)), 1800, (1, 0.85, 0.7))
    global teen, bat1, bat2, holder
    teen = rig(K.HERO_V1, O_DOJO + V((0, 0, 0)), 180, adult=True, scale=0.88, void=True)
    holder = dummy("holder", O_DOJO + V((0, 2.4, 0)), (0.05, 0.05, 0.06)); holder.rotation_euler = (0, 0, 0)
    bat1 = box("bat1", O_DOJO + V((0, 1.4, 0.55)), (0.07, 0.9, 0.07), mat("bat", (0.4, 0.4, 0.45)))
    bat2 = box("bat2", O_DOJO + V((0, 1.4, 0.55)), (0.07, 0.9, 0.07), mat("bat", (0.4, 0.4, 0.45)))
    # ---- map: dark floor, 8 red banners that topple
    ground(O_MAP, 60, (0.02, 0.03, 0.05)); light("ml", O_MAP + V((0, -4, 6)), 3000, (0.6, 0.7, 1))
    global banners
    banners = [box(f"ban{k}", O_MAP + V((-4.2 + k * 1.2, 2.5, 1.2)), (0.7, 0.06, 2.4), mat("ban", (0.65, 0.05, 0.05), 0)) for k in range(8)]
    # ---- war street
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
    war_mom = rig(K.W1, O_WAR + V((0, 14, 0)), 0, adult=False)
    war_cup = box("wcup", O_WAR + V((0, 14, 1.2)), (0.08, 0.08, 0.1), mat("cup", (0.9, 0.85, 0.6)))
    for k in range(100):
        CROWD.append(dummy(f"c{k}", O_WAR + V((RNG.uniform(-7, 7), RNG.uniform(5, 26), 0)), h=RNG.uniform(0.95, 1.12)))
    # ---- gate
    ground(O_GATE, 60, (0.03, 0.035, 0.05)); light("gl", O_GATE + V((0, 6, 5)), 3000, (0.5, 0.6, 1)); light("gw", O_GATE + V((-3, 1, 2.5)), 700, (1, 0.6, 0.3))
    for s in (-1, 1): box(f"gp{s}", O_GATE + V((s * 2.2, 3, 2.4)), (0.7, 0.7, 4.8), mat("gp", (0.1, 0.04, 0.04)))
    box("gb", O_GATE + V((0, 3, 4.9)), (5.6, 0.8, 0.5), mat("gb", (0.1, 0.04, 0.04)))
    global gate_g, gate_mom
    gate_g = rig(K.HERO_V1, O_GATE + V((0, -3, 0)), 0, adult=True, void=True)     # walks out toward -Y... (camera side)
    gate_mom = rig(K.W1, O_GATE + V((1.6, 3.4, 0)), 0, adult=False)
    # ---- fantasy
    ground(O_FANT, 90, (0.25, 0.4, 0.2))
    sky = ball("sky", O_FANT, 60, mat("sky", (1.0, 0.78, 0.55), 1.6)); sky.scale = (1, 1, 1)
    ball("moon1", O_FANT + V((-14, 30, 22)), 3.0, mat("m1", (1, 1, 0.95), 6)); ball("moon2", O_FANT + V((10, 34, 26)), 1.6, mat("m2", (0.8, 0.85, 1), 6))
    for k in range(5): box(f"cs{k}", O_FANT + V((14 + k * 1.2, 40, 3 + k * 0.6)), (1.4, 1.4, 6 + k * 1.2), mat("cs", (0.3, 0.3, 0.45)))
    for k in range(16): ball(f"fl{k}", O_FANT + V((RNG.uniform(-8, 8), RNG.uniform(1, 14), RNG.uniform(0.5, 5))), 0.07, mat("fl", (1, 1, 0.7), 8))
    light("fs", O_FANT + V((0, -4, 12)), 12000, (1, 0.9, 0.8), size=2)
    global fant_g, mage, fireball, fl_l
    fant_g = rig(K.HERO_V1, O_FANT + V((0, 0, 0)), 180, adult=True, void=True)
    mage = rig(K.MAN_LONG, O_FANT + V((0, 9, 0)), 0, adult=False)
    fireball = ball("fireball", O_FANT + V((0, 9, 1.5)), 0.4, mat("fb2", (1, 0.5, 0.1), 12))
    fl_l = light("fbl", O_FANT + V((0, 9, 1.5)), 2500, (1, 0.5, 0.15), size=0.5)
    # ---- dark close-up set
    global d_kid, d_adult, d_human
    light("dk1", O_DARK + V((0.6, -1.2, 2.2)), 120, (0.8, 0.85, 1)); light("dk2", O_DARK + V((-0.8, -1.0, 1.6)), 70, (1, 0.6, 0.4))
    d_kid = rig(K.KID2, O_DARK + V((-3, 0, 0)), 0, adult=False, void=True)
    d_adult = rig(K.HERO_V1, O_DARK + V((0, 0, 0)), 0, adult=True, void=True)
    d_human = rig(K.HERO_V1, O_DARK + V((3, 0, 0)), 0, adult=True, void=False)
    for p in (-3, 3): light(f"dkk{p}", O_DARK + V((p + 0.4, -1.2, 2.0)), 110, (0.9, 0.9, 1))

def head_pos(g):
    scn.frame_set(1); bpy.context.view_layer.update()
    return V(g.matrix_world @ g.pose.bones["head"].head)
HEADP = {}
# ------------------------------------------------------------------ action
HITS_BIG = [7.0, 22.4, 23.2, 24.0, 24.8, 52.4]
HITS_SMALL = [13.6, 14.2, 14.7, 15.2, 15.7, 20.5, 21.3]
HITS = sorted(HITS_BIG + HITS_SMALL)

def animate():
    for g in (hall_mom, hall_kid, teen, war_g, war_mom, gate_g, gate_mom, fant_g, mage, d_kid, d_adult, d_human):
        pose(g, 1, "stand")
    # ---- hall: the cup falls at 4.2 s (shot 2: 2.5-5.5)
    key(cup, F(2.5), O_HALL + V((0.9, 3.8, 1.2))); key(cup, F(4.2), O_HALL + V((0.9, 3.8, 1.2))); key(cup, F(4.55), O_HALL + V((0.9, 3.8, 0.04)))
    constant(cup) if False else None
    # ---- dojo (5.5-8): bat held, teen kicks at 7.0, the bat breaks
    key(bat1, F(5.5), O_DOJO + V((0, 1.5, 0.62)), (0, 0, 0)); key(bat1, F(6.95), O_DOJO + V((0, 1.5, 0.62)), (0, 0, 0))
    key(bat1, F(7.0), O_DOJO + V((0, 1.5, 0.62)), (0, 0, 0)); key(bat1, F(7.5), O_DOJO + V((-1.2, 2.5, 0.2)), (0.3, 0, 1.1))
    key(bat2, F(5.5), O_DOJO + V((0, 1.4, 0.55)), (0, 0, 0)); key(bat2, F(6.95), O_DOJO + V((0, 1.4, 0.55)), (0, 0, 0))
    key(bat2, F(7.5), O_DOJO + V((1.4, 2.7, 0.15)), (0.2, 0, -1.2))
    pose(teen, F(5.5), "guard"); pose(teen, F(6.2), "punch_R"); pose(teen, F(6.5), "guard"); pose(teen, F(6.9), "guard")
    pose(teen, F(7.0), "kick_R"); pose(teen, F(7.5), "guard")
    # ---- map (8-11): banners topple one by one
    for k, b in enumerate(banners):
        t = 8.4 + k * 0.28
        key(b, F(t), None, (0, 0, 0)); key(b, F(t + 0.35), None, (math.pi / 2 * (1 if k % 2 else -1), 0, 0))
    # ---- hall: kid + mother already still. dummies in the war set
    crowd_action()
    # ---- war: Gojo's poses (shots 5-9)
    wg = war_g; base = O_WAR
    pose(wg, F(11), "stand"); pose(wg, F(13.3), "stand")
    for t, p in ((13.5, "guard"), (13.62, "punch_R"), (13.8, "guard"), (14.1, "wrist"), (14.22, "guard"), (14.6, "kick_R"), (14.75, "guard"),
                 (15.1, "punch_L"), (15.25, "guard"), (15.6, "wrist"), (15.75, "stand")):
        pose(wg, F(t), p)
    key(wg, F(13.4), base + V((0, 0, wg["base_z"])), (0, 0, math.radians(180)))
    # shot 8: walks toward the camera (y 0 -> 3.5), 19-22
    ph = 0.0
    for k, t in enumerate([19 + i * 0.25 for i in range(13)]):
        pose(wg, F(t), "walk", phase=(k % 2) * 0.5)
    key(wg, F(18.9), base + V((0, 0, wg["base_z"]))); key(wg, F(22.0), base + V((0, 3.5, wg["base_z"])))
    # shot 9 (22-25): the count punches at 22.4/23.2/24.0/24.8, then 25 resets
    for k, t in enumerate((22.4, 23.2, 24.0, 24.8)):
        pose(wg, F(t - 0.25), "guard"); pose(wg, F(t), "punch_R" if k % 2 == 0 else "punch_L"); pose(wg, F(t + 0.3), "guard")
    key(wg, F(22.05), base + V((0, 3.5, wg["base_z"])), (0, 0, math.radians(180))); key(wg, F(24.9), base + V((0, 3.5, wg["base_z"])))
    key(wg, F(25.0), base + V((0, 0, wg["base_z"])), (0, 0, math.radians(180)))
    pose(wg, F(25.0), "stand"); pose(wg, F(34), "stand")
    # shot 11: the mother walks in with the tea (29-31.5), he drinks at 32.5
    mm = war_mom
    key(mm, 1, base + V((0, 10, -60)), (0, 0, 0)); key(mm, F(28.9), base + V((0, 10, -60)), (0, 0, 0)); key(war_cup, 1, base + V((0.1, 10, -60))); key(war_cup, F(28.9), base + V((0.1, 10, -60)))
    key(mm, F(29), base + V((0, 10, mm["base_z"])), (0, 0, 0)); key(mm, F(31.5), base + V((0, 1.5, mm["base_z"])), (0, 0, 0))
    for k, t in enumerate([29 + i * 0.3 for i in range(9)]): pose(mm, F(t), "walk", phase=(k % 2) * 0.5)
    pose(mm, F(31.5), "wrist")
    key(war_cup, F(29), base + V((0.1, 10, 1.15)))
    key(war_cup, F(31.5), base + V((0.1, 1.4, 1.1))); key(war_cup, F(32.4), base + V((0.1, 1.4, 1.1))); key(war_cup, F(33.0), base + V((0.0, 0.25, 1.65)))
    pose(wg, F(32.0), "wrist"); pose(wg, F(33.0), "wrist"); pose(wg, F(33.6), "stand")
    # ---- gate (34-37): he walks out slowing and drops to a knee; the mother holds the cup
    gg = gate_g
    for k, t in enumerate([34 + i * 0.35 for i in range(7)]): pose(gg, F(t), "walk", phase=(k % 2) * 0.5)
    key(gg, F(34), O_GATE + V((0, -1.5, gg["base_z"]))); key(gg, F(36.2), O_GATE + V((0, 0.8, gg["base_z"])))
    pose(gg, F(36.4), "stand"); pose(gg, F(37.0), "kneel")
    key(gg, F(36.4), O_GATE + V((0, 0.9, gg["base_z"]))); key(gg, F(37.0), O_GATE + V((0, 1.0, gg["base_z"] - 0.55)))
    pose(gate_mom, F(34), "wrist")
    # ---- fantasy (43-): he wakes lying down, stands, the fireball (47-50), slips, punches (51-52.5)
    fg = fant_g
    key(fg, F(43), O_FANT + V((0, 0, 0.25)), (math.radians(-85), 0, math.radians(180)))
    key(fg, F(45.2), O_FANT + V((0, 0, 0.25)), (math.radians(-85), 0, math.radians(180))); key(fg, F(46.6), O_FANT + V((0, 0, fg["base_z"])), (0, 0, math.radians(180)))
    pose(fg, F(46.6), "stand"); pose(fg, F(47.0), "guard")
    key(fireball, 1, O_FANT + V((0, 9, -60))); key(fl_l, 1, O_FANT + V((0, 9, -60))); key(fireball, F(46.9), O_FANT + V((0, 9, -60))); key(fl_l, F(46.9), O_FANT + V((0, 9, -60)))
    key(fireball, F(47.0), O_FANT + V((0, 9, 1.5))); key(fireball, F(50.0), O_FANT + V((0.2, 1.3, 1.5))); key(fireball, F(50.2), O_FANT + V((0.2, -3, 1.5)))
    key(fl_l, F(47.0), O_FANT + V((0, 9, 1.5))); key(fl_l, F(50.0), O_FANT + V((0.2, 1.3, 1.5))); key(fl_l, F(50.2), O_FANT + V((0.2, -3, 1.5)))
    key(fg, F(49.6), O_FANT + V((0, 0, fg["base_z"]))); key(fg, F(50.1), O_FANT + V((-0.9, 0.2, fg["base_z"]))); key(fg, F(51.0), O_FANT + V((-0.9, 0.2, fg["base_z"])))
    key(fg, F(52.4), O_FANT + V((-0.4, 7.4, fg["base_z"])))
    pose(fg, F(50.1), "guard"); pose(fg, F(51.8), "guard"); pose(fg, F(52.4), "punch_R"); pose(fg, F(53.4), "guard")
    pose(mage, F(47.0), "wrist")
    key(mage, F(52.4), O_FANT + V((0, 9, mage["base_z"])), (0, 0, 0)); key(mage, F(53.4), O_FANT + V((0.5, 13, mage["base_z"])), (math.radians(-70), 0, 0))
    key(mage, F(54.4), O_FANT + V((0.5, 12.5, mage["base_z"])), (0, 0, 0)); key(mage, F(55.0), O_FANT + V((0.5, 12.5, mage["base_z"])), (0, 0, 0))
    # ---- flicker the fires
    for fl in fires:
        for t in range(F(11), F(34), 3):
            fl.data.energy = 3500 * RNG.uniform(0.7, 1.3); fl.data.keyframe_insert("energy", frame=t)
    # exposure flash on the big hits
    for ht in HITS_BIG:
        for fr_, v in ((F(ht) - 1, 0.3), (F(ht), 3.0), (F(ht) + 2, 0.3)):
            scn.view_settings.exposure = v; scn.view_settings.keyframe_insert("exposure", frame=fr_)
    for ob in (hall_mom, hall_kid, teen, war_g, war_mom, gate_g, gate_mom, fant_g, mage, d_kid, d_adult, d_human): hold(ob)

def crowd_action():
    c = CROWD; base = O_WAR
    # 20 already lie on the ground; 8 rush in shot 6; 72 in four groups of 18 for the count (shot 9)
    pre, wave1, groups = c[:20], c[20:28], [c[28 + 18 * i: 28 + 18 * (i + 1)] for i in range(4)]
    def lie(ob, pos, yaw=0.0): key(ob, 1, pos, (math.radians(-88), 0, yaw))
    for k, ob in enumerate(pre):
        p = ob.location.copy(); p.z = 0.18; lie(ob, p, RNG.uniform(0, 6.28))
    hit_t = (13.6, 14.2, 14.7, 15.2, 15.7, 16.0, 16.3, 16.5)
    for k, ob in enumerate(wave1):
        p0 = ob.location.copy(); t = hit_t[k]
        key(ob, 1, p0, (0, 0, math.pi)); key(ob, F(t - 1.1), p0, (0, 0, math.pi))
        key(ob, F(t - 0.1), base + V((RNG.uniform(-0.6, 0.6), 1.2, 0)), (0, 0, math.pi))
        key(ob, F(t), base + V((RNG.uniform(-0.6, 0.6), 1.3, 0)), (0, 0, math.pi))
        key(ob, F(t + 0.45), base + V((RNG.uniform(-2.5, 2.5), 4.5, 0.15)), (math.radians(-88), 0, RNG.uniform(-1, 1)))
    for gi, (t, grp) in enumerate(zip((22.4, 23.2, 24.0, 24.8), groups)):
        for k, ob in enumerate(grp):
            p0 = ob.location.copy(); ob.rotation_euler = (0, 0, math.pi)
            key(ob, 1, p0, (0, 0, math.pi)); key(ob, F(t - 0.9), p0, (0, 0, math.pi))
            tx = base + V((RNG.uniform(-1.2, 1.2) + (k - 9) * 0.25, 1.6 + RNG.uniform(0, 1.2), 0))
            key(ob, F(t - 0.05), tx, (0, 0, math.pi)); key(ob, F(t), tx, (0, 0, math.pi))
            key(ob, F(t + 0.5), base + V((RNG.uniform(-5, 5), 6 + RNG.uniform(0, 5), 0.15)), (math.radians(-88), 0, RNG.uniform(-1, 1)))
    # 25-29: everyone kneels in a ring
    for k, ob in enumerate(c):
        a = k / len(c) * math.tau; r = 3.5 + (k % 4) * 1.2
        p = base + V((r * math.cos(a), r * math.sin(a), 0)); yaw = math.atan2(-p.x + base.x, p.y - base.y) + math.pi
        key(ob, F(24.95), None, (math.radians(-88), 0, 0)); key(ob, F(25.0), p, (0, 0, yaw), (1, 1, 0.62))
        key(ob, F(34.0), p, (0, 0, yaw), (1, 1, 0.62))
    for ob in c: constant(ob)

# ------------------------------------------------------------------ camera
cam = None
def make_cam():
    global cam, cd
    cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05; cd.clip_end = 3000; cd.dof.use_dof = False
    cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam; cam.rotation_mode = "QUATERNION"
def lerp(a, b, u): return a + (b - a) * u
def vlerp(a, b, u): return V(a) + (V(b) - V(a)) * u
def ease(u): return u * u * (3 - 2 * u)
def pos_of(g, f_sec):
    return V(g.matrix_world.translation)

def shots():
    """Return fn(t) -> (loc, look, lens, roll_deg). Each shot is a list of cuts."""
    S = []
    def add(t0, t1, fn): S.append((t0, t1, fn))
    def lin(a, b, t0, t1, t):
        return vlerp(a, b, ease(min(1, max(0, (t - t0) / (t1 - t0)))))
    EYE = lambda O, ey, dist=0.55, lens=90: (O + V((0.03, -dist, ey)), O + V((0, 0, ey)), lens, 0)
    # 1 newborn (0-2.5): kid face close-up in the dark set
    add(0, 2.5, lambda t: (lin(HEADP['kid'] + V((0.02, -0.9, 0.0)), HEADP['kid'] + V((0.02, -0.38, 0.0)), 0, 2.5, t), HEADP['kid'] + V((0, 0, 0)), 85, 0))
    # 2 kid in the hall (2.5-5.5): low wide, then push on the kid
    add(2.5, 4.3, lambda t: (lin(O_HALL + V((0.8, -4, 0.7)), O_HALL + V((0.6, -1.6, 0.9)), 2.5, 4.3, t), O_HALL + V((0, 2.5, 1.3)), 28, 4))
    add(4.3, 5.5, lambda t: (O_HALL + V((0.3, -0.2, 1.05)), lin(O_HALL + V((0.9, 3.8, 1.2)), O_HALL + V((0.9, 3.8, 0.1)), 4.2, 4.6, t), 50, -8))
    # 3 teen (5.5-8): wide, close on shin at 7.0 then bat
    add(5.5, 6.5, lambda t: (lin(O_DOJO + V((-3, -3.5, 1.2)), O_DOJO + V((-2.4, -3.0, 1.2)), 5.5, 6.5, t), O_DOJO + V((0, 1, 1.0)), 32, 0))
    add(6.5, 7.2, lambda t: (O_DOJO + V((1.2, 0.2, 0.55)), O_DOJO + V((0, 1.5, 0.6)), 45, 18))
    add(7.2, 8.0, lambda t: (O_DOJO + V((-2.2, 3.0, 1.3)), O_DOJO + V((-0.6, 2.3, 0.4)), 40, -12))
    # 4 map (8-11): sweep over the banners
    add(8, 11, lambda t: (lin(O_MAP + V((-5, -2, 1.0)), O_MAP + V((5, -2, 1.4)), 8, 11, t), O_MAP + V((0, 2.5, 1.2)), 35, lerp(-6, 6, (t - 8) / 3)))
    # 5 war wide (11-13)
    add(11, 13, lambda t: (lin(O_WAR + V((-2.6, -3.5, 1.1)), O_WAR + V((-1.4, -2.6, 1.2)), 11, 13, t), O_WAR + V((0, 8, 1.5)), 30, 0))
    # 6 first wave (13-16): four setups cut every 0.4 s
    sets6 = [
        (lambda t: (O_WAR + V((0.9, -2.2, 0.55)), O_WAR + V((0, 3.5, 1.3)), 28, 0)),
        (lambda t: (O_WAR + V((-2.4, 0.6, 1.5)), O_WAR + V((0, 0.8, 1.3)), 55, -14)),
        (lambda t: (O_WAR + V((0.5, 3.2, 0.35)), O_WAR + V((0, 0, 1.3)), 35, 16)),
        (lambda t: (O_WAR + V((1.3, 0.1, 1.9)), O_WAR + V((0, 0.8, 1.4)), 70, 9)),
    ]
    for k in range(8): add(13 + k * 0.375, 13 + (k + 1) * 0.375, sets6[k % 4])
    # 7 Ultra Instinct eye close-up (16-19)
    add(16, 19, lambda t: (lin(HEADP['adult'] + V((0.03, -0.62, 0)), HEADP['adult'] + V((0.02, -0.4, 0)), 16, 19, t), HEADP['adult'], 95, 0))
    # 8 silhouette walk (19-22): low front, fire behind
    add(19, 22, lambda t: (O_WAR + V((0.2, 7.5, 0.7)), O_WAR + V((0, lerp(0, 3.5, (t - 19) / 3), 1.5)), lerp(32, 40, (t - 19) / 3), lerp(-5, 3, (t - 19) / 3)))
    # 9 the count (22-25): three setups alternate around each hit
    def s9(t):
        k = int((t - 22) / 0.4) % 3
        return [(O_WAR + V((0.7, 0.4, 1.35)), O_WAR + V((0, 3, 1.3)), 40, 10), (O_WAR + V((-1.6, 2.4, 0.5)), O_WAR + V((0, 0, 1.5)), 32, -16), (O_WAR + V((0.1, -1.5, 1.2)), O_WAR + V((0, 4, 1.3)), 24, 6)][k]
    add(22, 25, s9)
    # 10 Korea is one (25-29): wide orbit
    def s10(t):
        a = lerp(-0.7, 0.7, (t - 25) / 4)
        return (O_WAR + V((9 * math.sin(a), -9 * math.cos(a) + 0.5, 3.2)), O_WAR + V((0, 0, 1.2)), 28, lerp(-4, 4, (t - 25) / 4))
    add(25, 29, s10)
    # 11 mother (29-34)
    add(29, 31, lambda t: (O_WAR + V((3.6, lerp(8, 4, (t - 29) / 2), 1.3)), O_WAR + V((0, lerp(10, 2, (t - 29) / 2), 1.2)), 35, 0))
    add(31, 32.3, lambda t: (O_WAR + V((0.5, 0.15, 1.7)), O_WAR + V((0, 1.5, 1.6)), 70, 4))
    add(32.3, 33.3, lambda t: (O_WAR + V((0.35, 1.5, 1.75)), O_WAR + V((0, 0, 1.7)), 85, -4))
    add(33.3, 34, lambda t: (O_WAR + V((-0.4, 1.3, 1.55)), O_WAR + V((0, 1.5, 1.6)), 85, 6))
    # 12 poison at the gate (34-37)
    add(34, 36, lambda t: (lin(O_GATE + V((3.2, -4.5, 1.3)), O_GATE + V((2.4, -2.4, 1.3)), 34, 36, t), O_GATE + V((0, 0.5, 1.2)), 35, lerp(0, -8, (t - 34) / 2)))
    add(36, 37, lambda t: (lin(O_GATE + V((1.6, -0.6, 0.9)), O_GATE + V((1.0, 0.0, 0.8)), 36, 37, t), O_GATE + V((0, 1.0, 1.0)), 50, -14))
    # 13 last look (37-40): eye close-up in the dark set
    add(37, 40, lambda t: (lin(HEADP['adult'] + V((0.03, -0.7, 0)), HEADP['adult'] + V((0.03, -0.5, 0)), 37, 40, t), HEADP['adult'], 95, 0))
    # 14 reborn (40-43): human-eyed face
    add(40, 43, lambda t: (lin(HEADP['human'] + V((0.03, -0.7, 0)), HEADP['human'] + V((0.03, -0.5, 0)), 40, 43, t), HEADP['human'], 95, 0))
    # 15 new world (43-47): pull back from the face lying in the grass
    add(43, 47, lambda t: (lin(O_FANT + V((0.5, -1.6, 0.9)), O_FANT + V((2.5, -6.5, 2.2)), 43, 47, t), O_FANT + V((0, 1, 0.9)), lerp(60, 30, (t - 43) / 4), 0))
    # 16 fireball (47-51)
    add(47, 49, lambda t: (O_FANT + V((2.8, -2.0, 1.4)), O_FANT + V((0, 4, 1.4)), 35, -6))
    add(49, 49.9, lambda t: (O_FANT + V((-0.4, -0.3, 1.7)), O_FANT + V((0, 4, 1.5)), 80, 10))
    add(49.9, 51, lambda t: (O_FANT + V((-2.2, 1.0, 0.9)), O_FANT + V((-0.5, 1.0, 1.4)), 28, -14))
    # 17 counter (51-55)
    add(51, 52.0, lambda t: (O_FANT + V((-2.8, 3.4, 1.0)), O_FANT + V((-0.9, 3.6, 1.4)), 30, 12))
    add(52.0, 52.9, lambda t: (O_FANT + V((1.5, 6.2, 1.3)), O_FANT + V((-0.4, 7.2, 1.5)), 45, -16))
    add(52.9, 55, lambda t: (lin(O_FANT + V((0.5, 4.5, 1.0)), O_FANT + V((1.5, 6.0, 1.6)), 52.9, 55, t), O_FANT + V((0.5, 11, 1.2)), 28, 0))
    # 18 mage face (55-57)
    add(55, 57, lambda t: (lin(O_FANT + V((0.5, 7.0, 1.7)), O_FANT + V((0.5, 7.5, 1.7)), 55, 57, t), O_FANT + V((0.5, 13, 1.7)), 100, 0))
    # 19 title eyes (57-60)
    add(57, 60, lambda t: (lin(HEADP['adult'] + V((0.03, -0.8, 0)), HEADP['adult'] + V((0.03, -0.45, 0)), 57, 60, t), HEADP['adult'], 95, 0))
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
        q = fwd.to_track_quat("-Z", "Y"); q = q @ Quaternion((0, 0, 1), math.radians(roll))
        cam.location = loc; cam.rotation_quaternion = q; cd.lens = lens
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f); cd.keyframe_insert("lens", frame=f)
    scn.frame_start, scn.frame_end = 1, NF

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    wd = scn.world or bpy.data.worlds.new("w"); scn.world = wd; wd.use_nodes = True
    bg = wd.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.004, 0.004, 0.006, 1); bg.inputs[1].default_value = 1.0
    build_all()
    for k_, g_ in (('kid', d_kid), ('adult', d_adult), ('human', d_human)): HEADP[k_] = head_pos(g_)
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
