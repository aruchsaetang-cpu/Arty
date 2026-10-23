#!/usr/bin/env python3
"""Contact sheet of a rendered clip for the platform-safety review.

usage: safety_sheet.py OUT.mp4 sheet.png [--every 0.5]

One timestamped frame every --every seconds (default 0.5 s), 8 per row. The first frame is
outlined in red: it is the thumbnail and must not show anything from the risk table in SKILL.md.
Open the sheet and check every frame before sending the clip.
"""
import argparse
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=0.5)
    a = ap.parse_args()
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video],
        capture_output=True, text=True, check=True,
    ).stdout)
    n = int(dur / a.every) + 1
    rows = (n + 7) // 8
    vf = (
        f"fps=1/{a.every},scale=180:-2,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=red:t=6:enable='eq(n,0)',"
        "drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black,"
        f"tile=8x{rows}"
    )
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vf", vf, "-frames:v", "1", a.out], check=True)
    print(f"{n} frames -> {a.out} (first frame = thumbnail, outlined red)")


if __name__ == "__main__":
    main()
