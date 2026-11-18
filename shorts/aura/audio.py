"""Synthesize the music bed and SFX stems for "Aura Monster" (no samples, all numpy).

    python3 shorts/aura/audio.py   -> shorts/aura/audio/music.wav, sfx.wav  (48 kHz stereo)
Timing follows beats.json; the rain freezes on "The rain stopped around me" and returns at the payoff.
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
beats = json.load(open(os.path.join(HERE, "beats.json")))
DUR = beats["duration"]; n = int(DUR * SR)
B = {b["id"]: b for b in beats["shots"]}
FREEZE = beats["freeze"]
PAYOFF = B["payoff_side"]["start"]; TURN = B["turn"]["start"]; REVEAL = B["reveal_low"]["start"]
rng = np.random.default_rng(3)
t = np.arange(n) / SR

def env(points):
    """Piecewise-linear envelope from [(time, gain), ...]."""
    ts, gs = zip(*points); return np.interp(t, ts, gs)

def lp(x, cutoff):  # fast one-pole via cumulative filter in blocks
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)

def hp(x, cutoff):
    return x - lp(x, cutoff)

def stereo(x, width=0.3, seed=0):
    d = int(SR * 0.011 * (1 + seed % 3))
    r = np.concatenate([np.zeros(d), x[:-d]])
    return np.stack([x, (1 - width) * x + width * r], 1)

# ------------------------------------------------------------------ music: slow minor pad + plucked motif
def pad(freqs, start, end, gain=1.0):
    out = np.zeros(n)
    i0, i1 = int(start * SR), min(n, int(end * SR)); tt = t[i0:i1] - start
    for k, f in enumerate(freqs):
        for det in (-0.12, 0.0, 0.13):          # detuned saw-ish stack, softened
            ph = 2 * np.pi * f * (1 + det / 100) * tt
            out[i0:i1] += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)) / (1 + k * 0.3)
    a = np.clip(np.minimum((t - start) / 1.6, (end - t) / 1.6), 0, 1)
    return out * a * gain

def pluck(f, at, gain=1.0, decay=1.4):
    i0 = int(at * SR); L = min(n - i0, int(SR * 3.0)); tt = np.arange(L) / SR
    x = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 6)) * np.exp(-tt / decay * 3)
    out = np.zeros(n); out[i0:i0 + L] = x * gain; return out

A2, C3, D3, E3, F3, G3, A3, C4, E4, G4, A4, B3 = 110, 130.81, 146.83, 164.81, 174.61, 196, 220, 261.63, 329.63, 392, 440, 246.94
prog = [(A2, E3, A3, C4), (F3 / 2, C3, F3, A3), (C3, G3, C4, E4), (G3 / 2, D3, G3, B3)]
music = np.zeros(n); bar = 3.4
tt0 = 0.0; k = 0
while tt0 < TURN + 0.4:
    ch = prog[k % 4]; music += pad(ch, tt0, min(tt0 + bar + 0.8, TURN + 0.8), 0.35 if tt0 < REVEAL else 0.55)
    tt0 += bar; k += 1
motif = [A4, E4, G4, E4, C4 * 2, B3 * 2, A4, E4]
for i, at in enumerate(np.arange(1.0, TURN, 0.85)):
    if FREEZE - 0.2 < at < FREEZE + 1.6:  # hold the breath when time stops
        continue
    music += pluck(motif[i % len(motif)] / 2, at, 0.18)
music += pad((A2, E3, A3, C4, E4), PAYOFF - 0.2, DUR, 0.45)           # resolve for the payoff
music += pad((A2 / 2,), 0.0, DUR, 0.25)                                # sub drone under everything
music *= env([(0, 0), (1.2, 1), (FREEZE - 0.1, 1), (FREEZE + 0.2, 0.55), (TURN - 0.3, 0.9), (TURN + 0.6, 0.15),
              (PAYOFF - 0.2, 0.15), (PAYOFF + 1.5, 1), (DUR - 1.5, 1), (DUR, 0)])
music = lp(music, 2800)

# ------------------------------------------------------------------ SFX
sfx = np.zeros((n, 2))
rain = rng.standard_normal(n); rain = hp(lp(rain, 3800), 500) * 0.5 + lp(rng.standard_normal(n), 250) * 0.5
drops = (rng.random(n) < 0.0009) * rng.standard_normal(n) * 3.0
rain = rain + lp(drops, 4000)
rain *= env([(0, 0), (0.8, 1), (FREEZE - 0.05, 1), (FREEZE + 0.12, 0.0), (PAYOFF - 0.1, 0.0), (PAYOFF + 0.9, 1), (DUR, 1)])
RAIN = stereo(rain, 0.6, 1)

def place(x, at, gain=1.0, width=0.4, seed=2):
    i0 = int(at * SR); L = min(len(x), n - i0); s = stereo(x[:L], width, seed) * gain
    sfx[i0:i0 + L] += s

tl = np.arange(int(SR * 4.0)) / SR
thunder = lp(rng.standard_normal(len(tl)), 180) * np.exp(-tl * 0.9) * (1 + 0.6 * np.sin(2 * np.pi * 2.3 * tl))
place(thunder, 0.4, 2.2)
place(lp(rng.standard_normal(len(tl)), 140) * np.exp(-tl * 1.1), REVEAL + 1.0, 1.4)            # far thunder during the reveal
tw = np.arange(int(SR * 1.2)) / SR                                                       # time-stop: reverse whoosh into a low boom
whoosh = hp(lp(rng.standard_normal(len(tw)), 2400), 200) * (tw / tw[-1]) ** 3
place(whoosh, FREEZE - 1.15, 1.6)
tb = np.arange(int(SR * 2.5)) / SR
boom = (np.sin(2 * np.pi * (55 - 20 * tb) * tb) * np.exp(-tb * 2.2) + lp(rng.standard_normal(len(tb)), 90) * np.exp(-tb * 3))
place(boom, FREEZE, 2.6)
ring = np.sin(2 * np.pi * 1760 * tb) * np.exp(-tb * 1.6) * 0.25 + np.sin(2 * np.pi * 2637 * tb) * np.exp(-tb * 2.2) * 0.15
place(ring, FREEZE + 0.05, 1.0)                                                          # glassy shimmer of frozen drops
tc = np.arange(int(SR * 3.0)) / SR                                                       # a car passing (hook)
car = lp(rng.standard_normal(len(tc)), 900) * np.exp(-((tc - 1.5) / 0.6) ** 2)
place(car, 2.0, 1.2, 0.8)
sting = np.sin(2 * np.pi * 880 * tb) * np.exp(-tb * 2.0) + 0.5 * np.sin(2 * np.pi * 1318.5 * tb) * np.exp(-tb * 2.6)
place(sting, next(x["start"] for x in json.load(open(os.path.join(HERE, "sentences.json"))) if "Your turn" in x["text"]) + 0.05, 0.8)                                               # "Your turn."
place(boom * 0.6, DUR - 2.4, 1.2)                                                        # last word lands

def write(path, x):
    x = x / max(1e-9, np.abs(x).max()) * 0.9
    if x.ndim == 1: x = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)
write(os.path.join(HERE, "audio", "music.wav"), stereo(music, 0.35, 2))
write(os.path.join(HERE, "audio", "sfx.wav"), sfx)
write(os.path.join(HERE, "audio", "rain.wav"), RAIN)
print(f"stems written: {DUR:.2f}s, freeze at {FREEZE:.2f}s, payoff at {PAYOFF:.2f}s")
