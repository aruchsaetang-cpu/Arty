"""Synthesise a 30s trailer score: drone, braams, hits, ticks, riser, slam."""
import sys, wave
import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)

def at(sec): return int(sec * SR)

def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc; y[i] = acc
    return y

def env(n, attack, decay):
    e = np.ones(n)
    na = max(1, int(attack * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (decay * SR))
    return e

def add(sig, start, gain=1.0, pan=0.0):
    s = at(start); e = min(N, s + len(sig)); sig = sig[: e - s] * gain
    L[s:e] += sig * (1 - max(0, pan)); R[s:e] += sig * (1 + min(0, pan))

def saw(freq, n):
    ph = (np.arange(n) * freq / SR) % 1.0
    return 2 * ph - 1

def braam(start, root=55.0, length=3.2, gain=0.55):
    n = int(length * SR); x = np.zeros(n)
    for mult, det in [(1, 0), (1, 0.4), (1.5, -0.3), (2, 0.2), (3, -0.5)]:
        x += saw(root * mult + det, n)
    x = lowpass(x / 5, 420) * env(n, 0.04, 1.1)
    sub = np.sin(2 * np.pi * root / 2 * np.arange(n) / SR) * env(n, 0.01, 1.4)
    add(np.tanh(2.2 * (x + 0.8 * sub)), start, gain, -0.15)
    add(np.tanh(2.2 * (x + 0.8 * sub)), start + 0.012, gain, 0.15)

def boom(start, f0=70, gain=0.9, decay=0.6):
    n = int(2.0 * SR); k = np.arange(n) / SR
    f = f0 * np.exp(-k * 3) + 30
    ph = 2 * np.pi * np.cumsum(f) / SR
    hit = np.sin(ph) * env(n, 0.002, decay)
    click = lowpass(rng.standard_normal(n), 2500) * env(n, 0.001, 0.03)
    add(np.tanh(1.8 * (hit + 0.6 * click)), start, gain)

def tick(start, gain=0.25):
    n = int(0.08 * SR)
    x = lowpass(rng.standard_normal(n), 6000) * env(n, 0.001, 0.012)
    add(x, start, gain)

def chime(start, freqs, gain=0.18):
    n = int(2.5 * SR); k = np.arange(n) / SR; x = np.zeros(n)
    for i, f in enumerate(freqs):
        x += np.sin(2 * np.pi * f * k) * np.exp(-k * (2.2 + i * 0.4))
    add(x / len(freqs), start, gain, 0.2)

def whoosh(start, length, gain=0.3, rise=True):
    n = int(length * SR)
    x = rng.standard_normal(n)
    shape = np.linspace(0, 1, n) ** 2 if rise else np.linspace(1, 0, n) ** 2
    add(lowpass(x, 1800) * shape, start, gain)

# drone bed 0–23.9 and 24–30
for a, b, g in [(0.0, 23.9, 0.22), (24.0, 30.0, 0.16)]:
    s, e = at(a), at(b); k = t[s:e] - a
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * k)
    d = (np.sin(2 * np.pi * 41.2 * k) + 0.5 * np.sin(2 * np.pi * 61.8 * k) + 0.25 * np.sin(2 * np.pi * 82.4 * k)) * lfo
    fade = np.minimum(1, k / 2.0) * np.minimum(1, (b - a - k) / 0.6)
    L[s:e] += d * fade * g; R[s:e] += d * fade * g

whoosh(1.3, 1.2, 0.25)
braam(2.5)                       # IN A WORLD
boom(6.0, 60, 0.7)               # the city is melting
for i, f in enumerate([880, 740, 587, 494]):   # drips
    chime(6.4 + i * 0.6, [f], 0.14)
whoosh(8.5, 1.0, 0.3)
braam(9.5, 49.0, 3.4, 0.6)       # ONE MAN
boom(9.5, 80, 0.8)
for s, f in [(13.6, 70), (14.3, 80), (15.0, 95)]:   # scoops land
    boom(s, f, 0.75, 0.35)
for k in range(8):               # montage clock
    tick(16.5 + k * 0.45)
for s in (16.5, 17.4, 18.3, 19.2):
    boom(s, 90, 0.6, 0.25)
# riser 20–23.9
s, e = at(20.0), at(23.9); k = t[s:e] - 20.0; dur = 3.9
f = 180 * (6.5 ** (k / dur))
riser = np.sin(2 * np.pi * np.cumsum(f) / SR) * (k / dur) ** 2
noise = lowpass(rng.standard_normal(e - s), 3000) * (k / dur) ** 3
L[s:e] += (0.22 * riser + 0.3 * noise); R[s:e] += (0.22 * riser + 0.3 * noise)
braam(24.0, 55.0, 4.0, 0.7)      # THE LAST SCOOP
boom(24.0, 65, 1.0, 0.9)
chime(27.0, [1318.5, 1975.5, 2637.0], 0.16)   # brand sparkle
boom(27.0, 50, 0.45, 0.8)

mix = np.stack([L, R], axis=1)
mix *= 0.89 / np.max(np.abs(mix))
fade_n = at(1.0); mix[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None]
pcm = (mix * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1])
