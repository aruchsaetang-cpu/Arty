#!/usr/bin/env python3
"""Plan B-roll cuts on caption boundaries (style-guide.md §2) and write edit.json.

usage: plan_broll.py captions.json broll.json edit.json --facecam talk.mp4 [--music bed.m4a]

broll.json: list of clips, in story order:
  [{"src": "footage/a.mp4", "in": 0, "out": 6, "keywords": ["avatar", "ฉากเปิด"]}, ...]
  "in"/"out" are optional (default the whole file); "keywords" are optional.

Rules:
  * a cut may only land on a caption start (cuts snap to phrases)
  * shot length target 1.70 s, allowed 1.00-2.77 s; the first shot ends at the first
    caption start after 0.45 s (a quick iconic opener; reference 0.67 s); the last shot may run long
  * a clip whose keyword appears in the captions of the coming shot is used there
    (B-roll shows the noun just spoken); otherwise clips are used in order
"""
import argparse
import json
import os
import subprocess

TARGET, MIN_SHOT, MAX_SHOT, FIRST_MIN = 1.70, 1.00, 2.77, 0.45


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def cut_points(caps, total):
    starts = [c["start"] for c in caps if c["start"] > 0]
    cuts, last = [0.0], 0.0
    first = next((s for s in starts if s >= FIRST_MIN), None)
    if first is not None:
        cuts.append(first)
        last = first
    for s in starts:
        if s <= last:
            continue
        gap = s - last
        if gap < MIN_SHOT:
            continue
        nxt = next((x for x in starts if x > s), None)
        # take this boundary if it is the closest one to the target, or waiting would break the max
        if nxt is None or abs(gap - TARGET) <= abs(nxt - last - TARGET) or nxt - last > MAX_SHOT:
            if total - s >= MIN_SHOT:
                cuts.append(s)
                last = s
    return cuts + [total]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captions")
    ap.add_argument("broll")
    ap.add_argument("out")
    ap.add_argument("--facecam", required=True, help="tightened talking-head clip (its audio is the voice)")
    ap.add_argument("--music")
    ap.add_argument("--music-volume", type=float, default=0.12)
    a = ap.parse_args()

    caps = json.load(open(a.captions))
    clips = json.load(open(a.broll))
    for c in clips:
        c["src"] = os.path.abspath(c["src"])  # edit.json stores absolute paths
        c.setdefault("in", 0.0)
        c.setdefault("out", duration(c["src"]))
        c["pos"] = c["in"]
        c["keywords"] = [k.lower() for k in c.get("keywords", [])]
    total = round(duration(a.facecam), 3)
    cuts = cut_points(caps, total)

    shots, order = [], 0
    for s, e in zip(cuts, cuts[1:]):
        said = " ".join(c["text"].lower() for c in caps if s <= c["start"] < e)
        pick = next((c for c in clips if any(k in said for k in c["keywords"]) and c["pos"] + 0.5 < c["out"]), None)
        if pick is None:
            for _ in range(len(clips)):
                cand = clips[order % len(clips)]
                order += 1
                if cand["pos"] + 0.5 < cand["out"]:
                    pick = cand
                    break
            else:
                for c in clips:  # every clip used up: loop from its in-point
                    c["pos"] = c["in"]
                pick = clips[order % len(clips)]
                order += 1
        dur = round(e - s, 3)
        media_start = pick["pos"] if pick["pos"] + dur <= pick["out"] else max(pick["in"], pick["out"] - dur)
        shots.append({"src": pick["src"], "start": round(s, 3), "dur": dur, "media_start": round(media_start, 3)})
        pick["pos"] = media_start + dur

    edit = {
        "duration": total,
        "facecam": os.path.abspath(a.facecam),
        "music": os.path.abspath(a.music) if a.music else None,
        "music_volume": a.music_volume,
        "shots": shots,
        "captions": caps,
    }
    json.dump(edit, open(a.out, "w"), ensure_ascii=False, indent=1)
    lens = [x["dur"] for x in shots]
    print(f"{len(shots)} shots, mean {sum(lens) / len(lens):.2f}s, min {min(lens):.2f}s, max {max(lens):.2f}s -> {a.out}")


if __name__ == "__main__":
    main()
