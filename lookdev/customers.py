"""Shop customers as cel-shaded sprites for the see-through shop windows (city.shop_room samples them in the glass shader).

    /root/.venvs/bpy/bin/python lookdev/customers.py [count]
Builds `count` townsfolk with the character builder, every one their own look (build, face, hair, colours, outfit,
bag, mask, pose), and renders each from three sides (front, side, back) on a transparent background:
shorts/aura/assets/customers/c{NN}_{front,side,back}.png  (+ customers.json: height of each in metres)."""
import bpy, os, sys, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import character_mh as ch
N = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 16
OUT = os.path.join(HERE, "..", "shorts", "aura", "assets", "customers"); os.makedirs(OUT, exist_ok=True)
rng = random.Random(2026)

SKIN = [("#f3d6bf", "#bf9274"), ("#f0cfb3", "#b48466"), ("#e9c4a6", "#a8795d"), ("#e3b894", "#a2734f"), ("#c58f6a", "#86583d"),
        ("#f2d5c0", "#c0927a")]
HAIR_COL = ["#15171c", "#1a1414", "#2a1c15", "#4a3022", "#5a3a26", "#7a6a5a", "#2e2a33", "#8a5a3a", "#c8b8a8"]
TOPS = [("#e9e6df", "#9a978f"), ("#2b2d33", "#0e0f12"), ("#8a2f3a", "#4a141c"), ("#3d5a80", "#1c2c44"), ("#c9a46a", "#7d6336"),
        ("#6f7d5c", "#3a4430"), ("#d9d2e9", "#8f86a6"), ("#f2efe9", "#a9a59c"), ("#1f3b34", "#0b1a16"), ("#b85c38", "#66301c"),
        ("#a7b6c8", "#5d6b7c"), ("#e6b8c2", "#a2727c")]
COATS = [None, None, ("#2f343c", "#11141a"), ("#7a5c3e", "#3f2e1e"), ("#c9c0ae", "#857d6c"), ("#1f2a3d", "#0c1220"),
         ("#4b5a3a", "#262e1d"), ("#9b8468", "#5e4d3a")]
LEGS = [("#24272d", "#0c0e12"), ("#3a4a66", "#18202e"), ("#c4b9a6", "#7c7364"), ("#4a4a4d", "#1d1d1f"), ("#7c7f88", "#3a3c42"),
        ("#e8e4da", "#a19c90"), ("#2b2622", "#100d0b")]
SHOES = [("#141416", "#2a2a2e"), ("#f2f2f0", "#141416"), ("#1b1a1c", "#3a2a22"), ("#e8bdb6", "#f2efe9"), ("#7a5a3c", "#45321f")]
BAGS = [None, None, ("#8a5a32", "#4e321b"), ("#1d1d20", "#0b0b0d"), ("#c9b28a", "#7d6a4a")]

def style(k):
    f = rng.random() < 0.5; kid = rng.random() < 0.12
    body = ("kid_f" if f else "kid_m") if kid else ("f" if f else rng.choice(["m", "m_slim", "m_heavy", "m_lean"]))
    st = dict(vary=300 + k, body=body, height=(rng.uniform(1.25, 1.42) if kid else rng.uniform(1.55, 1.70) if f else rng.uniform(1.66, 1.86)),
              skin=rng.choice(SKIN), hair_col=rng.choice(HAIR_COL), top=rng.choice(TOPS), turtleneck=rng.random() < 0.4,
              coat=None, legs="trousers", leg_col=rng.choice(LEGS), shoes=rng.choice(SHOES),
              sneakers=rng.random() < 0.5, clear_face=True, manhwa_head=not kid, subsurf=1, head_yaw=0, locks=False)
    if f:
        st.update(face=rng.choice(["kstar_f", "soft_f", "sharp_f"]), hair=rng.choice(["long", "bob", "long", "bangs"]),
                  hair_len=rng.uniform(0.2, 0.4), lips=rng.choice(["#c25a62", "#d27a7a", "#b84a55"]), brows="#14110f")
        if rng.random() < 0.45:
            st.update(legs="skirt", skirt_hem=rng.uniform(0.3, 0.6), tights=rng.choice(["#e9c9b2", "#23222a"]))
    else:
        st.update(face=rng.choice(["boy", "square", "round", "long", "diamond", "idol"]),
                  hair=rng.choice(["short", "buzz", "quiff", "crop", "bangs", "idol"]), brows="#121014")
    if st["coat"]:
        st.update(hem=rng.uniform(0.8, 0.98), open_skirt=False, open_coat=rng.random() < 0.4, coat_flare=(0.02, 0.04))
    if kid:
        st["face"] = "soft_f" if f else "boy"
    if not kid and rng.random() < 0.5: st["bag"] = rng.choice(BAGS)
    if rng.random() < 0.15: st["mask"] = rng.choice(["#f4f4f2", "#111114"])
    return st, rng.choice(["stand", "stand", "phone"])

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.engine = "CYCLES"; scn.cycles.samples = 10; scn.cycles.use_denoising = False
scn.render.film_transparent = True; scn.view_settings.view_transform = "Standard"
scn.render.image_settings.color_mode = "RGBA"
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.74, 0.7, 1)
cd = bpy.data.cameras.new("cam"); cd.type = "ORTHO"
cam = bpy.data.objects.new("cam", cd); scn.collection.objects.link(cam); scn.camera = cam
meta = {}
for k in range(N):
    st, pose = style(k)
    cc = bpy.data.collections.new(f"c{k}"); scn.collection.children.link(cc)
    arm, objs = ch.build(cc, (0, 0, 0), st, pose_mode=pose); arm.location.z = arm["ground"]
    bpy.context.view_layer.update()
    H = st["height"] + 0.06
    scn.render.resolution_x, scn.render.resolution_y = 260, 600; cd.sensor_fit = "VERTICAL"; cd.ortho_scale = H
    for view, yaw in (("front", -20), ("side", 90), ("back", 180)):
        a = math.radians(yaw); d = 6.0
        cam.location = (d * math.sin(a), -d * math.cos(a), H / 2); cam.rotation_euler = (math.radians(90), 0, a)
        scn.render.filepath = os.path.join(OUT, f"c{k:02d}_{view}.png"); bpy.ops.render.render(write_still=True)
    meta[f"c{k:02d}"] = dict(height=round(H, 3), body=st["body"], pose=pose)
    for o in list(cc.all_objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(cc)
    print("customer", k, st["body"], st.get("hair"), pose, flush=True)
json.dump(meta, open(os.path.join(OUT, "customers.json"), "w"), indent=1)
print("DONE")
