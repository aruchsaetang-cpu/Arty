"""High-detail convenience store for the "shop" shot (the one interior the camera clearly sees), dressed from the user's
store references: a wall of lit glass-door drink coolers, packed shelving and a centre gondola with price strips,
a busy counter with the cigarette wall and a lit menu board, big white floor tiles, a grid ceiling with LED panels,
hanging aisle signs. Products are thousands of small boxes, bottles, cans and cups merged into a few meshes and
coloured per product (one material reads the colour attribute), so the detail costs little.

    exec'd by film_sets.py: shop_dressing(coll, x0, x1, y0, y1, z0, z1, avoid)   (needs C = lookdev.city)"""
import random as _r
import bmesh as _bm
from mathutils import Matrix as _Mx, Vector as _V

_PAL = ["#e63b2e", "#f5c518", "#1f8f4a", "#2b6fd6", "#ff7a1a", "#8a3fd1", "#e8e4da", "#d81e5b", "#18b7c9", "#3a3a3e",
        "#ffd84a", "#6bc23a", "#f2f2f0", "#c9132f", "#0e6b3a", "#ffb2c8", "#7b4a2a", "#202a6e"]

def _hexrgb(h):
    c = C.lin(h); return (c[0], c[1], c[2], 1.0)

def _prod_mat(name, emit=0.12, rough=0.4, alpha=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N_, L_ = nt.nodes, nt.links
    b = N_["Principled BSDF"]; at = N_.new("ShaderNodeAttribute"); at.attribute_name = "Col"
    L_.new(at.outputs["Color"], b.inputs["Base Color"]); L_.new(at.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = emit; b.inputs["Roughness"].default_value = rough
    if alpha is not None:
        b.inputs["Transmission Weight"].default_value = alpha; b.inputs["Roughness"].default_value = 0.08
    return m

class _Batch:
    """Boxes and cylinders with a colour per piece, merged into one mesh."""
    def __init__(self, name, mat):
        self.bm = _bm.new(); self.col = self.bm.loops.layers.color.new("Col"); self.name, self.mat = name, mat
    def _paint(self, faces, rgba):
        for f in faces:
            for l_ in f.loops: l_[self.col] = rgba
    def box(self, c, size, rgba, rz=0.0):
        r = _bm.ops.create_cube(self.bm, size=1.0, matrix=_Mx.Translation(c) @ _Mx.Rotation(rz, 4, "Z") @ _Mx.Diagonal((*size, 1)))
        self._paint({f for v in r["verts"] for f in v.link_faces}, rgba)
    def cyl(self, c, r1, r2, h, rgba, seg=10):
        r = _bm.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=h, matrix=_Mx.Translation(c))
        self._paint({f for v in r["verts"] for f in v.link_faces}, rgba)
    def done(self, coll):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free(); me.materials.append(self.mat)
        ob = bpy.data.objects.new(self.name, me); coll.objects.link(ob); return ob

def shop_dressing(coll, x0, x1, y0, y1, z0, z1, avoid=()):
    rng = _r.Random(77)
    W = y1 - y0; xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    PROD = _prod_mat("shop_products", 0.14); BOTTLE = _prod_mat("shop_bottles", 0.2, alpha=0.35)
    FIX = _prod_mat("shop_fixtures", 0.0, 0.35)                       # shelving, frames, counter (coloured per piece)
    prod, bott, fix = _Batch("shop_goods", PROD), _Batch("shop_drinks", BOTTLE), _Batch("shop_fixtures", FIX)
    WHITE, STEEL, DARK, WOOD = _hexrgb("#eceae4"), _hexrgb("#b8bcc2"), _hexrgb("#1c1e22"), _hexrgb("#b98b5c")
    TAG, TAG_Y = _hexrgb("#f4f4f0"), _hexrgb("#ffd21f")
    def pc(): return _hexrgb(rng.choice(_PAL))
    def clear(x, y, r=0.55): return all((_V((x, y)) - _V(a)).length > r for a in avoid)
    # ---- floor: big white tiles, glossy; ceiling: grid tiles with LED panels
    fm = bpy.data.materials.new("shop_tiles"); g = C.G(fm); b = g.bsdf()
    tc = g.n("ShaderNodeTexCoord"); br = g.n("ShaderNodeTexBrick", Scale=1.66, **{"Mortar Size": 0.008, "Bias": 0.0})
    br.inputs["Color1"].default_value = C.lin("#e9e7e1"); br.inputs["Color2"].default_value = C.lin("#dedbd3")
    br.inputs["Mortar"].default_value = C.lin("#9a978f"); br.inputs["Row Height"].default_value = 0.5; br.offset = 0.0
    g.ln(tc.outputs["Object"], br.inputs["Vector"]); g.ln(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.12
    _box(coll, "shop_floor", (xm, ym, z0 + 0.02), (x1 - x0, W, 0.04), fm)
    _box(coll, "shop_ceiling", (xm, ym, z1 - 0.02), (x1 - x0, W, 0.04), C.principled("shop_ceil", "#d9d7d1", 0.8))
    LED = _emit("shop_led", "#f6f8ff", 7.0)
    for gx in (x0 + 0.9, xm + 0.3, x1 - 0.9):
        for gy in (y0 + W * 0.25, y0 + W * 0.75):
            _box(coll, "shop_led", (gx, gy, z1 - 0.045), (0.6, 1.2, 0.02), LED)
    for k in range(int((x1 - x0) / 0.6) + 1):                        # ceiling grid
        fix.box((x0 + k * 0.6, ym, z1 - 0.05), (0.02, W, 0.015), _hexrgb("#bdbab3"))
    for k in range(int(W / 0.6) + 1):
        fix.box((xm, y0 + k * 0.6, z1 - 0.05), (x1 - x0, 0.02, 0.015), _hexrgb("#bdbab3"))
    _box(coll, "shop_wall_back", (x1 - 0.03, ym, (z0 + z1) / 2), (0.06, W, z1 - z0), C.principled("shop_wall", "#ebe8e1", 0.8))
    _box(coll, "shop_wall_side", (xm, y1 - 0.03, (z0 + z1) / 2), (x1 - x0, 0.06, z1 - z0), C.principled("shop_wall", "#ebe8e1", 0.8))
    # ---- back wall: glass-door drink coolers, lit inside, bottles and cans in rows
    cz0, cz1 = z0 + 0.12, z0 + 2.15; doors = max(3, int((W - 0.6) / 0.72)); dw = (W - 0.6) / doors; cx = x1 - 0.36
    GLOW = _emit("cooler_glow", "#f2f7ff", 3.0); DOOR = bpy.data.materials.new("cooler_door"); g2 = C.G(DOOR)
    tr = g2.n("ShaderNodeBsdfTransparent"); gl = g2.n("ShaderNodeBsdfGlossy", Roughness=0.03); lw = g2.n("ShaderNodeLayerWeight", Blend=0.15)
    mx = g2.n("ShaderNodeMixShader"); g2.ln(lw.outputs["Fresnel"], mx.inputs[0]); g2.ln(tr.outputs[0], mx.inputs[1]); g2.ln(gl.outputs[0], mx.inputs[2])
    g2.ln(mx.outputs[0], g2.out.inputs[0])
    _box(coll, "cooler_back", (x1 - 0.08, ym, (cz0 + cz1) / 2), (0.02, W - 0.6, cz1 - cz0), GLOW)
    for d in range(doors):
        yd0 = y0 + 0.3 + d * dw
        fix.box((cx - 0.3, yd0, (cz0 + cz1) / 2), (0.06, 0.05, cz1 - cz0), DARK)                       # mullions
        _box(coll, "cooler_door", (cx - 0.31, yd0 + dw / 2, (cz0 + cz1) / 2), (0.01, dw - 0.06, cz1 - cz0 - 0.08), DOOR)
        fix.box((cx - 0.34, yd0 + dw - 0.09, (cz0 + cz1) / 2), (0.025, 0.025, 0.7), STEEL)            # handle
        for s in range(5):
            sz = cz0 + 0.08 + s * (cz1 - cz0 - 0.1) / 5
            fix.box((cx, yd0 + dw / 2, sz), (0.5, dw - 0.06, 0.012), _hexrgb("#d9e2ea"))
            fix.box((cx - 0.26, yd0 + dw / 2, sz + 0.012), (0.01, dw - 0.06, 0.03), TAG)
            kind = rng.choice(["bottle", "bottle", "can", "tall"]); col = pc(); cap = pc()
            n = int((dw - 0.1) / (0.07 if kind != "can" else 0.075))
            for i in range(n):
                y = yd0 + 0.07 + i * (dw - 0.12) / max(1, n - 1)
                if rng.random() < 0.06: continue                                           # a gap where one was taken
                if rng.random() < 0.2: col = pc()
                for row in (0.0, 0.1):
                    xx = cx - 0.18 + row
                    if kind == "can":
                        bott.cyl((xx, y, sz + 0.07), 0.032, 0.032, 0.125, col)
                    else:
                        h = 0.27 if kind == "bottle" else 0.32
                        bott.cyl((xx, y, sz + 0.012 + h / 2), 0.03, 0.03, h * 0.78, col)
                        bott.cyl((xx, y, sz + 0.012 + h * 0.86), 0.03, 0.015, h * 0.16, col)
                        prod.cyl((xx, y, sz + 0.012 + h * 0.97), 0.015, 0.015, h * 0.06, cap)
    fix.box((cx - 0.3, y0 + 0.3 + doors * dw, (cz0 + cz1) / 2), (0.06, 0.05, cz1 - cz0), DARK)
    fix.box((cx - 0.3, ym, cz1 + 0.06), (0.08, W - 0.6, 0.12), DARK)                                    # header
    # ---- shelving units: wall run along y1, a centre gondola, the wall behind the counter
    def shelving(xa, xb, yc, depth, height, face, levels=5, small=False):
        """Shelf run from xa to xb at y=yc (face=+1 opens toward +y, -1 toward -y, 0 = double-sided gondola)."""
        L = xb - xa; xmid = (xa + xb) / 2; sides = (1, -1) if face == 0 else (face,)
        fix.box((xmid, yc, z0 + 0.06), (L, depth, 0.12), WHITE)
        fix.box((xmid, yc if face == 0 else yc - face * depth / 2, z0 + height / 2), (L, 0.03, height), WHITE)   # back panel
        for k in range(int(L / 0.9) + 1):
            fix.box((xa + k * L / max(1, int(L / 0.9)), yc, z0 + height / 2), (0.03, depth, height), STEEL)
        for s in range(levels):
            sz = z0 + 0.14 + s * (height - 0.2) / levels
            for sd in sides:
                yo = yc + sd * depth / 4 if face == 0 else yc
                dp = depth / 2 if face == 0 else depth
                fix.box((xmid, yo, sz), (L, dp, 0.018), WHITE)
                fix.box((xmid, yo + sd * dp / 2, sz + 0.02), (L, 0.006, 0.035), TAG_Y if rng.random() < 0.3 else TAG)
                x = xa + 0.03; band_col = pc()
                while x < xb - 0.06:
                    if rng.random() < 0.15: band_col = pc()
                    w = rng.uniform(0.05, 0.11) if small else rng.uniform(0.07, 0.17)
                    h = rng.uniform(0.08, 0.16) if small else rng.uniform(0.12, (height - 0.2) / levels - 0.05)
                    d_ = dp * rng.uniform(0.55, 0.9)
                    if rng.random() < 0.04: x += w; continue
                    kind = rng.random()
                    cy_ = yo + sd * (dp / 2 - d_ / 2 - 0.02)
                    if kind < 0.7:                                                  # boxed goods with a label band
                        prod.box((x + w / 2, cy_, sz + 0.009 + h / 2), (w * 0.95, d_, h), band_col)
                        prod.box((x + w / 2, cy_ + sd * (d_ / 2 + 0.002), sz + 0.009 + h * 0.62), (w * 0.85, 0.004, h * 0.25),
                                 _hexrgb(rng.choice(["#ffffff", "#ffe066", "#111111", "#ff3b30"])))
                    elif kind < 0.85:                                               # cup noodles / tubs, stacked
                        for st in range(2):
                            prod.cyl((x + w / 2, cy_, sz + 0.06 + st * 0.105), 0.045, 0.036, 0.1, band_col)
                    else:                                                           # bottles (sauces, shampoo)
                        for q in range(max(1, int(w / 0.055))):
                            bott.cyl((x + 0.03 + q * 0.055, cy_, sz + 0.1), 0.024, 0.024, 0.18, band_col)
                    x += w
    # wall run along the far side wall
    shelving(x0 + 1.4, x1 - 0.8, y1 - 0.3, 0.45, 2.0, -1)
    # centre gondola, slid along y until it clears the customers
    gy = ym + 0.2
    for dy in (0.0, 0.5, -0.5, 1.0, -1.0, 1.5, -1.5):
        if all(clear(x, ym + dy, 0.75) for x in (9.7, 10.3, 10.9)): gy = ym + dy; break
    shelving(9.6, x1 - 0.85, gy, 0.7, 1.45, 0, levels=4)
    _sign(coll, "음료", (x1 - 0.7, ym, z1 - 0.38)); _sign(coll, "과자 · 라면", (10.2, gy, z1 - 0.42)); _sign(coll, "생활용품", (x0 + 2.6, y1 - 0.5, z1 - 0.42))
    # ---- the counter: wood front, white top, register, card reader, gum rack, coffee machine; cigarette wall behind
    ccx, ccy = 8.55, y0 + 1.0
    fix.box((ccx, ccy, z0 + 0.47), (0.62, 1.6, 0.94), WOOD); fix.box((ccx, ccy, z0 + 0.96), (0.68, 1.66, 0.04), WHITE)
    fix.box((ccx, ccy - 0.3, z0 + 1.1), (0.3, 0.34, 0.2), DARK); fix.box((ccx - 0.05, ccy - 0.3, z0 + 1.3), (0.04, 0.3, 0.22), DARK)
    _box(coll, "register_screen", (ccx - 0.075, ccy - 0.3, z0 + 1.3), (0.005, 0.26, 0.17), _emit("register_screen", "#8fd0ff", 2.0))
    fix.box((ccx - 0.2, ccy + 0.25, z0 + 1.02), (0.08, 0.12, 0.06), DARK)                                 # card reader
    for i in range(4):                                                                                      # gum / candy rack
        for j in range(5):
            prod.box((ccx - 0.28, ccy + 0.45 + j * 0.06, z0 + 1.0 + i * 0.055), (0.06, 0.05, 0.045), pc())
    fix.box((ccx + 0.1, ccy + 0.6, z0 + 1.2), (0.32, 0.3, 0.45), _hexrgb("#2a2c30"))                       # coffee machine
    _box(coll, "coffee_panel", (ccx - 0.065, ccy + 0.6, z0 + 1.3), (0.005, 0.2, 0.1), _emit("coffee_panel", "#ffb347", 2.5))
    wall_y = y0 + 0.12; cw0, cw1 = x0 + 0.5, x0 + 2.4
    _box(coll, "cig_back", ((cw0 + cw1) / 2, wall_y, z0 + 1.55), (cw1 - cw0, 0.02, 1.1), _emit("cig_back", "#fff4dc", 1.6))
    for i in range(int((cw1 - cw0) / 0.065)):
        for j in range(9):
            prod.box((cw0 + 0.04 + i * 0.065, wall_y + 0.04, z0 + 1.05 + j * 0.11), (0.055, 0.03, 0.085), pc())
    for j in range(10):
        fix.box(((cw0 + cw1) / 2, wall_y + 0.05, z0 + 1.0 + j * 0.11), (cw1 - cw0, 0.06, 0.008), STEEL)
    _box(coll, "menu_board", ((cw0 + cw1) / 2, wall_y + 0.02, z0 + 2.45), (cw1 - cw0, 0.02, 0.5), _menu_mat())
    # ---- posters on the side wall by the window
    for k, (col, txt) in enumerate((("#ff5a3c", "1+1"), ("#1fb36b", "NEW"))):
        _box(coll, "poster", (x0 + 0.9 + k * 0.8, y1 - 0.065, z0 + 1.9), (0.6, 0.01, 0.8), _emit(f"poster_{k}", col, 1.8))
    for b_ in (prod, bott, fix):
        ob = b_.done(coll); ob.visible_shadow = b_ is not bott
    return coll

def _sign(coll, txt, c):
    """A blue aisle sign hung from the ceiling on two wires, white lettering both sides."""
    BL = C.principled("aisle_sign", "#1f4fa8", 0.4)
    _box(coll, "aisle_sign", c, (0.04, 0.9, 0.26), BL)
    for s in (-1, 1):
        _box(coll, "sign_wire", (c[0], c[1] + s * 0.35, c[2] + 0.3), (0.006, 0.006, 0.34), C.METAL)
        C.text(txt, _Mx.Identity(4), (c[0] + s * 0.025, c[1], c[2]),
               _Mx.Rotation(math.radians(-90 if s < 0 else 90), 4, "Z") @ _Mx.Rotation(math.radians(90), 4, "X"),
               0.12, C.glow("#ffffff", 2.0, name="sign_text"), coll, extrude=0.002)

def _menu_mat():
    m = bpy.data.materials.new("menu_board"); g = C.G(m); e = g.n("ShaderNodeEmission", Strength=2.2)
    tc = g.n("ShaderNodeTexCoord"); sp = g.n("ShaderNodeSeparateXYZ"); g.ln(tc.outputs["Generated"], sp.inputs[0])
    tiles = g.m("MULTIPLY", g.m("GREATER_THAN", g.m("FRACT", g.m("MULTIPLY", sp.outputs[0], 6.0)), 0.06),
                g.m("GREATER_THAN", g.m("FRACT", g.m("MULTIPLY", sp.outputs[2], 2.0)), 0.08))
    wn = g.n("ShaderNodeTexWhiteNoise", _noise_dimensions="3D"); fl = g.n("ShaderNodeVectorMath", _operation="FLOOR")
    mp = g.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (6, 1, 2); g.ln(tc.outputs["Generated"], mp.inputs[0])
    g.ln(mp.outputs[0], fl.inputs[0]); g.ln(fl.outputs[0], wn.inputs["Vector"])
    c = g.mix(tiles, C.lin("#101114"), g.mix(0.45, wn.outputs["Color"], C.lin("#ffe9c4")))
    g.ln(c, e.inputs["Color"]); g.ln(e.outputs[0], g.out.inputs[0]); return m
