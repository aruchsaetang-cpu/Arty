"""Lineup test for cast_kuro: builds the whole cast in two rows, renders one still.
    /root/.venvs/bpy/bin/python shorts/kuro_oni/cast_test.py [scale%] [samples] [out.png] [names comma list]"""
import os, sys, time, resource
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
T0 = time.time()
import cast_kuro as CK
import bpy
import city as C
from mathutils import Vector as V
scn = C.scn; P = C.PEOPLE_C
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 50
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 8
OUT = sys.argv[3] if len(sys.argv) > 3 else "/tmp/claude-0/-home-user-Arty/850f0f2e-d712-5a7f-92a0-77d71a44d544/scratchpad/cast_lineup.png"
WHICH = sys.argv[4].split(",") if len(sys.argv) > 4 else None
def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0

# rows: main cast front (y=0), clan + kids + town middle (y=3), fighters back (y=6)
front = ["BOY", "TEEN", "HERO", "HERO_HUMAN", "MOTHER", "FATHER", "MASTER", "VASSAL"]
mid = ["CLAN_MEN_%d" % i for i in range(5)] + ["CLAN_WOMEN_0", "CLAN_WOMEN_1"] + ["KID_%d" % i for i in range(4)] + ["TOWN_%d" % i for i in range(6)]
back = ["FIGHTER_%d" % i for i in range(12)]
locs = {}
for row, y in ((front, 0.0), (mid, 3.0), (back, 6.0)):
    for i, n in enumerate(row): locs[n] = (-0.5 * 1.35 * (len(row) - 1) + 1.35 * i, y, 0)
names = [n for n in (front + mid + back) if WHICH is None or any(n == w or n.startswith(w + "_") or w == n.rsplit("_", 1)[0] for w in WHICH)]
t = time.time()
arms = CK.build_cast(P, names, locs=locs, scales={"TEEN": 0.88}, hero_cloak=False)
build_s = time.time() - t; rss_build = rss()
crowd = CK.make_silhouette_crowd(P, 20, area=((-12, 12), (9, 12)), rows=2)
print(f"BUILD {len(arms)} rigs in {build_s:.1f}s, peak RSS {rss_build:.2f} GB; crowd {len(crowd)} objs")

# ground, sun, camera
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 4, 0)); g = bpy.context.object
m = bpy.data.materials.new("gr"); m.use_nodes = True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35, 0.35, 0.38, 1)
g.data.materials.append(m)
sd = bpy.data.lights.new("sun", "SUN"); sd.energy = 3.5; so = bpy.data.objects.new("sun", sd); scn.collection.objects.link(so)
so.rotation_euler = (0.9, 0.2, 0.5)
w = bpy.data.worlds.new("w"); w.use_nodes = True; w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.6, 0.65, 0.75, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8; scn.world = w
cd = bpy.data.cameras.new("cam"); cd.lens = 40; cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam
if os.environ.get("CLOSE"):
    cam.location = (0, -13, 1.4); cam.rotation_euler = (1.5, 0, 0); cd.lens = 40
else:
    cam.location = (0, -17, 4.2); cam.rotation_euler = (1.43, 0, 0)
C.render_settings(SCALE, SAMPLES)
scn.render.resolution_x, scn.render.resolution_y = 1920, 1080; scn.render.resolution_percentage = SCALE
scn.render.filepath = OUT; scn.frame_set(1)
t = time.time(); bpy.ops.render.render(write_still=True); r_s = time.time() - t
print(f"RENDER {r_s:.1f}s, peak RSS {rss():.2f} GB, total {time.time() - T0:.1f}s -> {OUT}")
