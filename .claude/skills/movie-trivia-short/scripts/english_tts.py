#!/usr/bin/env python3
"""English voiceover + exact caption timing, offline (Kokoro-82M via kokoro-onnx).

usage: english_tts.py spec.json voice.wav caps.json
spec: {"voice": "am_michael", "speed": 1.1, "gap": 0.08, "phrases": [[speak, display, extra_gap], ...]}
Setup: pip install kokoro-onnx soundfile; run `npx hyperframes tts "hi"` once to download the model into
~/.cache/hyperframes/tts/. Each phrase becomes one caption card, so keep phrases to 2-5 words.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

C = os.path.expanduser("~/.cache/hyperframes/tts")
spec = json.load(open(sys.argv[1]))
k = Kokoro(f"{C}/models/kokoro-v1.0.onnx", f"{C}/voices/voices-v1.0.bin")
out, caps, t, sr = [], [], 0.0, 24000
for p in spec["phrases"]:
    speak, disp = p[0], p[1]
    extra = p[2] if len(p) > 2 else 0
    x, sr = k.create(speak, voice=spec.get("voice", "am_michael"), speed=spec.get("speed", 1.1), lang="en-us")
    x = np.asarray(x, np.float32)
    idx = np.where(np.abs(x) > 0.01)[0]
    if len(idx):
        x = x[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.04 * sr)]
    caps.append({"start": round(t, 2), "text": disp})
    out += [x, np.zeros(int((spec.get("gap", 0.08) + extra) * sr), np.float32)]
    t += len(x) / sr + spec.get("gap", 0.08) + extra
for i, c in enumerate(caps):
    c["end"] = caps[i + 1]["start"] if i + 1 < len(caps) else round(t, 2)
sf.write(sys.argv[2], np.concatenate(out), sr)
json.dump(caps, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
print("total", round(t, 2))
