"""Export a combat sequence to ONE GLB for the Three.js preview: the three skinned characters once, and one glTF
animation per clip (plus the whole sequence), baked from the solved armature keys (NLA track per clip -> glTF
animation). A manifest.json beside it carries what glTF cannot: clip timing, hit events (contact points), foot-lock
plant markers, camera cuts, cel base colours per material.

    python shorts/kuro_oni/combat/export_glb.py combat_test      # -> combat/preview/combat_test.glb + combat_test.json
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
BPY = "/root/.venvs/bpy/bin/python"
try:
    import bpy  # noqa
except ImportError:
    os.execv(BPY, [BPY, os.path.abspath(__file__)] + sys.argv[1:])
sys.path.insert(0, HERE)
args = [a for a in sys.argv[1:] if not a.startswith("-")]
SEQ = args[0] if args else "combat_test"
import build
import bpy
from mathutils import Vector as V
import character_mh as ch
import contact as CT

PREV = os.path.join(HERE, "preview")


def gl(p):                       # Blender Z-up -> glTF Y-up
    p = V(p); return [round(p.x, 4), round(p.z, 4), round(-p.y, 4)]


def main():
    T0 = time.time()
    W = build.build(SEQ, with_camera=True, with_secondary=False, with_hooks=False)
    scn = bpy.context.scene; tm = W.tm; fps = W.fps; seq = W.seq
    clips = [(c["id"], c["_out"][0], c["_out"][1]) for c in seq["clip_data"]]
    if len(clips) > 1: clips.append((seq["id"], 1, tm.n_out))
    for n, R in W.actors.items():                     # NLA track per clip, each a window of the one baked action
        ad = R.g.animation_data; act = ad.action; slot = getattr(ad, "action_slot", None); ad.action = None
        for cid, f0, f1 in clips:
            tr = ad.nla_tracks.new(); tr.name = cid
            st = tr.strips.new(cid, 1, act)
            if slot is not None and hasattr(st, "action_slot"):
                try: st.action_slot = slot
                except Exception: pass
            st.action_frame_start = f0; st.action_frame_end = f1; st.frame_end = 1 + (f1 - f0)
            tr.mute = False
    # export selection: armatures + their meshes (no contact discs, no hair curves)
    bpy.ops.object.select_all(action="DESELECT")
    for n, R in W.actors.items():
        R.g.select_set(True)
        for o in R.g.children_recursive:
            if o.type == "MESH" and not o.name.startswith("contact_shadow"): o.select_set(True)
    bpy.context.view_layer.objects.active = W.actors["hero"].g if "hero" in W.actors else next(iter(W.actors.values())).g
    for m in bpy.data.materials:                      # cel node trees do not survive glTF: put the base colour where it can
        m.diffuse_color = (0.6, 0.6, 0.6, 1)
    cols = {}
    import character_v1 as v1
    caches = list(ch._cache.items()) + list(getattr(v1, "_cache", {}).items())
    for key, m in caches:
        if not isinstance(key, tuple) or not isinstance(key[0], str) or not key[0].startswith("#"): continue
        try:
            c = ch.lin(key[0]); m.diffuse_color = c; cols[m.name] = "#%02x%02x%02x" % tuple(int(max(0, min(1, x)) ** (1 / 2.2) * 255) for x in c[:3])
        except Exception: pass
    for m in bpy.data.materials:              # copies made by Blender (name.00N) keep their source colour
        if m.name in cols or not m.users: continue
        src = next((k for k in cols if m.name.startswith(k + ".")), None)
        if src: cols[m.name] = cols[src]
    os.makedirs(PREV, exist_ok=True); p = os.path.join(PREV, f"{SEQ}.glb")
    kw = dict(filepath=p, export_format="GLB", use_selection=True, export_apply=False, export_animations=True,
              export_force_sampling=True, export_yup=True, export_skins=True, export_morph=False, export_materials="EXPORT",
              export_animation_mode="NLA_TRACKS", export_def_bones=False, export_optimize_animation_size=True, export_image_format="NONE")
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as e:
        print("exporter option fallback:", e); kw.pop("export_image_format", None); kw.pop("export_optimize_animation_size", None)
        bpy.ops.export_scene.gltf(**kw)
    size = os.path.getsize(p)
    # manifest
    man = dict(seq=SEQ, fps=fps, frames=tm.n_out, glb=os.path.basename(p), actors={n: R.g.name for n, R in W.actors.items()},
               materials=cols, clips=[])
    for cid, f0, f1 in clips:
        hits = []
        for h in W.hits:
            fo = tm.out_of(h["_s"])
            if f0 <= fo <= f1:
                hits.append(dict(id=h["id"], frame=fo - f0, time=round((fo - f0) / fps, 4), attacker=h["attacker"], target=h["target"],
                                 part=h["part"], effector=h["effector"], hitstop=h["hitstop"], point=gl(h["_target"])))
        plants = []
        for n, R in W.actors.items():
            for pl in R.ev["plants"]:
                a, b = tm.out_of(pl["a"]), tm.out_last(pl["b"])
                if b < f0 or a > f1: continue
                plants.append(dict(actor=n, side=pl["side"], kind=pl["kind"], t0=round((max(a, f0) - f0) / fps, 4),
                                   t1=round((min(b, f1) - f0) / fps, 4), point=gl(pl["anchor"])))
        cuts = [dict(time=round((c["frame"] - f0) / fps, 4), clip=c["clip"]) for c in W.cam_info["cuts"] if f0 <= c["frame"] <= f1]
        man["clips"].append(dict(id=cid, start_frame=f0, frames=f1 - f0 + 1, duration=round((f1 - f0 + 1) / fps, 4), hits=hits, plants=plants, cuts=cuts))
    with open(os.path.join(PREV, f"{SEQ}.json"), "w") as fh: json.dump(man, fh, indent=1)
    # verify: the GLB has one animation per clip with channels
    import struct
    b = open(p, "rb").read(); n = struct.unpack("<I", b[12:16])[0]; J = json.loads(b[20:20 + n])
    anims = [(a.get("name"), len(a.get("channels", []))) for a in J.get("animations", [])]
    print("GLB", p, size, "bytes  nodes", len(J.get("nodes", [])), "skins", len(J.get("skins", [])), "meshes", len(J.get("meshes", [])),
          "animations", anims, f"{time.time() - T0:.0f}s", flush=True)
    ok = all(any(a[0] == cid and a[1] > 0 for a in anims) for cid, _, _ in clips)
    print("EXPORT", "OK" if ok else "MISSING CLIPS", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
