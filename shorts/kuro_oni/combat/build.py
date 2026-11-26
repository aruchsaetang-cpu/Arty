"""Build a combat sequence (or one clip) in Blender: cast, plain set + neutral light, solved animation, contact sync,
reactions, secondary motion, camera, decal hooks. Used by render_seq.py, export_glb.py and checks.py.

    W = build.build("combat_test")          # -> World (actors, timemap, hits, report data); scene ready to render
"""
import json, math, os, sys, time, resource
HERE = os.path.dirname(os.path.abspath(__file__)); KO = os.path.dirname(HERE); ROOT = os.path.dirname(os.path.dirname(KO))
for p in (HERE, KO, os.path.join(ROOT, "lookdev"), os.path.join(ROOT, "shorts", "aura")):
    if p not in sys.path: sys.path.insert(0, p)
os.environ.setdefault("FRAMES", "400"); os.environ.setdefault("PEOPLE", "0"); os.environ.setdefault("SEED", "7")
_argv = sys.argv; sys.argv = sys.argv[:1]
import cast_kuro as CK                      # imports city (resets the scene), character_mh, cast, kimono
sys.argv = _argv
import bpy
from mathutils import Vector as V, Matrix
import city as C
import character_mh as ch
import moves as MV
import schema as S
import solver as SV
import moves_ext as MX
import contact as CT
import camera as CAM
import secondary as SEC

def rss(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0


class World:
    def __init__(self, seq):
        self.seq = seq; self.fps = seq["fps"]; self.tm = seq["timemap"]; self.S = seq["story_frames"]
        self.actors = {}; self.objs = {}; self.hits = []; self.eff_keys = {}; self.attacks = []; self.move_specs = []
    # ---- queries used by moves (aiming) and the camera
    def _quick(self, R, t, final=False):
        if final and getattr(R, "ev", None):
            s = max(0, min(self.S - 1, int(round(t * self.fps)))); return R.ev["states"][s], R.ev["fk"][s]
        st = R.blend_state(t)
        for sd in "LR":
            ft = st["foot" + sd]; st["_ank" + sd] = R.ankle_auth(sd, ft); st["_fd" + sd] = R.foot_dir(sd, ft[2], ft[4] if len(ft) > 4 else 0.0)
        loc, q, qm = R.solve(st); fkm = R.fk(R.objmat(st)[2], qm, st["hs"]); return st, fkm
    def pos(self, name, t):
        R = self.actors[name]; st = R.blend_state(t, skip_fists=True); return (st["x"] + R.O.x, st["y"] + R.O.y, 0.0)
    def part(self, name, part, t, final=False):
        R = self.actors[name]; st, fkm = self._quick(R, t, final); return tuple(CT.point(R, fkm, part))
    def hit_target(self, hid):
        h = next(h for h in self.hits if h["id"] == hid); return self.part(h["target"], h["part"], h["_s"] / self.fps)
    def mark_effector_keys(self, layer, hid, chan, tc):
        self.eff_keys.setdefault(hid, []).append((layer, chan, tc))
    def note_attack(self, attacker, target, t0, t1, chan):
        self.attacks.append(dict(attacker=attacker, target=target, t0=t0, t1=t1, chan=chan))
    def next_move_start(self, actor, t):
        ts = [m["_t0"] - m["_bin"] for m in self.move_specs if m["actor"] == actor and m["_t0"] > t + 1e-6]
        return min(ts) if ts else None


def build_set(scn):
    """plain neutral set: a large grey ground, soft key + fill + rim, neutral grey world (fast to render)."""
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0)); gp = bpy.context.object; gp.name = "combat_ground"
    m = bpy.data.materials.new("combat_ground_m"); m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.30, 0.30, 0.31, 1); bsdf.inputs["Roughness"].default_value = 0.85
    gp.data.materials.append(m)
    w = bpy.data.worlds.new("combat_world"); scn.world = w; w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND"); bg.inputs["Color"].default_value = (0.42, 0.43, 0.45, 1); bg.inputs["Strength"].default_value = 0.8
    for name, kind, loc, rot, energy, size in (("key", "AREA", (-3.0, -4.0, 5.0), (math.radians(50), 0, math.radians(-35)), 900, 3.0),
                                               ("fill", "AREA", (4.0, -3.0, 3.0), (math.radians(60), 0, math.radians(50)), 300, 4.0),
                                               ("rim", "AREA", (0.5, 5.0, 4.0), (math.radians(-55), 0, math.radians(180)), 500, 2.5)):
        ld = bpy.data.lights.new(f"combat_{name}", kind); ld.energy = energy; ld.size = size
        lo = bpy.data.objects.new(f"combat_{name}", ld); scn.collection.objects.link(lo); lo.location = loc; lo.rotation_euler = rot


def build(ident, verbose=True, with_camera=True, with_secondary=True, with_hooks=True):
    T0 = time.time()
    seq = S.load_sequence(ident); errs = S.validate_sequence(seq)
    if errs: raise SystemExit("invalid clip data:\n  " + "\n  ".join(errs))
    W = World(seq); scn = bpy.context.scene; fps = W.fps
    first = seq["clip_data"][0]
    # ---- cast (same styles in every clip: consistency)
    names = list(first["actors"]); styles = {n: first["actors"][n]["style"] for n in names}
    locs = {styles[n]: (40 + 3 * i, 40, 0) for i, n in enumerate(names)}
    arms = CK.build_cast(C.PEOPLE_C, [styles[n] for n in names], locs=locs, hero_cloak=any(a.get("cloak") for a in first["actors"].values()))
    for n in names:
        g = arms[styles[n]]; a = first["actors"][n]
        objs = [o for o in g.children_recursive]
        ch.grip(g, "L"); ch.grip(g, "R")
        R = SV.CombatRig(g, n, origin=(0, 0, 0), pockets=bool(a.get("pockets")))
        CT.calibrate(R, objs)
        st = a["start"]; R.ctx.update(x=st["x"], y=st["y"], facing=st["facing"], yaw=st["facing"] - (14 if a.get("pockets") else 28),
                                      twist=6 if a.get("pockets") else 18, drop=0.05 if a.get("pockets") else 0.11, lean=4, hp=3)
        fl, fr = (MV.pocket_feet if a.get("pockets") else MV.kamae_feet)(st["x"], st["y"], st["facing"])
        R.ctx.update(footL=fl, footR=fr)
        W.actors[n] = R; W.objs[n] = objs
    if verbose: print(f"[combat] cast {time.time() - T0:.1f}s rss {rss():.2f} GB", flush=True)
    # ---- moves + hits in global story time
    for c in seq["clip_data"]:
        o = c["_story0"]
        for h in c["hits"]:
            h = dict(h); h["_s"] = o + h["frame"]; h["_phys"] = c["physics"]; h["_clip"] = c["id"]; W.hits.append(h)
        for m in c["moves"]:
            m = dict(m); m["_t0"] = (o + m["start"]) / fps; m["_t1"] = (o + m["end"]) / fps; m["_bin"] = m["blend_in"] / fps
            m["_bout"] = m["blend_out"] / fps; m["_clip"] = c["id"]; W.move_specs.append(m)
    W.hits.sort(key=lambda h: h["_s"]); W.move_specs.sort(key=lambda m: m["_t0"])
    def gen(m):
        R = W.actors[m["actor"]]; spec = S.MOVE_SPECS[m["move"]]
        bu = getattr(R, "busy_until", -1.0)
        if m["_t0"] - m["_bin"] < bu:                # still reacting to a hit: the move waits for the reaction to finish
            sh = bu + m["_bin"] - m["_t0"]; m["_t0"] += sh; m["_t1"] = max(m["_t1"], m["_t0"] + 0.15); m["_delayed"] = round(sh, 3)
        L = R.layer(f"{m['move']}@{m['_clip']}:{m['start']}", m["_t0"], m["_t1"], blend_in=m["_bin"], ease=m["easing"],
                    balance=spec["balance"], kind=spec["kind"])
        MX.MOVES[m["move"]](L, m["_t0"], m["_t1"] - m["_t0"], m["easing"], m["params"], W)
        R.set_blend_out(L, m["_bout"]); m["_layer"] = L
    pending = list(W.move_specs)
    for h in W.hits:                                  # chronological: moves up to the hit, then contact sync + reaction
        th = h["_s"] / fps
        while pending and pending[0]["_t0"] < th - 1e-9: gen(pending.pop(0))
        CT.retarget(W, h); CT.make_reaction(W, h)
        if verbose: print(f"[combat] hit {h['id']} solver err {h['_err_solver_cm']} cm  log {h['_retarget_log']}  reaction {h['_reaction']}", flush=True)
    while pending: gen(pending.pop(0))
    for rnd in range(3):                              # final contact pass: later moves can nudge an earlier contact
        worst = 0.0
        for h in W.hits:
            CT.retarget(W, h); worst = max(worst, h["_err_solver_cm"])
        if worst < 0.06: break
    for R in W.actors.values(): R.evaluate(W.S, fps)
    if verbose: print(f"[combat] solved {time.time() - T0:.1f}s", flush=True)
    for R in W.actors.values():
        R.bake(W.tm, R.ev)
        if any(n == "fall" for _, _, n in R.flags):
            t_fall = min(a for a, _, n in R.flags if n == "fall"); f_fall = W.tm.out_of(int(t_fall * fps))
            for cobj in R.g.children:
                if cobj.name.startswith("contact_shadow"):
                    for f, hide in ((1, False), (f_fall, True)):
                        cobj.hide_render = hide; cobj.keyframe_insert("hide_render", frame=f)
    build_set(scn)
    W.secondary = SEC.setup_and_simulate(W, seq) if with_secondary else {}
    if with_camera: W.cam, W.cam_info = CAM.build(scn, seq, W)
    if with_hooks:
        for h in W.hits:
            if h.get("decal") in CT.HOOKS: h["_decal"] = CT.HOOKS[h["decal"]](W, h, W.tm.out_of(h["_s"])).name
    scn.frame_start, scn.frame_end = 1, W.tm.n_out; scn.render.fps = fps
    W.build_s = round(time.time() - T0, 1); W.rss = round(rss(), 2)
    if verbose: print(f"[combat] built {ident}: {W.tm.n_out} output frames, {W.build_s}s rss {W.rss} GB", flush=True)
    return W
