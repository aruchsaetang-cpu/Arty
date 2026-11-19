"""Manhwa-style people built on the CC0 MakeHuman base mesh (lookdev/assets/makehuman).

build(collection, location, style=None, pose_mode="walk") -> (armature, objects)
animate_walk(arm, start, heading_deg, frames, phase, umbrella)  looping walk cycle
add_umbrella(arm, objs, colour) / add_phone(arm, objs)

Everything is cel shaded (Cycles-safe) with a rim band; leather and hair get a sheen band.
HERO is the story's lead (charcoal coat, oatmeal turtleneck); extras pick from STYLE keys.
"""
import bpy, bmesh, json, math, os
from mathutils import Vector, Matrix, Quaternion, kdtree, bvhtree

HERE = os.path.dirname(os.path.abspath(__file__))
MH = os.path.join(HERE, "assets", "makehuman")
S = 0.1  # MakeHuman decimetres -> metres
REAL = os.environ.get("CHAR_STYLE", "real") == "real"   # realistic materials lit by the scene (CHAR_STYLE=cel: flat manhwa)
OUTLINE = 0.0022 if REAL else 0.005  # ink line width in metres (0 disables); thin on the realistic look
SHADOW = 0.2      # manhwa shading: deep, hard-edged shadow (fraction of base colour)
SHADOW_TINT = (0.09, 0.07, 0.16)  # shadows lean cool violet, like printed webtoon panels

BODY = {
    "m": {"asian-male-young.target": 0.55, "caucasian-male-young.target": 0.45,
          "universal-male-young-maxmuscle-averageweight.target": 0.35,
          "universal-male-young-averagemuscle-minweight.target": 0.25,
          "male-young-averagemuscle-averageweight-maxheight.target": 0.3,
          "male-young-averagemuscle-averageweight-idealproportions.target": 1.0},
    "m_lean": {"asian-male-young.target": 0.75, "caucasian-male-young.target": 0.25,
               "universal-male-young-maxmuscle-averageweight.target": 0.55,
               "universal-male-young-averagemuscle-minweight.target": 0.45,
               "male-young-averagemuscle-averageweight-maxheight.target": 0.7,
               "male-young-averagemuscle-averageweight-idealproportions.target": 1.0},
    "m_muscle": {"asian-male-young.target": 0.75, "caucasian-male-young.target": 0.25,
                 "universal-male-young-maxmuscle-averageweight.target": 1.4,
                 "universal-male-young-averagemuscle-minweight.target": 0.55,
                 "male-young-averagemuscle-averageweight-maxheight.target": 0.7,
                 "male-young-averagemuscle-averageweight-idealproportions.target": 1.0},
    "m_slender": {"asian-male-young.target": 0.75, "caucasian-male-young.target": 0.25,     # tall, slim, lightly toned
                  "universal-male-young-maxmuscle-averageweight.target": 0.3,
                  "universal-male-young-averagemuscle-minweight.target": 0.6,
                  "male-young-averagemuscle-averageweight-maxheight.target": 0.85,
                  "male-young-averagemuscle-averageweight-idealproportions.target": 1.0},
    "m_fit": {"asian-male-young.target": 0.75, "caucasian-male-young.target": 0.25,
              "universal-male-young-maxmuscle-averageweight.target": 0.95,
              "universal-male-young-averagemuscle-minweight.target": 0.6,
              "male-young-averagemuscle-averageweight-maxheight.target": 0.6,
              "male-young-averagemuscle-averageweight-idealproportions.target": 1.0},
    "m_slim": {"asian-male-young.target": 0.8, "caucasian-male-young.target": 0.2,
               "universal-male-young-averagemuscle-minweight.target": 0.65,
               "male-young-averagemuscle-averageweight-maxheight.target": 0.5,
               "male-young-averagemuscle-averageweight-idealproportions.target": 0.8},
    # children: slim, soft, no muscle definition (no muscle or height targets)
    "kid_m": {"asian-male-young.target": 0.8, "caucasian-male-young.target": 0.2,
              "universal-male-young-averagemuscle-minweight.target": 0.55},
    "kid_f": {"asian-female-young.target": 0.8, "caucasian-female-young.target": 0.2,
              "universal-female-young-averagemuscle-minweight.target": 0.5},
    "m_heavy": {"asian-male-young.target": 0.5, "african-male-young.target": 0.2, "caucasian-male-young.target": 0.3,
                "universal-male-young-averagemuscle-maxweight.target": 0.55,
                "male-young-averagemuscle-averageweight-idealproportions.target": 0.6},
    "f": {"asian-female-young.target": 0.6, "caucasian-female-young.target": 0.4,
          "universal-female-young-averagemuscle-minweight.target": 0.35,
          "female-young-averagemuscle-averageweight-maxheight.target": 0.25,
          "female-young-averagemuscle-averageweight-idealproportions.target": 1.0},
}

# Lead: "midnight, no coat, no hat". Tall webtoon build, slicked-back black hair, black open-collar shirt,
# charcoal slacks, black leather shoes. Original design in the Korean webtoon idiom (not any existing character).
HERO = dict(body="m_lean", height=1.9, skin=("#efcfb4", "#b0806a"), hair="slick", hair_col="#101216", locks=True,
            top=("#1d1f25", "#07080b"), turtleneck=False, coat=None, manhwa_head=True,
            legs="trousers", leg_col=("#2b2e35", "#0b0c10"), shoes=("#141416", "#3a3236"), brows="#121014", iris="#6e4a32")

# the lead (only when build() is given HERO itself): tall and lean; a long light-grey jacket worn open and loose,
# flaring off the shoulders, black V-neck top, light-grey creased trousers, black loafers; slicked-back hair,
# idol face, and the eyes nobody else has (black sclera, white irises)
HERO_LOOK = dict(body="m_slender", vtaper=False, crease=0.0, turtleneck=False, vneck=True, top=("#17181c", "#050506"),
                 coat=("#cfd0d4", "#7a7c84"), hem=0.72, open_skirt=True, open_coat=True, lapels=True, drape=True, coat_flare=(0.04, 0.08),
                 tie=None,
                 creases=True,
                 leg_col=("#c4c5ca", "#767880"), shoes=("#121216", "#4a3c36"), loafer=True, sneakers=False,
                 face="idol", hair="quiff", hair_col="#16120f", locks=False, brow_style="sharp", jaw_v=0.42, void_eyes=True)

# face sculpts from MakeHuman's CC0 face targets (assets/makehuman/targets/face): weights per target
FACES = {
    # K-pop idol / webtoon lead: slim oval V-line face, small sharp chin, high straight narrow nose,
    # long upturned eyes, low angled brows, small mouth with a defined cupid's bow
    "idol": {"head-oval": 0.7, "head-invertedtriangular": 0.35, "head-scale-horiz-decr": 0.25, "head-age-decr": 0.4,
             "chin-width-decr": 0.7, "chin-triangle": 0.5, "chin-height-decr": 0.6, "mouth-trans-up": 0.35, "chin-prominent-incr": 0.25,
             "l-cheek-volume-decr": 0.6, "r-cheek-volume-decr": 0.6, "l-cheek-bones-incr": 0.3, "r-cheek-bones-incr": 0.3,
             "nose-scale-horiz-decr": 0.55, "nose-point-width-decr": 0.7, "nose-flaring-decr": 0.6,
             "nose-nostrils-width-decr": 0.6, "nose-volume-decr": 0.45, "nose-hump-decr": 0.5, "nose-greek-incr": 0.35,
             "nose-point-up": 0.25, "nose-scale-vert-incr": 0.2, "nose-width1-decr": 0.4, "nose-width2-decr": 0.4,
             "l-eye-corner1-up": 0.7, "r-eye-corner1-up": 0.7, "l-eye-height2-decr": 0.35, "r-eye-height2-decr": 0.35,
             "l-eye-scale-incr": 0.25, "r-eye-scale-incr": 0.25, "l-eye-epicanthus-in": 0.3, "r-eye-epicanthus-in": 0.3,
             "eyebrows-angle-up": 0.5, "eyebrows-trans-down": 0.3, "forehead-scale-vert-decr": 0.6,
             "mouth-scale-horiz-decr": 0.25, "mouth-cupidsbow-incr": 0.5, "mouth-angles-up": 0.2,
             "mouth-lowerlip-volume-incr": 0.3, "mouth-upperlip-volume-decr": 0.2, "neck-scale-vert-incr": 0.4},
    # everyone else gets a face of their own (no two of the cast share a head)
    "square": {"head-square": 0.7, "chin-width-incr": 0.5, "eyebrows-angle-down": 0.4, "l-eye-height2-decr": 0.3,
               "r-eye-height2-decr": 0.3, "nose-scale-horiz-incr": 0.3, "nose-hump-incr": 0.35, "mouth-scale-horiz-incr": 0.3,
               "head-age-incr": 0.35, "neck-scale-horiz-incr": 0.4},
    "round": {"head-round": 0.8, "head-fat-incr": 0.7, "l-cheek-volume-incr": 0.7, "r-cheek-volume-incr": 0.7,
              "nose-volume-incr": 0.5, "nose-point-width-incr": 0.5, "l-eye-scale-decr": 0.3, "r-eye-scale-decr": 0.3,
              "mouth-upperlip-volume-incr": 0.3, "head-age-incr": 0.5},
    "long": {"head-rectangular": 0.6, "forehead-scale-vert-incr": 0.4, "nose-scale-vert-incr": 0.5, "chin-height-incr": 0.4,
             "l-eye-corner1-down": 0.4, "r-eye-corner1-down": 0.4, "mouth-angles-down": 0.3, "eyebrows-angle-down": 0.3},
    "diamond": {"head-diamond": 0.7, "l-cheek-volume-incr": 0.4, "r-cheek-volume-incr": 0.4, "nose-flaring-incr": 0.5,
                "head-scale-horiz-incr": 0.3, "head-age-incr": 0.6},
    "soft_f": {"head-oval": 0.6, "l-eye-scale-incr": 0.45, "r-eye-scale-incr": 0.45, "l-eye-corner1-up": 0.3,
               "r-eye-corner1-up": 0.3, "nose-scale-horiz-decr": 0.5, "nose-point-width-decr": 0.5, "nose-volume-decr": 0.4,
               "chin-width-decr": 0.5, "chin-triangle": 0.3, "mouth-lowerlip-volume-incr": 0.4, "mouth-cupidsbow-incr": 0.4,
               "l-cheek-volume-decr": 0.2, "r-cheek-volume-decr": 0.2, "head-age-decr": 0.4},
    "sharp_f": {"head-invertedtriangular": 0.5, "l-eye-height2-decr": 0.3, "r-eye-height2-decr": 0.3, "l-eye-corner1-up": 0.6,
                "r-eye-corner1-up": 0.6, "nose-greek-incr": 0.3, "nose-scale-horiz-decr": 0.4, "chin-triangle": 0.5,
                "eyebrows-angle-up": 0.4, "mouth-scale-horiz-decr": 0.2, "head-age-decr": 0.3},
    # K-drama actress: slim V-line, big bright eyes, small refined nose, full defined lips, smooth young skin
    "kstar_f": {"head-oval": 0.6, "head-invertedtriangular": 0.35, "head-scale-horiz-decr": 0.2, "head-age-decr": 0.6,
                "chin-width-decr": 0.8, "chin-triangle": 0.55, "chin-height-decr": 0.15, "l-cheek-volume-decr": 0.4,
                "r-cheek-volume-decr": 0.4, "nose-scale-horiz-decr": 0.6, "nose-point-width-decr": 0.7,
                "nose-volume-decr": 0.55, "nose-point-up": 0.3, "nose-flaring-decr": 0.5, "nose-nostrils-width-decr": 0.5,
                "l-eye-scale-incr": 0.65, "r-eye-scale-incr": 0.65, "l-eye-height2-incr": 0.35, "r-eye-height2-incr": 0.35,
                "l-eye-corner1-up": 0.25, "r-eye-corner1-up": 0.25, "mouth-lowerlip-volume-incr": 0.3,
                "mouth-upperlip-volume-incr": 0.1, "mouth-cupidsbow-incr": 0.6, "mouth-scale-horiz-decr": 0.15,
                "mouth-angles-up": 0.15, "eyebrows-angle-up": 0.15, "forehead-scale-vert-decr": 0.3, "neck-scale-vert-incr": 0.5},
    "boy": {"head-oval": 0.4, "head-age-decr": 0.6, "l-eye-scale-incr": 0.2, "r-eye-scale-incr": 0.2,
            "nose-scale-horiz-decr": 0.3, "chin-width-decr": 0.3, "nose-volume-decr": 0.3, "mouth-lowerlip-volume-incr": 0.2},
}

VARY_PAIRS = ["eye-scale-incr", "eye-scale-decr", "eye-height2-incr", "eye-height2-decr", "eye-corner1-up",
              "eye-corner1-down", "cheek-volume-incr", "cheek-volume-decr", "cheek-bones-incr"]
VARY_SINGLES = ["head-oval", "head-round", "head-square", "head-rectangular", "head-diamond", "head-invertedtriangular",
                "head-fat-incr", "head-scale-horiz-incr", "head-scale-horiz-decr", "chin-width-incr", "chin-width-decr",
                "chin-height-incr", "chin-height-decr", "chin-prominent-incr", "chin-triangle", "nose-scale-horiz-incr",
                "nose-scale-horiz-decr", "nose-volume-incr", "nose-volume-decr", "nose-hump-incr", "nose-hump-decr",
                "nose-point-up", "nose-scale-vert-incr", "nose-point-width-incr", "nose-point-width-decr", "nose-flaring-incr",
                "nose-flaring-decr", "nose-greek-incr", "mouth-scale-horiz-incr", "mouth-scale-horiz-decr",
                "mouth-lowerlip-volume-incr", "mouth-upperlip-volume-incr", "mouth-upperlip-volume-decr", "mouth-cupidsbow-incr",
                "mouth-angles-up", "mouth-angles-down", "eyebrows-angle-up", "eyebrows-angle-down", "eyebrows-trans-down",
                "forehead-scale-vert-incr", "forehead-scale-vert-decr", "head-age-incr", "head-age-decr",
                "neck-scale-horiz-incr", "neck-scale-vert-incr"]
NOT_FOR_STARS = {"head-square", "head-rectangular", "head-fat-incr", "nose-hump-incr", "nose-volume-incr", "head-age-incr",
                 "chin-width-incr", "mouth-angles-down", "neck-scale-horiz-incr", "nose-flaring-incr", "eyebrows-angle-down",
                 "nose-scale-horiz-incr", "nose-point-width-incr", "eye-scale-decr", "eye-height2-decr", "eye-corner1-down",
                 "cheek-volume-incr"}

def _target(path):
    if path not in _TGT:
        _TGT[path] = [(int(a), float(b), float(c), float(d)) for a, b, c, d in
                      (l.split() for l in open(os.path.join(MH, "targets", path + ".target")) if l[0] not in "#\n")]
    return _TGT[path]

def apply_targets(V, weights):
    for path, w in weights.items():
        for i, dx, dy, dz in _target(path):
            V[i] += Vector((dx * S, -dz * S, dy * S)) * w

def vary_face(seed, pretty=False):
    """A face of one's own: 7-10 random face targets on top of the preset (gentler and 'beauty-safe' for stars)."""
    import random as _r
    rng = _r.Random(seed); out = {}
    pool = [t for t in VARY_SINGLES + VARY_PAIRS if not (pretty and t in NOT_FOR_STARS)]
    for t in rng.sample(pool, rng.randint(7, 10)):
        w = rng.uniform(0.1, 0.4) if pretty else rng.uniform(0.15, 0.6)
        if t in VARY_PAIRS:
            out["face/l-" + t] = w; out["face/r-" + t] = w
        else:
            out["face/" + t] = w
    return out

def vary_body(seed, sex):
    """A build of one's own: random weight / muscle / height / proportion blend on top of the body type."""
    import random as _r
    rng = _r.Random(seed * 7 + 3)
    if sex == "f":
        return {"universal-female-young-averagemuscle-minweight.target": rng.uniform(-0.25, 0.45),
                "female-young-averagemuscle-averageweight-maxheight.target": rng.uniform(-0.2, 0.4),
                "female-young-averagemuscle-averageweight-idealproportions.target": rng.uniform(-0.3, 0.3)}
    return {"universal-male-young-averagemuscle-maxweight.target": rng.choice([0.0, 0.0, rng.uniform(0.1, 0.55)]),
            "universal-male-young-averagemuscle-minweight.target": rng.uniform(-0.2, 0.45),
            "universal-male-young-maxmuscle-averageweight.target": rng.uniform(-0.15, 0.45),
            "male-young-averagemuscle-averageweight-maxheight.target": rng.uniform(-0.2, 0.4)}

def apply_face(V, name):
    for fn, w in FACES[name].items():
        key = "face/" + fn
        if key not in _TGT:
            _TGT[key] = [(int(a), float(b), float(c), float(d)) for a, b, c, d in
                         (l.split() for l in open(os.path.join(MH, "targets", "face", fn + ".target")) if l[0] not in "#\n")]
        for i, dx, dy, dz in _TGT[key]:
            V[i] += Vector((dx * S, -dz * S, dy * S)) * w

def set_interp(idblock, kind="LINEAR", data_path=None):
    """Force interpolation on an ID's keyframes (Blender 5 ignores the new-key preference in background mode)."""
    from bpy_extras import anim_utils
    ad = getattr(idblock, "animation_data", None)
    if not ad or not ad.action:
        return
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    if cb is None:
        return
    for fc in cb.fcurves:
        if data_path is None or fc.data_path == data_path:
            for k in fc.keyframe_points:
                k.interpolation = kind

def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

# ---------------------------------------------------------------- data (cached)
_BASE = None; _TGT = {}; _RIG = None
def load_base(body):
    global _BASE
    if _BASE is None:
        verts, faces, groups, g = [], [], [], None
        for line in open(os.path.join(MH, "base.obj")):
            if line.startswith("v "):
                verts.append(tuple(float(t) for t in line.split()[1:4]))
            elif line.startswith("g "):
                g = line.split()[1]
            elif line.startswith("f "):
                faces.append([int(p.split("/")[0]) - 1 for p in line.split()[1:]]); groups.append(g)
        _BASE = (verts, faces, groups)
    verts, faces, groups = _BASE
    vs = [list(v) for v in verts]
    for fn, w in BODY[body].items():
        if fn not in _TGT:
            d = []
            for line in open(os.path.join(MH, "targets", fn)):
                if line[0] not in "#\n":
                    i, dx, dy, dz = line.split(); d.append((int(i), float(dx), float(dy), float(dz)))
            _TGT[fn] = d
        for i, dx, dy, dz in _TGT[fn]:
            v = vs[i]; v[0] += dx * w; v[1] += dy * w; v[2] += dz * w
    return [Vector((x * S, -z * S, y * S)) for x, y, z in vs], faces, groups   # Z-up metres, facing -Y

def load_rig():
    global _RIG
    if _RIG is None:
        sk = json.load(open(os.path.join(MH, "default.mhskel")))
        w = json.load(open(os.path.join(MH, "default_weights.mhw")))["weights"]
        per_vert = {}
        for bone, lst in w.items():
            for vi, wt in lst:
                per_vert.setdefault(vi, []).append((bone, wt))
        _RIG = (sk, per_vert)
    return _RIG

# ---------------------------------------------------------------- materials
_cache = {}
def _nodes(m):
    m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    def mth(op, a, b=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    def mix(f, a, b):
        n = N.new("ShaderNodeMix"); n.data_type = "RGBA"
        for s, v in ((0, f), (6, a), (7, b)):
            if isinstance(v, (int, float, tuple)): n.inputs[s].default_value = v
            else: L.new(v, n.inputs[s])
        return n.outputs[2]
    return N, L, mth, mix

def cel(hexc, shade=None, rim="#cdeffd", spec=0.0, spec_col="#ffffff", light=(-0.55, -0.7, 0.55), rim_amt=0.8, name=None, glow=1.0,
        crease=0.0, crease_zmax=99.0):
    key = (hexc, shade, rim, spec, spec_col, light, rim_amt, glow, crease, crease_zmax, name)
    if key in _cache:
        return _cache[key]
    if REAL and glow <= 1.0:
        _cache[key] = real_mat(hexc, name, spec, crease, crease_zmax)
        return _cache[key]
    m = bpy.data.materials.new(name or f"cel_{hexc}")
    N, L, mth, mix = _nodes(m)
    out = N.new("ShaderNodeOutputMaterial"); geo = N.new("ShaderNodeNewGeometry")
    ln = Vector(light).normalized()
    d = N.new("ShaderNodeVectorMath"); d.operation = "DOT_PRODUCT"; L.new(geo.outputs["Normal"], d.inputs[0]); d.inputs[1].default_value = ln
    base = lin(hexc); sh = lin(shade) if shade else tuple(c * 0.38 for c in base[:3]) + (1.0,)
    if name != "skin":   # cloth and hair: deeper, cooler shadow; skin keeps its warm given shade
        sh = tuple(min(a, b * SHADOW + t) for a, b, t in zip(sh[:3], base[:3], SHADOW_TINT)) + (1.0,)
    mid = tuple(a * 0.62 + b * 0.38 for a, b in zip(base, sh))
    c = mix(mth("GREATER_THAN", d.outputs["Value"], 0.02), sh, mid)        # hard shadow edge
    c = mix(mth("GREATER_THAN", d.outputs["Value"], 0.42), c, base)
    if spec:  # sheen band: N.H with H = light + view
        h = N.new("ShaderNodeVectorMath"); h.operation = "ADD"; h.inputs[0].default_value = ln
        L.new(geo.outputs["Incoming"], h.inputs[1])
        hn = N.new("ShaderNodeVectorMath"); hn.operation = "NORMALIZE"; L.new(h.outputs[0], hn.inputs[0])
        d2 = N.new("ShaderNodeVectorMath"); d2.operation = "DOT_PRODUCT"; L.new(geo.outputs["Normal"], d2.inputs[0]); L.new(hn.outputs[0], d2.inputs[1])
        c = mix(mth("MULTIPLY", mth("GREATER_THAN", d2.outputs["Value"], 1 - spec), 0.9), c, lin(spec_col))
    if crease:   # webtoon muscle lines: ink the concave creases between muscle masses (Cycles pointiness)
        cav = mth("LESS_THAN", geo.outputs["Pointiness"], 0.5 - crease)
        tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        cav = mth("MULTIPLY", cav, mth("LESS_THAN", sep.outputs["Z"], crease_zmax))
        c = mix(mth("MULTIPLY", cav, 0.85), c, tuple(x * 0.35 for x in sh[:3]) + (1.0,))
    # soft contact shadows: under the chin, inside clothing folds, where arms meet the body (short-range AO)
    ao = N.new("ShaderNodeAmbientOcclusion"); ao.samples = 4; ao.inputs["Distance"].default_value = 0.05
    occ = mth("MULTIPLY", mth("SUBTRACT", 1.0, ao.outputs["AO"]), 0.4 if name == "skin" else 0.55)
    c = mix(occ, c, tuple(x * 0.7 for x in sh[:3]) + (1.0,))
    # light bounced from the neon signs either side of the street: magenta from one side, cyan from the other,
    # warm from the wet road below (world-space normal, so it stays put as people turn)
    sep_n = N.new("ShaderNodeSeparateXYZ"); L.new(geo.outputs["Normal"], sep_n.inputs[0])
    blum = 0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2]
    k_env = (0.03 if name == "skin" else 0.035) * (0.35 + min(1.0, blum * 1.5))   # a faint tint, fainter on dark cloth
    for comp, sign, col in (("X", -1, "#ff3d8a"), ("X", 1, "#2fd8ff"), ("Z", -1, "#ffb070")):
        f_ = mth("MULTIPLY", mth("MAXIMUM", mth("MULTIPLY", sep_n.outputs[comp], sign), 0.0), k_env)
        ad = N.new("ShaderNodeMix"); ad.data_type = "RGBA"; ad.blend_type = "ADD"
        L.new(f_, ad.inputs[0]); L.new(c, ad.inputs[6]); ad.inputs[7].default_value = lin(col)
        c = ad.outputs[2]
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.3
    c = mix(mth("MULTIPLY", mth("GREATER_THAN", lw.outputs["Facing"], 0.6), rim_amt), c, lin(rim))
    e = N.new("ShaderNodeEmission"); e.inputs["Strength"].default_value = glow
    L.new(c, e.inputs["Color"]); L.new(e.outputs[0], out.inputs[0])
    _cache[key] = m
    return m

def real_mat(hexc, name, spec=0.0, crease=0.0, crease_zmax=99.0):
    """Physically based material for the realistic look: lit by the street lights, neon and the aura."""
    m = bpy.data.materials.new((name or "mat") + "_real"); m.use_nodes = True; nt = m.node_tree
    N_, L_ = nt.nodes, nt.links; N_.clear()
    out = N_.new("ShaderNodeOutputMaterial"); b = N_.new("ShaderNodeBsdfPrincipled")
    L_.new(b.outputs[0], out.inputs[0])
    col = lin(hexc); n = name or ""
    rough, spec_lvl, sheen = 0.72, 0.4, 0.25                  # cloth
    if n == "skin":
        rough, spec_lvl, sheen = 0.42, 0.45, 0.0
        b.inputs["Subsurface Weight"].default_value = 0.12
        b.inputs["Subsurface Radius"].default_value = (0.9, 0.4, 0.25)
        b.inputs["Subsurface Scale"].default_value = 0.008
    elif n.startswith("hair"):     # matte strands with a soft sheen (no plastic helmet gloss)
        rough, spec_lvl, sheen = 0.58, 0.3, 0.18
    elif n in ("shoe", "sole", "belt", "loafer_strap", "lips", "shaft", "umbrella", "pov_umbrella", "bag", "bag_strap"):
        rough, spec_lvl, sheen = (0.22 if n in ("shoe", "loafer_strap", "lips") else 0.4), 0.6, 0.0
    elif n in ("brow", "lash"):
        rough, spec_lvl, sheen = 0.6, 0.2, 0.0
    if spec:
        rough = min(rough, 0.3)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec_lvl
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen; b.inputs["Sheen Roughness"].default_value = 0.5
    if crease:   # keep the muscle definition: darken the concave creases a little (pointiness)
        geo = N_.new("ShaderNodeNewGeometry"); mr = N_.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = 0.5 - crease * 2.5; mr.inputs["From Max"].default_value = 0.5
        mr.inputs["To Min"].default_value = 0.55; mr.inputs["To Max"].default_value = 1.0
        L_.new(geo.outputs["Pointiness"], mr.inputs["Value"])
        mx = N_.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
        mx.inputs[6].default_value = col; L_.new(mr.outputs["Result"], mx.inputs[7])
        L_.new(mx.outputs[2], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = col
    return m

def eye_mat(radius, iris="#7a5236", void=False):
    if void:
        return void_eye_mat(radius)
    key = ("eye", round(radius, 4), iris)
    if key in _cache:
        return _cache[key]
    m = bpy.data.materials.new("eye")
    N, L, mth, mix = _nodes(m)
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    r = mth("SQRT", mth("ADD", mth("MULTIPLY", sep.outputs["X"], sep.outputs["X"]), mth("MULTIPLY", sep.outputs["Z"], sep.outputs["Z"])))
    front = mth("LESS_THAN", sep.outputs["Y"], 0.0)
    # normal eyes (everyone but the hero): white sclera, a smaller warm-brown iris, dark pupil, clear catchlight
    c = mix(mth("GREATER_THAN", sep.outputs["Z"], radius * 0.62), lin("#f4f1ec"), lin("#c9c4bd"))
    IR = radius * 0.37
    c = mix(mth("MULTIPLY", mth("LESS_THAN", r, IR), front), c, mix(mth("DIVIDE", r, IR), lin(iris), lin("#2a1d14")))
    c = mix(mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.15), front), c, lin("#08070a"))
    gx = mth("SUBTRACT", sep.outputs["X"], radius * 0.13); gz = mth("SUBTRACT", sep.outputs["Z"], radius * 0.14)
    glint = mth("LESS_THAN", mth("ADD", mth("MULTIPLY", gx, gx), mth("MULTIPLY", gz, gz)), (radius * 0.085) ** 2)
    c = mix(mth("MULTIPLY", glint, front), c, lin("#ffffff"))
    e = N.new("ShaderNodeEmission"); L.new(c, e.inputs["Color"]); L.new(e.outputs[0], out.inputs[0])
    _cache[key] = m
    return m

def void_eye_mat(radius):
    """The hero's eyes: black sclera with a small glowing white iris (only he has them)."""
    key = ("void_eye", round(radius, 4))
    if key in _cache:
        return _cache[key]
    m = bpy.data.materials.new("eye_void")
    N, L, mth, mix = _nodes(m)
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    r = mth("SQRT", mth("ADD", mth("MULTIPLY", sep.outputs["X"], sep.outputs["X"]), mth("MULTIPLY", sep.outputs["Z"], sep.outputs["Z"])))
    front = mth("LESS_THAN", sep.outputs["Y"], 0.0)
    c = lin("#040405")
    ring = mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.3), front)
    c = mix(ring, c, lin("#f4f8ff"))
    c = mix(mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.12), front), c, lin("#9fb2c8"))
    e = N.new("ShaderNodeEmission"); L.new(c, e.inputs["Color"]); e.inputs["Strength"].default_value = 1.6
    L.new(e.outputs[0], out.inputs[0])
    _cache[key] = m
    return m

def ink_mat():
    """Shell faces that face the camera draw dark ink; the rest are invisible."""
    if "ink" not in _cache:
        m = bpy.data.materials.new("ink"); N, L, mth, mix = _nodes(m)
        out = N.new("ShaderNodeOutputMaterial"); geo = N.new("ShaderNodeNewGeometry")
        e = N.new("ShaderNodeEmission"); e.inputs["Color"].default_value = lin("#0b0c10")
        t = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
        lp = N.new("ShaderNodeLightPath")   # only the camera sees the ink: lights and bounces pass through the shell
        hide = mth("MAXIMUM", geo.outputs["Backfacing"], mth("SUBTRACT", 1.0, lp.outputs["Is Camera Ray"]))
        L.new(hide, mx.inputs[0]); L.new(e.outputs[0], mx.inputs[1]); L.new(t.outputs[0], mx.inputs[2])
        L.new(mx.outputs[0], out.inputs[0]); m.use_backface_culling = True; _cache["ink"] = m
    return _cache["ink"]

def glow_mat(hexc, strength):
    key = ("glow", hexc, strength)
    if key not in _cache:
        m = bpy.data.materials.new(f"glow_{hexc}"); N, L, mth, mix = _nodes(m)
        out = N.new("ShaderNodeOutputMaterial"); e = N.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = lin(hexc); e.inputs["Strength"].default_value = strength
        L.new(e.outputs[0], out.inputs[0]); _cache[key] = m
    return _cache[key]

# ---------------------------------------------------------------- mesh helpers
def make_mesh(name, coll, V, faces, offset=None):
    used = sorted({i for f in faces for i in f}); remap = {o: n for n, o in enumerate(used)}
    co = [V[i] + (offset[i] if offset else Vector()) for i in used]
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(c) for c in co], [], [[remap[i] for i in f] for f in faces])
    me.validate(); me.update()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    return ob, used

def assign_weights(ob, used, per_vert):
    for ni, oi in enumerate(used):
        for bone, w in per_vert.get(oi, ()):
            vg = ob.vertex_groups.get(bone) or ob.vertex_groups.new(name=bone)
            vg.add([ni], w, "REPLACE")

def weights_from_body(ob, body_kd, body_used, per_vert, k=4, bias=None):
    """Copy skin weights from the nearest body vertices (inverse-distance blend)."""
    acc = {}
    mw = ob.matrix_world
    for v in ob.data.vertices:
        tot = 0.0; ws = {}
        for co, idx, dist in body_kd.find_n(mw @ v.co, k):
            f = 1.0 / (dist + 1e-4); tot += f
            for bone, w in per_vert.get(body_used[idx], ()):
                ws[bone] = ws.get(bone, 0) + w * f
        ws = {b: w / tot for b, w in ws.items()}
        if bias:
            ws = bias(v.co, ws)
        for bone, w in ws.items():
            acc.setdefault(bone, []).append((v.index, w))
    for bone, lst in acc.items():
        vg = ob.vertex_groups.get(bone) or ob.vertex_groups.new(name=bone)
        for i, w in lst:
            vg.add([i], w, "REPLACE")

def snap_edge(ob, pick, width, cx):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for v in bm.verts:
        if v.is_boundary and pick(v.co):
            v.co.x = cx + (1 if v.co.x >= cx else -1) * width(v.co)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()

def vnormals(V, faces):
    n = {}
    for f in faces:
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        fn = (b - a).cross(c - a)
        for i in f:
            n[i] = n.get(i, Vector()) + fn
    for i in n:
        if n[i].length:
            n[i].normalize()
    return n

def add_mods(ob, arm, subsurf=1, solidify=0.0, outline=1.0):
    if solidify:
        m = ob.modifiers.new("solid", "SOLIDIFY"); m.thickness = solidify; m.offset = 1.0
        m.use_even_offset = False; m.use_quality_normals = True
    m = ob.modifiers.new("arm", "ARMATURE"); m.object = arm
    if solidify:  # armature must run before solidify
        ob.modifiers.move(ob.modifiers.find("arm"), 0)
    if subsurf:
        s = ob.modifiers.new("sub", "SUBSURF"); s.levels = 1; s.render_levels = subsurf
    if OUTLINE and outline:   # inverted-hull ink line (Cycles-friendly replacement for Freestyle)
        o = ob.modifiers.new("ink", "SOLIDIFY"); o.thickness = OUTLINE * outline; o.offset = 1.0
        o.use_flip_normals = True; o.use_rim = False; o.material_offset = 1; o.use_quality_normals = True
        while len(ob.data.materials) < 1:
            ob.data.materials.append(None)
        ob.data.materials.append(ink_mat())
    ob.parent = arm

def bone_parent(ob, arm, bone):
    """Parent ob to a pose bone keeping its current world transform."""
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    mw = ob.matrix_world.copy()
    ob.parent = arm; ob.parent_type = "BONE"; ob.parent_bone = bone
    ob.matrix_parent_inverse = (arm.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.length, 0))).inverted()
    ob.matrix_basis = mw

# ---------------------------------------------------------------- build
def build(coll, location=(0, 0, 0), style=None, pose_mode="walk", heading=0.0):
    st = dict(HERO, **HERO_LOOK) if style is None or style is HERO else dict(HERO)
    st.update(style if style is not None and style is not HERO else {})
    V, F, G = load_base(st["body"])
    sk, per_vert = load_rig()
    if st.get("vary") is not None and not st["body"].startswith("kid"):   # everyone's own build
        apply_targets(V, {k[:-len(".target")]: w for k, w in
                          vary_body(st["vary"], "f" if st["body"] == "f" else "m").items()})
    if st["body"] in ("m_muscle", "m_fit"):   # keep the lean face and neck on the muscular body (the muscle target widens the jaw)
        Vl = load_base("m_lean")[0]
        nidx = sk["joints"][sk["bones"]["neck02"]["head"]]
        cm = sum((V[i] for i in nidx), Vector()) / len(nidx); cl = sum((Vl[i] for i in nidx), Vector()) / len(nidx)
        for i in range(len(V)):
            t = max(0.0, min(1.0, (Vl[i].z - cl.z + 0.01) / 0.05))
            if t > 0:
                V[i] = V[i].lerp(Vl[i] + (cm - cl), t)
    if st.get("face"):
        apply_face(V, st["face"])
    if st.get("vary") is not None:                                        # ...and everyone's own face
        apply_targets(V, vary_face(st["vary"], pretty=st.get("face") == "kstar_f"))
    body_faces = [f for f, g in zip(F, G) if g == "body"]
    zmin = min(V[i].z for f in body_faces for i in f)
    for v in V:
        v.z -= zmin
    if st.get("manhwa_head"):
        jj = lambda n: sum((V[i] for i in sk["joints"][sk["bones"][n]["head"]]), Vector()) / len(sk["joints"][sk["bones"][n]["head"]])
        nz = jj("neck03").z; eye_z = jj("eye.L").z
        piv = Vector((0.0, jj("head").y, nz))
        for v in V:
            if v.z <= nz:
                continue
            t = min(1.0, (v.z - nz) / 0.07)
            k = 1.0 - 0.075 * t                          # ~8% smaller head: longer-looking webtoon body
            d = v - piv; v.x = piv.x + d.x * k * (1.0 - 0.12 * t); v.y = piv.y + d.y * k; v.z = piv.z + d.z * k
            jaw = max(0.0, min(1.0, (eye_z - 0.02 - v.z) / 0.085)) * t   # cheekbone -> chin: V-line jaw
            v.x *= 1.0 - 0.2 * jaw
            v.z -= (0.0 if st.get("jaw_v") else 0.01) * jaw     # slightly longer chin (not on the short idol face)
    if st.get("jaw_v"):   # idol V-line: taper the face from the cheekbones to a small chin; the neck stays as it is
        ny = jj("neck03").y
        NOTFACE = ("neck", "spine", "clavicle", "shoulder", "breast", "upperarm", "pectoral")
        hw = {i: sum(w for b, w in lst if not b.startswith(NOTFACE)) for i, lst in per_vert.items()}
        face = [i for i, w in hw.items() if w > 0.5 and nz - 0.08 < V[i].z < eye_z and abs(V[i].x) < 0.13]
        zc = min(V[i].z for i in face)
        for i in face:
            v = V[i]; w = min(1.0, (hw[i] - 0.5) / 0.4)
            front = max(0.0, min(1.0, (ny - 0.03 - v.y) / 0.04))
            rn = 0.04 - 0.028 * front
            if abs(v.x) <= rn:
                continue
            j = max(0.0, min(1.0, (eye_z - 0.015 - v.z) / (eye_z - 0.015 - zc))); j = j * j * (3 - 2 * j)
            k = 1.0 - st["jaw_v"] * j * w
            v.x = math.copysign(rn + (abs(v.x) - rn) * k, v.x)
    if st.get("vtaper"):   # webtoon fighter build: wide shoulders and lats, narrow waist, arms pushed out
        jz = lambda n: sum(V[i].z for i in sk["joints"][sk["bones"][n]["head"]]) / len(sk["joints"][sk["bones"][n]["head"]])
        waist = jz("spine04"); chest = jz("spine01"); nk = jz("neck01")
        dm = {i: max(lst, key=lambda t: t[1])[0] for i, lst in per_vert.items()}
        torso = ("spine", "pelvis", "breast", "clavicle", "shoulder", "neck01", "pectoral")
        arms = ("upperarm", "lowerarm", "wrist", "finger", "metacarpal")
        def sx(z):   # torso width factor by height
            if z < waist - 0.12: return 1.0
            if z < waist: return 1.0 - 0.07 * (z - (waist - 0.12)) / 0.12
            if z < chest: return 0.93 + 0.23 * (z - waist) / max(chest - waist, 1e-3)
            return 1.16 - 0.14 * min(1.0, (z - chest) / max(nk - chest, 1e-3))
        for i, v in enumerate(V):
            b = dm.get(i, "")
            if b.startswith(torso):
                f = sx(v.z); v.x *= f
                if waist < v.z < nk: v.y *= 1.0 + 0.05 * (f - 1.0) / 0.12   # deeper chest
            elif b.startswith(arms):
                v.x += math.copysign(0.022, v.x)                          # arms ride on the wider shoulders
        # thicker arms: push arm skin away from the bone axis (biceps/triceps and forearm mass)
        jp = lambda n: sum((V[i] for i in sk["joints"][sk["bones"][n]["head"]]), Vector()) / len(sk["joints"][sk["bones"][n]["head"]])
        for side in ("L", "R"):
            sh_, el, wr = jp(f"upperarm01.{side}"), jp(f"lowerarm01.{side}"), jp(f"wrist.{side}")
            for i, v in enumerate(V):
                b = dm.get(i, "")
                if not b.endswith("." + side) or not b.startswith(("upperarm", "lowerarm")):
                    continue
                a0, a1, gain = (sh_, el, 0.38) if b.startswith("upperarm") else (el, wr, 0.24)
                ax = a1 - a0; t = max(0.0, min(1.0, (v - a0).dot(ax) / ax.length_squared))
                bulge = gain * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.7     # belly of the muscle mid-segment
                foot = a0 + ax * t; r = v - foot
                V[i] = foot + r * (1.0 + bulge)
    jpos = {j: sum((V[i] for i in idx), Vector()) / len(idx) for j, idx in sk["joints"].items()}
    dom = {i: max(lst, key=lambda t: t[1])[0] for i, lst in per_vert.items()}
    def region(f, names):
        return all(any(dom.get(i, "").startswith(n) for n in names) for i in f)
    J = lambda b, end="head": jpos[sk["bones"][b][end]]

    # --- armature
    arm_d = bpy.data.armatures.new("rig"); arm = bpy.data.objects.new("rig", arm_d); coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name, b in sk["bones"].items():
        e = arm_d.edit_bones.new(name); e.head = jpos[b["head"]]; e.tail = jpos[b["tail"]]
        if (e.tail - e.head).length < 1e-4:
            e.tail = e.head + Vector((0, 0, 0.01))
        eb[name] = e
    for name, b in sk["bones"].items():
        if b["parent"]:
            eb[name].parent = eb[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT"); arm.select_set(False)
    arm["body"] = st["body"]

    nrm = vnormals(V, body_faces)
    objs = []
    def finish(ob, used=None, subsurf=1, solidify=0.0, kdw=None):
        if used is not None:
            assign_weights(ob, used, per_vert)
        add_mods(ob, arm, subsurf=subsurf * st.get("subsurf", 1), solidify=solidify); objs.append(ob)

    # --- skin: head, neck, hands (+ lower legs under a skirt)
    keep = ["head", "jaw", "neck", "eye", "oculi", "orbicularis", "oris", "levator", "risorius", "temporalis",
            "special", "tongue", "wrist", "finger", "metacarpal", "lowerarm02"]
    if st.get("sleeves") == "short":
        keep += ["lowerarm01", "upperarm02"]
    skin_faces = [f for f in body_faces if region(f, keep)]
    vz = J("neck01").z - 0.02 - 0.12                     # V-neck: bottom of the V, ~12 cm under the collarbone notch
    def in_vneck(f):
        c = sum((V[i] for i in f), Vector()) / len(f)
        return c.y < -0.025 and c.z > vz and abs(c.x) < (c.z - vz) * 0.62
    if st.get("vneck"):
        skin_faces += [f for f in body_faces if in_vneck(f) and not region(f, keep)]
    if st.get("socks"):   # school uniform: bare legs between hem and knee socks
        knee_z0 = jpos[sk["bones"]["lowerleg01.L"]["head"]].z
        skin_faces += [f for f in body_faces if region(f, ("upperleg", "lowerleg")) and min(V[i].z for i in f) > knee_z0 - 0.08]
    SKIN = cel(st["skin"][0], st["skin"][1], rim="#ffe6d2", name="skin", crease=st.get("crease", 0.0), crease_zmax=J("neck01").z - 0.03)
    skin, used = make_mesh("skin", coll, V, skin_faces); skin.data.materials.append(SKIN); finish(skin, used)

    bused = sorted({i for f in body_faces for i in f})
    kd = kdtree.KDTree(len(bused))
    for n, i in enumerate(bused):
        kd.insert(V[i], n)
    kd.balance()

    pelvis_z = J("spine05").z; neck_z = J("neck01").z; chin_z = J("head").z
    sternum_z = neck_z - 0.02

    # --- top (knit): fits the body 4 mm off the skin
    TOP = ("spine", "clavicle", "shoulder", "upperarm", "lowerarm01", "breast", "neck01", "neck02", "pelvis")
    if st.get("sleeves") == "short":   # fitted T-shirt: sleeve ends on the upper arm
        TOP = ("spine", "clavicle", "shoulder", "upperarm01", "breast", "neck01", "neck02", "pelvis")
    neck_cut = chin_z - (0.035 if st.get("turtleneck", True) else 0.075)
    sleeve = ("lowerarm",) if (not st.get("coat") or st.get("drape")) and st.get("sleeves") != "short" else ()
    tn_faces = [f for f in body_faces if region(f, TOP + sleeve) and min(V[i].z for i in f) > pelvis_z - 0.12
                and max(V[i].z for i in f) < neck_cut and not (st.get("vneck") and in_vneck(f))]
    off = {i: nrm[i] * 0.004 for f in tn_faces for i in f}
    tn, used = make_mesh("top", coll, V, tn_faces, off)
    if st.get("vneck"):   # clean straight V edges
        snap_edge(tn, lambda co: co.y < -0.02 and co.z > vz - 0.01 and abs(co.x) < (co.z - vz) * 0.62 + 0.025,
                  lambda co: max(0.004, (co.z - vz) * 0.62), 0.0)
    tn.data.materials.append(cel(st["top"][0], st["top"][1], rim="#fff4e0" if sum(lin(st["top"][0])[:3]) > 0.3 else "#4a5874", rim_amt=0.8 if sum(lin(st["top"][0])[:3]) > 0.3 else 0.6, name="knit", crease=st.get("crease", 0.0))); finish(tn, used)

    # --- coat / jacket
    if st.get("coat"):
        dark = sum(lin(st["coat"][0])[:3]) < 0.3
        COAT = cel(st["coat"][0], st["coat"][1], rim="#56668a" if dark else "#d6efff", rim_amt=0.6 if dark else 0.8, name="coat")
        wide = st.get("open_coat", False)       # worn fully open: the shirt shows from collar to belt
        def gap_w(z):
            return 0.07 + 0.045 * min(1.0, max(0.0, (z - pelvis_z) / (sternum_z - pelvis_z)))
        def open_front(f):
            c = sum((V[i] for i in f), Vector()) / len(f)
            if wide:
                return c.y < -0.02 and abs(c.x) < gap_w(c.z)
            return c.y < -0.02 and c.z > sternum_z - 0.13 and abs(c.x) < 0.012 + max(0.0, sternum_z - c.z) * 0.22
        drape = st.get("drape", False)         # jacket thrown over the shoulders, arms not in the sleeves
        sh = J("upperarm01.L"); sh_z, sh_x = sh.z, abs(sh.x)
        def side_push(x, z):   # the cape falls from the shoulder points and flares out to the sides
            k = min(1.0, max(0.0, (abs(x) - 0.05) / 0.1))
            return math.copysign(0.42 * max(0.0, sh_z + 0.03 - z) * k, x)
        def to_torso(co, ws):  # rigid on the chest: arm swings don't drag the cape
            out = {}
            for b, w in ws.items():
                key = "spine01" if b.startswith(("upperarm", "lowerarm", "wrist", "finger", "metacarpal", "shoulder")) else b
                out[key] = out.get(key, 0) + w
            return out
        if drape:
            build_drape_coat(coll, arm, V, body_faces, dom, kd, bused, per_vert, J, st, COAT, sh, neck_z, pelvis_z,
                             sternum_z, gap_w, objs)
        COAT_SET = ("spine", "clavicle", "shoulder", "upperarm", "lowerarm", "breast", "pelvis")
        coat_faces = [] if drape else [f for f in body_faces if region(f, COAT_SET) and min(V[i].z for i in f) > pelvis_z - 0.1
                      and max(V[i].z for i in f) < neck_z + 0.01 and not open_front(f)]
        off = {i: nrm[i] * (0.013 if dom.get(i, "").startswith(("lowerarm", "upperarm")) else 0.016) for f in coat_faces for i in f}
        if not drape:
          cu, used = make_mesh("coat_upper", coll, V, coat_faces, off); cu.data.materials.append(COAT)
        if drape:
            pass
        elif wide:
            snap_edge(cu, lambda co: co.y < -0.02 and abs(co.x) < 0.14, lambda co: gap_w(co.z) + 0.004, 0.0)
        else:
            snap_edge(cu, lambda co: co.y < -0.02 and co.z > sternum_z - 0.14 and abs(co.x) < 0.06,
                      lambda co: 0.028 + max(0.0, sternum_z - co.z) * 0.22, 0.0)
        if not drape:
            finish(cu, used, solidify=0.006)
        if st.get("lapels") and wide and not drape:   # notched suit lapels folded back along the open front
            body_bvh_l = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], body_faces)
            zb, zn, zt = pelvis_z + 0.13, sternum_z - 0.035, neck_z + 0.005
            LAP = cel(st["coat"][1] if not dark else st["coat"][0], st["coat"][1], rim="#d6efff", rim_amt=0.6, name="lapel")
            c0 = [int(st["coat"][0][k:k + 2], 16) for k in (1, 3, 5)]; c1 = [int(st["coat"][1][k:k + 2], 16) for k in (1, 3, 5)]
            lap_col = "#%02x%02x%02x" % tuple(int(a * 0.8 + b * 0.2) for a, b in zip(c0, c1))   # a shade under the coat
            LAP = cel(lap_col, st["coat"][1], rim="#e6f4ff", rim_amt=0.6, name="lapel") if not dark else COAT
            bm = bmesh.new()
            for sx in (1, -1):
                rows = []
                for k in range(16):
                    z = zb + (zt - zb) * k / 15
                    if z < zn:
                        w = 0.068 * (z - zb) / (zn - zb)
                    elif z < zn + 0.012:
                        w = 0.022                                   # the notch
                    else:
                        w = 0.04 * (1 - 0.5 * (z - zn) / (zt - zn))  # collar
                    row = []
                    for u in (0.0, 1.0):
                        x = sx * (gap_w(min(z, sternum_z)) + 0.004 + u * w)
                        hit = body_bvh_l.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))
                        p_ = (hit[0] + hit[1] * (0.038 if drape else 0.024)) if hit[0] else Vector((x, -0.1, z))
                        row.append(bm.verts.new(p_))
                    rows.append(row)
                for r0, r1 in zip(rows, rows[1:]):
                    bm.faces.new((r0[0], r1[0], r1[1], r0[1]) if sx > 0 else (r0[0], r0[1], r1[1], r1[0]))
            me = bpy.data.meshes.new("lapels"); bm.to_mesh(me); bm.free()
            lp = bpy.data.objects.new("lapels", me); coll.objects.link(lp); lp.data.materials.append(LAP)
            weights_from_body(lp, kd, bused, per_vert, k=4); add_mods(lp, arm, subsurf=0, solidify=0.003, outline=1.0)
            objs.append(lp)
        if not drape:
          skirt_piece("coat_skirt", coll, V, F, G, kd, bused, per_vert, COAT, st.get("hem", 0.36), st.get("open_skirt", True),
                    flare=st.get("coat_flare", (0.10, 0.22)), finish=finish, gap=0.075 if wide else 0.035,
                    side=(lambda x, z0, t: side_push(x, z0) + math.copysign(0.18 * t * min(1.0, max(0.0, (abs(x) - 0.05) / 0.1)), x))
                    if drape else None)

    # --- police tactical vest: navy shell over the jacket, reflective band, white chest patch
    if st.get("vest"):
        VEST = cel(st["vest"], "#070b16", rim="#5a6b90", rim_amt=0.6, name="vest")
        VS = ("spine", "breast", "pelvis", "clavicle")
        vf = [f for f in body_faces if region(f, VS) and pelvis_z + 0.07 < min(V[i].z for i in f)
              and max(V[i].z for i in f) < neck_z - 0.01]                  # ends at the belt, like a real duty vest
        off = {i: nrm[i] * 0.034 for f in vf for i in f}
        ve, used = make_mesh("vest", coll, V, vf, off); ve.data.materials.append(VEST); finish(ve, used, solidify=0.012)
        band_z = (sternum_z + pelvis_z) / 2 - 0.02
        bf = [f for f in vf if band_z < min(V[i].z for i in f) and max(V[i].z for i in f) < band_z + 0.06]
        off = {i: nrm[i] * 0.048 for f in bf for i in f}
        bd, used = make_mesh("vest_band", coll, V, bf, off)
        bd.data.materials.append(cel("#d6f25c", "#8fa832", rim="#f4ffc0", name="reflective", glow=1.6)); finish(bd, used)
        # black duty belt over the tucked-in shirt
        blf = [f for f in body_faces if region(f, ("spine", "pelvis")) and pelvis_z + 0.015 < min(V[i].z for i in f)
               and max(V[i].z for i in f) < pelvis_z + 0.075]
        off = {i: nrm[i] * 0.02 for f in blf for i in f}
        bl, used = make_mesh("duty_belt", coll, V, blf, off)
        bl.data.materials.append(cel("#111114", "#050506", rim="#5a6b90", rim_amt=0.5, name="belt")); finish(bl, used, solidify=0.008)
        pf = [f for f in vf if sum(V[i].y for i in f) / len(f) < -0.05 and 0.02 < sum(V[i].x for i in f) / len(f) < 0.1
              and sternum_z - 0.13 < min(V[i].z for i in f) and max(V[i].z for i in f) < sternum_z - 0.05]
        if pf:   # "POLICE" patch
            off = {i: nrm[i] * 0.05 for f in pf for i in f}
            pt, used = make_mesh("vest_patch", coll, V, pf, off); pt.data.materials.append(cel("#f2f2ee", "#a9acb4", name="patch"))
            finish(pt, used)

    # --- legwear
    if st["legs"] == "skirt":
        skirt_piece("skirt", coll, V, F, G, kd, bused, per_vert, cel(st["leg_col"][0], st["leg_col"][1], rim="#ffe0f0", name="skirt"),
                    st.get("skirt_hem", 0.52), False, flare=(0.03, 0.12), finish=finish, solid=0.003)
        legs = None if st.get("socks") else trousers(coll, V, F, G, sk, jpos, pelvis_z, per_vert, 0.0025, straight=False,
                        mat=cel(st.get("tights", "#23222a"), "#0d0c10", rim="#6d6a80", name="tights"))
    elif st["legs"] == "shorts":
        knee_z = jpos[sk["bones"]["lowerleg01.L"]["head"]].z
        legs = trousers(coll, V, F, G, sk, jpos, pelvis_z, per_vert, 0.014, straight=False, zlo=knee_z + 0.06,
                        mat=cel(st["leg_col"][0], st["leg_col"][1], rim="#c9e8ff", name="shorts"))
    else:
        legs = trousers(coll, V, F, G, sk, jpos, pelvis_z, per_vert, 0.009, straight=True,
                        mat=cel(st["leg_col"][0], st["leg_col"][1], rim="#c9e8ff", name="trousers"))
    if legs and st.get("creases"):   # pressed trousers: a crease line down the front of each leg
        tb = bvhtree.BVHTree.FromObject(legs, bpy.context.evaluated_depsgraph_get())
        bm = bmesh.new()
        for side in ("L", "R"):
            hip = jpos[sk["bones"][f"upperleg01.{side}"]["head"]]; knee = jpos[sk["bones"][f"lowerleg01.{side}"]["head"]]
            ank = jpos[sk["bones"][f"foot.{side}"]["head"]]
            row = []
            for k in range(22):
                z = (pelvis_z - 0.06) - k / 21 * (pelvis_z - 0.06 - (ank.z + 0.05))
                a, b = (hip, knee) if z > knee.z else (knee, ank)
                u = (a.z - z) / max(1e-4, a.z - b.z); x = a.x + (b.x - a.x) * u
                hit = tb.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))
                if hit[0]:
                    p_ = hit[0] + hit[1] * 0.0018
                    row.append((bm.verts.new(p_ + Vector((-0.0016, 0, 0))), bm.verts.new(p_ + Vector((0.0016, 0, 0)))))
            for r0, r1 in zip(row, row[1:]):
                bm.faces.new((r0[0], r1[0], r1[1], r0[1]))
        me = bpy.data.meshes.new("trouser_creases"); bm.to_mesh(me); bm.free()
        cr = bpy.data.objects.new("trouser_creases", me); coll.objects.link(cr)
        cr.data.materials.append(cel(st["leg_col"][1], "#2a2b30", rim=st["leg_col"][1], name="crease_line"))
        weights_from_body(cr, kd, bused, per_vert, k=4); add_mods(cr, arm, subsurf=0, outline=0); objs.append(cr)
    if legs: finish(legs)
    if st.get("socks"):
        knee_z = jpos[sk["bones"]["lowerleg01.L"]["head"]].z
        sock = trousers(coll, V, F, G, sk, jpos, pelvis_z, per_vert, 0.003, straight=False, zhi=knee_z - 0.08,
                        mat=cel(st["socks"], "#b9bcc4", rim="#ffffff", name="socks"))
        sock.name = "socks"; finish(sock)
    uniform_bits(coll, arm, V, J, st, sternum_z, pelvis_z, finish)

    # --- hair
    hair_objs = make_hair(coll, V, body_faces, region, nrm, J, st, per_vert)
    kd_h, bused_h = kd, bused
    for ob, used, sol in hair_objs:
        if ob.get("hang"):    # long locks: head-driven at the scalp, neck/chest-driven where they hang
            weights_from_body(ob, kd_h, bused_h, per_vert, k=4)
            add_mods(ob, arm, subsurf=1, solidify=0.004, outline=0.5); objs.append(ob)
        elif ob.get("tufts"):
            vg = ob.vertex_groups.new(name="head"); vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
            if ob.get("locks"):
                add_mods(ob, arm, subsurf=1, solidify=0.004, outline=0.5)
            else:
                add_mods(ob, arm, subsurf=0, outline=0.35)
            objs.append(ob)
        elif ob.name.startswith("hair_fade"):
            assign_weights(ob, used, per_vert); add_mods(ob, arm, subsurf=st.get("subsurf", 1), outline=0); objs.append(ob)
        else:
            finish(ob, used, solidify=sol)
    if st.get("locks") and st["hair"] == "short":
        add_locks(coll, arm, V, J, hair_objs[0][0], st, objs)

    # --- eyes and lash lines
    for side in ("l", "r"):
        ef = [f for f, g in zip(F, G) if g == f"helper-{side}-eye"]
        eidx = {i for f in ef for i in f}; c = sum((V[i] for i in eidx), Vector()) / len(eidx)
        rad = sum((V[i] - c).length for i in eidx) / len(eidx)
        ob, used = make_mesh(f"eye_{side}", coll, [v - c for v in V], ef)
        ob.location = c; ob.data.materials.append(eye_mat(rad, st.get("iris", "#5a4232"), st.get("void_eyes", False))); assign_weights(ob, used, per_vert); add_mods(ob, arm, subsurf=2, outline=0); objs.append(ob)
        for k in (1, 2):
            lf = [f for f, g in zip(F, G) if g == f"helper-{side}-eyelashes-{k}"]
            if lf:
                lo, used = make_mesh(f"lash_{side}{k}", coll, V, lf)
                lo.data.materials.append(cel("#0c0c0f", "#050506", rim="#0c0c0f", name="lash")); add_mods(lo, arm, subsurf=0, outline=0); assign_weights(lo, used, per_vert); objs.append(lo)

    # --- brows ray-cast onto the forehead
    skin_bvh = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], skin_faces)
    bm = bmesh.new()
    thick = 0.0034 if st["body"] not in ("f", "kid_f") else 0.0024
    for sx in (1, -1):
        ec = J("eye.L" if sx > 0 else "eye.R")
        rows = []
        for k in range(13):
            s = k / 12
            x = ec.x + sx * (-0.016 + 0.036 * s)
            if st.get("brow_style") == "sharp":   # low, straight and rising toward a tapered tail: a sharp webtoon brow
                x = ec.x + sx * (-0.02 + 0.04 * s)
                zc = ec.z + 0.0145 + 0.008 * math.sin(math.pi * 0.5 * min(s * 1.25, 1)) - 0.005 * max(0.0, s - 0.75) / 0.25
                half = thick * 1.2 * (1 - 0.7 * s ** 1.5) + 0.0005
            else:
                zc = ec.z + 0.019 + 0.003 * math.sin(math.pi * min(s * 1.15, 1)) - 0.004 * s
                half = thick * (1 - 0.55 * s) + 0.0006
            ring = []
            for dz in (-half, half):
                hit = skin_bvh.ray_cast(Vector((x, ec.y - 0.3, zc + dz)), Vector((0, 1, 0)))
                p = hit[0] if hit[0] else Vector((x, ec.y - 0.012, zc + dz))
                n = hit[1] if hit[1] else Vector((0, -1, 0))
                ring.append(bm.verts.new(p + n * 0.0009))
            rows.append(ring)
        for a, b in zip(rows, rows[1:]):
            bm.faces.new((a[0], b[0], b[1], a[1]) if sx > 0 else (a[0], a[1], b[1], b[0]))
    me = bpy.data.meshes.new("brows"); bm.to_mesh(me); bm.free()
    brows = bpy.data.objects.new("brows", me); coll.objects.link(brows)
    brows.data.materials.append(cel(st["brows"], "#0b0a09", rim=st["brows"], name="brow"))
    weights_from_body(brows, kd, bused, per_vert, k=2); add_mods(brows, arm, subsurf=0, outline=0); objs.append(brows)

    # --- idol fringe: flat tapered clumps lying on the forehead, swept toward the part
    if st["hair"] == "idol":
        HM = hair_objs[0][0].data.materials[0]
        ecL, ecR = J("eye.L"), J("eye.R"); mid = (ecL + ecR) / 2; ez = mid.z
        bm = bmesh.new()
        CLUMPS = ((-0.060, 0.030, 0.010, 0.022), (-0.044, 0.016, 0.014, 0.026), (-0.026, 0.008, 0.018, 0.028),
                  (-0.008, 0.012, 0.022, 0.027), (0.010, 0.004, 0.026, 0.026), (0.028, 0.016, 0.026, 0.024),
                  (0.046, 0.034, 0.020, 0.018))
        for x0, tip_z, sweep, w0 in CLUMPS:      # root x, tip height above the eyes, sideways sweep, root width
            pts = []
            for k in range(7):
                t = k / 6
                x = mid.x + x0 + sweep * t ** 1.4; z = ez + 0.105 - (0.105 - tip_z) * t ** 0.9
                hit = skin_bvh.ray_cast(Vector((x, mid.y - 0.3, z)), Vector((0, 1, 0)))
                if not hit[0]:
                    hit = skin_bvh.find_nearest(Vector((x, mid.y, z)))
                p, n = hit[0], hit[1]
                pts.append((p + n * (0.03 - 0.024 * t ** 0.7), n))
            ring = []
            for k, (p, n) in enumerate(pts):
                t = k / 6; d = (pts[min(k + 1, 6)][0] - pts[max(k - 1, 0)][0]).normalized()
                side = d.cross(n).normalized(); w = w0 * (1 - t) ** 0.8 * 0.5 + 0.0004
                ring.append((bm.verts.new(p - side * w), bm.verts.new(p + side * w)))
            for a, b in zip(ring, ring[1:]):
                bm.faces.new((a[0], b[0], b[1], a[1]))
        me = bpy.data.meshes.new("fringe"); bm.to_mesh(me); bm.free()
        fringe = bpy.data.objects.new("fringe", me); coll.objects.link(fringe); fringe.data.materials.append(HM)
        weights_from_body(fringe, kd, bused, per_vert, k=2); add_mods(fringe, arm, subsurf=1, solidify=0.004, outline=1.0)
        objs.append(fringe)

    # --- long hair: a curtain falling from under the cap down the back, clear of the neck and shoulders
    if st["hair"] == "long":
        HM = hair_objs[0][0].data.materials[0]
        body_bvh = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], body_faces)
        eyeL = J("eye.L"); sy = eyeL.y + 0.095
        drop = st.get("hair_len", 0.3)
        A = [math.radians(-12 + 204 * j / 16) for j in range(17)]
        rmax = [0.0] * len(A); bm = bmesh.new(); rows = []
        for k in range(13):
            t = k / 12; z = eyeL.z + 0.01 - drop * t; row = []
            for j, a in enumerate(A):
                d = Vector((math.cos(a), math.sin(a), 0)); c = Vector((0, sy, z))
                hit = body_bvh.ray_cast(c + d * 0.4, -d)          # from outside toward the axis: outermost surface
                r_hit = (0.4 - hit[3]) if hit[0] else 0.0
                r = max(r_hit + 0.014 + 0.006 * t, rmax[j] + 0.004 * t)
                rmax[j] = r
                row.append(bm.verts.new(c + d * r + Vector((0, 0.01 * t, 0))))
            rows.append(row)
        for r0, r1 in zip(rows, rows[1:]):
            for j in range(len(A) - 1):
                bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
        me = bpy.data.meshes.new("hair_long"); bm.to_mesh(me); bm.free()
        lh = bpy.data.objects.new("hair_long", me); coll.objects.link(lh); lh.data.materials.append(HM)
        weights_from_body(lh, kd, bused, per_vert, k=6); add_mods(lh, arm, subsurf=1, solidify=0.008, outline=1.0)
        objs.append(lh)
    # --- hoodie: the hood lying folded behind the neck
    if st.get("hood"):
        nk = J("neck01")
        bpy.ops.mesh.primitive_torus_add(major_radius=0.085, minor_radius=0.032, major_segments=32, minor_segments=10,
                                         location=(0, nk.y + 0.035, nk.z - 0.015), rotation=(math.radians(-28), 0, 0))
        hd = bpy.context.object; hd.name = "hood"; hd.scale = (1.15, 1.0, 1.0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        for c in list(hd.users_collection): c.objects.unlink(hd)
        coll.objects.link(hd); hd.data.materials.append(cel(st["top"][0], st["top"][1], rim="#56668a", rim_amt=0.6, name="hood"))
        for p_ in hd.data.polygons: p_.use_smooth = True
        add_mods(hd, arm, subsurf=0, outline=1.0)
        hd.modifiers.remove(hd.modifiers["arm"]); bone_parent(hd, arm, "spine01"); objs.append(hd)

    # --- face mask (Korean street style): a cloth shell over the nose, mouth and chin
    if st.get("mask"):
        eL = J("eye.L"); eR = J("eye.R"); ey = (eL.y + eR.y) / 2
        mf = [f for f in skin_faces if (lambda c: c.z < eL.z - 0.022 and c.z > eL.z - 0.115 and c.y < ey + 0.035
              and abs(c.x) < 0.072)(sum((V[i] for i in f), Vector()) / len(f))]
        if mf:
            off = {i: nrm[i] * 0.005 for f in mf for i in f}
            mk, used = make_mesh("face_mask", coll, V, mf, off)
            mk.data.materials.append(cel(st["mask"], "#1a1a1e" if sum(lin(st["mask"])[:3]) > 0.5 else "#050506",
                                         rim="#ffffff", name="face_mask"))
            finish(mk, used, solidify=0.002)

    # --- lip colour: a tint over the lips (the oris muscle region), no ink line
    if st.get("lips") and not st.get("mask"):
        mc = (J("oris01") + J("oris05")) / 2                      # between upper- and lower-lip centres
        def on_lips(f):
            c = sum((V[i] for i in f), Vector()) / len(f)
            u = (c.x / 0.025) ** 2 + ((c.z - mc.z) / 0.0105) ** 2
            return u < 1.0 and c.y < mc.y + 0.012
        lf = [f for f in skin_faces if region(f, ("oris",)) and on_lips(f)]
        if lf:
            off = {i: nrm[i] * 0.0007 for f in lf for i in f}
            lp_, used = make_mesh("lips", coll, V, lf, off)
            lp_.data.materials.append(cel(st["lips"], None, rim=st["lips"], spec=0.05, spec_col="#ffd6dc", name="lips"))
            assign_weights(lp_, used, per_vert); add_mods(lp_, arm, subsurf=st.get("subsurf", 1), outline=0); objs.append(lp_)

    # --- shoes
    make_shoes(coll, V, bused, dom, kd, per_vert, st, finish)

    # --- pose, scale to height, ground, place
    posed(arm, pose_mode, st.get("head_yaw", 0.0))
    top = max(V[i].z for f in skin_faces for i in f)
    arm.scale = (st["height"] / top,) * 3
    arm.rotation_euler = (0, 0, math.radians(heading))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); low = 9.0
    for ob in objs:
        if ob.name.startswith("shoe_sole"):
            e = ob.evaluated_get(dg); mw = e.matrix_world
            low = min(low, min((mw @ v.co).z for v in e.data.vertices))
    arm["ground"] = -low if low < 9 else 0.0
    contact_shadow(coll, arm)
    arm.location = Vector(location) + Vector((0, 0, arm["ground"]))
    bpy.context.view_layer.update()
    return arm, objs

def build_drape_coat(coll, arm, V, body_faces, dom, kd, bused, per_vert, J, st, COAT, sh, neck_z, pelvis_z, sternum_z,
                     gap_w, objs):
    """A suit jacket thrown over the shoulders (arms not in the sleeves): one lofted shell hanging from the shoulders,
    open down the front with notched lapels, loose and flaring at the sides to mid-thigh; empty sleeves hang down
    its sides. Rigid on the chest; the skirt part follows the thighs a little."""
    sh_z, sh_x = sh.z, abs(sh.x)
    knee_z = J("lowerleg01.L").z
    hem_z = knee_z + 0.16
    TORSO = ("spine", "pelvis", "breast", "clavicle", "neck01", "upperleg01", "upperleg02", "pectoral")
    tv = [i for i in bused if dom.get(i, "").startswith(TORSO)]
    def extents(z):
        sl = [V[i] for i in tv if abs(V[i].z - z) < 0.025]
        if not sl:
            return 0.0, -0.1, 0.1
        return sum(v.y for v in sl) / len(sl), min(v.y for v in sl), max(v.y for v in sl)
    def smooth(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
    zs_ = sh_z + 0.035      # where the shoulder slope ends (over the top of the deltoid)
    def W(z):   # half width: collar -> shoulder slope -> hanging, flaring out to the hem
        if z > zs_:
            return 0.1 + (sh_x + 0.1 - 0.1) * smooth((neck_z + 0.005 - z) / (neck_z + 0.005 - zs_)) ** 0.7
        return sh_x + 0.1 + 0.14 * smooth((zs_ - z) / (zs_ - hem_z)) ** 1.4
    ROWS, COLS = 34, 26
    zs = [neck_z + 0.005 - (neck_z + 0.005 - hem_z) * (k / (ROWS - 1)) for k in range(ROWS)]
    prof = []
    for z in zs:
        cy, yf, yb = extents(min(z, sh_z))
        if z < pelvis_z - 0.05:
            cy2, yf2, yb2 = extents(z); yf = min(yf, yf2); yb = max(yb, yb2)
        drop = smooth((sh_z - z) / (sh_z - hem_z))
        top = smooth((z - (sh_z - 0.06)) / 0.08)               # puff over the shoulders front and back
        prof.append((z, W(z), yf - 0.03 - 0.05 * drop - 0.01 * top, yb + 0.04 + 0.08 * drop + 0.02 * top, (yf + yb) / 2))
    P = 0.55
    def point(z, w, yf, yb, cy, phi, sx, out=0.0):
        x = sx * (w + out) * max(0.0, math.sin(phi)) ** P
        c = math.cos(phi)
        y = cy - (cy - yf + out) * c if c > 0 else cy - (yb - cy + out) * c
        return Vector((x, y, z))
    bm = bmesh.new(); grid = {}
    for sx in (1, -1):
        for r, (z, w, yf, yb, cy) in enumerate(prof):
            g = gap_w(min(z, sternum_z)) + 0.006 if z < neck_z - 0.02 else 0.02
            phi0 = math.asin(min(0.999, (g / w) ** (1 / P)))
            for c in range(COLS):
                phi = phi0 + (math.pi - phi0) * c / (COLS - 1)
                grid[(sx, r, c)] = bm.verts.new(point(z, w, yf, yb, cy, phi, sx))
        for r in range(ROWS - 1):
            for c in range(COLS - 1):
                q = (grid[(sx, r, c)], grid[(sx, r + 1, c)], grid[(sx, r + 1, c + 1)], grid[(sx, r, c + 1)])
                bm.faces.new(q if sx > 0 else q[::-1])
    bmesh.ops.remove_doubles(bm, verts=[grid[(sx, r, COLS - 1)] for sx in (1, -1) for r in range(ROWS)], dist=0.002)
    me = bpy.data.meshes.new("coat_drape"); bm.to_mesh(me); bm.free()
    for p_ in me.polygons: p_.use_smooth = True
    ob = bpy.data.objects.new("coat_drape", me); coll.objects.link(ob); ob.data.materials.append(COAT)
    def bias(co, ws):
        out = {}; legs = 0.0
        low = smooth((pelvis_z - co.z) / 0.25)
        for b, w in ws.items():
            if b.startswith(("upperarm", "lowerarm", "wrist", "finger", "metacarpal", "shoulder")):
                b = "spine01"
            if b.startswith(("upperleg", "lowerleg")):
                out[b] = out.get(b, 0) + w * 0.35 * low; legs += w * (1 - 0.35 * low)
            else:
                out[b] = out.get(b, 0) + w
        out["spine05"] = out.get("spine05", 0) + legs
        return out
    weights_from_body(ob, kd, bused, per_vert, k=6, bias=bias)
    add_mods(ob, arm, subsurf=st.get("subsurf", 1), solidify=0.007); objs.append(ob)
    # notched lapels: a lighter strip folded back along each front edge, chest to collar
    LAP = cel("#bec0c6", st["coat"][1], rim="#eef6ff", rim_amt=0.7, name="lapel")
    zb, zn = pelvis_z + 0.12, sternum_z - 0.04
    bm = bmesh.new()
    for sx in (1, -1):
        rows = []
        for z, w, yf, yb, cy in prof:
            if not (zb <= z <= neck_z + 0.02):
                continue
            lw = 0.07 * (z - zb) / (zn - zb) if z < zn else (0.024 if z < zn + 0.014 else 0.045)
            g = gap_w(min(z, sternum_z)) + 0.006 if z < neck_z - 0.02 else 0.02
            row = []
            for gx in (g, g + lw):
                phi = math.asin(min(0.999, (min(gx, w * 0.98) / w) ** (1 / P)))
                row.append(bm.verts.new(point(z, w, yf, yb, cy, phi, sx, out=0.006)))
            rows.append(row)
        for r0, r1 in zip(rows, rows[1:]):
            q = (r0[0], r1[0], r1[1], r0[1])
            bm.faces.new(q if sx > 0 else q[::-1])
    me = bpy.data.meshes.new("lapels"); bm.to_mesh(me); bm.free()
    lp = bpy.data.objects.new("lapels", me); coll.objects.link(lp); lp.data.materials.append(LAP)
    weights_from_body(lp, kd, bused, per_vert, k=4, bias=bias); add_mods(lp, arm, subsurf=0, solidify=0.003); objs.append(lp)
    # empty sleeves hanging down the outside, from the shoulder seam
    bm = bmesh.new()
    for sx in (1, -1):
        rings = []
        for k in range(12):
            t = k / 11; z = sh_z - 0.03 - 0.58 * t
            cy, yf, yb = extents(min(z, sh_z)); 
            c = Vector((sx * (W(min(z, zs_ - 0.001)) + 0.04 + 0.02 * t), cy + 0.03 + 0.02 * t, z)); r = 0.06 - 0.01 * t; ring = []
            for j in range(12):
                a = 2 * math.pi * j / 12
                ring.append(bm.verts.new(c + Vector((math.cos(a) * r * 0.75, math.sin(a) * r, 0))))
            rings.append(ring)
        for r0, r1 in zip(rings, rings[1:]):
            for j in range(12):
                bm.faces.new((r0[j], r0[(j + 1) % 12], r1[(j + 1) % 12], r1[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("coat_sleeves"); bm.to_mesh(me); bm.free()
    for p_ in me.polygons: p_.use_smooth = True
    sl = bpy.data.objects.new("coat_sleeves", me); coll.objects.link(sl); sl.data.materials.append(COAT)
    weights_from_body(sl, kd, bused, per_vert, k=4, bias=bias)
    add_mods(sl, arm, subsurf=st.get("subsurf", 1), solidify=0.004); objs.append(sl)

def skirt_piece(name, coll, V, F, G, kd, bused, per_vert, mat, hem, open_front, flare, finish, solid=0.006, gap=0.035, side=None):
    """MakeHuman skirt helper re-hemmed and flared: coat skirts, jacket tails, skirts."""
    sk_faces = [f for f, g in zip(F, G) if g == "helper-skirt"]
    sidx = {i for f in sk_faces for i in f}
    top = max(V[i].z for i in sidx); bot = min(V[i].z for i in sidx)
    cx = sum(V[i].x for i in sidx) / len(sidx); cy = sum(V[i].y for i in sidx) / len(sidx)
    Vs = list(V)
    for i in sidx:
        v = V[i].copy(); t = (top - v.z) / (top - bot)
        v.z = top - t * (top - hem)
        rad = Vector((v.x - cx, v.y - cy, 0)); fl = 1.0 + flare[0] + flare[1] * t
        v.x = cx + rad.x * fl; v.y = cy + rad.y * fl + 0.015 * t
        if side:   # continue a draped cape's sideways flare (x pushed out, front and back kept)
            v.x += side(V[i].x - cx, top, t)
        Vs[i] = v
    if open_front:
        sk_faces = [f for f in sk_faces if not (sum((Vs[i] for i in f), Vector()).y / len(f) < cy - 0.03
                    and abs(sum((Vs[i] for i in f), Vector()).x / len(f) - cx) < gap + 0.03 * (top - sum((Vs[i] for i in f), Vector()).z / len(f)))]
    cs, _ = make_mesh(name, coll, Vs, sk_faces); cs.data.materials.append(mat)
    if open_front:
        snap_edge(cs, lambda co: co.y < cy - 0.02 and abs(co.x - cx) < 0.2, lambda co: gap + 0.03 * (top - co.z), cx)
    def bias(co, ws):  # hem swings less than the legs: mostly pelvis-driven
        out = {}; legs = 0.0
        for b, w in ws.items():
            if b.startswith(("upperleg", "lowerleg")):
                out[b] = w * 0.4; legs += w * 0.6
            else:
                out[b] = w
        out["spine05"] = out.get("spine05", 0) + legs
        return out
    weights_from_body(cs, kd, bused, per_vert, bias=bias)
    disp = cs.modifiers.new("folds", "DISPLACE"); tex = bpy.data.textures.new("folds", "CLOUDS")
    tex.noise_scale = 0.12; disp.texture = tex; disp.strength = 0.01; disp.texture_coords = "LOCAL"
    finish(cs, solidify=solid)

def uniform_bits(coll, arm, V, J, st, sternum_z, pelvis_z, finish):
    """School-uniform extras: necktie or bow, and a backpack. Built in the rest pose, parented to the chest bone."""
    if not (st.get("tie") or st.get("backpack") or st.get("bag")):
        return
    def front_y(z, xr=0.03):
        ys = [v.y for v in V if abs(v.x) < xr and abs(v.z - z) < 0.02]
        return min(ys) if ys else -0.12
    def back_y(z):
        ys = [v.y for v in V if abs(v.x) < 0.06 and abs(v.z - z) < 0.03]
        return max(ys) if ys else 0.12
    def box(name, loc, size, col, shade, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot); ob = bpy.context.object
        ob.name = name; ob.scale = size; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        for c in list(ob.users_collection): c.objects.unlink(ob)
        coll.objects.link(ob); ob.data.materials.append(cel(col, shade, rim="#dfe8ff", name=name))
        bev = ob.modifiers.new("bev", "BEVEL"); bev.width = min(size) * 0.3; bev.segments = 2
        finish(ob, subsurf=0); bone_parent(ob, arm, "spine01"); return ob
    tie = st.get("tie")
    if tie:
        kind, col = tie
        z0 = sternum_z - 0.025
        if kind == "bow":
            y = front_y(z0) - 0.012
            for sx in (-1, 1):
                box("bow", (sx * 0.034, y, z0), (0.05, 0.012, 0.038), col, None, (0, sx * 0.25, 0))
            box("bow", (0, y - 0.004, z0), (0.018, 0.014, 0.022), col, None)
        else:
            L = 0.2; y = front_y(z0 - L / 2) - 0.009
            box("tie", (0, y, z0 - L / 2), (0.034, 0.007, L), col, None)
            box("tie", (0, front_y(z0) - 0.01, z0 + 0.004), (0.026, 0.012, 0.022), col, None)
    bag = st.get("bag")
    if bag:   # small leather crossbody bag on the right hip, strap from the left shoulder across the chest
        col, shade = bag
        zb = pelvis_z + 0.03; bx = -0.16
        yb = front_y(zb, 0.2) - 0.02
        box("bag", (bx, yb + 0.03, zb), (0.17, 0.06, 0.12), col, shade)
        box("bag", (bx, yb, zb + 0.035), (0.172, 0.012, 0.055), shade, None)          # flap
        a = Vector((0.11, front_y(sternum_z + 0.06, 0.13) - 0.012, sternum_z + 0.06)); b = Vector((bx + 0.06, yb + 0.01, zb + 0.06))
        d = b - a; rot = d.to_track_quat("Z", "Y").to_euler()
        box("bag_strap", (a + b) / 2, (0.022, 0.006, d.length), shade, None, tuple(rot))
    bp = st.get("backpack")
    if bp:
        zc = (sternum_z + pelvis_z) / 2 + 0.03
        y = back_y(zc) + 0.075
        box("backpack", (0, y, zc), (0.27, 0.12, 0.32), bp[0], bp[1])
        box("backpack", (0, y - 0.002, zc + 0.172), (0.25, 0.11, 0.035), bp[1], None)
        for sx in (-1, 1):   # straps: over the shoulder and down the chest, outside the blazer
            zs = sternum_z - 0.12
            box("strap", (sx * 0.09, front_y(zs, 0.12) - 0.024, zs), (0.03, 0.01, 0.15), bp[1], None)

def trousers(coll, V, F, G, sk, jpos, pelvis_z, per_vert, gap, straight, mat, zlo=None, zhi=None):
    tf = [f for f, g in zip(F, G) if g == "helper-tights"]
    tidx = {i for f in tf for i in f}
    tn_ = vnormals(V, tf)
    TV = list(V)
    for i in tidx:
        v = V[i] + tn_[i] * gap
        if straight:
            side = "L" if v.x > 0 else "R"
            knee = jpos[sk["bones"][f"lowerleg01.{side}"]["head"]]; ank = jpos[sk["bones"][f"foot.{side}"]["head"]]
            if v.z < knee.z:
                t = (knee.z - v.z) / max(knee.z - ank.z, 1e-3)
                axis = knee.lerp(ank, min(t, 1)); rv = Vector((v.x - axis.x, v.y - axis.y, 0))
                want = 0.058 + 0.006 * t
                if 1e-4 < rv.length < want:
                    rv = rv.normalized() * want; v.x = axis.x + rv.x; v.y = axis.y + rv.y
        TV[i] = v
    ank_z = jpos[sk["bones"]["foot.L"]["head"]].z
    cut = ank_z - (0.035 if straight else 0.0)
    lo = cut if zlo is None else zlo; hi = pelvis_z + 0.06 if zhi is None else zhi
    tf = [f for f in tf if min(TV[i].z for i in f) > lo and max(TV[i].z for i in f) < hi]
    tr, used = make_mesh("trousers", coll, TV, tf); tr.data.materials.append(mat)
    assign_weights(tr, used, per_vert)
    if straight:
        disp = tr.modifiers.new("folds", "DISPLACE"); tex = bpy.data.textures.new("tfolds", "CLOUDS")
        tex.noise_scale = 0.06; disp.texture = tex; disp.strength = 0.004; disp.texture_coords = "LOCAL"
    return tr

def make_hair(coll, V, body_faces, region, nrm, J, st, per_vert):
    eyeL = J("eye.L")
    skull = Vector((0.0, eyeL.y + 0.095, eyeL.z + 0.02))
    head_faces = [f for f in body_faces if region(f, ("head", "temporalis", "special"))
                  and all((V[i] - skull).length < 0.165 for i in f)]
    hx = max(abs(V[i].x) for f in head_faces for i in f)
    style = st["hair"]
    def scalp(f):
        c = sum((V[i] for i in f), Vector()) / len(f)
        frontness = min(1.0, max(0.0, (eyeL.y + 0.16 - c.y) / 0.16))
        if style == "long":      # parted, forehead showing, sides to the jaw; locks and a curtain added below
            thr = eyeL.z - 0.1 + 0.16 * frontness
            return c.z > thr
        if style in ("bob", "long"):   # fringe to the brows, sides to the jaw (long: plus a curtain down the back)
            thr = eyeL.z - 0.1 + 0.125 * frontness
            return c.z > thr
        if style == "bangs":     # heavy fringe down to the brows, short tidy sides
            thr = eyeL.z - 0.05 + 0.065 * frontness
            if abs(c.x) > hx * 0.86 and c.z < eyeL.z + 0.025:
                return False
            return c.z > thr
        if style == "quiff":     # two-block: full top, short tapered sides above the ears, short at the nape
            thr = eyeL.z - 0.015 + 0.08 * frontness
            if abs(c.x) > hx * 0.86 and c.z < eyeL.z + 0.03:
                return False
            return c.z > thr
        if style == "crop":      # textured crop: hair only on top, above a high fade; a crisp hairline at the front
            return c.z > eyeL.z + 0.052 + 0.03 * frontness
        if style == "idol":      # two-block: soft fringe swept to one side, the forehead showing at the part
            side = c.x / hx
            thr = eyeL.z - 0.075 + (0.152 + 0.012 * max(0.0, side)) * frontness
            if abs(c.x) > hx * 0.84 and c.z < eyeL.z + 0.045:
                return False
            return c.z > thr
        thr = eyeL.z - 0.075 + (0.155 if style == "slick" else 0.135) * frontness   # slick: higher hairline, forehead shows
        if abs(c.x) > hx * 0.86 and c.z < eyeL.z + 0.035:
            return False
        return c.z > thr
    hf = [f for f in head_faces if scalp(f)]
    hidx = {i for f in hf for i in f}
    hc = sum((V[i] for i in hidx), Vector()) / len(hidx)
    HV = list(V)
    for i in hidx:
        p = V[i]; n = nrm[i]
        up = min(1.0, max(0.0, (p.z - eyeL.z - 0.03) / 0.1)); front = min(1.0, max(0.0, (hc.y - p.y) / 0.1))
        if style == "slick":   # swept back: volume on top, pushed toward the crown, tight sides
            th = 0.006 + 0.03 * up + 0.022 * front * up + 0.003 * math.sin(p.x * 260 + p.y * 120) * up
            HV[i] = p + n * th + Vector((0, 0.016 * up, 0.006 * up + 0.012 * front * up))   # high swept-back volume
        elif style == "quiff":   # volume on top lifted at the front, swept back; sides cut close
            thin = max(abs(n.x), max(0.0, n.y)) * (1 - min(1.0, max(0.0, (p.z - eyeL.z - 0.1) / 0.05)))   # sides + back
            th = (0.004 + 0.024 * up + 0.016 * front * up) * (1 - 0.85 * thin ** 1.2) + 0.002 * math.sin(p.x * 260 + p.y * 180) * up
            HV[i] = p + n * th + Vector((0.004 * up, 0.008 * up, 0.012 * front * up))
        elif style == "crop":    # short dense top, a little forward lift at the front edge
            th = 0.009 + 0.017 * up + 0.006 * front * up + 0.002 * math.sin(p.x * 520 + p.y * 330) * up
            HV[i] = p + n * th + Vector((0, -0.006 * front * up, 0.002 * up + 0.008 * front * up))
        elif style == "idol":    # volume on top, fringe falling forward and swept toward the part, tight sides
            side = p.x / hx
            th = 0.005 + 0.028 * up + 0.008 * front * up + 0.003 * math.sin(p.x * 300 + p.z * 200) * up
            HV[i] = p + n * th + Vector((0.004 * up * side, 0.004 * up, 0.008 * up))
        elif style == "bangs":   # thick fringe falling forward over the brow
            low = min(1.0, max(0.0, (eyeL.z + 0.06 - p.z) / 0.06)) * front
            th = 0.008 + 0.016 * up + 0.012 * low + 0.002 * math.sin(p.x * 420) * (up + low)
            HV[i] = p + n * th + Vector((0, -0.01 * low, -0.004 * low))
        elif style == "short":
            th = 0.005 + 0.017 * up + 0.012 * front * up + 0.0018 * math.sin(p.x * 380) * up
            HV[i] = p + n * th + Vector((0, 0.008 * up, 0.004 * front * up))
        elif style == "buzz":
            HV[i] = p + n * (0.003 + 0.003 * up)
        else:  # bob: even volume, flares out toward the hem
            low = min(1.0, max(0.0, (eyeL.z - p.z) / 0.1))
            th = 0.012 + 0.008 * up + 0.014 * low + 0.0012 * math.sin(p.z * 300)
            HV[i] = p + n * th + Vector((0, 0.004 * low, 0))
    hair, used = make_mesh("hair", coll, HV, hf)
    HM = cel(st["hair_col"], "#050608", rim="#4f5d7c", spec=0.0, spec_col="#3c4660", rim_amt=0.45, name="hair")  # thin gloss band
    hair.data.materials.append(HM)
    out = [(hair, used, 0.004)]
    if style == "crop":
        out += crop_extras(coll, V, head_faces, hidx, HV, nrm, eyeL, hx, hc, st, HM)
    if style in ("short", "bangs", "slick", "bob"):
        out += natural_locks(coll, HV, hf, V, head_faces, eyeL, hx, hc, st, HM, style)
    if style == "long":
        out += long_locks(coll, HV, hf, V, head_faces, eyeL, hx, hc, st, HM, st.get("hair_len", 0.3))
    if style == "quiff":
        out += crop_extras(coll, V, head_faces, hidx, HV, nrm, eyeL, hx, hc, st, HM, top_z=eyeL.z + 0.03,
                           lo_z=eyeL.z - 0.075, tufts=False, front_max=0.62)
        out += quiff_locks(coll, hair, HV, hf, eyeL, hx, hc, st, HM, V, head_faces)
    return out

def natural_locks(coll, HV, hf, V, head_faces, eyeL, hx, hc, st, HM, style):
    """Ordinary hair: strands lying on the cap in the way hair grows, so it reads as hair and not a helmet.
    short: from the crown whorl outward and forward; bangs: the front falls over the forehead to the brows;
    slick: swept back from the hairline; bob: falls from a side parting to the jaw."""
    import random as _r
    rng = _r.Random(hash((style, st.get("vary", 0), st["hair_col"])) & 0xffffff)
    bvh = bvhtree.BVHTree.FromPolygons([tuple(HV[i]) for i in range(len(HV))], hf)
    sbvh = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], head_faces)
    C0 = Vector((0.0, hc.y + 0.01, eyeL.z - 0.005))
    def surf(el, az, skin=False):
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        best = None
        for b_ in ((bvh, sbvh) if skin else (bvh,)):
            hit = b_.ray_cast(C0 + d * 0.4, -d)
            if hit[0] is not None and (best is None or (hit[0] - C0).length > (best - C0).length):
                best = hit[0]
        if best is None:
            best = bvh.find_nearest(C0 + d * 0.11)[0]
        return best, (best - C0).normalized()
    bm = bmesh.new(); lite_faces = []
    def ribbon(path, w0, lift, lite, skin=False):
        pts = []
        for k, (el, az) in enumerate(path):
            p, n = surf(el, az, skin); pts.append((p + n * lift, n))
        ring = []
        for k, (p, n) in enumerate(pts):
            t = k / (len(pts) - 1); d = (pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]).normalized()
            side = d.cross(n).normalized(); w = w0 * (1 - 0.8 * t ** 1.3) * 0.5 + 0.0005
            ring.append((bm.verts.new(p - side * w), bm.verts.new(p + side * w)))
        for a, b in zip(ring, ring[1:]):
            fc = bm.faces.new((a[0], b[0], b[1], a[1]))
            if lite: lite_faces.append(fc)
    R = math.radians
    if style in ("short", "bangs"):
        crown_az = R(180) + rng.uniform(-0.3, 0.3)
        for j in range(70):
            az0 = rng.uniform(-math.pi, math.pi); el0 = R(rng.uniform(55, 95))
            fwd = math.cos(az0)                                        # +1 at the front
            L = R(rng.uniform(14, 24)) * (1.6 if style == "bangs" and fwd > 0.55 else 1.0)
            el1 = el0 - L * (1.8 if style == "bangs" and fwd > 0.55 else 1.0)
            if el0 < R(70):                                            # outer strands run past the cap into a soft hairline
                el1 = min(el1, R(rng.uniform(24, 34) + 14 * max(0.0, fwd)))
            if style == "bangs" and fwd > 0.55:
                el1 = R(rng.uniform(8, 16))                            # down onto the forehead, to the brows
            swirl = R(rng.uniform(4, 12)) * (1 if az0 > 0 else -1)
            n_ = 7; path = [(el0 + (el1 - el0) * k / (n_ - 1), az0 + swirl * k / (n_ - 1)) for k in range(n_)]
            ribbon(path, rng.uniform(0.016, 0.026), 0.006, rng.random() < 0.35, skin=True)
    elif style == "slick":
        for j in range(36):
            az0 = R(-70 + 140 * j / 35 + rng.uniform(-3, 3)); el0 = R(rng.uniform(38, 46))
            n_ = 10; path = [(el0 + (R(125) - el0) * k / (n_ - 1), az0 * (1 - 0.35 * k / (n_ - 1))) for k in range(n_)]
            ribbon(path, rng.uniform(0.018, 0.026), 0.006, rng.random() < 0.35)
    elif style == "bob":
        part = R(-12)
        for sx in (1, -1):
            for j in range(16):
                az1 = sx * R(25 + 95 * j / 15); n_ = 10
                path = [(R(84) + (R(-6) - R(84)) * k / (n_ - 1), part + (az1 - part) * (k / (n_ - 1)) ** 0.8) for k in range(n_)]
                ribbon(path, rng.uniform(0.022, 0.03), 0.007, rng.random() < 0.35, skin=True)
    me = bpy.data.meshes.new("hair_strands"); bm.to_mesh(me)
    lite_idx = {f.index for f in lite_faces}; bm.free()
    ob = bpy.data.objects.new("hair_strands", me); coll.objects.link(ob); ob.data.materials.append(HM)
    c0 = [int(st["hair_col"][k:k + 2], 16) for k in (1, 3, 5)]
    lite = "#%02x%02x%02x" % tuple(min(255, int(v * 1.35 + 10)) for v in c0)
    ob.data.materials.append(cel(lite, st["hair_col"], rim="#8a7a6c", rim_amt=0.4, name="hair_lite"))
    for pl in me.polygons:
        if pl.index in lite_idx: pl.material_index = 1
    ob["tufts"] = True; ob["locks"] = True
    return [(ob, None, 0.0)]

def long_locks(coll, HV, hf, V, head_faces, eyeL, hx, hc, st, HM, drop):
    """Long wavy hair: locks flowing from a side parting down over the head, and face-framing locks that leave the
    head at the temples and fall in soft waves past the cheeks to the collarbone."""
    import random as _r
    rng = _r.Random(31)
    bvh = bvhtree.BVHTree.FromPolygons([tuple(HV[i]) for i in range(len(HV))], hf)
    sbvh = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], head_faces)
    C0 = Vector((0.0, hc.y + 0.01, eyeL.z - 0.005))
    def surf(el, az):
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        best = None
        for b_ in (bvh, sbvh):
            hit = b_.ray_cast(C0 + d * 0.4, -d)
            if hit[0] is not None and (best is None or (hit[0] - C0).length > (best - C0).length):
                best = hit[0]
        if best is None:
            best = bvh.find_nearest(C0 + d * 0.11)[0]
        return best, (best - C0).normalized()
    bm = bmesh.new(); lite_faces = []
    def ribbon(pts, w0, lite):
        ring = []
        for k, (p, n) in enumerate(pts):
            t = k / (len(pts) - 1); d = (pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]).normalized()
            side = d.cross(n).normalized(); w = w0 * (1 - 0.75 * t ** 1.5) * 0.5 + 0.0006
            ring.append((bm.verts.new(p - side * w), bm.verts.new(p + side * w)))
        for a, b in zip(ring, ring[1:]):
            fc = bm.faces.new((a[0], b[0], b[1], a[1]))
            if lite: lite_faces.append(fc)
    R = math.radians; part = R(-14)                         # side parting, a little off centre
    for sx in (1, -1):                                      # over the head from the parting
        for j in range(14):
            az1 = sx * R(30 + 85 * j / 13) + rng.uniform(-0.05, 0.05); n_ = 12; pts = []
            for k in range(n_):
                t = k / (n_ - 1)
                el = R(84 - 70 * t); az = part + (az1 - part) * t ** 0.8 + R(3) * math.sin(t * 7 + j)
                p, n = surf(el, az); pts.append((p + n * (0.004 + 0.004 * math.sin(math.pi * t)), n))
            ribbon(pts, rng.uniform(0.024, 0.034), rng.random() < 0.3)
    for sx in (1, -1):                                      # face-framing waves
        for j in range(3):
            az_t = sx * R(48 + 9 * j); pts = []
            for k in range(8):
                t = k / 7
                p, n = surf(R(80 - 62 * t), part + (az_t - part) * t)
                pts.append((p + n * (0.006 + 0.002 * j), n))
            p0, n0 = pts[-1]; out_ = Vector((n0.x, n0.y, 0)).normalized()
            for k in range(1, 11):
                t = k / 10
                wave = 0.012 * math.sin(t * math.pi * 2.4 + j) * (0.4 + t)
                p = p0 + Vector((sx * (0.006 * k + wave), -0.004 * k + 0.002 * j, -drop * 0.85 * t))
                pts.append((p, out_))
            ribbon(pts, 0.03 - 0.004 * j, j == 1)
    me = bpy.data.meshes.new("hair_locks"); bm.to_mesh(me)
    lite_idx = {f.index for f in lite_faces}; bm.free()
    ob = bpy.data.objects.new("hair_locks", me); coll.objects.link(ob); ob.data.materials.append(HM)
    c0 = [int(st["hair_col"][k:k + 2], 16) for k in (1, 3, 5)]
    lite = "#%02x%02x%02x" % tuple(min(255, int(v * 1.6 + 16)) for v in c0)
    ob.data.materials.append(cel(lite, st["hair_col"], rim="#8a7a6c", rim_amt=0.4, name="hair_lite"))
    for pl in me.polygons:
        if pl.index in lite_idx: pl.material_index = 1
    ob["tufts"] = True; ob["locks"] = True; ob["hang"] = True
    return [(ob, None, 0.0)]

def quiff_locks(coll, cap, HV, hf, eyeL, hx, hc, st, HM, V=None, head_faces=None):
    """Wavy flat locks over the cap: swept up and back from the forehead and off to one side, the front ones
    lifted into a quiff, a few short ones on the sides, and three loose strands falling onto the forehead."""
    import random as _r
    rng = _r.Random(23)
    bvh = bvhtree.BVHTree.FromPolygons([tuple(HV[i]) for i in range(len(HV))], hf)
    C0 = Vector((0.0, hc.y + 0.01, eyeL.z - 0.005))
    sbvh = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], head_faces) if V is not None else None
    def surf(el, az):
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        best = None
        for b_ in ((bvh, sbvh) if sbvh else (bvh,)):
            hit = b_.ray_cast(C0 + d * 0.4, -d)
            if hit[0] is not None and (best is None or (hit[0] - C0).length > (best - C0).length):
                best = hit[0]
        if best is None:
            best = bvh.find_nearest(C0 + d * 0.11)[0]
        return best, (best - C0).normalized()
    bm = bmesh.new(); faces_lite = []
    def lock(path, w0, lift, lite):
        pts = []
        for k, (el, az, extra) in enumerate(path):
            p, n = surf(el, az); t = k / (len(path) - 1)
            pts.append((p + n * (0.003 + lift * math.sin(math.pi * min(1.0, t * 1.6)) + extra), n))
        ring = []
        for k, (p, n) in enumerate(pts):
            t = k / (len(pts) - 1); d = (pts[min(k + 1, len(pts) - 1)][0] - pts[max(k - 1, 0)][0]).normalized()
            side = d.cross(n).normalized(); w = w0 * (1 - t) ** 0.7 * 0.5 + 0.0006
            ring.append((bm.verts.new(p - side * w), bm.verts.new(p + side * w)))
        for a, b in zip(ring, ring[1:]):
            fc = bm.faces.new((a[0], b[0], b[1], a[1]))
            if lite: faces_lite.append(fc)
    R = math.radians
    # top: front hairline -> up and back over the crown, swept toward +x, tips curling
    for j in range(30):
        az0 = R(-58 + 116 * j / 29 + rng.uniform(-4, 4)); el0 = R(rng.uniform(40, 46) - 12 * (abs(-58 + 116 * j / 29) / 58) ** 2)
        el1 = R(rng.uniform(95, 135)); sweep = R(rng.uniform(18, 34)); n_ = 12
        path = []
        for k in range(n_):
            t = k / (n_ - 1)
            wav = R(5) * math.sin(t * math.pi * 2.2 + j)                # the wave
            curl = R(14) * max(0.0, t - 0.75) / 0.25
            path.append((el0 + (el1 - el0) * t, az0 + sweep * t ** 0.8 + wav + curl, 0.0))
        front = 1.0 - min(1.0, abs(az0) / R(60))
        lock(path, rng.uniform(0.022, 0.032), 0.018 * front + 0.006, rng.random() < 0.35)
    # sides: short locks swept back above the ears
    for sx in (1, -1):
        for j in range(6):
            az0 = sx * R(62 + 7 * j); el0 = R(14 + rng.uniform(-3, 3)); n_ = 8
            path = [(el0 + R(26) * k / (n_ - 1), az0 + sx * R(30) * k / (n_ - 1), 0.0) for k in range(n_)]
            lock(path, rng.uniform(0.018, 0.024), 0.002, rng.random() < 0.3)
    # three loose strands falling onto the forehead, curling at the ends
    for j, az0 in enumerate((R(-22), R(-10), R(4))):
        n_ = 9; path = []
        for k in range(n_):
            t = k / (n_ - 1)
            path.append((R(48 - 44 * t), az0 + R(8) * math.sin(t * 3.0 + j) - R(10) * t, 0.012 * (1 - t)))
        lock(path, 0.016, 0.004, j == 1)
    me = bpy.data.meshes.new("hair_locks"); bm.to_mesh(me)
    lite_idx = {f.index for f in faces_lite}; bm.free()
    ob = bpy.data.objects.new("hair_locks", me); coll.objects.link(ob); ob.data.materials.append(HM)
    c0 = [int(st["hair_col"][k:k + 2], 16) for k in (1, 3, 5)]
    lite = "#%02x%02x%02x" % tuple(min(255, int(v * 2.0 + 18)) for v in c0)
    ob.data.materials.append(cel(lite, st["hair_col"], rim="#6a5a4c", rim_amt=0.4, name="hair_lite"))
    for pl in me.polygons:
        if pl.index in lite_idx:
            pl.material_index = 1
    ob["tufts"] = True; ob["locks"] = True
    return [(ob, None, 0.0)]

def crop_extras(coll, V, head_faces, hidx, HV, nrm, eyeL, hx, hc, st, HM, top_z=None, lo_z=None, tufts=True, front_max=0.72):
    """Skin fade on the sides and back (dark at the top, bare skin at the bottom) + textured spiky tufts on top."""
    import random as _r
    rng = _r.Random(11)
    top_z = eyeL.z + 0.052 if top_z is None else top_z; lo_z = eyeL.z - 0.03 if lo_z is None else lo_z
    def frontness(c): return min(1.0, max(0.0, (eyeL.y + 0.16 - c.y) / 0.16))
    fade_f = [f for f in head_faces
              if lo_z < sum(V[i].z for i in f) / len(f) <= top_z + 0.03 * frontness(sum((V[i] for i in f), Vector()) / len(f)) + 0.004
              and frontness(sum((V[i] for i in f), Vector()) / len(f)) < front_max
              and max(abs(V[i].x) for i in f) < hx * 0.93]
    off = {i: nrm[i] * 0.0012 for f in fade_f for i in f}
    fd, used = make_mesh("hair_fade", coll, V, fade_f, off)
    # material: hair colour fading to transparent toward the bottom (object-space Z ramp)
    m = cel(st["hair_col"], "#0a0b0d", rim=st["hair_col"], name="hair_fade_base").copy(); m.name = "hair_fade"
    nt = m.node_tree; N_, L_ = nt.nodes, nt.links
    outn = next(n for n in N_ if n.type == "OUTPUT_MATERIAL"); src = outn.inputs[0].links[0].from_socket
    tc = N_.new("ShaderNodeTexCoord"); sp = N_.new("ShaderNodeSeparateXYZ"); L_.new(tc.outputs["Object"], sp.inputs[0])
    mr = N_.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = lo_z + 0.012; mr.inputs["From Max"].default_value = top_z - 0.004
    L_.new(sp.outputs["Z"], mr.inputs["Value"])
    nz = N_.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900.0; L_.new(tc.outputs["Object"], nz.inputs["Vector"])
    mul = N_.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; L_.new(mr.outputs["Result"], mul.inputs[0])
    L_.new(nz.outputs["Fac"], mul.inputs[1])
    ad = N_.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.use_clamp = True
    L_.new(mr.outputs["Result"], ad.inputs[0]); ad.inputs[1].default_value = 0.75; L_.new(mul.outputs[0], ad.inputs[2])
    tr = N_.new("ShaderNodeBsdfTransparent"); mx = N_.new("ShaderNodeMixShader")
    L_.new(ad.outputs[0], mx.inputs[0]); L_.new(tr.outputs[0], mx.inputs[1]); L_.new(src, mx.inputs[2]); L_.new(mx.outputs[0], outn.inputs[0])
    fd.data.materials.append(m)
    res = [(fd, used, 0.0)]
    if not tufts:
        return res
    # tufts: small tapered spikes, pointing up and forward at the front, up on top, back at the crown
    bm = bmesh.new()
    pts = [i for i in hidx if HV[i].z > eyeL.z + 0.06]
    for i in rng.sample(pts, min(len(pts), 520)):
        p = HV[i]; n = nrm[i]
        fr = min(1.0, max(0.0, (hc.y - p.y) / 0.08))           # 1 at the front
        bk = min(1.0, max(0.0, (p.y - hc.y) / 0.08))           # 1 at the crown
        d = (n * 0.5 + Vector((rng.uniform(-0.3, 0.3), -0.75 * fr + 0.5 * bk - 0.15, 0.35 + 0.15 * (1 - bk)))).normalized()
        L = rng.uniform(0.009, 0.019) * (1.25 if fr > 0.5 else 1.0); r = rng.uniform(0.007, 0.011)
        side = d.cross(Vector((0, 0, 1))); side = side.normalized() if side.length > 1e-4 else Vector((1, 0, 0))
        up2 = side.cross(d).normalized()
        base = p - n * 0.004
        bend = (side * rng.uniform(-1, 1) + up2 * rng.uniform(-0.5, 0.5)) * L * 0.25
        mid = base + d * L * 0.55 + bend * 0.5; tip = base + d * L + bend
        ring0 = [bm.verts.new(base + (side * math.cos(a) + up2 * math.sin(a)) * r) for a in (0, 2.1, 4.2)]
        ring1 = [bm.verts.new(mid + (side * math.cos(a) + up2 * math.sin(a)) * r * 0.5) for a in (0.3, 2.4, 4.5)]
        tv = bm.verts.new(tip)
        for k in range(3):
            bm.faces.new((ring0[k], ring0[(k + 1) % 3], ring1[(k + 1) % 3], ring1[k]))
            bm.faces.new((ring1[k], ring1[(k + 1) % 3], tv))
    me = bpy.data.meshes.new("hair_tufts"); bm.to_mesh(me); bm.free()
    tu = bpy.data.objects.new("hair_tufts", me); coll.objects.link(tu); tu.data.materials.append(HM)
    # a lighter brown on some tufts: strands catching the light give the crop its texture
    c0 = [int(st["hair_col"][k:k + 2], 16) for k in (1, 3, 5)]
    lite = "#%02x%02x%02x" % tuple(min(255, int(v * 1.9 + 14)) for v in c0)
    tu.data.materials.append(cel(lite, st["hair_col"], rim="#6a5a4c", rim_amt=0.4, name="hair_lite"))
    tri = 6                                               # faces per tuft
    for t0 in range(0, len(me.polygons), tri):
        if rng.random() < 0.38:
            for k in range(t0, min(t0 + tri, len(me.polygons))):
                me.polygons[k].material_index = 1
    tu["tufts"] = True
    res.append((tu, None, 0.0))
    return res

def add_locks(coll, arm, V, J, hair, st, objs):
    eyeL = J("eye.L"); hl = eyeL.z + 0.06
    fy = min(v.co.y for v in hair.data.vertices)
    HM = hair.data.materials[0]
    for k, (x0, drop, curl) in enumerate(((-0.022, 0.05, -0.012), (-0.004, 0.035, 0.01), (0.03, 0.028, -0.006))):
        cu = bpy.data.curves.new(f"lock{k}", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.0042; cu.bevel_resolution = 2
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(3)
        pts = [(x0 * 0.6, fy + 0.03, hl + 0.045), (x0 * 0.8, fy - 0.006, hl + 0.03), (x0 + curl * 0.5, fy - 0.012, hl - drop * 0.5),
               (x0 + curl, fy - 0.006, hl - drop)]
        for bp, co, r in zip(sp.bezier_points, pts, (1.0, 0.9, 0.6, 0.15)):
            bp.co = co; bp.handle_left_type = bp.handle_right_type = "AUTO"; bp.radius = r
        lo = bpy.data.objects.new(f"lock{k}", cu); coll.objects.link(lo); lo.data.materials.append(HM)
        bone_parent(lo, arm, "head")
        objs.append(lo)

_CS = {}
def contact_shadow(coll, arm):
    """A soft dark pool on the ground under the feet (follows the rig root): grounds the cel-shaded people."""
    if "mat" not in _CS:
        m = bpy.data.materials.new("contact_shadow"); m.use_nodes = True; nt = m.node_tree; N_, L_ = nt.nodes, nt.links
        N_.clear(); out = N_.new("ShaderNodeOutputMaterial"); tc = N_.new("ShaderNodeTexCoord")
        vm = N_.new("ShaderNodeVectorMath"); vm.operation = "LENGTH"; L_.new(tc.outputs["Object"], vm.inputs[0])
        mr = N_.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 1.0
        mr.inputs["To Min"].default_value = 0.55; mr.inputs["To Max"].default_value = 0.0; mr.interpolation_type = "SMOOTHSTEP"
        L_.new(vm.outputs["Value"], mr.inputs["Value"])
        tr = N_.new("ShaderNodeBsdfTransparent"); em = N_.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.004, 0.005, 0.01, 1)
        mx = N_.new("ShaderNodeMixShader"); L_.new(mr.outputs["Result"], mx.inputs[0]); L_.new(tr.outputs[0], mx.inputs[1])
        L_.new(em.outputs[0], mx.inputs[2]); L_.new(mx.outputs[0], out.inputs[0]); _CS["mat"] = m
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, radius=1.0, segments=24)
    me = bpy.data.meshes.new("contact_shadow"); bm.to_mesh(me); bm.free(); me.materials.append(_CS["mat"])
    ob = bpy.data.objects.new("contact_shadow", me); coll.objects.link(ob)
    ob.parent = arm; s_ = arm.scale[0]
    ob.location = (0, 0, (-arm["ground"] + 0.004) / s_); ob.scale = (0.38 / s_, 0.3 / s_, 1)
    ob.visible_shadow = False; ob["no_mask"] = True
    return ob

def make_shoes(coll, V, bused, dom, kd, per_vert, st, finish):
    up_c, sole_c = st["shoes"]
    sneaker = st.get("sneakers", False); loafer = st.get("loafer", False)
    LEATHER = cel(up_c, None, rim="#bcd8ff", spec=0.0 if sneaker else (0.07 if loafer else 0.035), spec_col="#9aa3b5", name="shoe")
    STRAP = cel("#34363d", "#121317", rim="#bcd8ff", spec=0.05, spec_col="#9aa3b5", name="loafer_strap")
    SOLE = cel(sole_c, None, rim=sole_c, name="sole")
    for side in ("L", "R"):
        fv = [i for i in bused if dom.get(i, "").startswith(("foot." + side, "toe")) and (V[i].x > 0) == (side == "L")]
        xs = [V[i].x for i in fv]; ys = [V[i].y for i in fv]
        x0 = sum(xs) / len(xs); yh = max(ys) + 0.012; yt = min(ys) - 0.016
        Lg = yh - yt; W = (max(xs) - min(xs)) + (0.02 if sneaker else 0.014)
        def section(t, sole=False):
            if loafer:   # slim penny loafer: low collar, long tapered toe, thin sole with a heel block
                w = W * (0.31 + 0.11 * math.sin(math.pi * min(t / 0.68, 1) * 0.5))
                if t > 0.72:
                    w *= math.sqrt(max(0.0, 1 - ((t - 0.72) / 0.28) ** 2)) * 0.82 + 0.18
                spring = 0.012 * max(0.0, (t - 0.8) / 0.2) ** 2
                heel = 0.026 if t < 0.24 else (0.009 if t > 0.3 else 0.026 - 0.017 * (t - 0.24) / 0.06)
                if sole:
                    return w + 0.0035, heel + spring, spring
                h = 0.056 - 0.024 * min(1.0, max(0.0, (t - 0.18) / 0.32)) - 0.006 * max(0.0, (t - 0.6) / 0.4)
                h *= 1 if t < 0.9 else math.sqrt(max(0.0, 1 - (t - 0.9) / 0.1)) * 0.8 + 0.2
                return w, heel + spring + h, heel + spring
            w = W * (0.36 + 0.14 * math.sin(math.pi * min(t / 0.72, 1) * 0.5))
            if t > 0.8:
                w *= math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 2)) * 0.9 + 0.1
            spring = 0.009 * max(0.0, (t - 0.78) / 0.22) ** 2
            if sneaker:
                heel = 0.026
            else:
                heel = 0.024 if t < 0.27 else (0.012 if t > 0.33 else 0.024 - 0.012 * (t - 0.27) / 0.06)
            if sole:
                return w + 0.003, heel + spring, spring
            h = 0.085 if t < 0.3 else 0.085 - 0.05 * (t - 0.3) / 0.55
            h = max(h, 0.032 if sneaker else 0.028) * (1 if t < 0.92 else math.sqrt(max(0.0, 1 - (t - 0.92) / 0.08)))
            return w, heel + spring + h, heel + spring
        for kind in ("upper", "sole"):
            bm = bmesh.new(); rings = []; M = 28
            for k in range(25):
                t = k / 24
                w, ztop, zbot = section(t, kind == "sole")
                y = yh - t * Lg; ring = []
                for j in range(M):
                    a = 2 * math.pi * j / M; c_, s_ = math.cos(a), math.sin(a)
                    px = x0 + w * math.copysign(abs(c_) ** 0.6, c_)
                    zz = zbot + (ztop - zbot) * (0.5 + 0.5 * math.copysign(abs(s_) ** (0.5 if s_ > 0 else 0.25), s_))
                    ring.append(bm.verts.new((px, y, zz)))
                rings.append(ring)
            for r0, r1 in zip(rings, rings[1:]):
                for j in range(M):
                    bm.faces.new((r0[j], r0[(j + 1) % M], r1[(j + 1) % M], r1[j]))
            bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            me = bpy.data.meshes.new(f"shoe_{kind}{side}"); bm.to_mesh(me); bm.free()
            for p in me.polygons:
                p.use_smooth = True
            ob = bpy.data.objects.new(f"shoe_{kind}{side}", me); coll.objects.link(ob)
            ob.data.materials.append(LEATHER if kind == "upper" else SOLE)
            weights_from_body(ob, kd, bused, per_vert, k=6); finish(ob)
        if loafer:   # the saddle strap across the instep: a lighter band that reads the loafer shape in close-up
            bm = bmesh.new(); rows = []
            for k in range(5):
                t = 0.44 + 0.08 * k / 4
                w, ztop, zbot = section(t); y = yh - t * Lg; row = []
                for j in range(13):
                    a = math.pi * (0.06 + 0.88 * j / 12); c_, s_ = math.cos(a), math.sin(a)
                    px = x0 + (w + 0.0015) * math.copysign(abs(c_) ** 0.6, c_)
                    zz = zbot + (ztop - zbot) * (0.5 + 0.5 * s_ ** 0.5) + 0.0015
                    row.append(bm.verts.new((px, y, zz)))
                rows.append(row)
            for r0, r1 in zip(rows, rows[1:]):
                for j in range(12):
                    bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
            me = bpy.data.meshes.new(f"loafer_strap{side}"); bm.to_mesh(me); bm.free()
            ob = bpy.data.objects.new(f"loafer_strap{side}", me); coll.objects.link(ob); ob.data.materials.append(STRAP)
            weights_from_body(ob, kd, bused, per_vert, k=6); finish(ob, solidify=0.002)

# ---------------------------------------------------------------- poses & walk cycle
ANIM_BONES = [f"{b}.{s}" for s in ("L", "R") for b in ("upperarm01", "upperarm02", "lowerarm01", "lowerarm02", "wrist",
                                                       "upperleg01", "upperleg02", "lowerleg01", "lowerleg02", "foot")] + ["head", "neck02"]

def _aimer(arm):
    vl = bpy.context.view_layer
    def aim(name, d):
        vl.update()
        pb = arm.pose.bones[name]
        cur = (pb.tail - pb.head).normalized(); q = cur.rotation_difference(Vector(d).normalized())
        h = pb.head.copy()
        pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    return aim

def _reset(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        if pb.name in ANIM_BONES:
            pb.rotation_quaternion = Quaternion()

RELAX = {2: (8, 14, 10), 3: (11, 17, 12), 4: (13, 19, 13), 5: (16, 22, 15)}   # degrees per joint, index -> pinky
def _fingers(arm, aim):
    """A relaxed hand: each finger curls a little toward the palm (about the bone's local Z, mirrored L/R),
    the little finger most; the thumb stays as modelled."""
    for side, sgn in (("L", 1), ("R", -1)):
        for k, angs in RELAX.items():
            for j, ang in zip((1, 2, 3), angs):
                n = f"finger{k}-{j}.{side}"
                if n in arm.pose.bones:
                    pb = arm.pose.bones[n]; pb.rotation_mode = "QUATERNION"
                    pb.rotation_quaternion = Quaternion((0, 0, sgn), math.radians(ang))

def grip(arm, side="R"):
    """Close one hand round a handle (umbrella shaft, phone)."""
    sgn = 1 if side == "L" else -1
    for k in range(2, 6):
        for j, ang in zip((1, 2, 3), (55, 70, 45)):
            n = f"finger{k}-{j}.{side}"
            if n in arm.pose.bones:
                pb = arm.pose.bones[n]; pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = Quaternion((0, 0, sgn), math.radians(ang))

def _walk_phase(arm, aim, p, prop=None):
    """Directions in rig space (facing -y). p in [0,1): 0 = left heel strike."""
    for side, sx, ph in (("L", 1, p), ("R", -1, p + 0.5)):
        a = math.radians(19) * math.cos(2 * math.pi * ph)
        flex = math.radians(6 + 42 * max(0.0, math.sin(2 * math.pi * (ph - 0.5))))
        pitch = math.radians(10 * math.cos(2 * math.pi * ph) - 14 * max(0.0, math.sin(2 * math.pi * (ph - 0.3))))
        th = (sx * 0.02, -math.sin(a), -math.cos(a)); sh = (0, -math.sin(a - flex), -math.cos(a - flex))
        aim(f"upperleg01.{side}", th); aim(f"upperleg02.{side}", th)
        aim(f"lowerleg01.{side}", sh); aim(f"lowerleg02.{side}", sh)
        aim(f"foot.{side}", (0, -math.cos(pitch - (a - flex) * 0.15), math.sin(pitch)))
    for side, sx, ph in (("L", 1, p + 0.5), ("R", -1, p)):
        if prop and (side == "R" or prop == "pockets"):
            continue
        s = math.radians(15) * math.cos(2 * math.pi * ph)
        ua = (sx * 0.12, -math.sin(s), -math.cos(s)); fa_ang = s + math.radians(14 + 10 * max(0.0, math.cos(2 * math.pi * ph)))
        fa = (sx * 0.02, -math.sin(fa_ang), -math.cos(fa_ang))
        aim(f"upperarm01.{side}", ua); aim(f"upperarm02.{side}", ua)
        aim(f"lowerarm01.{side}", fa); aim(f"lowerarm02.{side}", fa); aim(f"wrist.{side}", fa)
    if prop:
        _prop_arm(aim, prop)

def _prop_arm(aim, prop):
    if prop == "pockets":      # both hands in the trouser pockets, elbows out and back
        for side, sx in (("L", 1), ("R", -1)):
            ua = (sx * 0.2, 0.04, -1); fa = (-sx * 0.6, -0.5, -0.62); wr = (-sx * 0.25, -0.25, -1)
            aim(f"upperarm01.{side}", ua); aim(f"upperarm02.{side}", ua)
            aim(f"lowerarm01.{side}", fa); aim(f"lowerarm02.{side}", fa); aim(f"wrist.{side}", wr)
        return
    if prop == "umbrella":     # right fist at chest height, shaft vertical
        aim("upperarm01.R", (-0.18, -0.25, -1)); aim("upperarm02.R", (-0.18, -0.25, -1))
        aim("lowerarm01.R", (0.32, -1, 0.75)); aim("lowerarm02.R", (0.32, -1, 0.75)); aim("wrist.R", (0.2, -1, 0.5))
    elif prop == "phone":      # phone held in front of the chest, head down
        aim("upperarm01.R", (-0.1, -0.12, -1)); aim("upperarm02.R", (-0.1, -0.12, -1))
        aim("lowerarm01.R", (0.45, -1, 0.55)); aim("lowerarm02.R", (0.45, -1, 0.55)); aim("wrist.R", (0.3, -1, 0.2))

def hands_in_pockets(arm):
    """The hands disappear into the trouser pockets: scale them down inside the cloth (permanent for this rig)."""
    for side in ("L", "R"):
        arm.pose.bones[f"wrist.{side}"].scale = (0.35, 0.35, 0.35)

def posed(arm, mode, head_yaw=0.0):
    aim = _aimer(arm); _reset(arm)
    if mode == "walk":           # hero still: mid-stride, natural arm swing
        _walk_phase(arm, aim, 0.0)
    elif mode in ("stand", "phone", "umbrella", "pockets"):
        for side, sx in (("L", 1), ("R", -1)):
            aim(f"upperarm01.{side}", (sx * 0.1, 0.02, -1)); aim(f"upperarm02.{side}", (sx * 0.1, 0.02, -1))
            aim(f"lowerarm01.{side}", (sx * 0.02, -0.15, -1)); aim(f"lowerarm02.{side}", (sx * 0.02, -0.15, -1))
            aim(f"wrist.{side}", (sx * 0.03, -0.1, -1))
        if mode == "phone":
            _prop_arm(aim, "phone"); aim("neck02", (0, -0.35, 1)); aim("head", (0, -0.45, 1))
        if mode in ("umbrella", "pockets"):
            _prop_arm(aim, mode)
    _fingers(arm, aim)
    if head_yaw:   # look sideways: twist neck and head about their own (vertical) axes
        for b in ("neck02", "head"):
            pb = arm.pose.bones[b]
            pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion((0, 1, 0), math.radians(head_yaw) / 2)
    bpy.context.view_layer.update()

_LIB = {}
def walk_library(arm, prop=None, keys=8):
    """Rotation quaternions for each walk key, computed once per body type + prop."""
    k = (arm["body"], prop)
    if k not in _LIB:
        aim = _aimer(arm); lib = []
        for i in range(keys):
            _reset(arm); _walk_phase(arm, aim, i / keys, prop)
            bpy.context.view_layer.update()
            lib.append({b: arm.pose.bones[b].rotation_quaternion.copy() for b in ANIM_BONES})
        _LIB[k] = lib
    return _LIB[k]

def animate_walk(arm, start, heading_deg, f0, f1, phase=0.0, prop=None, cycle=32, speed=None, stride=0.62):
    """Key a looping walk from frame f0 to f1, moving along heading (0 = toward -y)."""
    lib = walk_library(arm, prop); keys = len(lib); step = cycle // keys
    speed = speed or (2 * stride * arm.scale[0] / 0.83) / (cycle / 30.0)
    d = Vector((math.sin(math.radians(heading_deg)), -math.cos(math.radians(heading_deg)), 0))
    arm.rotation_euler = (0, 0, math.radians(heading_deg))
    off = int(round(phase * keys))
    f = f0
    while f <= f1 + step:
        j = ((f - f0) // step + off) % keys
        for b, q in lib[j].items():
            pb = arm.pose.bones[b]; pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
        p = (j / keys)
        bob = 0.022 * (1 - math.cos(4 * math.pi * p)) / 2
        arm.location = Vector(start) + d * speed * (f - f0) / 30.0 + Vector((0, 0, arm["ground"] + bob))
        arm.keyframe_insert("location", frame=f)
        f += step
    set_interp(arm, "LINEAR", "location")          # steady walking speed between keys
    return speed

def add_umbrella(arm, coll, colour="#1d2230", clear=False):
    """Umbrella in the right fist (pose prop='umbrella'), parented to the wrist."""
    grip(arm, "R")
    bpy.context.view_layer.update()
    pb = arm.pose.bones["wrist.R"]
    hand = arm.matrix_world @ (pb.head.lerp(pb.tail, 1.6))
    obs = []
    shaft_len = 0.78; R = 0.52
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.007, depth=shaft_len, location=hand + Vector((0, 0, shaft_len / 2 - 0.08)))
    obs.append(bpy.context.object)
    bm = bmesh.new(); ribs = 8; tip = hand + Vector((0, 0, shaft_len - 0.06))
    apex = bm.verts.new(tip + Vector((0, 0, 0.03)))
    rim = [bm.verts.new(tip + Vector((R * math.cos(2 * math.pi * i / ribs), R * math.sin(2 * math.pi * i / ribs), -0.2))) for i in range(ribs)]
    mid = [bm.verts.new(tip + Vector((0.62 * R * math.cos(2 * math.pi * (i + 0.5) / ribs), 0.62 * R * math.sin(2 * math.pi * (i + 0.5) / ribs), -0.07)))
           for i in range(ribs)]
    for i in range(ribs):
        bm.faces.new((apex, rim[i], mid[i])); bm.faces.new((apex, mid[i], rim[(i + 1) % ribs]))
        bm.faces.new((mid[i], rim[i], rim[(i + 1) % ribs]))
    me = bpy.data.meshes.new("canopy"); bm.to_mesh(me); bm.free()
    can = bpy.data.objects.new("umbrella", me); coll.objects.link(can); obs.append(can)
    if clear:
        m = bpy.data.materials.new("clear_umbrella"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.9, 0.95, 1, 1)
        b.inputs["Transmission Weight"].default_value = 0.92; b.inputs["Roughness"].default_value = 0.18
        can.data.materials.append(m)
    else:
        can.data.materials.append(cel(colour, None, rim="#cfe6ff", name="umbrella"))
    obs[0].data.materials.append(cel("#202124", "#0a0a0b", rim="#9fb0c0", name="shaft"))
    for o in obs:
        if o.users_collection and o.users_collection[0] != coll:
            for c in o.users_collection:
                c.objects.unlink(o)
            coll.objects.link(o)
        bone_parent(o, arm, "wrist.R")
    return obs

def add_phone(arm, coll):
    grip(arm, "R")
    bpy.context.view_layer.update()
    pb = arm.pose.bones["wrist.R"]; hand = arm.matrix_world @ pb.tail
    bpy.ops.mesh.primitive_cube_add(size=1, location=hand + Vector((0, -0.02, 0.03)))
    ph = bpy.context.object; ph.scale = (0.035, 0.008, 0.07); ph.rotation_euler = (math.radians(-35), 0, arm.rotation_euler.z)
    for c in ph.users_collection:
        c.objects.unlink(ph)
    coll.objects.link(ph); ph.data.materials.append(glow_mat("#cfe8ff", 3.0))
    bone_parent(ph, arm, "wrist.R")
    return ph


def add_cap(arm, coll, colour="#1c2638", badge="#d9b24a"):
    """Peaked uniform cap on the head bone (police officer)."""
    bpy.context.view_layer.update()
    pb = arm.pose.bones["head"]
    top = arm.matrix_world @ pb.tail; up = (arm.matrix_world.to_3x3() @ (pb.tail - pb.head)).normalized()
    fwd = arm.matrix_world.to_3x3() @ Vector((0, -1, 0)); fwd.normalize()
    s = arm.scale[0] / 0.83
    obs = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.108 * s, depth=0.075 * s, location=top - up * 0.035 * s)
    obs.append(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.125 * s, depth=0.012 * s, location=top + up * 0.005 * s)
    obs.append(bpy.context.object)
    bpy.ops.mesh.primitive_cube_add(size=1, location=top - up * 0.075 * s + fwd * 0.1 * s)
    brim = bpy.context.object; brim.scale = (0.17 * s, 0.07 * s, 0.008 * s); brim.rotation_euler = (math.radians(-12), 0, arm.rotation_euler.z)
    obs.append(brim)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.018 * s, depth=0.004 * s, location=top - up * 0.02 * s + fwd * 0.106 * s,
                                        rotation=(math.radians(90), 0, arm.rotation_euler.z))
    obs.append(bpy.context.object)
    mats = [cel(colour, None, rim="#a9c4ff", name="cap"), cel("#141a26", None, rim="#a9c4ff", name="cap_top"),
            cel("#0d0f14", None, rim="#7f8faa", spec=0.05, name="brim"), glow_mat(badge, 2.0)]
    for o, m in zip(obs, mats):
        o.data.materials.append(m)
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o); bone_parent(o, arm, "head")
    return obs
