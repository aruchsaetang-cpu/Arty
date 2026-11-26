"""Kuro Oni ep 1: PROTOTYPE animatic (throwaway). Draws each storyboard shot with simple shapes + captions and
synthesises a rough sound track, to test the story, pacing, sound cuts and impact rhythm. No Blender.
python3 shorts/kuro_oni/proto.py  -> shorts/kuro_oni/out/proto_ep1.mp4"""
import math, os, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 540, 960, 30, 60.0
N = int(DUR * FPS)
F_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
F_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 21)
F_X = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 78)

# (start, end, title, caption) from docs/superpowers/specs/2026-11-25-kuro-oni-design.md
SHOTS = [
    (0, 2.5, "1 Newborn", "Newborn eyes open: black sclera, white iris. Mother leans in."),
    (2.5, 5.5, "2 Kid", "Kid Gojo, mother holds his hand. A cup drops; his eyes follow it first."),
    (5.5, 8, "3 Teen", "Kyokushin kata. He breaks a steel bat on his shin (black bone)."),
    (8, 11, "4 Korea", "Every clan banner falls. Rain begins."),
    (11, 13, "5 The war", "About 100 clan fighters pour in. One man stands alone."),
    (13, 16, "6 First wave", "One short move each: aikido wrist turn, low kick. He straightens his sleeve."),
    (16, 19, "7 Ultra Instinct", "Sound cuts out. Eyes full white. He sees every blow first."),
    (19, 22, "8 Silhouette", "He walks through the flames. Nobody can touch him. Oni shadow."),
    (22, 25, "9 The count", "25 ... 50 ... 75 ... 100. One clean hit each."),
    (25, 29, "10 Korea is one", "Every clan leader kneels."),
    (29, 34, "11 Mother", "His mother brings the victory tea. He drinks. Her smile never changes."),
    (34, 37, "12 Poison", "Black bone stops blades, not poison. He drops to one knee, calm."),
    (37, 40, "13 Last look", "He looks up at her. She turns away. Black."),
    (40, 43, "14 Reborn", "Eyes open again: a human face. Heartbeat returns."),
    (43, 47, "15 New world", "Dawn meadow. Floating lights, a castle, two moons."),
    (47, 51, "16 Fireball", "A mage throws a fireball. His eyes track it first."),
    (51, 55, "17 Counter", "He slips it and counters with one Kyokushin punch."),
    (55, 57, "18 The mage", "\"Black-eyed demon.\""),
    (57, 60, "19 Title", ""),
]
BIG = [7.0, 22.4, 23.2, 24.0, 24.8, 52.4]                   # big hits: flash + shake + sub drop
SMALL = [13.6, 14.2, 14.7, 15.2, 15.7, 20.5, 21.3]          # small hits: shake only
HITS = sorted(BIG + SMALL)
SOUND_CUT = [(14.5, 16.0), (16.0, 19.0), (37.0, 40.0)]       # no rain / no music

def shot_of(t):
    for i, s in enumerate(SHOTS):
        if s[0] <= t < s[1]: return i, s
    return len(SHOTS) - 1, SHOTS[-1]

_grad = {}
def grad(top, bot):
    k = (top, bot)
    if k not in _grad:
        a = np.zeros((H, W, 3), np.uint8)
        for c in range(3): a[:, :, c] = np.linspace(top[c], bot[c], H)[:, None]
        _grad[k] = Image.fromarray(a)
    return _grad[k].copy()

def eye(d, cx, cy, w, h, openness=1.0, human=False, white=False):
    hh = max(2, h * openness)
    sclera = (235, 232, 228) if human else (8, 8, 10)
    d.ellipse([cx - w, cy - hh, cx + w, cy + hh], fill=sclera, outline=(0, 0, 0))
    r = min(hh, w * 0.62)
    if r > 3:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 20, 18) if human else (245, 248, 255))
        p = r * 0.38
        d.ellipse([cx - p, cy - p, cx + p, cy + p], fill=(8, 6, 8))
        if white: d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255))
        d.ellipse([cx - r * 0.5, cy - r * 0.55, cx - r * 0.2, cy - r * 0.25], fill=(255, 255, 255))

def person(d, x, y, h, col, lean=0.0, arm=0.0, kneel=False, eyes=None):
    hd = h * 0.13; bx = x + lean * h * 0.15
    top = y - h
    if kneel: top = y - h * 0.62
    d.ellipse([bx - hd, top, bx + hd, top + 2 * hd], fill=col)
    d.polygon([(bx - hd * 1.7, top + 2 * hd), (bx + hd * 1.7, top + 2 * hd), (x + hd * 1.2, y - (0 if kneel else h * 0.42)), (x - hd * 1.2, y - (0 if kneel else h * 0.42))], fill=col)
    if not kneel:
        d.line([(x - hd * 0.7, y - h * 0.42), (x - hd * 0.9, y)], fill=col, width=int(hd * 1.1))
        d.line([(x + hd * 0.7, y - h * 0.42), (x + hd * 1.1, y)], fill=col, width=int(hd * 1.1))
    ay = top + 2 * hd + h * 0.06
    d.line([(bx - hd * 1.6, ay), (bx - hd * 2.4, ay + h * 0.25 - arm * h * 0.3)], fill=col, width=int(hd * 0.9))
    d.line([(bx + hd * 1.6, ay), (bx + hd * 2.4 + arm * h * 0.35, ay + h * 0.25 - arm * h * 0.25)], fill=col, width=int(hd * 0.9))
    if eyes:
        for dx in (-hd * 0.4, hd * 0.4):
            d.ellipse([bx + dx - 3, top + hd - 3, bx + dx + 3, top + hd + 3], fill=eyes)

def rain(d, f, n=120, alpha=140):
    r = random.Random(f)
    for _ in range(n):
        x, y = r.randint(0, W), r.randint(0, H)
        d.line([(x, y), (x - 4, y + 26)], fill=(170, 185, 205), width=1)

def fire(d, f, side=True):
    r = random.Random(f // 2)
    for _ in range(26):
        x = r.choice([r.randint(-30, 90), r.randint(W - 90, W + 30)]) if side else r.randint(0, W)
        y = H - r.randint(0, 520) if side else H - r.randint(0, 200)
        rad = r.randint(20, 60)
        col = r.choice([(255, 120, 20), (255, 180, 40), (230, 70, 10)])
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=col)

def draw(t, f):
    i, (s0, s1, title, cap) = shot_of(t)
    u = t - s0
    img = grad((12, 12, 18), (24, 20, 28)); d = ImageDraw.Draw(img)
    cx = W // 2
    if i == 0:
        img = grad((0, 0, 0), (0, 0, 0)); d = ImageDraw.Draw(img)
        op = min(1, max(0, (u - 0.4) / 0.8))
        eye(d, cx, 380, 190, 120, op)
        if u > 1.3:
            a = min(1, (u - 1.3) / 1.0)
            d.ellipse([cx - 150, 620, cx + 150, 920], fill=(int(190 * a), int(140 * a), int(120 * a)))
            d.arc([cx - 70, 760, cx + 70, 850], 20, 160, fill=(int(60 * a), 0, 0), width=6)
    elif i == 1:
        img = grad((50, 34, 26), (22, 14, 12)); d = ImageDraw.Draw(img)
        for k in range(5): person(d, 60 + k * 105, 640, 380, (10, 8, 8))
        person(d, 300, 880, 330, (150, 110, 100)); person(d, 410, 880, 200, (60, 50, 50))
        cy = 300 + (max(0, u - 1.6)) * 250
        if u < 3: d.rectangle([220, cy, 250, cy + 30], fill=(220, 200, 150))
        if u > 2.0: eye(d, 410, 700, 12, 8, 1, True)
    elif i == 2:
        img = grad((60, 52, 44), (30, 26, 22)); d = ImageDraw.Draw(img)
        person(d, cx - 40, 800, 520, (12, 12, 16), arm=(0.2 if u < 1.4 else 0.9))
        if u < 1.5: d.line([(cx + 120, 560), (cx + 330, 640)], fill=(120, 120, 130), width=16)
        else:
            d.line([(cx + 110, 560), (cx + 200, 610)], fill=(120, 120, 130), width=16)
            d.line([(cx + 270, 700), (cx + 360, 770)], fill=(120, 120, 130), width=16)
    elif i == 3:
        img = grad((20, 26, 40), (8, 10, 16)); d = ImageDraw.Draw(img)
        d.ellipse([140, 260, 400, 700], outline=(90, 100, 120), width=3)
        for k in range(8):
            fy = 100 + ((u * 240 + k * 120) % 900)
            d.rectangle([40 + k * 62, fy, 60 + k * 62, fy + 70], fill=(140 + k * 10, 40, 40))
        d.text((cx, 80), "KOREA", font=F_B, fill=(200, 200, 210), anchor="mm")
        rain(d, f, int(40 + u * 40))
    elif i in (4, 5, 6, 7, 8):
        img = grad((70, 30, 14), (20, 8, 6)) if i != 6 else grad((10, 10, 14), (4, 4, 6)); d = ImageDraw.Draw(img)
        if i != 6:
            fire(d, f)
            rnd = random.Random(7)
            n = 100 if i == 4 else max(0, 100 - int((t - 13) * 20))
            for k in range(n):
                px, py = rnd.randint(30, W - 30), rnd.randint(520, 900)
                person(d, px, py, 90 + (py - 520) // 6, (12, 8, 8))
            for k in range(100 - n):
                px, py = rnd.randint(30, W - 30), rnd.randint(780, 930)
                d.line([(px - 28, py), (px + 28, py)], fill=(30, 12, 10), width=12)
        if i == 4: person(d, cx, 880, 480, (2, 2, 4), eyes=(255, 255, 255))
        if i == 5:
            ph = (t * 2) % 1.0
            person(d, cx, 880, 480, (2, 2, 4), arm=(0.9 if ph < 0.2 else 0.2), eyes=(255, 255, 255))
            rain(d, f, 90)
        if i == 6:
            eye(d, cx, 430, 200, 120, 1, False, white=(u > 1.2))
            for k in range(18):
                a = k / 18 * math.tau; d.line([(cx + 230 * math.cos(a), 430 + 230 * math.sin(a)), (cx + 480 * math.cos(a), 430 + 480 * math.sin(a))], fill=(200, 200, 210), width=2)
        if i == 7:
            sc = 480 + u * 60
            person(d, cx, 940, sc, (0, 0, 0), eyes=(255, 255, 255))
            d.polygon([(cx - 40, 180), (cx - 10, 90), (cx + 10, 180)], fill=(0, 0, 0))
            d.polygon([(cx + 40, 180), (cx + 10, 90), (cx - 10, 180)], fill=(0, 0, 0))
        if i == 8:
            person(d, cx, 880, 480, (2, 2, 4), arm=0.9, eyes=(255, 255, 255))
            cnt = 25 * (1 + sum(1 for b in BIG if 22 <= b <= 25 and t >= b)) if t >= 22.4 else 0
            if t >= 22.4: d.text((cx, 330), str(min(100, cnt - 25 + 25)), font=F_X, fill=(255, 255, 255), anchor="mm")
    elif i == 9:
        img = grad((70, 30, 14), (20, 8, 6)); d = ImageDraw.Draw(img)
        for k in range(10): person(d, 40 + k * 55, 900, 150 + (k % 3) * 30, (12, 8, 8), kneel=True)
        person(d, cx, 800, 420, (2, 2, 4), eyes=(255, 255, 255))
        rain(d, f, 60)
        d.text((cx, 120), "KOREA IS ONE", font=F_B, fill=(235, 220, 200), anchor="mm")
    elif i == 10:
        img = grad((38, 40, 56), (10, 12, 18)); d = ImageDraw.Draw(img)
        for k in range(10): person(d, 30 + k * 55, 920, 130, (12, 12, 16), kneel=True)
        person(d, 150, 800, 460, (2, 2, 4), eyes=(255, 255, 255))
        mx = 480 - min(1, u / 2.5) * 230
        person(d, mx, 800, 400, (150, 80, 100)); d.ellipse([mx - 40, 360, mx + 40, 440], fill=(200, 150, 130))
        d.arc([mx - 22, 395, mx + 22, 425], 20, 160, fill=(80, 0, 0), width=3)
        d.rectangle([mx - 150, 520, mx - 120, 548], fill=(225, 205, 160))
        rain(d, f, 110)
    elif i == 11:
        img = grad((30, 34, 50), (6, 8, 12)); d = ImageDraw.Draw(img)
        d.rectangle([60, 360, 130, 960], fill=(30, 20, 20)); d.rectangle([410, 360, 480, 960], fill=(30, 20, 20))
        k = min(1, u / 2.2)
        person(d, cx, 860, 430 - 150 * k * k, (2, 2, 4), lean=k * 1.5, eyes=(255, 255, 255), kneel=(u > 2.2))
        person(d, 440, 640, 260, (150, 80, 100))
        rain(d, f, 130)
    elif i == 12:
        img = grad((5, 5, 7), (0, 0, 0)); d = ImageDraw.Draw(img)
        op = max(0, 1 - u / 2.2)
        eye(d, cx, 420, 190, 120, op, False, white=(u < 1.0))
        if u < 1.2:
            d.ellipse([cx - 160, 740, cx + 160, 960], fill=(150, 80, 100))
    elif i == 13:
        img = grad((0, 0, 0), (0, 0, 0)); d = ImageDraw.Draw(img)
        op = min(1, max(0, (u - 0.4) / 0.8))
        eye(d, cx, 420, 190, 120, op, True)
    elif i == 14:
        img = grad((250, 190, 150), (90, 150, 90)); d = ImageDraw.Draw(img)
        d.ellipse([60, 120, 160, 220], fill=(250, 250, 240)); d.ellipse([360, 70, 420, 130], fill=(210, 220, 250))
        d.polygon([(330, 520), (330, 360), (365, 330), (400, 360), (400, 520)], fill=(60, 60, 90))
        for k in range(14):
            lx = (k * 77 + u * 20) % W; ly = 300 + (k * 53 % 500)
            d.ellipse([lx - 4, ly - 4, lx + 4, ly + 4], fill=(255, 255, 200))
        person(d, cx - 100, 860, 150 + 330 * min(1, u / 2.5), (20, 20, 24), eyes=(255, 255, 255))
    elif i in (15, 16):
        img = grad((250, 190, 150), (90, 150, 90)); d = ImageDraw.Draw(img)
        d.ellipse([60, 120, 160, 220], fill=(250, 250, 240)); d.ellipse([360, 70, 420, 130], fill=(210, 220, 250))
        person(d, 140, 880, 480, (20, 20, 24), arm=(0.9 if i == 16 and u > 0.8 else 0.1), eyes=(255, 255, 255))
        person(d, 430, 880, 400, (80, 40, 110))
        if i == 15:
            fx = 400 - u * 90 * (1 if u < 2 else 3)
            r_ = 30 + u * 14; fy = 560 + u * 40
            d.ellipse([fx - r_, fy - r_, fx + r_, fy + r_], fill=(255, 140, 30))
        else:
            fx = 200 + u * 60; fy = 640 - u * 20
            d.ellipse([fx - 40, fy - 40, fx + 40, fy + 40], fill=(255, 140, 30))
    elif i == 17:
        img = grad((20, 12, 30), (6, 4, 10)); d = ImageDraw.Draw(img)
        eye(d, cx, 380, 140, 80, 1, True)
        d.polygon([(cx - 80, 640), (cx + 80, 640), (cx + 20, 800), (cx - 20, 800)], fill=(40, 20, 60))
    elif i == 18:
        img = grad((0, 0, 0), (0, 0, 0)); d = ImageDraw.Draw(img)
        op = min(1, u / 0.6)
        eye(d, cx, 360, 190, 120, 1, False, white=True)
        d.text((cx, 720), "KURO ONI", font=F_X, fill=(int(240 * op), int(240 * op), int(255 * op)), anchor="mm")
        d.text((cx, 800), "EP 1", font=F_B, fill=(150, 150, 160), anchor="mm")
    # hit effects: shake + flash
    for ht in HITS:
        if ht <= t < ht + 0.25:
            amp = (12 if ht in BIG else 5) * (1 - (t - ht) / 0.25)
            r = random.Random(f)
            img = img.transform((W, H), Image.AFFINE, (1, 0, r.uniform(-amp, amp), 0, 1, r.uniform(-amp, amp)))
            d = ImageDraw.Draw(img)
            if ht in BIG and t < ht + 0.07:
                img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), 0.8 if t < ht + 0.035 else 0.4); d = ImageDraw.Draw(img)
    # caption bar
    bar = Image.new("RGBA", (W, 130), (0, 0, 0, 170)); img.paste(bar, (0, H - 130), bar); d = ImageDraw.Draw(img)
    d.text((16, H - 122), title, font=F_B, fill=(255, 220, 120))
    words, line, y = cap.split(), "", H - 82
    for w_ in words:
        if d.textlength(line + w_ + " ", font=F_S) > W - 32: d.text((16, y), line, font=F_S, fill=(255, 255, 255)); line, y = "", y + 25
        line += w_ + " "
    d.text((16, y), line, font=F_S, fill=(255, 255, 255))
    d.text((W - 90, 14), f"{t:4.1f}s", font=F_S, fill=(200, 200, 200))
    return img

# ------------------------------------------------------------------ sound
SR = 44100
def sound():
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n); rng = np.random.default_rng(3)
    def add(x, at, g=1.0, pan=0.0):
        i = int(at * SR); x = x[: max(0, n - i)]
        L[i:i + len(x)] += x * g * (1 - pan); R[i:i + len(x)] += x * g * (1 + pan)
    def tt(d): return np.arange(int(d * SR)) / SR
    def lp(x, fc): return sosfilt(butter(2, fc, "lowpass", fs=SR, output="sos"), x)
    def bp(x, a, b): return sosfilt(butter(2, [a, b], "bandpass", fs=SR, output="sos"), x)
    def beat(at, g=1.0):
        t_ = tt(0.18); add(np.sin(2 * np.pi * 55 * t_) * np.exp(-t_ * 22), at, 0.9 * g); add(np.sin(2 * np.pi * 48 * t_) * np.exp(-t_ * 24), at + 0.24, 0.6 * g)
    def thud(at, big):
        t_ = tt(1.2 if big else 0.35); f = 38 + 110 * np.exp(-t_ * 22)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t_ * (4.5 if big else 14))
        x += lp(rng.standard_normal(len(t_)), 2400) * np.exp(-t_ * 38) * 0.9
        add(x, at, 1.0 if big else 0.5)
    # rain, with gaps where sound is cut
    rn = bp(rng.standard_normal(n), 2500, 9000) * 0.05
    env = np.interp(np.arange(n) / SR, [0, 8, 10, 12, 34, 36, 60], [0, 0, 0.7, 1, 1, 1, 0.0])
    env[int(40 * SR):] = np.interp(np.arange(n - int(40 * SR)) / SR, [0, 3, 20], [0, 0.25, 0.5])
    for a, b in SOUND_CUT: env[int(a * SR):int(b * SR)] = 0
    rn *= env; L += rn; R += rn * 0.9
    # heartbeats
    for k in range(3): beat(0.1 + 0.9 * k, 0.9)
    for k in range(4): beat(34.0 + 1.0 + k * (0.9 + 0.3 * k), 0.8 - 0.1 * k)   # slowing
    for k in range(4): beat(40.3 + k * 0.85, 0.8)
    # hits
    for h_ in HITS: thud(h_, h_ in BIG)
    # drums in shot 4, drone before the mother and the shadow, bells
    for k in range(8): add(lp(rng.standard_normal(int(0.25 * SR)), 300) * np.exp(-tt(0.25) * 14), 8 + k * 0.36, 0.8)
    for a, b, f0 in ((19, 22, 62), (29, 34, 55), (22 - 0.001, 22, 62)):
        t_ = tt(b - a); add(np.sin(2 * np.pi * f0 * t_) * 0.35 * np.minimum(1, t_ / 1.0) * np.minimum(1, (b - a - t_) / 0.5), a, 1.0)
    for k, at in enumerate((25.0, 26.2, 27.4)):
        t_ = tt(2.5); add((np.sin(2 * np.pi * 523 * t_) + 0.5 * np.sin(2 * np.pi * 1318 * t_)) * np.exp(-t_ * 2.2) * 0.18, at, 1.0)
    # new world: chimes + wind, title hit + whisper
    for k, f0 in enumerate((659, 784, 988, 1175)):
        t_ = tt(2.0); add(np.sin(2 * np.pi * f0 * t_) * np.exp(-t_ * 2.5) * 0.16, 43.2 + k * 0.5)
    w_ = lp(bp(rng.standard_normal(int(4 * SR)), 300, 1400), 1400) * 0.06
    add(w_, 43.0)
    add(lp(rng.standard_normal(int(1.2 * SR)), 900) * np.hanning(int(1.2 * SR)) * 0.5, 55.5, 1.0)       # the mage's whisper
    thud(57.2, True)
    m = np.stack([L, R], 1); m = np.tanh(m * 1.3); m /= max(1e-9, np.abs(m).max()) / 0.9
    wavfile.write(os.path.join(OUT, "proto_ep1.wav"), SR, (m * 32767).astype(np.int16))

def main():
    sound()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", os.path.join(OUT, "proto_ep1.wav"), "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", os.path.join(OUT, "proto_ep1.mp4")], stdin=subprocess.PIPE)
    for f in range(N):
        p.stdin.write(draw(f / FPS, f).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    print("done", os.path.join(OUT, "proto_ep1.mp4"))

if __name__ == "__main__":
    main()
