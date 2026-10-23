#!/usr/bin/env python3
"""Measure a rendered video against the reference style and print a match score.

usage: measure_style.py OUT.mp4 [--json report.json]

Each check compares a measured number with the reference value from style-guide.md
and scores 0-1 (1 = within tolerance, falling linearly to 0 at 3x tolerance).
"""
import argparse
import json
import os
import re
import subprocess
import tempfile

import numpy as np
from PIL import Image

REF = {
    "size": (1080, 1920),
    "band_top": 545, "band_bottom": 1371,
    "shot_mean": 1.70, "shot_min": 1.00, "shot_max": 2.77,
    "cap_mean": 0.74, "cap_center_y": 300, "cap_height": 100,
    "pop_first": 0.40, "pop_peak": 1.055, "pop_frames": 5,
    "max_gap_ms": 60,
    "cam_edge_x_at_1450": 67, "cam_bottom": 1523,
}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def score(measured, ref, tol):
    if measured is None:
        return 0.0
    err = abs(measured - ref)
    return 1.0 if err <= tol else max(0.0, 1 - (err - tol) / (2 * tol))


def lum(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
               "-of", "json", path]).stdout
    j = json.loads(out)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def band_edges(frames):
    tops, bots = [], []
    for f in frames:
        im = Image.open(f).convert("RGB")

        def row(y):
            return sum(lum(im.getpixel((x, y))) for x in range(600, 1080, 6)) / 80

        diffs = [(abs(row(y) - row(y - 1)), y) for y in range(420, 700)]
        tops.append(max(diffs)[1])
        diffs = [(abs(row(y) - row(y - 1)), y) for y in range(1250, 1500)]
        bots.append(max(diffs)[1])
    tops.sort()
    bots.sort()
    return tops[len(tops) // 2], bots[len(bots) // 2]


def cam_edges(frame):
    im = Image.open(frame).convert("RGB")
    # row y=1450 is below the band, so the circle edge sits on the blurred fill: x=67 for d=349 at (210,1349)
    xs = [(abs(lum(im.getpixel((x, 1450))) - lum(im.getpixel((x - 1, 1450)))), x) for x in range(20, 120)]
    ys = [(abs(lum(im.getpixel((210, y))) - lum(im.getpixel((210, y - 1)))), y) for y in range(1490, 1560)]
    return max(xs)[1], max(ys)[1]


def shots(path, dur):
    """Hard cuts in the sharp band: brightness-normalised frame difference that spikes
    (>= 0.28 and >= 2x the 2 frames on each side). Works on dark night footage too;
    motion blur and whip pans are plateaus, not spikes."""
    w, h = 68, 78
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps=30,crop=680:780:400:560,scale={w}:{h},format=gray",
         "-f", "rawvideo", "-"], capture_output=True, check=True,
    ).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2)) * 2 / (f[1:].mean(axis=(1, 2)) + f[:-1].mean(axis=(1, 2)) + 20)
    cuts = []
    for i in range(len(d)):
        nb = max(d[max(0, i - 2):i].max(initial=0), d[i + 1:i + 3].max(initial=0))
        if d[i] >= 0.28 and d[i] >= 2 * max(nb, 1e-3):
            cuts.append((i + 1) / 30)
    b = [0.0] + cuts + [dur]
    return [y - x for x, y in zip(b, b[1:]) if y - x > 0.2]


def captions(path, tmp):
    d = os.path.join(tmp, "top")
    os.makedirs(d)
    run(["ffmpeg", "-v", "error", "-i", path, "-vf", "fps=30,crop=1080:545:0:0,scale=540:-1", f"{d}/%05d.png"])
    rows = []
    for f in sorted(os.listdir(d)):
        im = Image.open(os.path.join(d, f)).convert("RGB")
        px = im.load()
        w, h = im.size
        xs, ys = [], []
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                r, g, b = px[x, y]
                if r > 235 and g > 235 and b > 235:
                    xs.append(x)
                    ys.append(y)
        rows.append((min(xs) * 2, max(xs) * 2, min(ys) * 2, max(ys) * 2) if len(xs) > 30 else None)
    # card starts = first non-empty frame after an empty one, or a width collapse
    starts = []
    for i in range(1, len(rows)):
        p, c = rows[i - 1], rows[i]
        if c and (p is None or (c[1] - c[0]) < 0.75 * (p[1] - p[0])):
            starts.append(i)
    # pop: width of the first frames relative to the settled width (frame 8)
    pops = []
    for i in starts:
        if i + 8 < len(rows) and all(rows[i + k] for k in range(9)):
            w = [rows[i + k][1] - rows[i + k][0] for k in range(9)]
            ratios = [x / w[8] for x in w]
            peak = max(ratios[:7])
            settle = next((k for k in range(7) if abs(ratios[k] - 1) < 0.02 and k > ratios.index(peak)), 7)
            pops.append((ratios[0], peak, settle))
    b = starts + [len(rows)]
    lens = [(y - x) / 30 for x, y in zip(b, b[1:])]
    settled = [rows[i + 3] for i in starts if i + 3 < len(rows) and rows[i + 3]]
    cy = sorted((r[2] + r[3]) / 2 for r in settled)
    hh = sorted(r[3] - r[2] for r in settled)
    med = lambda v: v[len(v) // 2] if v else None  # noqa: E731
    return {
        "cards": len(starts),
        "mean": sum(lens) / len(lens) if lens else None,
        "center_y": med(cy),
        "height": med(hh),
        "pop_first": med(sorted(p[0] for p in pops)),
        "pop_peak": med(sorted(p[1] for p in pops)),
        "pop_frames": med(sorted(p[2] for p in pops)),
    }


def max_gap(path):
    log = run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-30dB:d=0.06", "-f", "null", "-"]).stderr
    durs = [float(x) for x in re.findall(r"silence_duration: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    _, _, total = probe(path)
    inner = [d for d, e in zip(durs, ends) if e < total - 0.1 and e - d > 0.1]  # ignore head/tail silence
    return max(inner) * 1000 if inner else 0.0


def loudness(path):
    log = run(["ffmpeg", "-i", path, "-af", "ebur128", "-f", "null", "-"]).stderr
    m = re.findall(r"I:\s+(-?[0-9.]+) LUFS", log)
    return float(m[-1]) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--json")
    a = ap.parse_args()
    w, h, dur = probe(a.video)
    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        for k in range(8):
            f = os.path.join(tmp, f"s{k}.png")
            run(["ffmpeg", "-v", "error", "-ss", f"{dur * (k + 0.5) / 8:.2f}", "-i", a.video, "-frames:v", "1", "-vf",
                 "scale=1080:1920", f])
            frames.append(f)
        top, bot = band_edges(frames)
        cam_l, cam_b = cam_edges(frames[3])
        sl = shots(a.video, dur)
        cap = captions(a.video, tmp)
    inner = sl[1:-1] or sl
    checks = [
        ("1 ขนาดภาพ 1080x1920", f"{w}x{h}", "1080x1920", 1.0 if (w, h) == REF["size"] else 0.0, 1),
        ("2 ความยาวช็อตเฉลี่ย (s)", round(sum(inner) / len(inner), 2), REF["shot_mean"],
         score(sum(inner) / len(inner), REF["shot_mean"], 0.3), 2),
        ("2 ช็อตสั้นสุด/ยาวสุด (s)", f"{min(inner):.2f}/{max(inner):.2f}", "1.06/2.77",
         (score(min(inner), REF["shot_min"], 0.25) + score(max(inner), REF["shot_max"], 0.4)) / 2, 1),
        ("2 ช่องว่างเสียงพูดยาวสุด (ms)", round(max_gap(a.video)), "<=60",
         1.0 if max_gap(a.video) <= REF["max_gap_ms"] else score(max_gap(a.video), 60, 15), 2),
        ("3 ซับ: เวลาต่อการ์ดเฉลี่ย (s)", round(cap["mean"] or 0, 2), REF["cap_mean"], score(cap["mean"], REF["cap_mean"], 0.15), 2),
        ("3 ซับ: กึ่งกลางแนวตั้ง y (px)", cap["center_y"], REF["cap_center_y"], score(cap["center_y"], REF["cap_center_y"], 20), 2),
        ("3 ซับ: ความสูงข้อความ (px)", cap["height"], REF["cap_height"], score(cap["height"], REF["cap_height"], 15), 1),
        ("3 ซับ: เด้ง ขนาดเฟรมแรก", round(cap["pop_first"] or 0, 2), REF["pop_first"], score(cap["pop_first"], REF["pop_first"], 0.12), 1),
        ("3 ซับ: เด้ง จุดพีค (scale)", round(cap["pop_peak"] or 0, 3), REF["pop_peak"], score(cap["pop_peak"], REF["pop_peak"], 0.02), 1),
        ("3 ซับ: เด้ง จนนิ่ง (เฟรม)", cap["pop_frames"], REF["pop_frames"], score(cap["pop_frames"], REF["pop_frames"], 1), 1),
        ("4 แถบภาพคม ขอบบน (y)", top, REF["band_top"], score(top, REF["band_top"], 6), 1),
        ("4 แถบภาพคม ขอบล่าง (y)", bot, REF["band_bottom"], score(bot, REF["band_bottom"], 6), 1),
        ("4 วงกลมหน้า ขอบซ้าย@y1450 (x)", cam_l, REF["cam_edge_x_at_1450"], score(cam_l, REF["cam_edge_x_at_1450"], 6), 1),
        ("4 วงกลมหน้า ขอบล่าง (y)", cam_b, REF["cam_bottom"], score(cam_b, REF["cam_bottom"], 8), 1),
    ]
    lufs = loudness(a.video)
    total_w = sum(c[4] for c in checks)
    pct = 100 * sum(c[3] * c[4] for c in checks) / total_w
    print(f"{'หัวข้อ':34} {'วัดได้':>12} {'อ้างอิง':>12} {'คะแนน':>6}")
    for name, got, ref, s, _w in checks:
        print(f"{name:34} {str(got):>12} {str(ref):>12} {s * 100:5.0f}%")
    print(f"ความดัง (ข้อมูล ไม่คิดคะแนน): {lufs} LUFS, การ์ดซับ {cap['cards']} ใบ, ช็อต {len(sl)} ช็อต")
    print(f"ตรงสไตล์อ้างอิงรวม: {pct:.0f}%")
    if a.json:
        json.dump({"checks": [dict(zip(["item", "measured", "reference", "score", "weight"], [n, str(g), str(r), round(s, 3), wt]))
                              for n, g, r, s, wt in checks], "lufs": lufs, "match_percent": round(pct, 1)},
                  open(a.json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
