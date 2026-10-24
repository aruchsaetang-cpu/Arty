"""Synthesise the 20s Dyatlov Pass bed: dark drone, eerie shimmer, wind, tent rip, crunches, Geiger clicks and hits."""
import sys, wave
import numpy as np

SR = 48000
DUR = 20.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1959)
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
# Drop out under "One was missing her tongue", back in for the radiation.
gate = np.ones(N)
s, e = at(12.2), at(12.5); gate[s:e] = np.linspace(1, 0.1, e - s); gate[e:at(13.7)] = 0.1
s, e = at(13.7), at(14.0); gate[s:e] = np.linspace(0.1, 1, e - s)
bed = fade(bed * gate, 0.25, 1.2)
add(bed, 0, 0.5)

# Wind: band-passed noise in gusts, panned wide, carrying the snow on screen.
for pan, ph in ((-0.7, 0.0), (0.7, 1.7)):
    n = onepole(onepole(rng.standard_normal(N), 1400), 250, high=True)
    gust = 0.35 + 0.65 * np.clip(np.sin(2 * np.pi * 0.13 * t + ph) + 0.3 * np.sin(2 * np.pi * 0.41 * t), 0, 1.3) / 1.3
    add(fade(n * gust, 0.5, 1.0) * gate, 0, 0.5, pan)

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

def rip(dur=0.22):
    n = int(dur * SR)
    x = onepole(rng.standard_normal(n), 1800, high=True)
    crackle = (rng.random(n) < 0.02) * rng.standard_normal(n) * 3
    return (x + crackle) * env(n, 0.005, dur / 3)

def crunch():
    n = int(0.09 * SR)
    return onepole(rng.standard_normal(n), 2500) * env(n, 0.002, 0.03)

def click():
    n = int(0.004 * SR)
    return rng.standard_normal(n) * np.linspace(1, 0, n)

# The tent is cut from the inside (3.92s, 4.12s).
add(rip(), 3.93, 0.9, -0.2)
add(rip(), 4.13, 0.9, 0.2)
# Footprints crunch as they appear (5.0s + 0.082s each), every other one heard.
for k in range(0, 44, 2):
    add(crunch(), 5.0 + k * 0.082 + 0.03, 0.18, (-0.3 if k % 4 else 0.3))
# -30°C lands (7.62s); "CRUSHED CHESTS" (9.38s); the stamp (12.99s).
add(hit(1.2, 90, 45), 7.63, 0.7)
add(hit(1.4, 70, 38), 9.39, 0.8)
add(hit(0.9, 110, 60), 13.0, 0.8)
# Geiger counter while the trefoil pulses (13.87-15.9s), clicks thickening.
gt = 13.87
while gt < 15.9:
    add(click(), gt, 0.5, rng.uniform(-0.3, 0.3))
    rate = 6 + 34 * ((gt - 13.87) / 2.0) ** 1.5
    gt += rng.exponential(1 / rate)
# Riser into "DEAD MOUNTAIN" (17.52s), the one big impact.
n = at(1.3); tt = np.arange(n) / SR
riser = onepole(rng.standard_normal(n), 2500) * (tt / tt[-1]) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 500 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1])
add(riser, 16.22, 0.5)
add(hit(1.6, 75, 34), 17.53, 1.0)

mix = np.stack([L, R], 1)
mix /= np.abs(mix).max() / 0.85
out = sys.argv[1] if len(sys.argv) > 1 else "bed.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
