"""Per frame: white aura from the hero mask, then the cinematic grade.  python3 shorts/aura/compose.py [first] [last]
frames/fNNNN.png + masks/mask_NNNN.png -> graded/fNNNN.png for every frame 1..N (missing frames hold the last one).
The halo sits outside the silhouette (never over the face): a tight bright edge plus a wide soft glow,
brightening when the storm freezes (keys in aura.json)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
N = json.load(open(os.path.join(HERE, "beats.json")))["frames"]
_A = json.load(open(os.path.join(HERE, "aura.json"))); KEYS = _A["keys"]; KEYS_Y = _A.get("keys_y", [[1, 0.0]])
first = int(sys.argv[1]) if len(sys.argv) > 1 else 1
last = int(sys.argv[2]) if len(sys.argv) > 2 else N
os.makedirs(os.path.join(HERE, "graded"), exist_ok=True)
AURA = np.array([0.9, 0.96, 1.0], np.float32)       # the hero: white
AURA_Y = np.array([1.0, 0.82, 0.28], np.float32)    # the narrator once he can dodge: yellow

def aura_k(f, keys=None):
    fs, vs = zip(*(keys or KEYS)); return float(np.interp(f, fs, vs))

def blur(m, r):
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255

def add_aura(a, mask, k, col=AURA):
    h, w = mask.shape; s = w / 360.0
    grown = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
    tight = np.clip(blur(grown, 2.2 * s) * 1.9, 0, 1)
    wide = np.clip(blur(grown, 9.0 * s) * 1.4, 0, 1)
    outside = 1 - np.clip(blur(mask, 0.8 * s) * 1.3, 0, 1)
    glow = (0.85 * tight + 0.55 * wide) * outside * k
    rim = np.clip(mask - np.clip(blur(mask, 1.2 * s) * 1.0 - 0.35, 0, 1), 0, 1) * 0.25 * k   # faint inner rim light
    g = np.clip(glow + rim, 0, 1.4)[..., None]
    return 1 - (1 - a) * (1 - g * col)             # screen

def grade(a):
    h, w, _ = a.shape
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    bright = np.clip((lum - 0.62) / 0.38, 0, 1)[..., None] * a
    bi = Image.fromarray((np.clip(bright, 0, 1) * 255).astype(np.uint8))
    glow = sum(np.asarray(bi.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255 * k for r, k in ((w * 0.012, 0.55), (w * 0.05, 0.45)))
    a = 1 - (1 - a) * (1 - glow * 0.55)                          # restrained bloom: light scatter, not glow
    lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    sh = np.clip(1 - lum * 2.2, 0, 1); hi = np.clip((lum - 0.55) * 2.2, 0, 1)
    warm = np.clip((a[..., :1] - a[..., 2:3]) * 3.0, 0, 1)        # keep warm street-light accents warm
    a = a + sh * np.array([-0.012, 0.004, 0.03], np.float32) \
          + hi * (1 - warm) * np.array([0.014, 0.006, 0.022], np.float32) + hi * warm * np.array([0.02, 0.01, -0.005], np.float32)
    sat = a.mean(axis=2, keepdims=True); a = sat + (a - sat) * 0.94   # controlled saturation
    a = (a - 0.5) * 1.05 + 0.5
    a = a * 0.975 + 0.012                                         # rich blacks without crushing detail
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.6 + ((yy - h / 2) / (h / 2)) ** 2)
    a = a * (1 - np.clip(r - 0.55, 0, 1)[..., None] * 0.45)
    return a                                                      # film grain is added after the upscale (finish.sh)

SHOTS = json.load(open(os.path.join(HERE, "beats.json")))["shots"]
HAND = {"follow": 1.0, "alley_pov": 0.7, "turn": 0.45, "train_mont": 0.6}     # hand-held roll amount per shot
TRAIL = json.load(open(os.path.join(HERE, "aura.json"))).get("trail", [0, -1])

def shot_of(f):
    return next((s["id"] for s in SHOTS if s["f0"] <= f <= s["f1"]), None)

def handheld(a, f, amt):
    """First-person shots: the roll a hand-held camera can't avoid (position shake is keyed in film_camera.py)."""
    u = 2 * np.pi * f / 15.0
    roll = amt * (1.3 * np.sin(u / 2 + 0.3) + 0.45 * np.sin(f * 0.9) + 0.25 * np.sin(f * 2.3 + 1))
    h, w, _ = a.shape; z = 1.07
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).rotate(roll, Image.BICUBIC)
    cw, ch_ = int(w / z), int(h / z); im = im.crop(((w - cw) // 2, (h - ch_) // 2, (w - cw) // 2 + cw, (h - ch_) // 2 + ch_))
    return np.asarray(im.resize((w, h), Image.BICUBIC), np.float32) / 255

_SHOT_STARTS = sorted(s_["f0"] for s_ in json.load(open(os.path.join(HERE, "beats.json")))["shots"])
def _shot_of(f): return sum(1 for s0 in _SHOT_STARTS if s0 <= f)
GHOSTS = []          # (frame, rgb * mask, mask) of the last ~half second: afterimages while he dodges in slow motion
GHOST_LAGS = (3, 6, 9, 13)                   # how far back each afterimage is (frames): spaced, so every side-step
GHOST_ALPHA = (0.72, 0.55, 0.4, 0.26)        # leaves distinct copies (the reference's "Ultra Instinct" dodge)
GHOST_TINT = np.array([0.62, 0.78, 1.0], np.float32)
def trail(a, m, f):
    """Afterimages: translucent blue-white copies of the hero from earlier frames, behind him, fading with age.
    Each copy is weighted by how far he has moved since (no motion -> no ghost), so they bloom on the dodges."""
    global GHOSTS
    if not (TRAIL[0] <= f <= TRAIL[1]) or m is None:
        GHOSTS = []; return a
    if GHOSTS and GHOSTS[0][1].shape != a.shape: GHOSTS = []          # (resolution changed between shots)
    GHOSTS = [g for g in GHOSTS if _shot_of(g[0]) == _shot_of(f)]       # never carry a ghost across a cut
    out = a.copy(); free = (1 - np.clip(m * 1.5, 0, 1))[..., None]    # never over the hero himself
    ys, xs = np.nonzero(m > 0.5); c_now = (xs.mean(), ys.mean()) if len(xs) else None
    hist = {g[0]: g for g in GHOSTS}
    for lag, al in zip(reversed(GHOST_LAGS), reversed(GHOST_ALPHA)):     # oldest first, newest on top
        g = hist.get(f - lag)
        if g is None or c_now is None: continue
        _, gc, gm = g; gy, gx = np.nonzero(gm > 0.5)
        if not len(gx): continue
        moved = np.hypot(gx.mean() - c_now[0], gy.mean() - c_now[1]) / (a.shape[1] / 540)   # px at 540 wide
        k = min(1.0, max(0.0, (moved - 2.0) / 10.0))                        # bloom on real side-steps
        if k <= 0: continue
        lum = (gc @ np.array([0.3, 0.55, 0.15], np.float32))[..., None]
        ghost = np.clip(0.35 * gc + 0.75 * lum * GHOST_TINT + 0.10 * GHOST_TINT, 0, 1)
        w_ = (al * k) * gm[..., None] * free
        out = out * (1 - w_) + ghost * w_
        out = 1 - (1 - out) * (1 - 0.18 * w_ * GHOST_TINT)                 # a faint glow on the copies
    GHOSTS = [g for g in GHOSTS if f - g[0] < max(GHOST_LAGS)] + [(f, a * m[..., None], m)]
    return out

prev = None
for f in range(first, last + 1):
    src = os.path.join(HERE, "frames", f"f{f:04d}.png"); dst = os.path.join(HERE, "graded", f"f{f:04d}.png")
    if not os.path.exists(src) or os.path.getsize(src) == 0:
        if prev is not None:                       # held frame (rendered on twos)
            Image.open(prev).save(dst)
        continue
    a = np.asarray(Image.open(src).convert("RGB"), np.float32) / 255
    mp = os.path.join(HERE, "masks", f"mask_{f:04d}.png"); m = None
    if os.path.exists(mp):
        mi = Image.open(mp).convert("L")
        mi = mi.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))   # close holes punched by raindrops
        m = np.asarray(mi, np.float32) / 255
        a = trail(a, m, f)
        if m.max() > 0 and aura_k(f) > 0:
            a = add_aura(a, m, aura_k(f))
    my = os.path.join(HERE, "masks_y", f"mask_{f:04d}.png")
    if os.path.exists(my) and aura_k(f, KEYS_Y) > 0:
        miy = Image.open(my).convert("L").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
        m2 = np.asarray(miy, np.float32) / 255
        if m2.max() > 0:
            a = add_aura(a, m2, aura_k(f, KEYS_Y), AURA_Y)
    sid = shot_of(f)
    if sid in HAND:
        a = handheld(a, f, HAND[sid])
    Image.fromarray((np.clip(grade(a), 0, 1) * 255).astype(np.uint8)).save(dst)
    prev = dst
print("composed", first, last)
