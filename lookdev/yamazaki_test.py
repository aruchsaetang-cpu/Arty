"""Build every Yamazaki set at its own X offset and render one tiny still of each into /tmp/yamazaki/.
    /root/.venvs/bpy/bin/python lookdev/yamazaki_test.py [scale%=25] [samples=7] [names...]"""
import os, sys, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import yamazaki as Y
C = Y.C; scn = Y.scn
SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 25
SAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 7
ONLY = sys.argv[3:]
OUT = "/tmp/yamazaki"; os.makedirs(OUT, exist_ok=True)

SETS = [("hall", Y.hall, "indoor"), ("gate", Y.gate_courtyard, "day"), ("dojo", Y.dojo, "day"),
        ("bedroom", Y.bedroom, "night"), ("stairs_night", lambda O: Y.stairway(O, night=True), "night"),
        ("stairs_day", lambda O: Y.stairway(O, night=False), "day")]
built = {}
for i, (name, fn, world) in enumerate(SETS):
    if ONLY and name not in ONLY: continue
    t = time.time(); built[name] = fn(Vector((i * 120.0, 0, 0))); print(name, "built", round(time.time() - t, 1), "s", "tris", built[name].tris, flush=True)

cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36; cd.clip_start = 0.05; cd.clip_end = 3000
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam
C.render_settings(SCALE, SAMPLES)
SHOT = {"hall": "wide", "gate": "into_gate", "dojo": "into_room", "bedroom": "door", "stairs_night": "base", "stairs_day": "base"}
for name, fn, world in SETS:
    if name not in built: continue
    for n, s in built.items(): s.coll.hide_render = (n != name)
    Y.set_world(world)
    loc, tgt, lens = built[name].meta["cams"][SHOT[name]]
    cam.location = Vector(loc) + built[name].O; cd.lens = lens
    cam.rotation_euler = (Vector(tgt) + built[name].O - cam.location).to_track_quat("-Z", "Y").to_euler()
    scn.render.filepath = f"{OUT}/{name}.png"
    t = time.time(); bpy.ops.render.render(write_still=True); print(name, "render", round(time.time() - t, 1), "s ->", scn.render.filepath, flush=True)
