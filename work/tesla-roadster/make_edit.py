#!/usr/bin/env python3
"""Turn the aligned script (vo.json) into an edit plan for the edit skill's build.py.

Each script line gets its own 3D shots (clips3d/*.mp4); its time is split across
them, so cuts land on line boundaries and the "But" line always opens on a hard cut.
usage: make_edit.py <dir-with-vo.json>   -> <dir>/plan.json
"""
import json, re, subprocess, sys

D = sys.argv[1]
CLIPS = "clips3d"
LINES = [l.strip() for l in open("lines.txt", encoding="utf-8") if l.strip()]
# per line: (clip, in-point) pieces, in order
MAP = [
    [("a_hook", 0.0), ("e_land", 2.4)],                       # Hook
    [("b_site", 0.0), ("c_loop", 0.0)],                       # date / place
    [("c_loop", 1.4), ("a_hook", 0.7)],                       # ramp, upside down, launched
    [("d_thrusters", 0.3), ("e_land", 0.9), ("e_land", 2.7)], # thrusters, hover, smoke
    [("f_quote", 0.0)],                                       # "Flying cars are real"
    [("g_empty", 0.0)],                                       # BUT nobody inside
    [("h_remote", 0.0), ("b_site", 2.4)],                     # remote control
    [("i_stamp", 0.0)],                                       # not approved
    [("c_loop", 0.3), ("a_hook", 1.2)],                       # just a stunt
    [("j_end", 0.5)],                                         # not yet
]


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


words = [w for s in json.load(open(f"{D}/vo.json"))["segments"] for w in s["words"]]
end = words[-1]["end"] + 1.2
# line start times: consume words line by line
starts, i = [], 0
for l in LINES:
    starts.append(0.0 if i == 0 else words[i]["start"])
    i += len([w for w in re.split(r"\s+", l.replace("…", "… ")) if w])
bounds = starts + [end]


def at(word, nth=0):
    hits = [w["start"] for w in words if re.sub(r"[^\w]", "", w["word"]).lower() == word]
    return hits[nth]


shots = []
for li, pieces in enumerate(MAP):
    t0, t1 = bounds[li], bounds[li + 1]
    n = len(pieces)
    for k, (clip, cin) in enumerate(pieces):
        d = (t1 - t0) / n
        src = f"{CLIPS}/{clip}.mp4"
        cin = max(0.0, min(cin, dur(src) - d - 0.05))
        m = max(1, round(d / 1.45))                 # Zack pacing: ~1.4 s per shot, alternating push-in / pull-out
        for j in range(m):
            shots.append({"src": src, "in": round(cin + j * d / m, 3), "dur": round(d / m, 3),
                          "move": "in" if len(shots) % 2 == 0 else "out"})

plan = {
    "shots": shots,
    "graphics": [
        {"type": "flash", "at": 0.0, "dur": 0.18},
        {"type": "burst", "at": at("upsidedown"), "dur": 0.6},
        {"type": "stat", "at": at("october"), "dur": 2.2, "from": 0, "to": 15, "label": "OCT 2026"},
        {"type": "burst", "at": at("launched"), "dur": 0.6},
        {"type": "flash", "at": starts[5], "dur": 0.15},
        {"type": "glow", "at": at("not", 1), "dur": end - at("not", 1), "steps": ["NOT YET"], "y": 1180},
    ],
}
json.dump(plan, open(f"{D}/plan.json", "w"), indent=1)
print(f"{len(shots)} shots, {end:.1f}s, avg {end / len(shots):.2f}s/shot, 'But' at {starts[5]:.2f}s -> {D}/plan.json")
