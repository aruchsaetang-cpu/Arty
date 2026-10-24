"""Synthesise the 20s Wow! Signal bed: dark drone, eerie shimmer, radio hiss, blips, pen, pops, sweeps and hits."""
import sys, wave
import numpy as np

SR = 48000
DUR = 20.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1977)
L = np.zeros(N); R = np.zeros(N)

def at(sec): return int(sec * SR)

def onepole(x, cutoff, high=False):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc; y[i] = acc
    return x - y if high else y

def env(n, attack, decay):
    e = np.ones(n)
    na = max(1, int(attack * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (decay * SR))
    return e

def add(sig, start, gain=1.0, pan=0.0):
    s = at(start); e = min(N, s + len(sig)); sig = sig[: e - s] * gain
    L[s:e] += sig * (1 - max(0, pan)); R[s:e] += sig * (1 + min(0, pan))

def fade(x, fin, fout):
    x = x.copy(); a, b = int(fin * SR), int(fout * SR)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x

# Drone: E1 + B1 with a slow beat, a mid pad so phones hear it, and a dissonant high pair.
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.6 * np.sin(2 * np.pi * 61.7 * t)
         + 0.4 * np.sin(2 * np.pi * 87.3 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)) * lfo
pad = onepole(rng.standard_normal(N), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
pad += 0.25 * np.sin(2 * np.pi * 174.6 * t + 0.3 * np.sin(2 * np.pi * 0.3 * t))
shimmer = (np.sin(2 * np.pi * 932.3 * t) + np.sin(2 * np.pi * 987.8 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t - 1.2)) ** 2
pad += 0.06 * shimmer
bed = 0.22 * drone + 0.5 * pad
# Silence when it "never came back"; the bed returns under the question.
gate = np.ones(N)
s, e = at(15.5), at(15.7); gate[s:e] = np.linspace(1, 0.05, e - s); gate[e:at(16.9)] = 0.05
s, e = at(16.9), at(17.3); gate[s:e] = np.linspace(0.05, 1, e - s)
bed = fade(bed * gate, 0.25, 1.2)
add(bed, 0, 0.5)

# Radio hiss: the telescope listening, thin and high, phone-audible.
hiss = onepole(onepole(rng.standard_normal(N), 6000), 1200, high=True)
add(fade(hiss * (0.7 + 0.3 * np.sin(2 * np.pi * 0.2 * t)) * gate, 0.4, 1.0), 0, 0.08)

def hit(dur=1.6, f0=70, f1=38):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 6)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.45)
    click = onepole(rng.standard_normal(n), 3000) * env(n, 0.001, 0.03)
    return body + 0.4 * click

def whoosh(dur=0.6, lo=300, hi=2500):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.empty(n); acc = 0.0
    for i, v in enumerate(noise):
        c = lo + (hi - lo) * np.sin(np.pi * i / n)
        a = np.exp(-2 * np.pi * c / SR); acc = (1 - a) * v + a * acc; out[i] = acc
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2

def blip(f=1320.0, dur=0.35):
    n = int(dur * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * f * tt) * env(n, 0.004, 0.08)

def scratch(dur):
    n = int(dur * SR)
    x = onepole(rng.standard_normal(n), 3500, high=True) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * np.arange(n) / SR))
    return x * np.sin(np.linspace(0, np.pi, n)) ** 0.5

def pop(f=520.0):
    n = int(0.12 * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * f * tt * (1 - tt * 2)) * env(n, 0.002, 0.03)

# The source pulses (0.3s + 1.1s each).
for k in range(4):
    add(blip(), 0.3 + 1.1 * k, 0.25)
# Dive into the point of light (4.7s).
add(whoosh(0.6, 400, 3500), 4.62, 1.2)
# Red pen: the circle (6.75s), then "Wow!" (9.45s).
add(scratch(0.6), 6.76, 0.35, -0.1)
add(scratch(0.55), 9.46, 0.35, 0.1)
# Bars rise one by one (10.75s + 0.18s each), pitch following each value.
for i, v in enumerate([6, 14, 26, 30, 19, 5]):
    add(pop(300 + v * 18), 10.76 + 0.18 * i, 0.4)
# The search beam sweeps twice (13.5s, 14.5s).
add(whoosh(0.9, 300, 2000), 13.55, 0.8, -0.4)
add(whoosh(0.9, 300, 2000), 14.55, 0.8, 0.4)
# Riser into "WHO SENT IT?" (17.32s), the one big impact.
n = at(1.2); tt = np.arange(n) / SR
riser = onepole(rng.standard_normal(n), 2500) * (tt / tt[-1]) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 500 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1])
add(riser, 16.12, 0.5)
add(hit(1.6, 75, 34), 17.33, 1.0)

mix = np.stack([L, R], 1)
mix /= np.abs(mix).max() / 0.85
out = sys.argv[1] if len(sys.argv) > 1 else "bed.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
