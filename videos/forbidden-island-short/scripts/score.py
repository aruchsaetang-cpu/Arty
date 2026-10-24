"""Synthesise the 20s Hollow Truth bed: dark drone, eerie shimmer, surf, rotor and hits."""
import sys, wave
import numpy as np

SR = 48000
DUR = 20.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)
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

# Drone: A1 + E2 with a slow beat, plus a mid pad so phones hear it.
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.6 * np.sin(2 * np.pi * 61.9 * t)
         + 0.4 * np.sin(2 * np.pi * 87.3 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)) * lfo
pad = onepole(rng.standard_normal(N), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
pad += 0.25 * np.sin(2 * np.pi * 174.6 * t + 0.3 * np.sin(2 * np.pi * 0.3 * t))
# Eerie high pair a minor second apart, beating slowly, swelling in and out.
shimmer = (np.sin(2 * np.pi * 932.3 * t) + np.sin(2 * np.pi * 987.8 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t - 1.2)) ** 2
pad += 0.06 * shimmer
bed = 0.22 * drone + 0.5 * pad
# Drop out under "He never came back", back in on "No one knows".
gate = np.ones(N)
s, e = at(15.9), at(16.3); gate[s:e] = np.linspace(1, 0.08, e - s); gate[e:at(17.2)] = 0.08
s, e = at(17.2), at(17.6); gate[s:e] = np.linspace(0.08, 1, e - s)
bed = fade(bed * gate, 0.25, 1.2)
add(bed, 0, 0.5)

# Surf: low-passed noise in slow swells, panned wide.
for pan, ph in ((-0.6, 0.0), (0.6, 2.1)):
    n = onepole(rng.standard_normal(N), 1200)
    swell = np.clip(np.sin(2 * np.pi * 0.16 * t + ph), 0, 1) ** 2
    add(fade(n * (0.25 + 0.75 * swell), 0.4, 1.0) * gate, 0, 0.16, pan)

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

# Exclusion ring closes (1.4s), the chart pulls out (3.0s).
add(hit(), 1.42, 0.9)
add(whoosh(0.7), 2.85, 1.4, -0.3)
# Count-up lands on 60,000 (8.37s).
add(hit(1.2, 95, 50), 8.38, 0.7)
# Helicopter crosses 9.9-12.9s: rotor chop panned left to right.
n = at(3.0); tt = np.arange(n) / SR
chop = onepole(rng.standard_normal(n), 900) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 13 * tt))) ** 2
chop = fade(chop * np.sin(np.linspace(0, np.pi, n)), 0.3, 0.6)
pan = np.linspace(-0.8, 0.8, n)
s = at(9.9); L[s:s + n] += chop * 0.5 * (1 - np.clip(pan, 0, 1)); R[s:s + n] += chop * 0.5 * (1 + np.clip(pan, -1, 0))
# Arrow line draws up toward it (11.9s).
add(whoosh(0.35, 800, 4000), 11.85, 0.9, 0.2)
# Canoe path stops on the beach (15.7s).
add(hit(1.0, 60, 35), 15.74, 0.6)
# Riser into the last impact on "Would you go?" (17.92s).
n = at(1.3); tt = np.arange(n) / SR
riser = onepole(rng.standard_normal(n), 2500) * (tt / tt[-1]) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 500 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1])
add(riser, 16.62, 0.5)
add(hit(1.1, 80, 40), 17.94, 1.0)

mix = np.stack([L, R], 1)
mix /= np.abs(mix).max() / 0.85
out = sys.argv[1] if len(sys.argv) > 1 else "bed.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
