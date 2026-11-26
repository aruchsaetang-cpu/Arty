"""Kuro Oni ep 1 prototype: rendered 3D frames (every 2nd) -> 540x960 video with captions, hit speed lines, the count, title, sound.
python3 shorts/kuro_oni/compose.py"""
import math, os, random, subprocess
from PIL import Image, ImageDraw
import proto as PR
HERE = os.path.dirname(os.path.abspath(__file__)); FR = os.path.join(HERE, "frames"); OUT = os.path.join(HERE, "out")
W, H, FPS, N = PR.W, PR.H, PR.FPS, int(os.environ.get("LAST_FRAME", PR.N)); NAME = os.environ.get("OUT_NAME", "proto3d_ep1.mp4")
def src(f):
    for k in (f, f - 1, f + 1, f - 2, f + 2, f - 3):
        p = os.path.join(FR, f"f{k:04d}.png")
        if k >= 1 and os.path.exists(p): return p
    return None
def speed_lines(img, t):
    d = ImageDraw.Draw(img, "RGBA"); r = random.Random(int(t * 30)); cx, cy = W // 2, H // 2 - 60
    for _ in range(46):
        a = r.uniform(0, math.tau); r0 = r.uniform(230, 330); r1 = r0 + r.uniform(160, 420)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=(255, 255, 255, 210), width=r.choice((2, 2, 3, 5)))
def decorate(img, t):
    d = ImageDraw.Draw(img)
    for ht in PR.BIG:
        if ht <= t < ht + 0.2: speed_lines(img, t)
    big = [h for h in (22.4, 23.2, 24.0, 24.8)]
    n = sum(1 for h in big if t >= h)
    if n and t < 25.0:
        d = ImageDraw.Draw(img); d.text((W // 2, 190), str(25 * n), font=PR.F_X, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0), anchor="mm")
    if t >= 57.3:
        a = min(1, (t - 57.3) / 0.7)
        d = ImageDraw.Draw(img); d.text((W // 2, 640), "KURO ONI", font=PR.F_X, fill=(int(245 * a),) * 3, stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
        d.text((W // 2, 720), "EP 1", font=PR.F_B, fill=(int(190 * a),) * 3, anchor="mm")
    if t >= 25.0 and t < 28.5:
        d.text((W // 2, 120), "KOREA IS ONE", font=PR.F_B, fill=(235, 220, 200), stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
    if 55 <= t < 57: d.text((W // 2, H - 170), "\"Black-eyed demon.\"", font=PR.F_B, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0), anchor="mm")
def caption(img, t):
    i, (s0, s1, title, cap) = PR.shot_of(t)
    bar = Image.new("RGBA", (W, 120), (0, 0, 0, 160)); img.paste(bar, (0, H - 120), bar); d = ImageDraw.Draw(img)
    d.text((16, H - 114), title, font=PR.F_B, fill=(255, 220, 120))
    words, line, y = cap.split(), "", H - 76
    for w_ in words:
        if d.textlength(line + w_ + " ", font=PR.F_S) > W - 32: d.text((16, y), line, font=PR.F_S, fill=(255, 255, 255)); line, y = "", y + 25
        line += w_ + " "
    d.text((16, y), line, font=PR.F_S, fill=(255, 255, 255)); d.text((W - 90, 14), f"{t:4.1f}s", font=PR.F_S, fill=(200, 200, 200))
def main():
    PR.sound()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", os.path.join(OUT, "proto_ep1.wav"), "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-t", str(N / FPS), "-movflags", "+faststart", os.path.join(OUT, NAME)], stdin=subprocess.PIPE)
    last = None
    for f in range(1, N + 1):
        t = (f - 1) / FPS; s = src(f)
        if s is None: img = Image.new("RGB", (W, H), (0, 0, 0))
        else:
            if s != last: base = Image.open(s).convert("RGB").resize((W, H), Image.LANCZOS); last = s
            img = base.copy()
        decorate(img, t); caption(img, t); p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait(); print("done")
if __name__ == "__main__": main()
