#!/usr/bin/env python3
"""English voiceover + word-by-word captions, offline (Kokoro-82M via kokoro-onnx).

usage: english_tts.py spec.json voice.wav caps.json
spec: {"voice": "am_michael", "speed": 1.3, "gap": 0.05,
       "sentences": ["Did you know the *first* Woody almost killed *Toy Story*?", ...]}
Each sentence is spoken in one breath (natural intonation, fast like viral Shorts narrators), then cut into
one-word caption cards timed by syllable share; pauses inside the sentence (commas) are found in the audio
and used as anchors. Wrap keywords in *stars* to show them yellow (multi-word: *Toy Story* stays one card).
Setup: pip install kokoro-onnx soundfile; run `npx hyperframes tts "hi"` once to download the model into
~/.cache/hyperframes/tts/.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

C = os.path.expanduser("~/.cache/hyperframes/tts")
YELLOW = "#FFD400"


def syllables(w):
    w = re.sub(r"[^a-z0-9]", "", w.lower())
    if w.isdigit():
        return max(2, round(len(w) * 1.5))  # "1993" -> nineteen ninety-three
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


def tokens(sentence):
    """split into caption cards: *multi word* keyword stays together"""
    out = []
    for m in re.finditer(r"\*([^*]+)\*([^\s*]*)|(\S+)", sentence):
        if m.group(1):
            out.append((m.group(1) + m.group(2), True))
        elif re.fullmatch(r"[^\w]+", m.group(3)) and out:  # stray punctuation sticks to the previous card
            out[-1] = (out[-1][0] + m.group(3), out[-1][1])
        else:
            out.append((m.group(3), False))
    return out


def speech_runs(x, sr, thr=0.012, min_gap=0.09):
    """[(start, end)] of voiced runs separated by pauses >= min_gap"""
    h = int(0.01 * sr)
    e = np.array([np.abs(x[i:i + h]).max() for i in range(0, len(x) - h, h)])
    on = e > thr
    runs, s, last = [], None, None
    for i, v in enumerate(on):
        if v:
            if s is None:
                s = i
            elif last is not None and (i - last) * 0.01 >= min_gap:
                runs.append((s * 0.01, (last + 1) * 0.01))
                s = i
            last = i
    if s is not None:
        runs.append((s * 0.01, (last + 1) * 0.01))
    return runs


spec = json.load(open(sys.argv[1]))
k = Kokoro(f"{C}/models/kokoro-v1.0.onnx", f"{C}/voices/voices-v1.0.bin")
out, caps, t, sr = [], [], 0.0, 24000
for sent in spec["sentences"]:
    toks = tokens(sent)
    speak = sent.replace("*", "")
    x, sr = k.create(speak, voice=spec.get("voice", "am_michael"), speed=spec.get("speed", 1.3), lang="en-us")
    x = np.asarray(x, np.float32)
    idx = np.where(np.abs(x) > 0.01)[0]
    x = x[max(0, idx[0] - int(0.01 * sr)): idx[-1] + int(0.03 * sr)]
    dur = len(x) / sr
    # group tokens by clause (comma/;/: ends a clause) and match clauses to voiced runs when counts agree
    clauses, cur = [], []
    for tk in toks:
        cur.append(tk)
        if re.search(r"[,;:.!?]$", tk[0]):
            clauses.append(cur)
            cur = []
    if cur:
        clauses.append(cur)
    runs = speech_runs(x, sr)
    if len(runs) != len(clauses):
        runs = [(0.0, dur)]
        clauses = [toks]
    for (a, b), cl in zip(runs, clauses):
        w = [sum(syllables(p) for p in tk[0].split()) for tk in cl]
        pos = a
        for (txt, key), wi in zip(cl, w):
            c = {"start": round(t + pos, 2), "text": txt}
            if key:
                c["color"] = YELLOW
            caps.append(c)
            pos += (b - a) * wi / sum(w)
    out += [x, np.zeros(int(spec.get("gap", 0.05) * sr), np.float32)]
    t += dur + spec.get("gap", 0.05)
for i, c in enumerate(caps):
    c["end"] = caps[i + 1]["start"] if i + 1 < len(caps) else round(t, 2)
# merge flash cards (< 0.16 s) into the next card
merged = []
for c in caps:
    if merged and merged[-1]["end"] - merged[-1]["start"] < 0.16 and "color" not in merged[-1] and "color" not in c:
        merged[-1]["text"] += " " + c["text"]
        merged[-1]["end"] = c["end"]
    else:
        merged.append(c)
sf.write(sys.argv[2], np.concatenate(out), sr)
json.dump(merged, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
print("total", round(t, 2), "cards", len(merged))
