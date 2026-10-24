"""Synthesise a 30s quiz-show score: clock pulse, bass, pad, whooshes, reveal dings."""
import sys, wave
import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)
BEAT = 0.5  # 120 bpm

FACTS = [3.0, 8.0, 13.0, 18.0, 23.0]   # scene starts
REVEAL = 2.4                           # ding offset into each fact
OUTRO = 28.0

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

def kick(start, gain=0.55):
    n = int(0.4 * SR); k = np.arange(n) / SR
    f = 110 * np.exp(-k * 18) + 45
    add(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.12), start, gain)

def tick(start, gain=0.12, pan=0.0):
    n = int(0.05 * SR)
    x = rng.standard_normal(n); x = x - lowpass(x, 5000)
    add(x * env(n, 0.001, 0.008), start, gain, pan)

def pluck(start, freq, gain=0.18, decay=0.18):
    n = int(0.6 * SR); k = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * freq * k)) * 0.5 + np.sin(2 * np.pi * freq * 2 * k) * 0.3
    add(lowpass(x, 900) * env(n, 0.003, decay), start, gain)

def pad(start, length, freqs, gain=0.06):
    n = int(length * SR); k = np.arange(n) / SR; x = np.zeros(n)
    for f in freqs:
        for det in (-0.6, 0.6):
            x += np.sin(2 * np.pi * (f + det) * k)
    fade = np.minimum(1, k / 0.3) * np.minimum(1, (length - k) / 0.3)
    add(x / (2 * len(freqs)) * fade, start, gain, -0.2)
    add(x / (2 * len(freqs)) * fade, start, gain, 0.2)

def ding(start, base=1046.5, gain=0.22):
    n = int(1.6 * SR); k = np.arange(n) / SR; x = np.zeros(n)
    for i, (m, a) in enumerate([(1, 1), (2.76, 0.4), (5.4, 0.2)]):
        x += a * np.sin(2 * np.pi * base * m * k) * np.exp(-k * (2.5 + i * 2))
    add(x, start, gain, 0.15)
    add(x, start + 0.09, gain * 0.7, -0.15)   # second strike, a fifth up feel
    n2 = int(1.6 * SR)
    y = np.sin(2 * np.pi * base * 1.5 * np.arange(n2) / SR) * np.exp(-np.arange(n2) / SR * 3)
    add(y, start + 0.09, gain * 0.5)

def whoosh(start, length, gain=0.22):
    n = int(length * SR)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    add(lowpass(rng.standard_normal(n), 2200) * shape, start, gain)

# chord per section (A minor-ish quiz loop): Am, F, C, G, Am, F, then C major for the outro
CHORDS = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7),
          (164.8, 207.7, 246.9), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6)]
ROOTS = [110.0, 87.3, 98.0, 82.4, 110.0, 87.3]
bounds = [0.0] + FACTS + [OUTRO]
for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
    pad(a, b - a + 0.15, CHORDS[i])
    beat = a
    while beat < b - 1e-6:
        kick(beat, 0.5 if beat > 0.4 else 0.0)
        tick(beat + BEAT / 2, 0.10, 0.3)
        pluck(beat, ROOTS[i] if int(round((beat - a) / BEAT)) % 2 == 0 else ROOTS[i] * 1.5)
        beat += BEAT

# clock ticks louder in the half-second before each reveal
for f in FACTS:
    for k in range(4):
        tick(f + REVEAL - 0.5 + k * 0.125, 0.18, -0.3)
    whoosh(f - 0.45, 0.6)
    ding(f + REVEAL)
whoosh(OUTRO - 0.45, 0.6)

# outro: C major sting
for f, g in [(261.6, 0.2), (329.6, 0.18), (392.0, 0.18), (523.3, 0.14)]:
    pluck(OUTRO, f, g, 0.9)
pad(OUTRO, 2.0, (261.6, 329.6, 392.0), 0.09)
kick(OUTRO, 0.7)
ding(OUTRO + 0.5, 1318.5, 0.16)

mix = np.stack([L, R], axis=1)
mix *= 0.89 / np.max(np.abs(mix))
fade_n = at(0.8); mix[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None]
pcm = (mix * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1])
