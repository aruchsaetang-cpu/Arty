"""Kuro Oni ep 1, REAL SCENE 1 v3 (hook, 0-3 s, manhwa cut) -> out/scene1_v3.mp4 (1080x1920, 30 fps, drawings on twos).
Rendered panels (frames_s1v3/<shot>_<frame>.png, 540x960) + the reused v2 eyes close-up (frames_s1v2/) are upscaled once with
Real-ESRGAN (shorts/aura/upscale.py) into frames_s1v3_hd/, then every frame gets the MANHWA grade: posterised cel values,
hard black ink shadow shapes, thickened contours, halftone dots in the shadow band, a limited palette per shot with one
red accent, no grain. 2D on top (positions from frames_s1v3/proj.json, the 3D points projected per frame): speed lines with a
clean zone round the face, motion-blur smears, the enemy's snarl (brows, teeth, sweat, vein), the feather-burst impact,
blood, hollow SFX letters (퍽 / 쾅 / BAM / 쿵) cut by the frame, 3 diagonal split panels for the hit.
Every camera is fixed (no shake, no roll animation, no strobe; one 1-frame white flash at the hit).
Cuts: wide 1-16 | enemy rage ECU 17-30 | hero eyes ECU (v2) 31-40 | haymaker over the shoulder 41-51 |
3 split panels (fist / face caves / launched) 52-63 | flash + ink frame 64-65 | BAM low angle 66-73 | tumble 74-81 | aftermath 82-90.
    python3 shorts/kuro_oni/scene1_compose.py            (STILLS=1: also write out/scene1_v3_stills/)"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi
from scipy.io import wavfile
from scipy.signal import butter, sosfilt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
FR3 = os.path.join(HERE, "frames_s1v3"); FR2 = os.path.join(HERE, "frames_s1v2"); HD = os.path.join(HERE, "frames_s1v3_hd")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 1080, 1920, 30, 3.0; N = int(DUR * FPS)
F_HIT = 64; HIT = (F_HIT - 1) / FPS                     # the big hit (flash) at 2.10 s, as in v2
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
KFONT = "/usr/share/fonts/truetype/nanum/NanumSquareEB.ttf"
SUBS = [(0.15, 1.6, "He defeated an army alone."), (1.6, 3.0, "But he never felt fulfilled.")]
PJ = json.load(open(os.path.join(FR3, "proj.json"))) if os.path.exists(os.path.join(FR3, "proj.json")) else {}

# ------------------------------------------------------------------ timeline: output frame -> (shot, source frame)
def two(fs, n): return [fs[min(len(fs) - 1, i // 2)] for i in range(n)]
TL = {}
def seg(f0, shot, srcs):
    for i, s in enumerate(srcs): TL[f0 + i] = (shot, s)
seg(1, "wide", two(list(range(1, 17, 2)), 16))
seg(17, "rage", two(list(range(34, 47, 2)), 14))
seg(31, "eyes", two([43, 45, 47, 49, 51], 10))
seg(41, "swing", two([53, 55, 57, 59, 61, 63], 11))
for f in range(52, 64): TL[f] = ("panels", f)
TL[64] = ("flash", 66); TL[65] = ("inkframe", 66)
seg(66, "bam", two([66, 68, 70, 72], 8))
seg(74, "tumble", two([77, 79, 81, 82], 8))
seg(82, "after", [81, 83, 83, 85, 85, 87, 87, 89, 89])

# per-shot limited palette: (ink shadow, mid, light) + how much of the duotone replaces the render colour
PAL = {"wide": ((0.03, 0.01, 0.02), (0.55, 0.14, 0.05), (1.0, 0.86, 0.62), 0.45),
       "rage": ((0.04, 0.0, 0.0), (0.62, 0.08, 0.05), (1.0, 0.80, 0.66), 0.55),
       "eyes": ((0.02, 0.02, 0.04), (0.30, 0.30, 0.36), (0.96, 0.96, 1.0), 0.70),
       "swing": ((0.03, 0.02, 0.03), (0.42, 0.18, 0.12), (1.0, 0.88, 0.72), 0.50),
       "p_fist": ((0.02, 0.02, 0.03), (0.48, 0.30, 0.26), (1.0, 0.95, 0.88), 0.55),
       "p_face": ((0.03, 0.0, 0.01), (0.52, 0.16, 0.12), (1.0, 0.90, 0.82), 0.60),
       "p_flip": ((0.02, 0.02, 0.05), (0.34, 0.30, 0.44), (0.95, 0.94, 1.0), 0.75),
       "bam": ((0.02, 0.02, 0.04), (0.40, 0.26, 0.30), (1.0, 0.95, 0.92), 0.60),
       "tumble": ((0.03, 0.0, 0.0), (0.60, 0.07, 0.04), (1.0, 0.72, 0.50), 0.60),
       "after": ((0.03, 0.0, 0.01), (0.36, 0.04, 0.05), (0.95, 0.62, 0.48), 0.70)}

# ------------------------------------------------------------------ sources (upscaled once)
def src_path(shot, f):
    if shot == "eyes": return os.path.join(FR2, f"f{f:04d}.png")
    return os.path.join(FR3, f"{shot}_{f:04d}.png")
def upscale_all():
    need = sorted({src_path(s, f) for s, f in TL.values() if s not in ("panels", "flash", "inkframe")} |
                  {src_path(s, f) for s, fs in (("p_fist", (63,)), ("p_face", (65, 67)), ("p_flip", (72, 74)), ("bam", (66,))) for f in fs})
    os.makedirs(HD, exist_ok=True)
    todo = [p for p in need if os.path.exists(p) and not os.path.exists(hd_of(p))]
    missing = [p for p in need if not os.path.exists(p)]
    if missing: print("MISSING renders:", len(missing), [os.path.basename(m) for m in missing[:8]])
    if not todo: return
    sys.path.insert(0, os.path.join(ROOT, "shorts", "aura")); import torch, upscale as UP
    torch.set_num_threads(4); m = UP.model()
    for k, p in enumerate(todo):
        UP.upscale(m, Image.open(p)).save(hd_of(p), compress_level=1); print("upscaled", os.path.basename(p), flush=True)
def hd_of(p): return os.path.join(HD, ("v2_" if os.path.dirname(p) == FR2 else "") + os.path.basename(p))
def load(shot, f):
    p = hd_of(src_path(shot, f))
    if os.path.exists(p): return Image.open(p).convert("RGB")
    p = src_path(shot, f)
    if os.path.exists(p): return Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
    return Image.new("RGB", (W, H), (20, 10, 10))
def P(shot, f, key):
    """projected point -> pixels (x, y) in the full 1080x1920 frame, or None (behind the camera / unknown)."""
    d = PJ.get(f"{shot}_{f:04d}", {}).get(key)
    if not d or d[2] <= 0: return None
    return d[0] * W, d[1] * H

# ------------------------------------------------------------------ the manhwa grade
def sstep(a, b, x): k = np.clip((x - a) / (b - a), 0, 1); return k * k * (3 - 2 * k)
_dots = {}
def dots(period=9):
    if period not in _dots:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); u = (xx + yy) / math.sqrt(2); v = (xx - yy) / math.sqrt(2)
        _dots[period] = np.sqrt(((u % period) - period / 2) ** 2 + ((v % period) - period / 2) ** 2) / (period / 2)   # 0 centre .. ~1.4 corner
    return _dots[period]
def ink(img, shot, contour=0.10):
    a = np.asarray(img, np.float32) / 255.0
    L = a @ np.array([0.299, 0.587, 0.114], np.float32)
    gain = min(1.8, 0.88 / max(0.05, float(np.percentile(L[::4, ::4], 97.5))))     # auto-level: the lights reach paper white
    a = np.clip(a * gain, 0, 1); L = np.clip(L * gain, 0, 1); Lb = ndi.gaussian_filter(L, 1.6)
    # value bands (painterly cel): ink | deep shadow | shadow | mid | light, with tight soft edges
    edges = (0.07, 0.17, 0.33, 0.56); vals = (0.0, 0.17, 0.38, 0.62, 0.92)
    Lq = np.full_like(Lb, vals[0])
    for e, v0, v1 in zip(edges, vals, vals[1:]): Lq += (v1 - v0) * sstep(e - 0.012, e + 0.012, Lb)
    chroma = np.clip(a / (L[..., None] + 0.03), 0, 3.0)
    col = np.clip(chroma * Lq[..., None], 0, 1)
    sh, md, li, mixk = PAL[shot]
    sh, md, li = (np.array(c, np.float32) for c in (sh, md, li))
    k1 = np.clip(Lq / 0.5, 0, 1)[..., None]; k2 = np.clip((Lq - 0.5) / 0.34, 0, 1)[..., None]
    duo = np.where(Lq[..., None] < 0.5, sh + (md - sh) * k1, md + (li - md) * k2)
    col = col * (1 - mixk) + duo * mixk
    # the red accent survives the palette (blood, the red jacket, fire cores)
    red = np.clip((a[..., 0] - np.maximum(a[..., 1], a[..., 2]) * 1.6 - 0.05) * 5.0, 0, 1)[..., None]
    col = col * (1 - red) + np.clip(np.stack([a[..., 0] * 1.15, a[..., 1] * 0.55, a[..., 2] * 0.5], -1) * (0.6 + 0.6 * Lq[..., None]), 0, 1) * red
    # halftone in the shadow band
    tone = sstep(0.17, 0.07, Lb) * (Lb > 0.07) * (Lb < 0.17)
    hd = dots() < np.sqrt(np.clip(tone, 0, 1)) * 0.9
    col = col * (1 - 0.45 * hd[..., None])
    # hard black ink shadow shapes (blobby, from the blurred value) + thick contours
    inkm = Lb < 0.07
    gx = ndi.sobel(Lb, 1); gy = ndi.sobel(Lb, 0); g = np.hypot(gx, gy)
    edge = ndi.binary_dilation(g > contour * 4, iterations=1)
    col[inkm] = sh * 0.6
    col = col * (1 - 0.9 * edge[..., None])
    # paper-white highlights, punchy curve
    col = np.where(Lb[..., None] > 0.82, np.maximum(col, 0.96), col)
    col = np.clip((col - 0.5) * 1.08 + 0.5, 0, 1)
    return Image.fromarray((col * 255).astype(np.uint8))
_cache = {}
def graded(shot, f):
    k = (shot, f)
    if k not in _cache:
        if len(_cache) > 24: _cache.pop(next(iter(_cache)))
        _cache[k] = ink(load(shot, f), shot)
    return _cache[k].copy()

# ------------------------------------------------------------------ 2D drawing
def clean_alpha(x, y, c, r):
    if c is None: return 1.0
    return float(np.clip((math.hypot(x - c[0], y - c[1]) - r) / (0.35 * r), 0, 1))
def speed_parallel(img, ang, seed, n=260, focus=None, rclean=260, col=(0, 0, 0), alpha=210, width=(1, 6)):
    """dense parallel streaks over the whole panel, none inside the clean zone round the focus."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); r = random.Random(seed)
    ca, sa = math.cos(ang), math.sin(ang); Wd, Hd = img.size; diag = math.hypot(Wd, Hd)
    for _ in range(n):
        off = r.uniform(-diag / 2, diag / 2); along = r.uniform(-diag / 2, diag / 2); ln = r.uniform(120, 700)
        cx, cy = Wd / 2 - sa * off + ca * along, Hd / 2 + ca * off + sa * along
        x0, y0, x1, y1 = cx - ca * ln / 2, cy - sa * ln / 2, cx + ca * ln / 2, cy + sa * ln / 2
        segs = 8
        for k in range(segs):          # fade the line where it crosses the clean zone
            u0, u1 = k / segs, (k + 1) / segs; xa, ya = x0 + (x1 - x0) * u0, y0 + (y1 - y0) * u0; xb, yb = x0 + (x1 - x0) * u1, y0 + (y1 - y0) * u1
            ak = clean_alpha((xa + xb) / 2, (ya + yb) / 2, focus, rclean)
            taper = math.sin(math.pi * (u0 + u1) / 2) ** 0.5
            if ak > 0.02: d.line([(xa, ya), (xb, yb)], fill=col + (int(alpha * ak * taper),), width=r.randint(*width))
    img.paste(lay, (0, 0), lay)
def speed_radial(img, c, seed, n=180, r0=240, col=(0, 0, 0), alpha=220):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); r = random.Random(seed); Wd, Hd = img.size
    for _ in range(n):
        a = r.uniform(0, math.tau); a0 = r0 * r.uniform(1.0, 1.6); a1 = a0 + r.uniform(300, 1500); w = r.choice((2, 3, 4, 6, 9))
        p0 = (c[0] + a0 * math.cos(a), c[1] + a0 * math.sin(a)); p1 = (c[0] + a1 * math.cos(a), c[1] + a1 * math.sin(a))
        da = w / max(a0, 1) * 0.6        # wedge: thin at the inner end, wider outside (inked taper)
        p2 = (c[0] + a1 * math.cos(a + da * 3), c[1] + a1 * math.sin(a + da * 3))
        d.polygon([p0, p1, p2], fill=col + (alpha,))
    img.paste(lay, (0, 0), lay)
def smear(img, ang, length, focus=None, rclean=300, steps=10):
    """directional motion blur of the panel itself, kept off the clean zone."""
    a = np.asarray(img, np.float32); acc = np.zeros_like(a)
    for k in range(steps):
        s = length * k / steps; acc += np.roll(a, (int(round(math.sin(ang) * s)), int(round(math.cos(ang) * s))), (0, 1))
    acc /= steps
    if focus is not None:
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        m = np.clip((np.hypot(xx - focus[0], yy - focus[1]) - rclean) / (0.6 * rclean), 0, 1)[..., None]
    else: m = 1.0
    return Image.fromarray((a * (1 - m) + acc * m).astype(np.uint8))
def burst(img, c, seed, R=900, r0=150, protect=True):
    """white-blue feather/shatter burst behind the hit: jagged spikes from round the face; dark ink figures stay in front."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); r = random.Random(seed)
    for layer, (fill, scale) in enumerate((((150, 190, 255, 255), 1.0), ((225, 238, 255, 255), 0.82), ((255, 255, 255, 255), 0.62))):
        for _ in range(70):
            a = r.uniform(0, math.tau); ln = R * scale * r.uniform(0.35, 1.0); wd = r.uniform(0.03, 0.12)
            p = [(c[0] + r0 * 0.6 * math.cos(a - wd * 2), c[1] + r0 * 0.6 * math.sin(a - wd * 2)),
                 (c[0] + ln * math.cos(a), c[1] + ln * math.sin(a)),
                 (c[0] + ln * 0.55 * math.cos(a + wd), c[1] + ln * 0.55 * math.sin(a + wd)),
                 (c[0] + ln * 0.75 * math.cos(a + wd * 1.6), c[1] + ln * 0.75 * math.sin(a + wd * 1.6)),
                 (c[0] + r0 * 0.6 * math.cos(a + wd * 2.5), c[1] + r0 * 0.6 * math.sin(a + wd * 2.5))]
            d.polygon(p, fill=fill, outline=(20, 30, 60, 255) if layer == 0 else None)
    if protect:      # keep the dark ink figures in front of the burst; a clean core so the face reads
        L = np.asarray(img.convert("L"), np.float32) / 255.0
        al = np.asarray(lay.split()[3], np.float32) / 255.0 * np.clip((L - 0.10) / 0.18, 0, 1)
        yy, xx = np.mgrid[0:img.size[1], 0:img.size[0]]
        al *= np.clip((np.hypot(xx - c[0], yy - c[1]) - r0) / 60.0, 0, 1)
        lay.putalpha(Image.fromarray((al * 255).astype(np.uint8)))
    img.paste(lay, (0, 0), lay)
def blood(img, c, ang, seed, n=90, spread=0.7, reach=520, size=1.0, alpha=255):
    """splatter + droplets thrown from c along ang (ink-dark red, a few teardrop streaks)."""
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(seed)
    for _ in range(n):
        a = ang + r.gauss(0, spread); rr = abs(r.gauss(0, reach * 0.45)) + 20; sz = r.choice((3, 4, 5, 7, 9, 12, 16)) * size
        x, y = c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)
        colr = (r.randint(95, 140), 0, r.randint(6, 16), alpha)
        if sz > 8 and r.random() < 0.5:   # teardrop streak along the throw
            tx, ty = x - math.cos(a) * sz * 2.6, y - math.sin(a) * sz * 2.6
            d.polygon([(x + math.sin(a) * sz * 0.6, y - math.cos(a) * sz * 0.6), (tx, ty), (x - math.sin(a) * sz * 0.6, y + math.cos(a) * sz * 0.6)], fill=colr)
        d.ellipse([x - sz, y - sz * 0.85, x + sz, y + sz * 0.85], fill=colr)
    for _ in range(int(n * 0.6)):           # fine mist
        a = ang + r.gauss(0, spread * 1.3); rr = abs(r.gauss(0, reach * 0.6)) + 10; x, y = c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(120, 0, 10, int(alpha * 0.8)))
def sfx(img, text, x, y, size, rot, seed=0, font=KFONT, fill=(255, 255, 255), echo=True):
    """big hollow manhwa sound word: white letters, thick black outline, speed echo behind; may run off the frame."""
    f = ImageFont.truetype(font, size); pad = size
    tw, th = ImageDraw.Draw(img).textbbox((0, 0), text, font=f)[2:]
    lay = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if echo:
        for k in (3, 2, 1):
            d.text((pad - k * size * 0.05, pad + k * size * 0.035), text, font=f, fill=(0, 0, 0, 90 - k * 20), stroke_width=int(size * 0.06), stroke_fill=(0, 0, 0, 90 - k * 20))
    d.text((pad, pad), text, font=f, fill=(0, 0, 0, 255), stroke_width=int(size * 0.085), stroke_fill=(0, 0, 0, 255))
    d.text((pad, pad), text, font=f, fill=fill + (255,), stroke_width=int(size * 0.03), stroke_fill=(255, 255, 255, 255))
    d.text((pad, pad), text, font=f, fill=fill + (255,))
    # inked inner slashes (the hand-drawn feel)
    r = random.Random(seed); m = Image.new("L", lay.size, 0); ImageDraw.Draw(m).text((pad, pad), text, font=f, fill=255)
    sl = Image.new("RGBA", lay.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sl)
    for _ in range(2 if font == FONT else 0):
        yy = r.uniform(pad, pad + th); ds.line([(pad, yy), (pad + tw, yy + r.uniform(-30, 30))], fill=(0, 0, 0, 255), width=max(2, size // 40))
    sl.putalpha(Image.fromarray(np.minimum(np.asarray(sl.split()[3]), np.asarray(m.filter(ImageFilter.MinFilter(9))))))
    lay.alpha_composite(sl)
    lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(lay, (int(x - lay.width / 2), int(y - lay.height / 2)), lay)
def narration(img, t):
    for a, b, line in SUBS:
        if a <= t < b:
            f = ImageFont.truetype(FONT, 46); d = ImageDraw.Draw(img)
            x0, y0, x1, y1 = d.textbbox((W // 2, H - 250), line, font=f, anchor="mm")
            d.rectangle([x0 - 34, y0 - 24, x1 + 34, y1 + 24], fill=(250, 248, 244), outline=(0, 0, 0), width=5)
            d.text((W // 2, H - 250), line, font=f, fill=(10, 10, 10), anchor="mm")

# ------------------------------------------------------------------ the enemy's snarl (the rig has no face shapes: drawn on,
# placed from his projected eyes and mouth so it rides the head)
def snarl(img, shot, f):
    el, er, mo = P(shot, f, "ae_l"), P(shot, f, "ae_r"), P(shot, f, "mouth")
    if not (el and er and mo): return
    el, er = np.array(el), np.array(er)
    if el[0] > er[0]: el, er = er, el
    em = (el + er) / 2; dvec = er - el; D = np.linalg.norm(dvec); ex = dvec / D
    ey = np.array([-ex[1], ex[0]]); ey = ey if ey[1] > 0 else -ey      # down the face (the faces are near upright in frame)
    mo = em + ey * 1.27 * D                                             # the lips sit ~1.27 eye-spacings under the eyes
    def pt(p, u, v): return tuple(p + ex * u * D + ey * v * D)
    d = ImageDraw.Draw(img, "RGBA")
    # brows: heavy black wedges, inner ends low and pinched toward the nose
    for side, e in ((-1, el), (1, er)):
        inner, outer = -side, side
        poly = [pt(e, inner * 0.30, -0.22), pt(e, outer * 0.42, -0.62), pt(e, outer * 0.48, -0.48), pt(e, inner * 0.26, -0.08)]
        d.polygon(poly, fill=(8, 4, 4, 255))
        # glaring eye: hard upper lid line slanting down to the nose, a small white eye with a pin pupil
        d.polygon([pt(e, inner * 0.26, -0.02), pt(e, outer * 0.36, -0.24), pt(e, outer * 0.40, -0.14), pt(e, inner * 0.24, 0.06)], fill=(5, 3, 3, 255))
        # under-eye ink hatching
        for k in range(4):
            a0 = pt(e, outer * (0.05 + 0.08 * k), 0.20); a1 = pt(e, outer * (0.12 + 0.08 * k), 0.34)
            d.line([a0, a1], fill=(10, 4, 4, 200), width=max(2, int(D * 0.02)))
    # forehead crease between the brows
    d.line([pt(em, -0.05, -0.30), pt(em, -0.02, -0.12)], fill=(10, 4, 4, 230), width=max(2, int(D * 0.03)))
    d.line([pt(em, 0.06, -0.32), pt(em, 0.03, -0.12)], fill=(10, 4, 4, 230), width=max(2, int(D * 0.03)))
    # gritted teeth: a wide snarl, upper and lower rows clenched, gums at the corners, heavy outline
    m0 = mo + ey * 0.02 * D
    outline = [pt(m0, -0.55, 0.04), pt(m0, -0.30, -0.14), pt(m0, 0.0, -0.17), pt(m0, 0.30, -0.14), pt(m0, 0.55, 0.04),
               pt(m0, 0.34, 0.19), pt(m0, 0.0, 0.22), pt(m0, -0.34, 0.19)]
    d.polygon(outline, fill=(120, 20, 22, 255))
    teeth = [pt(m0, -0.47, 0.03), pt(m0, -0.28, -0.10), pt(m0, 0.0, -0.12), pt(m0, 0.28, -0.10), pt(m0, 0.47, 0.03),
             pt(m0, 0.30, 0.14), pt(m0, 0.0, 0.16), pt(m0, -0.30, 0.14)]
    d.polygon(teeth, fill=(240, 236, 226, 255))
    d.line([pt(m0, -0.47, 0.03), pt(m0, 0.0, 0.02), pt(m0, 0.47, 0.03)], fill=(0, 0, 0, 255), width=max(3, int(D * 0.03)))
    for k in range(-4, 5):
        u = k * 0.10; d.line([pt(m0, u, -0.10 + abs(u) * 0.05), pt(m0, u * 1.02, 0.14 - abs(u) * 0.05)], fill=(0, 0, 0, 255), width=max(2, int(D * 0.018)))
    d.polygon(outline, outline=(0, 0, 0, 255)); d.line(outline + [outline[0]], fill=(0, 0, 0, 255), width=max(4, int(D * 0.045)))
    # snarl folds: nose-to-mouth lines
    for s in (-1, 1): d.line([pt(m0, s * 0.30, -0.55), pt(m0, s * 0.58, -0.10), pt(m0, s * 0.62, 0.12)], fill=(10, 4, 4, 230), width=max(3, int(D * 0.035)))
    # scar over the left brow, sweat drops at the temples, a pulsing vein
    d.line([pt(el, -0.45, 0.35), pt(el, -0.15, 0.75)], fill=(150, 70, 70, 255), width=max(4, int(D * 0.05)))     # old scar on the cheek
    d.line([pt(el, -0.45, 0.35), pt(el, -0.15, 0.75)], fill=(30, 8, 8, 255), width=max(1, int(D * 0.012)))
    rs = random.Random(f)
    for (u, v, s) in ((1.02, -0.45, 0.13), (1.10, 0.05, 0.10), (-0.60, -0.95, 0.09)):
        c = np.array(pt(em, u, v + 0.02 * (f % 4) / 2)); s *= D
        drop = [tuple(c + ey * -s * 1.6), tuple(c + ex * s * 0.8), tuple(c + ey * s * 0.9), tuple(c - ex * s * 0.8)]
        d.polygon(drop, fill=(225, 240, 255, 235), outline=(20, 30, 60, 255))
        d.ellipse([c[0] - s * 0.25, c[1] - s * 0.2, c[0], c[1] + s * 0.05], fill=(255, 255, 255, 255))
    v0 = np.array(pt(er, 0.55, -0.85)); d.line([tuple(v0), pt(er, 0.72, -0.62), pt(er, 0.66, -0.42)], fill=(90, 10, 14, 230), width=max(3, int(D * 0.04)))
    d.line([pt(er, 0.72, -0.62), pt(er, 0.90, -0.55)], fill=(90, 10, 14, 230), width=max(2, int(D * 0.03)))

# ------------------------------------------------------------------ panels page (3 diagonal cuts)
PANELS = [[(0, 0), (W, 0), (W, 820), (0, 960)],
          [(0, 1000), (W, 860), (W, 1330), (0, 1470)],
          [(0, 1510), (W, 1370), (W, H), (0, H)]]
def panel_img(shot, f, poly, focus_key, zoom=1.0, fx=None):
    """the shot, graded, cropped round its focus point to cover the panel's bounding box."""
    im = graded(shot, f); xs = [p[0] for p in poly]; ys = [p[1] for p in poly]; bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    pts = [P(shot, f, k) for k in (focus_key if isinstance(focus_key, tuple) else (focus_key,))]; pts = [q for q in pts if q]
    c = (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts)) if pts else (W / 2, H / 2)
    cw, ch = bw / zoom, bh / zoom
    if cw > W or ch > H:                       # zoomed out past the frame: extend the edges (the panel stays full)
        px, py = int(max(0, cw - W) / 2) + 2, int(max(0, ch - H) / 2) + 2
        im = Image.fromarray(np.pad(np.asarray(im), ((py, py), (px, px), (0, 0)), mode="edge")); c = (c[0] + px, c[1] + py)
    Wi, Hi = im.size; x0 = min(max(c[0] - cw / 2, 0), Wi - cw); y0 = min(max(c[1] - ch / 2, 0), Hi - ch)
    crop = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((bw, bh), Image.LANCZOS)
    focus = ((c[0] - x0) * zoom, (c[1] - y0) * zoom)
    if fx: crop = fx(crop, focus)
    return crop, (min(xs), min(ys))
def page(f):
    img = Image.new("RGB", (W, H), (248, 246, 242)); d = ImageDraw.Draw(img)
    k = f - 52
    def fist_fx(im, c):
        speed_radial(im, c, 5 + f, 110, 330, (0, 0, 0), 170); return im
    def face_fx(im, c):
        burst(im, c, 9, R=700, r0=120); blood(im, c, -0.4, 17 + k, 70, 0.6, 380); speed_radial(im, c, 31, 90, 240); return im
    def flip_fx(im, c):
        speed_parallel(im, -2.4, 40 + f // 2, 150, c, 260, (0, 0, 0), 170, (1, 4)); blood(im, c, 2.0, 55, 50, 0.5, 300, 0.8); return im
    specs = [("p_fist", 63, ("fist", "he_l"), 0.82 if k < 2 else 1.0, fist_fx), ("p_face", 65 if k < 6 else 67, "face", 1.15, face_fx),
             ("p_flip", 72 if k < 10 else 74, ("ahead", "att_hip"), 1.0, flip_fx)]
    shown = 1 + (k >= 4) + (k >= 8)
    for i, (shot, sf, key, z, fx) in enumerate(specs[:shown]):
        poly = PANELS[i]; im, o = panel_img(shot, sf, poly, key, z, fx)
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
        full = Image.new("RGB", (W, H)); full.paste(im, o); img.paste(full, (0, 0), m)
        d.line(poly + [poly[0]], fill=(0, 0, 0), width=8)
    # the words, cut by the panel edges
    if shown >= 1: sfx(img, "슉", 860, 120, 230, 12, 1)
    if shown >= 2: sfx(img, "퍽", 150, 1150, 300, -14, 2)
    if shown >= 3: sfx(img, "BAM", 760, 1800, 250, 10, 3, font=FONT)
    return img

# ------------------------------------------------------------------ frames
def frame(f):
    shot, sf = TL[f]; t = (f - 1) / FPS
    if shot == "panels": img = page(f)
    elif shot == "flash":                       # the one white flash: paper white, the burst inked in negative
        img = Image.new("RGB", (W, H), (255, 255, 255)); c = P("bam", 66, "face") or (W * 0.6, H * 0.35)
        speed_radial(img, c, 77, 220, 150, (0, 0, 0), 255)
    elif shot == "inkframe":                    # ink impact frame: the BAM shot as pure black/white shapes
        g = np.asarray(graded("bam", 66).convert("L"), np.float32); im = Image.fromarray(np.where(g < 70, 0, 255).astype(np.uint8)).convert("RGB")
        c = P("bam", 66, "face") or (W * 0.6, H * 0.35); speed_radial(im, c, 78, 200, 200, (0, 0, 0), 255); img = im
        sfx(img, "퍽", c[0] + 60, c[1] + 330, 520, -10, 4)
    else:
        img = graded(shot, sf)
        if shot == "wide":
            pass
        elif shot == "rage":
            snarl(img, shot, sf); speed_parallel(img, -1.05, 3 + sf // 2, 120, P(shot, sf, "mouth"), 420, (0, 0, 0), 120, (1, 3))
        elif shot == "eyes":
            c = (W / 2, H * 0.45); speed_radial(img, c, 12, 90, 520, (255, 255, 255), 120)
        elif shot == "swing":
            c = P(shot, sf, "ahead") or (W * 0.6, H * 0.4)
            speed_parallel(img, 0.18, 20 + sf, 160, c, 300, (0, 0, 0), 170, (1, 4))
            if sf >= 57: sfx(img, "휙", W * 0.18, H * 0.16, 200, 8, 5)
        elif shot == "bam":
            c = P(shot, sf, "face") or (W * 0.62, H * 0.32); k = (f - 66) / 8
            burst(img, c, 21 + sf, R=900 * (0.8 + 0.3 * k), r0=170)
            img = smear(img, math.atan2(c[1] - H, c[0] - W * 0.2), 50, c, 380)
            blood(img, c, -0.35, 70 + sf, 120, 0.55, 520 + 500 * k, 1.2)
            speed_radial(img, c, 90 + sf, 120, 420, (0, 0, 0), 200)
            sfx(img, "퍽", W * 0.84, H * 0.60, 400, -12, 6); sfx(img, "BAM", W * 0.30, H * 0.13, 240, 8, 7, font=FONT)
        elif shot == "tumble":
            c = P(shot, sf, "att_hip") or (W / 2, H * 0.4)
            speed_parallel(img, -0.95, 50 + sf, 240, c, 300, (20, 0, 0), 190, (1, 5))
            blood(img, P(shot, sf, "mouth") or c, 2.6, 80 + sf, 70, 0.45, 420, 1.1)
            if f < 78: sfx(img, "쾅", W * 0.83, H * 0.82, 300, 16, 8)
        elif shot == "after":
            c = P(shot, sf, "att_hip")
            if c and sf in (83, 85):             # dust kick where the body slams (inked strokes, not a glow)
                d = ImageDraw.Draw(img, "RGBA"); r = random.Random(sf)
                for _ in range(26):
                    a = r.uniform(math.pi * 0.9, math.pi * 2.1); rr = r.uniform(60, 220) * (1 if sf == 83 else 1.5)
                    x, y = c[0] + rr * math.cos(a), c[1] + rr * 0.35 * math.sin(a); d.arc([x - 30, y - 18, x + 30, y + 18], 180, 330, fill=(30, 10, 10, 200), width=4)
                sfx(img, "쿵", c[0] + 230, c[1] - 260, 220, -8, 9)
    if shot not in ("flash", "inkframe"): narration(img, t)
    return img

# ------------------------------------------------------------------ sound (v2 bed + hits, retimed to the v3 cut, + paper rips)
SR = 44100
def sound(path):
    n = int(DUR * SR); L = np.zeros(n); R = np.zeros(n); rng = np.random.default_rng(5)
    def add(x, at, g=1.0, pan=0.0):
        i = int(at * SR); x = x[: max(0, n - i)]; L[i:i + len(x)] += x * g * (1 - pan); R[i:i + len(x)] += x * g * (1 + pan)
    def tt(d): return np.arange(int(d * SR)) / SR
    def lp(x, fc): return sosfilt(butter(2, fc, "lowpass", fs=SR, output="sos"), x)
    def bp(x, a, b): return sosfilt(butter(2, [a, b], "bandpass", fs=SR, output="sos"), x)
    def T(f): return (f - 1) / FPS
    tm = np.arange(n) / SR
    env = np.interp(tm, [0, 1.0, 1.5, 1.62, T(52), HIT, HIT + 0.05, 2.5, 3.0], [0.9, 0.9, 0.6, 0.15, 0.1, 0.1, 0.25, 0.75, 0.9])
    roar = lp(rng.standard_normal(n), 140) * 0.9 * (1 + 0.3 * np.sin(tm * 2.1))
    wind = bp(rng.standard_normal(n), 250, 900) * 0.035 * (1 + 0.5 * np.sin(tm * 1.3 + 1))
    cr = np.zeros(n)
    for at in rng.uniform(0, DUR, int(60 * DUR)): cr[int(at * SR)] += rng.uniform(0.3, 1.0) * rng.choice((-1, 1))
    cr = bp(cr, 700, 7000) * 3.5
    pops = np.zeros(n)
    for at in rng.uniform(0, DUR, 7): i = int(at * SR); k = tt(0.04); pops[i:i + len(k)] += (rng.standard_normal(len(k)) * np.exp(-k * 90))[: n - i]
    bed = roar + wind + cr + bp(pops, 300, 4000) * 0.6
    L += bed * env; R += np.roll(bed, 1300) * env
    t_ = tt(0.5); add(np.sin(2 * np.pi * 44 * t_) * np.minimum(1, t_ / 0.3) * np.minimum(1, (0.5 - t_) / 0.04) * 0.3, T(17))     # fear drone (rage)
    t_ = tt(0.6); add(lp(rng.standard_normal(len(t_)), 300) * np.sin(np.pi * t_ / 0.6) * 0.25, T(17), 0.8)                         # his growl breath
    t_ = tt(0.25); w = bp(rng.standard_normal(len(t_)), 400, 2200) * np.sin(np.pi * t_ / 0.25) ** 2 * 0.45; add(w, T(43), 1.0, -0.4)   # haymaker whoosh
    t_ = tt(0.1); add(bp(rng.standard_normal(len(t_)), 900, 4000) * np.sin(np.pi * t_ / 0.1) ** 2 * 0.35, T(52), 1.0, 0.3)          # punch whoosh
    def rip(at, g):                                                                                                                 # paper rip per panel
        t_ = tt(0.13); am = (rng.random(len(t_)) < 0.35) * 1.0; am = lp(am, 900)
        add(bp(rng.standard_normal(len(t_)), 1500, 9000) * am * np.exp(-t_ * 14) * 1.6, at, g, rng.uniform(-0.3, 0.3))
    for fr in (52, 56, 60): rip(T(fr), 0.8)
    t_ = tt(0.12); add(bp(rng.standard_normal(len(t_)), 2500, 10000) * np.exp(-t_ * 45) * 1.0, T(56), 0.6)                         # first crack (face caves)
    t_ = tt(0.18); add(bp(rng.standard_normal(len(t_)), 400, 2000) * np.exp(-t_ * 30) * 0.9, T(56) + 0.01, 0.6)                     # wet crunch
    # the big hit on the flash: sub drop, body thud, crack, a paper-tear accent
    t_ = tt(1.0); fq = 32 + 130 * np.exp(-t_ * 18); add(np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-t_ * 3.5), HIT, 1.3)
    t_ = tt(0.3); add(np.sin(2 * np.pi * 78 * t_) * np.exp(-t_ * 16) + lp(rng.standard_normal(len(t_)), 600) * np.exp(-t_ * 25) * 0.8, HIT, 1.0)
    t_ = tt(0.12); add(bp(rng.standard_normal(len(t_)), 2500, 10000) * np.exp(-t_ * 45) * 1.2, HIT, 0.7)
    rip(HIT + 0.005, 1.0)
    t_ = tt(0.3); add(bp(rng.standard_normal(len(t_)), 300, 1500) * np.sin(np.pi * t_ / 0.3) * 0.3, T(74), 0.8, 0.4)               # body flies (air)
    t_ = tt(0.4); add(np.sin(2 * np.pi * 60 * t_) * np.exp(-t_ * 12) * 0.8 + lp(rng.standard_normal(len(t_)), 400) * np.exp(-t_ * 18) * 0.6, T(83), 0.9)   # slam
    t_ = tt(0.25); add(bp(rng.standard_normal(len(t_)), 800, 3000) * np.exp(-t_ * 10) * 0.15, T(83) + 0.03, 0.8)
    m = np.stack([L, R], 1); m = np.tanh(m * 1.1); m /= max(1e-9, np.abs(m).max()) / 0.9
    wavfile.write(path, SR, (m * 32767).astype(np.int16))

def main():
    upscale_all()
    wav = os.path.join(OUT, "scene1_v3.wav"); sound(wav)
    out = os.path.join(OUT, "scene1_v3.mp4")
    sd = os.path.join(OUT, "scene1_v3_stills") if os.environ.get("STILLS") else None
    if sd: os.makedirs(sd, exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", wav, "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(1, N + 1):
        im = frame(f); p.stdin.write(im.tobytes())
        if sd and f in (8, 20, 26, 35, 45, 49, 55, 59, 63, 64, 65, 67, 71, 75, 79, 83, 88): im.resize((540, 960), Image.LANCZOS).save(os.path.join(sd, f"o{f:02d}.png"))
    p.stdin.close(); p.wait(); print("done", out)
if __name__ == "__main__": main()
