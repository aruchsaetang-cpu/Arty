"""Hoodie prints from the channel art: white on black, like a screen print.
    python3 shorts/aura/assets/brand/make_prints.py
logo_A.png (blue badge)        -> print_chest.png : the "A" in white, its 3D side in grey, a thin white ring
banner_arty_clips.png (banner) -> print_back.png  : "ARTY CLIPS" in white, its 3D side in grey
Black outlines and the blue fills become transparent, so the black hoodie shows through as the outline."""
import os
import numpy as np
from PIL import Image, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
GREY = 120

def classify(a):
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    white = (r > 170) & (g > 170) & (b > 170)
    side = (b > 90) & (b - r > 60) & (g < 115) & ~white          # the dark-blue 3D extrusion
    return opened(white, 5), opened(side, 5)                     # drop 1-2 px anti-alias slivers

def opened(m, k):
    im = Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    return np.asarray(im) > 127

def rgba(white, side):
    out = np.zeros(white.shape + (4,), np.uint8)
    out[white] = (255, 255, 255, 255); out[side] = (GREY, GREY, GREY, 255)
    return Image.fromarray(out)

# chest: the A badge
a = np.asarray(Image.open(os.path.join(D, "logo_A.png")).convert("RGB"))
white, side = classify(a)
r, g, b = [a[..., i].astype(int) for i in range(3)]
disc = Image.fromarray(((b > 150) | white | side).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
from scipy.ndimage import binary_fill_holes
dm = binary_fill_holes(np.asarray(disc) > 0)                   # the whole badge disc (the A's black outline included)
disc = Image.fromarray(dm.astype(np.uint8) * 255)
ring = dm & ~(np.asarray(disc.filter(ImageFilter.MinFilter(17))) > 0)
img = rgba(white | ring, side & ~ring)
img = img.crop(img.getbbox()).resize((512, 512), Image.LANCZOS); img.save(os.path.join(D, "print_chest.png"))

# back: the ARTY CLIPS wordmark
a = np.asarray(Image.open(os.path.join(D, "banner_arty_clips.png")).convert("RGB"))
white, side = classify(a)
img = rgba(white, side); bb = img.getbbox(); img = img.crop(bb)
w = 1024; img = img.resize((w, round(w * img.height / img.width)), Image.LANCZOS); img.save(os.path.join(D, "print_back.png"))
print("prints:", Image.open(os.path.join(D, "print_chest.png")).size, img.size)
