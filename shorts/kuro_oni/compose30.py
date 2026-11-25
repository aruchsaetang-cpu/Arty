"""Kuro Oni ep 1, 30 s prototype: rendered frames (every 2nd) -> 540x960 video with voice subtitles, ink silhouettes, fear tint,
speed lines, first-person vignette, title, and a synthesised sound track (no voice actor yet: the voice lines are subtitles).
python3 shorts/kuro_oni/compose30.py"""
import math, os, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__)); FR = os.path.join(HERE, "frames30"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 540, 960, 30, 30.0; N = int(DUR * FPS)
FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 27)
FX = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
FS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
BIG = [2.2, 6.2, 12.0, 19.0, 23.2]; SMALL = [18.3, 18.7, 19.5, 20.0, 14.6]; HITS = sorted(BIG + SMALL)
SILH = [(t, t + 0.25) for t in BIG]
FEAR = [(1.0, 1.7), (18.0, 18.3), (19.6, 20.0)]
VOICE = [  # (start, speaker, line)
    (0.0, "NARRATOR", "He defeated an army alone. But he never felt fulfilled."),
    (3.0, "NARRATOR", "He was born with the Demonic Eye, the mark of a clan leader."),
    (5.0, "NARRATOR", "And black bone: bones as hard as steel, that can stop even a katana."),
    (8.0, "NARRATOR", "But his father never gave him a name. They only called him Young Master."),
    (11.0, "MOTHER", "Young Master, a future clan leader will not play with those kids."),
    (13.0, "MASTER", "I can't believe you've mastered it already, Young Master."),
    (15.0, "NARRATOR", "He fought for one thing: his father's voice saying his name."),
    (18.0, "NARRATOR", "But his father died in the war, and the name never came."),
    (20.0, "DEFEATED ENEMIES", "Kuro Oni..."),
    (21.0, "NARRATOR", "Then he came home, and he slept."),
    (23.0, "MOTHER", "Young Master."),
    (24.0, "NARRATOR", "The smile he waited for his whole life."),
    (25.0, "YOUNG MASTER", "...Damn it."),
    (26.0, "NARRATOR", "He died without ever hearing his name. And woke in a world of magic."),
]
COL = {"NARRATOR": (255, 220, 120), "MOTHER": (255, 150, 180), "MASTER": (170, 220, 255), "DEFEATED ENEMIES": (255, 120, 120), "YOUNG MASTER": (255, 255, 255)}
def src(f):
    for k in (f, f - 1, f + 1, f - 2, f + 2):
        p = os.path.join(FR, f"f{k:04d}.png")
        if k >= 1 and os.path.exists(p): return p
    return None
def silhouette(img, t):
    a = np.asarray(img.convert("L"), np.float32); m = a < 78
    out = np.where(m, 0, 255).astype(np.uint8); im = Image.fromarray(out).convert("RGB"); d = ImageDraw.Draw(im)
    r = random.Random(int(t * 100)); cx, cy = W // 2 + r.randint(-60, 60), H // 2 - 90
    for _ in range(170):
        ang = r.uniform(0, math.tau); rr = abs(r.gauss(0, 150)) + 40
        x, y = cx + rr * math.cos(ang), cy + rr * math.sin(ang); s = r.choice((2, 3, 3, 5, 8))
        d.ellipse([x - s, y - s, x + s, y + s], fill=(0, 0, 0))
    return im
def fear(img):
    a = np.asarray(img.convert("L"), np.float32) / 255.0; a = np.clip((a - 0.15) * 1.6, 0, 1)
    rgb = np.stack([60 + 175 * a, 8 + 22 * a, 10 + 22 * a], -1).astype(np.uint8); return Image.fromarray(rgb)
def vignette(img, k):
    yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    m = np.clip(1.25 - r * 0.85 * k, 0.0, 1.0)[..., None]; return Image.fromarray((np.asarray(img, np.float32) * m).astype(np.uint8))
def speed_lines(img, t):
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(int(t * 30)); cx, cy = W // 2, H // 2 - 60
    for _ in range(46):
        a = r.uniform(0, math.tau); r0 = r.uniform(230, 330); r1 = r0 + r.uniform(160, 420)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=(255, 255, 255, 210), width=r.choice((2, 2, 3, 5)))
ONO = {2.2: ("BAM", -10), 6.2: ("CLANG", 8), 12.0: ("SLAP", -6), 19.0: ("THUD", 12), 23.2: ("...", 0)}
FO = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
def onomatopoeia(img, t):
    for ht, (word, ang) in ONO.items():
        if ht <= t < ht + 0.4 and word != "...":
            k = (t - ht) / 0.4; sz = 1.0 + 0.5 * (1 - k)
            lay = Image.new("RGBA", (W, 220), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((W // 2, 110), word, font=FO, fill=(255, 255, 255, int(255 * (1 - k * 0.5))), stroke_width=7, stroke_fill=(0, 0, 0, 255), anchor="mm")
            lay = lay.rotate(ang, resample=Image.BICUBIC, expand=False); lay = lay.resize((int(W * sz), int(220 * sz)))
            img.paste(lay, ((W - lay.width) // 2, 150), lay)
        if ht <= t < ht + 0.35:      # white shockwave ring from the impact (the Lookism panels)
            k = (t - ht) / 0.35; r = 60 + 360 * k; d = ImageDraw.Draw(img, "RGBA"); cx, cy = W // 2, H // 2 - 60
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, int(230 * (1 - k))), width=int(10 * (1 - k)) + 2)
def caption(img, t):
    cur = None
    for i, (s, who, line) in enumerate(VOICE):
        end = VOICE[i + 1][0] if i + 1 < len(VOICE) else 29.0
        if s <= t < max(end, s + 1.0): cur = (who, line)
    if cur is None and t >= 29.0: return
    if cur is None: return
    who, line = cur
    bar = Image.new("RGBA", (W, 110), (0, 0, 0, 170)); img.paste(bar, (0, H - 110), bar); d = ImageDraw.Draw(img)
    d.text((14, H - 104), who.title() if who != "NARRATOR" else "Narrator", font=FS, fill=COL.get(who, (255, 255, 255)))
    words, ln, y = line.split(), "", H - 78
    for w_ in words:
        if d.textlength(ln + w_ + " ", font=FB) > W - 28: d.text((14, y), ln, font=FB, fill=(255, 255, 255)); ln, y = "", y + 32
        ln += w_ + " "
    d.text((14, y), ln, font=FB, fill=(255, 255, 255))
def frame(f):
    t = (f - 1) / FPS; s = src(f)
    img = Image.open(s).convert("RGB").resize((W, H), Image.LANCZOS) if s else Image.new("RGB", (W, H), (0, 0, 0))
    if any(a <= t < b for a, b in FEAR): img = fear(img)
    if t >= 26.0: img = vignette(img, 1.0)
    if any(a <= t < b for a, b in SILH): img = silhouette(img, t)
    for ht in BIG:
        if ht <= t < ht + 0.2: speed_lines(img, t)
    onomatopoeia(img, t); d = ImageDraw.Draw(img)
    if t >= 29.0:
        a = min(1, (t - 29.0) / 0.5); d.text((W // 2, 430), "KURO ONI", font=FX, fill=(int(245 * a),) * 3, stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
        if t >= 29.5: d.text((W // 2, 505), "TO BE CONTINUED", font=FB, fill=(210, 210, 215), anchor="mm")
    else: caption(img, t)
    d.text((W - 80, 12), f"{t:4.1f}s", font=FS, fill=(200, 200, 200))
    return img
# ------------------------------------------------------------------ sound (no voice actor yet)
SR = 44100
def sound():
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n); rng = np.random.default_rng(3)
    def add(x, at, g=1.0, pan=0.0):
        i = int(at * SR); x = x[: max(0, n - i)]; L[i:i + len(x)] += x * g * (1 - pan); R[i:i + len(x)] += x * g * (1 + pan)
    def tt(d): return np.arange(int(d * SR)) / SR
    def lp(x, fc): return sosfilt(butter(2, fc, "lowpass", fs=SR, output="sos"), x)
    def bp(x, a, b): return sosfilt(butter(2, [a, b], "bandpass", fs=SR, output="sos"), x)
    def thud(at, big):
        t_ = tt(1.2 if big else 0.35); f = 38 + 110 * np.exp(-t_ * 22)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t_ * (4.5 if big else 14)); x += lp(rng.standard_normal(len(t_)), 2400) * np.exp(-t_ * 38) * 0.9
        add(x, at, 1.0 if big else 0.5)
    def beat(at, g=1.0):
        t_ = tt(0.18); add(np.sin(2 * np.pi * 55 * t_) * np.exp(-t_ * 22), at, 0.9 * g); add(np.sin(2 * np.pi * 48 * t_) * np.exp(-t_ * 24), at + 0.24, 0.6 * g)
    rn = bp(rng.standard_normal(n), 2500, 9000) * 0.05; env = np.interp(np.arange(n) / SR, [0, 1, 4, 10, 17, 19, 21, 21.6, 25, 30], [0.7, 0.7, 0.0, 0.0, 0.5, 1.0, 1.0, 0.0, 0.0, 0.0])
    for a, b in ((19.6, 20.0), (25.2, 26.3)): env[int(a * SR):int(b * SR)] = 0
    L += rn * env; R += rn * env * 0.9
    for h_ in HITS: thud(h_, h_ in BIG)
    # the clang of black bone (metal ring), the slap (bright burst), the stab (scrape + hit)
    t_ = tt(1.4); add((np.sin(2 * np.pi * 1180 * t_) + 0.6 * np.sin(2 * np.pi * 2310 * t_)) * np.exp(-t_ * 3.0) * 0.4, 6.2)
    add(bp(rng.standard_normal(int(0.2 * SR)), 1500, 8000) * np.exp(-tt(0.2) * 25) * 1.2, 12.0)
    add(bp(rng.standard_normal(int(0.9 * SR)), 2500, 9000) * np.exp(-tt(0.9) * 4) * 0.4, 22.6)
    for at in (4.7, 25.6, 26.5): beat(at, 0.9)
    for at in (3.1, 4.0, 5.0, 8.0, 15.0): add(lp(rng.standard_normal(int(0.25 * SR)), 300) * np.exp(-tt(0.25) * 14), at, 0.5)
    for a, b, f0 in ((8.0, 11.0, 55), (21.0, 25.0, 55)):
        t_ = tt(b - a); add(np.sin(2 * np.pi * f0 * t_) * 0.3 * np.minimum(1, t_ / 1.0) * np.minimum(1, (b - a - t_) / 0.5), a)
    for k, f0 in enumerate((659, 784, 988, 1175)):
        t_ = tt(2.0); add(np.sin(2 * np.pi * f0 * t_) * np.exp(-t_ * 2.5) * 0.14, 26.6 + k * 0.45)
    thud(29.2, True)
    m = np.stack([L, R], 1); m = np.tanh(m * 1.3); m /= max(1e-9, np.abs(m).max()) / 0.9
    wavfile.write(os.path.join(OUT, "proto30.wav"), SR, (m * 32767).astype(np.int16))
def main():
    sound()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", os.path.join(OUT, "proto30.wav"),
                          "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), "-movflags", "+faststart",
                          os.path.join(OUT, "proto30.mp4")], stdin=subprocess.PIPE)
    last, base = None, None
    for f in range(1, N + 1): p.stdin.write(frame(f).tobytes())
    p.stdin.close(); p.wait(); print("done")
if __name__ == "__main__": main()
