#!/usr/bin/env python3
"""Time caption cards to the syllables heard in the voice (tighter than align_runs.py).

usage: align_syll.py script.txt voice.wav captions.json --starts 0,3.2,10.1 --end 27.3

Same script.txt format as align_script.py (one line per take, words `|`, cards `/`, `~n` syllables).
Inside each take the voice's syllable nuclei are found as peaks of a smoothed loudness curve
(>= 90 ms apart, loud enough to be speech). The take's script syllables are mapped onto those peaks
in order (stretched evenly when the counts differ), and each card starts 60 ms before the peak of
its first syllable. Cards shorter than 0.25 s are merged into the previous card.
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
        if out and (LATIN.search(out[-1]) or LATIN.match(w)):
            out += " "
        out += w
    return out


def nuclei(env, a, b, step):
    i0, i1 = int(a / step), int(b / step)
    seg = env[i0:i1]
    if len(seg) < 3:
        return [a]
    floor = np.percentile(seg, 20)
    thr = floor + 0.25 * (seg.max() - floor)
    peaks = []
    gap = int(0.09 / step)
    for k in range(1, len(seg) - 1):
        if seg[k] >= thr and seg[k] >= seg[k - 1] and seg[k] > seg[k + 1]:
            if peaks and k - peaks[-1] < gap:
                if seg[k] > seg[peaks[-1]]:
                    peaks[-1] = k
                continue
            peaks.append(k)
    return [(i0 + k) * step for k in peaks] or [a]


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
step = 0.01
h = int(step * sr)
env = np.array([np.sqrt(np.mean(x[j:j + h] ** 2)) for j in range(0, len(x) - h, h)])
k = np.hanning(7)
env = np.convolve(env, k / k.sum(), mode="same")
starts = [float(v) for v in args.starts.split(",")] + [args.end]
lines = [l.strip() for l in open(args.script, encoding="utf-8") if l.strip()]
assert len(lines) == len(starts) - 1, "one --starts value per script line"

caps = []
for li, line in enumerate(lines):
    cards = [c.strip().split("|") for c in line.split("/")]
    sy = [sum(syl(w) for w in c) for c in cards]
    total = sum(sy)
    pk = nuclei(env, starts[li], starts[li + 1], step)
    first = 0
    for c, n in zip(cards, sy):
        # syllable index -> peak index, stretched evenly when counts differ
        p = pk[min(len(pk) - 1, int(round(first * (len(pk) - 1) / max(1, total - 1))))]
        t = max(starts[li], p - 0.06) if first else starts[li]
        caps.append({"start": round(t, 3), "text": card_text(c)})
        first += n
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
