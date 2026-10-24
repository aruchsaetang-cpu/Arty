"""Synthesise the 20s Mary Celeste bed: dark drone, eerie shimmer, swell, hull creaks, a bell and hits."""
import sys, wave
import numpy as np

SR = 48000
DUR = 20.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1872)
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
# Drop out under "They were never seen again", back in for the question.
gate = np.ones(N)
s, e = at(12.95), at(13.25); gate[s:e] = np.linspace(1, 0.1, e - s); gate[e:at(14.5)] = 0.1
s, e = at(14.5), at(14.9); gate[s:e] = np.linspace(0.1, 1, e - s)
bed = fade(bed * gate, 0.25, 1.2)
add(bed, 0, 0.5)

# Swell: low-passed noise in slow swells, panned wide, under the waves on screen.
for pan, ph in ((-0.6, 0.0), (0.6, 2.1)):
    n = onepole(rng.standard_normal(N), 900)
    swell = np.clip(np.sin(2 * np.pi * 0.18 * t + ph), 0, 1) ** 2
    add(fade(n * (0.3 + 0.7 * swell), 0.4, 1.0) * gate, 0, 0.3, pan)

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

def creak(dur=0.7, f0=95):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 * (1 + 0.25 * np.sin(2 * np.pi * 1.3 * tt))
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.4
    grain = (rng.random(n) < 0.05) * rng.standard_normal(n)
    return onepole(tone + grain, 1500) * np.sin(np.linspace(0, np.pi, n)) ** 2

def bell(dur=3.0, f=392.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    partials = [(1, 1), (2.4, 0.5), (3.0, 0.3), (4.5, 0.2)]
    return sum(a * np.sin(2 * np.pi * f * r * tt) for r, a in partials) * env(n, 0.003, 0.9)

# The hull creaks at the top of each roll (the ship rolls on a 5.5s cycle).
for k, c in enumerate([1.0, 3.7, 6.5, 9.2, 12.0, 14.7, 17.5]):
    add(creak(0.7, 90 + 12 * (k % 3)), c, 0.35, (-0.4 if k % 2 else 0.4))
# A ship's bell, once, as the title lands; the panel lifts off the cabin (7.6s).
add(bell(), 0.25, 0.25)
add(creak(0.5, 140), 7.6, 0.45)
# "6 MONTHS" lands (7.55s); the stamp (11.52s).
add(hit(1.2, 90, 45), 7.56, 0.7)
add(hit(0.9, 110, 60), 11.53, 0.8)
# Riser into "WHY DID THEY LEAVE?" (17.52s), the one big impact.
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
