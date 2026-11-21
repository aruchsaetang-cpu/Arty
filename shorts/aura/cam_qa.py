"""Camera QA: compare two per-frame camera dumps (film.py CAMDUMP) shot by shot.
    python3 shorts/aura/cam_qa.py before.json after.json
Per shot: max acceleration, max jerk, max view rotation rate and rotation acceleration, and jitter (the 3-15 Hz part
of the camera path: residual after a 5-frame Gaussian low-pass, RMS in mm). Cuts are excluded (only frames inside a
shot are differenced). Also checks that frame 1 is identical."""
import json, sys, math, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, "beats.json")))
A0, A1 = [np.array(json.load(open(p))) for p in sys.argv[1:3]]
FPS = 30.0

def lowpass(x, s=5.0):
    r = int(3 * s); k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    xp = np.concatenate([2 * x[:1] - x[r:0:-1], x, 2 * x[-1:] - x[-2:-r - 2:-1]])
    return np.stack([np.convolve(xp[:, i], k, "valid") for i in range(x.shape[1])], 1)

def stats(D, f0, f1):
    d = D[f0 - 1:f1]; cam, look = d[:, 1:4], d[:, 4:7]
    if len(d) < 8: return None
    v = np.gradient(cam, axis=0) * FPS; a = np.gradient(v, axis=0) * FPS; j = np.gradient(a, axis=0) * FPS
    dirs = look - cam; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    ang = np.degrees(np.arccos(np.clip((dirs[1:] * dirs[:-1]).sum(1), -1, 1))) * FPS
    angacc = np.abs(np.diff(ang)) * FPS
    jit = np.sqrt(((cam - lowpass(cam)) ** 2).sum(1).mean()) * 1000
    jit_look = np.sqrt(((look - lowpass(look)) ** 2).sum(1).mean()) * 1000
    return dict(acc=np.linalg.norm(a, axis=1)[2:-2].max(), jerk=np.linalg.norm(j, axis=1)[3:-3].max(),
                rot=ang[1:-1].max(), rotacc=angacc[2:-2].max(), jit=jit, jit_look=jit_look)

print(f"frame 1 identical: {np.allclose(A0[0], A1[0], atol=1e-6)}  (before {A0[0][1:4].round(4)} after {A1[0][1:4].round(4)})")
print(f"{'shot':13s} {'max acc m/s2':>14s} {'max jerk m/s3':>15s} {'max rot deg/s':>15s} {'rot acc deg/s2':>16s} {'jitter mm':>11s} {'aim jitter mm':>14s}")
for s in B["shots"]:
    a, b = stats(A0, s["f0"], s["f1"]), stats(A1, s["f0"], s["f1"])
    if not a: continue
    same = np.allclose(A0[s["f0"] - 1:s["f1"]], A1[s["f0"] - 1:s["f1"]], atol=1e-5)
    if same:
        print(f"{s['id']:13s}   unchanged"); continue
    fmt = lambda k, p=1: f"{a[k]:.{p}f}->{b[k]:.{p}f}"
    print(f"{s['id']:13s} {fmt('acc'):>14s} {fmt('jerk', 0):>15s} {fmt('rot'):>15s} {fmt('rotacc', 0):>16s} {fmt('jit'):>11s} {fmt('jit_look'):>14s}")
