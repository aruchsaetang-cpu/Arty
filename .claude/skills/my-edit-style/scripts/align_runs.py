#!/usr/bin/env python3
"""Time caption cards to the speech runs actually heard in the voice.

usage: align_runs.py script.txt voice.wav captions.json --starts 0,3.2,10.1 --end 27.3

script.txt: one line per take, words split by `|`, cards split by `/`, `~n` = syllable count
(same format as align_script.py). --starts are the take start times in voice.wav, --end is when
the last take stops. Inside each take the voice is split into runs at pauses >= 0.12 s; the take's
cards are partitioned over those runs so each group's syllable share matches the run's length, then
spread over the run by syllables. Cards shorter than 0.25 s are merged into the previous card.
"""
import argparse
import json
import re

import numpy as np
import soundfile as sf

LATIN = re.compile(r"[A-Za-z0-9]")


def syl(w):
    m = re.search(r"~(\d+)$", w)
    return int(m.group(1)) if m else 1


def clean(w):
    return re.sub(r"~\d+$", "", w)


def card_text(words):
    out = ""
    for w in map(clean, words):
        if out and LATIN.search(out[-1]) and LATIN.match(w):
            out += " "
        elif out and (LATIN.search(out[-1]) or LATIN.match(w)):
            out += " "
        out += w
    return out


def speech_runs(r, a, b, thr=0.06, gap=0.12):
    i0, i1 = int(a * 100), int(b * 100)
    out, s, last = [], None, None
    for k, v in enumerate(r[i0:i1] > thr):
        t = (i0 + k) / 100
        if v:
            if s is None:
                s = t
            elif last is not None and t - last >= gap:
                out.append((s, last + 0.01))
                s = t
            last = t
    if s is not None:
        out.append((s, last + 0.01))
    merged = []
    for q in out:
        if merged and q[1] - q[0] < 0.08:
            merged[-1] = (merged[-1][0], q[1])
        else:
            merged.append(q)
    return merged


def partition(cs, runs):
    n, k = len(cs), len(runs)
    tot = sum(cs)
    dur = sum(b - a for a, b in runs)
    pre = [0.0]
    for c in cs:
        pre.append(pre[-1] + c / tot)
    tgt = [(b - a) / dur for a, b in runs]
    inf = float("inf")
    best = [[inf] * (n + 1) for _ in range(k + 1)]
    back = [[0] * (n + 1) for _ in range(k + 1)]
    best[0][0] = 0
    for g in range(1, k + 1):
        for j in range(g, n - (k - g) + 1):
            for i in range(g - 1, j):
                v = best[g - 1][i] + abs((pre[j] - pre[i]) - tgt[g - 1])
                if v < best[g][j]:
                    best[g][j], back[g][j] = v, i
    cuts, j = [], n
    for g in range(k, 0, -1):
        i = back[g][j]
        cuts.append((i, j))
        j = i
    return list(reversed(cuts))


ap = argparse.ArgumentParser()
ap.add_argument("script")
ap.add_argument("voice")
ap.add_argument("out")
ap.add_argument("--starts", required=True)
ap.add_argument("--end", type=float, required=True)
args = ap.parse_args()

x, sr = sf.read(args.voice)
if x.ndim > 1:
    x = x.mean(axis=1)
h = int(0.01 * sr)
r = np.array([np.abs(x[j:j + h]).max() for j in range(0, len(x) - h, h)])
starts = [float(v) for v in args.starts.split(",")] + [args.end]
lines = [l.strip() for l in open(args.script, encoding="utf-8") if l.strip()]
assert len(lines) == len(starts) - 1, "one --starts value per script line"

caps = []
for li, line in enumerate(lines):
    cards = [c.strip().split("|") for c in line.split("/")]
    cs = [sum(syl(w) for w in c) for c in cards]
    runs = speech_runs(r, starts[li], starts[li + 1])
    while len(runs) > len(cards):
        gi = min(range(len(runs) - 1), key=lambda k: runs[k + 1][0] - runs[k][1])
        runs[gi] = (runs[gi][0], runs[gi + 1][1])
        del runs[gi + 1]
    for (i, j), (a, b) in zip(partition(cs, runs), runs):
        pos = a
        for c, w in zip(cards[i:j], cs[i:j]):
            caps.append({"start": round(pos, 3), "text": card_text(c)})
            pos += (b - a) * w / sum(cs[i:j])
for a, b in zip(caps, caps[1:]):
    a["end"] = b["start"]
caps[-1]["end"] = round(args.end + 0.3, 3)
merged = []
for c in caps:
    if merged and merged[-1]["end"] - merged[-1]["start"] < 0.25:
        merged[-1]["text"] += " " + c["text"]
        merged[-1]["end"] = c["end"]
    else:
        merged.append(c)
json.dump(merged, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(merged), "cards, ends", merged[-1]["end"])
