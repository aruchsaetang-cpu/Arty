"""Sharp upscale of the graded frames for the cel look: Real-ESRGAN animevideov3 (x4, made for anime/cel lines),
then a Lanczos resize to 1080x1920, plus the plain resize's fine detail so the rain streaks survive.
Ink lines come out crisp instead of the soft edges a plain resize leaves.

    python3 shorts/aura/upscale.py [graded_dir] [out_dir]      (default graded -> graded_hd; skips frames already done)
Weights: /root/models/realesr-animevideov3.pth (official release, github.com/xinntao/Real-ESRGAN v0.2.5.0,
sha256 b8a83768...). Runs on CPU with tiling."""
import glob, os, sys
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "graded")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "graded_hd")
W, H = 1080, 1920
DETAIL, DETAIL_SIGMA = 0.6, 1.8      # rain/texture detail put back on top of the model output
WEIGHTS = os.environ.get("ESRGAN", "/root/models/realesr-animevideov3.pth")

class SRVGGNetCompact(nn.Module):
    def __init__(self, feat=64, conv=16, scale=4):
        super().__init__()
        body = [nn.Conv2d(3, feat, 3, 1, 1), nn.PReLU(feat)]
        for _ in range(conv): body += [nn.Conv2d(feat, feat, 3, 1, 1), nn.PReLU(feat)]
        body += [nn.Conv2d(feat, 3 * scale * scale, 3, 1, 1)]
        self.body = nn.Sequential(*body); self.scale = scale
    def forward(self, x):
        return F.pixel_shuffle(self.body(x), self.scale) + F.interpolate(x, scale_factor=self.scale, mode="nearest")

URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth"
SHA = "b8a8376811077954d82ca3fcf476f1ac3da3e8a68a4f4d71363008000a18b75d"

def model():
    if not os.path.exists(WEIGHTS):                       # fetch the official release once (fresh containers)
        import hashlib, urllib.request
        os.makedirs(os.path.dirname(WEIGHTS), exist_ok=True); data = urllib.request.urlopen(URL, timeout=120).read()
        assert hashlib.sha256(data).hexdigest() == SHA, "weights checksum mismatch"
        open(WEIGHTS, "wb").write(data)
    m = SRVGGNetCompact(); sd = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    m.load_state_dict(sd.get("params", sd)); return m.eval()

@torch.inference_mode()
def upscale(m, img, tile=320, pad=12):
    x = torch.from_numpy(np.asarray(img.convert("RGB"), np.float32) / 255).permute(2, 0, 1)[None]
    _, _, h, w = x.shape; s = m.scale; out = torch.zeros(1, 3, h * s, w * s)
    for y0 in range(0, h, tile):
        for x0 in range(0, w, tile):
            ya, yb, xa, xb = max(0, y0 - pad), min(h, y0 + tile + pad), max(0, x0 - pad), min(w, x0 + tile + pad)
            o = m(x[:, :, ya:yb, xa:xb])
            ty, tx = (y0 - ya) * s, (x0 - xa) * s; th, tw = (min(h, y0 + tile) - y0) * s, (min(w, x0 + tile) - x0) * s
            out[:, :, y0 * s:y0 * s + th, x0 * s:x0 * s + tw] = o[:, :, ty:ty + th, tx:tx + tw]
    a = (out[0].clamp(0, 1).permute(1, 2, 0).numpy() * 255 + 0.5).astype(np.uint8)
    e = np.asarray(Image.fromarray(a).resize((W, H), Image.LANCZOS), np.float32)
    # the model smooths fine noise-like detail (rain streaks): add back the plain upscale's high frequencies
    l = img.convert("RGB").resize((W, H), Image.LANCZOS)
    hf = np.asarray(l, np.float32) - np.asarray(l.filter(ImageFilter.GaussianBlur(DETAIL_SIGMA)), np.float32)
    return Image.fromarray(np.clip(e + DETAIL * hf, 0, 255).astype(np.uint8))

if __name__ == "__main__":
    torch.set_num_threads(int(os.environ.get("THREADS", "4")))
    os.makedirs(DST, exist_ok=True); m = model()
    files = sorted(glob.glob(os.path.join(SRC, "*.png")))
    todo = [f for f in files if not os.path.exists(os.path.join(DST, os.path.basename(f)))]
    for k, f in enumerate(todo):
        upscale(m, Image.open(f)).save(os.path.join(DST, os.path.basename(f)), compress_level=1)
        if k % 50 == 0: print(f"{k}/{len(todo)}", flush=True)
    print("upscaled", len(todo), "frames ->", DST)
