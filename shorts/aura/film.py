""""Aura Monster": the story short, staged in the city of Sol.

    /root/.venvs/bpy/bin/python shorts/aura/film.py [scale%] [first] [last]
Renders PNG frames to shorts/aura/frames/ (existing frames are skipped, so it can resume).
env: SAMPLES (default 16), NORENDER=1 to only build, STILLS="f1,f2,..." to render single frames.
Shot timing comes from beats.json (python3 shorts/aura/cues.py).
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BEATS = json.load(open(os.path.join(HERE, "beats.json")))
N = BEATS["frames"]
os.environ["FRAMES"] = str(N)
os.environ.setdefault("PEOPLE", "24"); os.environ.setdefault("LIGHT_EXTRAS", "1"); os.environ.setdefault("SEED", "7")
sys.path.insert(0, os.path.join(ROOT, "lookdev"))
import bpy, bmesh
from mathutils import Vector
import city as C                     # importing resets the scene and defines the city builders
import character_mh as ch

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 50
FIRST = int(sys.argv[2]) if len(sys.argv) > 2 else 1
LAST = int(sys.argv[3]) if len(sys.argv) > 3 else N
SAMPLES = int(os.environ.get("SAMPLES", 16))
scn = C.scn; prefs = C.prefs
B = {b["id"]: b for b in BEATS["shots"]}
B["payoff"] = B["payoff_side"]               # the handover to the narrator starts with this shot
def fr(shot, k=0): return B[shot]["f0" if k == 0 else "f1"]

# ------------------------------------------------------------------ cast (built before the city)
HERO_X, HERO_Y0, CYCLE = 0.6, 66.0, 34
TURN = fr("turn") + 6                       # hero stops walking here, then turns around
FREEZE = BEATS["freeze_frame"]               # "The rain stopped around me"

hero, _ = ch.build(C.PEOPLE_C, (HERO_X, HERO_Y0, 0), ch.HERO, pose_mode="walk"); hero.name = "HERO"
speed = ch.animate_walk(hero, (HERO_X, HERO_Y0, 0), 0.0, -40, TURN - 1, phase=0.0, cycle=CYCLE)
def hero_y(f): return HERO_Y0 - speed * (min(f, TURN) + 40) / 30.0
STOP = Vector((HERO_X, hero_y(TURN), hero["ground"]))
prefs.keyframe_new_interpolation_type = "BEZIER"
scn.frame_set(TURN)
ch.posed(hero, "stand")                    # settle into a stand, then turn round to face the narrator
for b in ch.ANIM_BONES:
    hero.pose.bones[b].keyframe_insert("rotation_quaternion", frame=TURN + 8)
hero.location = STOP; hero.keyframe_insert("location", frame=TURN + 8)
hero.rotation_euler = (0, 0, 0); hero.keyframe_insert("rotation_euler", index=2, frame=TURN + 10)
hero.rotation_euler = (0, 0, math.pi); hero.keyframe_insert("rotation_euler", index=2, frame=TURN + 26)

# the narrator (who inherits the job): an ordinary kid in a dark hoodie, jeans and sneakers, heavy fringe
NARR = dict(body="m_lean", height=1.8, skin=("#f1d3ba", "#b4876e"), hair="bangs", hair_col="#15171c", locks=False,
            top=("#2a2c33", "#0b0c10"), turtleneck=True, coat=None, manhwa_head=True,
            legs="trousers", leg_col=("#4a6d96", "#1d2c44"), shoes=("#1c1c20", "#e8e6e0"), sneakers=True,
            brows="#16131a", iris="#2e2624")
narr_start = STOP + Vector((0, 2.2, 0))
narr, _ = ch.build(C.PEOPLE_C, (narr_start.x, narr_start.y, 0), NARR, pose_mode="walk"); narr.name = "NARRATOR"
nspeed = ch.animate_walk(narr, (narr_start.x, narr_start.y, 0), 0.0, fr("payoff") - 34, N, phase=0.25, cycle=36)

# the three theories: a shopkeeper, a police officer, two kids
SHOP = dict(manhwa_head=True, body="m_heavy", height=1.72, skin=("#e3b894", "#a2734f"), hair="buzz", hair_col="#22201f", coat=None,
            top=("#e9e6df", "#9a978f"), turtleneck=False, leg_col=("#4a4a4d", "#1d1d1f"), head_yaw=28, subsurf=1)
COP = dict(manhwa_head=True, body="m", height=1.82, skin=("#f0cfb3", "#b48466"), hair="short", locks=False, coat=("#1f2a3d", "#0c1220"),
           hem=0.62, top=("#8a9bb0", "#4b5868"), turtleneck=False, leg_col=("#1f2a3d", "#0c1220"), head_yaw=-24, subsurf=1)
KID1 = dict(body="f", height=1.28, skin=("#f3d6bf", "#bf9274"), hair="bob", hair_col="#2a1d16", coat=("#e2b437", "#8f6f16"),
            hem=0.62, top=("#e9e6df", "#9a978f"), legs="trousers", leg_col=("#2f3f5a", "#141c2b"),
            shoes=("#ecebe7", "#d9d7d0"), sneakers=True, head_yaw=30, subsurf=1)
KID2 = dict(KID1, body="m", height=1.34, hair="short", locks=False, coat=("#d23a26", "#7a1d12"), head_yaw=0)
shop, _ = ch.build(C.PEOPLE_C, (6.9, 53.0, 0.15), SHOP, pose_mode="stand", heading=-90)
cop, _ = ch.build(C.PEOPLE_C, (-5.5, 49.0, 0.15), COP, pose_mode="umbrella", heading=90)
ch.add_umbrella(cop, C.PEOPLE_C, "#121214"); ch.add_cap(cop, C.PEOPLE_C)
kid1, _ = ch.build(C.PEOPLE_C, (5.35, 45.1, 0.15), KID1, pose_mode="stand", heading=-90)
kid2, _ = ch.build(C.PEOPLE_C, (5.9, 44.3, 0.15), KID2, pose_mode="phone", heading=-90)
ch.add_phone(kid2, C.PEOPLE_C)
for k in (kid1, kid2):                       # children: larger head for their height
    k.pose.bones["head"].scale = (1.16, 1.16, 1.16)

# ------------------------------------------------------------------ the city
C.build_scene(with_hero=False, avoid=[(6.9, 53), (-5.5, 49), (5.6, 44.8), (HERO_X, 40)],
              rain_box=(0.0, 40.0, 18.0, 64.0, 9.0, 24, 18000))

# rain: falls, freezes on "The rain stopped around me", falls again for the payoff
rain = bpy.data.objects["rain"]; rain.animation_data_clear()
prefs.keyframe_new_interpolation_type = "CONSTANT"
phase, H, T = 0, 9.0, 24
for f in range(1, N + 1):
    falling = f < FREEZE or f >= fr("payoff")
    if falling:
        phase += 1
    rain.location.z = -H * ((phase % T) / T); rain.keyframe_insert("location", index=2, frame=f)
ch.set_interp(rain, "CONSTANT")
# a dry channel: no drop ever touches the hero's (and later the narrator's) path
bm = bmesh.new(); bm.from_mesh(rain.data)
ylo, yhi = hero_y(TURN) - 9.0, HERO_Y0 + 1.0
kill = [fc for fc in bm.faces if abs(fc.calc_center_median().x - HERO_X) < 0.8 and ylo < fc.calc_center_median().y < yhi]
bmesh.ops.delete(bm, geom=kill, context="FACES"); bm.to_mesh(rain.data); bm.free()

# the aura: a cold light that wakes when the storm is held up
def aura(owner, f_on, f_full, f_off=None, watts=70):
    ld = bpy.data.lights.new("aura", "POINT"); ld.color = (0.55, 0.92, 1.0); ld.shadow_soft_size = 0.6
    ob = bpy.data.objects.new("aura", ld); C.FX.objects.link(ob); ob.parent = owner; ob.location = (0, 0, 1.15 / owner.scale[0])
    prefs.keyframe_new_interpolation_type = "BEZIER"
    for f, e in ((1, 0), (f_on, 0), (f_full, watts)) + (((f_off - 1, watts), (f_off, 0)) if f_off else ()):
        ld.energy = e; ld.keyframe_insert("energy", frame=f)
    return ob
aura(hero, FREEZE - 4, FREEZE + 24, fr("payoff"))
aura(narr, fr("payoff"), fr("payoff") + 30, None, 45)

# the white aura is composited from a per-frame mask of the hero/narrator (see compose.py):
# tag them with pass index 7 so the compositor can write the mask next to each frame.
for rig in (hero, narr):
    for o in [rig] + list(rig.children_recursive):
        o.pass_index = 7
json.dump({"keys": [[1, 0.55], [FREEZE - 4, 0.55], [FREEZE + 20, 1.25], [fr("payoff"), 1.0], [fr("payoff") + 30, 1.1]]},
          open(os.path.join(HERE, "aura.json"), "w"))

# who is visible when: the hero hands over to the narrator at the payoff
def visible(rig, f_show, f_hide=None):
    obs = [rig] + list(rig.children_recursive)
    prefs.keyframe_new_interpolation_type = "CONSTANT"
    for o in obs:
        for f, hide in ((1, f_show > 1), (f_show, False)) + (((f_hide, True),) if f_hide else ()):
            o.hide_render = hide; o.keyframe_insert("hide_render", frame=f)
visible(hero, 1, fr("payoff")); visible(narr, fr("payoff"))

# ------------------------------------------------------------------ camera: one rig, hard cuts between shots
cam, tgt, cd = C.make_camera()
focus = bpy.data.objects.new("focus", None); scn.collection.objects.link(focus); cd.dof.focus_object = focus
prefs.keyframe_new_interpolation_type = "LINEAR"
def key(f, loc, look, foc, lens, fstop):
    cam.location = loc; cam.keyframe_insert("location", frame=f)
    tgt.location = look; tgt.keyframe_insert("location", frame=f)
    focus.location = foc; focus.keyframe_insert("location", frame=f)
    cd.lens = lens; cd.keyframe_insert("lens", frame=f)
    cd.dof.aperture_fstop = fstop; cd.dof.keyframe_insert("aperture_fstop", frame=f)
def hp(f): return Vector((HERO_X, hero_y(f), 0))
V = Vector
head = V((0, 0, 1.72))
def shot(sid, start, end):
    """Key a shot at its first and last frame: start/end = (cam, look, focus, lens, fstop) for frame f."""
    a, b = fr(sid), fr(sid, 1)
    key(a, *start(a)); key(b, *end(b))
def on_hero(cam_off, look_off, lens, fstop):
    return lambda f: (hp(f) + V(cam_off), hp(f) + V(look_off), hp(f) + head, lens, fstop)
def on_narr(cam_off, look_off, lens, fstop):
    return lambda f: (np_(f) + V(cam_off), np_(f) + V(look_off), np_(f) + head, lens, fstop)
def fixed(cam_p, look_p, foc_p, lens, fstop):
    return lambda f: (V(cam_p), V(look_p), V(foc_p), lens, fstop)
def np_(f): return narr_start + V((0, -nspeed * max(0, f - (fr("payoff") - 34)) / 30.0, 0))

# about every 3 s a new angle, cut just before the line that motivates it
shot("hook_wide",   on_hero((1.9, -17, 1.5), (-0.4, 10, 4.2), 24, 4.0),  on_hero((1.5, -12.5, 1.42), (-0.2, 8, 3.0), 26, 3.2))
shot("hook_feet",   on_hero((0.45, -1.7, 0.18), (0, 0, 0.32), 30, 2.0),  on_hero((0.38, -1.5, 0.2), (0, 0, 0.36), 30, 2.0))   # dry shoes, rain splashing around
shot("name_med",    on_hero((1.0, -3.5, 0.95), (0, 0, 1.5), 38, 2.0),    on_hero((0.8, -3.2, 1.0), (0, 0, 1.52), 40, 2.0))
shot("name_close",  on_hero((1.15, -1.0, 1.62), (0, -0.25, 1.66), 60, 2.0), on_hero((1.05, -0.8, 1.62), (0, -0.25, 1.66), 62, 2.0))  # profile
shot("shop",        fixed((4.6, 51.5, 1.45), (6.9, 53.3, 1.62), (6.9, 53.0, 1.62), 45, 2.0),
                    fixed((4.85, 51.75, 1.47), (6.9, 53.3, 1.62), (6.9, 53.0, 1.62), 45, 2.0))
shot("cop",         fixed((-3.25, 47.5, 1.35), (-5.5, 49.2, 1.72), (-5.5, 49.0, 1.7), 45, 2.0),
                    fixed((-3.5, 47.8, 1.38), (-5.5, 49.2, 1.72), (-5.5, 49.0, 1.7), 45, 2.0))
shot("kids",        fixed((3.2, 42.7, 1.0), (5.65, 44.7, 1.12), (5.6, 44.7, 1.15), 34, 2.2),
                    fixed((3.45, 42.95, 1.02), (5.65, 44.7, 1.12), (5.6, 44.7, 1.15), 34, 2.2))
shot("follow",      on_hero((0.75, 3.3, 1.72), (0, -6, 1.35), 30, 2.8),  on_hero((0.65, 3.1, 1.7), (0, -6, 1.3), 30, 2.8))
shot("freeze",      on_hero((-2.9, -0.6, 1.25), (0, -0.4, 1.55), 26, 3.5), on_hero((-2.7, -1.2, 1.3), (0, -0.4, 1.6), 26, 3.5))   # side track: rain stops
shot("reveal_low",  on_hero((0.55, -2.4, 0.32), (0, 0, 2.6), 20, 5.0),   on_hero((0.5, -2.2, 0.3), (0, 0, 2.8), 20, 5.0))   # up into the frozen storm
shot("reveal_crane", on_hero((1.0, 4.0, 2.2), (0, -6, 1.2), 26, 5.6),    on_hero((0.5, 11.0, 23.0), (0, -9, 0.5), 24, 11.0))
shot("turn",        lambda f: (STOP + V((0.35, 2.6, 1.66)), STOP + V((0, 0, 1.6)), STOP + head, 50, 2.0),
                    lambda f: (STOP + V((0.3, 2.2, 1.66)), STOP + V((0, 0, 1.62)), STOP + head, 52, 2.0))
shot("payoff_side", on_narr((1.6, -2.7, 1.0), (0, 0, 1.5), 35, 2.2),    on_narr((1.4, -2.4, 1.05), (0, 0, 1.55), 35, 2.2))
shot("payoff_wide", on_narr((0.6, 4.0, 1.3), (0, -9, 1.7), 26, 3.5),    on_narr((0.4, 6.5, 3.0), (0, -9, 1.5), 24, 4.0))

# hard cuts between shots, constant speed inside each shot (no overshoot / swinging camera)
for idb in (cam, tgt, focus, cd, cd.dof):
    ch.set_interp(idb, "LINEAR")
ch.set_interp(cd, "LINEAR")

# ------------------------------------------------------------------ render
C.render_settings(SCALE, SAMPLES)
scn.frame_start, scn.frame_end = FIRST, LAST
scn.frame_step = int(os.environ.get("STEP", 1))       # STEP=2 renders on twos (held frames at encode)
out_dir = os.path.join(HERE, "frames"); os.makedirs(out_dir, exist_ok=True)
scn.render.image_settings.file_format = "PNG"
# compositor: pass the image through and save the hero mask (object index 7) as masks/mask_####.png
scn.render.compositor_device = "CPU"
scn.view_layers[0].use_pass_object_index = True
ng = bpy.data.node_groups.new("comp", "CompositorNodeTree"); scn.compositing_node_group = ng
rl = ng.nodes.new("CompositorNodeRLayers"); idm = ng.nodes.new("CompositorNodeIDMask"); idm.inputs["Index"].default_value = 7
go = ng.nodes.new("NodeGroupOutput"); ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
ng.links.new(rl.outputs["Image"], go.inputs[0]); ng.links.new(rl.outputs["Object Index"], idm.inputs["ID value"])
fo = ng.nodes.new("CompositorNodeOutputFile"); fo.directory = os.path.join(HERE, "masks"); fo.file_name = "mask_"
fo.format.media_type = "IMAGE"; fo.format.file_format = "PNG"; fo.format.color_mode = "BW"
fo.file_output_items.new("FLOAT", ""); ng.links.new(idm.outputs["Alpha"], fo.inputs[0])
if os.environ.get("NORENDER"):
    print("built only"); sys.exit(0)
if os.environ.get("STILLS"):
    for f in [int(x) for x in os.environ["STILLS"].split(",")]:
        scn.frame_set(f); scn.render.filepath = os.path.join(HERE, "stills", f"s{f:04d}.png")
        bpy.ops.render.render(write_still=True); print("WROTE still", f)
else:
    scn.render.filepath = os.path.join(out_dir, "f")
    scn.render.use_overwrite = False; scn.render.use_placeholder = True    # resumable; parallel-safe
    bpy.ops.render.render(animation=True)
    print("WROTE frames", FIRST, LAST)
