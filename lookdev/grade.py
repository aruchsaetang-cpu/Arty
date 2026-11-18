"""Cinematic finish for a render: bloom, teal/magenta split-tone, vignette, fine grain.

    python3 lookdev/grade.py in.png out.png
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(np.float32) / 255.0
h, w, _ = a.shape

# bloom: bright pass, two blur radii, screen-added
lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
bright = np.clip((lum - 0.62) / 0.38, 0, 1)[..., None] * a
bi = Image.fromarray((bright * 255).astype(np.uint8))
glow = sum(np.asarray(bi.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0 * k
           for r, k in ((w * 0.012, 0.55), (w * 0.05, 0.45)))
a = 1 - (1 - a) * (1 - glow * 0.9)

# split tone: shadows toward teal, highlights toward warm-white, a touch of magenta in mids
lum = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
sh = np.clip(1 - lum * 2.2, 0, 1); hi = np.clip((lum - 0.55) * 2.2, 0, 1)
a = a + sh * np.array([-0.02, 0.025, 0.045]) + hi * np.array([0.03, 0.015, -0.01])
a = (a - 0.5) * 1.06 + 0.5                       # gentle contrast

# vignette + grain
yy, xx = np.mgrid[0:h, 0:w]
r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.6 + ((yy - h / 2) / (h / 2)) ** 2)
a = a * (1 - np.clip(r - 0.55, 0, 1)[..., None] * 0.45)
a = a + np.random.default_rng(1).normal(0, 0.012, a.shape)
Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(dst)
print("WROTE", dst)
