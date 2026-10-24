"""Synthesise the 10.5s case-board retention cut: dark drone, eerie shimmer, room tone, pin thunks, string zips, riser and hit."""
import sys, wave
import numpy as np

SR = 48000
N = int(SR * 10.5)
t = np.arange(N) / SR
rng = np.random.default_rng(906)
L = np.zeros(N); R = np.zeros(N)
TRAVEL = [2.52, 3.05, 5.77, 7.91, 9.19]      # camera leaves for the next piece of evidence
ARRIVE = [0.02, 2.97, 3.5, 6.22, 8.36]      # camera lands on it
QUESTION = 9.24   # the closing question slams in

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

# Drone, a mid pad phones can hear, and a high pair a minor second apart.
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.6 * np.sin(2 * np.pi * 61.7 * t)
         + 0.4 * np.sin(2 * np.pi * 87.3 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)) * lfo
pad = onepole(rng.standard_normal(N), 700) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t))
pad += 0.25 * np.sin(2 * np.pi * 174.6 * t + 0.3 * np.sin(2 * np.pi * 0.3 * t))
pad += 0.06 * (np.sin(2 * np.pi * 932.3 * t) + np.sin(2 * np.pi * 987.8 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t - 1.2)) ** 2
add(fade(0.22 * drone + 0.5 * pad, 0.25, 1.2), 0, 0.5)
# Room tone: a quiet, dark room around the board.
add(fade(onepole(onepole(rng.standard_normal(N), 900), 120, high=True), 0.5, 1.0), 0, 0.12)

def thunk():
    n = int(0.25 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * (140 - 200 * tt) * tt) * env(n, 0.002, 0.05)
            + 0.5 * onepole(rng.standard_normal(n), 2500) * env(n, 0.001, 0.012))

def zip_(dur=0.5):
    n = int(dur * SR); x = rng.standard_normal(n)
    out = np.empty(n); acc = 0.0
    for i, v in enumerate(x):
        c = 600 + 2600 * i / n
        a = np.exp(-2 * np.pi * c / SR); acc = (1 - a) * v + a * acc; out[i] = acc
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2

def hit(dur=1.6, f0=75, f1=34):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt * 6)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.45) + 0.4 * onepole(rng.standard_normal(n), 3000) * env(n, 0.001, 0.03)

for k, tr in enumerate(TRAVEL[:-1]):
    add(zip_(), tr, 0.6, (-0.3 if k % 2 else 0.3))
for ar in ARRIVE:
    add(thunk(), ar, 0.7)
add(zip_(0.8), TRAVEL[-1], 0.8)
n = at(1.3); tt = np.arange(n) / SR
riser = onepole(rng.standard_normal(n), 2500) * (tt / tt[-1]) ** 2
riser += 0.3 * np.sin(2 * np.pi * np.cumsum(200 + 500 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1])
add(riser, QUESTION - 1.3, 0.5)
add(hit(), QUESTION + 0.01, 1.0)

mix = np.stack([L, R], 1)
mix /= np.abs(mix).max() / 0.85
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "bed.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
