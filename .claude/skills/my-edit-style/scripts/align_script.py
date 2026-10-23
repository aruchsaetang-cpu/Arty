#!/usr/bin/env python3
"""Fallback when Whisper can't run: time a known script against the tightened voice.

usage: align_script.py script.txt words.json --anchors 0.03,3.52,... --end 26.83 [--voice voice.wav]

script.txt: one line per recorded take/sentence group, words separated by "|",
            caption-card breaks marked with "/" (e.g. "เพื่อนๆ~2|รู้มั้ยว่า~3 / ในหนัง~2").
            "~n" after a word = its number of spoken syllables (default 1 for Thai,
            vowel groups for Latin). Line ends are always card breaks.
--anchors:  start time (s, in the tightened voice) of each line, same count as lines.
--end:      time the last line ends.
--voice:    the tightened voice file. With it, syllables are spread over the time
            where the voice is actually sounding (not over pauses or breaths) and
            each word start is snapped to the nearest syllable onset (energy rise)
            within 120 ms. Without it, time is spread evenly by syllable count.
It is an estimate, not speech recognition: check it in preview.
"""
import argparse
import json
import re
import subprocess

import numpy as np

HOP = 0.01  # 10 ms analysis frames


def syllables(tok):
    m = re.match(r"^(.*)~(\d+)$", tok)
    if m:
        return m.group(1), int(m.group(2))
    if re.search("[฀-๿]", tok):
        return tok, 1
    return tok, max(1, len(re.findall(r"[aeiouyAEIOUY]+", tok)) or len(tok))


def envelope(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-af", "highpass=f=250,lowpass=f=3500", "-ac", "1", "-ar", "16000",
         "-f", "s16le", "-"], capture_output=True, check=True,
    ).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    e = np.sqrt(np.convolve(x ** 2, np.ones(400) / 400, "same")[:: int(16000 * HOP)])
    w = np.hanning(7)
    return 20 * np.log10(np.convolve(e, w / w.sum(), "same") + 1e-5)


def onsets(db, a, b):
    """syllable onsets in [a,b): the low point just before each prominent energy peak"""
    i0, i1 = int(a / HOP), int(b / HOP)
    seg = db[i0:i1]
    out = []
    for i in range(2, len(seg) - 2):
        if seg[i] == seg[max(0, i - 6): i + 7].max() and seg[i] > seg.max() - 25:
            left = seg[max(0, i - 15): i]
            if len(left) and seg[i] - max(left.min(), seg[i + 1: i + 16].min()) >= 3:
                out.append((i0 + max(0, i - 15) + int(left.argmin())) * HOP)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--voice")
    a = ap.parse_args()
    lines = [ln.strip() for ln in open(a.script, encoding="utf-8") if ln.strip()]
    anchors = [float(x) for x in a.anchors.split(",")]
    if len(anchors) != len(lines):
        raise SystemExit(f"{len(lines)} lines but {len(anchors)} anchors")
    bounds = anchors + [a.end]
    db = envelope(a.voice) if a.voice else None
    words = []
    for i, ln in enumerate(lines):
        toks, brks = [], []
        for group in ln.split("/"):
            g = [t.strip() for t in group.split("|") if t.strip()]
            toks += g
            brks += ([False] * (len(g) - 1) + [True]) if g else []
        parsed = [syllables(t) for t in toks]
        lo, hi = bounds[i], bounds[i + 1]
        total = sum(n for _, n in parsed)
        if db is not None:
            # clock that only runs while the voice is sounding (within 20 dB of the take's peak)
            seg = db[int(lo / HOP): int(hi / HOP)]
            voiced = (seg > seg.max() - 20).astype(float)
            clock = np.concatenate([[0], np.cumsum(voiced)])
            clock /= clock[-1] if clock[-1] else 1

            def at(frac):
                return lo + float(np.searchsorted(clock, frac)) * HOP

            ons = onsets(db, lo, hi)
        else:
            def at(frac):
                return lo + frac * (hi - lo)

            ons = []
        k = 0
        starts = []
        for _, n in parsed:
            t = at(k / total)
            near = [o for o in ons if abs(o - t) <= 0.12]
            starts.append(min(near, key=lambda o: abs(o - t)) if near else t)
            k += n
        starts[0] = lo
        for j in range(1, len(starts)):  # keep order after snapping
            starts[j] = max(starts[j], starts[j - 1] + 0.04)
        for j, ((word, _), brk) in enumerate(zip(parsed, brks)):
            end = starts[j + 1] if j + 1 < len(starts) else hi
            words.append({"start": round(starts[j], 3), "end": round(end, 3), "word": word, "brk": brk})
    json.dump(words, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(words)} words over {len(lines)} lines -> {a.out}")


if __name__ == "__main__":
    main()
