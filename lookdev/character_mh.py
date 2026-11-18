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
OUTLINE = 0.005  # ink line width in metres (0 disables); heavier webtoon ink
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
            legs="trousers", leg_col=("#2b2e35", "#0b0c10"), shoes=("#141416", "#3a3236"), brows="#121014", iris="#2a2220")

# the lead's fighter build (only when build() is given HERO itself): webtoon muscle anatomy
HERO_LOOK = dict(body="m_muscle", vtaper=True, crease=0.012, turtleneck=True,
                 coat=("#23262c", "#090b0e"), hem=0.36, open_skirt=True)   # his long black coat, over a fighter's body

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
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.3
    c = mix(mth("MULTIPLY", mth("GREATER_THAN", lw.outputs["Facing"], 0.6), rim_amt), c, lin(rim))
    e = N.new("ShaderNodeEmission"); e.inputs["Strength"].default_value = glow
    L.new(c, e.inputs["Color"]); L.new(e.outputs[0], out.inputs[0])
    _cache[key] = m
    return m

def eye_mat(radius, iris="#5a4232"):
    key = ("eye", round(radius, 4), iris)
    if key in _cache:
        return _cache[key]
    m = bpy.data.materials.new("eye")
    N, L, mth, mix = _nodes(m)
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    r = mth("SQRT", mth("ADD", mth("MULTIPLY", sep.outputs["X"], sep.outputs["X"]), mth("MULTIPLY", sep.outputs["Z"], sep.outputs["Z"])))
    front = mth("LESS_THAN", sep.outputs["Y"], 0.0)
    c = mix(mth("GREATER_THAN", sep.outputs["Z"], radius * 0.45), lin("#e6e0d8"), lin("#9a958f"))
    c = mix(mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.5), front), c, mix(mth("DIVIDE", r, radius * 0.5), lin(iris), lin("#1c1512")))
    c = mix(mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.24), front), c, lin("#050505"))
    gx = mth("SUBTRACT", sep.outputs["X"], radius * 0.18); gz = mth("SUBTRACT", sep.outputs["Z"], radius * 0.2)
    glint = mth("LESS_THAN", mth("ADD", mth("MULTIPLY", gx, gx), mth("MULTIPLY", gz, gz)), (radius * 0.11) ** 2)
    c = mix(mth("MULTIPLY", glint, front), c, lin("#ffffff"))
    e = N.new("ShaderNodeEmission"); L.new(c, e.inputs["Color"]); L.new(e.outputs[0], out.inputs[0])
    _cache[key] = m
    return m

def ink_mat():
    """Shell faces that face the camera draw dark ink; the rest are invisible."""
    if "ink" not in _cache:
        m = bpy.data.materials.new("ink"); N, L, mth, mix = _nodes(m)
        out = N.new("ShaderNodeOutputMaterial"); geo = N.new("ShaderNodeNewGeometry")
        e = N.new("ShaderNodeEmission"); e.inputs["Color"].default_value = lin("#0b0c10")
        t = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
        L.new(geo.outputs["Backfacing"], mx.inputs[0]); L.new(e.outputs[0], mx.inputs[1]); L.new(t.outputs[0], mx.inputs[2])
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
    if st["body"] == "m_muscle":   # keep the lean face and neck on the muscular body (the muscle target widens the jaw)
        Vl = load_base("m_lean")[0]
        nidx = sk["joints"][sk["bones"]["neck02"]["head"]]
        cm = sum((V[i] for i in nidx), Vector()) / len(nidx); cl = sum((Vl[i] for i in nidx), Vector()) / len(nidx)
        for i in range(len(V)):
            t = max(0.0, min(1.0, (Vl[i].z - cl.z + 0.01) / 0.05))
            if t > 0:
                V[i] = V[i].lerp(Vl[i] + (cm - cl), t)
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
            v.z -= 0.01 * jaw                                    # slightly longer chin
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
    sleeve = ("lowerarm",) if not st.get("coat") and st.get("sleeves") != "short" else ()
    tn_faces = [f for f in body_faces if region(f, TOP + sleeve) and min(V[i].z for i in f) > pelvis_z - 0.12
                and max(V[i].z for i in f) < neck_cut]
    off = {i: nrm[i] * 0.004 for f in tn_faces for i in f}
    tn, used = make_mesh("top", coll, V, tn_faces, off)
    tn.data.materials.append(cel(st["top"][0], st["top"][1], rim="#fff4e0" if sum(lin(st["top"][0])[:3]) > 0.3 else "#4a5874", rim_amt=0.8 if sum(lin(st["top"][0])[:3]) > 0.3 else 0.6, name="knit", crease=st.get("crease", 0.0))); finish(tn, used)

    # --- coat / jacket
    if st.get("coat"):
        dark = sum(lin(st["coat"][0])[:3]) < 0.3
        COAT = cel(st["coat"][0], st["coat"][1], rim="#56668a" if dark else "#d6efff", rim_amt=0.6 if dark else 0.8, name="coat")
        def open_front(f):
            c = sum((V[i] for i in f), Vector()) / len(f)
            return c.y < -0.02 and c.z > sternum_z - 0.13 and abs(c.x) < 0.012 + max(0.0, sternum_z - c.z) * 0.22
        COAT_SET = ("spine", "clavicle", "shoulder", "upperarm", "lowerarm", "breast", "pelvis")
        coat_faces = [f for f in body_faces if region(f, COAT_SET) and min(V[i].z for i in f) > pelvis_z - 0.1
                      and max(V[i].z for i in f) < neck_z + 0.01 and not open_front(f)]
        off = {i: nrm[i] * (0.013 if dom.get(i, "").startswith(("lowerarm", "upperarm")) else 0.016) for f in coat_faces for i in f}
        cu, used = make_mesh("coat_upper", coll, V, coat_faces, off); cu.data.materials.append(COAT)
        snap_edge(cu, lambda co: co.y < -0.02 and co.z > sternum_z - 0.14 and abs(co.x) < 0.06,
                  lambda co: 0.028 + max(0.0, sternum_z - co.z) * 0.22, 0.0)
        finish(cu, used, solidify=0.006)
        skirt_piece("coat_skirt", coll, V, F, G, kd, bused, per_vert, COAT, st.get("hem", 0.36), st.get("open_skirt", True),
                    flare=st.get("coat_flare", (0.10, 0.22)), finish=finish)

    # --- police tactical vest: navy shell over the jacket, reflective band, white chest patch
    if st.get("vest"):
        VEST = cel(st["vest"], "#070b16", rim="#5a6b90", rim_amt=0.6, name="vest")
        VS = ("spine", "breast", "pelvis", "clavicle")
        vf = [f for f in body_faces if region(f, VS) and pelvis_z - 0.06 < min(V[i].z for i in f)
              and max(V[i].z for i in f) < neck_z - 0.01]
        off = {i: nrm[i] * 0.034 for f in vf for i in f}
        ve, used = make_mesh("vest", coll, V, vf, off); ve.data.materials.append(VEST); finish(ve, used, solidify=0.012)
        band_z = (sternum_z + pelvis_z) / 2 - 0.02
        bf = [f for f in vf if band_z < min(V[i].z for i in f) and max(V[i].z for i in f) < band_z + 0.06]
        off = {i: nrm[i] * 0.048 for f in bf for i in f}
        bd, used = make_mesh("vest_band", coll, V, bf, off)
        bd.data.materials.append(cel("#d6f25c", "#8fa832", rim="#f4ffc0", name="reflective", glow=1.6)); finish(bd, used)
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
    if legs: finish(legs)
    if st.get("socks"):
        knee_z = jpos[sk["bones"]["lowerleg01.L"]["head"]].z
        sock = trousers(coll, V, F, G, sk, jpos, pelvis_z, per_vert, 0.003, straight=False, zhi=knee_z - 0.08,
                        mat=cel(st["socks"], "#b9bcc4", rim="#ffffff", name="socks"))
        sock.name = "socks"; finish(sock)
    uniform_bits(coll, arm, V, J, st, sternum_z, pelvis_z, finish)

    # --- hair
    hair_objs = make_hair(coll, V, body_faces, region, nrm, J, st, per_vert)
    for ob, used, sol in hair_objs:
        finish(ob, used, solidify=sol)
    if st.get("locks") and st["hair"] == "short":
        add_locks(coll, arm, V, J, hair_objs[0][0], st, objs)

    # --- eyes and lash lines
    for side in ("l", "r"):
        ef = [f for f, g in zip(F, G) if g == f"helper-{side}-eye"]
        eidx = {i for f in ef for i in f}; c = sum((V[i] for i in eidx), Vector()) / len(eidx)
        rad = sum((V[i] - c).length for i in eidx) / len(eidx)
        ob, used = make_mesh(f"eye_{side}", coll, [v - c for v in V], ef)
        ob.location = c; ob.data.materials.append(eye_mat(rad, st.get("iris", "#5a4232"))); assign_weights(ob, used, per_vert); add_mods(ob, arm, subsurf=2, outline=0); objs.append(ob)
        for k in (1, 2):
            lf = [f for f, g in zip(F, G) if g == f"helper-{side}-eyelashes-{k}"]
            if lf:
                lo, used = make_mesh(f"lash_{side}{k}", coll, V, lf)
                lo.data.materials.append(cel("#0c0c0f", "#050506", rim="#0c0c0f", name="lash")); add_mods(lo, arm, subsurf=0, outline=0); assign_weights(lo, used, per_vert); objs.append(lo)

    # --- brows ray-cast onto the forehead
    skin_bvh = bvhtree.BVHTree.FromPolygons([tuple(v) for v in V], skin_faces)
    bm = bmesh.new()
    thick = 0.0034 if st["body"] != "f" else 0.0024
    for sx in (1, -1):
        ec = J("eye.L" if sx > 0 else "eye.R")
        rows = []
        for k in range(13):
            s = k / 12
            x = ec.x + sx * (-0.016 + 0.036 * s)
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
    arm.location = Vector(location) + Vector((0, 0, arm["ground"]))
    bpy.context.view_layer.update()
    return arm, objs

def skirt_piece(name, coll, V, F, G, kd, bused, per_vert, mat, hem, open_front, flare, finish, solid=0.006):
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
        Vs[i] = v
    if open_front:
        sk_faces = [f for f in sk_faces if not (sum((Vs[i] for i in f), Vector()).y / len(f) < cy - 0.03
                    and abs(sum((Vs[i] for i in f), Vector()).x / len(f) - cx) < 0.035 + 0.03 * (top - sum((Vs[i] for i in f), Vector()).z / len(f)))]
    cs, _ = make_mesh(name, coll, Vs, sk_faces); cs.data.materials.append(mat)
    if open_front:
        snap_edge(cs, lambda co: co.y < cy - 0.02 and abs(co.x - cx) < 0.2, lambda co: 0.035 + 0.03 * (top - co.z), cx)
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
    if not (st.get("tie") or st.get("backpack")):
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
        if style == "bob":       # fringe to the brows, sides to the jaw
            thr = eyeL.z - 0.1 + 0.125 * frontness
            return c.z > thr
        if style == "bangs":     # heavy fringe down to the brows, short tidy sides
            thr = eyeL.z - 0.05 + 0.065 * frontness
            if abs(c.x) > hx * 0.86 and c.z < eyeL.z + 0.025:
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
            th = 0.004 + 0.022 * up + 0.006 * front * up + 0.0022 * math.sin(p.x * 260 + p.y * 120) * up
            HV[i] = p + n * th + Vector((0, 0.014 * up, 0.006 * up))
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
    HM = cel(st["hair_col"], "#050608", rim="#4f5d7c", spec=0.02, spec_col="#3c4660", rim_amt=0.45, name="hair")  # thin gloss band
    hair.data.materials.append(HM)
    return [(hair, used, 0.004)]

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

def make_shoes(coll, V, bused, dom, kd, per_vert, st, finish):
    up_c, sole_c = st["shoes"]
    sneaker = st.get("sneakers", False)
    LEATHER = cel(up_c, None, rim="#bcd8ff", spec=0.0 if sneaker else 0.035, spec_col="#9aa3b5", name="shoe")
    SOLE = cel(sole_c, None, rim=sole_c, name="sole")
    for side in ("L", "R"):
        fv = [i for i in bused if dom.get(i, "").startswith(("foot." + side, "toe")) and (V[i].x > 0) == (side == "L")]
        xs = [V[i].x for i in fv]; ys = [V[i].y for i in fv]
        x0 = sum(xs) / len(xs); yh = max(ys) + 0.012; yt = min(ys) - 0.016
        Lg = yh - yt; W = (max(xs) - min(xs)) + (0.02 if sneaker else 0.014)
        def section(t, sole=False):
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

def _fingers(arm, aim):
    vl = bpy.context.view_layer
    for side in ("L", "R"):
        for k in range(2, 6):
            for j in (1, 2, 3):
                n = f"finger{k}-{j}.{side}"
                if n in arm.pose.bones:
                    vl.update(); pb = arm.pose.bones[n]; d = (pb.tail - pb.head).normalized()
                    aim(n, d + Vector((0, -0.25 * j, 0)))

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
        if prop and side == "R":
            continue
        s = math.radians(15) * math.cos(2 * math.pi * ph)
        ua = (sx * 0.12, -math.sin(s), -math.cos(s)); fa_ang = s + math.radians(14 + 10 * max(0.0, math.cos(2 * math.pi * ph)))
        fa = (sx * 0.02, -math.sin(fa_ang), -math.cos(fa_ang))
        aim(f"upperarm01.{side}", ua); aim(f"upperarm02.{side}", ua)
        aim(f"lowerarm01.{side}", fa); aim(f"lowerarm02.{side}", fa); aim(f"wrist.{side}", fa)
    if prop:
        _prop_arm(aim, prop)

def _prop_arm(aim, prop):
    if prop == "umbrella":     # right fist at chest height, shaft vertical
        aim("upperarm01.R", (-0.18, -0.25, -1)); aim("upperarm02.R", (-0.18, -0.25, -1))
        aim("lowerarm01.R", (0.32, -1, 0.75)); aim("lowerarm02.R", (0.32, -1, 0.75)); aim("wrist.R", (0.2, -1, 0.5))
    elif prop == "phone":      # phone held in front of the chest, head down
        aim("upperarm01.R", (-0.1, -0.12, -1)); aim("upperarm02.R", (-0.1, -0.12, -1))
        aim("lowerarm01.R", (0.45, -1, 0.55)); aim("lowerarm02.R", (0.45, -1, 0.55)); aim("wrist.R", (0.3, -1, 0.2))

def posed(arm, mode, head_yaw=0.0):
    aim = _aimer(arm); _reset(arm)
    if mode == "walk":           # hero still: mid-stride, natural arm swing
        _walk_phase(arm, aim, 0.0)
    elif mode in ("stand", "phone", "umbrella"):
        for side, sx in (("L", 1), ("R", -1)):
            aim(f"upperarm01.{side}", (sx * 0.1, 0.02, -1)); aim(f"upperarm02.{side}", (sx * 0.1, 0.02, -1))
            aim(f"lowerarm01.{side}", (sx * 0.02, -0.15, -1)); aim(f"lowerarm02.{side}", (sx * 0.02, -0.15, -1))
            aim(f"wrist.{side}", (sx * 0.03, -0.1, -1))
        if mode == "phone":
            _prop_arm(aim, "phone"); aim("neck02", (0, -0.35, 1)); aim("head", (0, -0.45, 1))
        if mode == "umbrella":
            _prop_arm(aim, "umbrella")
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
