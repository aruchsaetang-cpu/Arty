"""Meridian GT-8 for Blender: the same car as car3d/meridian.html (Three.js), rebuilt with bpy from the same design
table, profile curves and loft, so the film and the browser model match.

    import meridian; root, wheels = meridian.build(collection, colour="#9c1418", lights=True)

Car frame of the Three.js model: +X forward, +Y up, +Z = the car's left. Blender/city frame: +y forward, x across
(+x = right), z up, origin on the ground midway between the axles. P() converts."""
import bpy, bmesh, math
from mathutils import Vector, Matrix

def P(x, y, z): return Vector((-z, x, y))

# ------------------------------------------------------------------ design table (metres)
WB, OHF, OHR = 2.723, 0.899, 1.008
TRACK_F, TRACK_R = 1.648, 1.585
XF_AX, XR_AX = WB / 2, -WB / 2
XF, XR = XF_AX + OHF, XR_AX - OHR
def _tire_r(w, ar, rim): return (rim * 0.0254 + 2 * w * ar) / 2
RF, RR = _tire_r(0.245, 0.35, 19), _tire_r(0.305, 0.30, 20)
RIMF, RIMR = 19 * 0.0254 / 2, 20 * 0.0254 / 2

def clamp(v, a, b): return min(b, max(a, v))
def lerp(a, b, t): return a + (b - a) * t
def sstep(t): t = clamp(t, 0, 1); return t * t * (3 - 2 * t)

def curve1d(k):
    k = sorted(k); n = len(k)
    def f(x):
        if x <= k[0][0]: return k[0][1]
        if x >= k[-1][0]: return k[-1][1]
        i = 0
        while x > k[i + 1][0]: i += 1
        p0, p1, p2, p3 = k[max(0, i - 1)], k[i], k[i + 1], k[min(n - 1, i + 2)]
        h = p2[0] - p1[0]; t = (x - p1[0]) / h
        m1 = (p2[1] - p0[1]) / (p2[0] - p0[0]) * h; m2 = (p3[1] - p1[1]) / (p3[0] - p1[0]) * h; t2 = t * t; t3 = t2 * t
        return (2 * t3 - 3 * t2 + 1) * p1[1] + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2[1] + (t3 - t2) * m2
    return f
hwK = curve1d([(XR, 0.86), (XR + 0.12, 0.925), (-2.0, 0.955), (-1.36, 0.967), (-0.7, 0.955), (-0.2, 0.935), (0.4, 0.925), (0.95, 0.94), (1.36, 0.955), (1.85, 0.93), (2.12, 0.86), (XF, 0.75)])
topK = curve1d([(XF, 0.50), (2.18, 0.60), (2.0, 0.665), (1.4, 0.725), (0.85, 0.79), (0.55, 0.95), (0.15, 1.165), (-0.1, 1.222), (-0.42, 1.234), (-0.8, 1.18), (-1.2, 1.065), (-1.6, 1.0), (-2.0, 0.985), (-2.2, 0.99), (-2.31, 0.965), (XR, 0.87)])
beltK = curve1d([(XF, 0.52), (2.1, 0.64), (1.36, 0.80), (0.8, 0.775), (0.2, 0.80), (-0.5, 0.88), (-1.36, 0.95), (-2.0, 0.97), (-2.3, 0.945), (XR, 0.87)])
floorK = curve1d([(XR, 0.30), (XR + 0.15, 0.24), (-1.85, 0.15), (-1.5, 0.115), (1.6, 0.115), (2.0, 0.11), (XF - 0.04, 0.12), (XF, 0.18)])
sillK = curve1d([(XR, 0.37), (-2.0, 0.28), (-1.6, 0.245), (1.6, 0.245), (2.0, 0.26), (XF, 0.30)])
ARCHES = [(XF_AX, RF, 0.36), (XR_AX, RR, 0.385)]
def arch_at(x):
    a = -1
    for (ax, R, r) in ARCHES:
        d = abs(x - ax)
        if d < r: a = max(a, R + math.sqrt(r * r - d * d))
    return a
def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return [0.5 * (2 * p1[i] + (-p0[i] + p2[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2 + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3) for i in (0, 1)]

_SEC = {}
def section(x):
    """Half cross-section at station x: 42 points (lateral, height) from the bottom centre to the roof centre."""
    x = clamp(x, XR, XF); key = round(x, 5)
    if key in _SEC: return _SEC[key]
    hw, top, belt, floor, sill = hwK(x), topK(x), beltK(x), floorK(x), sillK(x)
    c = sstep((top - belt - 0.03) / 0.22); a = arch_at(x); in_arch = a > 0; yF = belt - 0.14
    if in_arch: yF = min(belt - 0.05, max(yF, a + 0.035)); a = min(a, yF - 0.02)
    zin = lerp(0.60, 0.655, sstep((x + 0.5) / 1.0)); pts = []
    def seg(p, q, n, first=False):
        for k in range(0 if first else 1, n + 1): t = k / n; pts.append([lerp(p[0], q[0], t), lerp(p[1], q[1], t)])
    P0, A = [0, floor], [zin, floor]; B = [zin, a if in_arch else floor]; C = [hw - 0.025, a if in_arch else floor]
    D = [hw - 0.025, max(a, sill) if in_arch else sill]
    seg(P0, A, 3, True); seg(A, B, 3); seg(B, C, 3); seg(C, D, 2)
    P3, P4 = [hw, yF], [hw - 0.035, belt]; P5 = [lerp(hw - 0.10, 0.79, c), belt + 0.012]; P6 = [lerp(hw * 0.5, 0.565, c), top - lerp(0.01, 0.05, c)]; P7 = [0, top]
    ctl = [[D[0], D[1] - (P3[1] - D[1])], D, P3, P4, P5, P6, P7, [-P6[0], P6[1]]]
    for k, cnt in enumerate((4, 5, 5, 9, 7)):
        for q in range(1, cnt + 1): pts.append(_cr(ctl[k], ctl[k + 1], ctl[k + 2], ctl[k + 3], q / cnt))
    e = 0.17; d = min(XF - x, x - XR)
    if d < e:
        r = e - math.sqrt(max(0, e * e - (e - d) ** 2)); yc, hh = (floor + top) / 2, (top - floor) / 2
        sz, sy = (hw - 0.6 * r) / hw, (hh - 0.45 * r) / hh
        for p in pts: p[0] *= sz; p[1] = yc + (p[1] - yc) * sy
    s = dict(pts=pts, floor=floor, top=top); _SEC[key] = s; return s

def ring(x, j):
    """Body surface point at station x, ring index j (0..82, 0-41 = left side, 41-82 = right), car frame."""
    s = section(x); j = clamp(j, 0, 82); side, t = (1, j) if j <= 41 else (-1, 82 - j)
    i = min(40, int(math.floor(t))); f = t - i; p, q = s["pts"][i], s["pts"][i + 1]
    return (clamp(x, XR, XF), lerp(p[1], q[1], f), side * lerp(p[0], q[0], f))
def ring_n(x, j):
    a, b = Vector(ring(x - 0.003, j)), Vector(ring(x + 0.003, j)); c, d = Vector(ring(x, j - 0.04)), Vector(ring(x, j + 0.04))
    n = (b - a).cross(d - c)
    return n.normalized() * (1 if _WIND > 0 else -1)
_WIND = (Vector(ring(0.05, 15)) - Vector(ring(0, 15))).cross(Vector(ring(0.05, 16)) - Vector(ring(0, 15))).z

DX0, DX1, GW0, GW1, GS0, EG0 = -0.30, 0.92, 0.15, 0.82, -0.62, -1.55
def jA(x): return 25 + 9 * clamp((GW1 - x) / (GW1 - GW0), 0, 1)
def stations():
    s = set()
    x = XR
    while x <= XF: s.add(round(x, 5)); x += 0.034
    for k in range(17): u = k / 16; s.add(round(XF - 0.22 * u * u, 5)); s.add(round(XR + 0.22 * u * u, 5))
    for (ax, R, r) in ARCHES:
        for k in range(-14, 15): s.add(round(ax + (r - 0.0015) * math.sin(k / 14 * math.pi / 2), 5))
        s.add(round(ax - r - 0.003, 5)); s.add(round(ax + r + 0.003, 5))
    for v in (XR, XF, DX0, DX1, GW0, GW1, GS0, EG0, 0.70, GS0 - 0.06): s.add(round(v, 5))
    return sorted(v for v in s if XR - 1e-9 <= v <= XF + 1e-9)

def cell_mat(x0, x1, j):
    """Material slot of one body cell: 0 paint, 1 cladding, 2 glass, 3 gloss black."""
    ih = j if j < 41 else 81 - j; xm = (x0 + x1) / 2
    if ih < 9: return 1
    if GW0 <= xm <= GW1:                                   # windshield, A-pillars, front of the side glass
        ja = jA(xm)
        if ih >= ja + 0.5: return 2
        if ih >= ja - 0.9: return 3
        if 25 <= ih and xm <= 0.70: return 2
        return 0
    if GS0 <= xm < GW0:
        if 25 <= ih < 32: return 2
        if ih >= 32: return 3
    if EG0 <= xm < GS0 - 0.06 and ih >= 37: return 2
    return 0

# ------------------------------------------------------------------ materials
def _principled(name, col, rough, metal=0.0, coat=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    c = Vector(int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)); c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    b.inputs["Base Color"].default_value = (*c, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if coat: b.inputs["Coat Weight"].default_value = coat; b.inputs["Coat Roughness"].default_value = 0.025
    if emit:
        e = Vector(int(emit[i:i + 2], 16) / 255 for i in (1, 3, 5))
        b.inputs["Emission Color"].default_value = (*e, 1); b.inputs["Emission Strength"].default_value = strength
    return m
def materials(colour):
    return dict(paint=_principled(f"meridian_paint_{colour}", colour, 0.3, 0.55, 1.0),
                clad=_principled("meridian_clad", "#0d0e10", 0.85),
                glass=_principled("meridian_glass", "#06090d", 0.02, 0.0, 1.0),
                black=_principled("meridian_gloss_black", "#060708", 0.15, 0.1, 0.9),
                chrome=_principled("meridian_dark_chrome", "#2a2d32", 0.22, 1.0),
                head=_principled("meridian_headlamp", "#dfe8f0", 0.08, 0.3, 0, "#ffffff", 12.0),
                drl=_principled("meridian_drl", "#ffffff", 0.2, 0, 0, "#e9f3ff", 9.0),
                tail=_principled("meridian_tail", "#2b0003", 0.15, 0, 0, "#ff1020", 6.0),
                amber=_principled("meridian_amber", "#3b2400", 0.2, 0, 0, "#ffa11a", 0.0),
                grille=_principled("meridian_grille", "#0a0b0d", 0.6, 0.3),
                carbon=_principled("meridian_carbon", "#141619", 0.35, 0.4),
                tyre=_principled("meridian_tyre", "#121315", 0.9),
                rim=_principled("meridian_rim", "#c4c8cd", 0.28, 1.0),
                rimface=_principled("meridian_rim_face", "#6b7178", 0.3, 1.0),
                disc=_principled("meridian_disc", "#8a8e93", 0.42, 0.95),
                caliper=_principled("meridian_caliper", "#f2b51e", 0.38, 0.2),
                plate=_principled("meridian_plate", "#eef0ea", 0.6))

# ------------------------------------------------------------------ mesh helpers
def _mesh(name, coll, verts, faces, mats, face_mats=None, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces)
    for m in mats: me.materials.append(m)
    if face_mats:
        me.polygons.foreach_set("material_index", face_mats)
    me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons)); me.update()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    if parent: ob.parent = parent
    return ob

def _quad(f, a, b, c, d):
    f.append((a, b, c, d) if _WIND > 0 else (a, d, c, b))

def patch(name, coll, x0, x1, lo, hi, mat, off, root, nx=None, nj=8):
    nx = nx or max(2, int((x1 - x0) / 0.015)); V, F = [], []
    for a in range(nx + 1):
        u = a / nx; x = lerp(x0, x1, u); l, h = lo(x), hi(x)
        for b in range(nj + 1):
            j = lerp(l, h, b / nj); p = Vector(ring(x, j)) + ring_n(x, j) * off; V.append(P(*p))
    for a in range(nx):
        for b in range(nj):
            i0, i1 = a * (nj + 1) + b, (a + 1) * (nj + 1) + b; _quad(F, i0, i1, i1 + 1, i0 + 1)
    return _mesh(name, coll, V, F, [mat], parent=root)

def half(lo, hi, side):
    return (lo, hi) if side > 0 else ((lambda x: 82 - hi(x)), (lambda x: 82 - lo(x)))

def lathe(prof, seg=48):
    """Profile [(radius, axial)] revolved about the car-frame Z axis (the wheel axle): car-frame verts, quads."""
    V, F = [], []; n = len(prof)
    for s in range(seg):
        a = 2 * math.pi * s / seg
        for (r, z) in prof: V.append((r * math.cos(a), r * math.sin(a), z))
    for s in range(seg):
        for i in range(n - 1):
            a0, a1 = s * n + i, ((s + 1) % seg) * n + i; F.append((a0, a1, a1 + 1, a0 + 1))
    return V, F

# ------------------------------------------------------------------ build
def build(coll, colour="#9c1418", lights=True, name="meridian"):
    M = materials(colour)
    root = bpy.data.objects.new(name, None); coll.objects.link(root)
    X = stations()
    # body shell: separate vertex strips at the sharp arch edges, smooth inside each strip
    V, F, FM = [], [], []
    for (ja, jb) in ((0, 3), (3, 6), (6, 9), (9, 11), (11, 71), (71, 73), (73, 76), (76, 79), (79, 82)):
        base, nj = len(V), jb - ja + 1
        for x in X:
            for j in range(ja, jb + 1): V.append(P(*ring(x, j)))
        for s in range(len(X) - 1):
            for j in range(ja, jb):
                i0, i1 = base + s * nj + (j - ja), base + (s + 1) * nj + (j - ja)
                _quad(F, i0, i1, i1 + 1, i0 + 1); FM.append(cell_mat(X[s], X[s + 1], j))
    # end caps (nose fascia, tail panel), fanned from the last rings
    for xc, d in ((XF, 1), (XR, -1)):
        s = section(xc); c = len(V); V.append(P(xc + d * 0.012, (s["floor"] + s["top"]) / 2, 0)); r0 = len(V)
        for j in range(83): V.append(P(*ring(xc, j)))
        for j in range(82):
            tri = (c, r0 + j, r0 + j + 1)
            a, b, cc = (Vector(V[i]) for i in tri)
            if (b - a).cross(cc - a).y * d < 0: tri = (c, r0 + j + 1, r0 + j)
            F.append(tri); FM.append(0)
    body = _mesh(name + "_body", coll, V, F, [M["paint"], M["clad"], M["glass"], M["black"]], FM, parent=root)
    bpy.context.view_layer.objects.active = body
    parts = [body]
    # lamps on the body surface
    for side in (1, -1):
        hx0, hx1 = 1.90, XF - 0.025; u = lambda x: (x - hx0) / (hx1 - hx0)
        lo, hi = (lambda x: 16.4 + 2.2 * u(x)), (lambda x: 20.7 + 0.5 * u(x))
        parts.append(patch(name + "_head_housing", coll, hx0, hx1, *half(lo, hi, side), M["chrome"], 0.0022, root))
        parts.append(patch(name + "_head_lens", coll, hx0 + 0.03, hx1 - 0.02, *half(lambda x: lo(x) + 1.2, lambda x: hi(x) - 0.7, side),
                           M["head"] if lights else M["chrome"], 0.0036, root))
        parts.append(patch(name + "_drl", coll, hx0 + 0.01, hx1 - 0.01, *half(lambda x: hi(x) - 0.55, lambda x: hi(x) - 0.15, side), M["drl"], 0.004, root, nj=2))
        tx0, tx1 = XR + 0.018, XR + 0.34; ut = lambda x: (x - tx0) / (tx1 - tx0)
        tlo, thi = (lambda x: 17.6 + 1.5 * ut(x)), (lambda x: 21.0 - 0.4 * ut(x))
        parts.append(patch(name + "_tail_housing", coll, tx0, tx1, *half(tlo, thi, side), M["chrome"], 0.0022, root))
        parts.append(patch(name + "_tail_lamp", coll, tx0 + 0.01, tx1 - 0.02, *half(lambda x: tlo(x) + 0.5, lambda x: thi(x) - 0.25, side), M["tail"], 0.0036, root))
        ui = lambda x: (x + 1.02) / 0.66
        parts.append(patch(name + "_side_intake", coll, -1.02, -0.36, *half(lambda x: 13.2 + 3.6 * ui(x), lambda x: 19.3, side), M["grille"], 0.0018, root))
        parts.append(patch(name + "_door_handle", coll, -0.22, -0.08, *half(lambda x: 17.9, lambda x: 18.55, side), M["chrome"], 0.003, root, nj=2))
        # door seams (thin dark lines just proud of the paint)
        for (a, b, lo_, hi_) in ((DX0, DX0 + 0.006, lambda x: 11.1, lambda x: 19.9), (DX1 - 0.006, DX1, lambda x: 11.1, lambda x: 19.9),
                                 (DX0, DX1, lambda x: 19.75, lambda x: 19.95)):
            parts.append(patch(name + "_seam", coll, a, b, *half(lo_, hi_, side), M["clad"], 0.0012, root, nx=4 if b - a < 0.05 else None, nj=2))
        # mirror on a stalk
        mp, mn = Vector(ring(0.66, 20.4 if side > 0 else 61.6)), ring_n(0.66, 20.4 if side > 0 else 61.6)
        hc = mp + mn * 0.075 + Vector((-0.05, 0.05, 0))
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
        for v in bm.verts: v.co = P(hc.x + v.co.x * 0.105, hc.y + v.co.y * 0.047, hc.z + v.co.z * 0.07)
        me = bpy.data.meshes.new(name + "_mirror"); bm.to_mesh(me); bm.free(); me.materials.append(M["paint"])
        for pl in me.polygons: pl.use_smooth = True
        mo = bpy.data.objects.new(name + "_mirror", me); coll.objects.link(mo); mo.parent = root; parts.append(mo)
        st = [P(*mp), P(*(mp + Vector((-0.02, 0.03, side * 0.03)))), P(*(hc + Vector((0.02, -0.015, -side * 0.035))))]
        cu = bpy.data.curves.new(name + "_stalk", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.009; sp = cu.splines.new("POLY"); sp.points.add(len(st) - 1)
        for i, p in enumerate(st): sp.points[i].co = (*p, 1)
        so = bpy.data.objects.new(name + "_stalk", cu); cu.materials.append(M["carbon"]); coll.objects.link(so); so.parent = root; parts.append(so)
    # fascia: front grille + splitter, rear plate, diffuser face, light bars, exhaust tips, diffuser fins, lip spoiler
    sF, sR = section(XF), section(XR)
    def cap_quad(nm, x, d, z0, z1, y0, y1, mat, inset=0.0):
        V = [P(x, y0, z0), P(x, y0, z1), P(x, y1, z1 - inset), P(x, y1, z0 + inset)]
        f = [(0, 1, 2, 3)] if d < 0 else [(0, 3, 2, 1)]
        return _mesh(nm, coll, V, f, [mat], smooth=False, parent=root)
    parts.append(cap_quad(name + "_grille", XF + 0.014, 1, -0.50, 0.50, sF["floor"] + 0.10, sF["floor"] + 0.19, M["grille"], 0.06))
    parts.append(cap_quad(name + "_plate", XR - 0.014, -1, -0.25, 0.25, 0.505, 0.615, M["plate"]))
    parts.append(cap_quad(name + "_diffuser_face", XR - 0.014, -1, -0.56, 0.56, sR["floor"] + 0.08, sR["floor"] + 0.18, M["grille"], 0.06))
    for z0, z1 in ((0.40, 0.70), (-0.70, -0.40)):
        parts.append(cap_quad(name + "_tail_bar", XR - 0.015, -1, z0, z1, 0.70, 0.735, M["tail"]))
    def box(nm, c, size, mat, rz=0.0):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(P(*c)) @ Matrix.Rotation(rz, 4, "X") @ Matrix.Diagonal((size[2], size[0], size[1], 1)))
        me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free(); me.materials.append(mat)
        o = bpy.data.objects.new(nm, me); coll.objects.link(o); o.parent = root; parts.append(o); return o
    box(name + "_splitter", (XF - 0.10, 0.11, 0), (0.14, 0.016, 1.22), M["carbon"])
    for k in range(-2, 3): box(name + "_fin", (XR + 0.24, 0.21, k * 0.22), (0.46, 0.09, 0.008), M["carbon"], 0.28)
    for z in (0.50, 0.62, -0.50, -0.62):
        Vt, Ft = lathe([(0.040, 0.0), (0.046, 0.004), (0.046, 0.10), (0.040, 0.104), (0.036, 0.02)], 20)
        Vt = [P(XR + 0.06 - zz, 0.43 + yy, z + xx) for (xx, yy, zz) in Vt]
        parts.append(_mesh(name + "_exhaust", coll, Vt, Ft, [M["chrome"]], parent=root))
    # lip spoiler: airfoil extruded across the deck
    af = [(0, 0), (0.05, 0.022), (0.12, 0.03), (0.22, 0.006), (0.22, -0.004), (0.12, 0.0), (0.04, -0.003)]
    xs, ys = XR + 0.09, topK(XR + 0.20) + 0.045; Vs, Fs = [], []
    for zz in (-0.78, 0.78):
        for (ax, ay) in af: Vs.append(P(xs + ax * math.cos(0.1) + ay * math.sin(0.1), ys + ay - ax * 0.1, zz))
    n = len(af)
    for i in range(n): Fs.append((i, (i + 1) % n, n + (i + 1) % n, n + i))
    Fs.append(tuple(range(n))); Fs.append(tuple(range(2 * n - 1, n - 1, -1)))
    parts.append(_mesh(name + "_spoiler", coll, Vs, Fs, [M["carbon"]], smooth=False, parent=root))
    # wheels: tyre, rim barrel, ten spokes, hub, drilled disc, caliper (the caliper does not spin)
    wheels = []
    for (ax, side, front) in ((XF_AX, 1, True), (XF_AX, -1, True), (XR_AX, 1, False), (XR_AX, -1, False)):
        R, w, rimR, track = (RF, 0.245, RIMF, TRACK_F) if front else (RR, 0.305, RIMR, TRACK_R); hw = w / 2
        hub = bpy.data.objects.new(f"{name}_wheel", None); coll.objects.link(hub); hub.parent = root
        hub.location = P(ax, R, side * track / 2)
        prof = [(rimR + 0.004, -hw + 0.014), (rimR + 0.022, -hw - 0.002), (lerp(rimR, R, 0.5), -hw - 0.012), (R - 0.028, -hw - 0.006),
                (R - 0.009, -hw + 0.008), (R, -hw + 0.03)]
        for gz in (-0.22, 0, 0.22): c = gz * w; prof += [(R, c - 0.009), (R - 0.007, c - 0.006), (R - 0.007, c + 0.006), (R, c + 0.009)]
        prof += [(R, hw - 0.03), (R - 0.009, hw - 0.008), (R - 0.028, hw + 0.006), (lerp(rimR, R, 0.5), hw + 0.012), (rimR + 0.022, hw + 0.002), (rimR + 0.004, hw - 0.014)]
        def add(nm, verts, faces, mat, smooth=True):
            vv = [P(x, y, side * z) for (x, y, z) in verts]
            ff = [tuple(reversed(f)) for f in faces] if side < 0 else faces
            o = _mesh(nm, coll, vv, ff, [mat], smooth=smooth, parent=hub); return o
        tv, tf = lathe(prof, 56); add(name + "_tyre", tv, tf, M["tyre"])
        bv, bf = lathe([(rimR - 0.035, -hw + 0.01), (rimR - 0.012, -hw + 0.006), (rimR - 0.014, hw - 0.02), (rimR + 0.006, hw - 0.004),
                        (rimR + 0.012, hw + 0.004), (rimR - 0.006, hw + 0.008), (rimR - 0.02, hw - 0.004)], 48)
        add(name + "_rim", bv, bf, M["rim"])
        sv, sf = [], []
        for k in range(5):
            for sg in (-1, 1):
                a = k * 2 * math.pi / 5 + sg * 0.14; ca, sa = math.cos(a), math.sin(a)
                shape = [(0.058, -0.017), (rimR - 0.012, -0.008), (rimR - 0.006, 0.0), (rimR - 0.012, 0.008), (0.058, 0.017)]
                b0 = len(sv)
                for zz in (hw - 0.07, hw - 0.05):
                    for (r_, t_) in shape:
                        zc = zz + (r_ - 0.06) * 0.16           # dished: the spokes lean out toward the rim
                        sv.append((r_ * ca - t_ * sa, r_ * sa + t_ * ca, zc))
                m = len(shape)
                sf.append(tuple(range(b0 + m, b0 + 2 * m))); sf.append(tuple(range(b0 + m - 1, b0 - 1, -1)))
                for i in range(m - 1): sf.append((b0 + i, b0 + i + 1, b0 + m + i + 1, b0 + m + i))
                sf.append((b0 + m - 1, b0, b0 + m, b0 + 2 * m - 1))
        add(name + "_spokes", sv, sf, M["rimface"], smooth=False)
        hv, hf = lathe([(0.0, hw - 0.03), (0.035, hw - 0.03), (0.064, hw - 0.05), (0.07, hw - 0.08)], 24); add(name + "_hub", hv, hf, M["rimface"])
        Rd = 0.19 if front else 0.18
        dv, df = lathe([(0.075, -0.052), (Rd, -0.052), (Rd, -0.018), (0.075, -0.018), (0.075, -0.052)], 48); add(name + "_disc", dv, df, M["disc"])
        cv, cf = [], []; a0, a1, n_ = (2.0, 2.9, 10) if front else (0.25, 1.15, 10)
        for zz in (-0.07, 0.0):
            for i in range(n_ + 1): a = lerp(a0, a1, i / n_); cv.append(((Rd + 0.012) * math.cos(a), (Rd + 0.012) * math.sin(a), zz))
            for i in range(n_ + 1): a = lerp(a1, a0, i / n_); cv.append(((Rd - 0.06) * math.cos(a), (Rd - 0.06) * math.sin(a), zz))
        m = 2 * (n_ + 1)
        cf.append(tuple(range(m))); cf.append(tuple(range(2 * m - 1, m - 1, -1)))
        for i in range(m): cf.append((i, (i + 1) % m, m + (i + 1) % m, m + i))
        cal = _mesh(name + "_caliper", coll, [P(ax + x, R + y, side * (track / 2 + z * 1.0)) for (x, y, z) in cv],
                    [tuple(reversed(f)) for f in cf] if side < 0 else cf, [M["caliper"]], smooth=False, parent=root)
        parts.append(cal); wheels.append((hub, R))
    for o in parts:
        if o.type == "MESH": o.visible_shadow = True
    return root, wheels

def drive(root, wheels, keys, front_light=None):
    """Key the car root along straight segments [(frame, (x, y), heading_deg)] (linear) and spin the wheels by the
    distance travelled (angle = -distance / radius about the axle)."""
    prev = None; dist = 0.0
    for (f, (x, y), hd) in keys:
        if prev: dist += math.hypot(x - prev[0], y - prev[1])
        root.location = (x, y, 0); root.rotation_euler = (0, 0, math.radians(hd))
        root.keyframe_insert("location", frame=f); root.keyframe_insert("rotation_euler", index=2, frame=f)
        for hub, R in wheels:
            hub.rotation_euler = (-dist / R, 0, 0); hub.keyframe_insert("rotation_euler", index=0, frame=f)
        prev = (x, y)
    for ob in [root] + [h for h, _ in wheels]:
        ad = ob.animation_data
        if ad and ad.action:
            from bpy_extras import anim_utils
            cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
            for fc in cb.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
