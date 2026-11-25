"""Kuro Oni ep 1, REAL SCENE 1 v2 (hook, 0-3 s): rendered frames (odd frames + every frame of the punch) -> out/scene1_v2.mp4.
Post, kept calm outside the hit (no shake, no flicker): a red fear grade on the over-the-shoulder shot, faint radial lines
on the push-in, then at the hit: contact frame -> ONE white flash (2 frames) -> ink impact frame (2 frames) -> held contact
with a 3-frame shake (hit-stop), a small BAM, ink splatter from the face. Narrator subtitle. Synthesised sound: fire
crackle + low wind + distant roar (no rain), a fear drone, the haymaker whoosh, 0.4 s of silence, then sub drop + body thud
+ crack on the hit, and the thud of the body hitting the road.
    python3 shorts/kuro_oni/scene1_compose.py"""
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from compose30 import silhouette, W, H, FPS
FR = os.path.join(HERE, "frames_s1v2"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
DUR = 3.0; N = int(DUR * FPS)
F_HIT = 64                                   # contact frame (t = 2.10 s); the 3D hit-stop holds until frame 68
HIT = (F_HIT - 1) / FPS
FEAR = (0.8, 1.35)                           # over-the-shoulder shot: blood-red grade
FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
FO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
SUBS = [(0.15, 1.6, "He defeated an army alone."), (1.6, 3.0, "But he never felt fulfilled.")]
CX, CY = W // 2, H // 2                      # the punch shot is framed on the fist/face contact

def src(f):
    for k in range(f, 0, -1):
        p = os.path.join(FR, f"f{k:04d}.png")
        if os.path.exists(p): return p
    return None
def load(f):
    s = src(f); return Image.open(s).convert("RGB").resize((W, H), Image.LANCZOS) if s else Image.new("RGB", (W, H), (0, 0, 0))
def fear(img, k=0.75):
    a = np.asarray(img, np.float32); l = a.mean(-1, keepdims=True) / 255.0
    red = np.concatenate([40 + 215 * l, 6 + 40 * l, 8 + 36 * l], -1)
    return Image.fromarray(np.clip(a * (1 - k) + red * k, 0, 255).astype(np.uint8))
def radial(img, t, alpha, n=60, r0=(170, 300)):
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(int(t * 30) + 7)
    for _ in range(n):
        a = r.uniform(0, math.tau); a0 = r.uniform(*r0); a1 = a0 + r.uniform(220, 600)
        d.line([(CX + a0 * math.cos(a), CY + a0 * math.sin(a)), (CX + a1 * math.cos(a), CY + a1 * math.sin(a))],
               fill=(255, 255, 255, alpha) if r.random() < 0.6 else (0, 0, 0, alpha), width=r.choice((1, 2, 2, 3)))
def splatter(img, t, k):
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(11)
    for _ in range(70):
        a = r.uniform(-1.2, 1.0); rr = (abs(r.gauss(0, 60)) + 20) * (0.5 + 1.8 * k); sz = r.choice((2, 2, 3, 4, 6))
        x, y = CX + 30 + rr * math.cos(a), CY + rr * math.sin(a)
        d.ellipse([x - sz, y - sz, x + sz, y + sz], fill=(110, 6, 10, int(230 * (1 - 0.6 * k))))
def bam(img, k):
    lay = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W // 2, 100), "BAM", font=FO, fill=(255, 255, 255, int(255 * (1 - 0.7 * k))), stroke_width=6, stroke_fill=(0, 0, 0, 255), anchor="mm")
    lay = lay.rotate(-8, resample=Image.BICUBIC); sz = 1.0 + 0.25 * (1 - k); lay = lay.resize((int(W * sz), int(200 * sz)))
    img.paste(lay, ((W - lay.width) // 2, 120), lay)
def vignette(img, k=0.5):
    yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    m = np.clip(1.15 - r * 0.45 * k, 0.0, 1.0)[..., None]; return Image.fromarray((np.asarray(img, np.float32) * m).astype(np.uint8))
def subtitle(img, t):
    for a, b, line in SUBS:
        if a <= t < b:
            d = ImageDraw.Draw(img); y = H - 120
            d.text((W // 2, y), line, font=FB, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
def shift(img, dx, dy):
    out = Image.new("RGB", (W, H), (0, 0, 0)); out.paste(img, (dx, dy)); return out

def frame(f):
    t = (f - 1) / FPS
    if f in (F_HIT + 1, F_HIT + 2): img = Image.new("RGB", (W, H), (255, 255, 255))       # the one white flash, 2 frames
    elif f in (F_HIT + 3, F_HIT + 4):                                                     # ink impact frame
        img = silhouette(load(F_HIT), t); splatter(img, t, 0.2)
    elif F_HIT + 5 <= f <= F_HIT + 7:                                                     # hit-stop: held contact + short shake
        img = load(F_HIT); img = shift(img, (6, -5, 3)[f - F_HIT - 5], (-4, 5, -2)[f - F_HIT - 5])
        radial(img, t, 150, 90, (120, 260)); splatter(img, t, (f - F_HIT - 5) / 6)
    else:
        img = load(f)
        if FEAR[0] <= t < FEAR[1]: img = fear(img)
        if 1.95 <= t < HIT + 0.01: radial(img, t, 70, 40)                                # faint lines on the fast push-in
        if F_HIT + 8 <= f < F_HIT + 14: radial(img, t, int(90 * (1 - (f - F_HIT - 8) / 6)), 40); splatter(img, t, 0.5 + (f - F_HIT - 8) / 12)
    if F_HIT + 3 <= f < F_HIT + 13: bam(img, (f - F_HIT - 3) / 10)
    if f not in (F_HIT + 1, F_HIT + 2): img = vignette(img)
    subtitle(img, t)
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
    env = np.interp(tm, [0, 1.0, 1.65, 1.72, HIT, HIT + 0.05, 2.5, 3.0], [0.9, 0.9, 0.6, 0.0, 0.0, 0.2, 0.75, 0.9])  # silence 1.72-2.1
    roar = lp(rng.standard_normal(n), 140) * 0.9 * (1 + 0.3 * np.sin(tm * 2.1))                                    # distant fire roar
    wind = bp(rng.standard_normal(n), 250, 900) * 0.035 * (1 + 0.5 * np.sin(tm * 1.3 + 1))                         # low wind
    cr = np.zeros(n)
    for at in rng.uniform(0, DUR, int(60 * DUR)): cr[int(at * SR)] += rng.uniform(0.3, 1.0) * rng.choice((-1, 1))  # crackle
    cr = bp(cr, 700, 7000) * 3.5
    pops = np.zeros(n)
    for at in rng.uniform(0, DUR, 7): i = int(at * SR); k = tt(0.04); pops[i:i + len(k)] += (rng.standard_normal(len(k)) * np.exp(-k * 90))[: n - i]
    bed = roar + wind + cr + bp(pops, 300, 4000) * 0.6
    L += bed * env; R += np.roll(bed, 1300) * env
    t_ = tt(0.55); add(np.sin(2 * np.pi * 44 * t_) * np.minimum(1, t_ / 0.35) * np.minimum(1, (0.55 - t_) / 0.04) * 0.3, 0.8)   # fear drone
    t_ = tt(0.2); w = bp(rng.standard_normal(len(t_)), 500, 2500) * np.sin(np.pi * t_ / 0.2) ** 2 * 0.35; add(w, 1.82, 1.0, -0.4)   # haymaker whoosh
    t_ = tt(0.1); add(bp(rng.standard_normal(len(t_)), 900, 4000) * np.sin(np.pi * t_ / 0.1) ** 2 * 0.3, HIT - 0.09, 1.0, 0.3)       # punch whoosh
    # the hit: sub drop, low body thud, bright crack, a wet crunch
    t_ = tt(1.0); f = 32 + 130 * np.exp(-t_ * 18); add(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t_ * 3.5), HIT, 1.2)
    t_ = tt(0.3); add(np.sin(2 * np.pi * 78 * t_) * np.exp(-t_ * 16) + lp(rng.standard_normal(len(t_)), 600) * np.exp(-t_ * 25) * 0.8, HIT, 1.0)
    t_ = tt(0.12); add(bp(rng.standard_normal(len(t_)), 2500, 10000) * np.exp(-t_ * 45) * 1.2, HIT, 0.7)
    t_ = tt(0.15); add(bp(rng.standard_normal(len(t_)), 400, 2000) * np.exp(-t_ * 30) * 0.8, HIT + 0.01, 0.6)
    # the body slams the road (2.73 s) and a scrape
    t_ = tt(0.4); add(np.sin(2 * np.pi * 60 * t_) * np.exp(-t_ * 12) * 0.8 + lp(rng.standard_normal(len(t_)), 400) * np.exp(-t_ * 18) * 0.6, 2.73, 0.9)
    t_ = tt(0.25); add(bp(rng.standard_normal(len(t_)), 800, 3000) * np.exp(-t_ * 10) * 0.15, 2.76, 0.8)
    m = np.stack([L, R], 1); m = np.tanh(m * 1.1); m /= max(1e-9, np.abs(m).max()) / 0.9
    wavfile.write(os.path.join(OUT, "scene1_v2.wav"), SR, (m * 32767).astype(np.int16))

def main():
    sound()
    out = os.path.join(OUT, "scene1_v2.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", os.path.join(OUT, "scene1_v2.wav"), "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(1, N + 1): p.stdin.write(frame(f).tobytes())
    p.stdin.close(); p.wait(); print("done", out)
if __name__ == "__main__": main()
