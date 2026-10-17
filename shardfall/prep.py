"""Reshape the 12 keyframes into 2560x1440 graded plates + helper masks."""
import cv2, numpy as np, os, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src/web")
OUT = os.path.join(HERE, "plates")
os.makedirs(OUT, exist_ok=True)

NAMES = {
    "f01": "f01_city_at_dusk", "f02": "f02_rooftop_lookout", "f03": "f03_ren_closeup",
    "f04": "f04_hana_closeup", "f05": "f05_sky_cracks", "f06": "f06_glass_beast",
    "f07": "f07_ren_leaps", "f08": "f08_hana_raises_staff", "f09": "f09_clash",
    "f10": "f10_mirror_dive", "f11": "f11_shard_snow", "f12": "f12_next_morning",
}
MOOD = {"f01": "dusk", "f02": "dusk", "f03": "dusk", "f07": "dusk", "f10": "dusk",
        "f05": "night", "f06": "night", "f08": "night", "f11": "night",
        "f04": "day", "f12": "day", "f09": "impact"}

# (shadow tint, highlight tint, saturation, contrast) in RGB 0..1
GRADES = {
    "dusk":   ((0.10, 0.02, 0.22), (1.00, 0.62, 0.38), 1.18, 1.18),
    "night":  ((0.00, 0.10, 0.18), (0.55, 1.00, 0.95), 1.15, 1.22),
    "day":    ((0.05, 0.10, 0.25), (1.00, 0.93, 0.80), 1.10, 1.04),
    "impact": ((0.20, 0.05, 0.02), (1.00, 0.90, 0.70), 1.10, 1.25),
}


def fbm(h, w, seed, octaves=5):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = 2 ** (o + 2)
        n = rng.random((s * h // w + 2, s + 2)).astype(np.float32)
        acc += amp * cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= 0.55
    acc /= tot
    return (acc - acc.mean()) / (acc.std() + 1e-6)


def reshape(key):
    bgr = cv2.imread(os.path.join(SRC, NAMES[key] + ".jpg"))
    detailed = os.environ.get("DETAILED") == "1"  # painted keyframes with fine, coloured line art
    # 1. clean JPEG blocking on flat colour fields, then upscale 2x (skipped for detailed art: it would erase fine lines)
    clean = bgr if detailed else cv2.bilateralFilter(bgr, 7, 28, 5)
    up = cv2.resize(clean, (2560, 1440), interpolation=cv2.INTER_LANCZOS4)
    img = cv2.cvtColor(up, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    # 2. unsharp + ink-line punch (darken already-dark thin strokes)
    blur = cv2.GaussianBlur(img, (0, 0), 2.0)
    img = np.clip(img + (0.35 if detailed else 0.7) * (img - blur), 0, 1)
    lum = img @ np.float32([0.299, 0.587, 0.114])
    ink = np.clip((0.22 - lum) / 0.22, 0, 1)
    if not detailed:
        img *= (1 - 0.45 * ink)[..., None]
    # 3. painterly granulation: low-freq tone wobble + fine paper grain
    tex = fbm(1440, 2560, hash(key) % 1000) * 0.035 + fbm(1440, 2560, 7 + hash(key) % 99, 7) * 0.02
    img *= (1 + tex)[..., None]
    # 4. gradient light: soft top light, darker floor (ambient occlusion feel)
    yy = np.linspace(0, 1, 1440, dtype=np.float32)[:, None, None]
    img *= 1.06 - 0.16 * yy ** 1.6
    # 5. grade: contrast S-curve, saturation, split toning
    sh, hi, sat, con = GRADES[MOOD[key]]
    img = np.clip(img, 0, 1)
    img = 0.5 + (img - 0.5) * con
    img = np.clip(img, 0, 1)
    img = img * img * (3 - 2 * img) * 0.35 + img * 0.65  # gentle S
    lum = (img @ np.float32([0.299, 0.587, 0.114]))[..., None]
    img = lum + (img - lum) * sat
    w_sh = np.clip(1 - lum * 2, 0, 1)
    w_hi = np.clip(lum * 2 - 1, 0, 1)
    img = img + w_sh * (np.float32(sh) - 0.08) * 0.35 + w_hi * (np.float32(hi) - 0.8) * 0.18
    # 6. bloom on highlights
    lum = img @ np.float32([0.299, 0.587, 0.114])
    th = 0.8 if MOOD[key] == "day" else 0.62
    bright = img * np.clip((lum - th) / (1 - th), 0, 1)[..., None]
    small = cv2.resize(bright, (640, 360), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(small, (0, 0), 6) * 0.8 + cv2.GaussianBlur(small, (0, 0), 18) * 0.6
    img = img + cv2.resize(bloom, (2560, 1440)) * (0.18 if MOOD[key] == "day" else 0.55)
    img = np.clip(img, 0, 1)
    return (img * 255 + 0.5).astype(np.uint8)


def window_components(src_bgr, region_y0):
    """Lit windows: small warm/bright blobs below region_y0 (1280-space). Returns list of (x,y,w,h) at 2x."""
    hsv = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2HSV)
    v, s = hsv[..., 2], hsv[..., 1]
    m = ((v > 150) & (s < 200)).astype(np.uint8)
    m[:region_y0] = 0
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if 4 <= a <= 220 and w <= 20 and h <= 20:
            out.append((2 * x, 2 * y, 2 * w, 2 * h))
    return out


if __name__ == "__main__":
    meta = {}
    for k in NAMES:
        p = reshape(k)
        cv2.imwrite(os.path.join(OUT, k + ".png"), cv2.cvtColor(p, cv2.COLOR_RGB2BGR))
        print("plate", k)
    # f05 without its painted cracks/shards, for the crack-reveal
    bgr = cv2.imread(os.path.join(SRC, NAMES["f05"] + ".jpg"))
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    crack = ((hsv[..., 2] > 150) & (hsv[..., 1] < 170)) | ((hsv[..., 0] > 75) & (hsv[..., 0] < 100) & (hsv[..., 1] > 60) & (hsv[..., 2] > 120))
    crack[470:] = False  # keep city windows
    crack = cv2.dilate(crack.astype(np.uint8) * 255, np.ones((7, 7), np.uint8))
    clean = cv2.inpaint(bgr, crack, 9, cv2.INPAINT_TELEA)
    clean = cv2.GaussianBlur(clean, (0, 0), 1.2)
    cv2.imwrite(os.path.join(HERE, "src/f05_clean.jpg"), clean, [cv2.IMWRITE_JPEG_QUALITY, 97])
    tmp = NAMES["f05"]; NAMES["f05"] = "../f05_clean"
    p = reshape("f05"); NAMES["f05"] = tmp
    cv2.imwrite(os.path.join(OUT, "f05_clean.png"), cv2.cvtColor(p, cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(OUT, "f05_crackmask.png"), cv2.resize(crack, (2560, 1440)))
    for k, y0 in (("f01", 330), ("f02", 290), ("f11", 300), ("f05", 470), ("f10", 300)):
        meta[k + "_windows"] = window_components(cv2.imread(os.path.join(SRC, NAMES[k] + ".jpg")), y0)
        print(k, "windows", len(meta[k + "_windows"]))
    with open(os.path.join(OUT, "meta.pkl"), "wb") as f:
        pickle.dump(meta, f)
