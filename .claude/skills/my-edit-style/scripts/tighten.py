#!/usr/bin/env python3
"""Cut every pause out of a talking-head clip (style: no gap > 60 ms).

usage: tighten.py IN.mp4 OUT.mp4 [--db -35] [--min-gap 0.12] [--pad 0.025] [--cuts cuts.json]

Finds silences with FFmpeg silencedetect, keeps `pad` seconds of each silence
on both sides so words are not clipped, and drops the rest (video + audio together).
"""
import argparse
import json
import re
import subprocess
import sys
import sys


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def has_video(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=index", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    ).stdout
    return bool(out.strip())


def silences(path, db, min_gap):
    log = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=n={db}dB:d={min_gap}", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def keep_ranges(total, gaps, pad):
    keep, cur = [], 0.0
    for s, e in gaps:
        e = total if e is None else e
        cut_from, cut_to = s + pad, e - pad
        if cut_to - cut_from <= 0.02:
            continue
        if cut_from > cur:
            keep.append((cur, cut_from))
        cur = cut_to
    if total - cur > 0.02:
        keep.append((cur, total))
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--db", type=float, default=-35)
    ap.add_argument("--min-gap", type=float, default=0.12)
    ap.add_argument("--pad", type=float, default=0.025)
    ap.add_argument("--cuts", help="write kept ranges as JSON")
    a = ap.parse_args()

    total = duration(a.src)
    keep = keep_ranges(total, silences(a.src, a.db, a.min_gap), a.pad)
    if not keep:
        sys.exit("no audio above threshold; check --db")
    expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keep)
    vf = f"select='{expr}',setpts=N/FRAME_RATE/TB"
    af = f"aselect='{expr}',asetpts=N/SR/TB"
    if has_video(a.src):
        cmd = ["-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", "-b:a", "192k"]
    else:  # voice-only recording (no talking-head video)
        cmd = ["-vn", "-af", af] + (["-c:a", "aac", "-b:a", "192k"] if not a.out.endswith(".wav") else [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src] + cmd + [a.out], check=True)
    kept = sum(e - s for s, e in keep)
    print(f"kept {len(keep)} ranges, {kept:.2f}s of {total:.2f}s (removed {total - kept:.2f}s)")
    if a.cuts:
        json.dump([{"start": round(s, 3), "end": round(e, 3)} for s, e in keep], open(a.cuts, "w"), indent=1)


if __name__ == "__main__":
    main()
