"""Synthesise the 150s SFX track: alarms, snooze click, pen, rain, falls, heartbeat, door swell."""
import sys, wave
import numpy as np

SR = 48000
N = SR * 150
rng = np.random.default_rng(3)
L = np.zeros(N); R = np.zeros(N)

def at(s): return int(s * SR)

def lowpass(x, c):
    a = np.exp(-2 * np.pi * c / SR); y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc; y[i] = acc
    return y

def add(sig, start, gain=1.0, pan=0.0):
    s = at(start); e = min(N, s + len(sig)); sig = sig[: e - s] * gain
    L[s:e] += sig * (1 - max(0, pan)); R[s:e] += sig * (1 + min(0, pan))

def env(n, a, d):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR)); return e

def alarm(start, length, gain=0.22):
    t = start
    while t < start + length:
        for k in range(3):
            n = int(0.07 * SR); k_ = np.arange(n) / SR
            x = np.sign(np.sin(2 * np.pi * 2600 * k_)) * 0.5
            add(lowpass(x, 5000) * env(n, 0.002, 0.05), t + k * 0.1, gain, 0.4)
        t += 0.5

def click(start, gain=0.5):
    n = int(0.05 * SR); add(lowpass(rng.standard_normal(n), 3000) * env(n, 0.001, 0.01), start, gain, 0.4)

def thud(start, gain=0.9, f0=80):
    n = int(0.8 * SR); k = np.arange(n) / SR
    f = f0 * np.exp(-k * 8) + 35
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.18)
    x += lowpass(rng.standard_normal(n), 900) * env(n, 0.001, 0.05) * 0.6
    add(np.tanh(1.5 * x), start, gain)

def scribble(start, length, gain=0.12):
    n = int(length * SR); k = np.arange(n) / SR
    noise = rng.standard_normal(n); noise = noise - lowpass(noise, 1500)
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 7.5 * k) ** 2
    add(noise * am, start, gain)

def rain(start, length, gain=0.16):
    n = int(length * SR); k = np.arange(n) / SR
    x = lowpass(rng.standard_normal(n), 4000)
    fade = np.minimum(1, k / 0.6) * np.minimum(1, (length - k) / 0.6)
    add(x * fade, start, gain, -0.2); add(lowpass(rng.standard_normal(n), 4000) * fade, start, gain, 0.2)

def heartbeat(start, gain=0.7):
    for off in (0, 0.22):
        n = int(0.4 * SR); k = np.arange(n) / SR
        add(np.sin(2 * np.pi * (55 * np.exp(-k * 4) + 30) * k) * env(n, 0.005, 0.09), start + off, gain * (1 if off == 0 else 0.7))

def swell(start, length, gain=0.25):
    n = int(length * SR); k = np.arange(n) / SR
    x = lowpass(rng.standard_normal(n), 2500) * (k / length) ** 2
    add(x, start, gain)

alarm(3.0, 1.5); click(4.65, 0.6)
scribble(44.0, 2.6)
rain(56.0, 8.0); thud(62.6, 0.8)
thud(68.6, 0.6, 70)
for d in range(8): scribble(70.5 + d * 0.65, 0.22, 0.1)
heartbeat(107.2, 0.6); heartbeat(108.3, 0.6)
alarm(109.0, 2.0, 0.26)
thud(110.6, 0.35, 120)     # eyes snap open
swell(119.6, 3.2, 0.22)    # door light

mix = np.stack([L, R], axis=1)
mix *= 0.8 / max(1e-9, np.max(np.abs(mix)))
pcm = (mix * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1])
