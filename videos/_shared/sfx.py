"""Synthesised sound effects for the stick-figure shorts (no samples, no licences).

usage (from a project's make_sfx.py):
    from sfx import render
    render([(seconds, "coin", gain), ...], duration_s, "assets/sfx.wav")
"""
import wave
import numpy as np

SR = 44100


def _t(d):
    return np.arange(int(d * SR)) / SR


def _env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def _noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def _band(x, lo, hi, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR) + 1e-6
    g = 1 / np.sqrt(1 + (lo / f) ** (2 * order)) if lo else 1
    g = g * (1 / np.sqrt(1 + (f / hi) ** (2 * order)) if hi else 1)
    return np.fft.irfft(X * g, len(x))


def _partials(fs, d, decays, amps=None):
    t = _t(d)
    amps = amps or [1] * len(fs)
    return sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / k) for f, k, a in zip(fs, decays, amps))


def thud(seed=1):
    t = _t(0.45)
    body = np.sin(2 * np.pi * (60 * t + 40 * (1 - np.exp(-t / 0.05)) * 0.05)) * np.exp(-t / 0.14)
    return 0.9 * body + 0.5 * _band(_noise(len(t), seed), 0, 300) * np.exp(-t / 0.05)


def clank(seed=2):
    x = _partials([523, 1287, 2111, 3170, 4400], 0.5, [0.18, 0.1, 0.07, 0.05, 0.03], [1, 0.7, 0.5, 0.35, 0.2])
    n = _band(_noise(len(x), seed), 1500, 8000) * _env(len(x), 0.0005, 0.01)
    return 0.5 * x + 0.4 * n


def click(seed=3):
    n = int(0.03 * SR)
    a = _band(_noise(n, seed), 2000, 12000) * _env(n, 0.0002, 0.004)
    out = np.zeros(int(0.12 * SR)); out[:n] += a; out[int(0.07 * SR):int(0.07 * SR) + n] += 0.7 * a
    return out


def coin(seed=4):
    x = _partials([2093, 3136, 4699, 6272], 0.6, [0.25, 0.18, 0.12, 0.08], [1, 0.6, 0.4, 0.25])
    out = np.zeros(int(0.7 * SR)); out[:len(x)] += x
    d = int(0.07 * SR); out[d:d + len(x)] += 0.4 * x[: len(out) - d]
    return 0.5 * out


def kaching(seed=5):
    out = np.zeros(int(0.9 * SR))
    c = click(seed); out[:len(c)] += 0.6 * c
    b = _partials([1318, 1760, 2637], 0.8, [0.4, 0.3, 0.2], [1, 0.7, 0.4]); s = int(0.06 * SR)
    out[s:s + len(b)] += 0.45 * b[: len(out) - s]
    return out


def paper(seed=6):
    t = _t(0.22)
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 38 * t) ** 2
    return _band(_noise(len(t), seed), 1200, 6000) * am * np.exp(-t / 0.08) * 0.8


def whoosh(seed=7):
    t = _t(0.4)
    x = _band(_noise(len(t), seed), 300, 3000) * np.sin(np.pi * t / 0.4) ** 2
    return 0.7 * x


def step(seed=8):
    t = _t(0.1)
    return _band(_noise(len(t), seed), 60, 600) * np.exp(-t / 0.02) * 0.9


def pop(seed=9):
    t = _t(0.14)
    return np.sin(2 * np.pi * (300 * t + 3000 * t * t)) * np.exp(-t / 0.04) * 0.7


def tick(seed=10):
    t = _t(0.03)
    return _band(_noise(len(t), seed), 3000, 12000) * np.exp(-t / 0.003) * 0.8


def ding(seed=11):
    return 0.45 * _partials([880, 1320, 1760, 2640], 1.6, [0.9, 0.6, 0.4, 0.25], [1, 0.5, 0.35, 0.2])


def chalk(seed=12):
    t = _t(0.2)
    rough = np.abs(_band(_noise(len(t), seed + 50), 20, 120)); rough /= rough.max() + 1e-9
    return _band(_noise(len(t), seed), 2500, 7000) * rough * np.sin(np.pi * t / 0.2) * 0.9


def buzz(seed=13):
    t = _t(0.45)
    sq = np.sign(np.sin(2 * np.pi * 110 * t))
    return _band(sq, 0, 1200) * np.minimum(1, t / 0.01) * np.exp(-t / 0.3) * 0.35


def cheer(seed=14):
    t = _t(2.0)
    x = sum(_band(_noise(len(t), seed + i), 400 + 150 * i, 2500 + 300 * i) * (0.6 + 0.4 * np.sin(2 * np.pi * (2 + i) * t + i)) for i in range(4))
    return x / 4 * np.minimum(1, t / 0.3) * np.exp(-np.maximum(0, t - 1.2) / 0.4) * 0.8


def sparkle(seed=15):
    out = np.zeros(int(0.8 * SR))
    for i, f in enumerate([1568, 2093, 2637, 3136]):
        b = _partials([f, f * 2.01], 0.4, [0.15, 0.08]); s = int(i * 0.06 * SR); out[s:s + len(b)] += 0.35 * b
    return out


def splash(seed=16):
    t = _t(0.9)
    return _band(_noise(len(t), seed), 200, 5000) * np.minimum(1, t / 0.01) * np.exp(-t / 0.25) * 0.9


def pour(seed=17):
    t = _t(0.35)
    am = 0.7 + 0.3 * np.sin(2 * np.pi * 23 * t)
    return _band(_noise(len(t), seed), 600, 3500) * am * np.sin(np.pi * t / 0.35) * 0.45


SOUNDS = {k: v for k, v in globals().items() if callable(v) and not k.startswith("_") and k not in ("render",)}


def render(events, duration, path, peak_db=-3.0):
    out = np.zeros(int(duration * SR) + SR)
    for i, (sec, name, gain) in enumerate(events):
        x = SOUNDS[name](seed=i + 1) * gain
        s = int(sec * SR)
        if s >= len(out):
            continue
        out[s:s + len(x)] += x[: len(out) - s]
    out = out[: int(duration * SR)]
    out *= 10 ** (peak_db / 20) / (np.abs(out).max() + 1e-9)
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(path, len(events), "events", f"{duration:.2f}s")
