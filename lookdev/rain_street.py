"""Cinematic look-dev: cel-shaded (manhwa-style) character in a photoreal rainy street.

Run with the Blender 5 Python module (has OpenImageDenoise):
    /root/.venvs/bpy/bin/python lookdev/rain_street.py <shot> [scale%]
shots: hero | low
Everything is procedural (no downloaded assets). Scene units are metres.
The character is a STAND-IN mannequin to test the 2D-on-photoreal mix;
final characters are original designs (see STYLE.md).
"""
import bpy, bmesh, math, os, random, sys

SHOT = sys.argv[1] if len(sys.argv) > 1 else "hero"
SCALE = int(sys.argv[2]) if len(sys.argv) > 2 else 50
SAMPLES = int(os.environ.get("SAMPLES", 128))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
os.makedirs(OUT, exist_ok=True)
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
col = scn.collection

def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

# ---------- tiny node helpers ----------
class G:
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree; self.N = self.nt.nodes; self.L = self.nt.links
        self.N.clear()
        self.out = self.N.new("ShaderNodeOutputMaterial")
    def n(self, t, **kw):
        nd = self.N.new(t)
        for k, v in kw.items():
            if k.startswith("_"):
                setattr(nd, k[1:], v)
            else:
                nd.inputs[k].default_value = v
        return nd
    def ln(self, a, b):
        self.L.new(a, b)
    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", _operation=op, _use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.ln(v, m.inputs[i])
        return m.outputs[0]
    def mix(self, fac, a, b, rgba=False):
        m = self.n("ShaderNodeMix", _data_type="RGBA" if rgba else "FLOAT")
        ia, ib = (6, 7) if rgba else (2, 3)
        for slot, v in ((0, fac), (ia, a), (ib, b)):
            if isinstance(v, (int, float)) or (isinstance(v, tuple)):
                m.inputs[slot].default_value = v
            else:
                self.ln(v, m.inputs[slot])
        return m.outputs[2 if rgba else 0]
    def band(self, x, lo, hi):  # 1 where lo < x < hi
        return self.math("MULTIPLY", self.math("GREATER_THAN", x, lo), self.math("LESS_THAN", x, hi))

def box(name, size, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object; ob.name = name; ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(mat); return ob

# ---------- materials ----------
def asphalt():
    m = bpy.data.materials.new("asphalt"); g = G(m)
    b = g.n("ShaderNodeBsdfPrincipled"); g.ln(b.outputs[0], g.out.inputs[0])
    tc = g.n("ShaderNodeTexCoord")
    pud = g.n("ShaderNodeTexNoise", Scale=0.22, Detail=3.0, Roughness=0.6); g.ln(tc.outputs["Object"], pud.inputs["Vector"])
    ramp = g.n("ShaderNodeMapRange"); ramp.inputs[1].default_value = 0.47; ramp.inputs[2].default_value = 0.53
    g.ln(pud.outputs["Fac"], ramp.inputs[0]); M = ramp.outputs[0]          # 1 = puddle
    grain = g.n("ShaderNodeTexNoise", Scale=260.0, Detail=4.0); g.ln(tc.outputs["Object"], grain.inputs["Vector"])
    stain = g.n("ShaderNodeTexNoise", Scale=1.8, Detail=5.0); g.ln(tc.outputs["Object"], stain.inputs["Vector"])
    base = g.mix(stain.outputs["Fac"], lin("#16181b"), lin("#2a2c2f"), rgba=True)
    base = g.mix(g.math("MULTIPLY", grain.outputs["Fac"], 0.5), base, lin("#3a3c3e"), rgba=True)
    base = g.mix(M, base, lin("#0b0c0e"), rgba=True)
    g.ln(base, b.inputs["Base Color"])
    g.ln(g.mix(M, 0.55, 0.025), b.inputs["Roughness"])
    # aggregate bump outside puddles, rain ripples inside puddles
    vor = g.n("ShaderNodeTexVoronoi", Scale=9.0, _feature="F1"); g.ln(tc.outputs["Object"], vor.inputs["Vector"])
    rings = g.math("SINE", g.math("MULTIPLY", vor.outputs["Distance"], 60.0))
    rings = g.math("MULTIPLY", rings, g.math("LESS_THAN", vor.outputs["Distance"], 0.12))
    h = g.mix(M, g.math("MULTIPLY", grain.outputs["Fac"], 1.0), g.math("MULTIPLY", rings, 0.15))
    bump = g.n("ShaderNodeBump", Strength=0.35, Distance=0.002); g.ln(h, bump.inputs["Height"])
    g.ln(bump.outputs[0], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = 0.6
    return m

def concrete(hexc="#5b5f63", rough=0.35, name="concrete"):
    m = bpy.data.materials.new(name); g = G(m)
    b = g.n("ShaderNodeBsdfPrincipled"); g.ln(b.outputs[0], g.out.inputs[0])
    tc = g.n("ShaderNodeTexCoord"); nz = g.n("ShaderNodeTexNoise", Scale=3.0, Detail=8.0)
    g.ln(tc.outputs["Object"], nz.inputs["Vector"])
    g.ln(g.mix(nz.outputs["Fac"], lin(hexc), lin("#2b2e31"), rgba=True), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    bump = g.n("ShaderNodeBump", Strength=0.2); g.ln(nz.outputs["Fac"], bump.inputs["Height"]); g.ln(bump.outputs[0], b.inputs["Normal"])
    return m

def facade(side):
    """Building face in the YZ plane: concrete + window grid + random lit rooms + neon shopfront."""
    m = bpy.data.materials.new(f"facade{side}"); g = G(m)
    b = g.n("ShaderNodeBsdfPrincipled"); g.ln(b.outputs[0], g.out.inputs[0])
    geo = g.n("ShaderNodeNewGeometry"); sep = g.n("ShaderNodeSeparateXYZ"); g.ln(geo.outputs["Position"], sep.inputs[0])
    info = g.n("ShaderNodeObjectInfo")
    u = g.math("DIVIDE", sep.outputs["Y"], 2.6); v = g.math("DIVIDE", sep.outputs["Z"], 3.3)
    fu, fv = g.math("FRACT", u), g.math("FRACT", v)
    win = g.math("MULTIPLY", g.band(fu, 0.3, 0.7), g.band(fv, 0.35, 0.72))
    upper = g.math("GREATER_THAN", sep.outputs["Z"], 4.2)
    win = g.math("MULTIPLY", win, upper)
    # random per window cell
    cell = g.n("ShaderNodeCombineXYZ"); g.ln(g.math("FLOOR", u), cell.inputs[0]); g.ln(g.math("FLOOR", v), cell.inputs[1])
    g.ln(info.outputs["Random"], cell.inputs[2])
    wn = g.n("ShaderNodeTexWhiteNoise", _noise_dimensions="3D"); g.ln(cell.outputs[0], wn.inputs["Vector"])
    sepc = g.n("ShaderNodeSeparateColor"); g.ln(wn.outputs["Color"], sepc.inputs[0])
    lit = g.math("MULTIPLY", win, g.math("GREATER_THAN", sepc.outputs[0], 0.78))
    lit_col = g.mix(sepc.outputs[1], lin("#ffcf9a"), lin("#bfe6ff"), rgba=True)
    lit_col = g.mix(g.math("GREATER_THAN", sepc.outputs[2], 0.85), lit_col, lin("#ff4fa3"), rgba=True)
    # shopfront band 0.4..3.6 m, neon colour per building
    shop = g.band(sep.outputs["Z"], 0.4, 3.4)
    shop_col = g.n("ShaderNodeValToRGB"); g.ln(info.outputs["Random"], shop_col.inputs[0])
    cr = shop_col.color_ramp; cr.interpolation = "CONSTANT"
    cr.elements[0].color = lin("#18e0ff"); cr.elements[1].position = 0.4; cr.elements[1].color = lin("#ff3d8b")
    e = cr.elements.new(0.75); e.color = lin("#f5f1e8")
    shopglass = g.math("MULTIPLY", shop, g.band(fu, 0.06, 0.94))
    # concrete base
    tc = g.n("ShaderNodeTexCoord"); nz = g.n("ShaderNodeTexNoise", Scale=1.2, Detail=8.0); g.ln(tc.outputs["Object"], nz.inputs["Vector"])
    conc = g.mix(nz.outputs["Fac"], lin("#3b3f44"), lin("#1c1f23"), rgba=True)
    glass = g.math("MAXIMUM", win, shopglass)
    g.ln(g.mix(glass, conc, lin("#05070a"), rgba=True), b.inputs["Base Color"])
    g.ln(g.mix(glass, 0.75, 0.04), b.inputs["Roughness"])
    emis = g.mix(lit, lin("#000000"), lit_col, rgba=True)
    emis = g.mix(shopglass, emis, shop_col.outputs["Color"], rgba=True)
    g.ln(emis, b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 4.0
    return m

def emissive(hexc, strength):
    m = bpy.data.materials.new(f"em_{hexc}"); g = G(m)
    e = g.n("ShaderNodeEmission", Strength=strength); e.inputs["Color"].default_value = lin(hexc)
    g.ln(e.outputs[0], g.out.inputs[0]); return m

def rain_mat():
    m = bpy.data.materials.new("rain"); g = G(m)
    e = g.n("ShaderNodeEmission", Strength=1.6); e.inputs["Color"].default_value = lin("#dff3ff")
    t = g.n("ShaderNodeBsdfTransparent"); mx = g.n("ShaderNodeMixShader", Fac=0.14)
    g.ln(t.outputs[0], mx.inputs[1]); g.ln(e.outputs[0], mx.inputs[2]); g.ln(mx.outputs[0], g.out.inputs[0])
    return m

def fog_mat(density):
    m = bpy.data.materials.new("fog"); g = G(m)
    v = g.n("ShaderNodeVolumePrincipled", Density=density, Anisotropy=0.55)
    v.inputs["Color"].default_value = lin("#cfe3ee")
    g.ln(v.outputs[0], g.out.inputs["Volume"]); return m

def cel(hexc, shade="#000000", rim="#c9f6ff", light=(0.35, 0.8, 0.55)):
    """Manhwa cel shading that works in Cycles: flat 2-tone from a fixed key direction + cyan rim."""
    m = bpy.data.materials.new(f"cel_{hexc}"); g = G(m)
    geo = g.n("ShaderNodeNewGeometry")
    dot = g.n("ShaderNodeVectorMath", _operation="DOT_PRODUCT"); g.ln(geo.outputs["Normal"], dot.inputs[0])
    l = math.sqrt(sum(c * c for c in light)); dot.inputs[1].default_value = tuple(c / l for c in light)
    step = g.math("GREATER_THAN", dot.outputs["Value"], 0.05)
    shade_c = shade if shade != "#000000" else None
    lo = lin(shade_c) if shade_c else tuple(c * 0.42 for c in lin(hexc)[:3]) + (1.0,)
    col_ = g.mix(step, lo, lin(hexc), rgba=True)
    lw = g.n("ShaderNodeLayerWeight", Blend=0.3)
    rimv = g.math("GREATER_THAN", lw.outputs["Facing"], 0.55)
    col_ = g.mix(g.math("MULTIPLY", rimv, 0.85), col_, lin(rim), rgba=True)
    e = g.n("ShaderNodeEmission", Strength=1.0); g.ln(col_, e.inputs["Color"]); g.ln(e.outputs[0], g.out.inputs[0])
    return m

# ---------- street ----------
ASPH = asphalt()
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 40, 0)); road = bpy.context.object
road.scale = (60, 120, 1); bpy.ops.object.transform_apply(scale=True); road.data.materials.append(ASPH)
bpy.ops.object.modifier_add(type="SUBSURF"); road.modifiers[0].subdivision_type = "SIMPLE"; road.modifiers[0].levels = 2

# worn road paint: centre dashes + crosswalk just behind the character
def paint():
    m = bpy.data.materials.new("paint"); g = G(m)
    b = g.n("ShaderNodeBsdfPrincipled"); g.ln(b.outputs[0], g.out.inputs[0])
    tc = g.n("ShaderNodeTexCoord"); nz = g.n("ShaderNodeTexNoise", Scale=14.0, Detail=6.0); g.ln(tc.outputs["Object"], nz.inputs["Vector"])
    worn = g.math("GREATER_THAN", nz.outputs["Fac"], 0.42)
    g.ln(g.mix(worn, lin("#2a2c2f"), lin("#c9ccc8"), rgba=True), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    return m
PAINT = paint()
for yy in range(10, 90, 6):
    box("dash", (0.15, 3.0, 0.004), (0, yy, 0.002), PAINT)
for i in range(9):
    box("zebra", (0.55, 3.6, 0.004), (-4.4 + i * 1.1, CHAR_Y + 3.6, 0.002), PAINT)
for sx in (-1, 1):
    box("edge", (0.12, 120, 0.004), (sx * 4.85, 40, 0.002), PAINT)

CURB = concrete("#55595d", 0.18, "curb")
for sx in (-1, 1):
    box(f"walk{sx}", (3.0, 120, 0.16), (sx * 6.6, 40, 0.08), CURB)

for sx in (-1, 1):
    F = facade(sx)
    y = -6.0
    while y < 95:
        w = random.uniform(7, 13); h = random.uniform(12, 34); dep = 10
        box(f"bld{sx}_{int(y)}", (dep, w - 0.25, h), (sx * (8.1 + dep / 2), y + w / 2, h / 2), F)
        y += w

# street lights (cool LED) with volumetric spots
LAMP = emissive("#e9f6ff", 40)
POLE = concrete("#2a2d30", 0.4, "pole")
for i, yy in enumerate(range(4, 90, 14)):
    for sx in (-1, 1):
        if (i + (sx > 0)) % 2:
            continue
        box("pole", (0.12, 0.12, 6.2), (sx * 5.4, yy, 3.1), POLE)
        box("arm", (1.4, 0.1, 0.1), (sx * 4.8, yy, 6.15), POLE)
        box("head", (0.6, 0.25, 0.08), (sx * 4.2, yy, 6.08), LAMP)
        ld = bpy.data.lights.new("spot", "SPOT"); ld.energy = 900; ld.spot_size = math.radians(80); ld.spot_blend = 0.6
        ld.color = lin("#dcefff")[:3]; ld.shadow_soft_size = 0.25
        o = bpy.data.objects.new("spot", ld); col.objects.link(o); o.location = (sx * 4.2, yy, 6.0)

# bright haze at the end of the street (the "walk out of the light" backdrop)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 85, 12), rotation=(math.pi / 2, 0, 0))
bl = bpy.context.object; bl.scale = (30, 30, 1); bl.data.materials.append(emissive("#eaf7ff", 4.0))

def area(name, loc, target, size, watts, hexc):
    ld = bpy.data.lights.new(name, "AREA"); ld.size = size; ld.energy = watts; ld.color = lin(hexc)[:3]
    ob = bpy.data.objects.new(name, ld); col.objects.link(ob); ob.location = loc
    e = bpy.data.objects.new(name + "_t", None); col.objects.link(e); e.location = target
    c = ob.constraints.new("TRACK_TO"); c.target = e; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"

CHAR_Y = 3.2
area("backrim", (0.0, CHAR_Y + 4.5, 3.2), (0, CHAR_Y, 1.2), 3.0, 2500, "#e6f6ff")
area("magenta_kick", (-4.5, CHAR_Y + 2.0, 1.8), (0, CHAR_Y, 1.2), 1.5, 500, "#ff3d8b")

# distant skyline silhouettes against the glow
SIL = concrete("#0d1117", 0.6, "sil")
for i, (sx, w_, h_, yy) in enumerate(((-6, 7, 38, 72), (5, 9, 46, 76), (-1, 5, 28, 79), (9, 6, 30, 70), (-11, 8, 52, 74))):
    box(f"far{i}", (w_, 6, h_), (sx, yy, h_ / 2), SIL)

# fog volume
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 40, 10)); fog = bpy.context.object
fog.scale = (30, 110, 20); fog.data.materials.append(fog_mat(0.0045)); fog.name = "fog"

# rain: camera-facing streak quads, slight wind lean
bm = bmesh.new()
for _ in range(9000):
    x = random.uniform(-7, 7); yv = random.uniform(0.8, 30); z = random.uniform(0, 9)
    L_ = random.uniform(0.25, 0.55); W = 0.004 + 0.002 * random.random(); lean = 0.12
    vs = [bm.verts.new(p) for p in ((x - W, yv, z), (x + W, yv, z), (x + W + lean * L_, yv, z + L_), (x - W + lean * L_, yv, z + L_))]
    bm.faces.new(vs)
me = bpy.data.meshes.new("rain"); bm.to_mesh(me); bm.free()
rain = bpy.data.objects.new("rain", me); col.objects.link(rain); me.materials.append(rain_mat())
rain.visible_shadow = False

# ---------- stand-in character (cel shaded + line art) ----------
chars = bpy.data.collections.new("character"); col.children.link(chars)
def part(prim, name, loc, scale, mat, rot=(0, 0, 0), **kw):
    getattr(bpy.ops.mesh, prim)(location=loc, rotation=rot, **kw)
    ob = bpy.context.object; ob.name = name; ob.scale = scale
    for c in ob.users_collection:
        c.objects.unlink(ob)
    chars.objects.link(ob); ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob

COAT = cel("#3a4556", "#151a23"); KNIT = cel("#d9d4cc", "#77726c"); SKIN = cel("#ecc9ab", "#9c7158")
HAIR = cel("#16181d", "#08090b"); PANTS = cel("#23262e", "#0c0e12"); SHOE = cel("#141517", "#050506")
X, Y = 0.0, CHAR_Y

def lathe(name, prof, mat, seg=40, off=(0, 0, 0)):
    """prof: [(z, rx, ry, dy)] elliptical rings stacked in z (dy shifts a ring forward/back)."""
    bm = bmesh.new(); rings = []
    for z, rx, ry, dy in prof:
        rings.append([bm.verts.new((off[0] + rx * math.cos(2 * math.pi * i / seg), off[1] + dy + ry * math.sin(2 * math.pi * i / seg), off[2] + z)) for i in range(seg)])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(seg):
            bm.faces.new((r0[i], r0[(i + 1) % seg], r1[(i + 1) % seg], r1[i]))
    bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me); chars.objects.link(ob); me.materials.append(mat)
    return ob

def limb(name, a, b_, r0, r1, mat):
    """Tapered tube from point a to point b_ with ball joints."""
    ax, ay, az = a; bx, by, bz = b_
    d = math.dist(a, b_); mid = ((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r0, radius2=r1, depth=d, location=mid)
    ob = bpy.context.object; ob.name = name
    for c in ob.users_collection:
        c.objects.unlink(ob)
    chars.objects.link(ob); ob.data.materials.append(mat)
    v = (bx - ax, by - ay, bz - az); ob.rotation_mode = "QUATERNION"
    from mathutils import Vector
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(v).normalized())
    for p in ob.data.polygons:
        p.use_smooth = True
    for pt, r in ((a, r0), (b_, r1)):
        part("primitive_uv_sphere_add", name + "_j", pt, (r, r, r), mat, segments=20, ring_count=10)

# long coat: tall manhwa proportions (~8 heads), hem flares and swings with the stride
lathe("coat", [(0.40, 0.33, 0.21, 0.05), (0.62, 0.29, 0.19, 0.03), (0.9, 0.25, 0.165, 0.0), (1.12, 0.215, 0.15, 0.0),
               (1.3, 0.22, 0.15, 0.0), (1.42, 0.245, 0.15, 0.0), (1.49, 0.23, 0.14, 0.0), (1.53, 0.15, 0.11, 0.0),
               (1.555, 0.07, 0.07, 0.0)], COAT, off=(X, Y, 0))
lathe("collar", [(1.5, 0.075, 0.075, 0.0), (1.64, 0.062, 0.065, 0.0), (1.66, 0.05, 0.05, 0.0)], KNIT, off=(X, Y, 0))
stride = math.radians(13)
for sx, a in ((-1, stride), (1, -stride)):   # mid-stride walk toward camera
    hip = (X + sx * 0.1, Y, 0.95); knee = (X + sx * 0.1, Y - math.sin(a) * 0.48, 0.5)
    ank = (X + sx * 0.1, Y - math.sin(a) * 0.48 - math.sin(a * 0.4) * 0.42, 0.08)
    limb(f"thigh{sx}", hip, knee, 0.085, 0.07, PANTS); limb(f"shin{sx}", knee, ank, 0.07, 0.055, PANTS)
    part("primitive_uv_sphere_add", f"shoe{sx}", (ank[0], ank[1] - 0.06, 0.045), (0.06, 0.14, 0.05), SHOE, segments=24, ring_count=12)
for sx in (-1, 1):   # hands in coat pockets
    sh = (X + sx * 0.235, Y, 1.43); el = (X + sx * 0.29, Y + 0.03, 1.13); pk = (X + sx * 0.25, Y - 0.07, 0.93)
    limb(f"uarm{sx}", sh, el, 0.065, 0.058, COAT); limb(f"farm{sx}", el, pk, 0.058, 0.055, COAT)
part("primitive_uv_sphere_add", "head", (X, Y - 0.005, 1.775), (0.098, 0.112, 0.122), SKIN, segments=48, ring_count=24)
part("primitive_uv_sphere_add", "jaw", (X, Y - 0.03, 1.715), (0.07, 0.075, 0.06), SKIN, segments=32, ring_count=16)
part("primitive_uv_sphere_add", "hair", (X, Y + 0.02, 1.835), (0.106, 0.12, 0.085), HAIR, segments=48, ring_count=24)
part("primitive_uv_sphere_add", "hair_back", (X, Y + 0.05, 1.78), (0.1, 0.09, 0.1), HAIR, segments=32, ring_count=16)

# freestyle line art on the character only
scn.render.use_freestyle = True; scn.render.line_thickness_mode = "ABSOLUTE"; scn.render.line_thickness = 1.3
vl = scn.view_layers[0]; fs = vl.freestyle_settings
ls = fs.linesets[0] if fs.linesets else fs.linesets.new("chars")
ls.select_by_collection = True; ls.collection = chars
ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
ls.linestyle = ls.linestyle or bpy.data.linestyles.new("ink")
ls.linestyle.color = (0.03, 0.035, 0.05); ls.linestyle.thickness = 1.6

# ---------- camera ----------
SHOTS = {
    "hero": dict(loc=(0.35, -1.2, 0.75), tgt=(0.0, CHAR_Y, 1.25), lens=38, f=2.2),
    "low": dict(loc=(0.6, CHAR_Y - 1.6, 0.18), tgt=(0.0, CHAR_Y + 0.6, 0.9), lens=24, f=2.8),
}
S = SHOTS[SHOT]
cd = bpy.data.cameras.new("cam"); cd.lens = S["lens"]; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05
cam = bpy.data.objects.new("cam", cd); col.objects.link(cam); cam.location = S["loc"]; scn.camera = cam
t = bpy.data.objects.new("cam_t", None); col.objects.link(t); t.location = S["tgt"]
c = cam.constraints.new("TRACK_TO"); c.target = t; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
foc = bpy.data.objects.new("focus", None); col.objects.link(foc); foc.location = (X, Y - 0.1, 1.5)
cd.dof.use_dof = True; cd.dof.focus_object = foc; cd.dof.aperture_fstop = S["f"]; cd.dof.aperture_blades = 7

# ---------- world + render ----------
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = lin("#0a1622"); w.node_tree.nodes["Background"].inputs[1].default_value = 0.12

scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"
scn.cycles.samples = SAMPLES; scn.cycles.use_adaptive_sampling = True
scn.cycles.use_denoising = True; scn.cycles.denoiser = "OPENIMAGEDENOISE"
scn.cycles.max_bounces = 6; scn.cycles.volume_bounces = 1; scn.cycles.volume_step_rate = 4.0
scn.cycles.sample_clamp_indirect = 6.0; scn.cycles.transparent_max_bounces = 16
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920; scn.render.resolution_percentage = SCALE
scn.view_settings.view_transform = "AgX"; scn.view_settings.look = "AgX - Punchy"; scn.view_settings.exposure = -0.9
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.join(OUT, f"rain_{SHOT}_raw.png")
bpy.ops.render.render(write_still=True)
print("WROTE", scn.render.filepath)
