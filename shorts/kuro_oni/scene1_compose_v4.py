"""Kuro Oni ep 1, REAL SCENE 1 v4 -> out/scene1_v4.mp4: plain clean 3D render, SILENT (no audio track), 1080x1920, 30 fps, 3.0 s.
Rendered frames (frames_s1v4/f####.png, 540x960, on twos, punches on ones) are upscaled once with Real-ESRGAN
(shorts/aura/upscale.py) into frames_s1v4_hd/. No grade, no 2D effects. Only a small plain white subtitle at the bottom (no box).
    python3 shorts/kuro_oni/scene1_compose_v4.py            (STILLS=1: also write out/scene1_v4_stills/)"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
FR = os.path.join(HERE, "frames_s1v4"); HD = os.path.join(HERE, "frames_s1v4_hd"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
W, H, FPS, DUR = 1080, 1920, 30, 3.0; N = int(DUR * FPS)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SUBS = [(0.15, 1.6, "He defeated an army alone."), (1.6, 3.0, "But he never felt fulfilled.")]
def src(n):
    for f in (n, n - 1, n - 2):
        if os.path.exists(os.path.join(FR, f"f{f:04d}.png")): return f
    return None
def upscale_all():
    need = sorted({src(n) for n in range(1, N + 1)} - {None})
    todo = [f for f in need if not os.path.exists(os.path.join(HD, f"f{f:04d}.png"))]
    miss = [n for n in range(1, N + 1) if src(n) is None]
    if miss: print("MISSING renders for output frames", miss)
    if not todo: return
    os.makedirs(HD, exist_ok=True)
    sys.path.insert(0, os.path.join(ROOT, "shorts", "aura")); import torch, upscale as UP
    torch.set_num_threads(4); m = UP.model()
    for f in todo:
        UP.upscale(m, Image.open(os.path.join(FR, f"f{f:04d}.png"))).save(os.path.join(HD, f"f{f:04d}.png"), compress_level=1); print("upscaled", f, flush=True)
def frame(n):
    f = src(n); p = os.path.join(HD, f"f{f:04d}.png")
    im = Image.open(p).convert("RGB") if os.path.exists(p) else Image.open(os.path.join(FR, f"f{f:04d}.png")).convert("RGB").resize((W, H), Image.LANCZOS)
    t = (n - 1) / FPS
    for a, b, line in SUBS:
        if a <= t < b:
            d = ImageDraw.Draw(im); ft = ImageFont.truetype(FONT, 38); xy = (W // 2, H - 170)
            d.text((xy[0] + 2, xy[1] + 2), line, font=ft, fill=(0, 0, 0), anchor="mm")       # thin dark shadow only, no box
            d.text(xy, line, font=ft, fill=(255, 255, 255), anchor="mm")
    return im
def main():
    upscale_all()
    out = os.path.join(OUT, "scene1_v4.mp4")
    sd = os.path.join(OUT, "scene1_v4_stills") if os.environ.get("STILLS") else None
    if sd: os.makedirs(sd, exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-t", str(DUR), "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for n in range(1, N + 1):
        im = frame(n); p.stdin.write(im.tobytes())
        if sd and n in (8, 17, 24, 30, 33, 45, 50, 57, 64, 72, 82, 90): im.resize((540, 960), Image.LANCZOS).save(os.path.join(sd, f"o{n:02d}.png"))
    p.stdin.close(); p.wait(); print("done", out)
if __name__ == "__main__": main()
