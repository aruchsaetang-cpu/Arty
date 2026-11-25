"""Yamazaki house: five original sets of a large traditional clan compound, in the cel + ink look of lookdev/city.py.

    import yamazaki as Y
    hall = Y.hall(Vector((0, 0, 0)))            # each builder: origin Vector -> Set (see below)
    gate = Y.gate_courtyard(Vector((60, 0, 0)))

Builders (O = origin Vector; ground at z=0, metres, front of a character is -Y at heading 0; cameras sit at -Y and look +Y):
    hall(O, shoji_col, lantern_col)    16 x 9 m tatami hall, 30 kneeling spots, 12 m dolly line, dais at the back (+Y)
    gate_courtyard(O)                  tiled gate (y=8), gravel courtyard, stone path, sunny lane seen through the open gate
    dojo(O)                            10 x 8 m wooden dojo, veranda (engawa) on +X, weapon rack, scroll, paper doors
    bedroom(O, door_open)              4 x 4 m tatami room, futon, moon window (+Y), sliding door (-X) onto a corridor
    stairway(O, night)                 40 stone steps (+Y) between lantern rows, torii, 3-storey dark hall, cherry tree, moon

Every builder returns a Set: .coll (its Collection), .objects, .meta (dict: camera hints, kneel spots, ...), .tris.
Look: solids use a 3-band cel emission shader (same bands as character_mh.cel, without the street-neon tints),
glow() from city.py for paper and lanterns, and every mesh carries the project's ink outline (Solidify, flipped
normals, character_mh.ink_mat). Light is baked into the palette (the cel shader ignores scene lights), so the set colours
carry the mood. set_world(kind) sets the sky; each builder calls it unless world=False.
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("FRAMES", "1"); os.environ.setdefault("PEOPLE", "0")
import city as C
import character_mh as ch

scn = C.scn
lin = ch.lin
RAD = math.radians
INK = 0.028        # default outline thickness (m) for big shapes; small details pass less

# ======================================================================= materials
LIGHT = Vector((-0.55, -0.7, 0.55)).normalized()   # same fixed light as character_mh.cel
_CM = {}

def cel(hexc, shade=None, pat=None, scale=1.0, dark=0.5, name=None):
    """3-band cel emission (hard shadow edge like character_mh.cel). pat: None | 'stone' | 'speckle'."""
    key = (hexc, shade, pat, scale, dark)
    if key in _CM: return _CM[key]
    m = bpy.data.materials.new(name or f"yz_{hexc[1:]}{'_' + pat if pat else ''}"); g = C.G(m)
    geo = g.n("ShaderNodeNewGeometry")
    d = g.n("ShaderNodeVectorMath", _operation="DOT_PRODUCT"); d.inputs[1].default_value = LIGHT
    g.ln(geo.outputs["Normal"], d.inputs[0]); dv = d.outputs["Value"]
    base = lin(hexc)
    sh = lin(shade) if shade else tuple(c * 0.33 + t for c, t in zip(base[:3], (0.002, 0.003, 0.009))) + (1.0,)
    mid = tuple(a * 0.62 + b * 0.38 for a, b in zip(base, sh))
    c = g.mix(g.m("GREATER_THAN", dv, 0.02), sh, mid)
    c = g.mix(g.m("GREATER_THAN", dv, 0.42), c, base)
    if pat:
        tc = g.n("ShaderNodeTexCoord")
        if pat == "stone":      # irregular block lines on every face (3D voronoi edges, world space)
            v = g.n("ShaderNodeTexVoronoi", _voronoi_dimensions="3D", _feature="DISTANCE_TO_EDGE", Scale=scale)
            g.ln(tc.outputs["Object"], v.inputs["Vector"]); f = g.m("GREATER_THAN", v.outputs["Distance"], 0.06)
        else:                   # speckle: gravel, grass, plaster grain
            v = g.n("ShaderNodeTexNoise", Scale=scale, Detail=2.0); g.ln(tc.outputs["Object"], v.inputs["Vector"])
            f = g.m("GREATER_THAN", v.outputs["Fac"], 0.47)
        dk = g.n("ShaderNodeMix", _data_type="RGBA", _blend_type="MULTIPLY"); dk.inputs[0].default_value = 1.0
        g.ln(c, dk.inputs[6]); dk.inputs[7].default_value = (dark, dark, dark, 1.0)
        c = g.mix(f, dk.outputs[2], c)
    e = g.n("ShaderNodeEmission", Strength=1.0); g.ln(c, e.inputs["Color"]); g.ln(e.outputs[0], g.out.inputs[0])
    _CM[key] = m; return m

def radial(col, strength, name=None):
    """Soft round glow (halo billboard or floor light pool): emission fading to transparent from the quad centre (UV)."""
    key = ("radial", col, strength)
    if key in _CM: return _CM[key]
    m = bpy.data.materials.new(name or f"yz_halo_{col[1:]}"); g = C.G(m)
    uv = g.n("ShaderNodeTexCoord"); sub = g.n("ShaderNodeVectorMath", _operation="SUBTRACT")
    sub.inputs[1].default_value = (0.5, 0.5, 0.0); g.ln(uv.outputs["UV"], sub.inputs[0])
    ln_ = g.n("ShaderNodeVectorMath", _operation="LENGTH"); g.ln(sub.outputs[0], ln_.inputs[0])
    fall = g.m("POWER", g.m("SUBTRACT", 1.0, g.m("MULTIPLY", ln_.outputs["Value"], 2.0), clamp=True), 2.2)
    e = g.n("ShaderNodeEmission", Strength=strength); e.inputs["Color"].default_value = lin(col)
    t = g.n("ShaderNodeBsdfTransparent"); mx = g.n("ShaderNodeMixShader")
    g.ln(fall, mx.inputs[0]); g.ln(t.outputs[0], mx.inputs[1]); g.ln(e.outputs[0], mx.inputs[2]); g.ln(mx.outputs[0], g.out.inputs[0])
    _CM[key] = m; return m

def set_world(kind):
    """Scene sky. 'night' (deep blue, faint horizon glow), 'day' (bright warm-white to blue), 'indoor' (dark warm)."""
    w = bpy.data.worlds.new("yz_" + kind); scn.world = w; w.use_nodes = True
    g = C.G.__new__(C.G); g.nt = w.node_tree; g.N = g.nt.nodes; g.L = g.nt.links; g.N.clear()
    out = g.N.new("ShaderNodeOutputWorld"); bg = g.N.new("ShaderNodeBackground")
    tc = g.N.new("ShaderNodeTexCoord"); so = g.N.new("ShaderNodeSeparateXYZ"); g.L.new(tc.outputs["Generated"], so.inputs[0])
    cr = g.N.new("ShaderNodeValToRGB"); g.L.new(so.outputs["Z"], cr.inputs[0])
    e = cr.color_ramp.elements
    if kind == "day":
        e[0].position = 0.5; e[0].color = lin("#fff4dc"); e[1].position = 0.72; e[1].color = lin("#5aa0f0"); s = 1.4
    elif kind == "indoor":
        e[0].position = 0.45; e[0].color = lin("#1a1210"); e[1].position = 0.85; e[1].color = lin("#0a0a10"); s = 1.0
    else:
        e[0].position = 0.45; e[0].color = lin("#243258"); e[1].position = 0.9; e[1].color = lin("#070b1c"); s = 1.0
    g.L.new(cr.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = s
    g.L.new(bg.outputs[0], out.inputs["Surface"])

# ======================================================================= geometry kit
class Set:
    """A builder's result: its collection, objects, meta dict and triangle count. Geometry is merged per (material, ink width)."""
    def __init__(self, name, O):
        self.O = Vector(O); self.name = name; self.meta = {}; self.objects = []; self.tris = 0
        self.coll = bpy.data.collections.new(name); scn.collection.children.link(self.coll)
        self._bm = {}

    def _b(self, mat, ink):
        key = (mat.name, round(ink, 5))
        if key not in self._bm: self._bm[key] = (mat, ink, bmesh.new())
        return self._bm[key][2]

    def box(self, mat, c, size, rot=(0, 0, 0), ink=INK, M=None):
        T = Matrix.Translation(self.O + Vector(c)) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
        if M is not None: T = Matrix.Translation(self.O) @ M @ Matrix.Translation(Vector(c)) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y")
        bmesh.ops.create_cube(self._b(mat, ink), size=1.0, matrix=T @ Matrix.Diagonal((size[0], size[1], size[2], 1)))

    def cyl(self, mat, c, r, h, seg=10, r2=None, axis="z", ink=INK):
        rot = {"z": Matrix.Identity(4), "x": Matrix.Rotation(RAD(90), 4, "Y"), "y": Matrix.Rotation(RAD(90), 4, "X")}[axis]
        bmesh.ops.create_cone(self._b(mat, ink), cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h,
                              matrix=Matrix.Translation(self.O + Vector(c)) @ rot)

    def blob(self, mat, c, r, squash=(1, 1, 1), sub=1, ink=INK):
        bmesh.ops.create_icosphere(self._b(mat, ink), subdivisions=sub, radius=1.0,
                                   matrix=Matrix.Translation(self.O + Vector(c)) @ Matrix.Diagonal((r * squash[0], r * squash[1], r * squash[2], 1)))

    def beam(self, mat, a, b, tw, th=None, ink=INK):
        a = self.O + Vector(a); b = self.O + Vector(b); d = b - a
        q = d.to_track_quat("Z", "Y")
        bmesh.ops.create_cube(self._b(mat, ink), size=1.0, matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
                              @ Matrix.Diagonal((tw, th or tw, d.length, 1)))

    def solid(self, mat, loops, ink=INK):
        """Closed solid between two same-length vertex loops (bottom ring, top ring), local coords."""
        bm = self._b(mat, ink); n = len(loops[0])
        v0 = [bm.verts.new(self.O + Vector(p)) for p in loops[0]]; v1 = [bm.verts.new(self.O + Vector(p)) for p in loops[1]]
        fs = [bm.faces.new(v0[::-1]), bm.faces.new(v1)]
        for i in range(n): fs.append(bm.faces.new((v0[i], v0[(i + 1) % n], v1[(i + 1) % n], v1[i])))
        bmesh.ops.recalc_face_normals(bm, faces=fs)

    def prism(self, mat, pts, axis, a0, a1, ink=INK):
        """Polygon pts [(u, v)] extruded along axis 'x' (u=y, v=z) or 'y' (u=x, v=z) from a0 to a1."""
        mk = (lambda u, v, a: (a, u, v)) if axis == "x" else (lambda u, v, a: (u, a, v))
        self.solid(mat, ([mk(u, v, a0) for u, v in pts], [mk(u, v, a1) for u, v in pts]), ink)

    def frustum(self, mat, c, hw0, hd0, hw1, hd1, h, ink=INK):
        x, y, z = c
        r = lambda hw, hd, zz: [(x - hw, y - hd, zz), (x + hw, y - hd, zz), (x + hw, y + hd, zz), (x - hw, y + hd, zz)]
        self.solid(mat, (r(hw0, hd0, z), r(hw1, hd1, z + h)), ink)

    def quad(self, mat, pts, ink=0.0):
        bm = self._b(mat, ink); vs = [bm.verts.new(self.O + Vector(p)) for p in pts]
        f = bm.faces.new(vs); uv = bm.loops.layers.uv.verify() if bm.loops.layers.uv else bm.loops.layers.uv.new("UVMap")
        for l, t in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): l[uv].uv = t

    def halo(self, c, size, col, strength, ink=0.0):
        """Round glow facing the camera (-Y)."""
        x, y, z = c; s = size / 2
        self.quad(radial(col, strength), [(x - s, y, z - s), (x + s, y, z - s), (x + s, y, z + s), (x - s, y, z + s)], ink)

    def pool(self, c, r, col, strength):
        """Round pool of light on a floor at z=c[2]."""
        x, y, z = c
        self.quad(radial(col, strength), [(x - r, y - r, z), (x + r, y - r, z), (x + r, y + r, z), (x - r, y + r, z)])

    def light(self, loc, watts, col, kind="POINT", size=0.4):
        ld = bpy.data.lights.new(self.name + "_l", kind); ld.energy = watts; ld.color = col[:3] if len(col) > 3 else col
        if kind == "POINT": ld.shadow_soft_size = size
        ob = bpy.data.objects.new(self.name + "_l", ld); self.coll.objects.link(ob); ob.location = self.O + Vector(loc)
        return ob

    def finish(self):
        """Merge the batches into objects, each with the project's ink outline modifier."""
        inkm = ch.ink_mat()
        for (mn, _), (mat, ink, bm) in self._bm.items():
            me = bpy.data.meshes.new(f"{self.name}_{mn}"); bm.to_mesh(me); bm.free()
            ob = bpy.data.objects.new(f"{self.name}_{mn}", me); self.coll.objects.link(ob)
            me.materials.append(mat); me.materials.append(inkm)
            o = ob.modifiers.new("ink", "SOLIDIFY"); o.thickness = ink; o.offset = 1.0   # as character_mh.add_mods; thickness 0 = tagged, no line
            o.use_flip_normals = True; o.use_rim = False; o.material_offset = 1; o.use_quality_normals = True
            me.calc_loop_triangles(); self.tris += len(me.loop_triangles) * (2 if ink else 1)
            self.objects.append(ob)
        self._bm = {}
        return self

def hip_roof(k, mat, ridge_mat, c, w, d, rise, tiers=7, ink=0.04):
    """Black-tiled hip roof: stacked frusta (steps read as tile courses), curved profile, hip ridges, ridge cap, end tiles.
    c = centre of the eave line (bottom of the roof), w x d eave outline."""
    x, y, z = c; lip = 0.07
    if w >= d: hw1, hd1 = (w - d) / 2 + 0.12, 0.14
    else: hw1, hd1 = 0.14, (d - w) / 2 + 0.12
    hw0, hd0 = w / 2, d / 2
    k.box(ridge_mat, (x, y, z - 0.08), (w + 0.1, d + 0.1, 0.16), ink=ink * 0.6)            # soffit / eave board
    for i in range(tiers):
        t0, t1 = i / tiers, (i + 1) / tiers
        a = lambda t, e=0.0: (hw0 + (hw1 - hw0) * t + e, hd0 + (hd1 - hd0) * t + e)
        (wa, da), (wb, db) = a(t0, lip), a(t1)
        k.frustum(mat, (x, y, z + rise * t0 ** 1.5), wa, da, wb, db, rise * (t1 ** 1.5 - t0 ** 1.5) + 0.02, ink)
    zt = z + rise
    if w >= d: k.box(ridge_mat, (x, y, zt + 0.1), (2 * hw1 + 0.5, 0.42, 0.32), ink=ink * 0.6)
    else: k.box(ridge_mat, (x, y, zt + 0.1), (0.42, 2 * hd1 + 0.5, 0.32), ink=ink * 0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k.beam(ridge_mat, (x + sx * (hw0 + lip), y + sy * (hd0 + lip), z + 0.05), (x + sx * hw1, y + sy * hd1, zt + 0.05), 0.16, 0.2, ink * 0.5)
    ex, ey = (hw1 + 0.3, 0) if w >= d else (0, hd1 + 0.3)
    for s in (-1, 1): k.box(ridge_mat, (x + s * ex, y + s * ey, zt + 0.4), (0.4, 0.4, 0.55), ink=ink * 0.5)   # end ornament tiles

def tatami_floor(k, x0, x1, y0, y1, z, mat, seam, mat_w=1.8, mat_d=0.9):
    """Flat tatami slab with seam lines laid like mats (rows offset by half a mat)."""
    k.box(mat, ((x0 + x1) / 2, (y0 + y1) / 2, z - 0.025), (x1 - x0, y1 - y0, 0.05), ink=0.012)
    ny = max(1, round((y1 - y0) / mat_d)); dy = (y1 - y0) / ny
    for r in range(ny + 1):
        k.box(seam, ((x0 + x1) / 2, y0 + r * dy, z + 0.003), (x1 - x0, 0.045, 0.008), ink=0.004)
    for r in range(ny):
        x = x0 + (mat_w / 2 if r % 2 else 0) + mat_w
        while x < x1 - 0.2:
            k.box(seam, (x, y0 + (r + 0.5) * dy, z + 0.003), (0.045, dy, 0.008), ink=0.004); x += mat_w

def shoji_panel(k, M, w, h, paper, frame, bars=(2, 4), ink=0.01):
    """One sliding paper panel in a local frame M (panel lies in local x-z, thin in y, origin at bottom centre)."""
    t = 0.05
    k.box(paper, (0, 0, h / 2), (w, 0.02, h), M=M, ink=0.004)
    for sx in (-1, 1): k.box(frame, (sx * (w / 2 - t / 2), 0, h / 2), (t, t, h), M=M, ink=ink)
    for z in (t / 2, h - t / 2): k.box(frame, (0, 0, z), (w, t, t), M=M, ink=ink)
    for i in range(1, bars[0] + 1): k.box(frame, (-w / 2 + w * i / (bars[0] + 1), 0, h / 2), (0.022, 0.03, h), M=M, ink=0.005)
    for i in range(1, bars[1] + 1): k.box(frame, (0, 0, h * i / (bars[1] + 1)), (w, 0.03, 0.022), M=M, ink=0.005)

def paper_lantern(k, c, r, h, col, strength, cap, ink=0.012):
    x, y, z = c
    k.cyl(C.glow(col, strength), (x, y, z), r, h, 10, r2=r * 0.9, ink=ink)
    for dz in (-h / 2, h / 2): k.cyl(cap, (x, y, z + dz), r * 0.95, 0.05, 10, ink=0.008)
    for i in (-1, 1): k.cyl(cap, (x, y, z + i * h * 0.22), r * 1.01, 0.025, 10, ink=0.004)

def toro(k, c, stone, ink=0.02):
    """Small stone garden lantern."""
    x, y, z = c
    k.box(stone, (x, y, z + 0.1), (0.6, 0.6, 0.2), ink=ink); k.cyl(stone, (x, y, z + 0.6), 0.1, 0.8, 8, ink=ink)
    k.box(stone, (x, y, z + 1.1), (0.5, 0.5, 0.12), ink=ink); k.box(stone, (x, y, z + 1.32), (0.34, 0.34, 0.34), ink=ink)
    k.frustum(stone, (x, y, z + 1.49), 0.5, 0.5, 0.12, 0.12, 0.3, ink); k.blob(stone, (x, y, z + 1.85), 0.1, ink=ink)

def pine(k, c, h, lean=0.0, trunk=None, leaf=None):
    x, y, z = c
    k.beam(trunk, (x, y, z), (x + lean, y, z + h * 0.7), 0.3, 0.3, 0.02); k.beam(trunk, (x + lean, y, z + h * 0.45), (x + lean + 1.4, y, z + h * 0.8), 0.14, 0.14, 0.02)
    for i, (dx, dz, r) in enumerate(((0.2, 0.75, 1.3), (1.5, 0.82, 0.95), (-0.9, 0.58, 1.0), (lean, 1.0, 0.9))):
        k.blob(leaf, (x + lean * dz + dx, y, z + h * dz), r, (1.3, 1.0, 0.55), ink=0.03)

# ======================================================================= 1. hall
def hall(O=Vector((0, 0, 0)), shoji_col="#aebfe8", lantern_col="#ffa04a", world=True):
    """16 x 9 m tatami hall (x -8..8, y -4.5..4.5, floor z=0.05). Dais at the back (+Y), shoji along the -Y long wall,
    dark beams, hanging lanterns. meta: kneel_spots (30 x (x,y,z), heading 180 faces the dais), dolly (12 m line at y=-3.9), cams."""
    k = Set("yz_hall", O)
    wood, wood_d = cel("#4a3022", "#150d09"), cel("#2c1c13", "#0b0605")
    plaster = cel("#8a765a", "#2c2419", "speckle", 30.0, 0.8)
    tat, seam = cel("#8e9a5a", "#2f3820"), cel("#1d1c10")
    paper = C.glow(shoji_col, 1.5); gold = cel("#8a7340", "#2c2412"); crimson = cel("#8a2a2e", "#2a0c0e")
    cream = cel("#d9cfae", "#5c5440"); dk = cel("#17100c", "#050303")
    k.box(wood_d, (0, 0, -0.2), (17.0, 9.8, 0.4))
    tatami_floor(k, -7.9, 7.9, -4.4, 4.4, 0.05, tat, seam)
    # walls and posts
    k.box(plaster, (0, 4.62, 1.8), (16.4, 0.24, 3.6)); k.box(wood_d, (0, 4.5, 0.45), (16.2, 0.1, 0.9))
    for s in (-1, 1):
        k.box(plaster, (s * 8.12, 0, 1.8), (0.24, 9.2, 3.6))
        k.box(wood, (s * 8.0, 0, 3.45), (0.3, 9.2, 0.3)); k.box(wood, (s * 8.0, 0, 2.2), (0.12, 9.0, 0.16), ink=0.015)
    for sy in (-4.5, 4.5):
        k.box(wood, (0, sy, 3.45), (16.4, 0.3, 0.3)); k.box(wood, (0, sy, 2.2), (16.2, 0.16, 0.16), ink=0.015)
    for x in range(-8, 9, 2):
        k.box(wood, (x, -4.5, 1.8), (0.3, 0.3, 3.6))
        if x % 4 == 0: k.box(wood, (x, 4.5, 1.8), (0.3, 0.3, 3.6))
    for sy in (-4.5, 4.5):
        for s in (-8, 8): k.box(wood, (s, sy, 1.8), (0.32, 0.32, 3.6))
    # shoji wall (-Y long side): 8 bays x 2 panels below, glowing transoms above
    for i, xc in enumerate(range(-7, 8, 2)):
        for j, dx in enumerate((-0.5, 0.5)):
            shoji_panel(k, Matrix.Translation((xc + dx, -4.46 + 0.04 * j, 0.05)), 0.98, 2.0, paper, wood_d)
        shoji_panel(k, Matrix.Translation((xc, -4.5, 2.35)), 1.9, 0.95, paper, wood_d, bars=(5, 2))
    # end walls: fusuma
    for s in (-1, 1):
        for yc in (-2.3, 0.0, 2.3):
            k.box(cream, (s * 7.95, yc, 1.2), (0.04, 2.1, 2.1), ink=0.01); k.box(wood_d, (s * 7.93, yc, 1.2), (0.05, 2.14, 0.06), ink=0.01)
            k.box(gold, (s * 7.93, yc, 0.4), (0.03, 2.0, 0.5), ink=0.01)
    # dais at the back
    k.box(wood, (0, 3.4, 0.25), (11.0, 2.2, 0.5)); k.box(tat, (0, 3.4, 0.505), (10.6, 1.9, 0.02), ink=0.01)
    k.box(wood, (0, 2.15, 0.12), (4.0, 0.3, 0.24))
    for s in (-1, 1): k.box(crimson, (s * 5.35, 3.4, 0.52), (0.18, 1.95, 0.03), ink=0.008)
    k.box(crimson, (0, 3.45, 0.58), (1.0, 1.0, 0.1), ink=0.015); k.box(wood_d, (0, 3.9, 0.9), (0.9, 0.12, 0.7), ink=0.015)
    k.box(wood_d, (0, 3.0, 0.7), (0.7, 0.4, 0.4), ink=0.015)
    # back wall dressing: big scroll + gold fusuma
    k.box(cream, (0, 4.42, 1.95), (1.3, 0.03, 2.2), ink=0.01); k.box(dk, (0, 4.4, 1.95), (0.5, 0.03, 1.6), ink=0.005)
    for z in (0.78, 3.12): k.box(wood_d, (0, 4.4, z), (1.5, 0.06, 0.07), ink=0.01)
    for s in (-1, 1):
        for xc in (2.6, 4.2, 5.8, 7.2):
            k.box(gold, (s * xc, 4.45, 1.5), (1.5, 0.04, 2.0), ink=0.01); k.box(wood_d, (s * xc, 4.43, 1.5), (1.54, 0.04, 0.06), ink=0.01)
            k.box(cel("#2e3a40", "#0d1214"), (s * xc, 4.43, 0.9), (1.4, 0.03, 0.4), ink=0.006)
    # ceiling and beams
    k.box(wood_d, (0, 0, 3.72), (16.4, 9.4, 0.14), ink=0.01)
    for x in range(-8, 9, 2): k.box(wood, (x, 0, 3.45), (0.28, 9.0, 0.3), ink=0.02)
    for y in (-3, 0, 3): k.box(wood, (0, y, 3.3), (16.0, 0.3, 0.3), ink=0.02)
    # lanterns (hanging) and floor standing lamps, with light pools
    lc = lantern_col; cap = dk
    spots = [(x, y) for x in (-6, -2, 2, 6) for y in (-1.3, 1.2)]
    for (x, y) in spots:
        k.cyl(dk, (x, y, 3.0), 0.012, 0.6, 4, ink=0); paper_lantern(k, (x, y, 2.5), 0.24, 0.6, lc, 6.0, cap)
        k.pool((x, y, 0.07), 2.4, lc, 0.7); k.halo((x, y - 0.05, 2.5), 1.4, lc, 0.9)
    for s in (-1, 1):
        x = s * 5.4; k.box(wood_d, (x, 3.95, 0.9), (0.4, 0.4, 0.8), ink=0.015); k.box(C.glow(lc, 4.5), (x, 3.95, 1.0), (0.32, 0.32, 0.62), ink=0.01)
        k.pool((x, 3.2, 0.52), 1.6, lc, 0.7)
    for x in (-5, 0, 5): k.light((x, 0.5, 3.0), 600, (1, 0.62, 0.3), size=0.6)
    k.light((0, -2, 2.6), 400, (0.6, 0.7, 1.0), size=0.6)
    xs = [-5.4 + 1.2 * i for i in range(10)]
    k.meta.update(kneel_spots=[(x, y, 0.05) for y in (-1.9, -0.6, 0.7) for x in xs], kneel_heading=180,
                  dolly=((-6, -3.9, 1.1), (6, -3.9, 1.1)), dais_z=0.5, dais_seat=(0, 3.45, 0.5),
                  cams={"wide": ((-6.5, -4.1, 1.5), (0, 2.0, 1.2), 24), "dolly_mid": ((0, -3.9, 1.1), (0, 3, 1.3), 28)})
    if world: set_world("indoor")
    return k.finish()

# ======================================================================= 2. gate + courtyard + lane
def gate_courtyard(O=Vector((0, 0, 0)), world=True):
    """Courtyard x -20..20, y -16..8, gravel, stone path along x=0, tiled gate at y 6..10 with open doors, sunny lane (y 10..17.5)
    beyond. Daylight. meta: path (stone path start/end), lane_rect, cams."""
    k = Set("yz_gate", O)
    gravel = cel("#c9bd9f", "#6c6350", "speckle", 55.0, 0.8); slab = cel("#8d8d8a", "#3a3b3d", "stone", 3.0, 0.7)
    wood = cel("#5a3a26", "#1c1009"); wood_d = cel("#33201a", "#0e0806"); plaster = cel("#e6dfcc", "#7d7766")
    tile = cel("#252a33", "#0a0c10", "stone", 24.0, 0.6); tile_r = cel("#12151b", "#040506"); sand = cel("#f0dfae", "#9b8d62", "speckle", 25.0, 0.85)
    base = cel("#6d6b66", "#2a2a2c", "stone", 2.6, 0.7); iron = cel("#1b1b1f", "#060608"); green = cel("#5e8b4a", "#1e3320")
    leaf = cel("#3f6f3e", "#14281a"); trunk = cel("#4a3426", "#150e09")
    k.box(gravel, (0, -4, -0.1), (40.4, 24.4, 0.2), ink=0.03)
    for xr in range(-18, 19, 3): k.box(cel("#e2d8bd", "#7a7058"), (xr, -3, 0.005), (0.05, 22, 0.01), ink=0.003)   # raked lines
    for i in range(19):        # stone path, staggered slabs
        k.box(slab, (0.15 * (-1) ** i, 7.2 - i * 1.0 - 0.1, 0.04), (1.35, 0.85, 0.08), ink=0.012)
    # courtyard walls: low plaster wall on a stone foot with a tiled cap
    for (cx, cy, sx, sy) in ((-12.2, 8.5, 15.6, 0.45), (12.2, 8.5, 15.6, 0.45), (-20.2, -4, 0.45, 24.4), (20.2, -4, 0.45, 24.4)):
        k.box(plaster, (cx, cy, 1.3), (sx, sy, 2.6)); k.box(base, (cx, cy, 0.35), (sx + 0.1, sy + 0.1, 0.7))
        k.box(tile, (cx, cy, 2.75), (sx + 0.55 if sx < sy else sx + 0.05, sy + 0.55 if sy <= sx else sy + 0.05, 0.3), ink=0.02)
        k.box(tile_r, (cx, cy, 2.95), (sx + 0.3 if sx < sy else sx + 0.05, sy + 0.3 if sy <= sx else sy + 0.05, 0.12), ink=0.015)
    # gate house
    gy = 8.0
    k.box(base, (0, gy, 0.25), (10.0, 5.2, 0.5))
    for sx in (-1, 1):
        for sy_ in (-1, 1):
            k.cyl(wood, (sx * 1.9, gy + sy_ * 2.0, 2.5), 0.3, 4.0, 10); k.box(base, (sx * 1.9, gy + sy_ * 2.0, 0.6), (0.7, 0.7, 0.2), ink=0.015)
        for sy_ in (-1, 1): k.box(wood, (sx * 4.2, gy + sy_ * 2.0, 2.3), (0.34, 0.34, 3.6))
        k.box(plaster, (sx * 3.05, gy, 1.9), (2.2, 3.6, 3.0)); k.box(wood_d, (sx * 3.05, gy - 1.85, 0.9), (2.2, 0.1, 0.1), ink=0.015)
        k.box(wood_d, (sx * 3.05, gy - 1.85, 3.1), (2.2, 0.12, 0.12), ink=0.015)
    k.box(plaster, (0, gy, 3.95), (8.6, 3.6, 0.9)); k.box(wood, (0, gy - 2.0, 3.55), (8.8, 0.4, 0.4)); k.box(wood, (0, gy + 2.0, 3.55), (8.8, 0.4, 0.4))
    k.box(wood, (0, gy - 2.0, 4.4), (8.8, 0.34, 0.3)); k.box(wood, (0, gy + 2.0, 4.4), (8.8, 0.34, 0.3))
    for i in range(-5, 6): k.box(wood_d, (i * 0.82, gy - 2.15, 4.7), (0.26, 0.5, 0.3), ink=0.012)    # eave brackets
    hip_roof(k, tile, tile_r, (0, gy, 4.9), 11.6, 7.8, 2.9, tiers=8, ink=0.05)
    # open doors (swung in toward the courtyard), studs and iron bands
    for sx in (-1, 1):
        k.box(wood, (sx * 2.15, gy - 1.0, 1.85), (0.14, 2.0, 3.5), ink=0.02)
        for z in (0.7, 1.85, 3.0): k.box(iron, (sx * 2.2, gy - 1.0, z), (0.05, 2.0, 0.12), ink=0.008)
        for j in range(4):
            for zz in (0.7, 1.85, 3.0): k.box(iron, (sx * 2.23, gy - 0.45 - j * 0.4, zz + 0.2), (0.05, 0.1, 0.1), ink=0.005)
    # stone lanterns, pines
    for sx in (-1, 1): toro(k, (sx * 3.6, 2.5, 0), base)
    pine(k, (-12, 1.5, 0), 4.6, 0.5, trunk, leaf); pine(k, (13.5, -5, 0), 4.0, -0.4, trunk, leaf)
    for (x, y) in ((-16.5, 5), (15.5, 5.5), (-8, 6)): k.blob(green, (x, y, 0.5), 0.9, (1.3, 1, 0.8), ink=0.02)
    # the sunny lane beyond the gate
    k.box(sand, (0, 14, -0.1), (60, 12.0, 0.2), ink=0.03)
    k.box(cel("#cdbd90", "#6e6444"), (0, 11.6, 0.01), (60, 0.2, 0.02), ink=0.004)
    k.box(plaster, (0, 18.2, 1.4), (60, 0.5, 2.8)); k.box(base, (0, 18.2, 0.3), (60, 0.6, 0.6))
    k.box(tile, (0, 18.2, 2.95), (60, 1.1, 0.3), ink=0.02); k.box(tile_r, (0, 18.2, 3.15), (60, 0.5, 0.12), ink=0.015)
    for x in (-9, 6):    # houses behind the lane wall
        k.box(plaster, (x, 23, 2.4), (7, 5, 4.8)); hip_roof(k, tile, tile_r, (x, 23, 4.8), 9.4, 7.4, 2.4, tiers=5, ink=0.04)
    for (x, z, r) in ((-3, 4.8, 2.0), (3.5, 4.4, 1.7), (14, 5, 2.3), (-16, 5.5, 2.4), (0, 8, 3)):
        k.blob(cel("#6faa55", "#2b4a2a"), (x, 21, z), r, (1.2, 1, 0.9), ink=0.03)
    k.halo((0, 26, 3.0), 18, "#fffbe8", 2.2)       # bright haze in the doorway
    k.light((0, 0, 8), 4000, (1, 0.95, 0.85), kind="POINT", size=2)
    k.meta.update(path=((0, 7.2, 0.08), (0, -10, 0.08)), lane_rect=((-30, 11, 0), (30, 18, 0)), kids_play_area=((-4, 12, 0), (4, 17, 0)),
                  cams={"into_gate": ((0, -9, 1.5), (0, 12, 2.0), 22), "wide": ((-12, -12, 3.0), (0, 8, 2.5), 24)})
    if world: set_world("day")
    return k.finish()

# ======================================================================= 3. dojo
def dojo(O=Vector((0, 0, 0)), world=True):
    """Wooden dojo, interior x -5..5, y -4..4, floor z=0; scroll on the back wall (+Y), weapon rack on -X, shoji + engawa on +X.
    Bright warm daylight. meta: floor_z, engawa_z, cams."""
    k = Set("yz_dojo", O)
    p1, p2 = cel("#b3834f", "#3d2812"), cel("#a1733f", "#35210f")
    wood, wood_d = cel("#5a3a24", "#1a0f08"), cel("#34211a", "#0d0705")
    plaster = cel("#e0d3b4", "#6f6650", "speckle", 32.0, 0.82); paper = C.glow("#fff0cf", 1.3); cream = cel("#e8dfc4", "#6a634c")
    dk = cel("#17100c", "#050303"); steel = cel("#aab0b8", "#3a3e45"); red = cel("#8a2a2e", "#2a0c0e")
    gravel = cel("#cfc4a4", "#6c6350", "speckle", 55.0, 0.8); green = cel("#5e8b4a", "#1e3320"); leaf = cel("#3f6f3e", "#14281a")
    stone = cel("#8d8d8a", "#3a3b3d", "stone", 3.0, 0.7); trunk = cel("#4a3426", "#150e09")
    k.box(wood_d, (0, 0, -0.3), (10.6, 8.6, 0.6))
    for i in range(40):                       # floorboards run along Y
        k.box(p1 if i % 2 else p2, (-4.875 + i * 0.25, 0, 0.0), (0.24, 7.9, 0.03), ink=0.006)
    # frame, walls
    for sx in (-5, 5):
        for sy in (-4, 4): k.box(wood, (sx, sy, 2.0), (0.32, 0.32, 4.0))
    for y in (-2, 0, 2): k.box(wood, (-5, y, 2.0), (0.28, 0.28, 4.0)); k.box(wood, (5, y, 2.0), (0.28, 0.28, 4.0))
    k.box(wood_d, (0, 4.05, 0.55), (10.2, 0.1, 1.1)); k.box(plaster, (0, 4.1, 2.45), (10.2, 0.12, 2.8))
    k.box(wood_d, (-5.05, 0, 0.55), (0.1, 8.0, 1.1)); k.box(plaster, (-5.1, 0, 2.45), (0.12, 8.0, 2.8))
    k.box(wood, (0, 4.0, 3.9), (10.4, 0.32, 0.3)); k.box(wood, (-5, 0, 3.9), (0.3, 8.2, 0.3)); k.box(wood, (5, 0, 3.9), (0.3, 8.2, 0.3))
    k.box(wood, (0, -4, 3.9), (10.4, 0.32, 0.3))
    for z in (1.15, 3.1): k.box(wood, (0, 4.0, z), (10.2, 0.14, 0.12), ink=0.015)
    # kamiza: shelf + scroll on the back wall
    k.box(cream, (0, 3.98, 2.35), (1.2, 0.03, 1.9), ink=0.008); k.box(wood_d, (0, 3.96, 2.2), (0.5, 0.03, 1.2), ink=0.005)
    for z in (1.38, 3.32): k.box(wood_d, (0, 3.96, z), (1.4, 0.06, 0.07), ink=0.01)
    k.box(wood, (0, 3.75, 1.0), (2.4, 0.5, 0.1)); k.box(wood_d, (0, 3.9, 0.55), (2.2, 0.25, 0.9), ink=0.015)
    for s in (-1, 1): k.cyl(cel("#4f7a46", "#1b2e1b"), (s * 0.8, 3.75, 1.2), 0.07, 0.3, 8, ink=0.008)
    # high lattice windows (back wall)
    for s in (-1, 1):
        k.box(paper, (s * 3.2, 3.98, 3.1), (1.8, 0.02, 0.7), ink=0.004)
        for i in range(8): k.box(wood_d, (s * 3.2 - 0.8 + i * 0.23, 3.95, 3.1), (0.03, 0.04, 0.72), ink=0.005)
    # weapon rack on -X wall
    k.box(wood, (-4.6, 0, 0.1), (0.5, 4.4, 0.2)); k.box(wood, (-4.75, 0, 1.45), (0.14, 4.4, 0.12), ink=0.015); k.box(wood, (-4.75, 0, 0.75), (0.14, 4.4, 0.12), ink=0.015)
    for sy in (-2.1, 2.1): k.box(wood, (-4.75, sy, 0.95), (0.18, 0.18, 1.9))
    for i in range(12):
        y = -1.9 + i * 0.35; k.beam(cel("#c9a06a", "#5a4020"), (-4.6, y, 0.22), (-4.72, y + 0.04, 1.35 + (i % 3) * 0.05), 0.055, 0.045, 0.008)
    for i, y in enumerate((-1.2, 0.0, 1.2)):
        k.beam(wood_d, (-4.45, y, 0.2), (-4.62, y, 2.5), 0.05, 0.05, 0.01); k.beam(steel, (-4.62, y, 2.5), (-4.65, y, 3.05), 0.07, 0.015, 0.01)
    for sx in (-4.55, -4.35): k.beam(wood, (sx, 2.4, 0.25), (sx - 0.1, 2.4, 1.6), 0.04, 0.04, 0.008)
    # paper doors + engawa on +X, one pair slid open
    for j in range(6):
        yc = -3.4 + j * 1.36; slid = j in (1, 2)
        shoji_panel(k, Matrix.Translation((5.0 + 0.05 * (j % 2), yc, 0.0)) @ Matrix.Rotation(RAD(90), 4, "Z"), 1.3, 2.9, paper, wood_d, bars=(3, 6))
    k.box(wood, (5, 0, 3.0), (0.14, 8.0, 0.14), ink=0.015)
    k.box(wood, (6.2, 0, -0.18), (2.8, 9.0, 0.16))          # engawa floor at z ~ -0.1
    for i in range(10): k.box(p1 if i % 2 else p2, (5.3 + i * 0.28, 0, -0.095), (0.26, 8.8, 0.02), ink=0.005)
    for y in (-4.4, -1.5, 1.5, 4.4):
        k.box(wood, (7.5, y, 1.7), (0.26, 0.26, 3.6)); k.box(wood_d, (7.5, y, -0.7), (0.4, 0.4, 0.6), ink=0.015)
    k.box(wood, (7.5, 0, 3.55), (0.3, 9.2, 0.28)); k.box(wood_d, (7.5, 0, 0.7), (0.06, 9.0, 0.06), ink=0.01)
    k.prism(cel("#3a3a42", "#101014", "stone", 22.0, 0.7), [(4.7, 3.9), (8.9, 3.45), (8.9, 3.75), (4.7, 4.25)], "y", -4.8, 4.8, ink=0.04)   # veranda eave
    # ceiling: open rafters under a plank roof
    for ys in (-3, 0, 3):
        k.box(wood, (0, ys, 3.55), (10.2, 0.28, 0.3), ink=0.02)
        k.beam(wood, (-5.1, ys, 3.9), (0, ys, 5.0), 0.2, 0.22, 0.02); k.beam(wood, (5.1, ys, 3.9), (0, ys, 5.0), 0.2, 0.22, 0.02)
        k.box(wood, (0, ys, 4.3), (0.2, 0.2, 1.4), ink=0.02)
    k.box(wood, (0, 0, 5.0), (0.3, 8.4, 0.3), ink=0.02)
    for s in (-1, 1): k.prism(cel("#6a4a30", "#1d130b"), [(s * 0.0, 4.9), (s * 5.4, 3.95), (s * 5.4, 4.05), (0, 5.05)], "y", -4.3, 4.3, ink=0.02)
    # garden
    k.box(gravel, (13, 0, -0.9), (14.0, 16.0, 0.4), ink=0.03); k.box(gravel, (0, -12, -0.5), (30, 8, 0.2), ink=0.03)
    for i in range(3): k.box(stone, (8.6 + i * 0.55, -3.0, -0.75 + i * 0.15), (0.6, 1.4, 0.15 * (3 - i) + 0.1), ink=0.015)
    pine(k, (13, 3.5, -0.7), 5.0, 0.6, trunk, leaf); toro(k, (10.5, -2.5, -0.7), stone)
    for i in range(20): k.box(wood, (16.5, -8 + i * 0.85, 0.0), (0.12, 0.12, 1.6), ink=0.012)
    k.box(wood, (16.5, 0, 0.8), (0.1, 17, 0.1), ink=0.01)
    k.light((0, 0, 3.2), 1600, (1, 0.85, 0.65), size=0.8)
    k.meta.update(floor_z=0.0, engawa_z=-0.1, cams={"into_room": ((-3.5, -3.6, 1.5), (1, 2.5, 1.3), 24), "from_engawa": ((9, -2.5, 1.2), (-2, 1, 1.4), 26)})
    if world: set_world("day")
    return k.finish()

# ======================================================================= 4. bedroom
def bedroom(O=Vector((0, 0, 0)), door_open=0.65, world=True):
    """4 x 4 m tatami room (x -2..2, y -2..2, ceiling 2.6). Futon at the back-left, moon window on the +Y wall, paper door on the -X wall
    sliding open (door_open 0..1) onto a corridor with a lantern, oshiire closet on +X. Dim blue moonlight + one warm lantern (andon).
    meta: futon (centre), lantern_pos, cams."""
    k = Set("yz_bedroom", O)
    tat, seam = cel("#6c7c5a", "#1d2518"), cel("#0c100a")
    wood, wood_d = cel("#4a3629", "#140d0a"), cel("#2a1d16", "#0a0605")
    plaster = cel("#7983a6", "#232842", "speckle", 30.0, 0.82); paper_b = C.glow("#8fa4e8", 0.6)
    futon = cel("#6d6aa8", "#1f1e3a"); sheet = cel("#c9cce6", "#4a4c64"); pillow = cel("#bcc0d6", "#40425a")
    cream = cel("#7a7f9a", "#22253a"); dk = cel("#0c0b12", "#030305"); lamp = C.glow("#ffa850", 6.0)
    k.box(wood_d, (0, 0, -0.2), (4.4, 4.4, 0.4))
    tatami_floor(k, -1.95, 1.95, -1.95, 1.95, 0.05, tat, seam, mat_w=2.0, mat_d=1.0)
    for x in (-2, 2):
        for y in (-2, 2): k.box(wood, (x, y, 1.3), (0.2, 0.2, 2.6))
    # back wall with moon window (opening x -0.6..1.0, z 0.9..2.1)
    k.box(plaster, (-1.3, 2.05, 1.3), (1.4, 0.12, 2.6)); k.box(plaster, (1.5, 2.05, 1.3), (1.0, 0.12, 2.6))
    k.box(plaster, (0.2, 2.05, 0.45), (1.6, 0.12, 0.9)); k.box(plaster, (0.2, 2.05, 2.35), (1.6, 0.12, 0.5))
    for x in (-0.62, 1.02): k.box(wood, (x, 2.0, 1.5), (0.1, 0.16, 1.3), ink=0.015)
    for z in (0.9, 2.1): k.box(wood, (0.2, 2.0, z), (1.7, 0.16, 0.1), ink=0.015)
    for x in (-0.1, 0.5): k.box(wood_d, (x, 1.97, 1.5), (0.04, 0.05, 1.2), ink=0.006)
    shoji_panel(k, Matrix.Translation((0.55, 1.93, 0.95)), 0.8, 1.15, paper_b, wood_d, bars=(1, 3))   # one shoji slid half across the window
    k.box(wood_d, (0.2, 1.9, 0.9), (1.7, 0.4, 0.06), ink=0.012)       # sill
    # -X wall: paper door opening onto the corridor
    k.box(plaster, (-2.05, 1.2, 1.3), (0.12, 1.6, 2.6)); k.box(plaster, (-2.05, -1.55, 2.3), (0.12, 0.9, 0.6)); k.box(plaster, (-2.05, -0.2, 2.45), (0.12, 3.6, 0.3))
    k.box(wood, (-2.0, 0, 2.1), (0.16, 4.0, 0.12), ink=0.015); k.box(wood, (-2.0, 0, 0.06), (0.16, 4.0, 0.06), ink=0.01)
    paper = C.glow("#8fa4e8", 0.55)
    opening = 0.0 + 0.95 * door_open
    shoji_panel(k, Matrix.Translation((-1.98, 0.33 + 0.5 + opening - 0.5 * 0, 0.05)) @ Matrix.Rotation(RAD(90), 4, "Z"), 0.95, 2.0, paper, wood_d, bars=(2, 4))
    shoji_panel(k, Matrix.Translation((-2.03, 1.2 - 0.05 - 0.0, 0.05)) @ Matrix.Rotation(RAD(90), 4, "Z"), 0.95, 2.0, paper, wood_d, bars=(2, 4))
    # +X wall: oshiire closet, fusuma
    k.box(plaster, (2.05, 0, 1.3), (0.12, 4.0, 2.6))
    for y in (-0.9, 0.9):
        k.box(cream, (1.96, y, 1.2), (0.04, 1.75, 2.0), ink=0.01); k.box(wood_d, (1.94, y, 1.2), (0.05, 1.78, 0.05), ink=0.008)
    # ceiling
    k.box(wood_d, (0, 0, 2.66), (4.3, 4.3, 0.1), ink=0.01)
    for y in (-1, 0, 1): k.box(wood, (0, y, 2.5), (4.2, 0.18, 0.2), ink=0.015)
    # futon, pillow, folded bedding
    k.box(futon, (-0.75, 0.45, 0.11), (1.05, 2.0, 0.12), ink=0.012); k.box(sheet, (-0.75, 0.2, 0.2), (0.95, 1.5, 0.08), ink=0.012)
    k.box(pillow, (-0.75, 1.25, 0.2), (0.5, 0.3, 0.12), ink=0.012); k.box(futon, (-0.75, -0.1, 0.27), (1.0, 1.0, 0.1), ink=0.012)
    k.box(futon, (1.4, 1.5, 0.25), (0.8, 0.9, 0.4), ink=0.012); k.box(sheet, (1.4, 1.5, 0.52), (0.8, 0.9, 0.12), ink=0.012)
    # andon (standing paper lamp), the one warm light
    k.box(wood_d, (0.55, 0.95, 0.35), (0.34, 0.34, 0.6), ink=0.012); k.box(lamp, (0.55, 0.95, 0.42), (0.28, 0.28, 0.45), ink=0.008)
    k.box(wood_d, (0.55, 0.95, 0.66), (0.4, 0.4, 0.05), ink=0.01)
    k.pool((0.55, 0.95, 0.065), 1.7, "#ffa850", 0.9); k.halo((0.55, 0.8, 0.45), 1.0, "#ffa850", 0.9)
    k.light((0.55, 0.95, 0.6), 80, (1, 0.6, 0.28), size=0.2)
    # moon light falling through the window: 2x2 panes on the floor
    for ix in range(2):
        for iy in range(2):
            x0 = -0.2 + ix * 0.6; y0 = -0.4 + iy * 0.62
            k.quad(C.glow("#6f87d6", 0.5), [(x0, y0, 0.072), (x0 + 0.52, y0 - 0.05, 0.072), (x0 + 0.52, y0 + 0.5, 0.072), (x0, y0 + 0.55, 0.072)])
    k.light((0.2, 1.8, 1.6), 120, (0.5, 0.6, 1.0), size=0.5)
    # corridor outside the sliding door
    k.box(wood, (-3.0, 0, -0.05), (1.9, 6.0, 0.1)); k.box(wood_d, (-3.95, 0, 1.2), (0.12, 6.0, 2.5)); k.box(wood, (-3.0, 0, 2.55), (2.0, 6.0, 0.1))
    for y in range(-2, 3): k.box(wood, (-3.95, y * 1.2, 1.25), (0.2, 0.2, 2.5), ink=0.015)
    for i in range(12): k.box(wood_d, (-3.0, -2.8 + i * 0.5, 0.0), (1.9, 0.02, 0.01), ink=0.003)
    k.cyl(dk, (-3.0, -0.9, 2.3), 0.012, 0.5, 4, ink=0); paper_lantern(k, (-3.0, -0.9, 1.95), 0.2, 0.5, "#ffb060", 5.0, dk); k.halo((-3.0, -1.0, 1.95), 1.6, "#ffa850", 0.8)
    k.pool((-3.0, -0.9, 0.04), 1.8, "#ffa850", 0.5)
    # the moon, large and pale, far behind the window, with a few dark branches
    moon = Vector((-2.0, 45.0, 17.0))
    k.cyl(C.glow("#fff6dc", 5.0), moon, 3.3, 0.2, 24, axis="y", ink=0); k.halo(moon + Vector((0, -1, 0)), 20.0, "#bcd0ff", 0.7)
    for (x, z, r) in ((-6, 3, 4), (9, 2, 5), (-12, 6, 3), (14, 6, 4)):
        k.blob(cel("#0c1322", "#05080f"), (x, 18, z), r, (1.4, 1, 1), ink=0.0)
    k.beam(dk, (2.5, 3.2, 1.0), (0.9, 3.2, 2.0), 0.05, 0.05, 0.0); k.beam(dk, (0.9, 3.2, 2.0), (0.4, 3.2, 2.35), 0.03, 0.03, 0.0)
    k.meta.update(futon=(-0.75, 0.45, 0.2), lantern_pos=(0.55, 0.95, 0.5), door_line=(-2.0, -0.4, 0),
                  cams={"door": ((1.5, -1.7, 1.2), (-1.5, 0.2, 1.0), 24), "window": ((-1.3, -1.7, 0.9), (0.4, 2.0, 1.4), 24)})
    if world: set_world("night")
    return k.finish()

# ======================================================================= 5. stairway
def stairway(O=Vector((0, 0, 0)), night=True, world=True):
    """40 stone steps (0.17 rise x 0.35 run, y 0..14, z up to 6.8) between two rows of paper lanterns on poles, climbing to a red torii
    (y=16), a paved plaza and a 3-storey black-roofed main hall (y 28..42). Lawns, one pink cherry tree, stone wall, full moon
    (night=True) or daylight (night=False). meta: step(i) helper positions, hall front, cams."""
    k = Set("yz_stairs", O)
    N, RISE, RUN = 40, 0.17, 0.35; TOP = N * RISE
    if night:
        stone = cel("#6b7088", "#1c1f30", "stone", 2.6, 0.7); step = cel("#7e839c", "#22263a", "stone", 3.0, 0.8)
        grass = cel("#2d5a4c", "#0c1c1c", "speckle", 20.0, 0.75); wood = cel("#4b3128", "#150d0b"); wall_p = cel("#7d7488", "#24202e")
        tile = cel("#1a2030", "#06080e"); tile_r = cel("#0e121c", "#030408"); red = cel("#b2301f", "#340e0c"); pink = cel("#e79ab8", "#7a3f66")
        trunk = cel("#3b2a2f", "#120c0e"); paving = cel("#6a6f86", "#1c1f2e", "stone", 1.6, 0.75); win = C.glow("#ffb25a", 2.6)
        lawn_far = cel("#233f44", "#0a1618", "speckle", 14.0, 0.75)
    else:
        stone = cel("#9a9a96", "#4a4a4c", "stone", 2.6, 0.7); step = cel("#b8b6ae", "#5a5852", "stone", 3.0, 0.8)
        grass = cel("#6aa84f", "#2b4d2a", "speckle", 20.0, 0.78); wood = cel("#6a4630", "#24150d"); wall_p = cel("#e3dccb", "#7d7766")
        tile = cel("#2b3038", "#0c0e12"); tile_r = cel("#15181e", "#050607"); red = cel("#d23a22", "#561508"); pink = cel("#f6b0cc", "#b8688c")
        trunk = cel("#5a4036", "#1d1411"); paving = cel("#aaa89e", "#55534c", "stone", 1.6, 0.75); win = cel("#3a2a20", "#100a08")
        lawn_far = cel("#5a9a46", "#244422", "speckle", 14.0, 0.78)
    dk = cel("#0e0c10", "#030304"); zs = lambda y: max(0.0, min(y, N * RUN)) * RISE / RUN
    # ground and lawns (wedges along the climb)
    k.box(grass, (0, 20, -0.25), (60, 52, 0.5), ink=0.04)
    for s in (-1, 1):
        k.prism(lawn_far, [(-3, -0.02), (0, -0.02), (N * RUN, TOP), (44, TOP), (44, -0.3), (-3, -0.3)], "x", *sorted((s * 2.45, s * 24)), ink=0.04)
        k.prism(stone, [(0, 0), (N * RUN, TOP), (N * RUN, TOP + 0.55), (0, 0.55)], "x", *sorted((s * 2.1, s * 2.55)), ink=0.025)   # retaining wall along the stair
    for i in range(N): k.box(step, (0, i * RUN + RUN / 2, (i + 1) * RISE / 2), (4.0, RUN, (i + 1) * RISE), ink=0.02)
    # lantern rows
    for s in (-1, 1):
        for j in range(8):
            y = 1.0 + j * 1.9; x = s * 3.0; z0 = zs(y)
            k.cyl(wood, (x, y, z0 + 1.35), 0.055, 2.7, 6, ink=0.012)
            if night:
                paper_lantern(k, (x, y, z0 + 2.45), 0.25, 0.72, "#ffb070", 7.0, dk); k.halo((x, y - 0.3, z0 + 2.45), 2.6, "#ffa050", 1.1)
            else:
                paper_lantern(k, (x, y, z0 + 2.45), 0.25, 0.72, "#f2e6c8", 1.3, dk)
            k.box(wood, (x, y, z0 + 2.88), (0.34, 0.34, 0.06), ink=0.01)
    # torii at the top
    ty = N * RUN + 2.0; z0 = TOP
    for s in (-1, 1):
        k.cyl(red, (s * 2.4, ty, z0 + 2.7), 0.27, 5.4, 12, r2=0.23, ink=0.03); k.cyl(dk, (s * 2.4, ty, z0 + 0.2), 0.32, 0.4, 12, ink=0.02)
    k.box(red, (0, ty, z0 + 4.3), (6.0, 0.28, 0.32), ink=0.025); k.box(red, (0, ty, z0 + 5.2), (7.4, 0.5, 0.36), ink=0.03)
    for s in (-1, 1):
        k.beam(red, (s * 3.7, ty, z0 + 5.2), (s * 4.4, ty, z0 + 5.55), 0.5, 0.36, 0.03)
    k.box(dk, (0, ty, z0 + 5.55), (7.6, 0.6, 0.12), ink=0.02); k.box(dk, (0, ty - 0.01, z0 + 4.75), (0.7, 0.1, 0.8), ink=0.015)
    # plaza + hall base
    k.box(paving, (0, 21.5, TOP + 0.02), (10.0, 14.0, 0.2), ink=0.03)
    # outer stone wall with tile cap
    for (cx, cy, sx, sy) in ((-14.5, -3.0, 22.0, 0.8), (14.5, -3.0, 22.0, 0.8), (-25.5, 20, 0.8, 50), (25.5, 20, 0.8, 50), (0, 45, 52, 0.8)):
        zt = 1.5 if cy == -3.0 else 2.6
        k.box(stone, (cx, cy, zt / 2 - 0.1), (sx, sy, zt)); k.box(tile, (cx, cy, zt + 0.05), (sx + 0.4, sy + 0.4, 0.18), ink=0.02)
    # main hall: stone base, 3 storeys, black roofs
    hy = 35.0
    k.box(stone, (0, hy, TOP + 0.5), (28.0, 15.0, 1.0)); z1 = TOP + 1.0
    for i in range(4): k.box(step, (0, hy - 7.5 - 0.35 * (4 - i) + 0.3, TOP + 0.25 * (i + 0.5)), (6.0, 0.4, 0.25 * (i + 1)), ink=0.02)
    def storey(z, w, d, h, bays, window_h):
        k.box(wall_p, (0, hy, z + h / 2), (w, d, h))
        for i in range(bays + 1):
            x = -w / 2 + i * w / bays; k.box(wood, (x, hy - d / 2 - 0.05, z + h / 2), (0.42, 0.42, h), ink=0.025)
        for sx in (-1, 1): k.box(wood, (sx * w / 2, hy, z + h / 2), (0.42, d, h), ink=0.025)
        k.box(wood, (0, hy - d / 2 - 0.05, z + h - 0.15), (w + 0.2, 0.4, 0.34), ink=0.025); k.box(wood, (0, hy - d / 2 - 0.05, z + 0.3), (w, 0.3, 0.3), ink=0.02)
        bw = w / bays
        for i in range(bays):
            xc = -w / 2 + (i + 0.5) * bw
            if i == bays // 2 and z == z1: continue
            k.box(win, (xc, hy - d / 2 - 0.02, z + h / 2 + 0.05), (bw - 0.6, 0.06, window_h), ink=0.01)
            for j in range(-3, 4): k.box(dk, (xc + j * (bw - 0.6) / 7, hy - d / 2 - 0.1, z + h / 2 + 0.05), (0.07, 0.07, window_h), ink=0.008)
            for j in (-1, 0, 1): k.box(dk, (xc, hy - d / 2 - 0.1, z + h / 2 + 0.05 + j * window_h / 3.4), (bw - 0.6, 0.07, 0.07), ink=0.008)
    storey(z1, 24.0, 12.0, 3.6, 8, 1.8)
    k.box(dk, (0, hy - 6.1, z1 + 1.6), (3.0, 0.14, 3.2), ink=0.02)                      # open main door
    k.box(C.glow("#ffb25a", 2.0) if night else wall_p, (0, hy - 6.05, z1 + 1.6), (2.4, 0.06, 2.8), ink=0.0)
    hip_roof(k, tile, tile_r, (0, hy, z1 + 3.7), 29.0, 17.0, 3.0, tiers=8, ink=0.05)
    z2 = z1 + 3.7 + 2.2
    storey(z2, 17.0, 8.0, 3.2, 5, 1.5); hip_roof(k, tile, tile_r, (0, hy, z2 + 3.3), 22.0, 12.5, 2.7, tiers=7, ink=0.05)
    z3 = z2 + 3.3 + 2.0
    storey(z3, 10.5, 5.0, 3.0, 3, 1.4); hip_roof(k, tile, tile_r, (0, hy, z3 + 3.1), 15.0, 9.0, 2.6, tiers=6, ink=0.045)
    for s in (-1, 1): k.cyl(dk, (s * 2.4, hy, z3 + 6.35), 0.18, 1.0, 6, r2=0.04, ink=0.02)
    # cherry tree on the left lawn
    cx, cy = -7.5, 6.5; cz = zs(cy) - 0.0
    k.beam(trunk, (cx, cy, cz), (cx + 0.3, cy, cz + 3.0), 0.55, 0.5, 0.03)
    for (dx, dz, tx) in ((-1.3, 1.6, 0.3), (1.6, 1.8, 0.3), (-0.4, 2.0, 0.3), (0.9, 2.6, 0.3)):
        k.beam(trunk, (cx + tx, cy, cz + 2.4), (cx + dx * 1.4 + tx, cy + (dz - 2) * 0.4, cz + 2.4 + dz * 1.3), 0.2, 0.2, 0.02)
    for (dx, dy, dz, r) in ((0, 0, 4.6, 2.2), (-2.2, 0.2, 4.0, 1.7), (2.3, -0.3, 4.2, 1.8), (-1.0, 0.9, 5.4, 1.6), (1.2, 0.6, 5.3, 1.6),
                            (-3.0, -0.2, 3.2, 1.1), (3.1, 0.2, 3.5, 1.2), (0.2, -0.9, 3.5, 1.4)):
        k.blob(pink, (cx + dx, cy + dy, cz + dz), r, (1.1, 1.0, 0.8), ink=0.03)
    # sky: full moon and stars (night)
    if night:
        mp = Vector((-14, 110, 78))
        k.cyl(C.glow("#fff3d2", 4.0), mp, 7.5, 0.5, 28, axis="y", ink=0); k.halo(mp + Vector((0, -2, 0)), 60, "#cfe0ff", 0.6)
        rnd = random.Random(5)
        for _ in range(70):
            a = rnd.uniform(-1.4, 1.4); e = rnd.uniform(0.15, 1.3); R = 190
            p = Vector((math.sin(a) * math.cos(e) * R, math.cos(a) * math.cos(e) * R, math.sin(e) * R))
            k.halo(p, rnd.uniform(0.8, 2.2), "#dfe8ff", 3.0)
        k.light((0, 10, 12), 500, (0.55, 0.65, 1.0), size=2.0)
        for y in (3, 10): k.light((0, y, 3.5 + zs(y)), 250, (1, 0.6, 0.3), size=0.5)
    else:
        k.light((0, 10, 20), 3000, (1, 0.95, 0.85), size=2.0)
    k.meta.update(steps=N, step_rise=RISE, step_run=RUN, stair_top=(0, N * RUN, TOP), hall_front=(0, hy - 6.1, z1), torii=(0, ty, TOP),
                  cams={"base": ((0, -7, 1.7), (0, 24, 9.0), 24), "mid": ((0.0, 5.0, 3.0), (0, 20, 8.0), 28)})
    if world: set_world("night" if night else "day")
    return k.finish()
