"""Combat clip / sequence data: JSON loader, validator and the story-time <-> output-frame map (hit-stop).

Pure Python (no bpy): `python -m` friendly, used by the solver, the renderer, the GLB exporter and the tests.

    import schema as S
    seq = S.load_sequence("combat_test")          # or S.load_sequence("ct_slip_punch_a"): one clip = a sequence of one
    errs = S.validate_sequence(seq)               # [] when valid
    tm = seq["timemap"]; tm.story(f_out) -> story frame; tm.out_of(story_frame) -> first output frame

Frames: every frame number inside a clip is CLIP-LOCAL STORY time (0 = first frame of the clip, at clip fps).
Story time is the action's own time; hit-stop holds story time still for `hitstop` extra OUTPUT frames after each
contact, so a clip's output length = story_frames + sum(hitstop). `duration` in the JSON is that output length and
the validator checks it. Output frames are 1-based (Blender), global over the sequence.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
CLIP_DIR = os.path.join(HERE, "clips")
SEQ_DIR = os.path.join(HERE, "sequences")

EASINGS = ("io", "in", "out", "snap", "lin")
# move registry (names the solver implements in moves_ext.MOVES). kind drives blending defaults and checks:
# attack moves end exactly on their hit frame; balance = "enforce" -> the solver keeps the centre of mass over the
# planted feet, "report" -> only measured (steps, lunges, reactions are dynamic).
MOVE_SPECS = {
    "pocket_idle":     dict(kind="idle",     balance="enforce", params={"seed": int}),
    "guard_idle":      dict(kind="idle",     balance="enforce", params={"seed": int, "bounce": float}),
    "hurt_idle":       dict(kind="idle",     balance="enforce", params={"seed": int}),
    "slip_turn":       dict(kind="dodge",    balance="enforce", params={"pocket": bool, "hold": float}),
    "gyaku_zuki":      dict(kind="attack",   balance="enforce", params={"pocket": bool, "drive": float, "hit": str}),
    "mawashi_geri_low": dict(kind="attack",  balance="enforce", params={"side": str, "pocket": bool, "hit": str}),
    "uchi_uke":        dict(kind="block",    balance="enforce", params={"side": str}),
    "pocket_recover":  dict(kind="recovery", balance="enforce", params={}),
    "kick_recover":    dict(kind="recovery", balance="report",  params={"side": str}),
    "guard_recover":   dict(kind="recovery", balance="report",  params={"face": str}),
    "turn_step":       dict(kind="turn",     balance="report",  params={"face": str, "facing": float, "pocket": bool}),
    "step_in":         dict(kind="step",     balance="report",  params={"dist": float, "face": str}),
    "hook_r":          dict(kind="attack",   balance="report",  params={"aim": str, "step": float}),
    "lunge_punch":     dict(kind="attack",   balance="report",  params={"aim": str, "step": float}),
}
BODY_PARTS = ("cheek_L", "cheek_R", "jaw", "nose", "solar_plexus", "liver", "ribs_L", "thigh_L", "thigh_R", "calf_L", "calf_R")
EFFECTORS = ("fist_L", "fist_R", "shin_L", "shin_R", "foot_L", "foot_R")
STYLES_OK_PREFIX = ("HERO", "FIGHTER_", "CLAN_MEN_", "MASTER", "FATHER", "VASSAL", "TEEN")
DEFAULT_PHYSICS = dict(reaction_strength=1.0, mass=72.0, damping=0.32, freq=2.6, friction=5.5, head_gain=0.7, fall_threshold=0.45,
                       coat=dict(stiffness=60.0, damping=0.12, gravity=1.0, max_offset=0.08),
                       cloak=dict(stiffness=55.0, damping=0.10, gravity=1.0, max_deg=14.0),
                       hair=dict(stiffness=120.0, damping=0.16, gravity=0.5, max_offset=0.02))


def _path(kind, ident):
    d = CLIP_DIR if kind == "clip" else SEQ_DIR
    p = ident if ident.endswith(".json") else os.path.join(d, ident + ".json")
    return p


def load_clip(ident):
    with open(_path("clip", ident)) as fh:
        c = json.load(fh)
    phys = json.loads(json.dumps(DEFAULT_PHYSICS))
    for k, v in (c.get("physics") or {}).items():
        if isinstance(v, dict): phys.setdefault(k, {}).update(v)
        else: phys[k] = v
    c["physics"] = phys
    c.setdefault("fps", 30); c.setdefault("hits", []); c.setdefault("impact_frame", {"exposure": 0.0, "frames": 0})
    for m in c.get("moves", []):
        m.setdefault("easing", "io"); m.setdefault("blend_in", 0); m.setdefault("blend_out", 0); m.setdefault("params", {})
    for h in c["hits"]:
        h.setdefault("hitstop", 3); h.setdefault("decal", None); h.setdefault("fall", False)
    return c


def load_sequence(ident):
    """A sequence JSON ({"id", "clips": [...]}) or a single clip id (a sequence of one). Adds global offsets + timemap."""
    if os.path.exists(_path("seq", ident)):
        with open(_path("seq", ident)) as fh:
            seq = json.load(fh)
        clips = [load_clip(c) for c in seq["clips"]]
    else:
        clips = [load_clip(ident)]
        seq = dict(id=ident, clips=[ident], render={})
    seq["clip_data"] = clips
    seq.setdefault("render", {})
    off = 0; hits = []
    for c in clips:
        c["_story0"] = off
        for h in c["hits"]:
            hits.append((off + int(h["frame"]), int(h["hitstop"])))
        off += int(c["story_frames"])
    seq["story_frames"] = off
    seq["fps"] = clips[0]["fps"]
    seq["timemap"] = TimeMap(off, hits)
    o = 1
    for c in clips:           # each clip's global output frame range [f0, f1]
        f0 = seq["timemap"].out_of(c["_story0"]); f1 = seq["timemap"].out_last(c["_story0"] + c["story_frames"] - 1)
        c["_out"] = (f0, f1)
    return seq


class TimeMap:
    """story frame (int, 0-based, global) <-> output frame (1-based). Hit frames repeat `hitstop` extra times."""
    def __init__(self, story_frames, hits):
        self.hold = {}
        for s, n in hits: self.hold[s] = self.hold.get(s, 0) + n
        self.map = []                                  # output index -> story frame
        for s in range(story_frames):
            self.map += [s] * (1 + self.hold.get(s, 0))
        self.n_out = len(self.map)
    def story(self, f_out):
        return self.map[max(0, min(self.n_out - 1, f_out - 1))]
    def out_of(self, s):
        return self.map.index(s) + 1 if s in self.map else self.n_out
    def out_last(self, s):
        return len(self.map) - self.map[::-1].index(s) if s in self.map else self.n_out
    def frozen(self, f_out):
        """True on the held copies of a hit frame (the freeze, not the contact frame itself)."""
        return f_out > 1 and self.story(f_out) == self.story(f_out - 1)
    def frames(self):
        return list(range(1, self.n_out + 1))


def _num(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
def _vec(x, n): return isinstance(x, (list, tuple)) and len(x) == n and all(_num(v) for v in x)


def validate_clip(c):
    """-> list of error strings (empty = valid)."""
    E = []
    cid = c.get("id", "?")
    def err(msg): E.append(f"{cid}: {msg}")
    for k in ("id", "fps", "duration", "story_frames", "actors", "moves", "hits", "camera", "physics"):
        if k not in c: err(f"missing key '{k}'")
    if E: return E
    if c["fps"] not in (24, 25, 30, 60): err(f"fps {c['fps']} not supported")
    sf = c["story_frames"]
    if not isinstance(sf, int) or sf <= 0: err("story_frames must be a positive int")
    hs = sum(int(h.get("hitstop", 0)) for h in c["hits"])
    if c["duration"] != sf + hs: err(f"duration {c['duration']} != story_frames {sf} + hit-stop {hs}")
    actors = c["actors"]
    if not actors: err("no actors")
    for name, a in actors.items():
        if not str(a.get("style", "")).startswith(STYLES_OK_PREFIX): err(f"actor {name}: unknown style {a.get('style')}")
        st = a.get("start", {})
        if not all(_num(st.get(k)) for k in ("x", "y", "facing")): err(f"actor {name}: start needs x, y, facing")
    hit_ids = {h.get("id") for h in c["hits"]}
    for i, m in enumerate(c["moves"]):
        tag = f"move {i} ({m.get('actor')}:{m.get('move')})"
        if m.get("actor") not in actors: err(f"{tag}: unknown actor")
        spec = MOVE_SPECS.get(m.get("move"))
        if spec is None: err(f"{tag}: unknown move"); continue
        s, e = m.get("start"), m.get("end")
        if not (_num(s) and _num(e) and 0 <= s < e <= sf): err(f"{tag}: start/end {s}/{e} outside 0..{sf} or empty")
        if m.get("easing", "io") not in EASINGS: err(f"{tag}: easing {m.get('easing')} not in {EASINGS}")
        for k in ("blend_in", "blend_out"):
            v = m.get(k, 0)
            if not (_num(v) and 0 <= v <= 30): err(f"{tag}: {k} {v} must be 0..30 frames")
        for k, v in m.get("params", {}).items():
            t = spec["params"].get(k)
            if t is None: err(f"{tag}: unknown param '{k}'")
            elif t is float and not _num(v): err(f"{tag}: param {k} must be a number")
            elif t is not float and not isinstance(v, t): err(f"{tag}: param {k} must be {t.__name__}")
        if spec["kind"] == "attack" and m["move"] in ("gyaku_zuki", "mawashi_geri_low"):
            hid = m.get("params", {}).get("hit")
            if hid not in hit_ids: err(f"{tag}: attack needs params.hit naming a hit event")
            else:
                h = next(h for h in c["hits"] if h.get("id") == hid)
                if abs(h["frame"] - e) > 1e-6: err(f"{tag}: attack must end on its hit frame ({h['frame']}), ends {e}")
                if h.get("attacker") != m["actor"]: err(f"{tag}: hit {hid} attacker is {h.get('attacker')}")
    by_actor = {}
    for m in c["moves"]: by_actor.setdefault(m.get("actor"), []).append(m)
    for a, ms in by_actor.items():
        ms = sorted(ms, key=lambda m: m.get("start", 0))
        if ms and ms[0].get("start", 0) > 0 and MOVE_SPECS.get(ms[0].get("move"), {}).get("kind") != "idle":
            pass   # the solver holds the carried-in pose until the first move
    for h in c["hits"]:
        tag = f"hit {h.get('id')}"
        if not isinstance(h.get("frame"), int) or not 0 <= h["frame"] < sf: err(f"{tag}: frame must be an int in 0..{sf - 1}")
        if h.get("attacker") not in actors or h.get("target") not in actors: err(f"{tag}: attacker/target must be actors")
        if h.get("attacker") == h.get("target"): err(f"{tag}: attacker == target")
        if h.get("part") not in BODY_PARTS: err(f"{tag}: part {h.get('part')} not in {BODY_PARTS}")
        if h.get("effector") not in EFFECTORS: err(f"{tag}: effector {h.get('effector')} not in {EFFECTORS}")
        if not _vec(h.get("force"), 3): err(f"{tag}: force must be [forward, left, up] (attacker frame)")
        if not (isinstance(h.get("hitstop"), int) and 0 <= h["hitstop"] <= 8): err(f"{tag}: hitstop must be 0..8 frames")
    cam = c["camera"]; cuts = cam.get("cuts", [])
    if not cuts: err("camera needs at least one cut")
    last = -1
    for k, cu in enumerate(cuts):
        if not (_num(cu.get("frame")) and cu["frame"] > last): err(f"cut {k}: frames must increase")
        last = cu.get("frame", last)
        if not cu.get("keys"): err(f"cut {k}: no keys")
        for kk in cu.get("keys", []):
            if not _vec(kk.get("pos"), 3): err(f"cut {k}: key pos must be [x,y,z]")
            if not (_vec(kk.get("look"), 3) or kk.get("look_actor") in actors or (isinstance(kk.get("look_mid"), list) and all(n in actors for n in kk["look_mid"]))): err(f"cut {k}: key needs look [x,y,z] or look_actor")
            if not (_num(kk.get("lens", 35)) and 10 <= kk.get("lens", 35) <= 200): err(f"cut {k}: lens out of range")
            if "roll" in kk and kk["roll"] != 0: err(f"cut {k}: roll must be 0 (steady, level camera)")
        if cuts and cuts[0].get("frame") != 0: err("first cut must start at frame 0")
    p = c["physics"]
    for k in ("reaction_strength", "mass", "damping", "freq", "friction"):
        if not _num(p.get(k)) or p[k] < 0: err(f"physics.{k} must be a non-negative number")
    if not 0 < p.get("damping", 0.3) < 2: err("physics.damping (zeta) must be in (0, 2)")
    for chain in ("coat", "cloak", "hair"):
        q = p.get(chain, {})
        for k in ("stiffness", "damping"):
            if not _num(q.get(k)) or q[k] < 0: err(f"physics.{chain}.{k} must be >= 0")
    return E


def validate_sequence(seq):
    E = []
    for c in seq["clip_data"]: E += validate_clip(c)
    names = None
    for c in seq["clip_data"]:
        n = {k: v["style"] for k, v in c["actors"].items()}
        if names is None: names = n
        elif n != names: E.append(f"{seq['id']}: clip {c['id']} actors/styles differ from the first clip (consistency)")
    ids = [h["id"] for c in seq["clip_data"] for h in c["hits"]]
    if len(ids) != len(set(ids)): E.append(f"{seq['id']}: hit ids must be unique across the sequence")
    return E


if __name__ == "__main__":
    import sys
    bad = 0
    for ident in (sys.argv[1:] or [os.path.splitext(n)[0] for n in sorted(os.listdir(SEQ_DIR))]):
        seq = load_sequence(ident); e = validate_sequence(seq)
        print(ident, "OK" if not e else "INVALID", f"story {seq['story_frames']} out {seq['timemap'].n_out} frames")
        for x in e: print("  ", x)
        bad += bool(e)
    sys.exit(1 if bad else 0)
