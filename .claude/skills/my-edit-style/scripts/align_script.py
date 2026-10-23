#!/usr/bin/env python3
"""Fallback when Whisper can't run: time a known script against the tightened voice.

usage: align_script.py script.txt words.json --anchors 0.03,3.52,... --end 26.83

script.txt: one line per recorded take/sentence group, words separated by "|",
            caption-card breaks marked with "/" (e.g. "เพื่อนๆ|รู้มั้ยว่า / ในหนัง|Back to the Future").
            Line ends are always card breaks. chunk_captions.py never joins across a break.
--anchors:  start time (s, in the tightened voice) of each line, same count as lines.
--end:      time the last line ends.
Inside a line, time is shared out by each word's length in base characters
(Thai vowel/tone marks don't count), which tracks syllables closely enough for
phrase captions after pauses are cut. Check the result in preview: it is an
estimate, not speech recognition.
"""
import argparse
import json
import re

COMBINING = re.compile("[ัิ-ฺ็-๎]")


def weight(word):
    if re.search("[฀-๿]", word):
        return max(1, len(COMBINING.sub("", word)))
    # Latin/digits: about 2.2 letters per spoken syllable-equivalent base char
    return max(1.5, len(word.replace(" ", "")) / 2.2 * 1.6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--end", type=float, required=True)
    a = ap.parse_args()
    lines = [ln.strip() for ln in open(a.script, encoding="utf-8") if ln.strip()]
    anchors = [float(x) for x in a.anchors.split(",")]
    if len(anchors) != len(lines):
        raise SystemExit(f"{len(lines)} lines but {len(anchors)} anchors")
    bounds = anchors + [a.end]
    words = []
    for i, ln in enumerate(lines):
        toks, brks = [], []
        for group in ln.split("/"):
            g = [t.strip() for t in group.split("|") if t.strip()]
            toks += g
            brks += [False] * (len(g) - 1) + [True] if g else []
        ws = [weight(t) for t in toks]
        span, t = bounds[i + 1] - bounds[i], bounds[i]
        for tok, w, brk in zip(toks, ws, brks):
            d = span * w / sum(ws)
            words.append({"start": round(t, 3), "end": round(t + d, 3), "word": tok, "brk": brk})
            t += d
    json.dump(words, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(words)} words over {len(lines)} lines -> {a.out}")


if __name__ == "__main__":
    main()
