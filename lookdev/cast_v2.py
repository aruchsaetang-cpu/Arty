"""Lineup of the v2 cast + hero face and loafer close-ups:  /root/.venvs/bpy/bin/python lookdev/cast_v2.py [scale]"""
import bpy, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "shorts", "aura"))
import character_mh as ch
import cast as K
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 40
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
cc = bpy.data.collections.new("cast"); scn.collection.children.link(cc)
LINE = [("hero", K.HERO_V1, "pockets"), ("narr_a", K.NARR_A, "umbrella"), ("narr_b", K.NARR_B, "stand"), ("cop", K.COP_V1, "stand"),
        ("shop", K.SHOP, "stand"), ("w1", K.W1, "stand"), ("w2", K.W2, "stand"), ("w4", K.W4, "stand")]
X = {}
for k, (name, st, pose) in enumerate(LINE):
    x = (k - (len(LINE) - 1) / 2) * 0.75; X[name] = x
    if name in ("hero", "cop"):   # first-version designs
        arm, _ = ch.build_v1(cc, (x, 0, 0), dict(st, head_yaw=0), pose_mode=pose, void_eyes=name == "hero")
    else:
        arm, _ = ch.build(cc, (x, 0, 0), dict(st, head_yaw=0), pose_mode=pose)
    arm.location.z = arm["ground"]
    if pose == "umbrella":
        ch.add_umbrella(arm, cc, "#1d2230")
    if pose == "pockets":
        ch.hands_in_pockets(arm)
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.78, 0.8, 0.84, 1)
scn.render.engine = "CYCLES"; scn.cycles.samples = 16; scn.cycles.use_denoising = False
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920; scn.render.resolution_percentage = SCALE
scn.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam
t = bpy.data.objects.new("t", None); scn.collection.objects.link(t)
c = cam.constraints.new("TRACK_TO"); c.target = t; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
OUT = os.path.join(HERE, "renders"); os.makedirs(OUT, exist_ok=True)
hx = X["hero"]
VIEWS = [("v2_lineup", (0, -6.6, 1.05), (0, 0, 1.0), 40, 1080, 1920),
         ("v2_face_hero", (hx + 0.12, -0.95, 1.84), (hx, 0, 1.82), 70, 1080, 1920),
         ("v2_side_hero", (hx - 0.85, 0.15, 1.84), (hx, 0, 1.82), 70, 1080, 1920),
         ("v2_feet_hero", (hx + 0.35, -0.75, 0.16), (hx, 0, 0.08), 40, 1080, 1920),
         ("v2_face_narr_b", (X["narr_b"] + 0.1, -0.95, 1.62), (X["narr_b"], 0, 1.62), 70, 1080, 1920),
         ("v2_body_narr_b", (X["narr_b"], -2.0, 1.25), (X["narr_b"], 0, 1.2), 50, 1080, 1920),
         ("v2_body_hero", (hx, -3.2, 1.0), (hx, 0, 0.95), 50, 1080, 1920)]
only = os.environ.get("VIEWS")
for name, loc, tgt, lens, rx, ry in VIEWS:
    if only and name not in only.split(","):
        continue
    if name == "v2_lineup":
        scn.render.resolution_x, scn.render.resolution_y = 1920, 1080; cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36
    else:
        scn.render.resolution_x, scn.render.resolution_y = rx, ry; cd.sensor_fit = "VERTICAL"
    cam.location = loc; t.location = tgt; cd.lens = lens
    scn.render.filepath = os.path.join(OUT, f"{name}.png"); bpy.ops.render.render(write_still=True)
print("DONE")
