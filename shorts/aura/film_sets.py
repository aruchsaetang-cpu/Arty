# Extra sets for film.py (exec'd inside it, after C.build_scene): the see-through shop, the rooftop, alley dressing,
# and the rain objects for each set (RAINS).

# ------------------------------------------------------------------ a real shop behind the shopkeeper
def _box(coll, name, c, size, mat, rot=0.0):
    me = bpy.data.meshes.new(name); bm_ = bmesh.new()
    bmesh.ops.create_cube(bm_, size=1.0, matrix=Matrix.Diagonal((size[0], size[1], size[2], 1))); bm_.to_mesh(me); bm_.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob); ob.location = c; ob.rotation_euler = (0, 0, rot)
    me.materials.append(mat); return ob

def _emit(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; e_ = m.node_tree.nodes.new("ShaderNodeEmission")
    e_.inputs[0].default_value = C.lin(col); e_.inputs[1].default_value = strength
    m.node_tree.links.new(e_.outputs[0], m.node_tree.nodes["Material Output"].inputs[0]); return m

def shop_interior(probe=(9.5, 54.5, 1.5)):
    """Swap the shop's painted window for clear glass, cut a room into the building and furnish it."""
    P_ = Vector(probe)
    glass = next(o for o in C.CITY.objects if o.name.startswith("shop") and abs(o.matrix_world.translation.x - 7.58) < 0.3
                 and abs(o.matrix_world.translation.y - P_.y) < o.dimensions.y / 2)
    def inside(o):
        lp = o.matrix_world.inverted() @ P_; bb = [Vector(c) for c in o.bound_box]
        return all(min(c[k] for c in bb) <= lp[k] <= max(c[k] for c in bb) for k in range(3))
    bld = next(o for o in C.CITY.objects if o.name.startswith("bld") and inside(o))
    gy = glass.matrix_world.translation.y; hw = glass.dimensions.y / 2
    y0, y1, x0, x1, z0, z1 = gy - hw + 0.1, gy + hw - 0.1, 7.55, 11.8, 0.12, 3.45
    xm, ym, W = (x0 + x1) / 2, (y0 + y1) / 2, y1 - y0
    coll = bpy.data.collections.new("shop_interior"); C.CITY.children.link(coll)
    cut = _box(coll, "shop_cut", (xm, ym, (z0 + z1) / 2), (x1 - x0, W, z1 - z0), C.CONC)
    cut.hide_render = True; cut.display_type = "WIRE"
    bo = bld.modifiers.new("shop_room", "BOOLEAN"); bo.operation = "DIFFERENCE"; bo.object = cut
    try: bo.solver = "EXACT"
    except TypeError: pass
    gm = bpy.data.materials.new("shop_glass_clear"); gm.use_nodes = True; nt = gm.node_tree; nt.nodes.clear()
    o_ = nt.nodes.new("ShaderNodeOutputMaterial"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs[0].default_value = (0.86, 0.93, 0.95, 1); gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.02
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.12
    mx = nt.nodes.new("ShaderNodeMixShader"); nt.links.new(lw.outputs["Fresnel"], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o_.inputs[0])
    glass.data.materials[0] = gm
    # high-detail convenience store (the shop shot looks straight in): coolers, shelving, counter, lights, signs
    exec(open(os.path.join(HERE, "shop_detail.py")).read(), globals())
    shop_dressing(coll, x0, x1, y0, y1, z0, z1, avoid=[(9.4, 54.2), (8.5, 55.5), (10.2, 56.4)])
    print("shop interior", round(x0, 2), round(x1, 2), round(y0, 2), round(y1, 2))
    ld = bpy.data.lights.new("shop_fill", "AREA"); ld.shape = "RECTANGLE"; ld.size = 3.0; ld.size_y = W - 1.0
    ld.energy = 1400; ld.color = (1.0, 0.96, 0.9)
    lo = bpy.data.objects.new("shop_fill", ld); coll.objects.link(lo); lo.location = (9.7, ym, z1 - 0.1)
shop_interior()

# ------------------------------------------------------------------ the rooftop (training): wet tar, parapet, tank, hut
def rooftop(c):
    coll = bpy.data.collections.new("rooftop"); C.CITY.children.link(coll)
    Wx, Wy = 16.0, 13.0
    _box(coll, "roof_mass", (c.x, c.y, c.z / 2 - 0.05), (Wx, Wy, c.z - 0.1), C.facade("concrete"))
    _box(coll, "roof_floor", (c.x, c.y, c.z - 0.05), (Wx, Wy, 0.1), C.ASPH)
    for (dx, dy, sx, sy) in ((0, Wy / 2, Wx, 0.25), (0, -Wy / 2, Wx, 0.25), (Wx / 2, 0, 0.25, Wy), (-Wx / 2, 0, 0.25, Wy)):
        _box(coll, "roof_parapet", (c.x + dx, c.y + dy, c.z + 0.5), (sx, sy, 1.0), C.CONC)
    _box(coll, "roof_hut", (c.x - 5.0, c.y - 3.8, c.z + 1.35), (3.0, 2.6, 2.7), C.CONC)
    _box(coll, "roof_door", (c.x - 3.48, c.y - 3.8, c.z + 1.05), (0.04, 1.0, 2.0), _emit("roof_door_light", "#ffd9a0", 3.0))
    lt = bpy.data.lights.new("roof_door", "AREA"); lt.size = 1.0; lt.energy = 120; lt.color = (1.0, 0.82, 0.6)
    lo = bpy.data.objects.new("roof_door", lt); coll.objects.link(lo); lo.location = (c.x - 3.2, c.y - 3.8, c.z + 1.4)
    lo.rotation_euler = (0, math.radians(90), 0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=1.0, depth=2.0, location=(c.x + 5.2, c.y - 3.6, c.z + 2.0))
    tk = bpy.context.object; tk.name = "roof_tank"
    for cc in list(tk.users_collection): cc.objects.unlink(tk)
    coll.objects.link(tk); tk.data.materials.append(C.principled("tank_blue", "#3a6ea8", 0.4, 0.4))
    for dx, dy in ((-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)):
        _box(coll, "roof_leg", (c.x + 5.2 + dx, c.y - 3.6 + dy, c.z + 0.5), (0.1, 0.1, 1.0), C.METAL)
    for k, (dx, dy) in enumerate(((-6.4, 2.0), (-6.4, 3.4), (6.6, 1.0), (4.0, 5.4))):
        _box(coll, "roof_ac", (c.x + dx, c.y + dy, c.z + 0.45), (0.9, 0.9, 0.9), C.METAL_L)
    # string lights across the roof: small warm bulbs on a sagging line
    for row, (y0, h0) in enumerate(((c.y - 1.0, 3.0), (c.y + 4.5, 2.8))):
        for k in range(15):
            u = k / 14; x = c.x - 7 + 14 * u; z = c.z + h0 - 0.5 * math.sin(math.pi * u)
            _box(coll, "roof_bulb", (x, y0, z), (0.07, 0.07, 0.09), _emit("bulb", "#ffcf7a", 30.0))
    fill = bpy.data.lights.new("roof_fill", "AREA"); fill.size = 10; fill.energy = 900; fill.color = (1.0, 0.78, 0.55)
    fo_ = bpy.data.objects.new("roof_fill", fill); coll.objects.link(fo_); fo_.location = (c.x, c.y + 1.5, c.z + 5.5)
    return coll
rooftop(ROOF)

# ------------------------------------------------------------------ alley dressing: an awning + warm doorway light
coll_al = bpy.data.collections.new("alley_dress"); C.CITY.children.link(coll_al)
_box(coll_al, "awning", (-15.5, AL_Y + 2.05, 2.7), (2.4, 0.9, 0.05), C.principled("awning", "#7a2232", 0.6))
door = bpy.data.lights.new("alley_door", "AREA"); door.size = 1.2; door.energy = 160; door.color = (1.0, 0.8, 0.55)
do_ = bpy.data.objects.new("alley_door", door); coll_al.objects.link(do_); do_.location = (-15.5, AL_Y + 2.3, 2.4)
do_.rotation_euler = (math.radians(70), 0, 0)
for k, x in enumerate((-12.0, -19.0, -26.0, -33.0)):          # light pools between the lanterns
    l_ = bpy.data.lights.new(f"alley_pool{k}", "POINT"); l_.energy = 140; l_.color = (1.0, 0.55, 0.35); l_.shadow_soft_size = 0.4
    o_ = bpy.data.objects.new(f"alley_pool{k}", l_); coll_al.objects.link(o_); o_.location = (x, AL_Y, 4.2)
for k, x in enumerate((14.0, 22.0)):
    l_ = bpy.data.lights.new(f"alley2_pool{k}", "POINT"); l_.energy = 160; l_.color = (1.0, 0.5, 0.42); l_.shadow_soft_size = 0.4
    o_ = bpy.data.objects.new(f"alley2_pool{k}", l_); coll_al.objects.link(o_); o_.location = (x, AL2_Y, 4.2)

# ------------------------------------------------------------------ rain for each set
rain_alley = C.rain(-22.0, AL_Y, 28.0, 5.0, 9.0, 24, 3600)
rain_alley2 = C.rain(18.0, AL2_Y, 20.0, 5.0, 9.0, 24, 2600)
rain_roof = C.rain(ROOF.x, ROOF.y + 2.0, 16.0, 12.0, 9.0, 24, 4200)
for r_, z_ in ((rain_main, 0.0), (rain_alley, 0.0), (rain_alley2, 0.0), (rain_roof, ROOF.z)):
    r_.animation_data_clear(); r_.location = (0, 0, z_)
RAINS = [rain_main, rain_alley, rain_alley2, rain_roof]
