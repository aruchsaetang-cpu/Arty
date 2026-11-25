"""Kuro Oni ep 1, REAL SCENE 1 (hook, 0-3 s): rendered frames (every 2nd, held for 2) -> out/scene1.mp4 at 540x960.
Post: red fear grade on the enemy-POV shots, white flash + ink impact frame at the punch, speed lines / ink burst / cracks / shock ring /
"BAM" (all reused from compose30.py), the narrator subtitle, and a synthesised sound track (rain bed, fire crackle, 0.4 s of silence,
one sub drop + bright thud at 2.2 s).
    python3 shorts/kuro_oni/scene1_compose.py [scale 1.0 = 540x960]"""
import os, sys
import numpy as np
from PIL import Image
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import compose30 as C30
from compose30 import silhouette, fear, dense_lines, burst, cracks, onomatopoeia, caption, VOICE, W, H, FPS
import subprocess
FR = os.path.join(HERE, "frames_s1"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
DUR = 3.0; N = int(DUR * FPS)
HIT = 2.2                       # the punch lands; frame index of the blast = 68 (t = 2.233)
FEAR = [(1.0, 1.7)]             # enemy-POV shots: graded blood red
C30.VOICE[:] = VOICE[:1] + [(3.0, "NARRATOR", "")]      # only the hook line in this clip

def src(f):
    for k in (f, f - 1, f + 1, f - 2, f + 2):
        p = os.path.join(FR, f"f{k:04d}.png")
        if k >= 1 and os.path.exists(p): return p
    return None
def frame(f):
    t = (f - 1) / FPS; s = src(f)
    img = Image.open(s).convert("RGB").resize((W, H), Image.LANCZOS) if s else Image.new("RGB", (W, H), (0, 0, 0))
    if any(a <= t < b for a, b in FEAR): img = fear(img)
    if HIT + 0.01 <= t < HIT + 0.05: return Image.new("RGB", (W, H), (255, 255, 255))              # the white flash frame
    if HIT + 0.05 <= t < HIT + 0.12: img = silhouette(img, t)                                       # two ink impact frames
    if HIT - 0.12 <= t < HIT + 0.45: dense_lines(img, t, "radial" if t < HIT + 0.2 else "parallel")
    if HIT <= t < HIT + 0.3: burst(img, t, (t - HIT) / 0.3)
    if HIT <= t < HIT + 0.5: cracks(img, t)
    onomatopoeia(img, t)
    caption(img, t)
    return img

# ------------------------------------------------------------------ sound
SR = 44100
def sound():
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n); rng = np.random.default_rng(5)
    def add(x, at, g=1.0, pan=0.0):
        i = int(at * SR); x = x[: max(0, n - i)]; L[i:i + len(x)] += x * g * (1 - pan); R[i:i + len(x)] += x * g * (1 + pan)
    def tt(d): return np.arange(int(d * SR)) / SR
    def lp(x, fc): return sosfilt(butter(2, fc, "lowpass", fs=SR, output="sos"), x)
    def bp(x, a, b): return sosfilt(butter(2, [a, b], "bandpass", fs=SR, output="sos"), x)
    tm = np.arange(n) / SR
    env = np.interp(tm, [0, 1.0, 1.75, 1.8, 2.2, 2.25, 2.6, 3.0], [0.8, 0.8, 0.55, 0.0, 0.0, 0.35, 0.8, 0.9])       # silence 1.8-2.2
    rain = bp(rng.standard_normal(n), 2500, 9000) * 0.07 + bp(rng.standard_normal(n), 400, 1500) * 0.03
    L += rain * env; R += np.roll(rain, 900) * env
    # fire crackle: random clicks, lows, on both sides (louder at the start, gone in the silence)
    cr = np.zeros(n); k = int(14 * DUR * 3)
    for at in rng.uniform(0, DUR, k): cr[int(at * SR)] += rng.uniform(0.3, 1.0) * rng.choice((-1, 1))
    cr = bp(cr, 800, 6000) * 4 + lp(rng.standard_normal(n), 120) * 0.05
    cenv = np.interp(tm, [0, 1.0, 1.75, 1.8, 2.2, 2.6, 3.0], [0.7, 0.7, 0.4, 0.0, 0.0, 0.5, 0.6]); L += cr * cenv * 1.1; R += np.roll(cr, 1700) * cenv * 0.9
    # fear: a low drone rises under the enemy POV shots (1.0-1.8), then it is cut with everything else
    t_ = tt(0.8); d = np.sin(2 * np.pi * 46 * t_) * np.minimum(1, t_ / 0.6) * np.minimum(1, (0.8 - t_) / 0.03) * 0.35; add(d, 1.0)
    for at in (1.02, 1.33, 1.62):
        t_ = tt(0.18); add(np.sin(2 * np.pi * 52 * t_) * np.exp(-t_ * 22), at, 0.9)
    # the drop: sub sweep + noise crack, then the bright thud (the punch), then the blast rumble and a whoosh of bodies
    t_ = tt(1.0); f = 34 + 120 * np.exp(-t_ * 20); sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t_ * 4.0)
    add(sub, HIT, 1.1); add(lp(rng.standard_normal(len(t_)), 2400) * np.exp(-t_ * 30), HIT, 0.9)
    t_ = tt(0.35); add(bp(rng.standard_normal(len(t_)), 2800, 11000) * np.exp(-t_ * 26) * 1.6 + np.sin(2 * np.pi * 180 * t_) * np.exp(-t_ * 30), HIT, 0.8)   # bright thud
    t_ = tt(0.7); add(bp(rng.standard_normal(len(t_)), 400, 3500) * np.sin(np.pi * t_ / 0.7) ** 2 * 0.5, HIT + 0.1, 0.8)     # bodies whooshing out
    t_ = tt(1.2); add(lp(rng.standard_normal(len(t_)), 200) * np.exp(-t_ * 3) * 0.6, HIT + 0.05, 0.9)
    m = np.stack([L, R], 1); m = np.tanh(m * 1.2); m /= max(1e-9, np.abs(m).max()) / 0.9
    wavfile.write(os.path.join(OUT, "scene1.wav"), SR, (m * 32767).astype(np.int16))

def main():
    sound()
    out = os.path.join(OUT, "scene1.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "scene1.wav"),
                          "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), "-movflags", "+faststart", out],
                         stdin=subprocess.PIPE)
    for f in range(1, N + 1): p.stdin.write(frame(f).tobytes())
    p.stdin.close(); p.wait(); print("done", out)
if __name__ == "__main__": main()
