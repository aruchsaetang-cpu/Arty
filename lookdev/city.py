"""Sol: an original procedural night city for the story shorts.

    /root/.venvs/bpy/bin/python lookdev/city.py <shot> [scale%]
shots: street | hero | alley | aerial | clip   (clip renders an animated test sequence)
env: SAMPLES (default 96), FRAMES (clip length, default 72), PEOPLE (default 28), SEED

Main street runs along +y with sidewalks, alleys branching off, a crosswalk, utility poles and
sagging wires, shopfronts with light spill, blade signs, AC units, balconies, rooftop tanks,
parked and moving cars, a walking crowd (umbrellas, phones), rain, steam and flickering neon.
Everything is generated here: no downloaded assets, no real signage or landmarks.
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import character_mh as ch

SHOT = sys.argv[1] if len(sys.argv) > 1 else "street"
SCALE = int(sys.argv[2]) if len(sys.argv) > 2 else 50
SAMPLES = int(os.environ.get("SAMPLES", 96))
FRAMES = int(os.environ.get("FRAMES", 72))
PEOPLE = int(os.environ.get("PEOPLE", 28))
random.seed(int(os.environ.get("SEED", 11)))
OUT = os.path.join(HERE, "renders"); os.makedirs(OUT, exist_ok=True)
FONT_PATH = os.path.join(HERE, "assets", "fonts", "NanumSquareEB.ttf")   # Korean signage (Nanum, SIL OFL)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = 30; scn.frame_start = 1; scn.frame_end = FRAMES
prefs = bpy.context.preferences.edit
def C(name):
    c = bpy.data.collections.new(name); scn.collection.children.link(c); return c
CITY, PROPS, PEOPLE_C, FX = C("city"), C("props"), C("people"), C("fx")
lin = ch.lin
FONT = bpy.data.fonts.load(FONT_PATH) if os.path.exists(FONT_PATH) else None

# ======================================================================= node helper
class G:
    def __init__(self, mat):
        mat.use_nodes = True; self.nt = mat.node_tree; self.N = self.nt.nodes; self.L = self.nt.links
        self.N.clear(); self.out = self.N.new("ShaderNodeOutputMaterial")
    def n(self, t, **kw):
        nd = self.N.new(t)
        for k, v in kw.items():
            if k.startswith("_"): setattr(nd, k[1:], v)
            else: nd.inputs[k].default_value = v
        return nd
    def ln(self, a, b): self.L.new(a, b)
    def m(self, op, a, b=None, clamp=False):
        x = self.n("ShaderNodeMath", _operation=op, _use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): x.inputs[i].default_value = v
            else: self.ln(v, x.inputs[i])
        return x.outputs[0]
    def mix(self, f, a, b, rgba=True):
        x = self.n("ShaderNodeMix", _data_type="RGBA" if rgba else "FLOAT")
        ia, ib = (6, 7) if rgba else (2, 3)
        for s, v in ((0, f), (ia, a), (ib, b)):
            if isinstance(v, (int, float, tuple)): x.inputs[s].default_value = v
            else: self.ln(v, x.inputs[s])
        return x.outputs[2 if rgba else 0]
    def band(self, x, lo, hi): return self.m("MULTIPLY", self.m("GREATER_THAN", x, lo), self.m("LESS_THAN", x, hi))
    def bsdf(self):
        b = self.n("ShaderNodeBsdfPrincipled"); self.ln(b.outputs[0], self.out.inputs[0]); return b

def drive(socket, expr, prop="default_value", index=-1):
    fc = socket.driver_add(prop, index) if index >= 0 else socket.driver_add(prop)
    fc.driver.type = "SCRIPTED"; fc.driver.expression = expr
    return fc

# ======================================================================= materials
_M = {}
def principled(name, col, rough=0.5, metal=0.0, spec=0.5):
    if name in _M: return _M[name]
    m = bpy.data.materials.new(name); g = G(m); b = g.bsdf()
    b.inputs["Base Color"].default_value = lin(col); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Specular IOR Level"].default_value = spec
    _M[name] = m; return m

def grimy(name, col, col2, rough=0.6, scale=2.0, bump=0.2):
    if name in _M: return _M[name]
    m = bpy.data.materials.new(name); g = G(m); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord"); nz = g.n("ShaderNodeTexNoise", Scale=scale, Detail=8.0)
    g.ln(tc.outputs["Object"], nz.inputs["Vector"])
    streak = g.n("ShaderNodeTexNoise", Scale=scale * 0.5, Detail=4.0)
    mp = g.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (6, 6, 0.4)
    g.ln(tc.outputs["Object"], mp.inputs[0]); g.ln(mp.outputs[0], streak.inputs["Vector"])
    c = g.mix(nz.outputs["Fac"], lin(col), lin(col2))
    c = g.mix(g.m("MULTIPLY", streak.outputs["Fac"], 0.5), c, lin("#141518"))      # rain streak grime
    g.ln(c, b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    bp = g.n("ShaderNodeBump", Strength=bump); g.ln(nz.outputs["Fac"], bp.inputs["Height"]); g.ln(bp.outputs[0], b.inputs["Normal"])
    _M[name] = m; return m

def glow(col, strength=6.0, flicker=None, name=None):
    key = name or f"glow_{col}_{strength}_{flicker}"
    if key in _M: return _M[key]
    m = bpy.data.materials.new(key); g = G(m)
    e = g.n("ShaderNodeEmission"); e.inputs["Color"].default_value = lin(col); e.inputs["Strength"].default_value = strength
    g.ln(e.outputs[0], g.out.inputs[0])
    if flicker == "soft":
        drive(e.inputs["Strength"], f"{strength}*(0.88+0.12*sin(frame*2.3)*sin(frame*0.41))")
    elif flicker == "broken":
        drive(e.inputs["Strength"], f"{strength}*max(0.05, min(1, 3*sin(frame*0.8)*sin(frame*0.27)+0.6))")
    _M[key] = m; return m

def asphalt():
    m = bpy.data.materials.new("asphalt"); g = G(m); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord")
    pud = g.n("ShaderNodeTexNoise", Scale=0.18, Detail=3.0, Roughness=0.6); g.ln(tc.outputs["Object"], pud.inputs["Vector"])
    mr = g.n("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.52; mr.inputs[2].default_value = 0.58
    g.ln(pud.outputs["Fac"], mr.inputs[0]); M = mr.outputs[0]
    grain = g.n("ShaderNodeTexNoise", Scale=240.0, Detail=4.0); g.ln(tc.outputs["Object"], grain.inputs["Vector"])
    stain = g.n("ShaderNodeTexNoise", Scale=1.4, Detail=5.0); g.ln(tc.outputs["Object"], stain.inputs["Vector"])
    patch = g.n("ShaderNodeTexVoronoi", Scale=0.35); g.ln(tc.outputs["Object"], patch.inputs["Vector"])   # repair patches
    base = g.mix(stain.outputs["Fac"], lin("#17191c"), lin("#2b2d30"))
    base = g.mix(g.m("MULTIPLY", g.m("GREATER_THAN", patch.outputs["Distance"], 0.42), 0.6), base, lin("#202226"))
    base = g.mix(g.m("MULTIPLY", grain.outputs["Fac"], 0.45), base, lin("#3a3c3f"))
    base = g.mix(M, base, lin("#0b0c0e"))
    g.ln(base, b.inputs["Base Color"]); g.ln(g.mix(M, 0.5, 0.02, rgba=False), b.inputs["Roughness"])
    vor = g.n("ShaderNodeTexVoronoi", Scale=7.0, _voronoi_dimensions="4D"); g.ln(tc.outputs["Object"], vor.inputs["Vector"])
    drive(vor.inputs["W"], "frame/7")                                      # rain ripples evolve every frame
    rings = g.m("MULTIPLY", g.m("SINE", g.m("MULTIPLY", vor.outputs["Distance"], 70.0)), g.m("LESS_THAN", vor.outputs["Distance"], 0.1))
    h = g.mix(M, g.m("MULTIPLY", grain.outputs["Fac"], 1.0), g.m("MULTIPLY", rings, 0.18), rgba=False)
    bp = g.n("ShaderNodeBump", Strength=0.35, Distance=0.002); g.ln(h, bp.inputs["Height"]); g.ln(bp.outputs[0], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = 0.6
    return m

def pavers():
    m = bpy.data.materials.new("pavers"); g = G(m); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord"); br = g.n("ShaderNodeTexBrick", Scale=3.2, **{"Mortar Size": 0.012})
    br.inputs["Color1"].default_value = lin("#55585c"); br.inputs["Color2"].default_value = lin("#4a4c50")
    br.inputs["Mortar"].default_value = lin("#1e1f22")
    g.ln(tc.outputs["Object"], br.inputs["Vector"])
    wet = g.n("ShaderNodeTexNoise", Scale=0.6, Detail=3.0); g.ln(tc.outputs["Object"], wet.inputs["Vector"])
    W = g.m("GREATER_THAN", wet.outputs["Fac"], 0.5)
    g.ln(g.mix(W, br.outputs["Color"], lin("#1c1d20")), b.inputs["Base Color"])
    g.ln(g.mix(W, 0.32, 0.05, rgba=False), b.inputs["Roughness"])
    bp = g.n("ShaderNodeBump", Strength=0.4); g.ln(br.outputs["Fac"], bp.inputs["Height"]); g.ln(bp.outputs[0], b.inputs["Normal"])
    return m

FACADES = {   # base, base2, bay width, floor height, window w/h, lit chance
    "tile":     ("#b9ad98", "#8c8273", 2.2, 3.2, 0.62, 0.55, 0.38),
    "concrete": ("#6d6f72", "#45474b", 2.6, 3.3, 0.55, 0.5, 0.3),
    "brick":    ("#6e3b2c", "#4a271d", 1.8, 3.0, 0.5, 0.55, 0.35),
    "dark":     ("#25282d", "#16181b", 1.6, 3.4, 0.8, 0.7, 0.45),
    "white":    ("#d4d2cc", "#a9a7a2", 2.4, 3.2, 0.6, 0.55, 0.32),
    "glass":    ("#1b2733", "#0e151c", 1.5, 3.6, 0.94, 0.86, 0.5),
}
def facade(kind):
    if f"fac_{kind}" in _M: return _M[f"fac_{kind}"]
    base, base2, bay, fl, ww, wh, litp = FACADES[kind]
    m = bpy.data.materials.new(f"fac_{kind}"); g = G(m); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord"); geo = g.n("ShaderNodeNewGeometry"); info = g.n("ShaderNodeObjectInfo")
    so = g.n("ShaderNodeSeparateXYZ"); g.ln(tc.outputs["Object"], so.inputs[0])
    sw = g.n("ShaderNodeSeparateXYZ"); g.ln(geo.outputs["Position"], sw.inputs[0])
    u = g.m("DIVIDE", g.m("ADD", so.outputs["X"], so.outputs["Y"]), bay); v = g.m("DIVIDE", sw.outputs["Z"], fl)
    fu, fv = g.m("FRACT", u), g.m("FRACT", v)
    win = g.m("MULTIPLY", g.band(fu, (1 - ww) / 2, (1 + ww) / 2), g.band(fv, 0.18, 0.18 + wh))
    win = g.m("MULTIPLY", win, g.m("GREATER_THAN", sw.outputs["Z"], 4.4))
    roofn = g.n("ShaderNodeVectorMath", _operation="DOT_PRODUCT"); g.ln(geo.outputs["Normal"], roofn.inputs[0]); roofn.inputs[1].default_value = (0, 0, 1)
    win = g.m("MULTIPLY", win, g.m("LESS_THAN", roofn.outputs["Value"], 0.5))
    cell = g.n("ShaderNodeCombineXYZ"); g.ln(g.m("FLOOR", u), cell.inputs[0]); g.ln(g.m("FLOOR", v), cell.inputs[1]); g.ln(info.outputs["Random"], cell.inputs[2])
    wn = g.n("ShaderNodeTexWhiteNoise", _noise_dimensions="3D"); g.ln(cell.outputs[0], wn.inputs["Vector"])
    sc = g.n("ShaderNodeSeparateColor"); g.ln(wn.outputs["Color"], sc.inputs[0])
    lit = g.m("MULTIPLY", win, g.m("LESS_THAN", sc.outputs[0], litp))
    warm = g.mix(sc.outputs[1], lin("#ffc887"), lin("#fff1d6")); cool = lin("#cfe9ff")
    lc = g.mix(g.m("GREATER_THAN", sc.outputs[2], 0.62), warm, cool)
    lc = g.mix(g.m("GREATER_THAN", sc.outputs[2], 0.93), lc, lin("#7fd8ff"))                 # tv glow rooms
    blinds = g.m("ADD", 0.55, g.m("MULTIPLY", g.m("GREATER_THAN", g.m("FRACT", g.m("MULTIPLY", fv, 14)), 0.5), 0.45))
    blinds = g.mix(g.m("GREATER_THAN", sc.outputs[1], 0.7), 1.0, blinds, rgba=False)
    grad = g.m("ADD", 0.55, g.m("MULTIPLY", fv, 0.9))                                           # ceiling-lit falloff
    nz = g.n("ShaderNodeTexNoise", Scale=1.6, Detail=8.0); g.ln(tc.outputs["Object"], nz.inputs["Vector"])
    stain = g.n("ShaderNodeTexNoise", Scale=0.9, Detail=3.0)
    mp = g.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (3, 3, 0.25)
    g.ln(tc.outputs["Object"], mp.inputs[0]); g.ln(mp.outputs[0], stain.inputs["Vector"])
    wall = g.mix(nz.outputs["Fac"], lin(base), lin(base2))
    wall = g.mix(g.m("MULTIPLY", stain.outputs["Fac"], 0.55), wall, lin("#1a1b1e"))
    wall = g.mix(g.m("LESS_THAN", sw.outputs["Z"], 4.4), wall, lin("#1b1c1f"))
    g.ln(g.mix(win, wall, lin("#06080b")), b.inputs["Base Color"])
    g.ln(g.mix(win, 0.82 if kind != "glass" else 0.25, 0.04, rgba=False), b.inputs["Roughness"])
    if kind == "glass":
        b.inputs["Metallic"].default_value = 0.3
    em = g.mix(lit, lin("#000000"), lc)
    ems = g.m("MULTIPLY", g.m("MULTIPLY", blinds, grad), 3.2)
    g.ln(em, b.inputs["Emission Color"]); g.ln(ems, b.inputs["Emission Strength"])
    bp = g.n("ShaderNodeBump", Strength=0.15); g.ln(nz.outputs["Fac"], bp.inputs["Height"]); g.ln(bp.outputs[0], b.inputs["Normal"])
    _M[f"fac_{kind}"] = m; return m

def shopglass(col):
    key = f"shop_{col}"
    if key in _M: return _M[key]
    m = bpy.data.materials.new(key); g = G(m); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord"); so = g.n("ShaderNodeSeparateXYZ"); g.ln(tc.outputs["Generated"], so.inputs[0])
    shelves = g.m("GREATER_THAN", g.m("FRACT", g.m("MULTIPLY", so.outputs["Z"], 5.0)), 0.18)          # shelf bands
    racks = g.m("GREATER_THAN", g.m("FRACT", g.m("MULTIPLY", g.m("ADD", so.outputs["X"], so.outputs["Y"]), 7.0)), 0.12)
    goods = g.n("ShaderNodeTexWhiteNoise", _noise_dimensions="3D")
    mp = g.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (40, 40, 10); g.ln(tc.outputs["Generated"], mp.inputs[0])
    flo = g.n("ShaderNodeVectorMath", _operation="FLOOR"); g.ln(mp.outputs[0], flo.inputs[0]); g.ln(flo.outputs[0], goods.inputs["Vector"])
    c = g.mix(g.m("MULTIPLY", shelves, racks), lin("#2b241c"), lin(col))
    c = g.mix(g.m("MULTIPLY", g.m("GREATER_THAN", goods.outputs["Value"], 0.55), 0.5), c, goods.outputs["Color"])
    b.inputs["Base Color"].default_value = lin("#05070a"); b.inputs["Roughness"].default_value = 0.03
    g.ln(c, b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.3
    _M[key] = m; return m

ASPH = asphalt(); PAVE = pavers()
CURB = grimy("curb", "#6a6d70", "#3f4144", 0.35, 4.0)
METAL = principled("metal_dark", "#202226", 0.45, 0.8)
METAL_L = principled("metal_light", "#b8b9b6", 0.4, 0.3)
CONC = grimy("ledge", "#77797c", "#4b4d50", 0.7, 3.0)
GLASS = principled("glass_dark", "#0b1016", 0.05, 0.0, 0.8)
WIRE = principled("wire", "#0c0d0f", 0.5, 0.2)
PAINT = principled("road_paint", "#c9ccc8", 0.35)
FABRIC = {c: principled(f"awning_{c}", c, 0.7) for c in ("#8b1d24", "#1f4d3a", "#2b3e66", "#c7a24a", "#3a3a3e")}
NEON = ["#ff2f6d", "#18e4ff", "#ffb02e", "#7dff6a", "#c45bff", "#ff6a1f", "#f5f1e8", "#3d7bff"]

# ======================================================================= geometry helpers
class Batch:
    """Many boxes/cylinders merged into one mesh per material (fast for thousands of details)."""
    def __init__(self, name, mat): self.bm = bmesh.new(); self.name = name; self.mat = mat
    def box(self, M, c, size, rz=0.0):
        T = M @ Matrix.Translation(c) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Diagonal((size[0], size[1], size[2], 1))
        bmesh.ops.create_cube(self.bm, size=1.0, matrix=T)
    def cyl(self, M, c, r, h, seg=12, rot=None):
        T = M @ Matrix.Translation(c) @ (rot or Matrix.Identity(4))
        bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h, matrix=T)
    def done(self, coll):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        ob = bpy.data.objects.new(self.name, me); coll.objects.link(ob); me.materials.append(self.mat)
        return ob

_B = {}
def B(name, mat):
    if name not in _B: _B[name] = Batch(name, mat)
    return _B[name]

def obj_box(name, M, c, size, mat, coll=CITY, bevel=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((size[0], size[1], size[2], 1))); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.matrix_world = M @ Matrix.Translation(c)
    me.materials.append(mat)
    if bevel:
        bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 2
    return ob

def text(body, M, loc, rot, size, mat, coll=PROPS, align="CENTER", extrude=0.01, line=1.0):
    cu = bpy.data.curves.new("txt", "FONT"); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = "CENTER"; cu.space_line = line
    if FONT: cu.font = FONT
    ob = bpy.data.objects.new("txt", cu); coll.objects.link(ob); cu.materials.append(mat)
    ob.matrix_world = M @ Matrix.Translation(loc) @ rot
    return ob

def area(name, M, loc, target, size, watts, col, coll=CITY, shape="SQUARE", size_y=None):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = watts; ld.color = lin(col)[:3]
    ld.shape = shape if size_y is None else "RECTANGLE"; ld.size = size
    if size_y: ld.size_y = size_y
    ob = bpy.data.objects.new(name, ld); coll.objects.link(ob)
    p = M @ Vector(loc); t = M @ Vector(target)
    q = (t - p).to_track_quat("-Z", "Y")
    ob.matrix_world = Matrix.Translation(p) @ q.to_matrix().to_4x4()
    return ob

def spot(M, loc, watts, col, size_deg=75, blend=0.5, coll=PROPS):
    ld = bpy.data.lights.new("spot", "SPOT"); ld.energy = watts; ld.color = lin(col)[:3]
    ld.spot_size = math.radians(size_deg); ld.spot_blend = blend; ld.shadow_soft_size = 0.2
    ob = bpy.data.objects.new("spot", ld); coll.objects.link(ob); ob.matrix_world = M @ Matrix.Translation(loc)
    return ob

ROT_FACE_STREET = Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X")  # text on local -x face

# ======================================================================= buildings
# Korean signage, same list lengths as before so the seeded layout is unchanged
SHOP_NAMES = ["국수집", "24시 마트", "노래방", "숯불구이", "약국", "달빛카페", "만두", "오락실",
              "호텔", "안경원", "서점", "빵집", "PC방", "수산시장", "찻집", "치과", "세탁소",
              "라멘", "꽃집", "사진관", "초밥", "미용실", "3층 주점", "커피"]
BLADE = ["호텔", "노래방", "주점", "의원", "게임장", "사우나", "당구장", "국수", "모텔", "사진관", "식당", "클럽", "고기", "호프"]
BILLBOARD = ["솔", "강변선", "심야영업", "하늘은행", "루나항공"]

def building(M, w, depth, h, kind, shop=True, blades=1, detail="ledges", rooftop=True, tag=""):
    """Local frame: facade plane at x=0, building extends to +x, spans y in [0,w]; street is toward -x."""
    mass = obj_box(f"bld{tag}", M, (depth / 2, w / 2, h / 2), (depth, w - 0.08, h), facade(kind))
    floors = int((h - 4.4) / FACADES[kind][3])
    fl = FACADES[kind][3]; bay = FACADES[kind][2]
    # --- façade relief
    if detail == "ledges":
        for k in range(floors + 1):
            B("ledges", CONC).box(M, (-0.1, w / 2, 4.4 + k * fl + 0.05), (0.22, w - 0.08, 0.14))
    elif detail == "fins":
        nb = int(w / bay)
        for k in range(nb + 1):
            B("fins", METAL).box(M, (-0.18, k * w / nb, (h + 4.4) / 2), (0.36, 0.12, h - 4.4))
    elif detail == "balcony":
        for k in range(1, floors):
            for yb in range(int(w / 3.2)):
                if random.random() < 0.7:
                    y = 1.6 + yb * 3.2; z = 4.4 + k * fl
                    B("ledges", CONC).box(M, (-0.55, y, z), (1.1, 2.6, 0.12))
                    B("rail", METAL).box(M, (-1.08, y, z + 0.5), (0.04, 2.6, 0.04))
                    for r in range(9):
                        B("rail", METAL).box(M, (-1.08, y - 1.25 + r * 0.31, z + 0.27), (0.03, 0.03, 0.5))
                    if random.random() < 0.4:   # laundry / plants / boxes
                        B("clutter", principled("clutter", random.choice(["#8a8f96", "#3d5a40", "#a3734a"]), 0.8)).box(
                            M, (-0.7, y + random.uniform(-0.8, 0.8), z + 0.3), (0.4, 0.5, 0.5))
    # AC units, pipes
    for k in range(1, floors + 1):
        for yb in range(int(w / bay)):
            if random.random() < 0.22:
                y = (yb + 0.5) * bay; z = 4.4 + k * fl - 0.55
                B("ac", METAL_L).box(M, (-0.3, y, z), (0.6, 0.85, 0.6))
                B("ac_grille", METAL).cyl(M, (-0.61, y, z), 0.22, 0.02, 16, Matrix.Rotation(math.radians(90), 4, "Y"))
    B("pipes", METAL).cyl(M, (-0.12, 0.25, h / 2), 0.06, h, 8)
    # --- ground floor shopfront
    if shop:
        col = random.choice(["#ffd9a0", "#fff2d8", "#d8f0ff", "#ffe3c0", "#ffcf9a"])
        g = obj_box(f"shop{tag}", M, (-0.02, w / 2, 1.85), (0.06, w - 0.9, 3.1), shopglass(col))
        n_m = max(2, int(w / 1.6))
        for k in range(n_m + 1):
            B("mullion", METAL).box(M, (-0.07, 0.45 + k * (w - 0.9) / n_m, 1.85), (0.08, 0.07, 3.1))
        B("mullion", METAL).box(M, (-0.07, w / 2, 3.42), (0.1, w - 0.8, 0.1))
        B("mullion", METAL).box(M, (-0.07, w / 2, 0.25), (0.1, w - 0.8, 0.1))
        sign_c = random.choice(NEON)
        name = random.choice(SHOP_NAMES)
        B("fascia", METAL).box(M, (-0.18, w / 2, 3.95), (0.3, w - 0.3, 0.75))
        obj_box("signface", M, (-0.34, w / 2, 3.95), (0.02, w - 0.6, 0.6), glow(sign_c, 2.2))
        text(name, M, (-0.36, w / 2, 3.95), ROT_FACE_STREET, 0.48, glow("#fffaf0" if sign_c != "#f5f1e8" else "#202024", 4.0), extrude=0.02)
        if random.random() < 0.45:   # awning
            fab = random.choice(list(FABRIC.values()))
            aw = obj_box("awning", M @ Matrix.Translation((0, 0, 3.5)) @ Matrix.Rotation(math.radians(-18), 4, "Y"),
                         (-0.7, w / 2, 0), (1.5, w - 0.4, 0.05), fab)
        area("spill", M, (-1.4, w / 2, 3.3), (-2.6, w / 2, 0.0), w * 0.7, random.uniform(140, 260), col, size_y=0.6)
    # --- blade signs (vertical neon), letters on both faces
    for k in range(blades):
        bh = random.uniform(4.0, 9.0); bz = random.uniform(5.0, max(5.5, min(h - bh - 0.5, 12.0)))
        y = random.uniform(0.6, w - 0.6); c = random.choice(NEON); word = random.choice(BLADE)
        flick = random.choice([None, None, "soft", "broken"]) if k == 0 else None
        B("blade_frame", METAL).box(M, (-0.75, y, bz + bh / 2), (1.3, 0.34, bh + 0.2))
        obj_box("blade", M, (-0.75, y, bz + bh / 2), (1.1, 0.36, bh), glow(c, 3.0, flick))
        chars = word.replace(" ", "")[:max(2, int(bh / 1.05))]
        letters = "\n".join(chars)    # Korean vertical sign: one syllable per row, spread down the blade
        spread = min(1.9, max(1.05, 0.72 * bh / (len(chars) * 0.88)))
        for face, rz in ((-0.19, 0), (0.19, 180)):
            text(letters, M, (-0.75, y + face, bz + bh / 2), Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Rotation(math.radians(rz), 4, "Y"),
                 0.88, glow("#ffffff", 5.0, flick), extrude=0.01, line=spread)
        B("blade_arm", METAL).box(M, (-0.2, y, bz + bh + 0.1), (0.5, 0.06, 0.06))
    # --- rooftop
    if rooftop:
        for (cx, cy, sx, sy) in ((depth / 2, 0.1, depth, 0.2), (depth / 2, w - 0.1, depth, 0.2), (0.1, w / 2, 0.2, w), (depth - 0.1, w / 2, 0.2, w)):
            B("parapet", CONC).box(M, (cx, cy, h + 0.45), (sx, sy, 0.9))
        if random.random() < 0.7:
            tx, ty = random.uniform(2, depth - 2), random.uniform(1.5, w - 1.5)
            B("tank", principled("tank", random.choice(["#3a6ea8", "#b9bcbf", "#d8d2c4"]), 0.4, 0.4)).cyl(M, (tx, ty, h + 2.0), 0.9, 1.8, 16)
            for dx, dy in ((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)):
                B("pipes", METAL).box(M, (tx + dx, ty + dy, h + 0.55), (0.08, 0.08, 1.1))
        if random.random() < 0.6:
            B("hut", CONC).box(M, (depth * 0.7, w * 0.6, h + 1.3), (2.6, 2.2, 2.6))
        for k in range(random.randint(1, 4)):
            B("ac", METAL_L).box(M, (random.uniform(1, depth - 1), random.uniform(1, w - 1), h + 0.45), (0.9, 0.9, 0.9))
        if random.random() < 0.35:
            B("pipes", METAL).cyl(M, (depth * 0.3, w * 0.3, h + 3.5), 0.04, 7.0, 6)
            obj_box("beacon", M, (depth * 0.3, w * 0.3, h + 7.05), (0.12, 0.12, 0.12), glow("#ff2020", 25, "soft"))
        if random.random() < 0.3 and h < 26:   # rooftop billboard facing the street
            B("bb_frame", METAL).box(M, (0.8, w / 2, h + 3.4), (0.3, min(w - 1, 8), 4.6))
            obj_box("billboard", M, (0.62, w / 2, h + 3.6), (0.04, min(w - 1.4, 7.6), 3.8),
                    glow(random.choice(NEON), 2.0))
            text(random.choice(BILLBOARD), M, (0.6, w / 2, h + 3.6),
                 ROT_FACE_STREET, 0.9, glow("#101014", 1.0), extrude=0.02)
    return mass

# ======================================================================= layout
ROAD_HALF, WALK = 4.6, 3.0
FRONT = ROAD_HALF + WALK          # 7.6
STREET_Y = (-14, 150)
ALLEYS = {-1: [30, 68, 112], 1: [46, 90]}   # y of alley openings per side
ALLEY_W = 5.0
CROSS_Y = 22.0

def street_side(side):
    y = STREET_Y[0]; i = 0
    kinds = ["tile", "concrete", "brick", "dark", "white", "tile", "concrete"]
    gaps = sorted(ALLEYS[side])
    while y < STREET_Y[1]:
        g = next((a for a in gaps if a - 0.01 <= y < a + ALLEY_W), None)
        if g is not None:
            y = g + ALLEY_W; continue
        w = random.uniform(7, 13)
        nxt = next((a for a in gaps if a > y), None)
        if nxt is not None and y + w > nxt - 3.0:
            w = nxt - y
        h = random.choice([random.uniform(12, 20), random.uniform(18, 30), random.uniform(26, 42)])
        depth = random.uniform(13, 18)
        kind = random.choice(kinds)
        detail = random.choice(["ledges", "ledges", "balcony", "fins"])
        if side > 0:
            M = Matrix.Translation((FRONT, y, 0))
        else:
            M = Matrix.Translation((-FRONT, y + w, 0)) @ Matrix.Rotation(math.pi, 4, "Z")
        building(M, w, depth, h, kind, shop=True, blades=random.choice([0, 1, 1, 2]), detail=detail, tag=f"{side}_{i}")
        y += w; i += 1

def alley(side, ya):
    """Narrow lane running away from the main street, lined with small buildings, signs and lanterns."""
    xs = FRONT + 19.0          # first stretch is flanked by the side walls of the main-street blocks
    for wall in (+1, -1):          # buildings on the +y and -y sides of the alley
        x = xs; i = 0
        while x < xs + 36:
            w = random.uniform(6, 10); h = random.uniform(9, 22); depth = random.uniform(8, 12)
            Mb = alley_frame(side, wall, ya, x, w)
            building(Mb, w, depth, h, random.choice(["tile", "brick", "concrete", "white"]), shop=random.random() < 0.8,
                     blades=random.choice([0, 1]), detail=random.choice(["ledges", "balcony"]), rooftop=True, tag=f"a{side}{ya}{wall}{i}")
            x += w; i += 1
    # paper lanterns strung across the alley + a crossing wire tangle
    for k in range(6):
        xx = side * (FRONT + 3 + k * 5.5)
        lantern = obj_box("lantern", Matrix.Identity(4), (xx, ya + ALLEY_W / 2, 4.6 + 0.3 * math.sin(k)), (0.35, 0.35, 0.5),
                          glow(random.choice(["#ff5a3c", "#ffb347", "#ff3d6e"]), 6.0, "soft"), coll=PROPS, bevel=0.12)
        WIRES.append(((xx, ya + 0.2, 6.0), (xx, ya + ALLEY_W - 0.2, 6.0), 0.5))

def alley_frame(side, wall, ya, x, w):
    """Local frame for an alley building: facade toward the alley centreline."""
    if wall > 0:   # building on the +y side of the alley, facade faces -y
        rot = Matrix.Rotation(math.radians(90), 4, "Z")          # local +x -> world +y, local +y -> world -x
        if side > 0:
            return Matrix.Translation((x + w, ya + ALLEY_W, 0)) @ rot
        return Matrix.Translation((-x, ya + ALLEY_W, 0)) @ rot
    rot = Matrix.Rotation(math.radians(-90), 4, "Z")             # local +x -> world -y, local +y -> world +x
    if side > 0:
        return Matrix.Translation((x, ya, 0)) @ rot
    return Matrix.Translation((-x - w, ya, 0)) @ rot

WIRES = []

def ground():
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 60, 0)); g = bpy.context.object; g.name = "road"
    g.scale = (220, 420, 1); bpy.ops.object.transform_apply(scale=True); g.data.materials.append(ASPH)
    for c in g.users_collection: c.objects.unlink(g)
    CITY.objects.link(g)
    for side in (-1, 1):
        y0 = STREET_Y[0]
        cuts = sorted(ALLEYS[side]) + [STREET_Y[1]]
        for a in cuts:
            y1 = a if a != STREET_Y[1] else a
            if y1 - y0 > 0.5:
                obj_box("walk", Matrix.Identity(4), (side * (ROAD_HALF + WALK / 2), (y0 + y1) / 2, 0.075), (WALK, y1 - y0, 0.15), PAVE)
                B("curb", CURB).box(Matrix.Identity(4), (side * (ROAD_HALF + 0.08), (y0 + y1) / 2, 0.08), (0.18, y1 - y0, 0.17))
            y0 = a + ALLEY_W
    # paint: centre line, edge lines, crosswalk, stop line, arrows
    for y in range(-12, 150, 6):
        B("paint", PAINT).box(Matrix.Identity(4), (0, y, 0.003), (0.14, 3.0, 0.005))
    for i in range(8):
        B("paint", PAINT).box(Matrix.Identity(4), (-3.85 + i * 1.1, CROSS_Y, 0.003), (0.55, 3.4, 0.005))
    B("paint", PAINT).box(Matrix.Identity(4), (2.3, CROSS_Y - 2.4, 0.003), (4.4, 0.3, 0.005))
    # manholes + steam
    for (x, y) in ((1.2, 12), (-2.0, 37), (1.6, 58)):
        B("manhole", METAL).cyl(Matrix.Identity(4), (x, y, 0.006), 0.35, 0.012, 24)
    for (x, y) in ((1.2, 12), (-2.0, 37)):
        steam(x, y)

def steam(x, y):
    m = bpy.data.materials.new("steam"); g = G(m)
    tc = g.n("ShaderNodeTexCoord"); nz = g.n("ShaderNodeTexNoise", Scale=3.0, Detail=6.0, _noise_dimensions="4D")
    mp = g.n("ShaderNodeMapping"); g.ln(tc.outputs["Generated"], mp.inputs[0]); g.ln(mp.outputs[0], nz.inputs["Vector"])
    drive(nz.inputs["W"], "frame/20"); drive(mp.inputs["Location"], "-frame*0.012", index=2)
    so = g.n("ShaderNodeSeparateXYZ"); g.ln(tc.outputs["Generated"], so.inputs[0])
    edge = g.m("MULTIPLY", g.m("SINE", g.m("MULTIPLY", so.outputs["X"], math.pi)), g.m("SUBTRACT", 1.0, so.outputs["Z"]))
    a = g.m("MULTIPLY", g.m("MULTIPLY", g.m("POWER", nz.outputs["Fac"], 3.0), edge), 1.4, clamp=True)
    e = g.n("ShaderNodeEmission", Strength=0.35); e.inputs["Color"].default_value = lin("#dfe8f0")
    t = g.n("ShaderNodeBsdfTransparent"); mx = g.n("ShaderNodeMixShader")
    g.ln(a, mx.inputs[0]); g.ln(t.outputs[0], mx.inputs[1]); g.ln(e.outputs[0], mx.inputs[2]); g.ln(mx.outputs[0], g.out.inputs[0])
    for k, rz in enumerate((0, 60, 120)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, y, 1.3), rotation=(math.radians(90), 0, math.radians(rz)))
        p = bpy.context.object; p.scale = (1.2, 2.6, 1); p.data.materials.append(m); p.visible_shadow = False
        for c in p.users_collection: c.objects.unlink(p)
        FX.objects.link(p)

# ======================================================================= street furniture
def poles_and_wires():
    poles = []
    for side in (-1, 1):
        for y in range(-8, 146, 17):
            if any(abs(y - a - ALLEY_W / 2) < 4 for a in ALLEYS[side]): continue
            x = side * (ROAD_HALF + 0.45)
            B("poles", principled("pole_conc", "#7c7d7b", 0.6)).cyl(Matrix.Identity(4), (x, y, 5.0), 0.16, 10.0, 12)
            B("poles", principled("pole_conc", "#7c7d7b", 0.6)).box(Matrix.Identity(4), (x, y, 9.1), (1.6, 0.1, 0.1))
            for dx in (-0.6, 0.0, 0.6):
                B("insul", principled("insul", "#4d5a52", 0.3)).cyl(Matrix.Identity(4), (x + dx, y, 9.25), 0.04, 0.16, 8)
            B("transformer", principled("transformer", "#6d7376", 0.5, 0.5)).cyl(Matrix.Identity(4), (x - side * 0.35, y, 7.4), 0.25, 0.9, 12) if y % 34 == 9 else None
            # street lamp arm + head + light
            B("poles", principled("pole_conc", "#7c7d7b", 0.6)).box(Matrix.Identity(4), (x - side * 1.1, y, 7.8), (2.2, 0.08, 0.08))
            obj_box("lamp", Matrix.Identity(4), (x - side * 2.1, y, 7.72), (0.6, 0.25, 0.08), glow("#eef6ff", 30), coll=PROPS)
            spot(Matrix.Identity(4), (x - side * 2.1, y, 7.6), 700, "#dcecff", 85, 0.6)
            poles.append((x, y, side))
    # wires: along each side between poles (3 lines) and a few across the street
    for side in (-1, 1):
        ps = sorted([p for p in poles if p[2] == side], key=lambda p: p[1])
        for a, b in zip(ps, ps[1:]):
            for dx, z, sag in ((-0.6, 9.2, 0.6), (0.0, 9.2, 0.7), (0.6, 9.2, 0.55), (0.0, 7.0, 0.4)):
                WIRES.append(((a[0] + dx, a[1], z), (b[0] + dx, b[1], z), sag))
            if random.random() < 0.5:    # service drop to a building
                WIRES.append(((a[0], a[1], 8.4), (side * (FRONT + 0.2), a[1] + random.uniform(-3, 3), random.uniform(6, 9)), 0.3))
    for y in (-8, 26, 60, 94, 128):
        WIRES.append(((-ROAD_HALF - 0.45, y, 9.2), (ROAD_HALF + 0.45, y + 2, 9.2), 0.9))
        WIRES.append(((-ROAD_HALF - 0.45, y, 7.0), (ROAD_HALF + 0.45, y - 1, 7.4), 0.7))

def build_wires():
    cu = bpy.data.curves.new("wires", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.012; cu.bevel_resolution = 1
    for a, b, sag in WIRES:
        a, b = Vector(a), Vector(b); sp = cu.splines.new("POLY"); n = 16; sp.points.add(n - 1)
        for i in range(n):
            t = i / (n - 1); p = a.lerp(b, t); p.z -= sag * 4 * t * (1 - t)
            sp.points[i].co = (p.x, p.y, p.z, 1)
    ob = bpy.data.objects.new("wires", cu); PROPS.objects.link(ob); cu.materials.append(WIRE)

def traffic_light(x, y, side):
    M = Matrix.Identity(4)
    B("poles", METAL).cyl(M, (x, y, 2.6), 0.09, 5.2, 10)
    B("poles", METAL).box(M, (x - side * 1.8, y, 5.1), (3.6, 0.1, 0.1))
    B("tl_box", METAL).box(M, (x - side * 3.2, y, 4.75), (0.36, 0.3, 1.0))
    red = glow("#ff2a1a", 18.0, name=f"tl_red{x}"); grn = glow("#22ff9a", 18.0, name=f"tl_grn{x}")
    drive(red.node_tree.nodes["Emission"].inputs["Strength"], "18*min(1,max(0,sin(frame*0.035)*40))")
    drive(grn.node_tree.nodes["Emission"].inputs["Strength"], "18*min(1,max(0,-sin(frame*0.035)*40))")
    obj_box("tl_r", M, (x - side * 3.2, y - 0.16, 5.05), (0.22, 0.02, 0.22), red, PROPS)
    obj_box("tl_g", M, (x - side * 3.2, y - 0.16, 4.45), (0.22, 0.02, 0.22), grn, PROPS)
    # pedestrian signal
    B("tl_box", METAL).box(M, (x, y - 0.2, 2.9), (0.3, 0.2, 0.6))
    obj_box("ped", M, (x, y - 0.31, 3.0), (0.2, 0.02, 0.2), grn, PROPS)

def car(M, colour, moving=False, name="car"):
    """Simple hatch/sedan: rounded body, glass cabin, wheels, emissive lights. Local +y = forward."""
    paint = principled(f"paint_{colour}", colour, 0.18, 0.6, 0.8)
    parts = []
    body = obj_box(name, M, (0, 0, 0.62), (1.78, 4.35, 0.62), paint, PROPS, bevel=0.14); parts.append(body)
    cab = obj_box(name + "_cab", M, (0, -0.25, 1.17), (1.56, 2.3, 0.56), GLASS, PROPS, bevel=0.16); parts.append(cab)
    roof = obj_box(name + "_roof", M, (0, -0.3, 1.47), (1.5, 1.9, 0.06), paint, PROPS, bevel=0.03); parts.append(roof)
    for sx in (-0.86, 0.86):
        for sy in (-1.35, 1.35):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.33, depth=0.24, rotation=(0, math.radians(90), 0))
            wh = bpy.context.object; wh.matrix_world = M @ Matrix.Translation((sx, sy, 0.33)) @ Matrix.Rotation(math.radians(90), 4, "Y")
            wh.data.materials.append(principled("tyre", "#0d0d0e", 0.7))
            for c in wh.users_collection: c.objects.unlink(wh)
            PROPS.objects.link(wh); parts.append(wh)
    for sx in (-0.62, 0.62):
        parts.append(obj_box(name + "_hl", M, (sx, 2.17, 0.72), (0.38, 0.04, 0.12), glow("#f4f8ff", 12 if moving else 0.6), PROPS))
        parts.append(obj_box(name + "_tl", M, (sx, -2.17, 0.78), (0.4, 0.04, 0.1), glow("#ff1a2a", 6 if moving else 1.5), PROPS))
    if moving:
        sp = spot(M, (0, 2.3, 0.75), 900, "#eaf2ff", 50, 0.4); sp.matrix_world = M @ Matrix.Translation((0, 2.3, 0.75)) @ Matrix.Rotation(math.radians(-85), 4, "X")
        parts.append(sp)
    return parts

def street_props():
    M = Matrix.Identity(4)
    traffic_light(ROAD_HALF + 0.4, CROSS_Y - 2.2, 1); traffic_light(-ROAD_HALF - 0.4, CROSS_Y + 2.2, -1)
    # parked cars along the curbs
    for (x, y, rz, c) in ((3.3, 32, 0, "#d6d8da"), (3.3, 38.5, 0, "#1d2a3a"), (-3.3, 18, 180, "#7a1d22"),
                          (3.3, 70, 0, "#2b2d30"), (-3.3, 84, 180, "#c8c3b5"), (3.3, 104, 0, "#30465c")):
        car(Matrix.Translation((x, y, 0)) @ Matrix.Rotation(math.radians(rz), 4, "Z"), c)
    # vending machines, bins, bollards, planters with trees, scooters
    for side in (-1, 1):
        for y in range(2, 140, 9):
            r = random.random(); x = side * (FRONT - 0.5)
            if r < 0.18:
                obj_box("vend", M, (x, y, 0.95), (0.8, 0.75, 1.8), METAL_L, PROPS, bevel=0.03)
                obj_box("vend_face", M, (x - side * 0.41, y, 1.1), (0.02, 0.62, 1.2), glow(random.choice(["#d8f0ff", "#ffe8c8"]), 3.0), PROPS)
            elif r < 0.35:
                B("bins", principled("bin", random.choice(["#2f6b45", "#3a3d41"]), 0.5)).box(M, (x, y, 0.55), (0.6, 0.6, 0.95))
                for k in range(random.randint(1, 3)):
                    B("bags", principled("trashbag", "#141416", 0.25)).box(M, (x + random.uniform(-0.3, 0.3), y + 0.7 + k * 0.4, 0.35), (0.5, 0.45, 0.5))
            elif r < 0.5:
                xb = side * (ROAD_HALF + 0.9)
                B("planter", CONC).box(M, (xb, y, 0.4), (1.0, 1.6, 0.8))
                B("trunk", principled("trunk", "#3a2b20", 0.8)).cyl(M, (xb, y, 2.0), 0.08, 3.2, 8)
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.2, location=(xb, y, 4.0))
                t = bpy.context.object; t.scale = (1, 1, 1.25); t.data.materials.append(grimy("leaves", "#1e3a26", "#0f1f14", 0.7, 6.0, 0.8))
                d = t.modifiers.new("d", "DISPLACE"); tex = bpy.data.textures.new("leafn", "CLOUDS"); tex.noise_scale = 0.4; d.texture = tex; d.strength = 0.5
                for c in t.users_collection: c.objects.unlink(t)
                PROPS.objects.link(t)
            elif r < 0.62:     # delivery scooter
                xs = side * (ROAD_HALF + 1.1)
                B("scooter", principled("scooter", random.choice(["#b8202a", "#e6e2d8", "#1f4f8a"]), 0.3, 0.3)).box(M, (xs, y, 0.6), (0.4, 1.4, 0.45))
                B("scooter_box", principled("scooter_box", "#d23a26", 0.5)).box(M, (xs, y - 0.5, 1.05), (0.45, 0.45, 0.4))
                B("tyres", principled("tyre", "#0d0d0e", 0.7)).cyl(M, (xs, y + 0.55, 0.22), 0.22, 0.12, 14, Matrix.Rotation(math.radians(90), 4, "Y"))
                B("tyres", principled("tyre", "#0d0d0e", 0.7)).cyl(M, (xs, y - 0.55, 0.22), 0.22, 0.12, 14, Matrix.Rotation(math.radians(90), 4, "Y"))
        for y in range(-10, 146, 4):
            if random.random() < 0.4:
                B("bollard", METAL).cyl(M, (side * (ROAD_HALF + 0.3), y, 0.45), 0.07, 0.9, 8)

# ======================================================================= distant city, hill and tower
def skyline():
    for i in range(70):
        x = random.choice([-1, 1]) * random.uniform(22, 220); y = random.uniform(170, 520)
        if abs(x) < 30 and y < 260: continue
        h = random.uniform(35, 160) * (1.4 if random.random() < 0.15 else 1.0)
        w = random.uniform(14, 34); d = random.uniform(14, 34)
        ob = obj_box("tower", Matrix.Identity(4), (x, y, h / 2), (w, d, h), facade(random.choice(["glass", "dark", "concrete", "glass"])))
        if random.random() < 0.3:
            obj_box("crown", Matrix.Identity(4), (x, y, h + 1.5), (w * 0.8, d * 0.8, 3.0), glow(random.choice(["#9fd8ff", "#ffffff", "#ff7ab8"]), 3.0))
    # an original twisted landmark tower
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-40, 330, 120)); t = bpy.context.object
    t.scale = (26, 26, 240); bpy.ops.object.transform_apply(scale=True)
    sd = t.modifiers.new("taper", "SIMPLE_DEFORM"); sd.deform_method = "TAPER"; sd.factor = -0.6
    tw = t.modifiers.new("twist", "SIMPLE_DEFORM"); tw.deform_method = "TWIST"; tw.angle = math.radians(80)
    sub = t.modifiers.new("cut", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = 4; t.modifiers.move(2, 0)
    t.data.materials.append(facade("glass"))
    for c in t.users_collection: c.objects.unlink(t)
    CITY.objects.link(t)
    obj_box("spire_tip", Matrix.Identity(4), (-40, 330, 245), (0.8, 0.8, 10), glow("#ff3030", 30, "soft"))
    # hill with a broadcast tower far away
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(60, 1100, -60)); hill = bpy.context.object
    hill.scale = (420, 300, 210); hill.data.materials.append(hill_mat())
    d = hill.modifiers.new("d", "DISPLACE"); tex = bpy.data.textures.new("hilln", "CLOUDS"); tex.noise_scale = 0.4; d.texture = tex; d.strength = 0.15
    for c in hill.users_collection: c.objects.unlink(hill)
    CITY.objects.link(hill)
    B("btower", principled("btower", "#d8d8d4", 0.4, 0.3)).cyl(Matrix.Identity(4), (60, 1100, 190), 4, 120, 16)
    obj_box("btower_ring", Matrix.Identity(4), (60, 1100, 235), (22, 22, 9), glow("#fff3d6", 4.0))
    B("btower", principled("btower", "#d8d8d4", 0.4, 0.3)).cyl(Matrix.Identity(4), (60, 1100, 275), 1.2, 70, 10)
    obj_box("btower_tip", Matrix.Identity(4), (60, 1100, 311), (1.5, 1.5, 2), glow("#ff2828", 40, "soft"))

def hill_mat():
    m = bpy.data.materials.new("hill"); g = G(m); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord"); vor = g.n("ShaderNodeTexVoronoi", Scale=220.0); g.ln(tc.outputs["Object"], vor.inputs["Vector"])
    lights = g.m("LESS_THAN", vor.outputs["Distance"], 0.06)
    so = g.n("ShaderNodeSeparateXYZ"); g.ln(tc.outputs["Object"], so.inputs[0])
    lights = g.m("MULTIPLY", lights, g.m("LESS_THAN", so.outputs["Z"], 0.35))       # city lights on the lower slopes
    b.inputs["Base Color"].default_value = lin("#0b1210"); b.inputs["Roughness"].default_value = 0.9
    g.ln(g.mix(lights, lin("#000000"), lin("#ffcf8a")), b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 6.0
    return m

# ======================================================================= rain & fog
def rain(cx, cy, w, dep, H=9.0, T=24, n=14000):
    m = bpy.data.materials.new("rain"); g = G(m)
    e = g.n("ShaderNodeEmission", Strength=1.5); e.inputs["Color"].default_value = lin("#e3f2ff")
    t = g.n("ShaderNodeBsdfTransparent"); mx = g.n("ShaderNodeMixShader", Fac=0.1)
    g.ln(t.outputs[0], mx.inputs[1]); g.ln(e.outputs[0], mx.inputs[2]); g.ln(mx.outputs[0], g.out.inputs[0])
    bm = bmesh.new()
    pts = [(random.uniform(cx - w / 2, cx + w / 2), random.uniform(cy - dep / 2, cy + dep / 2), random.uniform(0, H)) for _ in range(n)]
    for x, y, z in pts:
        for dz in (0.0, H):                   # tiled twice so the loop is seamless
            L_ = random.uniform(0.3, 0.6); W = 0.0045; lean = 0.08
            vs = [bm.verts.new(p) for p in ((x - W, y, z + dz), (x + W, y, z + dz), (x + W + lean * L_, y, z + dz + L_), (x - W + lean * L_, y, z + dz + L_))]
            bm.faces.new(vs)
    me = bpy.data.meshes.new("rain"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("rain", me); FX.objects.link(ob); me.materials.append(m); ob.visible_shadow = False
    prefs.keyframe_new_interpolation_type = "LINEAR"
    for k in range(0, FRAMES + T, T):           # fall H metres every T frames, then wrap
        ob.location = (0, 0, 0); ob.keyframe_insert("location", index=2, frame=k)
        ob.location = (0, 0, -H * (T - 1) / T); ob.keyframe_insert("location", index=2, frame=k + T - 1)
    ch.set_interp(ob, "LINEAR")
    return ob

def fog():
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 450, 120)); f = bpy.context.object; f.name = "fog"
    f.scale = (900, 1300, 260)
    m = bpy.data.materials.new("fog"); g = G(m)
    v = g.n("ShaderNodeVolumePrincipled", Density=0.0028, Anisotropy=0.6); v.inputs["Color"].default_value = lin("#c9d6e6")
    g.ln(v.outputs[0], g.out.inputs["Volume"]); f.data.materials.append(m)
    for c in f.users_collection: c.objects.unlink(f)
    FX.objects.link(f)

def world():
    w = bpy.data.worlds.new("night"); scn.world = w; w.use_nodes = True; g = G.__new__(G)
    g.nt = w.node_tree; g.N = g.nt.nodes; g.L = g.nt.links; g.N.clear()
    out = g.N.new("ShaderNodeOutputWorld"); bg = g.N.new("ShaderNodeBackground")
    tc = g.N.new("ShaderNodeTexCoord"); so = g.N.new("ShaderNodeSeparateXYZ"); g.L.new(tc.outputs["Generated"], so.inputs[0])
    cr = g.N.new("ShaderNodeValToRGB"); g.L.new(so.outputs["Z"], cr.inputs[0])
    e = cr.color_ramp.elements; e[0].position = 0.0; e[0].color = lin("#3a2a44"); e[1].position = 0.3; e[1].color = lin("#05070d")
    mid = e.new(0.06); mid.color = lin("#1b1f36")                         # light-polluted horizon -> deep night
    g.L.new(cr.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.8
    g.L.new(bg.outputs[0], out.inputs["Surface"])

# ======================================================================= people
HAIR = ["#16181d", "#2a1d16", "#3b2a20", "#0f1012", "#5a4030", "#22201f"]
SKIN = [("#e8c2a2", "#a9775b"), ("#f0cfb3", "#b48466"), ("#d9a982", "#9a6a4a"), ("#c58f6a", "#86583d"), ("#f3d6bf", "#bf9274")]
COATS = [("#2f343c", "#11141a"), ("#b59a74", "#6e5b42"), ("#1f2a3d", "#0c1220"), ("#5a5f66", "#2b2e33"), ("#6b2a2e", "#331314"),
         ("#c9c3b6", "#7f7a70"), ("#1c1c1e", "#08080a"), ("#3d4a3a", "#1b2219")]
TOPS = [("#cfc4b2", "#7d7466"), ("#e9e6df", "#9a978f"), ("#26292f", "#0e1013"), ("#8a9bb0", "#4b5868"), ("#a14b3c", "#5a261d"), ("#d8b65a", "#8a7130")]
LEGS = [("#24272d", "#0c0e12"), ("#2f3f5a", "#141c2b"), ("#4a4a4d", "#1d1d1f"), ("#c6bfae", "#7d7768"), ("#141416", "#060607")]
UMB = ["#1d2230", "#121214", "#6b1d24", "#24405e", "#3c3f44", "#c9a227"]

_LOOKS = random.Random(1234)
# women passers-by, from the user's references: oversized blazers, wrap suits, cropped blazer + midi skirt, long coats
WOMEN = [dict(coat=("#ece3d2", "#a49a88"), hem=0.66, open_skirt=True, open_coat=True, top=("#c09f74", "#7a6345"), legs="skirt",
              leg_col=("#7a5a3c", "#45321f"), skirt_hem=0.56, tights="#e9c9b2"),
         dict(coat=("#9b8468", "#5e4d3a"), hem=0.78, open_skirt=False, top=("#9b8468", "#5e4d3a"), legs="trousers",
              leg_col=("#9b8468", "#5e4d3a"), mask="#111114"),
         dict(coat=("#8f9a82", "#566050"), hem=0.88, open_skirt=False, top=("#8f9a82", "#566050"), legs="skirt",
              leg_col=("#8f9a82", "#566050"), skirt_hem=0.3, socks="#141416", shoes=("#f2f2f0", "#141416"), sneakers=True,
              mask="#f4f4f2"),
         dict(coat=("#d9a51b", "#8a6608"), hem=0.3, open_skirt=True, open_coat=True, top=("#a29a90", "#5f5a53"), turtleneck=True,
              legs="trousers", leg_col=("#c4b9a6", "#7c7364")),
         dict(coat=("#2a2a2e", "#0c0c0e"), hem=0.36, open_skirt=True, top=("#e9e6df", "#9a978f"), turtleneck=True,
              legs="skirt", leg_col=("#24272d", "#0c0e12"), skirt_hem=0.5, tights="#23222a")]
def extra_style():
    sex = random.choice(["m", "m", "f", "f", "m_heavy"])
    st = dict(body=sex, skin=random.choice(SKIN), hair_col=random.choice(HAIR), locks=False,
              top=random.choice(TOPS), legs="trousers", leg_col=random.choice(LEGS),
              shoes=random.choice([("#1b1a1c", "#3a2a22"), ("#ecebe7", "#d9d7d0"), ("#2a2421", "#1a1512")]),
              brows=random.choice(["#1a1714", "#2b211b"]), iris=random.choice(["#7a5236", "#5e4030", "#6a4a34"]))
    st["sneakers"] = st["shoes"][0] == "#ecebe7"
    st["height"] = random.uniform(1.58, 1.72) if sex == "f" else random.uniform(1.68, 1.86)
    st["hair"] = random.choice(["bob", "long", "long"]) if sex == "f" else random.choice(["short", "short", "buzz"])
    st["hair_len"] = _LOOKS.uniform(0.22, 0.38)        # separate RNG: the seeded city layout stays the same
    st["manhwa_head"] = True        # every passer-by gets a face of their own
    st["face"] = _LOOKS.choice(["soft_f", "sharp_f"]) if sex == "f" else _LOOKS.choice(["round", "long", "diamond", "square", "boy"])
    if sex == "f":
        st["face"] = "kstar_f"; st["jaw_v"] = 0.3
        st["lips"] = _LOOKS.choice(["#c25a62", "#d27a7a", "#b84a55", "#cf7468"])
        st["_women_look"] = _LOOKS.choice(WOMEN)
        if _LOOKS.random() < 0.6:
            st["bag"] = _LOOKS.choice([("#8a5a32", "#4e321b"), ("#1c1c1e", "#08080a"), ("#b88a5a", "#6e5032")])
    r = random.random()
    st["coat"] = random.choice(COATS) if r < 0.75 else None
    st["hem"] = random.choice([0.36, 0.5, 0.72, 0.8])
    st["open_skirt"] = True
    st["turtleneck"] = random.random() < 0.4
    if sex == "f" and random.random() < 0.45:
        st["legs"] = "skirt"; st["leg_col"] = random.choice(LEGS + [("#7a2d3a", "#3a141b")])
        st["skirt_hem"] = random.uniform(0.42, 0.56); st["tights"] = random.choice(["#23222a", "#3a2f2a"])
    if st.get("_women_look"):
        look = st.pop("_women_look")
        for k in ("legs", "skirt_hem", "tights", "socks", "mask", "sneakers"):
            st.pop(k, None)
        st["legs"] = "trousers"; st.update(look); st["turtleneck"] = look.get("turtleneck", False)
    return st

def crowd(with_hero=True, avoid=()):
    actors = []
    if with_hero:   # hero walks down the middle of the wet street toward camera
        hero, _ = ch.build(PEOPLE_C, (0.6, 34, 0), ch.HERO, pose_mode="walk")
        hero.name = "HERO"
        ch.animate_walk(hero, (0.6, 34, 0), 0.0, -40, FRAMES, phase=0.0, cycle=34)
        actors.append(hero)
    for i in range(PEOPLE):
        st = extra_style(); st["subsurf"] = 0 if os.environ.get("LIGHT_EXTRAS") else 1
        side = random.choice([-1, 1])
        y = random.uniform(-2, 90); x = side * random.uniform(ROAD_HALF + 0.8, FRONT - 0.9)
        while any(abs(x - ax) < 2.5 and abs(y - ay) < 3.0 for ax, ay in avoid):
            y = random.uniform(-2, 90)
        r = random.random()
        if r < 0.82:   # walkers
            heading = random.choice([0.0, 180.0]); prop = "umbrella" if random.random() < 0.55 else None
            arm, objs = ch.build(PEOPLE_C, (x, y, 0.15), st, pose_mode="walk", heading=heading)
            ch.animate_walk(arm, (x, y, 0.15), heading, -40, FRAMES, phase=random.random(), prop=prop,
                            cycle=random.choice([30, 32, 34, 36]))
            scn.frame_set(1)
            if prop:
                ch.add_umbrella(arm, PEOPLE_C, random.choice(UMB), clear=random.random() < 0.2)
        else:          # standing: on the phone outside a shop, or waiting at the crossing
            heading = random.choice([90.0, -90.0, 0.0, 180.0])
            y = CROSS_Y + random.uniform(-3, 3) if random.random() < 0.5 else y
            arm, objs = ch.build(PEOPLE_C, (x, y, 0.15), st, pose_mode="phone", heading=heading)
            ch.add_phone(arm, PEOPLE_C)
        actors.append(arm)
    prefs.keyframe_new_interpolation_type = "BEZIER"
    return actors

# ======================================================================= assemble
def build_scene(with_hero=True, avoid=(), rain_box=(0, 22, 18, 46)):
    """Build the whole city. People first: their pose solves stay cheap in an empty scene."""
    t0 = __import__("time").time()
    actors = crowd(with_hero, avoid)
    print("people", round(__import__("time").time() - t0, 1), "s")
    ground()
    street_side(-1); street_side(1)
    for side, ys in ALLEYS.items():
        for ya in ys:
            alley(side, ya)
    poles_and_wires(); build_wires(); street_props(); skyline()
    for name, b in list(_B.items()):
        b.done(CITY if name in ("ledges", "fins", "parapet", "hut", "tank", "pipes", "ac", "ac_grille", "rail", "clutter", "mullion", "fascia",
                                "curb", "paint", "manhole") else PROPS)
    _B.clear()
    prefs.keyframe_new_interpolation_type = "LINEAR"      # moving traffic: one car toward camera, one away
    for (x, y0, y1, rz, col) in ((-2.2, 120, 120 - 13 * FRAMES / 30 * 1.0, 180, "#e5e3dd"), (2.3, 72, 72 + 11 * FRAMES / 30, 0, "#1a2c44")):
        root = bpy.data.objects.new("traffic", None); PROPS.objects.link(root)
        for p in car(Matrix.Rotation(math.radians(rz), 4, "Z"), col, moving=True, name="mcar"):
            mw = p.matrix_world.copy(); p.parent = root; p.matrix_world = mw
        root.location = (x, y0, 0); root.keyframe_insert("location", frame=1)
        root.location = (x, y1, 0); root.keyframe_insert("location", frame=FRAMES)
        ch.set_interp(root, "LINEAR")
    rain(*rain_box)
    fog(); world()
    print("objects", len(bpy.data.objects), "build", round(__import__("time").time() - t0, 1), "s")
    return actors

def render_settings(scale, samples):
    scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"
    scn.cycles.samples = samples; scn.cycles.use_adaptive_sampling = True; scn.cycles.adaptive_threshold = 0.03
    scn.cycles.use_denoising = True; scn.cycles.denoiser = "OPENIMAGEDENOISE"
    scn.cycles.max_bounces = 4; scn.cycles.diffuse_bounces = 2; scn.cycles.glossy_bounces = 3
    scn.cycles.transparent_max_bounces = 12; scn.cycles.volume_bounces = 0; scn.cycles.volume_step_rate = 8.0
    scn.cycles.sample_clamp_indirect = 5.0; scn.cycles.light_sampling_threshold = 0.02
    scn.render.resolution_x, scn.render.resolution_y = 1080, 1920; scn.render.resolution_percentage = scale
    scn.view_settings.view_transform = "AgX"; scn.view_settings.look = "AgX - Punchy"; scn.view_settings.exposure = -0.4
    scn.render.use_persistent_data = True      # keep the static city in memory between frames

def make_camera():
    cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05; cd.clip_end = 3000
    cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam
    tgt = bpy.data.objects.new("cam_t", None); scn.collection.objects.link(tgt)
    c = cam.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    cd.dof.use_dof = True; cd.dof.aperture_fstop = 2.8; cd.dof.aperture_blades = 7
    return cam, tgt, cd

# ======================================================================= camera, lines, render (CLI)
if __name__ == "__main__":
    actors = build_scene()
    scn.render.use_freestyle = bool(os.environ.get("FREESTYLE")); scn.render.line_thickness_mode = "ABSOLUTE"; scn.render.line_thickness = 1.0 * SCALE / 50
    vl = scn.view_layers[0]; fs = vl.freestyle_settings
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new("people")
    ls.select_by_collection = True; ls.collection = PEOPLE_C
    ls.select_silhouette = True; ls.select_border = True; ls.select_crease = False; ls.select_material_boundary = True
    ls.linestyle = ls.linestyle or bpy.data.linestyles.new("ink"); ls.linestyle.color = (0.03, 0.035, 0.05); ls.linestyle.thickness = 1.2

    cam, tgt, cd = make_camera()
    hero = actors[0]
    SHOTS = {
        "street": dict(loc=(1.8, -6.0, 1.7), tgt=(0.0, 40, 5.5), lens=22, f=8, focus=(0, 26, 1.5), frame=1),
        "hero":   dict(loc=(1.2, 22.5, 1.25), tgt=(0.4, 31, 1.75), lens=35, f=2.2, focus="HERO", frame=1),
        "alley":  dict(loc=(-3.2, 32.5, 1.6), tgt=(-40, 32.5, 4.5), lens=24, f=5.6, focus=(-20, 32.5, 2), frame=1),
        "aerial": dict(loc=(0.8, -16.0, 24.0), tgt=(0.0, 45, 3.0), lens=24, f=11, focus=(0, 40, 0), frame=1),
    }
    if SHOT == "clip":     # camera dollies backward in front of the hero
        prefs.keyframe_new_interpolation_type = "LINEAR"
        cd.lens = 32; cd.dof.focus_object = hero; cd.dof.aperture_fstop = 2.8
        for f in (1, FRAMES):
            scn.frame_set(f); hp = hero.matrix_world.translation
            cam.location = (hp.x + 0.9, hp.y - 6.5, 1.45); cam.keyframe_insert("location", frame=f)
            tgt.location = (hp.x - 0.2, hp.y + 4, 2.4); tgt.keyframe_insert("location", frame=f)
    else:
        S = SHOTS[SHOT]; scn.frame_set(S["frame"])
        cam.location = S["loc"]; tgt.location = S["tgt"]; cd.lens = S["lens"]; cd.dof.aperture_fstop = S["f"]
        if S["focus"] == "HERO":
            cd.dof.focus_object = hero
        else:
            fo = bpy.data.objects.new("focus", None); scn.collection.objects.link(fo); fo.location = S["focus"]; cd.dof.focus_object = fo

    render_settings(SCALE, SAMPLES)
    if os.environ.get("NORENDER"):
        print("built only"); sys.exit(0)
    if SHOT == "clip":
        scn.render.image_settings.file_format = "PNG"
        scn.render.filepath = os.path.join(OUT, "clip", "f")
        scn.render.use_overwrite = not os.environ.get("RESUME")      # RESUME=1 skips frames already on disk
        bpy.ops.render.render(animation=True)
        print("WROTE clip frames")
    else:
        scn.render.image_settings.file_format = "PNG"
        scn.render.filepath = os.path.join(OUT, f"city_{SHOT}_raw.png")
        bpy.ops.render.render(write_still=True)
        print("WROTE", scn.render.filepath)
