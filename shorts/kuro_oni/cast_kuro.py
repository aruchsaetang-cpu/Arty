"""Kuro Oni cast: style dicts, build_cast(), make_silhouette_crowd().
    import cast_kuro as CK; arms = CK.build_cast(P, ["MOTHER", "FATHER", "FIGHTERS"], locs={"MOTHER": (0, 0, 0)})
Names: BOY TEEN HERO HERO_HUMAN MOTHER FATHER MASTER VASSAL, groups CLAN_MEN (CLAN_MEN_0..4), CLAN_WOMEN (CLAN_WOMEN_0..1),
FIGHTERS (FIGHTER_0..11), KIDS (KID_0..3), TOWNSFOLK (TOWN_0..5). which=None builds everything (heavy: build only what a shot needs).
TEEN is built at scale 1.0; the caller applies 0.88 to the returned armature (loc z uses ground_rest, so pass scale= via the scales dict)."""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.setdefault("FRAMES", "1800"); os.environ.setdefault("PEOPLE", "0"); os.environ.setdefault("SEED", "7")
sys.path.insert(0, os.path.join(ROOT, "lookdev")); sys.path.insert(0, os.path.join(ROOT, "shorts", "aura"))
import bpy, bmesh
from mathutils import Vector as V, Matrix
import city as C
import character_mh as ch
import cast as K
import kimono as KM

# ------------------------------------------------------------------ style dicts
_BLACK = ("#1b1b22", "#0a0a10")
BOY = dict(K.KID2, body="kid_lean", height=1.3, tie=None, backpack=None, legs="trousers", leg_col=("#1c1a20", "#0c0b10"), coat=None,
           top=("#d8d4cc", "#8a867e"), turtleneck=False, hair="bangs", face="lean_boy", void_eyes=True)
TEEN = dict(K.HERO_V1, height=1.86, void_eyes=True)          # the hero style; caller scales it by 0.88
HERO = dict(K.HERO_V1, void_eyes=True)
HERO_HUMAN = dict(K.HERO_V1, void_eyes=False)
MOTHER = dict(K.W1, vary=300, skin=("#f4e4d8", "#c8a698"), coat=("#4a4256", "#221e2a"), hem=1.0, open_skirt=False, open_coat=False, lapels=True,
              coat_flare=(0.02, 0.05), top=("#3a3446", "#1a1620"), turtleneck=False, legs="skirt", leg_col=("#3a3446", "#1a1620"),
              skirt_hem=1.0, bag=None, hair="long", hair_len=0.12, hair_col="#0c0a0a", lips="#8a4a52")
FATHER = dict(K.MAN_LONG, vary=301, body="m_lean", height=1.88, face="long", hair="long", hair_len=0.3, hair_col="#0a0a0e",
              coat=_BLACK, hem=1.0, open_skirt=False, top=("#202028", "#0c0c12"), legs="trousers", leg_col=("#16161c", "#08080c"),
              clear_face=False)
MASTER = dict(K.MAN_LONG, vary=302, body="m_slim", height=1.62, face="square", skin=("#e6cdb8", "#a58570"), hair="buzz", hair_col="#e4e2e8",
              coat=("#1c1c22", "#08080c"), hem=1.0, open_skirt=False, top=("#26262e", "#0e0e14"), legs="trousers",
              leg_col=("#1a1a20", "#08080c"), brows="#cfcfd6", clear_face=False)
VASSAL = dict(K.MAN_DIAMOND, vary=303, body="m", height=1.74, face="diamond", skin=("#d6ad8a", "#98694b"), hair="slick", hair_col="#15151a",
              coat=None, top=("#d8d2c6", "#8a8478"), turtleneck=False, legs="trousers", leg_col=("#1e1e24", "#0a0a0e"),
              glasses="#1b2a3a", clear_face=False)

def _man(v, face, body, h, hair, hcol, skin, coat=_BLACK, top=("#202028", "#0c0c12"), leg=("#16161c", "#08080c")):
    return dict(K.MAN_LONG, vary=v, body=body, height=h, face=face, hair=hair, hair_col=hcol, skin=skin, coat=coat, hem=1.0,
                open_skirt=False, top=top, legs="trousers", leg_col=leg, clear_face=False)
CLAN_MEN = [
    _man(310, "long", "m", 1.78, "short", "#0c0c10", ("#e6c5a8", "#a8795d"), coat=("#2e2a3c", "#14111e")),
    _man(311, "square", "m_heavy", 1.74, "buzz", "#161618", ("#d9a982", "#9a6a4a"), coat=("#232329", "#0c0c10")),
    _man(312, "diamond", "m_lean", 1.84, "slick", "#0e0e12", ("#efd2b8", "#b0806a"), coat=("#1a2230", "#0a0e16")),
    _man(313, "round", "m", 1.70, "bangs", "#1a1410", ("#dcb08a", "#9a6c4c"), coat=("#3a2c34", "#1a1218")),
    _man(314, "boy", "m_fit", 1.80, "crop", "#0c0c10", ("#e9c4a6", "#a8795d"), coat=("#28282e", "#0e0e12")),
]
def _wom(v, col, hair, hl, hcol, face="kstar_f"):
    return dict(K.W1, vary=v, face=face, skin=("#f4e0d0", "#c4a090"), coat=col, hem=1.0, open_skirt=False, open_coat=False, lapels=True,
                coat_flare=(0.02, 0.05), top=col, turtleneck=False, legs="skirt", leg_col=col, skirt_hem=1.0, bag=None,
                hair=hair, hair_len=hl, hair_col=hcol, lips="#8a4a52")
CLAN_WOMEN = [_wom(320, ("#3a3446", "#1a1620"), "long", 0.35, "#0c0a0a"), _wom(321, ("#2e3440", "#12161e"), "bob", 0.2, "#16100e", "soft_f")]
_FH = ["short", "buzz", "bangs", "slick", "crop", "quiff"]
_FF = ["long", "square", "diamond", "round", "boy", "long"]
_FB = ["m", "m_heavy", "m_lean", "m_fit", "m_slim", "m_muscle"]
_FS = [("#e6c5a8", "#a8795d"), ("#d9a982", "#9a6a4a"), ("#efd2b8", "#b0806a"), ("#c58f6a", "#86583d")]
# street gang fighters: each man his own jacket / shirt / hair colour (v1 was all black suits and read as blobs)
_FO = [  # (coat or None, top, trousers, hair colour)
    (("#7a2230", "#3a0e16"), ("#1c1c22", "#0a0a0e"), ("#2a3550", "#121828"), "#0e0e12"),     # burgundy leather, jeans
    (("#5a6234", "#2a2e16"), ("#dcd6c8", "#8a8478"), ("#3a3428", "#181510"), "#3a2616"),     # olive bomber
    (("#22325a", "#0e1630"), ("#e4e0d8", "#908c84"), ("#22325a", "#0e1630"), "#0e0e12"),     # navy suit, white shirt
    (None, ("#8a8a92", "#3e3e46"), ("#1c1c22", "#0a0a0e"), "#d8bc6a"),                       # grey hoodie, bleached hair
    (("#6a4026", "#30180c"), ("#c8962a", "#7a5410"), ("#24242a", "#0e0e12"), "#1a1410"),     # brown leather, mustard tee
    (None, ("#e0dcd2", "#8e8a80"), ("#18181e", "#08080c"), "#0e0e12"),                       # white shirt
    (("#1f6a6a", "#0c2e2e"), ("#18181e", "#08080c"), ("#18181e", "#08080c"), "#8a2a1a"),     # teal track jacket, red hair
    (("#a02a24", "#4a100e"), ("#1c1c22", "#0a0a0e"), ("#2a2c34", "#101216"), "#0e0e12"),     # red jacket
    (("#3a3a44", "#16161c"), ("#6a3a8a", "#2e1640"), ("#2a2a30", "#0e0e12"), "#2a1a10"),     # charcoal, purple shirt
    (("#a8834e", "#5a4024"), ("#2a2a30", "#0e0e12"), ("#3a3226", "#181410"), "#0e0e12"),     # camel coat
    (("#1c1c22", "#0a0a0e"), ("#9a1e1e", "#480a0a"), ("#1c1c22", "#0a0a0e"), "#c0c0c8"),     # black jacket, red shirt, grey hair
    (("#3a5a86", "#1a2a44"), ("#d8d2c4", "#8a8478"), ("#24242a", "#0e0e12"), "#1a1410"),     # denim jacket
]
FIGHTERS = [dict(K.MAN_LONG, vary=200 + i * 7, body=_FB[i % 6], height=1.70 + 0.02 * (i % 6), face=_FF[(i + i // 6) % 6], skin=_FS[i % 4],
                 hair=_FH[(i * 5) % 6], hair_col=_FO[i][3], coat=_FO[i][0], hem=(0.6 if i in (2, 9) else 0.3),
                 top=_FO[i][1], turtleneck=False, legs="trousers", leg_col=_FO[i][2], clear_face=False) for i in range(12)]
_KC = [("#e8574a", "#9a2a20"), ("#4a9ae8", "#20609a"), ("#f2c230", "#a07c10"), ("#5cc46a", "#2a7a36")]
KIDS = [dict(K.KID1 if i % 2 == 0 else K.KID2, vary=340 + i, top=_KC[i], leg_col=_KC[(i + 1) % 4], coat=None, tie=None, backpack=None,
             hair=("bob", "bangs")[i % 2], hair_col=("#1a1414", "#3a2616", "#14100c", "#5a3a20")[i], height=1.22 + 0.04 * i) for i in range(4)]
_TC = [("#e8a0c0", "#a05a78"), ("#3aa8c8", "#1a6a88"), ("#f0b840", "#a07818"), ("#8a5ac8", "#4a2a88"), ("#e86a3a", "#9a3a1a"), ("#6ac85a", "#2a8a2a")]
TOWNSFOLK = [dict((K.W_LOOKS[i % 4] if i % 2 == 0 else K.MAN_LONG), vary=360 + i, coat=_TC[i], top=_TC[(i + 2) % 6], leg_col=_TC[(i + 3) % 6],
                  hem=0.5, hair_col=("#2a1a10", "#6a3a1a", "#d8b060", "#14100c", "#8a2a1a", "#3a2a5a")[i], clear_face=True) for i in range(6)]
STYLES = dict(BOY=BOY, TEEN=TEEN, HERO=HERO, HERO_HUMAN=HERO_HUMAN, MOTHER=MOTHER, FATHER=FATHER, MASTER=MASTER, VASSAL=VASSAL,
              CLAN_MEN=CLAN_MEN, CLAN_WOMEN=CLAN_WOMEN, FIGHTERS=FIGHTERS, KIDS=KIDS, TOWNSFOLK=TOWNSFOLK)
_V1 = ("TEEN", "HERO", "HERO_HUMAN")        # built with the first-version builder (the hero's body and face)
_GROUPS = dict(CLAN_MEN="CLAN_MEN", CLAN_WOMEN="CLAN_WOMEN", FIGHTERS="FIGHTER", KIDS="KID", TOWNSFOLK="TOWN")

# ------------------------------------------------------------------ build
def _glasses(arm, coll, objs, colour):
    """Tinted round lenses + bridge on the head bone (the rig has no glasses of its own)."""
    bpy.context.view_layer.update()
    eyes = [o for o in objs if o.name.startswith("eye_")]
    if len(eyes) < 2: return []
    s = arm.scale[0] / 0.83; R = arm.matrix_world.to_3x3(); fwd = R @ V((0, -1, 0)); fwd.normalize()
    m = ch.cel(colour, None, rim="#8fa8c8", name="lens"); out = []; ps = [o.matrix_world.translation.copy() for o in eyes]
    for p in ps:
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.032 * s, depth=0.006 * s, location=p + fwd * 0.03 * s,
                                            rotation=(math.radians(90), 0, arm.rotation_euler.z))
        ob = bpy.context.object; ob.data.materials.append(m)
        for c in list(ob.users_collection): c.objects.unlink(ob)
        coll.objects.link(ob); ch.bone_parent(ob, arm, "head"); out.append(ob)
    return out

def _kit(name, arm, coll, objs, st, cloak):
    if name == "MOTHER":
        KM.add_robe(arm, coll, "#3a3446"); KM.add_obi(arm, coll, "#1a1620"); KM.add_crests(arm, coll); KM.add_bun(arm, coll)
    elif name == "FATHER":
        KM.add_robe(arm, coll, "#16161c"); KM.add_obi(arm, coll, "#0e0e14"); KM.add_cloak(arm, coll)
    elif name == "MASTER":
        KM.add_robe(arm, coll, "#1a1a20"); KM.add_obi(arm, coll, "#0e0e14"); KM.add_topknot(arm, coll); KM.add_beard(arm, coll)
    elif name.startswith("CLAN_"):
        KM.add_robe(arm, coll, st["leg_col"][0] if isinstance(st["leg_col"], tuple) else st["leg_col"]); KM.add_obi(arm, coll, "#16121e")
    elif name in ("HERO", "TEEN", "HERO_HUMAN") and cloak:
        KM.add_cloak(arm, coll)
    if st.get("glasses"): _glasses(arm, coll, objs, st["glasses"])

def _expand(which):
    if which is None: which = list(STYLES)
    if isinstance(which, str): which = [which]
    out = []
    for w in which:
        if w in _GROUPS: out += [(f"{_GROUPS[w]}_{i}", STYLES[w][i], w) for i in range(len(STYLES[w]))]
        elif w in STYLES: out.append((w, STYLES[w], w))
        else:
            g = next((k for k, p in _GROUPS.items() if w.startswith(p + "_")), None)
            if g is None: raise KeyError(w)
            out.append((w, STYLES[g][int(w.rsplit("_", 1)[1])], g))
    return out

def build_cast(P, which=None, locs=None, scales=None, hero_cloak=False, heading=0.0):
    """-> {name: armature}. locs: name -> (x,y,z); default spreads along +X, 1.5 m apart. scales: name -> scale (TEEN: 0.88)."""
    locs = locs or {}; scales = scales or {}; res = {}; x = 0.0
    for name, st, grp in _expand(which):
        st = dict(st); void = bool(st.get("void_eyes")); sc = scales.get(name, 1.0)
        if grp in _V1:
            g, objs = ch.build_v1(P, (0, 0, 0), st, pose_mode="stand", void_eyes=void)
        else:
            g, objs = ch.build(P, (0, 0, 0), st, pose_mode="stand", heading=0)
        loc = V(locs.get(name, (x, 0, 0))); x += 1.5
        g.location = loc + V((0, 0, g["ground_rest"] * sc)); g.scale = (sc,) * 3
        g.rotation_euler = (0, 0, math.radians(heading)); g["base_z"] = g["ground_rest"] * sc
        _kit(name, g, P, objs, st, hero_cloak)
        res[name] = g
    return res

# ------------------------------------------------------------------ silhouette crowd
_SIL = {}
def _sil_mesh():
    """One shared mesh: black cone body + sphere head (slot 0) and a bigger flipped hull (slot 1) that only shows as a white rim."""
    if "me" in _SIL: return _SIL["me"]
    def figure(bm, grow, flip):
        a = bmesh.ops.create_cone(bm, segments=8, radius1=0.27 + grow, radius2=0.17 + grow, depth=1.15 + 2 * grow, cap_ends=True,
                                  matrix=Matrix.Translation((0, 0, 0.58)))["verts"]
        b = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.13 + grow, matrix=Matrix.Translation((0, 0, 1.38)))["verts"]
        fs = {f for v in a + b for f in v.link_faces}
        if flip: bmesh.ops.reverse_faces(bm, faces=list(fs))
        return fs
    bm = bmesh.new(); figure(bm, 0.0, False)
    for f in bm.faces: f.material_index = 0
    for f in figure(bm, 0.035, True): f.material_index = 1
    me = bpy.data.meshes.new("sil_crowd"); bm.to_mesh(me); bm.free()
    m0 = bpy.data.materials.new("sil_black"); m0.use_nodes = True; nt = m0.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (0.01, 0.01, 0.014, 1); nt.links.new(e.outputs[0], o.inputs[0])
    m1 = bpy.data.materials.new("sil_rim"); m1.use_nodes = True; nt = m1.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission"); t = nt.nodes.new("ShaderNodeBsdfTransparent")
    bf = nt.nodes.new("ShaderNodeNewGeometry"); mx = nt.nodes.new("ShaderNodeMixShader")
    e.inputs["Color"].default_value = (1, 1, 1, 1); e.inputs["Strength"].default_value = 3.0
    nt.links.new(bf.outputs["Backfacing"], mx.inputs[0]); nt.links.new(e.outputs[0], mx.inputs[1]); nt.links.new(t.outputs[0], mx.inputs[2])   # near shell (backfacing) clear, far shell white
    nt.links.new(mx.outputs[0], o.inputs[0])
    me.materials.append(m0); me.materials.append(m1); _SIL["me"] = me
    return me

def make_silhouette_crowd(P, n, area=((-10, 10), (0, 12)), rows=None, seed=1, height=(1.55, 1.85), heading=0.0, jitter=0.3, name="sil"):
    """n flat black figures with a white rim, all sharing ONE mesh (~230 tris each). area=((x0,x1),(y0,y1)); rows=k puts them in k even rows
    in y, else random. heading = degrees the figures face (they are round, so it only matters for the cone; kept for symmetry)."""
    me = _sil_mesh(); rng = random.Random(seed); out = []
    (x0, x1), (y0, y1) = area
    for i in range(n):
        if rows:
            r = i % rows; y = y0 + (y1 - y0) * (r / max(1, rows - 1)) if rows > 1 else y0
            x = x0 + (x1 - x0) * ((i // rows + 0.5) / max(1, math.ceil(n / rows))) + rng.uniform(-jitter, jitter)
            y += rng.uniform(-jitter, jitter)
        else:
            x = rng.uniform(x0, x1); y = rng.uniform(y0, y1)
        ob = bpy.data.objects.new(f"{name}_{i}", me); P.objects.link(ob); ob.location = (x, y, 0)
        h = rng.uniform(*height) / 1.55; ob.scale = (rng.uniform(0.85, 1.1), rng.uniform(0.85, 1.1), h)
        ob.rotation_euler = (0, 0, math.radians(heading + rng.uniform(-10, 10)))
        ob.visible_shadow = False
        out.append(ob)
    return out
