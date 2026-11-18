"""Manhwa-style hero built on the CC0 MakeHuman base mesh (lookdev/assets/makehuman).

build(collection, location) -> (armature, objects)
  * realistic male body (MakeHuman macro targets), real skeleton + skin weights
  * clothes fitted from the body surface: turtleneck, open long coat, straight trousers
  * modelled leather dress shoes, slicked-back hair shell, drawn eyes, thick brows
  * cel shading (Cycles-safe) with a rim band and a specular sheen for leather/hair
Original design: charcoal coat, oatmeal turtleneck, no glasses.
"""
import bpy, bmesh, json, math, os
from mathutils import Vector, Matrix, Quaternion, kdtree, bvhtree

HERE = os.path.dirname(os.path.abspath(__file__))
MH = os.path.join(HERE, "assets", "makehuman")
S = 0.1  # MakeHuman decimetres -> metres
HEIGHT = 1.86

TARGETS = {  # body shape: tall, lean, athletic, east-asian/caucasian blend
    "asian-male-young.target": 0.55,
    "caucasian-male-young.target": 0.45,
    "universal-male-young-maxmuscle-averageweight.target": 0.35,
    "universal-male-young-averagemuscle-minweight.target": 0.25,
    "male-young-averagemuscle-averageweight-maxheight.target": 0.3,
    "male-young-averagemuscle-averageweight-idealproportions.target": 1.0,
}

def lin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

# ---------------------------------------------------------------- data
def load_base():
    verts, faces, groups = [], [], []
    g = None
    for line in open(os.path.join(MH, "base.obj")):
        if line.startswith("v "):
            _, x, y, z = line.split()[:4]; verts.append([float(x), float(y), float(z)])
        elif line.startswith("g "):
            g = line.split()[1]
        elif line.startswith("f "):
            faces.append([int(p.split("/")[0]) - 1 for p in line.split()[1:]]); groups.append(g)
    for fn, w in TARGETS.items():
        for line in open(os.path.join(MH, "targets", fn)):
            if line[0] in "#\n":
                continue
            i, dx, dy, dz = line.split(); i = int(i)
            v = verts[i]; v[0] += float(dx) * w; v[1] += float(dy) * w; v[2] += float(dz) * w
    # Y-up decimetres -> Z-up metres, facing -Y
    V = [Vector((x * S, -z * S, y * S)) for x, y, z in verts]
    return V, faces, groups

def load_rig():
    sk = json.load(open(os.path.join(MH, "default.mhskel")))
    w = json.load(open(os.path.join(MH, "default_weights.mhw")))["weights"]
    per_vert = {}
    for bone, lst in w.items():
        for vi, wt in lst:
            per_vert.setdefault(vi, []).append((bone, wt))
    return sk, per_vert

# ---------------------------------------------------------------- materials
_cache = {}
def cel(hexc, shade=None, rim="#cdeffd", spec=0.0, spec_col="#ffffff", light=(-0.55, -0.7, 0.55), rim_amt=0.8, name=None):
    key = (hexc, shade, rim, spec, light, rim_amt)
    if key in _cache:
        return _cache[key]
    m = bpy.data.materials.new(name or f"cel_{hexc}"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial")
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
    geo = N.new("ShaderNodeNewGeometry")
    ln = Vector(light).normalized()
    d = N.new("ShaderNodeVectorMath"); d.operation = "DOT_PRODUCT"; L.new(geo.outputs["Normal"], d.inputs[0]); d.inputs[1].default_value = ln
    base = lin(hexc); sh = lin(shade) if shade else tuple(c * 0.38 for c in base[:3]) + (1.0,)
    mid = tuple((a + b) / 2 for a, b in zip(base, sh))
    c = mix(mth("GREATER_THAN", d.outputs["Value"], -0.15), sh, mid)       # 3-tone ramp
    c = mix(mth("GREATER_THAN", d.outputs["Value"], 0.25), c, base)
    if spec:  # sheen band: N.H with H = light + view (Cycles-safe "anime highlight")
        h = N.new("ShaderNodeVectorMath"); h.operation = "ADD"; h.inputs[0].default_value = ln
        L.new(geo.outputs["Incoming"], h.inputs[1])
        hn = N.new("ShaderNodeVectorMath"); hn.operation = "NORMALIZE"; L.new(h.outputs[0], hn.inputs[0])
        d2 = N.new("ShaderNodeVectorMath"); d2.operation = "DOT_PRODUCT"; L.new(geo.outputs["Normal"], d2.inputs[0]); L.new(hn.outputs[0], d2.inputs[1])
        c = mix(mth("MULTIPLY", mth("GREATER_THAN", d2.outputs["Value"], 1 - spec), 0.9), c, lin(spec_col))
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.3
    c = mix(mth("MULTIPLY", mth("GREATER_THAN", lw.outputs["Facing"], 0.6), rim_amt), c, lin(rim))
    e = N.new("ShaderNodeEmission"); L.new(c, e.inputs["Color"]); L.new(e.outputs[0], out.inputs[0])
    _cache[key] = m
    return m

def eye_mat(radius):
    m = bpy.data.materials.new("eye"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
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
    r = mth("SQRT", mth("ADD", mth("MULTIPLY", sep.outputs["X"], sep.outputs["X"]), mth("MULTIPLY", sep.outputs["Z"], sep.outputs["Z"])))
    front = mth("LESS_THAN", sep.outputs["Y"], 0.0)
    c = mix(mth("GREATER_THAN", sep.outputs["Z"], radius * 0.45), lin("#e6e0d8"), lin("#9a958f"))   # lid shadow on sclera
    iris = mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.5), front)
    c = mix(iris, c, mix(mth("DIVIDE", r, radius * 0.5), lin("#5a4232"), lin("#1c1512")))
    c = mix(mth("MULTIPLY", mth("LESS_THAN", r, radius * 0.24), front), c, lin("#050505"))
    gx = mth("SUBTRACT", sep.outputs["X"], radius * 0.18); gz = mth("SUBTRACT", sep.outputs["Z"], radius * 0.2)
    glint = mth("LESS_THAN", mth("ADD", mth("MULTIPLY", gx, gx), mth("MULTIPLY", gz, gz)), (radius * 0.11) ** 2)
    c = mix(mth("MULTIPLY", glint, front), c, lin("#ffffff"))
    e = N.new("ShaderNodeEmission"); L.new(c, e.inputs["Color"]); L.new(e.outputs[0], out.inputs[0])
    return m

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
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        near = body_kd.find_n(p, k)
        tot = 0.0; ws = {}
        for co, idx, dist in near:
            f = 1.0 / (dist + 1e-4); tot += f
            for bone, w in per_vert.get(body_used[idx], ()):
                ws[bone] = ws.get(bone, 0) + w * f
        if bias:
            ws = bias(v.co, {b: w / tot for b, w in ws.items()}); tot = 1.0
        for bone, w in ws.items():
            acc.setdefault(bone, []).append((v.index, w / tot))
    for bone, lst in acc.items():
        vg = ob.vertex_groups.get(bone) or ob.vertex_groups.new(name=bone)
        for i, w in lst:
            vg.add([i], w, "REPLACE")

def snap_edge(ob, pick, width, cx):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for v in bm.verts:
        if v.is_boundary and pick(v.co):
            sgn = 1 if v.co.x >= cx else -1
            v.co.x = cx + sgn * width(v.co)
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

def add_mods(ob, arm, subsurf=1, solidify=0.0, outline=False):
    if solidify:
        m = ob.modifiers.new("solid", "SOLIDIFY"); m.thickness = solidify; m.offset = 1.0; m.use_even_offset = False; m.use_quality_normals = True
    m = ob.modifiers.new("arm", "ARMATURE"); m.object = arm
    if solidify:  # armature must run before solidify
        bpy.context.view_layer.objects.active = ob
        ob.modifiers.move(ob.modifiers.find("arm"), 0)
    if subsurf:
        s = ob.modifiers.new("sub", "SUBSURF"); s.levels = 1; s.render_levels = subsurf
    ob.parent = arm

# ---------------------------------------------------------------- build
def build(coll, location=(0, 0, 0), walk=True):
    V, F, G = load_base()
    sk, per_vert = load_rig()
    # ground the rest mesh
    body_faces = [f for f, g in zip(F, G) if g == "body"]
    zmin = min(V[i].z for f in body_faces for i in f)
    for v in V:
        v.z -= zmin
    jpos = {j: sum((V[i] for i in idx), Vector()) / len(idx) for j, idx in sk["joints"].items()}
    dom = {i: max(lst, key=lambda t: t[1])[0] for i, lst in per_vert.items()}
    def region(f, names):
        return all(any(dom.get(i, "").startswith(n) for n in names) for i in f)

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
    bpy.ops.object.mode_set(mode="OBJECT")

    nrm = vnormals(V, body_faces)
    objs = []
    # --- skin: keep head, neck and hands only (the rest is under clothes)
    SKIN_KEEP = ("head", "jaw", "neck", "eye", "oculi", "orbicularis", "oris", "levator", "risorius", "temporalis",
                 "special", "tongue", "wrist", "finger", "metacarpal", "lowerarm02")
    skin_faces = [f for f in body_faces if region(f, SKIN_KEEP)]
    SKIN = cel("#e8c2a2", "#a9775b", rim="#ffe6d2", name="skin")
    skin, used = make_mesh("skin", coll, V, skin_faces); skin.data.materials.append(SKIN)
    assign_weights(skin, used, per_vert); add_mods(skin, arm); objs.append(skin)

    # body KD for weight transfer (full body surface, rest pose)
    bused = sorted({i for f in body_faces for i in f})
    kd = kdtree.KDTree(len(bused))
    for n, i in enumerate(bused):
        kd.insert(V[i], n)
    kd.balance()

    pelvis_z = jpos[sk["bones"]["spine05"]["head"]].z if "spine05" in sk["bones"] else 0.95
    neck_z = jpos[sk["bones"]["neck01"]["head"]].z
    chin_z = jpos[sk["bones"]["head"]["head"]].z

    # --- turtleneck (fits the body: 4 mm off the skin)
    TOP = ("spine", "clavicle", "shoulder", "upperarm", "lowerarm01", "breast", "neck01", "neck02", "pelvis")
    tn_faces = [f for f in body_faces if region(f, TOP) and min(V[i].z for i in f) > pelvis_z - 0.12
                and max(V[i].z for i in f) < chin_z - 0.035]
    off = {i: nrm[i] * 0.004 for f in tn_faces for i in f}
    tn, used = make_mesh("turtleneck", coll, V, tn_faces, off)
    tn.data.materials.append(cel("#cfc4b2", "#7d7466", rim="#fff4e0", name="knit"))
    assign_weights(tn, used, per_vert); add_mods(tn, arm); objs.append(tn)

    # --- coat upper: 1.6 cm off the body, open V at the front
    sternum_z = jpos[sk["bones"]["neck01"]["head"]].z - 0.02
    def open_front(f):
        c = sum((V[i] for i in f), Vector()) / len(f)
        if c.y > -0.02:
            return False
        return c.z > sternum_z - 0.13 and abs(c.x) < 0.012 + max(0.0, sternum_z - c.z) * 0.22
    COAT_SET = ("spine", "clavicle", "shoulder", "upperarm", "lowerarm", "breast", "pelvis")
    coat_faces = [f for f in body_faces if region(f, COAT_SET) and min(V[i].z for i in f) > pelvis_z - 0.1
                  and max(V[i].z for i in f) < neck_z + 0.01 and not open_front(f)]
    def coat_off(i):
        d = 0.016 if not dom.get(i, "").startswith(("lowerarm", "upperarm")) else 0.013
        return nrm[i] * d
    off = {i: coat_off(i) for f in coat_faces for i in f}
    COAT = cel("#2f343c", "#11141a", rim="#d6efff", name="coat")
    cu, used = make_mesh("coat_upper", coll, V, coat_faces, off); cu.data.materials.append(COAT)
    snap_edge(cu, lambda co: co.y < -0.02 and co.z > sternum_z - 0.14 and abs(co.x) < 0.06,
              lambda co: 0.012 + 0.016 + max(0.0, sternum_z - co.z) * 0.22, 0.0)
    assign_weights(cu, used, per_vert); add_mods(cu, arm, solidify=0.006); objs.append(cu)

    # --- coat skirt: MakeHuman skirt helper, lengthened to mid-calf, flared, open front
    sk_faces = [f for f, g in zip(F, G) if g == "helper-skirt"]
    sidx = {i for f in sk_faces for i in f}
    top = max(V[i].z for i in sidx); bot = min(V[i].z for i in sidx)
    cx = sum(V[i].x for i in sidx) / len(sidx); cy = sum(V[i].y for i in sidx) / len(sidx)
    hem = 0.36
    SV = {}
    for i in sidx:
        v = V[i].copy(); t = (top - v.z) / (top - bot)            # 0 at waist, 1 at helper hem
        v.z = top - t * (top - hem)
        rad = Vector((v.x - cx, v.y - cy, 0)); flare = 1.0 + 0.10 + 0.22 * t
        v.x = cx + rad.x * flare; v.y = cy + rad.y * flare + 0.015 * t
        SV[i] = v
    Vs = list(V)
    for i, v in SV.items():
        Vs[i] = v
    def skirt_open(f):
        c = sum((Vs[i] for i in f), Vector()) / len(f)
        return c.y < cy - 0.03 and abs(c.x - cx) < 0.035 + 0.03 * (top - c.z)
    sk_faces = [f for f in sk_faces if not skirt_open(f)]
    cs, _ = make_mesh("coat_skirt", coll, Vs, sk_faces); cs.data.materials.append(COAT)
    snap_edge(cs, lambda co: co.y < cy - 0.02 and abs(co.x - cx) < 0.2,
              lambda co: 0.035 + 0.03 * (top - co.z), cx)
    def skirt_bias(co, ws):  # hem swings less than the legs: mostly pelvis-driven
        out = {}
        legs = sum(w for b, w in ws.items() if b.startswith(("upperleg", "lowerleg")))
        for b, w in ws.items():
            out[b] = w * (0.35 if b.startswith(("upperleg", "lowerleg")) else 1.0)
        out["spine05"] = out.get("spine05", 0) + legs * 0.65
        return out
    weights_from_body(cs, kd, bused, per_vert, bias=skirt_bias)
    disp = cs.modifiers.new("folds", "DISPLACE"); tex = bpy.data.textures.new("folds", "CLOUDS")
    tex.noise_scale = 0.12; disp.texture = tex; disp.strength = 0.012; disp.texture_coords = "LOCAL"
    add_mods(cs, arm, solidify=0.006); objs.append(cs)

    # --- trousers: tights helper, 1 cm off, straight leg below the knee, hem breaks on the shoe
    tf = [f for f, g in zip(F, G) if g == "helper-tights"]
    tidx = {i for f in tf for i in f}
    tn_ = vnormals(V, tf)
    TV = list(V)
    for i in tidx:
        v = V[i] + tn_[i] * 0.009
        side = "L" if v.x > 0 else "R"
        knee = jpos[sk["bones"][f"lowerleg01.{side}"]["head"]]; ank = jpos[sk["bones"][f"foot.{side}"]["head"]]
        if v.z < knee.z:
            t = (knee.z - v.z) / max(knee.z - ank.z, 1e-3)
            axis = knee.lerp(ank, min(t, 1)); rv = Vector((v.x - axis.x, v.y - axis.y, 0))
            want = 0.058 + 0.006 * t
            if rv.length < want and rv.length > 1e-4:
                rv = rv.normalized() * want; v.x = axis.x + rv.x; v.y = axis.y + rv.y
        TV[i] = v
    ank_z = jpos[sk["bones"]["foot.L"]["head"]].z
    tf = [f for f in tf if min(TV[i].z for i in f) > ank_z - 0.035 and max(TV[i].z for i in f) < pelvis_z + 0.06]
    tr, used = make_mesh("trousers", coll, TV, tf); tr.data.materials.append(cel("#24272d", "#0c0e12", rim="#c9e8ff", name="trousers"))
    assign_weights(tr, used, per_vert)
    disp = tr.modifiers.new("folds", "DISPLACE"); tex = bpy.data.textures.new("tfolds", "CLOUDS")
    tex.noise_scale = 0.06; disp.texture = tex; disp.strength = 0.004; disp.texture_coords = "LOCAL"
    add_mods(tr, arm); objs.append(tr)

    # --- hair: scalp helper pushed out, volume on top/front, combed-back grooves, sheen band
    eyeL = jpos[sk["bones"]["eye.L"]["head"]]
    skull = Vector((0.0, eyeL.y + 0.095, eyeL.z + 0.02))
    head_faces = [f for f in body_faces if region(f, ("head", "temporalis", "special"))
                  and all((V[i] - skull).length < 0.165 for i in f)]
    hx = max(abs(V[i].x) for f in head_faces for i in f)
    def scalp(f):
        c = sum((V[i] for i in f), Vector()) / len(f)
        frontness = min(1.0, max(0.0, (eyeL.y + 0.16 - c.y) / 0.16))
        thr = eyeL.z - 0.075 + 0.135 * frontness
        if abs(c.x) > hx * 0.86 and c.z < eyeL.z + 0.035:      # leave the ears out
            return False
        return c.z > thr
    hf = [f for f in head_faces if scalp(f)]
    hidx = {i for f in hf for i in f}
    hc = sum((V[i] for i in hidx), Vector()) / len(hidx)
    HV = list(V)
    for i in hidx:
        p = V[i]; n = nrm[i]
        up = min(1.0, max(0.0, (p.z - eyeL.z - 0.03) / 0.1)); front = min(1.0, max(0.0, (hc.y - p.y) / 0.1))
        th = 0.005 + 0.017 * up + 0.012 * front * up                 # volume on top, swept-back front
        th += 0.0018 * math.sin(p.x * 380) * up                     # comb grooves running front-to-back
        HV[i] = p + n * th + Vector((0, 0.008 * up, 0.004 * front * up))
    hair, used = make_mesh("hair", coll, HV, hf)
    HAIRM = cel("#16181d", "#07080a", rim="#6f7f9f", spec=0.06, spec_col="#5d6782", rim_amt=0.5, name="hair")
    hair.data.materials.append(HAIRM)
    assign_weights(hair, used, per_vert); add_mods(hair, arm, solidify=0.004); objs.append(hair)
    # loose locks swept back off the forehead, two falling forward (the "cool" detail)
    hl = eyeL.z + 0.06; fy = min(V[i].y for i in hidx)
    for k, (x0, drop, curl) in enumerate(((-0.022, 0.05, -0.012), (-0.004, 0.035, 0.01), (0.03, 0.028, -0.006))):
        cu = bpy.data.curves.new(f"lock{k}", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.0042; cu.bevel_resolution = 2
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(3)
        pts = [(x0 * 0.6, fy + 0.03, hl + 0.045), (x0 * 0.8, fy - 0.006, hl + 0.03), (x0 + curl * 0.5, fy - 0.012, hl - drop * 0.5),
               (x0 + curl, fy - 0.006, hl - drop)]
        for bp, co, r in zip(sp.bezier_points, pts, (1.0, 0.9, 0.6, 0.15)):
            bp.co = co; bp.handle_left_type = bp.handle_right_type = "AUTO"; bp.radius = r
        lo = bpy.data.objects.new(f"lock{k}", cu); coll.objects.link(lo); lo.data.materials.append(HAIRM)
        lo.parent = arm; lo.parent_type = "BONE"; lo.parent_bone = "head"
        hb = arm.pose.bones["head"]
        lo.matrix_parent_inverse = (arm.matrix_world @ hb.matrix @ Matrix.Translation((0, hb.length, 0))).inverted()
        objs.append(lo)

    # --- eyes (eye helpers, drawn iris/pupil/glint) and dark lash lines
    for side in ("l", "r"):
        ef = [f for f, g in zip(F, G) if g == f"helper-{side}-eye"]
        eidx = {i for f in ef for i in f}; c = sum((V[i] for i in eidx), Vector()) / len(eidx)
        rad = sum((V[i] - c).length for i in eidx) / len(eidx)
        ob, used = make_mesh(f"eye_{side}", coll, [v - c for v in V], ef)
        ob.location = c; ob.data.materials.append(eye_mat(rad))
        assign_weights(ob, used, per_vert); add_mods(ob, arm, subsurf=2); objs.append(ob)
        for k in (1, 2):
            lf = [f for f, g in zip(F, G) if g == f"helper-{side}-eyelashes-{k}"]
            if lf:
                lo, used = make_mesh(f"lash_{side}{k}", coll, V, lf); lo.data.materials.append(cel("#0c0c0f", "#050506", rim="#0c0c0f", name="lash"))
                assign_weights(lo, used, per_vert); add_mods(lo, arm, subsurf=0); objs.append(lo)

    # --- brows: thick straight manhwa brows, ray-cast onto the forehead
    skin_bvh = bvhtree.BVHTree.FromPolygons([tuple(V[i]) for i in range(len(V))], skin_faces)
    bm = bmesh.new()
    for side, sx in (("l", 1), ("r", -1)):
        ec = jpos[sk["bones"][f"eye.{'L' if sx > 0 else 'R'}"]["head"]]
        rows = []
        for k in range(13):
            s = k / 12
            x = ec.x + sx * (-0.016 + 0.036 * s)
            zc = ec.z + 0.019 + 0.003 * math.sin(math.pi * min(s * 1.15, 1)) - 0.004 * s
            half = 0.0034 * (1 - 0.55 * s) + 0.0006
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
    brows.data.materials.append(cel("#1a1714", "#0b0a09", rim="#1a1714", name="brow"))
    weights_from_body(brows, kd, bused, per_vert, k=2); add_mods(brows, arm, subsurf=0); objs.append(brows)

    # --- shoes: lofted leather dress shoes with sole, heel block and toe spring
    LEATHER = cel("#1b1a1c", "#060607", rim="#bcd8ff", spec=0.035, spec_col="#9aa3b5", name="leather")
    SOLE = cel("#3a2a22", "#1a120e", rim="#3a2a22", name="sole")
    for side in ("L", "R"):
        fv = [i for i in bused if dom.get(i, "").startswith(("foot." + side, "toe")) and (V[i].x > 0) == (side == "L")]
        xs = [V[i].x for i in fv]; ys = [V[i].y for i in fv]
        x0 = sum(xs) / len(xs); yh = max(ys) + 0.012; yt = min(ys) - 0.016   # heel at +y, toe at -y
        Lg = yh - yt; W = (max(xs) - min(xs)) + 0.014
        def section(t, sole=False):
            # half-width, top height and bottom height along the foot (t=0 heel .. 1 toe)
            w = W * (0.36 + 0.14 * math.sin(math.pi * min(t / 0.72, 1) * 0.5))
            if t > 0.8:
                w *= math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 2)) * 0.9 + 0.1
            spring = 0.009 * max(0.0, (t - 0.78) / 0.22) ** 2
            heel = 0.024 if t < 0.27 else (0.012 if t > 0.33 else 0.024 - 0.012 * (t - 0.27) / 0.06)
            if sole:
                return w + 0.003, heel + spring, spring
            h = 0.085 if t < 0.3 else 0.085 - 0.05 * (t - 0.3) / 0.55
            h = max(h, 0.028) * (1 if t < 0.92 else math.sqrt(max(0.0, 1 - (t - 0.92) / 0.08)))
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
            weights_from_body(ob, kd, bused, per_vert, k=6); add_mods(ob, arm, subsurf=1); objs.append(ob)

    # --- pose: mid-stride toward camera, hands in coat pockets
    if walk:
        pose(arm, jpos, sk)
    # normalise height to HEIGHT metres (top of head), then ground the posed feet and place
    top = max(V[i].z for f in skin_faces for i in f)
    arm.scale = (HEIGHT / top,) * 3
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); low = 9.0
    for ob in objs:
        if ob.name.startswith("shoe_sole"):
            e = ob.evaluated_get(dg); mw = e.matrix_world
            low = min(low, min((mw @ v.co).z for v in e.data.vertices))
    arm.location = Vector(location) + Vector((0, 0, -low if low < 9 else 0))
    bpy.context.view_layer.update()
    return arm, objs

def pose(arm, jpos, sk):
    """Aim bones at world directions, parent to child (robust to the A-pose's bent elbows)."""
    vl = bpy.context.view_layer
    def aim(name, d):
        vl.update()
        pb = arm.pose.bones[name]
        cur = (pb.tail - pb.head).normalized(); q = cur.rotation_difference(Vector(d).normalized())
        h = pb.head.copy()
        pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    swing = {"L": (0.16, -0.06), "R": (-0.2, -0.3)}   # (upper-arm y, forearm y): right arm forward, left back
    for side, sx in (("L", 1), ("R", -1)):   # character's left is +x; facing -y
        ua, fa = swing[side]
        aim(f"upperarm01.{side}", (sx * 0.12, ua, -1)); aim(f"upperarm02.{side}", (sx * 0.12, ua, -1))
        aim(f"lowerarm01.{side}", (sx * 0.02, fa, -1)); aim(f"lowerarm02.{side}", (sx * 0.02, fa, -1))
        aim(f"wrist.{side}", (sx * 0.05, fa * 0.6, -1))
    for side in ("L", "R"):                          # relaxed, slightly curled fingers
        for k in range(2, 6):
            for j in (1, 2, 3):
                n = f"finger{k}-{j}.{side}"
                if n in arm.pose.bones:
                    vl.update(); pb = arm.pose.bones[n]; d = (pb.tail - pb.head).normalized()
                    aim(n, d + Vector((0, -0.25 * j, 0)))
    # left leg forward (heel strike), right leg back (push-off)
    aim("upperleg01.L", (0.02, -0.3, -1)); aim("upperleg02.L", (0.02, -0.3, -1))
    aim("lowerleg01.L", (0.0, -0.14, -1)); aim("lowerleg02.L", (0.0, -0.14, -1)); aim("foot.L", (0.0, -1, 0.12))
    aim("upperleg01.R", (-0.02, 0.2, -1)); aim("upperleg02.R", (-0.02, 0.2, -1))
    aim("lowerleg01.R", (0.0, 0.55, -1)); aim("lowerleg02.R", (0.0, 0.55, -1)); aim("foot.R", (0.0, -1, -0.55))
    vl.update()
