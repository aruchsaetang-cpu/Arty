"""Render ONE combat sequence (or one clip) on its own - never the whole film.

    python shorts/kuro_oni/combat/render_seq.py <seq_or_clip_id> [--frames a-b] [--scale 50] [--samples 12] [--twos]
           [--stills 12,40] [--check] [--check-only] [--no-mp4] [--mp4-only] [--keeplast]

Frames -> shorts/kuro_oni/frames_seq/<id>/f####.png (existing frames are skipped, so a killed run resumes; the newest
frame is re-rendered in case it was half written). --twos renders odd frames + every contact frame; hit-stop held
frames are never rendered (they repeat the contact image). The mp4 (silent) is assembled from whatever exists:
shorts/kuro_oni/out/<id>.mp4. --check builds, runs the Blender-side verification (checks.py) and writes
combat/out/<id>_checks.json. --stills renders single frames to frames_seq/<id>/stills/ (quick look). Runs under the
project Blender (/root/.venvs/bpy/bin/python); plain `python` re-launches itself there.
"""
import os, sys, json, time, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); KO = os.path.dirname(HERE)
BPY = "/root/.venvs/bpy/bin/python"
try:
    import bpy  # noqa
except ImportError:
    os.execv(BPY, [BPY, os.path.abspath(__file__)] + sys.argv[1:])
import argparse
ap = argparse.ArgumentParser(); ap.add_argument("seq"); ap.add_argument("--frames"); ap.add_argument("--scale", type=int)
ap.add_argument("--samples", type=int); ap.add_argument("--twos", action="store_true"); ap.add_argument("--ones", action="store_true")
ap.add_argument("--stills"); ap.add_argument("--check", action="store_true"); ap.add_argument("--check-only", action="store_true"); ap.add_argument("--no-mp4", action="store_true")
ap.add_argument("--mp4-only", action="store_true"); ap.add_argument("--keeplast", action="store_true"); ap.add_argument("--blur-steps", type=int, default=1)
A = ap.parse_args()
sys.path.insert(0, HERE)
import schema as S

FR = os.path.join(KO, "frames_seq", A.seq); OUTV = os.path.join(KO, "out")


def frame_plan(tm, hits_out, twos):
    """frames to render: all, or odd + contacts (on twos); never the held hit-stop copies."""
    keep = []
    for f in tm.frames():
        if tm.frozen(f): continue
        if not twos or f % 2 == 1 or f in hits_out: keep.append(f)
    return keep


def assemble(seq_id, n_out, fps, frozen):
    if not os.path.isdir(FR): print("no frames"); return None
    have = sorted(int(n[1:5]) for n in os.listdir(FR) if n.startswith("f") and n.endswith(".png"))
    if not have: print("no frames"); return None
    lst = os.path.join(FR, "concat.txt"); last = None
    with open(lst, "w") as fh:
        for f in range(1, n_out + 1):
            cand = [h for h in have if h <= f]
            src = cand[-1] if cand else have[0]
            fh.write(f"file 'f{src:04d}.png'\nduration {1.0 / fps:.6f}\n"); last = src
        fh.write(f"file 'f{last:04d}.png'\n")
    os.makedirs(OUTV, exist_ok=True); out = os.path.join(OUTV, f"{seq_id}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={fps},format=yuv420p", "-an",
           "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True); print("MP4", out, os.path.getsize(out), "bytes", flush=True); return out


seq = S.load_sequence(A.seq); tm = seq["timemap"]; R_ = seq.get("render", {})
scale = A.scale or R_.get("scale", 50); samples = A.samples or R_.get("samples", 12); twos = (A.twos or R_.get("twos", False)) and not A.ones
if A.mp4_only:
    assemble(A.seq, tm.n_out, seq["fps"], None); sys.exit(0)

import build
W = build.build(A.seq)
import bpy
import city as C
scn = bpy.context.scene
if A.check or A.check_only:
    import checks
    rep = checks.run(W); print(checks.summary(rep), flush=True)
    if A.check_only: sys.exit(0 if rep["pass"] else 1)
C.render_settings(scale, samples)
scn.view_settings.look = "None"; base_exp = scn.view_settings.exposure
scn.render.image_settings.file_format = "PNG"; scn.render.fps = seq["fps"]
scn.render.motion_blur_shutter = 0.35
try:
    scn.cycles.motion_blur_position = "CENTER"
except Exception:
    pass
for n, R in W.actors.items():                         # selective motion blur: only the fighters (deforming meshes) blur
    for o in R.g.children_recursive:
        if o.type in ("MESH", "CURVE") and hasattr(o, "cycles"):
            try: o.cycles.use_motion_blur = True; o.cycles.use_deform_motion = True; o.cycles.motion_steps = A.blur_steps
            except Exception: pass
for o in scn.objects:
    if not any(o in R.g.children_recursive or o is R.g for R in W.actors.values()) and hasattr(o, "cycles"):
        try: o.cycles.use_motion_blur = False
        except Exception: pass
hits_out = {tm.out_of(h["_s"]): h for h in W.hits}
impact = {}
for c in seq["clip_data"]:
    ip = c.get("impact_frame", {})
    for h in c["hits"]:
        f0 = tm.out_of(c["_story0"] + h["frame"])
        for k in range(int(ip.get("frames", 0))): impact[f0 + k] = float(ip.get("exposure", 0.0))


def setup_frame(f):
    scn.frame_set(f)
    scn.render.use_motion_blur = bool(W.cam_info["motion_blur"].get(f, False)) and not tm.frozen(f) and f not in hits_out
    scn.view_settings.exposure = base_exp + impact.get(f, 0.0)      # impact-frame hook: subtle exposure lift on contact


if A.stills:
    sd = os.path.join(FR, "stills"); os.makedirs(sd, exist_ok=True)
    for s_ in A.stills.split(","):
        f = int(s_); setup_frame(f); scn.render.filepath = os.path.join(sd, f"s{f:04d}.png"); t = time.time()
        bpy.ops.render.render(write_still=True); print(f"STILL {f} {time.time() - t:.1f}s rss {build.rss():.2f} GB", flush=True)
    sys.exit(0)

os.makedirs(FR, exist_ok=True)
plan = frame_plan(tm, hits_out, twos)
if A.frames:
    a, b = (int(x) for x in A.frames.split("-")); plan = [f for f in plan if a <= f <= b]
done = sorted(int(n[1:5]) for n in os.listdir(FR) if n.startswith("f") and n.endswith(".png"))
if done and not A.keeplast:
    os.remove(os.path.join(FR, f"f{done[-1]:04d}.png")); print("re-render newest frame", done[-1], flush=True)
logp = os.path.join(FR, "render_log.json"); log = json.load(open(logp)) if os.path.exists(logp) else {}
T0 = time.time(); n = 0
for f in plan:
    p = os.path.join(FR, f"f{f:04d}.png")
    if os.path.exists(p): continue
    setup_frame(f); scn.render.filepath = p; t = time.time(); bpy.ops.render.render(write_still=True); dt = time.time() - t; n += 1
    log[str(f)] = dict(s=round(dt, 1), rss_gb=round(build.rss(), 2), blur=scn.render.use_motion_blur, scale=scale, samples=samples)
    print(f"FRAME {f} {dt:.1f}s peak rss {build.rss():.2f} GB", flush=True)
    with open(logp, "w") as fh: json.dump(log, fh, indent=0)
print(f"RENDERED {n} frames in {time.time() - T0:.0f}s ({len(plan)} planned, twos={twos})", flush=True)
if not A.no_mp4: assemble(A.seq, tm.n_out, seq["fps"], None)
