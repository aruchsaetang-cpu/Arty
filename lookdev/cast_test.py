"""Cast lineup + face close-ups for lookdev:  /root/.venvs/bpy/bin/python lookdev/cast_test.py [scale]"""
import bpy, os, sys, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import character_mh as ch
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 40
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
cc = bpy.data.collections.new("cast"); scn.collection.children.link(cc)
src = open(os.path.join(HERE, "..", "shorts", "aura", "film.py")).read()
NARR = eval(src[src.index("NARR = dict(") + 7:src.index("narr_start")].strip())
KID1 = eval(src[src.index("KID1 = dict(") + 7:src.index("KID2 = dict(")].strip())
KID2 = eval(src[src.index("KID2 = dict(") + 7:src.index("shop, _ = ch.build")].strip(), {"KID1": KID1})
if os.environ.get("CAST") == "kids":
    ch.build(cc, (-0.4, 0, 0), dict(KID1, head_yaw=0), pose_mode="stand"); ch.build(cc, (0.4, 0, 0), KID2, pose_mode="stand")
    VIEWS = (("kids_front", (0, -4.6, 0.75), (0, 0, 0.68), 50), ("kids_back", (1.2, 4.2, 0.8), (0, 0, 0.68), 50))
else:
    ch.build(cc, (-0.5, 0, 0), ch.HERO, pose_mode="stand")
    ch.build(cc, (0.5, 0, 0), NARR, pose_mode="stand")
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
for name, loc, tgt, lens in VIEWS if os.environ.get("CAST") == "kids" else (("lineup", (0, -6.4, 1.0), (0, 0, 0.95), 50),
                             ("face_hero", (-0.32, -0.85, 1.8), (-0.5, 0, 1.77), 70),
                             ("face_hero_front", (-0.5, -0.95, 1.79), (-0.5, 0, 1.77), 75),
                             ("face_narr", (0.66, -0.85, 1.69), (0.5, 0, 1.67), 70)):
    cam.location = loc; t.location = tgt; cd.lens = lens
    scn.render.filepath = os.path.join(OUT, f"cast_{name}.png"); bpy.ops.render.render(write_still=True)
print("DONE")
