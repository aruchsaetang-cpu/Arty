"""Character turnaround test: /root/.venvs/bpy/bin/python lookdev/char_test.py [scale]"""
import bpy, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import character_mh as ch
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 25
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
cc = bpy.data.collections.new("character"); scn.collection.children.link(cc)
arm, objs = ch.build(cc, (0, 0, 0))
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.25, 0.28, 0.32, 1)
scn.render.engine = "CYCLES"; scn.cycles.samples = 16; scn.cycles.use_denoising = False
scn.render.use_freestyle = True; scn.render.line_thickness_mode = "ABSOLUTE"; scn.render.line_thickness = 1.0
fs = scn.view_layers[0].freestyle_settings; ls = fs.linesets[0] if fs.linesets else fs.linesets.new("c")
ls.select_by_collection = True; ls.collection = cc; ls.select_crease = False
ls.select_silhouette = True; ls.select_border = True; ls.select_material_boundary = True
ls.linestyle = ls.linestyle or bpy.data.linestyles.new("ink"); ls.linestyle.color = (0.03, 0.03, 0.04); ls.linestyle.thickness = 1.4
scn.render.resolution_x, scn.render.resolution_y = 1080, 1920; scn.render.resolution_percentage = SCALE
scn.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam
t = bpy.data.objects.new("t", None); scn.collection.objects.link(t)
c = cam.constraints.new("TRACK_TO"); c.target = t; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
for name, loc, tgt, lens in (("front", (0, -5.2, 1.0), (0, 0, 0.93), 50), ("three4", (2.6, -4.4, 1.1), (0, 0, 0.93), 50),
                             ("face", (0.22, -0.8, 1.74), (0, 0, 1.72), 70), ("feet", (0.6, -1.5, 0.3), (0, -0.1, 0.1), 50)):
    cam.location = loc; t.location = tgt; cd.lens = lens
    scn.render.filepath = os.path.join(OUT, f"char_{name}.png"); bpy.ops.render.render(write_still=True)
print("DONE")
