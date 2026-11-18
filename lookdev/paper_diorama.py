"""Paper-cutout diorama look-dev for Arty shorts.

Run headless:
    blender -b -P lookdev/paper_diorama.py -- <shot> [scale%]
shots: hook | wide | pivot
Scene units are metres: the diorama is a ~36 cm tabletop miniature,
which is what gives the real-lens miniature depth of field.
"""
import bpy, math, sys, os

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHOT = argv[0] if argv else "wide"
SCALE = int(argv[1]) if len(argv) > 1 else 50
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
os.makedirs(OUT, exist_ok=True)
NIGHT = SHOT == "pivot"

# ---------- palette (Arty: muted risograph, no pure white, no black ink) ----------
PAL = dict(
    cream="#F3E6CC", navy="#23324A", teal="#2E6F73", sea="#3F8C8C", deep="#24566B",
    sage="#8FB3A0", moss="#5E9A86", grass="#2F5A47", mustard="#E3A72F",
    coral="#E8664A", ochre="#D49A4A", clay="#B9773F", skin="#C9825B",
    skin_dk="#A9653F", sky="#BFD9D2", sky_n="#2A3B63", kraft="#C49A6C",
    margin="#FBF4E4", brass="#C9A13B",
)

def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

# ---------- reset ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
col = scn.collection

# ---------- materials ----------
_mats = {}
def paper(hexc, glow=0.0, fibre=1.0):
    key = (hexc, glow, fibre)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"paper_{hexc}_{glow}")
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N["Principled BSDF"]
    tc = N.new("ShaderNodeTexCoord")
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900; nz.inputs["Detail"].default_value = 6
    blot = N.new("ShaderNodeTexNoise"); blot.inputs["Scale"].default_value = 60; blot.inputs["Detail"].default_value = 2
    L.new(tc.outputs["Object"], nz.inputs["Vector"]); L.new(tc.outputs["Object"], blot.inputs["Vector"])
    # risograph-ish uneven ink density: base colour * (0.9..1.04)
    mr = N.new("ShaderNodeMapRange"); mr.inputs[3].default_value = 0.9; mr.inputs[4].default_value = 1.04
    L.new(blot.outputs["Fac"], mr.inputs[0])
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    mul.inputs[6].default_value = lin(hexc)
    cmb = N.new("ShaderNodeCombineColor")
    for i in range(3):
        L.new(mr.outputs[0], cmb.inputs[i])
    L.new(cmb.outputs[0], mul.inputs[7])
    L.new(mul.outputs[2], bsdf.inputs["Base Color"])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25 * fibre
    bump.inputs["Distance"].default_value = 0.0003
    L.new(nz.outputs["Fac"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.92
    for name, v in (("Sheen Weight", 0.35), ("Specular IOR Level", 0.25)):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = v
    if glow:
        bsdf.inputs["Emission Color"].default_value = lin(hexc)
        bsdf.inputs["Emission Strength"].default_value = glow
    _mats[key] = m
    return m

def metal(hexc):
    m = bpy.data.materials.new("brass"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexc)
    b.inputs["Metallic"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.32
    return m
BRASS = metal(PAL["brass"])

# ---------- geometry helpers ----------
def ellipse(cx, cz, rx, rz, n=48, a0=0, a1=2 * math.pi):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cz + rz * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n)]

def squircle(cx, cz, rx, rz, p=4, n=64):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n; c, s = math.cos(t), math.sin(t)
        pts.append((cx + rx * math.copysign(abs(c) ** (2 / p), c), cz + rz * math.copysign(abs(s) ** (2 / p), s)))
    return pts

def rrect(x0, z0, x1, z1, r, n=6):
    pts = []
    for cx, cz, a in ((x1 - r, z0 + r, -90), (x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180)):
        for i in range(n + 1):
            t = math.radians(a + 90 * i / n); pts.append((cx + r * math.cos(t), cz + r * math.sin(t)))
    return pts

def wave_strip(x0, x1, base, top, amp, waves, phase=0, n=120, jag=0.0):
    pts = [(x0, base)]
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        z = top + amp * math.sin(phase + waves * 2 * math.pi * i / n) + amp * 0.35 * math.sin(phase * 1.7 + waves * 5.1 * math.pi * i / n)
        if jag and i % 2:
            z += jag
        pts.append((x, z))
    pts.append((x1, base))
    return pts

def rot(pts, ox, oz, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return [(ox + (x - ox) * c - (z - oz) * s, oz + (x - ox) * s + (z - oz) * c) for x, z in pts]

def offset(pts, d):
    """Push a closed polygon outward by d (the sticker cut margin)."""
    n = len(pts); area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    out = []
    for i in range(n):
        (ax, az), (bx, bz), (cx, cz) = pts[i - 1], pts[i], pts[(i + 1) % n]
        def nrm(px, pz, qx, qz):
            ex, ez = qx - px, qz - pz; l = math.hypot(ex, ez) or 1
            return ez / l * sgn, -ex / l * sgn
        n1, n2 = nrm(ax, az, bx, bz), nrm(bx, bz, cx, cz)
        mx, mz = n1[0] + n2[0], n1[1] + n2[1]; l = math.hypot(mx, mz) or 1
        k = min(1 / max((mx / l) * n1[0] + (mz / l) * n1[1], 0.35), 2.5)
        out.append((bx + mx / l * d * k, bz + mz / l * d * k))
    return out

def card(name, pts, y, hexc, thick=0.0010, glow=0.0, margin=0.0, mat=None):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "2D"; cu.fill_mode = "BOTH"
    cu.extrude = thick / 2; cu.bevel_depth = thick * 0.25; cu.bevel_resolution = 1
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for i, (x, z) in enumerate(pts):
        sp.points[i].co = (x, z, 0, 1)
    sp.use_cyclic_u = True
    ob = bpy.data.objects.new(name, cu); col.objects.link(ob)
    ob.rotation_euler = (math.pi / 2, 0, 0); ob.location = (0, y, 0)
    ob.data.materials.append(mat or paper(hexc, glow))
    if margin:  # off-white die-cut margin instead of a black ink outline
        card(name + "_margin", offset(pts, margin), y + thick * 0.9, PAL["margin"], thick)
    return ob

def disc(name, cx, cz, r, y, mat, depth=0.0012):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=depth, location=(cx, y, cz), rotation=(math.pi / 2, 0, 0))
    ob = bpy.context.object; ob.name = name; ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob

# ---------- world: tabletop diorama ----------
bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0.2, -0.03))
bpy.context.object.data.materials.append(paper(PAL["kraft"], fibre=2.0))

card("sky", rrect(-0.45, -0.03, 0.5, 0.8, 0.01), 0.30, PAL["sky_n"] if NIGHT else PAL["sky"], thick=0.002)
card("sun", ellipse(-0.07, 0.31, 0.035, 0.035), 0.288, PAL["cream"] if NIGHT else PAL["mustard"], glow=0.6 if NIGHT else 0)
for i, (cx, cz, s) in enumerate(((0.12, 0.33, 1.0), (-0.13, 0.24, 0.7), (0.02, 0.40, 0.55))):
    top = []  # cloud = flat bottom + scalloped top
    for k in range(5):
        bx = cx + (k - 2) * 0.021 * s; br = (0.017 + 0.008 * (k in (1, 3)) + 0.012 * (k == 2)) * s
        top += [(bx + br * math.cos(t), cz + br * math.sin(t)) for t in [math.pi - math.pi * j / 12 for j in range(13)]]
    pts = [(cx - 0.065 * s, cz)] + [p for p in top if p[1] >= cz] + [(cx + 0.065 * s, cz)]
    card(f"cloud{i}", pts, 0.275 - i * 0.004, PAL["cream"], margin=0.0015)

card("hills_far", wave_strip(-0.45, 0.5, -0.03, 0.115, 0.018, 1.6, 0.4), 0.22, PAL["sage"])
card("hills_mid", wave_strip(-0.45, 0.5, -0.03, 0.08, 0.016, 2.3, 2.0), 0.17, PAL["moss"])
card("sea_back", wave_strip(-0.45, 0.5, -0.03, 0.048, 0.003, 14, 0.0), 0.12, PAL["teal"])
card("sea_mid", wave_strip(-0.45, 0.5, -0.03, 0.032, 0.0035, 11, 1.3), 0.085, PAL["sea"])

# cliff with a darker stratum
cliff = [(0.0, -0.03), (0.01, 0.06), (0.025, 0.095), (0.04, 0.112), (0.075, 0.12), (0.12, 0.118),
         (0.17, 0.124), (0.22, 0.12), (0.27, 0.115), (0.3, -0.03)]
card("cliff", cliff, 0.055, PAL["ochre"], thick=0.0016)
card("cliff_band", [(0.012, 0.04), (0.03, 0.07), (0.08, 0.08), (0.15, 0.076), (0.3, 0.083), (0.3, 0.05), (0.15, 0.045), (0.06, 0.05), (0.012, 0.025)],
     0.0535, PAL["clay"])

# lighthouse
LX = 0.165
card("lh_tower", [(LX - 0.02, 0.12), (LX + 0.02, 0.12), (LX + 0.013, 0.215), (LX - 0.013, 0.215)], 0.064, PAL["cream"], margin=0.0012)
for i, z in enumerate((0.135, 0.17, 0.2)):
    w0 = 0.02 - (z - 0.12) * 0.074; w1 = 0.02 - (z + 0.012 - 0.12) * 0.074
    card(f"lh_band{i}", [(LX - w0, z), (LX + w0, z), (LX + w1, z + 0.012), (LX - w1, z + 0.012)], 0.0628, PAL["coral"])
card("lh_lamp", rrect(LX - 0.012, 0.215, LX + 0.012, 0.236, 0.002), 0.0632, PAL["mustard"], glow=8.0 if NIGHT else 1.2)
card("lh_frame", rrect(LX - 0.015, 0.213, LX + 0.015, 0.217, 0.001), 0.0624, PAL["navy"])
card("lh_roof", [(LX - 0.017, 0.236), (LX + 0.017, 0.236), (LX, 0.258)], 0.0632, PAL["coral"], margin=0.0012)
card("lh_door", rrect(LX - 0.005, 0.12, LX + 0.005, 0.137, 0.004), 0.0625, PAL["navy"])

# diegetic sign: paper tag pinned to the cliff
card("tag", rrect(0.205, 0.088, 0.262, 0.108, 0.003), 0.0525, PAL["cream"], margin=0.0008)
disc("tag_pin", 0.209, 0.104, 0.0016, 0.051, BRASS)
bpy.ops.object.text_add(location=(0.233, 0.0518, 0.0945), rotation=(math.pi / 2, 0, 0))
t = bpy.context.object; t.data.body = "KEEPER\nWANTED"; t.data.align_x = "CENTER"; t.data.align_y = "CENTER"
t.data.size = 0.0072; t.data.space_line = 0.9; t.data.extrude = 0.0001
t.data.materials.append(paper(PAL["navy"], fibre=0.3))

card("sea_front", wave_strip(-0.45, 0.5, -0.03, 0.014, 0.004, 9, 2.4), 0.03, PAL["deep"])
card("foam", wave_strip(-0.45, 0.0, 0.004, 0.017, 0.002, 9, 2.4), 0.029, PAL["cream"])
card("grass_fg", wave_strip(-0.45, 0.5, -0.03, 0.006, 0.004, 26, 0.7, n=160, jag=0.012), -0.03, PAL["grass"])

# ---------- character: the keeper (paper puppet, split-pin joints) ----------
def keeper(x, y, zf, s=1.0):
    P = lambda pts: [(x + px * s, zf + pz * s) for px, pz in pts]
    d = 0.0016  # layer step toward camera
    card("k_legL", P(rrect(-0.010, 0.0, -0.002, 0.022, 0.003)), y, PAL["navy"], margin=0.001)
    card("k_legR", P(rrect(0.002, 0.0, 0.010, 0.022, 0.003)), y, PAL["navy"], margin=0.001)
    card("k_bootL", P(ellipse(-0.008, 0.002, 0.007, 0.0035)), y - d, PAL["clay"])
    card("k_bootR", P(ellipse(0.008, 0.002, 0.007, 0.0035)), y - d, PAL["clay"])
    card("k_armL", P(rot(rrect(-0.019, 0.022, -0.012, 0.046, 0.0035), -0.0155, 0.043, -12)), y - d, PAL["mustard"], margin=0.001)
    coat = [(-0.017, 0.018), (0.017, 0.018), (0.012, 0.05), (-0.012, 0.05)]
    card("k_coat", P(coat), y - 2 * d, PAL["mustard"], margin=0.0012)
    card("k_scarf", P(rrect(-0.013, 0.046, 0.013, 0.053, 0.003)), y - 3 * d, PAL["coral"])
    card("k_head", P(squircle(0.0, 0.068, 0.018, 0.016, p=3.2)), y - 3 * d, PAL["skin"], margin=0.0012)
    card("k_cap", P([(-0.0175, 0.077)] + ellipse(0.0, 0.077, 0.0175, 0.013, n=24, a0=0, a1=math.pi)[::-1][:-1] + [(0.0175, 0.077)][::-1]),
         y - 4 * d, PAL["coral"], margin=0.0012)
    card("k_capband", P(rrect(-0.019, 0.074, 0.019, 0.08, 0.002)), y - 5 * d, PAL["teal"])
    card("k_pom", P(ellipse(0.0, 0.092, 0.0045, 0.0045)), y - 4 * d, PAL["cream"])
    for sx in (-1, 1):  # punched-hole eyes with a paper glint, rosy cheeks
        card(f"k_eye{sx}", P(ellipse(sx * 0.0062, 0.067, 0.0021, 0.0026, n=20)), y - 5 * d, PAL["navy"], thick=0.0006)
        card(f"k_glint{sx}", P(ellipse(sx * 0.0062 + 0.0007, 0.0679, 0.0006, 0.0006, n=12)), y - 6 * d, PAL["cream"], thick=0.0004)
        card(f"k_cheek{sx}", P(ellipse(sx * 0.0115, 0.061, 0.0028, 0.002, n=20)), y - 5 * d, PAL["coral"], thick=0.0006)
    card("k_nose", P([(-0.0018, 0.0625), (0.0018, 0.0625), (0.0, 0.0655)]), y - 5 * d, PAL["skin_dk"], thick=0.0006)
    card("k_mouth", P(ellipse(0.0, 0.0595, 0.0035, 0.0016, n=16, a0=math.pi, a1=2 * math.pi)), y - 5 * d, PAL["navy"], thick=0.0006)
    # raised right arm holding the lantern, brass split pins at the shoulders
    arm = rot(rrect(0.012, 0.022, 0.019, 0.046, 0.0035), 0.0155, 0.043, 62)
    card("k_armR", P(arm), y - 6 * d, PAL["mustard"], margin=0.001)
    disc("k_pinL", x - 0.0155 * s, zf + 0.043 * s, 0.0016 * s, y - 2 * d - 0.001, BRASS)
    disc("k_pinR", x + 0.0155 * s, zf + 0.043 * s, 0.0016 * s, y - 6 * d - 0.001, BRASS)
    hx, hz = 0.037, 0.052
    card("k_lant_handle", P(ellipse(hx, hz + 0.004, 0.004, 0.004, n=20, a0=0, a1=math.pi) + ellipse(hx, hz + 0.004, 0.0028, 0.0028, n=20, a0=math.pi, a1=0)),
         y - 7 * d, PAL["navy"], thick=0.0006)
    card("k_lant", P(rrect(hx - 0.006, hz - 0.012, hx + 0.006, hz + 0.003, 0.002)), y - 7 * d, PAL["navy"], margin=0.001)
    card("k_lant_glass", P(rrect(hx - 0.0042, hz - 0.0095, hx + 0.0042, hz + 0.0005, 0.0015)), y - 8 * d, PAL["mustard"],
         glow=10.0 if NIGHT else 2.0)
    return (x + hx * s, zf + (hz - 0.004) * s)

KX, KY, KZ = 0.06, 0.047, 0.118
lantern_xz = keeper(KX, KY, KZ)

# ---------- pivot device: paper curtain slides in (scalloped hem) ----------
if NIGHT:
    def curtain(x0, x1, y):
        pts = [(x0, 0.75)]
        n = 9
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n
            pts.append((xx, -0.02 + 0.006 * (i % 2)))
        pts.append((x1, 0.75))
        return pts[::-1]
    card("curtainL", curtain(-0.45, -0.065, -0.06), -0.06, PAL["coral"], thick=0.002, margin=0.002)
    card("curtainR", curtain(0.145, 0.55, -0.06), -0.06, PAL["coral"], thick=0.002, margin=0.002)
    card("valance", wave_strip(-0.45, 0.55, 0.7, 0.33, 0.012, 7, 1.0), -0.065, PAL["navy"], thick=0.002)

# ---------- lights ----------
def area(name, loc, target, size, watts, hexc):
    ld = bpy.data.lights.new(name, "AREA"); ld.size = size; ld.energy = watts; ld.color = lin(hexc)[:3]
    ob = bpy.data.objects.new(name, ld); col.objects.link(ob); ob.location = loc
    tr = ob.constraints.new("TRACK_TO"); e = bpy.data.objects.new(name + "_t", None); col.objects.link(e)
    e.location = target; tr.target = e; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    return ob

def point(name, loc, watts, hexc, r=0.004):
    ld = bpy.data.lights.new(name, "POINT"); ld.energy = watts; ld.color = lin(hexc)[:3]; ld.shadow_soft_size = r
    ob = bpy.data.objects.new(name, ld); col.objects.link(ob); ob.location = loc

world = bpy.data.worlds.new("w"); scn.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]
if NIGHT:
    bg.inputs[0].default_value = lin("#1B2747"); bg.inputs[1].default_value = 0.25
    area("key", (-0.4, -0.5, 0.6), (0.05, 0.1, 0.08), 0.4, 9, "#7C97E0")
    area("rim", (0.35, 0.55, 0.35), (0.05, 0.05, 0.1), 0.2, 4, "#A9B9F0")
    point("lantern", (lantern_xz[0], KY - 0.02, lantern_xz[1]), 0.25, "#FFB45A")
    point("lamp", (LX, 0.05, 0.226), 0.6, "#FFC46B")
else:
    bg.inputs[0].default_value = lin("#F6EBD8"); bg.inputs[1].default_value = 0.35
    area("key", (-0.35, -0.45, 0.55), (0.05, 0.1, 0.08), 0.35, 26, "#FFE9C9")
    area("rim", (0.3, 0.55, 0.4), (0.05, 0.05, 0.1), 0.2, 10, "#FFF4E2")
    area("fill", (0.4, -0.5, 0.15), (0.05, 0.05, 0.1), 0.5, 5, "#DCEBF2")

# ---------- camera ----------
SHOTS = {
    "hook": dict(loc=(0.08, -0.17, 0.178), tgt=(0.076, KY, 0.172), lens=50, f=2.0, focus=(0.062, KY, 0.185)),
    "wide": dict(loc=(0.08, -0.33, 0.2), tgt=(0.08, 0.12, 0.185), lens=35, f=2.8, focus=(KX, KY, 0.16)),
    "pivot": dict(loc=(0.08, -0.33, 0.2), tgt=(0.08, 0.12, 0.185), lens=35, f=2.8, focus=(KX, KY, 0.16)),
}
S = SHOTS[SHOT]
cd = bpy.data.cameras.new("cam"); cd.lens = S["lens"]; cd.sensor_width = 36; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36
cd.clip_start = 0.005
cam = bpy.data.objects.new("cam", cd); col.objects.link(cam); cam.location = S["loc"]; scn.camera = cam
tgt = bpy.data.objects.new("cam_t", None); col.objects.link(tgt); tgt.location = S["tgt"]
c = cam.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
foc = bpy.data.objects.new("focus", None); col.objects.link(foc); foc.location = S["focus"]
cd.dof.use_dof = True; cd.dof.focus_object = foc; cd.dof.aperture_fstop = S["f"]; cd.dof.aperture_blades = 6

# ---------- render ----------
scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"
# the apt Blender build has no OpenImageDenoise: plain path tracing, few bounces
scn.cycles.samples = int(os.environ.get("SAMPLES", 192)); scn.cycles.use_denoising = False
scn.cycles.max_bounces = 4; scn.cycles.diffuse_bounces = 3; scn.cycles.glossy_bounces = 2
scn.cycles.transmission_bounces = 0; scn.cycles.transparent_max_bounces = 2
scn.cycles.sample_clamp_indirect = 4.0
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920
scn.render.resolution_percentage = SCALE
try:
    scn.view_settings.view_transform = "AgX"; scn.view_settings.look = "AgX - Punchy"; scn.view_settings.exposure = -0.35
except Exception:
    scn.view_settings.view_transform = "Filmic"
scn.render.image_settings.file_format = "PNG"
scn.render.filepath = os.path.join(OUT, f"{SHOT}.png")
bpy.ops.render.render(write_still=True)
print("WROTE", scn.render.filepath)
