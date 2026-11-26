"""Kuro Oni ep 1, 30-SECOND prototype (approved voice script). Reuses the sets, rigs and helpers of film.py (v2).
    /root/.venvs/bpy/bin/python shorts/kuro_oni/film30.py [scale%] [first] [last] [step]
Renders PNGs to shorts/kuro_oni/frames30/ (existing frames skipped). env: SAMPLES (default 8), STILLS="t1,t2" seconds -> stills30/."""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import film as V2
from film import *          # sets, rigs, poses, helpers, scn, C, V, F, RAD ...
V2.NF = 900; V2.DUR = 30.0
NF = 900
FRAMES_DIR = os.path.join(HERE, "frames30")

BIG = [2.2, 6.2, 12.0, 19.0, 23.2]
SMALL = [18.3, 18.7, 19.5, 20.0, 14.6]
V2.HITS_BIG = BIG; V2.HITS_SMALL = SMALL; V2.HITS = sorted(BIG + SMALL)
O_HOUSE = V((800, 0, 0))

def build_house():
    global h_g, h_mom, katana
    ground(O_HOUSE, 40, (0.2, 0.14, 0.09)); box("hw", O_HOUSE + V((0, 4, 3)), (14, 0.3, 6), mat("hwl", (0.12, 0.09, 0.07)))
    box("moonwin", O_HOUSE + V((-3, 3.8, 3.2)), (1.8, 0.1, 2.0), mat("mw", (0.85, 0.9, 1.0), 5))
    light("hm", O_HOUSE + V((-3, 2.5, 3.2)), 900, (0.6, 0.7, 1.0), size=1.0); light("hl", O_HOUSE + V((2, -1, 2.5)), 350, (1, 0.7, 0.4))
    box("futon", O_HOUSE + V((0, 1.5, 0.08)), (1.6, 2.2, 0.16), mat("fu", (0.35, 0.3, 0.3)))
    h_g = rig(K.HERO_V1, O_HOUSE + V((0, 1.5, 0.16)), 180, adult=True, void=True)       # asleep, kneeling, slumped, back to the door
    h_mom = rig(MOM, O_HOUSE + V((0, -2.2, 0)), 0, adult=False)
    katana = box("katana", O_HOUSE + V((0, -2.2, -60)), (0.05, 1.0, 0.03), mat("kat", (0.8, 0.85, 0.95), 0.6))

def town_extra():
    """The unknown town: fire magic everywhere (first-person ending)."""
    global tfire, tlamp
    box("tground", O_FANT + V((0, 16, -0.04)), (40, 20, 0.1), mat("tg", (0.35, 0.3, 0.25)))
    for k in range(6): box(f"tb{k}", O_FANT + V((-9 + k * 3.4, 22, 2.5)), (2.6, 2.6, 5 + (k % 3)), mat("tbl", (0.55, 0.4, 0.3)))
    for k in range(5): dummy(f"tp{k}", O_FANT + V((-4 + k * 2.2, 13 + (k % 2) * 2, 0)), (0.5, 0.3, 0.3), 0.75 + 0.1 * k)
    tlamp = ball("lamp", O_FANT + V((4.5, 14, 2.6)), 0.25, mat("lp", (1, 0.7, 0.3), 12)); tlamp.scale = (0.01, 0.01, 0.01)
    tfire = [ball(f"tf{k}", O_FANT + V((-3 + k * 2, 12.5, 1.4)), 0.5, mat("tfm", (1, 0.5, 0.1), 12)) for k in range(4)]
    straw = dummy("straw", O_FANT + V((-1, 19, 0)), (0.7, 0.6, 0.2), 0.9)
    for k in range(4): light(f"tfl{k}", O_FANT + V((-3 + k * 2, 14, 2.5)), 900, (1, 0.5, 0.15), size=0.5)

def head_at(g, t):
    scn.frame_set(F(t)); bpy.context.view_layer.update(); return V(g.matrix_world @ g.pose.bones["head"].head)

def animate30():
    base = O_WAR; wg = war_g; bz = wg["base_z"]
    ALL = [hall_kid, hall_mom, court_kid, court_mom, teen, master, d_mom, ban_g, war_g, war_mom, gate_g, gate_mom, fant_g, knight, d_kid, d_adult, d_human, h_g, h_mom] + FIGHTERS
    for g in ALL: pose(g, 1, "stand")
    # ---- 0-3 HOOK: a hundred men ring him; one straight punch at 2.2 blasts them out
    c = CROWD
    for k, ob in enumerate(c):
        a = k / len(c) * math.tau; r = 3.2 + (k % 5) * 0.9
        p = base + V((r * math.cos(a), r * math.sin(a), 0)); yaw = math.atan2(-(p.x - base.x), p.y - base.y) + math.pi
        out = base + V(((r + 6 + (k % 4)) * math.cos(a), (r + 6 + (k % 4)) * math.sin(a), 0.2))
        key(ob, 1, p, (0, 0, yaw)); key(ob, F(2.15), p, (0, 0, yaw)); key(ob, F(2.8), out, (RAD(-85), 0, yaw + 0.5)); key(ob, F(30), out, (RAD(-85), 0, yaw + 0.5))
    for ob in c: constant(ob) if False else None
    key(wg, 1, base + V((0, 0, bz)), (0, 0, math.pi)); pose(wg, 1, "guard"); pose(wg, F(1.9), "guard"); pose(wg, F(2.2), "punch_R"); pose(wg, F(3.0), "stand")
    # ---- 3-5 hall (the boy, the clan of 30), 5-8 the black bone, 8-11 the slumped father
    key(father, F(0), O_HALL + V((3.2, 0.2, 0)), (0, 0, math.pi)); key(father, F(8), O_HALL + V((3.2, 0.2, 0)), (0, 0, math.pi))
    key(father, F(8.1), O_HALL + V((3.2, 0.2, -0.25)), (RAD(18), 0, math.pi)); key(father, F(11), O_HALL + V((3.2, 0.2, -0.25)), (RAD(18), 0, math.pi))
    key(hall_boy, F(0), O_HALL + V((0.2, 1.7, -60)), (0, 0, 0)); key(hall_boy, F(30), O_HALL + V((0.2, 1.7, -60)), (0, 0, 0))
    pose(teen, F(5.0), "guard"); pose(teen, F(5.8), "guard"); pose(teen, F(6.2), "kick_R"); pose(teen, F(6.9), "guard"); pose(teen, F(8), "stand")
    key(bat1, F(5.0), O_DOJO + V((0.35, 0.8, 0.45)), (0, 0, 0)); key(bat1, F(6.15), O_DOJO + V((0.35, 0.8, 0.45)), (0, 0, 0)); key(bat1, F(6.7), O_DOJO + V((-0.8, 1.6, 0.2)), (0.3, 0, 1.1))
    key(bat2, F(5.0), O_DOJO + V((0.35, 0.8, -60)))
    # ---- 11-13 the slap at 12.0 (courtyard)
    walk(court_kid, 10.6, 11.9, (0, -1.0, 0), (0, 3.2, 0), 2.2)
    key(court_kid, F(12.0), O_COURT + V((0, 3.2, court_kid["base_z"])), (0, 0, math.pi)); key(court_kid, F(12.12), O_COURT + V((-0.25, 3.15, court_kid["base_z"])), (0, 0, math.pi + RAD(38)))
    key(court_kid, F(13.0), O_COURT + V((-0.25, 3.15, court_kid["base_z"])), (0, 0, math.pi + RAD(38)))
    key(court_mom, F(10.6), O_COURT + V((-4.0, 4.2, court_mom["base_z"])), (0, 0, RAD(-90))); key(court_mom, F(11.7), O_COURT + V((-0.1, 4.25, court_mom["base_z"])), (0, 0, RAD(-90)))
    key(court_mom, F(11.8), O_COURT + V((-0.1, 4.25, court_mom["base_z"])), (0, 0, 0)); key(court_mom, F(13), O_COURT + V((-0.1, 4.25, court_mom["base_z"])), (0, 0, 0))
    for k, t in enumerate([10.6 + i * 0.25 for i in range(5)]): pose(court_mom, F(t), "walk", phase=(k % 2) * 0.5)
    pose(court_mom, F(11.8), "wrist"); pose(court_mom, F(11.95), "slap"); pose(court_mom, F(12.1), "slap"); pose(court_mom, F(12.6), "stand")
    for k, d in enumerate(play):
        for i in range(10): a = i * 0.7 + k; key(d, F(10.6 + i * 0.25), O_COURT + V((-2 + k * 1.3 + math.sin(a) * 0.8, 10.5 + math.cos(a) * 0.8, 0)))
    # ---- 13-15 dojo: the master is thrown, the teen's kata, mother smiles at 14.6
    pose(teen, F(13.0), "guard"); pose(teen, F(13.35), "wrist"); pose(teen, F(13.7), "wrist"); pose(teen, F(14.1), "guard"); pose(teen, F(14.4), "punch_R"); pose(teen, F(14.9), "stand")
    key(teen, F(13.0), O_DOJO + V((0, 0, teen["base_z"])), (0, 0, math.pi)); key(teen, F(13.35), O_DOJO + V((0.6, 0, teen["base_z"])), (0, 0, math.pi + RAD(-35))); key(teen, F(14.1), O_DOJO + V((0.4, 0, teen["base_z"])), (0, 0, math.pi))
    pose(master, F(13.0), "guard"); pose(master, F(13.25), "punch_R"); pose(master, F(13.6), "stand")
    key(master, F(5.0), O_DOJO + V((0, 2.4, master["base_z"])), (0, 0, 0)); key(master, F(13.0), O_DOJO + V((0, 2.4, master["base_z"])), (0, 0, 0)); key(master, F(13.3), O_DOJO + V((0.2, 1.1, master["base_z"])), (0, 0, 0))
    key(master, F(13.65), O_DOJO + V((0.9, 0.3, 1.4)), (RAD(-100), 0, 0)); key(master, F(14.0), O_DOJO + V((1.2, -0.6, 0.25)), (RAD(-88), 0, 0)); key(master, F(15), O_DOJO + V((1.2, -0.6, 0.25)), (RAD(-88), 0, 0))
    # ---- 15-18 the father's cloak (mud): lifted at 16.4
    key(cloak, F(15), O_BAN + V((0, 1.5, 0.03)), (0, 0, 0)); key(cloak, F(16.2), O_BAN + V((0, 1.5, 0.03)), (0, 0, 0)); key(cloak, F(16.8), O_BAN + V((0.0, 0.5, 1.45)), (RAD(-80), 0, 0), (1.3, 1.9, 0.05))
    pose(ban_g, F(15), "stand"); pose(ban_g, F(16.2), "wrist"); pose(ban_g, F(16.9), "stand")
    for k, b in enumerate(banners): key(b, F(15), O_BAN + V((-4.2 + k * 1.2, 5.5, -60)))
    # ---- 18-21 the war: six rush, are flung; eyes full white; they crawl back (20.0)
    for i, f_ in enumerate(FIGHTERS[:6]):
        t0 = 18.0 + i * 0.28; x = (-0.4, 0.5, -0.3, 0.4, -0.5, 0.3)[i]
        key(f_, 1, base + V((x * 3, 9 + i, f_["base_z"])), (0, 0, 0)); key(f_, F(t0 - 0.7), base + V((x * 3, 9 + i, f_["base_z"])), (0, 0, 0))
        key(f_, F(t0), base + V((x, 1.5, f_["base_z"])), (0, 0, 0)); key(f_, F(t0 + 0.3), base + V((x, 1.4, f_["base_z"])), (0, 0, 0))
        pose(f_, F(t0 - 0.7), "walk", phase=0.0); pose(f_, F(t0 - 0.35), "walk", phase=0.5); pose(f_, F(t0 - 0.05), "guard"); pose(f_, F(t0), "punch_R" if i % 2 == 0 else "punch_L"); pose(f_, F(t0 + 0.3), "stand")
        key(f_, F(t0 + 0.7), base + V((x * 2.5, 4.2 + i * 0.4, 0.2 + f_["base_z"])), (RAD(-85), 0, 0.6 * (-1) ** i)); key(f_, F(30), base + V((x * 2.5, 4.2 + i * 0.4, 0.2 + f_["base_z"])), (RAD(-85), 0, 0.6 * (-1) ** i))
    for t, p in ((18.2, "punch_R"), (18.5, "punch_L"), (18.8, "kick_R"), (19.0, "punch_R"), (19.4, "punch_L"), (19.7, "punch_R")):
        pose(wg, F(t - 0.15), "guard"); pose(wg, F(t), p); pose(wg, F(t + 0.15), "guard")
    pose(wg, F(20.3), "stand"); key(wg, F(3.0), base + V((0, 0, bz)), (0, 0, math.pi)); key(wg, F(30), base + V((0, 0, bz)), (0, 0, math.pi))
    # ---- 21-26 the house at night: he sleeps kneeling; the mother with the katana; the stab at 23.2
    pose(h_g, F(21.0), "kneel"); pose(h_g, F(24.4), "kneel"); pose(h_g, F(24.9), "kneel")
    hb = h_g["base_z"]
    key(h_g, F(21.0), O_HOUSE + V((0, 1.5, hb - 0.55)), (RAD(22), 0, math.pi)); key(h_g, F(23.3), O_HOUSE + V((0, 1.5, hb - 0.55)), (RAD(22), 0, math.pi))
    key(h_g, F(23.6), O_HOUSE + V((0, 1.5, hb - 0.55)), (RAD(5), 0, math.pi)); key(h_g, F(24.9), O_HOUSE + V((0, 1.5, hb - 0.55)), (RAD(5), 0, math.pi)); key(h_g, F(25.6), O_HOUSE + V((0, 1.5, hb - 0.7)), (RAD(40), 0, math.pi))
    mb = h_mom["base_z"]
    key(h_mom, 1, O_HOUSE + V((0, -2.2, -60)), (0, 0, 0)); key(h_mom, F(20.9), O_HOUSE + V((0, -2.2, -60)), (0, 0, 0))
    key(h_mom, F(21.0), O_HOUSE + V((0, -2.2, mb)), (0, 0, 0)); key(h_mom, F(22.8), O_HOUSE + V((0, 0.0, mb)), (0, 0, 0)); key(h_mom, F(26), O_HOUSE + V((0, 0.0, mb)), (0, 0, 0))
    for k, t in enumerate([21.0 + i * 0.3 for i in range(7)]): pose(h_mom, F(t), "walk", phase=(k % 2) * 0.5)
    pose(h_mom, F(22.8), "punch_R"); pose(h_mom, F(23.2), "punch_R"); pose(h_mom, F(23.6), "stand")
    key(katana, 1, O_HOUSE + V((0, 0, -60))); key(katana, F(21.0), O_HOUSE + V((0, 0, -60)))
    key(katana, F(21.1), O_HOUSE + V((0.35, -1.8, 1.45)), (RAD(-80), 0, 0)); key(katana, F(22.8), O_HOUSE + V((0.35, 0.2, 1.7)), (RAD(-20), 0, 0))
    key(katana, F(23.2), O_HOUSE + V((0.05, 1.0, 1.25)), (RAD(-86), 0, 0)); key(katana, F(26), O_HOUSE + V((0.05, 1.0, 1.25)), (RAD(-86), 0, 0))
    # ---- 26-30 first person: lying, sitting up, the town, the hands
    fg = fant_g
    key(fg, 1, O_FANT + V((0, 0, -60)), (0, 0, math.pi)); key(fg, F(28.1), O_FANT + V((0, 0, -60)), (0, 0, math.pi))
    key(fg, F(28.2), O_FANT + V((0, 0, fg["base_z"])), (0, 0, math.pi)); key(fg, F(30), O_FANT + V((0, 0, fg["base_z"])), (0, 0, math.pi))
    pose(fg, F(26), "stand"); pose(fg, F(28.6), "stand"); pose(fg, F(29.1), "wrist")
    key(fireball, 1, O_FANT + V((0, 9, -60)))
    skin = mat('skin', (0.85, 0.62, 0.48))
    for sx in (-1, 1):
        hnd = box('hand', (sx * 0.15, -0.12, -0.5), (0.09, 0.07, 0.22), skin); hnd.parent = V2.cam
        hnd.scale = (0.001, 0.001, 0.001); hnd.keyframe_insert('scale', frame=1); hnd.keyframe_insert('scale', frame=F(28.85))
        hnd.scale = (0.09, 0.07, 0.22); hnd.keyframe_insert('scale', frame=F(28.95)); hnd.keyframe_insert('scale', frame=F(30))
    key(knight, 1, O_FANT + V((0, 9, -60)), (0, 0, 0)); key(knight, F(30), O_FANT + V((0, 9, -60)), (0, 0, 0))
    # fire magic: balls fly between the people and the straw dummy
    seq = [(27.9, -3, 10.5, -1, 18.6), (28.2, -1, 10.5, -1, 18.8), (28.5, 1, 10.5, -1, 18.7), (28.8, 3, 10.5, -1, 18.9)]
    for k, (t, x0, y0, tx, ty) in enumerate(seq):
        b = tfire[k]
        key(b, 1, O_FANT + V((x0, y0, -60))); key(b, F(t - 0.01), O_FANT + V((x0, y0, -60))); key(b, F(t), O_FANT + V((x0, y0, 1.6)))
        key(b, F(t + 0.9), O_FANT + V((tx, ty, 1.3))); key(b, F(t + 0.91), O_FANT + V((tx, ty, -60)))
    key(tlamp, F(26), None, None, (0.01, 0.01, 0.01)); key(tlamp, F(27.0), None, None, (1, 1, 1))
    for fl in fires:
        for t in range(F(0), F(23), 3):
            fl.data.energy = 3500 * RNG.uniform(0.7, 1.3); fl.data.keyframe_insert("energy", frame=t)
    for ht in BIG:
        for fr_, v in ((F(ht) - 1, 0.3), (F(ht), 3.0), (F(ht) + 2, 0.3)):
            scn.view_settings.exposure = v; scn.view_settings.keyframe_insert("exposure", frame=fr_)
    # fade to black at 25.4-26.2 and from black at 26.2
    for fr_, v in ((F(25.3), 0.3), (F(25.6), -9.0), (F(26.15), -9.0), (F(26.3), 0.3)):
        scn.view_settings.exposure = v; scn.view_settings.keyframe_insert("exposure", frame=fr_)
    for g in ALL: linear_bones(g)

def shots30(HEADP2):
    S = []
    def add(t0, t1, fn): S.append((t0, t1, fn))
    def lin(a, b, t0, t1, t): return vlerp(a, b, ease(min(1, max(0, (t - t0) / (t1 - t0)))))
    H, Co, D, W_, G, Fa, B, Ho = O_HALL, O_COURT, O_DOJO, O_WAR, O_GATE, O_FANT, O_BAN, O_HOUSE
    def setup(name):
        g = W_
        return {"side": (g + V((-3.2, 0.6, 1.4)), g + V((0, 0.5, 1.3)), 45, 0), "side_low": (g + V((3.0, 0.4, 0.5)), g + V((0, 0.7, 1.2)), 35, -14),
                "over_enemy": (g + V((0.55, 2.4, 1.7)), g + V((0, 0, 1.5)), 50, 8), "over_gojo": (g + V((-0.45, -1.3, 1.75)), g + V((0, 3, 1.3)), 50, -6),
                "fist": (g + V((-1.0, 0.2, 1.35)), g + V((0.1, 1.0, 1.4)), 85, 12), "face": (g + V((0.9, 1.4, 1.75)), g + V((0, 0, 1.75)), 90, -10),
                "fear": (g + V((0.2, 1.8, 0.25)), g + V((0, 0, 1.8)), 28, 0), "wide": (g + V((-2.6, -3.0, 1.2)), g + V((0, 6, 1.4)), 30, 0)}[name]
    # hook 0-3
    add(0, 1.0, lambda t: (lin(W_ + V((-4.2, -6.0, 2.2)), W_ + V((-3.2, -4.8, 1.8)), 0, 1.0, t), W_ + V((0, 1, 1.3)), 24, -5))
    add(1.0, 1.7, lambda t: setup("fear")); add(1.7, 2.2, lambda t: setup("face")); add(2.2, 2.55, lambda t: setup("side_low")); add(2.55, 3.0, lambda t: (W_ + V((0.3, -7.5, 3.0)), W_ + V((0, 2, 1.0)), 24, 4))
    # 3-5 the boy before the clan, the Demonic Eye; 5-8 black bone; 8-11 the slumped father
    add(3.0, 4.1, lambda t: (lin(H + V((-3.5, -4.5, 0.6)), H + V((-2.5, -3.5, 0.8)), 3.0, 4.1, t), H + V((0, 3, 1.1)), 26, -3))
    add(4.1, 5.0, lambda t: (lin(HEADP2["kid"] + V((0.02, -0.9, 0)), HEADP2["kid"] + V((0.02, -0.38, 0)), 4.1, 5.0, t), HEADP2["kid"], 85, 0))
    add(5.0, 6.15, lambda t: (D + V((1.3, 0.3, 0.25)), D + V((0.2, 0.8, 0.35)), 50, 10))
    add(6.15, 6.6, lambda t: (D + V((1.0, 0.2, 0.5)), D + V((0, 0.9, 0.5)), 85, -14)); add(6.6, 8.0, lambda t: (D + V((-3.6, 0.4, 1.1)), D + V((0, 0.5, 0.9)), 38, -4))
    add(8.0, 9.4, lambda t: (H + V((0.6, -1.6, 0.7)), H + V((3.2, 0.2, 0.55)), 38, 6)); add(9.4, 11.0, lambda t: (lin(H + V((-2.6, -2.5, 1.0)), H + V((-1.8, -1.8, 1.0)), 9.4, 11.0, t), H + V((0, 3, 1.2)), 30, -4))
    # 11-13 the slap
    add(11.0, 11.8, lambda t: (Co + V((4.2, lerp(-1, 2.8, (t - 11.0) / 0.8), 1.2)), Co + V((0, lerp(0, 3.2, (t - 11.0) / 0.8), 1.0)), 32, 0))
    add(11.8, 12.2, lambda t: (Co + V((0.2, 2.2, 1.0)), Co + V((0, 4.25, 1.0)), 28, -9)); add(12.2, 12.7, lambda t: (Co + V((2.2, 3.7, 1.0)), Co + V((-0.1, 3.7, 1.0)), 85, 12))
    add(12.7, 13.0, lambda t: (Co + V((-2.0, 0.2, 0.4)), Co + V((0, 3.0, 0.9)), 30, -7))
    # 13-15 dojo (the master thrown, then the kata; mother on the veranda smiles at 14.6)
    add(13.0, 13.9, lambda t: (D + V((-4.2, 1.4, 1.2)), D + V((0.4, 1.0, 1.0)), 32, 0)); add(13.9, 14.4, lambda t: (D + V((1.6, -2.0, 0.4)), D + V((1.0, -0.6, 0.4)), 30, 14))
    add(14.4, 15.0, lambda t: (D + V((3.0, 2.8, 1.5)), D + V((4.5, 5.2, 1.5)), 70, -6))
    # 15-18 cloak
    add(15.0, 16.0, lambda t: (B + V((0.8, 0.4, 0.5)), B + V((0, 1.5, 0.05)), 45, -12)); add(16.0, 16.9, lambda t: (B + V((-1.6, 0.8, 1.2)), B + V((0, 0.4, 1.3)), 45, 8))
    add(16.9, 18.0, lambda t: setup("wide"))
    # 18-21 the war
    def cuts(t0, t1, names, dts):
        t = t0; k = 0
        while t < t1:
            dt = dts[k % len(dts)]; nm = names[k % len(names)]; add(t, min(t1, t + dt), (lambda n: (lambda tt: setup(n)))(nm)); t += dt; k += 1
    add(18.0, 18.3, lambda t: setup("fear")); cuts(18.3, 19.6, ["side", "over_enemy", "fist", "side_low", "over_gojo", "face"], [0.2, 0.22])
    add(19.6, 20.0, lambda t: (lin(HEADP2["adult"] + V((0.03, -0.62, 0)), HEADP2["adult"] + V((0.02, -0.4, 0)), 19.6, 20.0, t), HEADP2["adult"], 95, 0))
    add(20.0, 21.0, lambda t: (W_ + V((1.6, 4.6, 0.5)), W_ + V((0, 4.4, 0.25)), 38, -8))
    # 21-26 the house
    add(21.0, 22.2, lambda t: (Ho + V((3.4, -0.5, 1.4)), Ho + V((0, 0.8, 1.0)), 32, -6)); add(22.2, 22.9, lambda t: (Ho + V((-0.5, -1.2, 1.9)), Ho + V((0, 1.6, 1.3)), 50, 8))
    add(22.9, 23.15, lambda t: (Ho + V((-2.4, 1.0, 1.3)), Ho + V((0, 1.4, 1.2)), 45, -12)); add(23.15, 23.5, lambda t: (Ho + V((0.9, 2.4, 1.5)), Ho + V((0.05, 1.4, 1.3)), 70, 10))
    add(23.5, 24.4, lambda t: (HEADP2["adult"] * 0 + Ho + V((1.5, 0.9, 1.25)), Ho + V((0, 1.5, 1.25)), 85, -6)); add(24.4, 25.0, lambda t: (Ho + V((2.4, -0.2, 0.7)), Ho + V((0, 1.5, 0.6)), 32, 8))
    add(25.0, 25.7, lambda t: (Ho + V((0.4, 0.4, 1.0)), Ho + V((0, 1.5, 0.7)), 60, 0)); add(25.7, 26.0, lambda t: (Ho + V((0.4, 0.4, 1.0)), Ho + V((0, 1.5, 0.7)), 60, 0))
    # 26-30 first person (our own eyes): lying, sitting up, the town, the hands
    HF = HEADP2["fant"]
    add(26.0, 27.0, lambda t: (Fa + V((0, -0.2, 0.35)), Fa + V((lerp(-3, 2, (t - 26) / 1.0), 6, 7.5)), 26, lerp(-4, 3, (t - 26) / 1.0)))
    add(27.0, 28.2, lambda t: (lin(Fa + V((0, -0.2, 0.35)), V(HF) + V((0, 0.12, 0.03)), 27.0, 28.2, t), lin(Fa + V((0, 8, 6)), Fa + V((-1, 14, 1.8)), 27.0, 28.2, t), 24, 0))
    add(28.2, 29.0, lambda t: (V(HF) + V((0, 0.12, 0.03)), lin(Fa + V((-1, 14, 1.8)), Fa + V((3, 14, 1.8)), 28.2, 29.0, t), 24, 0))
    add(29.0, 30.0, lambda t: (V(HF) + V((0, 0.16, 0.06)), V(HF) + V((0.05, 1.3, -0.45)), 30, 0))
    return S

if __name__ == "__main__":
    wd = scn.world or bpy.data.worlds.new("w"); scn.world = wd; wd.use_nodes = True
    bg = wd.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.004, 0.004, 0.006, 1); bg.inputs[1].default_value = 1.0
    build_all(); globals().update({k: v for k, v in vars(V2).items() if not k.startswith('__')}); build_house(); town_extra()
    HEADP2 = {}
    for k_, g_ in (("kid", d_kid), ("adult", d_adult), ("human", d_human), ("fant", fant_g)): HEADP2[k_] = head_pos(g_)
    make_cam(); animate30(); key_camera(shots30(HEADP2))
    scn.frame_start, scn.frame_end = 1, NF
    C.render_settings(SCALE, SAMPLES); scn.view_settings.exposure = 0.3
    scn.render.fps = FPS
    os.makedirs(FRAMES_DIR, exist_ok=True)
    stills = os.environ.get("STILLS")
    if stills:
        sd = os.path.join(HERE, "stills30"); os.makedirs(sd, exist_ok=True)
        for s in stills.split(","):
            f = F(float(s)); scn.frame_set(f); scn.render.filepath = os.path.join(sd, f"t{float(s):05.2f}.png"); bpy.ops.render.render(write_still=True)
        sys.exit(0)
    for f in range(FIRST, min(LAST, NF) + 1, STEP):
        p = os.path.join(FRAMES_DIR, f"f{f:04d}.png")
        if os.path.exists(p): continue
        scn.frame_set(f); scn.render.filepath = p; bpy.ops.render.render(write_still=True)
