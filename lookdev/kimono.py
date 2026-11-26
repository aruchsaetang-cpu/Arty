"""Props that dress the project's rigs as Yamazaki clan members (kimono details, cloak, katana). Same pattern as
character_mh.add_cap: build in world space from the posed bones, then bone_parent so they follow the rig.
    import kimono as KM; KM.add_obi(arm, coll, "#241f2e"); KM.add_crests(arm, coll); KM.add_bun(arm, coll)
Forward is -Y at heading 0; s scales with the rig (arm.scale[0] / 0.83 like add_cap)."""
import math
import bpy
from mathutils import Vector
import character_mh as ch

def _s(arm): return arm.scale[0] / 0.83
def _link(ob, mat, coll, arm, bone):
    ob.data.materials.append(mat)
    for c in list(ob.users_collection): c.objects.unlink(ob)
    coll.objects.link(ob); ch.bone_parent(ob, arm, bone); return ob
def _bonepos(arm, bone):
    bpy.context.view_layer.update(); pb = arm.pose.bones[bone]; return arm.matrix_world @ pb.head

def add_obi(arm, coll, colour="#241f2e"):
    """The wide sash around the waist (a short wide cylinder), on spine04."""
    s = _s(arm); p = _bonepos(arm, "spine04")
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.19 * s, depth=0.14 * s, location=p + Vector((0, 0, 0.02 * s)))
    return _link(bpy.context.object, ch.cel(colour, None, rim="#8f86a8", name="obi"), coll, arm, "spine04")

def add_crests(arm, coll, colour="#f4f1ec"):
    """Two small round white clan crests on the chest (on the breast, left and right of the sternum)."""
    s = _s(arm); p = _bonepos(arm, "spine01"); out = []; R = arm.matrix_world.to_3x3()
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=18, radius=0.024 * s, depth=0.006 * s, location=p + R @ Vector((sx * 0.06 * s, -0.115 * s, -0.03 * s)),
                                            rotation=(math.radians(90), 0, arm.rotation_euler.z))
        out.append(_link(bpy.context.object, ch.glow_mat(colour, 0.8), coll, arm, "spine01"))
    return out

def add_bun(arm, coll, colour="#0c0a0a"):
    """A hair bun on the crown (the mother)."""
    s = _s(arm); pb = arm.pose.bones["head"]; bpy.context.view_layer.update()
    top = arm.matrix_world @ pb.tail; up = (arm.matrix_world.to_3x3() @ (pb.tail - pb.head)).normalized()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.062 * s, location=top + up * 0.025 * s + arm.matrix_world.to_3x3() @ Vector((0, 0.05 * s, 0)))
    return _link(bpy.context.object, ch.cel(colour, None, rim="#7f8faa", name="bun"), coll, arm, "head")

def add_topknot(arm, coll, colour="#e9e6ea"):
    """A white topknot on the crown (the master)."""
    s = _s(arm); pb = arm.pose.bones["head"]; bpy.context.view_layer.update()
    top = arm.matrix_world @ pb.tail; up = (arm.matrix_world.to_3x3() @ (pb.tail - pb.head)).normalized()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=0.045 * s, location=top + up * 0.045 * s)
    return _link(bpy.context.object, ch.cel(colour, "#9a97a3", rim="#ffffff", name="topknot"), coll, arm, "head")

def add_beard(arm, coll, colour="#ecebef"):
    """A long white beard (a flattened cone under the chin)."""
    s = _s(arm); pb = arm.pose.bones["head"]; bpy.context.view_layer.update()
    base = arm.matrix_world @ pb.head; fwd = arm.matrix_world.to_3x3() @ Vector((0, -1, 0)); fwd.normalize()
    bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=0.045 * s, radius2=0.01 * s, depth=0.24 * s, location=base + fwd * 0.07 * s + Vector((0, 0, 0.0)),
                                    rotation=(math.radians(180), 0, 0))
    return _link(bpy.context.object, ch.cel(colour, "#a9a7b3", rim="#ffffff", name="beard"), coll, arm, "head")

def add_cloak(arm, coll, colour="#0b0b10", length=1.15):
    """The father's long black cloak hanging from the shoulders: a wide thin panel behind the back plus two shoulder pieces."""
    s = _s(arm); p = _bonepos(arm, "spine01"); out = []
    bpy.ops.mesh.primitive_cube_add(size=1, location=p + arm.matrix_world.to_3x3() @ Vector((0, 0.13 * s, -0.5 * length * s + 0.05 * s)))
    pan = bpy.context.object; pan.rotation_euler = (0, 0, arm.rotation_euler.z); pan.scale = (0.46 * s, 0.018 * s, 0.5 * length * s * 2)
    out.append(_link(pan, ch.cel(colour, None, rim="#6f7aa0", name="cloak"), coll, arm, "spine01"))
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=p + arm.matrix_world.to_3x3() @ Vector((sx * 0.2 * s, 0.03 * s, 0.1 * s)))
        sh = bpy.context.object; sh.scale = (0.14 * s, 0.2 * s, 0.03 * s); sh.rotation_euler = (0, sx * math.radians(-18), arm.rotation_euler.z)
        out.append(_link(sh, ch.cel(colour, None, rim="#6f7aa0", name="cloak"), coll, arm, "spine01"))
    return out

def add_katana(arm, coll, side="R"):
    """A katana in the hand: blade, guard, grip, parented to the wrist (raised overhead by the pose)."""
    s = _s(arm); bone = f"wrist.{side}"; p = _bonepos(arm, bone); out = []
    bpy.ops.mesh.primitive_cube_add(size=1, location=p + Vector((0, 0, 0.45 * s))); b = bpy.context.object; b.scale = (0.012 * s, 0.003 * s, 0.9 * s)
    out.append(_link(b, ch.cel("#d6dbe6", "#8a93a6", rim="#ffffff", name="blade"), coll, arm, bone))
    bpy.ops.mesh.primitive_cube_add(size=1, location=p + Vector((0, 0, 0.0))); g = bpy.context.object; g.scale = (0.07 * s, 0.07 * s, 0.01 * s)
    out.append(_link(g, ch.cel("#caa24a", "#6d561c", rim="#fff0b0", name="guard"), coll, arm, bone))
    bpy.ops.mesh.primitive_cube_add(size=1, location=p + Vector((0, 0, -0.1 * s))); h = bpy.context.object; h.scale = (0.025 * s, 0.025 * s, 0.2 * s)
    out.append(_link(h, ch.cel("#1a1a1f", None, rim="#7f8faa", name="grip"), coll, arm, bone))
    return out

def add_robe(arm, coll, colour="#3a3446", length=0.85):
    """The kimono skirt: a wide tapered tube from the obi down to the ankles (rigid, for standing and slow-walking characters)."""
    s = _s(arm); p = _bonepos(arm, "spine04")
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.23 * s, radius2=0.18 * s, depth=length * s, location=p + Vector((0, 0, -0.5 * length * s + 0.03 * s)),
                                    rotation=(0, 0, 0))
    return _link(bpy.context.object, ch.cel(colour, None, rim="#8f86a8", name="robe"), coll, arm, "spine04")
