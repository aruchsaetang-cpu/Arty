"""SHARDFALL — 3-minute anime short rendered in code from 12 reshaped keyframes.

World coordinates are the 1280x720 keyframe space; plates are 2x (2560x1440).
Usage: python3 film.py render <start_frame> <end_frame> <out.mp4>
       python3 film.py still <seconds> <out.png>
"""
import math, os, pickle, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

cv2.setNumThreads(1)
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 24
CYAN = (0.50, 1.00, 0.95)
GOLD = (1.00, 0.78, 0.30)
WHITE = (1.0, 1.0, 1.0)

# ---------------------------------------------------------------- utilities
_PL = {}


def plate(k):
    if k not in _PL:
        _PL[k] = cv2.cvtColor(cv2.imread(os.path.join(HERE, "plates", k + ".png")), cv2.COLOR_BGR2RGB)
    return _PL[k]


with open(os.path.join(HERE, "plates/meta.pkl"), "rb") as f:
    META = pickle.load(f)

U, V = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.42 * (((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.66)) ** 2) ** 1.4).clip(0.25, 1)[..., None]
_rng = np.random.default_rng(3)
GRAIN = [cv2.GaussianBlur(_rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.8) for _ in range(6)]


def clamp01(x): return max(0.0, min(1.0, x))
def lerp(a, b, t): return a + (b - a) * t
def smooth(t): t = clamp01(t); return t * t * (3 - 2 * t)
def ease_io(t): t = clamp01(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
def ease_out(t): t = clamp01(t); return 1 - (1 - t) ** 3
def ease_out_expo(t): t = clamp01(t); return 1 if t >= 1 else 1 - 2 ** (-10 * t)
def ease_in(t): t = clamp01(t); return t ** 3
def twos(t): return math.floor(t * 12) / 12  # animate on twos
def threes(t): return math.floor(t * 8) / 8


def pulse(t, t0, attack, decay):
    if t < t0: return 0.0
    d = t - t0
    return d / attack if d < attack else math.exp(-(d - attack) / decay)


def shake(t, amp, freq=18, seed=0):
    if amp <= 0: return 0.0, 0.0, 0.0
    p = seed * 1.7
    dx = math.sin(t * freq * 1.00 + p) * .6 + math.sin(t * freq * 2.31 + p * 2) * .4
    dy = math.sin(t * freq * 1.37 + p * 3) * .6 + math.sin(t * freq * 2.71 + p) * .4
    dr = math.sin(t * freq * 0.83 + p * 5)
    return dx * amp, dy * amp, dr * amp * 0.0012


class Cam:
    def __init__(self, cx, cy, w, rot=0.0):
        self.cx, self.cy, self.w, self.rot = cx, cy, w, rot
        self.s = w / W

    def maps(self):
        c, sn = math.cos(self.rot), math.sin(self.rot)
        du = (U - W / 2) * self.s
        dv = (V - H / 2) * self.s
        return self.cx + du * c - dv * sn, self.cy + du * sn + dv * c

    def scr(self, pts):
        """world (N,2) -> screen (N,2)"""
        p = np.asarray(pts, np.float32).reshape(-1, 2) - (self.cx, self.cy)
        c, sn = math.cos(self.rot), math.sin(self.rot)
        u = (p[:, 0] * c + p[:, 1] * sn) / self.s + W / 2
        v = (-p[:, 0] * sn + p[:, 1] * c) / self.s + H / 2
        return np.stack([u, v], 1)


def cam_with_shake(cx, cy, w, rot, t, amp, freq=18, seed=0):
    dx, dy, dr = shake(t, amp, freq, seed)
    return Cam(cx + dx, cy + dy, w, rot + dr)


def sway_field(x, y, t, specs):
    """specs: (ex, ey, rx, ry, amp, k, speed, axis, grow)  grow: weight increases toward +y (hems, ponytails)."""
    for ex, ey, rx, ry, amp, k, spd, axis, grow in specs:
        d = ((x - ex) / rx) ** 2 + ((y - ey) / ry) ** 2
        m = np.clip(1 - d, 0, 1)
        m = m * m * (3 - 2 * m)
        if grow:
            m = m * np.clip((y - (ey - ry)) / (2 * ry), 0, 1)
        ph = (y if axis == "x" else x) * k - spd * t
        off = m * amp * (np.sin(ph) + 0.35 * np.sin(ph * 2.3 + 1.1))
        if axis == "x": x = x + off
        else: y = y + off
    return x, y


def render_plate(key, cam, t=0.0, sway=None, warp=None):
    x, y = cam.maps()
    if sway: x, y = sway_field(x, y, t, sway)
    if warp: x, y = warp(x, y)
    img = cv2.remap(plate(key), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return img.astype(np.float32) / 255


def render_mb(key, cams, t, sway=None, warp=None):
    acc = None
    for c in cams:
        im = render_plate(key, c, t, sway, warp)
        acc = im if acc is None else acc + im
    return acc / len(cams)


def glow(light, k1=0.9, k2=0.7):
    small = cv2.resize(light, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g = cv2.GaussianBlur(small, (0, 0), 3) * k1 + cv2.GaussianBlur(small, (0, 0), 12) * k2
    return light + cv2.resize(g, (W, H))


def add_light(img, light, k1=0.9, k2=0.7):
    return img + glow(light, k1, k2)


def blank():
    return np.zeros((H, W, 3), np.float32)


def flash(img, a, col=WHITE):
    if a <= 0: return img
    return img * (1 - a) + np.float32(col) * a


def tint(img, col, a):
    return img * (1 - a) + img * np.float32(col) * a


def chroma(img, k):
    if k <= 0: return img
    out = img.copy()
    for ch, sc in ((0, 1 + k), (2, 1 - k)):
        M = np.float32([[sc, 0, W / 2 * (1 - sc)], [0, sc, H / 2 * (1 - sc)]])
        out[..., ch] = cv2.warpAffine(img[..., ch], M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return out


def zoom_blur(img, cx, cy, k, n=6):
    if k <= 0: return img
    acc = img.copy()
    for i in range(1, n):
        sc = 1 + k * i / n
        M = np.float32([[sc, 0, cx * (1 - sc)], [0, sc, cy * (1 - sc)]])
        acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / n


def two_tone(img, dark=(0.02, 0.02, 0.04), light=(1, 1, 1), th=0.45, invert=False):
    lum = img @ np.float32([0.299, 0.587, 0.114])
    m = (lum > th).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), 1.0)
    if invert: m = 1 - m
    return np.float32(dark) * (1 - m[..., None]) + np.float32(light) * m[..., None]


def shockwave(x, y, cx, cy, r, width, amp, yscale=1.0):
    dx, dy = x - cx, (y - cy) * yscale
    d = np.sqrt(dx * dx + dy * dy) + 1e-3
    band = np.exp(-((d - r) / width) ** 2) * amp
    return x - dx / d * band, y - dy / d * band / yscale


# ---------------------------------------------------------------- FX primitives
def _u8():
    return np.zeros((H, W, 3), np.uint8)


def light_from_u8(c): return c.astype(np.float32) / 255


def col8(c, a=1.0): return tuple(int(255 * v * a) for v in c)


class CrackTree:
    def __init__(self, cx, cy, seed, n_main=9, length=900, step=26, branch=0.13, jag=0.35):
        rng = np.random.default_rng(seed)
        self.segs = []  # (x0,y0,x1,y1,dist,depth)
        stack = []
        for i in range(n_main):
            a = 2 * math.pi * i / n_main + rng.normal(0, .25)
            stack.append((cx, cy, a, 0.0, 0, length * rng.uniform(.6, 1.15)))
        while stack:
            x, y, a, d, dep, L = stack.pop()
            run = 0
            while run < L:
                a += rng.normal(0, jag)
                st = step * rng.uniform(.6, 1.4) * (0.75 ** dep)
                nx, ny = x + math.cos(a) * st, y + math.sin(a) * st
                self.segs.append((x, y, nx, ny, d, dep))
                d += st; run += st; x, y = nx, ny
                if dep < 3 and rng.random() < branch:
                    stack.append((x, y, a + rng.choice([-1, 1]) * rng.uniform(.4, 1.1), d, dep + 1, L * .45))
        self.maxd = max(s[4] for s in self.segs)

    def draw(self, canvas, cam, progress, col=CYAN, width=3.0, alpha=1.0, flicker=0.0, t=0.0):
        lim = progress * self.maxd
        if lim <= 0: return
        segs = [s for s in self.segs if s[4] < lim]
        if not segs: return
        a = np.array([[s[0], s[1], s[2], s[3]] for s in segs], np.float32)
        p0, p1 = cam.scr(a[:, :2]), cam.scr(a[:, 2:])
        sc = 1 / cam.s
        f = 1 - flicker * (0.5 + 0.5 * math.sin(t * 47))
        for (u0, v0), (u1, v1), s in zip(p0, p1, segs):
            wdt = max(1, int(width * sc * (0.62 ** s[5]) + .5))
            cv2.line(canvas, (int(u0), int(v0)), (int(u1), int(v1)), col8(col, alpha * f), wdt + 2, cv2.LINE_AA)
            cv2.line(canvas, (int(u0), int(v0)), (int(u1), int(v1)), col8(WHITE, alpha * f), max(1, wdt // 2), cv2.LINE_AA)


class Shards:
    """Falling glass shards in world space; each a spinning triangle."""

    def __init__(self, seed, n, x0, x1, y0, y1, vy=(40, 120), size=(4, 14), vx=(-15, 15), spin=3.0):
        r = np.random.default_rng(seed)
        self.p = np.stack([r.uniform(x0, x1, n), r.uniform(y0, y1, n)], 1)
        self.v = np.stack([r.uniform(*vx, n), r.uniform(*vy, n)], 1)
        self.sz = r.uniform(*size, n)
        self.ph = r.uniform(0, 6.3, n)
        self.sp = r.uniform(-spin, spin, n)
        self.br = r.uniform(.45, 1, n)
        self.span = (y0, y1)
        self.shape = r.uniform(.5, 1.0, (n, 3))

    def draw(self, canvas, cam, t, alpha=1.0, col=CYAN, wrap=True, origin=None, burst=None):
        if origin is not None:  # burst outward from origin
            pos = origin + self.v * t * burst + np.array([0, 60]) * t * t
        else:
            pos = self.p + self.v * t
            if wrap:
                y0, y1 = self.span
                pos[:, 1] = y0 + np.mod(pos[:, 1] - y0, (y1 - y0) + 80) - 40
        ang = self.ph + self.sp * t
        sc = 1 / cam.s
        for i in range(len(pos)):
            r = self.sz[i]
            pts = []
            for j, base in enumerate((0, 2.3, 4.1)):
                a = ang[i] + base
                rr = r * self.shape[i, j]
                pts.append((pos[i, 0] + math.cos(a) * rr, pos[i, 1] + math.sin(a) * rr * abs(math.cos(ang[i] * .7)) + .5))
            sp = cam.scr(pts).astype(np.int32)
            if sp[:, 0].max() < -20 or sp[:, 0].min() > W + 20 or sp[:, 1].max() < -20 or sp[:, 1].min() > H + 20:
                continue
            glint = 0.6 + 0.4 * math.sin(ang[i] * 3) ** 8
            c = col8(col, alpha * self.br[i] * glint)
            cv2.fillConvexPoly(canvas, sp, c, cv2.LINE_AA)
            if r * sc > 6:
                cv2.polylines(canvas, [sp], True, col8(WHITE, alpha * glint * .8), 1, cv2.LINE_AA)


def speed_lines(img, cx, cy, t, n=90, r0=(0.30, 0.55), col=(0, 0, 0), alpha=0.9, seed=0, thick=(2, 9)):
    r = np.random.default_rng(seed + int(t * 12))
    canvas = np.zeros((H, W), np.uint8)
    diag = math.hypot(W, H)
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi)
        ri = r.uniform(*r0) * diag
        th = r.uniform(*thick) * 0.5 / diag * 6
        pts = np.array([[cx + math.cos(a) * ri, cy + math.sin(a) * ri],
                        [cx + math.cos(a - th) * diag, cy + math.sin(a - th) * diag],
                        [cx + math.cos(a + th) * diag, cy + math.sin(a + th) * diag]], np.int32)
        cv2.fillConvexPoly(canvas, pts, 255, cv2.LINE_AA)
    m = canvas.astype(np.float32)[..., None] / 255 * alpha
    return img * (1 - m) + np.float32(col) * m


def parallel_lines(img, t, angle, n=40, col=(1, 1, 1), alpha=.5, seed=0, length=(200, 700)):
    r = np.random.default_rng(seed + int(t * 12))
    canvas = np.zeros((H, W), np.uint8)
    dx, dy = math.cos(angle), math.sin(angle)
    for _ in range(n):
        x, y = r.uniform(-200, W + 200), r.uniform(-200, H + 200)
        L = r.uniform(*length)
        cv2.line(canvas, (int(x), int(y)), (int(x + dx * L), int(y + dy * L)), 255, int(r.uniform(1, 4)), cv2.LINE_AA)
    m = canvas.astype(np.float32)[..., None] / 255 * alpha
    return img * (1 - m) + np.float32(col) * m


def motes(canvas, t, seed, n, col, size=(1, 3), drift=(10, -20), alpha=.7):
    r = np.random.default_rng(seed)
    x = (r.uniform(0, W, n) + drift[0] * t * r.uniform(.5, 1.5, n)) % W
    y = (r.uniform(0, H, n) + drift[1] * t * r.uniform(.5, 1.5, n)) % H
    tw = 0.5 + 0.5 * np.sin(t * r.uniform(1, 4, n) + r.uniform(0, 6, n))
    s = r.uniform(*size, n)
    for i in range(n):
        cv2.circle(canvas, (int(x[i]), int(y[i])), max(1, int(s[i])), col8(col, alpha * tw[i]), -1, cv2.LINE_AA)


def birds(canvas, cam, t, flock, col=(0.08, 0.06, 0.12)):
    """flock: list of (x0, y0, vx, vy, size, phase) world space; draws flapping Vs as dark strokes."""
    for x0, y0, vx, vy, sz, ph in flock:
        x, y = x0 + vx * t, y0 + vy * t + 3 * math.sin(t * 2 + ph)
        flap = math.sin(twos(t) * 14 + ph)
        p = cam.scr([(x - sz, y - sz * 0.5 * flap), (x, y), (x + sz, y - sz * 0.5 * flap)]).astype(np.int32)
        cv2.polylines(canvas, [p], False, (255, 255, 255), max(1, int(sz / cam.s * .25)), cv2.LINE_AA)


def draw_birds(img, cam, t, flock, col=(0.1, 0.07, 0.14)):
    m = np.zeros((H, W, 3), np.uint8)
    birds(m, cam, t, flock)
    a = m[..., :1].astype(np.float32) / 255
    return img * (1 - a) + np.float32(col) * a


def windows_layer(img, cam, key, t, on_until=None, seed=0, twinkle=0.0, warm=(1.0, .82, .45)):
    """Darken windows not yet lit (on_until: seconds over which they switch on), plus twinkle."""
    wins = META[key + "_windows"]
    r = np.random.default_rng(seed)
    times = r.uniform(0, 1, len(wins))
    dark = np.zeros((H, W), np.uint8)
    lit = _u8()
    for (x, y, w, h), tt in zip(wins, times):
        x, y, w, h = x / 2, y / 2, w / 2, h / 2
        pts = cam.scr([(x - .5, y - .5), (x + w + .5, y - .5), (x + w + .5, y + h + .5), (x - .5, y + h + .5)]).astype(np.int32)
        if on_until is not None:
            ton = tt * on_until
            on = t > ton and not (ton < t < ton + .25 and int(t * 24) % 2)
            if not on:
                cv2.fillConvexPoly(dark, pts, 255)
                continue
        if twinkle > 0:
            k = twinkle * max(0, math.sin(t * (1 + tt * 3) + tt * 40)) ** 6
            if k > .05: cv2.fillConvexPoly(lit, pts, col8(warm, k))
    m = cv2.GaussianBlur(dark.astype(np.float32) / 255, (0, 0), 1)[..., None]
    img = img * (1 - m * .85)
    return add_light(img, light_from_u8(lit), .6, .4)


def ribbons(canvas, cam, t, cx, cy, n=5, r0=30, r1=170, height=300, turns=2.2, growth=1.0, alpha=1.0):
    for i in range(n):
        col = GOLD if i % 2 else CYAN
        pts = []
        ss = np.linspace(0, growth, 70)
        for s in ss:
            a = s * turns * 2 * math.pi + t * 4.5 + i * 2 * math.pi / n
            r = r0 + (r1 - r0) * s
            pts.append((cx + math.cos(a) * r, cy + height * 0.5 - s * height + math.sin(a) * r * 0.28))
        p = cam.scr(pts).astype(np.int32)
        for j in range(len(p) - 1):
            fade = j / len(p)
            cv2.line(canvas, tuple(p[j]), tuple(p[j + 1]), col8(col, alpha * (0.3 + 0.7 * fade)), max(1, int(3 / cam.s)), cv2.LINE_AA)


def bezier(p0, p1, p2, n=50):
    s = np.linspace(0, 1, n)[:, None]
    return (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s * s * p2


# ---------------------------------------------------------------- text
FONT_T = os.path.join(HERE, "fonts/DelaGothicOne-Regular.ttf")
FONT_B = os.path.join(HERE, "fonts/ZenKakuGothicNew-Bold.ttf")
_TXT = {}


def text_rgba(s, font, size, fill=(255, 255, 255), stroke=0, stroke_fill=(0, 0, 0), spacing=0):
    key = (s, font, size, fill, stroke, spacing)
    if key in _TXT: return _TXT[key]
    f = ImageFont.truetype(font, size)
    if spacing:
        widths = [f.getbbox(c)[2] - f.getbbox(c)[0] for c in s]
        tw = sum(widths) + spacing * (len(s) - 1) + 2 * stroke + 10
    else:
        b = f.getbbox(s, stroke_width=stroke); tw = b[2] + 10
    th = int(size * 1.5) + 2 * stroke
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if spacing:
        x = stroke + 5
        for c, wd in zip(s, widths):
            d.text((x, stroke), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += wd + spacing
    else:
        d.text((5, stroke), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    a = np.asarray(im).astype(np.float32) / 255
    _TXT[key] = a
    return a


def paste(img, rgba, cx, cy, alpha=1.0, scale=1.0, additive=False):
    if alpha <= 0: return img
    if scale != 1.0:
        rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return img
    sub = rgba[ya - y0:yb - y0, xa - x0:xb - x0]
    a = sub[..., 3:4] * alpha
    if additive:
        img[ya:yb, xa:xb] += sub[..., :3] * a
    else:
        img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - a) + sub[..., :3] * a
    return img


SUBS = []  # (t0, t1, jp, en)


def subtitles(img, g):
    for t0, t1, jp, en in SUBS:
        if t0 - .2 <= g <= t1 + .2:
            a = smooth((g - t0 + .2) / .2) * smooth((t1 + .2 - g) / .2)
            img = paste(img, text_rgba(jp, FONT_B, 50, stroke=4, stroke_fill=(10, 10, 20)), W / 2, 935, a)
            img = paste(img, text_rgba(en, FONT_B, 34, fill=(255, 226, 160), stroke=3, stroke_fill=(10, 10, 20)), W / 2, 1005, a)
    return img


# ---------------------------------------------------------------- shots
SHOTS = []


def shot(dur, name=None):
    def deco(fn):
        SHOTS.append((dur, fn, name or fn.__name__))
        return fn
    return deco


# precomputed systems
CRK_F05 = CrackTree(740, 170, seed=5, n_main=11, length=950)
CRK_F01 = CrackTree(700, 150, seed=9, n_main=8, length=500)
CRK_BEAST = CrackTree(690, 380, seed=21, n_main=9, length=380, step=16, jag=.5)
CRK_TITLE = CrackTree(640, 360, seed=33, n_main=7, length=650, branch=.07)
SH_FALL = Shards(1, 160, 0, 1280, -80, 720, vy=(50, 140), size=(3, 12))
SH_FALL2 = Shards(2, 70, 0, 1280, -80, 720, vy=(90, 220), size=(8, 22))
SH_SNOW = Shards(3, 260, 0, 1280, -60, 720, vy=(18, 45), size=(2, 6), vx=(-6, 6), spin=1.2)
SH_SNOW_FG = Shards(4, 40, 0, 1280, -60, 720, vy=(30, 60), size=(10, 22), vx=(-8, 8), spin=1.0)
SH_BURST = Shards(5, 140, 0, 1, 0, 1, vy=(-400, 400), vx=(-500, 500), size=(5, 26), spin=8)
SH_DRIFT = Shards(6, 90, 0, 1280, 0, 720, vy=(-8, 8), vx=(-10, 10), size=(4, 14), spin=.8)
FLOCK = [(-60 - i * 28, 150 + (i % 3) * 14 + i * 3, 70, -6, 6, i) for i in range(7)]
FLOCK2 = [(1340 + i * 30, 90 + (i % 2) * 15, -60, 3, 5, i * 1.3) for i in range(5)]

# ---- ACT 0: cold open -------------------------------------------------------


@shot(1.5)
def s_black(t, T):
    img = blank()
    lt = _u8()
    k = smooth(t / T) * .5
    cv2.circle(lt, (W // 2, H // 2), 2, col8(CYAN, k), -1, cv2.LINE_AA)
    return add_light(img, light_from_u8(lt), 2.5, 2.5)


@shot(1.5)
def s_cold_clash(t, T):
    tq = twos(t)
    cam = cam_with_shake(520 + 20 * tq, 380, 900 - 80 * tq, 0, t, 14, 30)
    img = render_plate("f09", cam)
    sc = cam.scr([(520, 400)])[0]
    img = speed_lines(img, sc[0], sc[1], t, 120, (0.12, 0.35), (0, 0, 0), .85, seed=11)
    phase = int(t * 12) % 4
    if phase == 0: img = two_tone(img, invert=True)
    elif phase == 2: img = two_tone(img, dark=(0.03, 0, 0), light=(0.95, 0.12, 0.10))
    return chroma(img, 0.012)


@shot(0.75)
def s_cold_ren(t, T):
    cam = cam_with_shake(640, 230, 640 - 120 * t, -0.05, t, 6, 25)
    img = render_plate("f07", cam)
    img = parallel_lines(img, t, -0.9, 50, (1, 1, 1), .6, seed=3)
    return two_tone(img, dark=(0.02, 0.02, 0.05), light=(0.9, 1, 1), th=.38) if int(t * 12) % 3 == 0 else img


@shot(0.75)
def s_cold_beast(t, T):
    cam = cam_with_shake(905, 205, 300 - 60 * t, 0, t, 5, 30)
    img = render_plate("f06", cam)
    lt = _u8()
    e = cam.scr([(920, 187)])[0]
    cv2.circle(lt, (int(e[0]), int(e[1])), 30, col8(WHITE, .9), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 2, 2)
    return flash(img, smooth((t - .45) / .3))


@shot(7.0)
def s_title(t, T):
    img = blank()
    g = np.float32([0.02, 0.06, 0.08]) * (1 + 0.6 * np.exp(-((_yy - H / 2) / 400) ** 2))[..., None]
    img = img + g
    title = "SHARDFALL"
    lt = _u8()
    cam = Cam(640, 360, 1280)
    # cracks spread behind the logo, then flare
    CRK_TITLE.draw(lt, cam, ease_out(t / 2.2), CYAN, 1.0, .28 * (1 - .5 * smooth((t - 2.5) / 2)))
    # assemble letters: each slams in on its own beat
    f = ImageFont.truetype(FONT_T, 190)
    widths = [f.getbbox(c)[2] - f.getbbox(c)[0] + 18 for c in title]
    x = W / 2 - sum(widths) / 2
    shatter = smooth((t - 5.6) / .8)
    for i, c in enumerate(title):
        t0 = 0.35 + i * 0.13
        k = clamp01((t - t0) / 0.18)
        if k > 0 and shatter < 1:
            sc = 1 + 1.8 * (1 - ease_out(k))
            col = (230, 255, 250) if c not in "FALL" or i < 5 else (127, 243, 230)
            rgba = text_rgba(c, FONT_T, 190, fill=col)
            dy = -40 * shatter * (i % 3 - 1) + 600 * shatter ** 2
            img = paste(img, rgba, x + widths[i] / 2, H / 2 - 30 + dy, k * (1 - shatter), sc)
        x += widths[i]
    jp = text_rgba("硝 子 の 空", FONT_T, 54, fill=(255, 168, 96))
    img = paste(img, jp, W / 2, H / 2 + 135, smooth((t - 2.0) / .8) * (1 - shatter))
    # light sweep across the logo
    sweep = (t - 2.6) / 1.2
    if 0 < sweep < 1:
        xs = int(lerp(-200, W + 200, sweep))
        cv2.line(lt, (xs, 0), (xs - 300, H), col8(WHITE, .55), 60)
    if shatter > 0:
        SH_BURST.draw(lt, cam, (t - 5.6), 1 - shatter * .7, CYAN, origin=np.array([640, 340]), burst=0.9)
    hit = pulse(t, 0.35 + 8 * .13, .02, .25) + pulse(t, 5.6, .03, .3)
    img = add_light(img, light_from_u8(lt), 1.2, 1.0)
    img = flash(img, hit * .5)
    return img * smooth((T - t) / .6)


# ---- ACT 1: dusk -------------------------------------------------------------
SWAY_F02 = [(547, 205, 70, 50, 2.4, .08, 5, "x", False), (750, 390, 30, 130, 5, .05, 4, "x", True),
            (545, 600, 120, 45, 3, .05, 6, "x", True), (750, 600, 110, 45, 3, .05, 6, "x", True)]
SWAY_F03 = [(640, 180, 260, 140, 3.2, .06, 4, "x", False), (640, 700, 330, 50, 1.5, .05, 4, "y", False)]
SWAY_F04 = [(350, 400, 95, 330, 7, .022, 3, "x", True), (413, 147, 55, 40, 2.5, .2, 8, "y", False)]
SWAY_F08 = [(440, 460, 80, 270, 6, .03, 6, "x", True), (640, 260, 230, 90, 3, .08, 7, "y", False)]
SWAY_F07 = [(390, 640, 150, 110, 7, .05, 12, "y", False), (553, 330, 60, 50, 3, .2, 14, "x", False)]
SWAY_F11 = [(640, 640, 220, 70, 1.5, .05, 3, "x", True)]
SWAY_F12 = [(610, 520, 200, 120, 1.2, .05, 2, "x", True)]


def haze(img, t, col, a, speed=8, seed=0):
    r = np.random.default_rng(seed)
    n = r.random((9, 16)).astype(np.float32)
    big = cv2.resize(n, (W + 400, H), interpolation=cv2.INTER_CUBIC)
    off = int(t * speed) % 400
    m = big[:, off:off + W][..., None]
    return img + np.float32(col) * m * a


@shot(10.0)
def s_city_pan(t, T):
    p = ease_io(t / T)
    cam = Cam(lerp(560, 720, p), lerp(380, 360, p), lerp(1050, 980, p))
    img = render_plate("f01", cam)
    img = windows_layer(img, cam, "f01", t, on_until=7.5, seed=1, twinkle=.4)
    img = draw_birds(img, cam, t, FLOCK)
    img = haze(img, t, (1, .55, .35), .06, 10)
    lt = _u8()
    motes(lt, t, 4, 40, (1, .7, .4), (1, 2), (6, -4), .35)
    img = add_light(img, light_from_u8(lt))
    return img * smooth(t / 1.2)


@shot(5.0)
def s_city_detail(t, T):
    cam = Cam(lerp(860, 900, t / T), 300, lerp(480, 420, ease_io(t / T)))
    img = render_plate("f01", cam)
    img = windows_layer(img, cam, "f01", t + 8, seed=1, twinkle=.8)
    return haze(img, t, (1, .5, .4), .05, 14)


@shot(8.0)
def s_rooftop(t, T):
    cam = Cam(640 + 4 * math.sin(t * .4), 360 + 3 * math.sin(t * .3), 1240 - 30 * t / T)
    img = render_plate("f02", cam, twos(t), SWAY_F02)
    img = windows_layer(img, cam, "f02", t, seed=2, twinkle=.5)
    img = haze(img, t, (1, .5, .3), .05, 12, 1)
    lt = _u8()
    motes(lt, t, 7, 50, (1, .75, .5), (1, 3), (40, -6), .4)
    img = add_light(img, light_from_u8(lt))
    return img


@shot(4.0)
def s_rooftop_heads(t, T):
    cam = Cam(lerp(640, 660, t / T), lerp(300, 290, t / T), lerp(620, 560, ease_io(t / T)))
    img = render_plate("f02", cam, twos(t), SWAY_F02)
    img = haze(img, t, (1, .55, .35), .05, 12, 2)
    return img


@shot(6.0)
def s_ren_push(t, T):
    p = ease_in(t / T) * .6 + (t / T) * .4
    cam = Cam(lerp(640, 645, p), lerp(380, 400, p), lerp(1280, 820, p))
    amp = 1 + 2 * t / T
    sw = [(a, b, c, d, e * amp, f, g, h, i) for a, b, c, d, e, f, g, h, i in SWAY_F03]
    img = render_plate("f03", cam, twos(t), sw)
    lt = _u8()
    motes(lt, t, 9, 30, (1, .8, .5), (2, 6), (0, -10), .25)
    img = add_light(img, light_from_u8(lt), 1.5, 1.5)
    # eye glint as he focuses
    k = pulse(t, 4.6, .12, .5)
    if k > 0:
        lt = _u8()
        for e in cam.scr([(573, 413), (720, 413)]):
            cv2.line(lt, (int(e[0] - 60 * k), int(e[1])), (int(e[0] + 60 * k), int(e[1])), col8(WHITE, k), 2, cv2.LINE_AA)
            cv2.circle(lt, (int(e[0]), int(e[1])), 6, col8((1, .85, .5), k), -1, cv2.LINE_AA)
        img = add_light(img, light_from_u8(lt), 2, 2)
    return img


@shot(2.0)
def s_ren_eyes(t, T):
    cam = cam_with_shake(646, 413, lerp(470, 400, ease_out(t / T)), 0, t, 1.2, 9)
    img = render_plate("f03", cam, twos(t), [(646, 300, 300, 140, 5, .08, 9, "x", False)])
    img = parallel_lines(img, t, 0.08, 26, (1, .9, .8), .25, seed=8, length=(300, 900))
    lt = _u8()
    for e in cam.scr([(573, 413), (720, 413)]):
        cv2.circle(lt, (int(e[0]), int(e[1])), 34, col8((1, .7, .25), .12 + .08 * math.sin(t * 20)), -1, cv2.LINE_AA)
    return add_light(img, light_from_u8(lt), 1.2, 1.4)


@shot(4.0)
def s_hana_flash(t, T):
    cam = Cam(lerp(640, 630, t / T), lerp(400, 420, t / T), lerp(1280, 1100, ease_io(t / T)))
    img = render_plate("f04", cam, twos(t), SWAY_F04)
    img = draw_birds(img, cam, t, FLOCK2, col=(.2, .25, .4))
    # dreamy flashback: soft bloom + warm halation + white vignette
    soft = cv2.GaussianBlur(img, (0, 0), 6)
    img = img * .78 + soft * .32
    edge = 1 - VIGNETTE
    img = img + edge * .9
    lt = _u8()
    motes(lt, t, 12, 40, (1, 1, .9), (2, 5), (14, -16), .35)
    img = add_light(img, light_from_u8(lt))
    return flash(img, 1 - smooth(t / .5))


@shot(4.0)
def s_hana_smile(t, T):
    cam = Cam(lerp(625, 640, t / T), lerp(470, 460, t / T), lerp(720, 640, ease_io(t / T)))
    img = render_plate("f04", cam, twos(t), SWAY_F04)
    soft = cv2.GaussianBlur(img, (0, 0), 6)
    img = img * .8 + soft * .3 + (1 - VIGNETTE) * .9
    lt = _u8()
    motes(lt, t, 13, 30, (1, 1, .85), (2, 6), (18, -12), .4)
    img = add_light(img, light_from_u8(lt))
    return flash(img, smooth((t - (T - .4)) / .4))


@shot(3.0)
def s_ren_back(t, T):
    cam = Cam(640, 400, 1150 - 40 * t)
    img = render_plate("f03", cam, twos(t), SWAY_F03)
    k = pulse(t, 2.0, .05, .5)
    img = tint(img, (.6, 1.3, 1.4), k * .8)
    img = flash(img, k * .25, CYAN)
    return flash(img, 1 - smooth(t / .3))


# ---- ACT 2: crack + beast ----------------------------------------------------


@shot(2.5)
def s_point(t, T):
    cam = cam_with_shake(680, 330, 1100, 0, t, 2 * smooth(t / T), 20)
    img = render_plate("f01", cam)
    img = tint(img, (.55, .65, 1.0), smooth(t / T) * .6)  # light drains from the dusk
    lt = _u8()
    p = cam.scr([(700, 150)])[0]
    k = smooth(t / T)
    cv2.circle(lt, (int(p[0]), int(p[1])), int(3 + 10 * k), col8(WHITE, .5 + .5 * k), -1, cv2.LINE_AA)
    cv2.line(lt, (int(p[0] - 200 * k), int(p[1])), (int(p[0] + 200 * k), int(p[1])), col8(CYAN, k), 2, cv2.LINE_AA)
    CRK_F01.draw(lt, cam, smooth((t - 1.7) / .8) * .35, CYAN, 2.0)
    img = add_light(img, light_from_u8(lt), 2, 2)
    return flash(img, smooth((t - 2.2) / .3))


@shot(6.0)
def s_sky_cracks(t, T):
    cam = cam_with_shake(lerp(700, 720, t / T), lerp(330, 345, t / T), lerp(1000, 1200, ease_out(t / T)), 0, t,
                         8 * pulse(t, 0, .05, .8) + 2.5, 22)
    img = render_plate("f05", cam)
    lt = _u8()
    CRK_F05.draw(lt, cam, ease_out_expo(t / 2.5), CYAN, 2.2, .9, flicker=.3, t=t)
    SH_FALL.draw(lt, cam, t, smooth((t - .4) / 1.2))
    SH_FALL2.draw(lt, cam, t * .8, smooth((t - 1.0) / 1.2) * .8)
    img = windows_layer(img, cam, "f05", t, seed=5, twinkle=.4, warm=(.7, 1, 1))
    c = cam.scr([(740, 170)])[0]
    img = add_light(img, light_from_u8(lt), 1.2, 1.1)
    img = zoom_blur(img, c[0], c[1], .06 * pulse(t, 0, .05, .6))
    img = flash(img, (1 - smooth(t / .5)) * .95)
    return chroma(img, .006 * pulse(t, 0, .05, 1))


@shot(3.5)
def s_city_rain(t, T):
    cam = cam_with_shake(740, lerp(470, 450, t / T), 640, 0, t, 3, 20)
    img = render_plate("f05", cam)
    img = windows_layer(img, cam, "f05", t + 3, seed=5, twinkle=.8, warm=(.7, 1, 1))
    lt = _u8()
    SH_FALL.draw(lt, cam, t + 6)
    SH_FALL2.draw(lt, cam, t * .9 + 5)
    img = add_light(img, light_from_u8(lt), 1.1, 1.0)
    for k, tt in ((.25, .8), (.35, 2.4)):
        img = flash(img, pulse(t, tt, .03, .2) * k, CYAN)
    return img


@shot(2.0)
def s_heads_wind(t, T):
    cam = cam_with_shake(650, 300, 560, 0, t, 3, 14)
    sw = [(a, b, c, d, e * 3, f, g * 2.5, h, i) for a, b, c, d, e, f, g, h, i in SWAY_F02]
    img = render_plate("f02", cam, twos(t), sw)
    img = tint(img, (.45, .75, 1.1), .75)
    img = img + np.float32(CYAN) * .12 * (0.5 + 0.5 * math.sin(t * 30))
    img = parallel_lines(img, t, 3.0, 40, (.8, 1, 1), .35, seed=6)
    lt = _u8()
    SH_FALL2.draw(lt, cam, t + 2)
    return add_light(img, light_from_u8(lt))


@shot(8.0)
def s_beast_reveal(t, T):
    p = ease_io(t / 6.0)
    cam = cam_with_shake(lerp(600, 680, p), lerp(590, 330, p), lerp(560, 1240, p), 0, t,
                         1.5 + 6 * pulse(t, 6.2, .05, .6), 16)
    img = render_plate("f06", cam)
    lt = _u8()
    # surface glints on crystal plates
    r = np.random.default_rng(2)
    pts = np.stack([r.uniform(380, 980, 70), r.uniform(150, 600, 70)], 1)
    for i, s in enumerate(cam.scr(pts)):
        k = max(0, math.sin(t * 2.5 + i * 1.7)) ** 12
        if k > .05:
            L = int(18 * k / cam.s)
            cv2.line(lt, (int(s[0] - L), int(s[1])), (int(s[0] + L), int(s[1])), col8(WHITE, k), 1, cv2.LINE_AA)
            cv2.line(lt, (int(s[0]), int(s[1] - L)), (int(s[0]), int(s[1] + L)), col8(WHITE, k), 1, cv2.LINE_AA)
    SH_FALL.draw(lt, cam, t + 10, .8)
    e = cam.scr([(920, 187)])[0]
    ek = .4 + .6 * smooth((t - 5.5) / .6)
    cv2.circle(lt, (int(e[0]), int(e[1])), int(14 / cam.s * ek), col8(WHITE, ek), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.4, 1.4)
    img = flash(img, (0.5 + 0.5 * math.sin(t * 37)) * .08 * pulse(t, 6.2, .05, .8), CYAN)
    return img


@shot(3.0)
def s_beast_roar(t, T):
    cam = cam_with_shake(910, 215, lerp(420, 340, ease_out(t / T)), 0, t, 4 + 10 * pulse(t, .4, .05, 1.2), 34)
    x, y = cam.maps()
    r = (t - .4) * 900
    if r > 0:
        x, y = shockwave(x, y, 960, 260, r, 40, 25)
    img = cv2.remap(plate("f06"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    lt = _u8()
    e = cam.scr([(920, 187)])[0]
    cv2.circle(lt, (int(e[0]), int(e[1])), 40, col8(WHITE, 1), -1, cv2.LINE_AA)
    cv2.line(lt, (int(e[0] - 700), int(e[1])), (int(e[0] + 700), int(e[1])), col8(CYAN, .8), 3, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 2, 2)
    m = cam.scr([(967, 267)])[0]
    img = zoom_blur(img, m[0], m[1], .12 * pulse(t, .4, .05, 1), 7)
    if int(t * 12) % 5 == 1 and t > .4:
        img = two_tone(img, dark=(0, .02, .05), light=(.6, 1, 1), th=.3)
    return chroma(img, .015 * pulse(t, .4, .05, 1))


@shot(3.0)
def s_beast_wide_roar(t, T):
    cam = cam_with_shake(660, 380, 1200, 0, t, 5 * (1 - t / T) + 1, 26)
    x, y = cam.maps()
    x, y = shockwave(x, y, 960, 260, t * 700, 50, 18)
    img = cv2.remap(plate("f06"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    lt = _u8()
    c = cam.scr([(960, 260)])[0]
    cv2.ellipse(lt, (int(c[0]), int(c[1])), (int(t * 700 / cam.s), int(t * 700 / cam.s * .6)), 0, 0, 360,
                col8(CYAN, (1 - t / T) * .8), 3, cv2.LINE_AA)
    SH_FALL2.draw(lt, cam, t + 9)
    return add_light(img, light_from_u8(lt))


@shot(4.0)
def s_ren_resolve(t, T):
    cam = cam_with_shake(646, 420, lerp(760, 560, ease_in(t / T)), 0, t, 1.5, 12)
    sw = [(646, 200, 300, 160, 6, .08, 10, "x", False)]
    img = render_plate("f03", cam, twos(t), sw)
    img = tint(img, (.55, .9, 1.15), .55)
    rim = .5 + .5 * math.sin(t * 9)
    img = img + np.float32(CYAN) * .08 * rim
    img = parallel_lines(img, t, -2.6, 30, (.8, 1, 1), .3, seed=14)
    lt = _u8()
    SH_FALL.draw(lt, cam, t + 4, .7)
    img = add_light(img, light_from_u8(lt))
    if t > 2.4:
        img = speed_lines(img, W / 2, H / 2 - 40, t, 70, (.28, .5), (1, 1, 1), .5 * smooth((t - 2.4) / .3), seed=15)
    return img


@shot(3.0)
def s_hana_ready(t, T):
    cam = cam_with_shake(lerp(700, 720, t / T), lerp(380, 360, t / T), lerp(860, 800, t / T), 0, t, 1, 10)
    img = render_plate("f08", cam, twos(t), SWAY_F08)
    lt = _u8()
    k = smooth(t / T)
    c = cam.scr([(950, 70)])[0]
    cv2.circle(lt, (int(c[0]), int(c[1])), int(30 + 40 * k), col8(GOLD, .3 + .5 * k), -1, cv2.LINE_AA)
    motes(lt, t, 21, 40, GOLD, (1, 3), (0, -60), .5)
    return add_light(img, light_from_u8(lt), 1.4, 1.2)


# ---- ACT 3: fight ------------------------------------------------------------


@shot(5.0)
def s_ren_leap(t, T):
    p = t / T
    cams = []
    for d in (-.02, 0, .02):
        q = ease_out(clamp01(p + d))
        cams.append(cam_with_shake(lerp(480, 640, q), lerp(520, 330, q), lerp(760, 1180, q), lerp(.08, -.03, q), t + d, 3, 16))
    img = render_mb("f07", cams, twos(t), SWAY_F07)
    img = parallel_lines(img, t, -0.65, 60, (1, 1, 1), .45, seed=17, length=(300, 1100))
    lt = _u8()
    SH_DRIFT.draw(lt, cams[1], t * 3, .9)
    img = add_light(img, light_from_u8(lt))
    return img


@shot(2.0)
def s_blade(t, T):
    cam = cam_with_shake(820, 110, 520 - 60 * t, -.04, t, 2, 20)
    img = render_plate("f07", cam)
    lt = _u8()
    k = ease_out(t / 1.0)
    a, b = np.array([707, 260.]), np.array([907, 11.])
    tip = a + (b - a) * k
    sa, sb = cam.scr([a, tip])
    cv2.line(lt, tuple(sa.astype(int)), tuple(sb.astype(int)), col8(CYAN, 1), 18, cv2.LINE_AA)
    cv2.line(lt, tuple(sa.astype(int)), tuple(sb.astype(int)), col8(WHITE, 1), 6, cv2.LINE_AA)
    cv2.circle(lt, tuple(sb.astype(int)), int(30 + 20 * math.sin(t * 30)), col8(WHITE, 1), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.6, 1.6)
    return flash(img, pulse(t, 1.0, .03, .25) * .6)


@shot(6.0)
def s_hana_barrier(t, T):
    rot = .03 * math.sin(t * .6)
    cam = cam_with_shake(lerp(660, 700, t / T), lerp(380, 340, t / T), lerp(1180, 980, ease_io(t / T)), rot, t, 1.5, 12)
    sw = [(a, b, c, d, e * 1.6, f, g * 1.5, "y" if h == "x" else h, i) for a, b, c, d, e, f, g, h, i in SWAY_F08]
    img = render_plate("f08", cam, twos(t), sw)
    lt = _u8()
    ribbons(lt, cam, twos(t), 950, 90, n=6, r0=20, r1=150 + 40 * smooth(t / 2), height=260, growth=ease_out(t / 1.5))
    motes(lt, t, 22, 70, GOLD, (1, 3), (0, -90), .6)
    img = add_light(img, light_from_u8(lt), 1.3, 1.2)
    img = img + np.float32(GOLD) * .06 * smooth(t / 2)
    return img


@shot(2.0)
def s_threads_burst(t, T):
    cam = cam_with_shake(930, 110, 560, 0, t, 3, 22)
    img = render_plate("f08", cam, twos(t), SWAY_F08)
    lt = _u8()
    ribbons(lt, cam, twos(t) + 3, 950, 90, n=6, r0=20, r1=190, height=260)
    r = np.random.default_rng(31)
    c = np.array([950, 60.])
    for i in range(16):
        a = r.uniform(-2.6, -.2)
        L = ease_out((t - .3 - i * .03) / .5) * 900
        if L <= 0: continue
        e = c + np.array([math.cos(a), math.sin(a)]) * L
        s0, s1 = cam.scr([c, e]).astype(int)
        cv2.line(lt, tuple(s0), tuple(s1), col8(GOLD if i % 2 else CYAN, 1), 4, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.6, 1.4)
    return flash(img, pulse(t, .3, .03, .3) * .5, GOLD)


@shot(4.0)
def s_bind_beast(t, T):
    cam = cam_with_shake(680, 380, 1100, 0, t, 2 + 4 * pulse(t, 2.6, .05, .8), 20)
    img = render_plate("f06", cam)
    lt = _u8()
    r = np.random.default_rng(41)
    for i in range(9):
        y0 = r.uniform(180, 600); y2 = r.uniform(180, 600)
        p0, p2 = np.array([300., y0]), np.array([1060., y2])
        p1 = np.array([680, r.uniform(80, 700)])
        curve = bezier(p0, p1, p2, 60)
        k = ease_out((t - i * .14) / 1.2)
        n = int(len(curve) * k)
        if n < 2: continue
        sp = cam.scr(curve[:n]).astype(np.int32)
        cv2.polylines(lt, [sp], False, col8(GOLD if i % 2 else CYAN, 1), 3, cv2.LINE_AA)
    e = cam.scr([(920, 187)])[0]
    cv2.circle(lt, (int(e[0]), int(e[1])), int(16 + 10 * pulse(t, 2.6, .05, .5)), col8(WHITE, 1), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.3, 1.3)
    return img


@shot(2.0)
def s_ren_charge(t, T):
    cams = [cam_with_shake(560, 380, lerp(900, 380, ease_in(clamp01((t + d) / T))), -.05, t, 4, 30) for d in (-.03, 0, .03)]
    img = render_mb("f07", cams, twos(t), SWAY_F07)
    img = speed_lines(img, W / 2, H / 2, t, 110, (.2, .45), (1, 1, 1), .75, seed=19, thick=(2, 6))
    return chroma(img, .01 * t / T)


@shot(1.0)
def s_ma(t, T):
    img = blank() + np.float32([0.01, 0.01, 0.02])
    img = speed_lines(img, W / 2, H / 2, threes(t), 140, (.1, .3), (1, 1, 1), 1.0, seed=23, thick=(1, 4))
    return img


@shot(6.0)
def s_clash(t, T):
    # 0-.25 white | .25-1 two-tone stutter | 1-3 impact w/ burst | 3-4 slow push | 4-6 second hit
    if t < .25:
        return blank() + 1
    cx, cy = 520, 400
    amp = 16 * pulse(t, .25, .02, 1.0) + 18 * pulse(t, 4.0, .02, 1.2) + 2
    w = 1280 if t < 3 else lerp(1280, 520, ease_io((t - 3) / 1.0)) if t < 4 else 640 + 40 * math.sin(t * 40)
    cam = cam_with_shake(lerp(600, cx, smooth((t - 3))), lerp(360, cy, smooth(t - 3)), w, 0, t, amp, 32)
    x, y = cam.maps()
    if t > 4:
        x, y = shockwave(x, y, cx, cy, (t - 4) * 1200, 50, 30)
    img = cv2.remap(plate("f09"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    sc = cam.scr([(cx, cy)])[0]
    img = speed_lines(img, sc[0], sc[1], t, 120, (.12, .32), (0, 0, 0), .8, seed=29)
    lt = _u8()
    tb = t - .25 if t < 4 else t - 4
    SH_BURST.draw(lt, cam, tb * (0.25 if 3 < t < 4 else 1), 1, CYAN, origin=np.array([cx, cy]), burst=1.2)
    cv2.circle(lt, (int(sc[0]), int(sc[1])), int(80 + 60 * pulse(t, 4, .03, .4)), col8(WHITE, 1), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.4, 1.4)
    img = zoom_blur(img, sc[0], sc[1], .1 * pulse(t, .25, .02, .5) + .14 * pulse(t, 4, .02, .6), 7)
    st = int(t * 12)
    if .25 <= t < 1.0 or 4.0 <= t < 4.6:
        mode = st % 3
        if mode == 0: img = two_tone(img, invert=True, th=.55)
        elif mode == 1: img = two_tone(img, dark=(.03, 0, 0), light=(.95, .1, .1), th=.5)
    img = flash(img, pulse(t, 4.0, .02, .2))
    return chroma(img, .02 * pulse(t, .25, .02, .8) + .025 * pulse(t, 4, .02, .8))


@shot(3.0)
def s_beast_fracture(t, T):
    cam = cam_with_shake(680, 390, 1000, 0, t, 6 + 8 * pulse(t, 2.2, .03, .4), 28)
    img = render_plate("f06", cam)
    lt = _u8()
    CRK_BEAST.draw(lt, cam, ease_out(t / 2.0), WHITE, 3.0, 1.0, flicker=.3, t=t)
    SH_FALL2.draw(lt, cam, t + 3)
    img = add_light(img, light_from_u8(lt), 1.6, 1.6)
    return flash(img, smooth((t - 2.3) / .5))


@shot(1.0)
def s_hana_shout(t, T):
    cam = cam_with_shake(660, 420, 700, 0, t, 3, 22)
    img = render_plate("f08", cam, twos(t), [(a, b, c, d, e * 2, f, g * 2, "y", i) for a, b, c, d, e, f, g, h, i in SWAY_F08])
    img = flash(img, (1 - smooth(t / .3)))
    img = parallel_lines(img, t, -1.57, 50, (1, .9, .6), .5, seed=31)
    return img


@shot(6.0)
def s_mirror_dive(t, T):
    p = ease_io(t / T)
    cams = [cam_with_shake(lerp(660, 590, p), lerp(170, 420, ease_io((t + d) / T)), lerp(820, 1100, p), 0, t, 1.5 + 6 * pulse(t, 2.5, .05, .6), 18) for d in (-.03, 0, .03)]
    tr = max(0, t - 2.5)

    def warp(x, y):
        below = (y > 360).astype(np.float32)
        x = x + below * 1.6 * np.sin(y * .35 + t * 6)
        if tr > 0:
            dx, dy = x - 587, (y - 360) * 3.2
            d = np.sqrt(dx * dx + dy * dy)
            env = np.exp(-((d - tr * 260) / 160) ** 2) * math.exp(-tr * .5)
            x = x + env * 6 * np.sin(d * .08 - tr * 14)
            y = y + env * 2 * np.sin(d * .08 - tr * 14)
        return x, y
    img = render_mb("f10", cams, twos(t), SWAY_F07[:0], warp)
    lt = _u8()
    cam = cams[1]
    c = cam.scr([(587, 360)])[0]
    for i in range(5):
        rr = tr * 260 - i * 70
        if rr > 0:
            a = math.exp(-tr * .7) * (1 - i * .15)
            cv2.ellipse(lt, (int(c[0]), int(c[1])), (int(rr / cam.s), int(rr / cam.s / 3.2)), 0, 0, 360, col8(CYAN, a), 2, cv2.LINE_AA)
    SH_DRIFT.draw(lt, cam, t, .8)
    img = add_light(img, light_from_u8(lt), 1.4, 1.2)
    return flash(img, pulse(t, 2.5, .04, .4) * .7)


@shot(2.0)
def s_mirror_contact(t, T):
    cam = cam_with_shake(587, 360, lerp(520, 300, ease_in(t / T)), 0, t, 2, 20)
    x, y = cam.maps()
    dx, dy = x - 587, (y - 360) * 3.2
    d = np.sqrt(dx * dx + dy * dy)
    x = x + 8 * np.sin(d * .1 - t * 18) * np.exp(-d / 300)
    img = cv2.remap(plate("f10"), x * 2, y * 2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) / 255
    lt = _u8()
    c = cam.scr([(587, 360)])[0]
    for i in range(8):
        rr = (t * 300 + i * 60) % 500
        cv2.ellipse(lt, (int(c[0]), int(c[1])), (int(rr / cam.s), int(rr / cam.s / 3.2)), 0, 0, 360, col8(CYAN, 1 - rr / 500), 2, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.5, 1.5)
    return flash(img, smooth((t - 1.2) / .8))


@shot(4.0)
def s_shatter(t, T):
    cam = cam_with_shake(680, 380, 1100, 0, t, 4 * (1 - t / T), 20)
    base = render_plate("f06", cam)
    bg = blank() + np.float32([.02, .05, .09]) + (np.float32([.05, .12, .16]) * (1 - _yy / H)[..., None])
    hide = smooth((t - .15) / .5)
    img = base * (1 - hide) + bg * hide
    lt = _u8()
    SH_BURST.draw(lt, cam, t * .6, 1 - smooth((t - 2.5) / 1.5), CYAN, origin=np.array([680, 380]), burst=1.0)
    SH_SNOW.draw(lt, cam, t, smooth((t - 1) / 2))
    img = add_light(img, light_from_u8(lt), 1.4, 1.4)
    return flash(img, 1 - smooth(t / .9))


MEM = [("f03", 646, 413, 260), ("f04", 610, 450, 330), ("f02", 650, 260, 500), ("f12", 650, 400, 600), ("f08", 670, 430, 360)]


@shot(4.0)
def s_memories(t, T):
    img = blank() + np.float32([.02, .04, .07])
    lt = _u8()
    SH_SNOW.draw(lt, Cam(640, 360, 1280), t + 4, .5)
    img = add_light(img, light_from_u8(lt))
    for i, (k, cx, cy, w) in enumerate(MEM):
        tt = t - i * .35
        if tt < 0: continue
        a = smooth(tt / .6) * smooth((T - t) / .6)
        ang = tt * .5 + i * 1.3
        sx = W * (.18 + .16 * i) + 30 * math.sin(tt)
        sy = H * (.5 + .22 * math.sin(i * 2.1)) - tt * 25
        R = 170 + 30 * (i % 2)
        tri = np.float32([[sx + R * math.cos(ang + j * 2.09), sy + R * .85 * math.sin(ang + j * 2.09)] for j in range(3)])
        src = np.float32([[cx - w / 2, cy - w / 2], [cx + w / 2, cy - w / 2], [cx, cy + w / 2]]) * 2
        M = cv2.getAffineTransform(src, tri)
        tex = cv2.warpAffine(plate(k), M, (W, H)).astype(np.float32) / 255
        m = np.zeros((H, W), np.uint8)
        cv2.fillConvexPoly(m, tri.astype(np.int32), 255, cv2.LINE_AA)
        mf = (m.astype(np.float32) / 255 * a)[..., None]
        img = img * (1 - mf) + (tex * 1.1 + np.float32(CYAN) * .1) * mf
        edge = _u8()
        cv2.polylines(edge, [tri.astype(np.int32)], True, col8(WHITE, a), 2, cv2.LINE_AA)
        img = add_light(img, light_from_u8(edge), .8, .6)
    return img


# ---- ACT 4: aftermath ---------------------------------------------------------


@shot(9.0)
def s_shard_snow(t, T):
    cam = Cam(640, lerp(380, 400, t / T), lerp(1280, 1060, ease_io(t / T)))
    img = render_plate("f11", cam, twos(t), SWAY_F11)
    # breathing: subtle shoulder rise on threes
    img = windows_layer(img, cam, "f11", t, seed=11, twinkle=.6)
    lt = _u8()
    SH_SNOW.draw(lt, cam, t, .9)
    img = add_light(img, light_from_u8(lt), 1.0, 1.0)
    fg = _u8()
    SH_SNOW_FG.draw(fg, Cam(640, 360, 1280), t)
    fgf = cv2.GaussianBlur(light_from_u8(fg), (0, 0), 7) * 2.2
    img = img + fgf
    return img * smooth(t / 1.0)


@shot(5.0)
def s_snow_close(t, T):
    cam = Cam(640, lerp(470, 460, t / T), lerp(640, 580, t / T))
    img = render_plate("f11", cam, twos(t), SWAY_F11)
    lt = _u8()
    SH_SNOW.draw(lt, cam, t + 9, .9)
    img = add_light(img, light_from_u8(lt))
    fg = _u8()
    SH_SNOW_FG.draw(fg, Cam(640, 360, 1280), t + 9)
    img = img + cv2.GaussianBlur(light_from_u8(fg), (0, 0), 9) * 2.4
    return flash(img, smooth((t - 3.6) / 1.4))


@shot(13.5)
def s_morning(t, T):
    p = ease_io(t / T)
    cam = Cam(lerp(650, 640, p), lerp(430, 360, p), lerp(760, 1280, p))
    img = render_plate("f12", cam, twos(t), SWAY_F12)
    img = draw_birds(img, cam, t, [(-40 + i * 25, 120 + i * 9, 55, -4, 5, i) for i in range(6)], col=(.15, .2, .35))
    img = haze(img, t, (1, 1, 1), .05, 6, 4)
    lt = _u8()
    sun = cam.scr([(1030, 110)])[0]
    # lens flare chain through screen centre
    cv2.circle(lt, (int(sun[0]), int(sun[1])), int(70 / cam.s), col8((1, .95, .8), .6), -1, cv2.LINE_AA)
    img = add_light(img, light_from_u8(lt), 1.1, 1.3)
    # final hook: a single cyan glint in the clear sky
    hk = pulse(t, 10.2, .1, .6)
    if hk > 0:
        g = _u8()
        q = cam.scr([(880, 160)])[0].astype(int)
        cv2.line(g, (q[0] - 40, q[1]), (q[0] + 40, q[1]), col8(CYAN, hk), 2, cv2.LINE_AA)
        cv2.line(g, (q[0], q[1] - 40), (q[0], q[1] + 40), col8(CYAN, hk), 2, cv2.LINE_AA)
        img = add_light(img, light_from_u8(g), 1.5, 1.5)
    img = flash(img, 1 - smooth(t / 1.2))
    return img * smooth((T - t) / .8)


@shot(12.0)
def s_end(t, T):
    img = blank()
    logo = text_rgba("SHARDFALL", FONT_T, 150, fill=(230, 255, 250), spacing=14)
    a = smooth((t - .5) / 1.0) * smooth((T - t) / 1.0)
    img = paste(img, logo, W / 2, H / 2 - 80, a)
    sweep = (t - 1.8) / 1.4
    if 0 < sweep < 1:
        lt = _u8()
        xs = int(lerp(300, W - 300, sweep))
        cv2.line(lt, (xs, H // 2 - 200), (xs - 120, H // 2 + 40), col8(WHITE, .7), 40)
        m = np.zeros((H, W, 1), np.float32)
        m = paste(m.repeat(3, 2), logo, W / 2, H / 2 - 80, 1)[..., :1]
        img = img + light_from_u8(lt) * (m > .3)
    img = paste(img, text_rgba("硝 子 の 空", FONT_T, 46, fill=(255, 168, 96)), W / 2, H / 2 + 40, a)
    b = smooth((t - 3) / 1.0) * smooth((T - t) / 1.0)
    for i, line in enumerate(["Story & keyframes — SHARDFALL storyboard",
                              "Reshape · animation · FX · score — rendered in code",
                              "Ren  ·  Hana  ·  The Glass Beast"]):
        img = paste(img, text_rgba(line, FONT_B, 28, fill=(162, 168, 189)), W / 2, H / 2 + 150 + i * 46, b)
    e = smooth((t - 7) / .8) * smooth((T - t) / .8)
    img = paste(img, text_rgba("次は、どこだ？", FONT_B, 40, fill=(127, 243, 230)), W / 2, H - 140, e)
    lt = _u8()
    SH_SNOW.draw(lt, Cam(640, 360, 1280), t, .35)
    return add_light(img, light_from_u8(lt))


# ---------------------------------------------------------------- timeline
STARTS = {}
_acc = 0.0
for d, fn, nm in SHOTS:
    STARTS[nm] = _acc
    _acc += d
TOTAL = _acc


def at(name, off): return STARTS[name] + off


SUBS += [
    (at("s_rooftop", 3.6), at("s_rooftop", 6.8), "…静かすぎる。", "…It's too quiet."),
    (at("s_hana_flash", 1.0), at("s_hana_smile", 2.6), "大丈夫、ふたりならね。", "We'll be fine, as long as it's both of us."),
    (at("s_ren_resolve", 2.4), at("s_ren_resolve", 3.9), "行くぞ！", "Let's go!"),
    (at("s_hana_barrier", 1.4), at("s_hana_barrier", 4.6), "結べ、光の糸！", "Bind it, threads of light!"),
    (at("s_shard_snow", 4.0), at("s_shard_snow", 7.0), "…きれい。", "…It's beautiful."),
    (at("s_morning", 6.0), at("s_morning", 9.2), "次は、どこだ？", "So, where's the next one?"),
]


def frame(i):
    g = i / FPS
    for d, fn, nm in SHOTS:
        if g < STARTS[nm] + d:
            img = fn(g - STARTS[nm], d)
            break
    else:
        img = blank()
    img = np.clip(img, 0, 1.5)
    # filmic shoulder for anything pushed past white
    img = np.where(img > .85, .85 + (1 - np.exp(-(img - .85) * 4)) * .15, img)
    img = img * VIGNETTE + (1 - VIGNETTE) * img * .0
    img = subtitles(img, g)
    img = img + GRAIN[(i // 2) % len(GRAIN)][..., None] * 0.022
    return (np.clip(img, 0, 1) * 255 + .5).astype(np.uint8)


def render(a, b, out):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(a, b):
        p.stdin.write(frame(i).tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    if sys.argv[1] == "render":
        render(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif sys.argv[1] == "still":
        cv2.imwrite(sys.argv[3], cv2.cvtColor(frame(int(float(sys.argv[2]) * FPS)), cv2.COLOR_RGB2BGR))
    elif sys.argv[1] == "info":
        print("TOTAL", TOTAL, "frames", int(round(TOTAL * FPS)))
        for d, fn, nm in SHOTS:
            print(f"{STARTS[nm]:7.2f} {d:5.2f} {nm}")
