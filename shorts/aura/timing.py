"""Align script beats to the voiceover: syllable share of speech time, snapped to detected pauses.
    python3 shorts/aura/timing.py shorts/aura/audio/voice.wav  -> prints beats and writes beats.json"""
import json, re, subprocess, sys
wav = sys.argv[1]
BEATS = [  # (shot id, narration)
    ("hook",    "It had rained in Sol for nine years. One man never got wet."),
    ("name",    "They called him Aura monster. Midnight, no coat, no hat, bone dry."),
    ("theory",  "The shopkeepers said luck. The police said a trick. The kids said magic."),
    ("follow",  "So one night I followed him. The rain stopped around me. Then I saw why."),
    ("reveal",  "He wasn't dodging the storm. He was holding it up, one walk at a time, so the city could sleep."),
    ("turn",    "He turned, tired, and smiled. Your turn."),
    ("payoff",  "Now I walk these streets at midnight. And I never get wet."),
]
def syl(w):
    w = w.lower().strip(".,!?\"'"); w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w) if len(w) > 3 else w
    return max(1, len(re.findall(r"[aeiouy]+", w)))
out = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.28", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                           capture_output=True, text=True).stdout)
gaps = list(zip(starts, ends))
speech, t = [], 0.0
for s, e in gaps:
    if s > t: speech.append((t, s))
    t = e
if t < dur: speech.append((t, dur))
total = sum(b - a for a, b in speech)
def speech_to_real(x):
    for a, b in speech:
        if x <= b - a: return a + x
        x -= b - a
    return dur
counts = [sum(syl(w) for w in txt.split()) for _, txt in BEATS]; S = sum(counts)
bounds, cum = [0.0], 0
for c in counts[:-1]:
    cum += c; tr = speech_to_real(total * cum / S)
    best = min(gaps, key=lambda g: abs((g[0] + g[1]) / 2 - tr))
    bounds.append(round((best[0] + best[1]) / 2, 3))
bounds.append(round(dur, 3))
beats = [dict(id=b[0], text=b[1], start=bounds[i], end=bounds[i + 1], f0=round(bounds[i] * 30) + 1, f1=round(bounds[i + 1] * 30))
         for i, b in enumerate(BEATS)]
json.dump(dict(duration=dur, frames=round(dur * 30), beats=beats), open(sys.argv[2] if len(sys.argv) > 2 else "shorts/aura/beats.json", "w"), indent=1)
for b in beats:
    print(f'{b["id"]:7s} {b["start"]:6.2f}-{b["end"]:6.2f}s  frames {b["f0"]:4d}-{b["f1"]:4d}  {b["text"]}')
