#!/usr/bin/env python3
"""Synthesise a bouncy lo-fi swing beat (plucked nylon-style guitar chords, boom-bap drums with swung
hats, round bass, light vinyl crackle) — the feel of the trending movie-fact sounds, no samples.

usage: swing_beat.py OUT.wav [--dur 18.9] [--bpm 88] [--drop 8.1] [--seed 4]

Drums are thin before --drop and full after it (put the drop on the "แต่" line).
These channels mix the music fairly loud: about 10–12 dB under the voice (data-volume ~0.22 after
loudnorm to -16 LUFS), not the 20 dB used for the tension beds.
"""
import argparse
import wave

import numpy as np

SR = 48000


def pluck(freq, length, rng, bright=0.5):
    """Karplus-Strong string"""
    n = int(length * SR)
    p = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, p)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * (bright * buf[i % p] + (1 - bright) * buf[(i + 1) % p])
    return out * np.clip(np.arange(n) / 30, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=18.9)
    ap.add_argument("--bpm", type=float, default=88)
    ap.add_argument("--drop", type=float, default=8.1)
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    n = int(a.dur * SR)
    L, R = np.zeros(n), np.zeros(n)

    def place(sig, t, g=1.0, pan=0.0):
        s = int(t * SR)
        if s >= n or s < 0:
            return
        e = min(n, s + len(sig))
        L[s:e] += sig[: e - s] * g * (1 - max(0.0, pan))
        R[s:e] += sig[: e - s] * g * (1 + min(0.0, pan))

    def env(length, decay):
        k = np.arange(int(length * SR)) / SR
        return k, np.exp(-k / decay)

    def kick():
        k, e = env(0.4, 0.12)
        return np.sin(2 * np.pi * (48 + 90 * np.exp(-k * 28)) * k) * e

    def snare():
        k, e = env(0.25, 0.07)
        noise = rng.standard_normal(len(k))
        noise = noise - np.convolve(noise, np.ones(12) / 12, "same")
        return (noise * 0.7 + np.sin(2 * np.pi * 200 * k) * 0.3) * e

    def hat(open_=False):
        k, e = env(0.12 if open_ else 0.04, 0.05 if open_ else 0.01)
        noise = rng.standard_normal(len(k))
        return (noise - np.convolve(noise, np.ones(4) / 4, "same")) * e * 0.35

    def bass(freq, length):
        k, e = env(length, length * 0.7)
        return np.tanh(1.6 * np.sin(2 * np.pi * freq * k)) * e * 0.55

    def hz(midi):
        return 440 * 2 ** ((midi - 69) / 12)

    beat = 60 / a.bpm
    swing = 0.62  # second 8th lands at 62% of the beat
    # Am7 - D9 - Gmaj7 - E7 (one chord per bar), voiced around the guitar's middle register
    prog = [([57, 60, 64, 67], 45), ([57, 62, 64, 66], 50), ([55, 59, 62, 66], 43), ([56, 59, 62, 64], 52)]
    strums = {}
    bar_t, b = 0.0, 0
    while bar_t < a.dur:
        chord, root = prog[b % 4]
        full = bar_t >= a.drop
        # guitar: syncopated stabs (1, 2&, 3&, 4) with a small strum spread
        for beat_pos in (0, 1 + swing, 2 + swing, 3):
            t0 = bar_t + beat_pos * beat
            for j, m in enumerate(chord):
                key = (m, b % 4)
                if key not in strums:
                    strums[key] = pluck(hz(m), 1.2, rng, bright=0.45)
                place(strums[key], t0 + j * 0.012, 0.28, -0.3 + 0.2 * j)
        # bass on 1 and 3&
        place(bass(hz(root), beat * 1.6), bar_t, 1.0 if full else 0.6)
        place(bass(hz(root + 7), beat * 0.9), bar_t + (2 + swing) * beat, 0.8 if full else 0.5)
        # drums
        for q in range(4):
            tq = bar_t + q * beat
            if q in (0, 2) or (full and q == 2):
                place(kick(), tq, 1.0 if full else 0.55)
            if full and q == 2:
                place(kick(), tq + swing * beat, 0.6)
            if q in (1, 3):
                place(snare(), tq, 0.75 if full else 0.35)
            place(hat(), tq, 0.9 if full else 0.5, 0.3)
            place(hat(open_=(q == 3 and full)), tq + swing * beat, 0.7 if full else 0.4, 0.3)
        bar_t += 4 * beat
        b += 1
    # vinyl crackle bed
    crack = np.zeros(n)
    idx = rng.integers(0, n, int(a.dur * 30))
    crack[idx] = rng.uniform(-1, 1, len(idx))
    crack = np.convolve(crack, np.exp(-np.arange(40) / 6), "same") * 0.05
    L += crack
    R += crack
    t = np.arange(n) / SR
    mix = np.stack([L, R], 1) * (np.clip(t / 0.05, 0, 1) * np.clip((a.dur - t) / 0.8, 0, 1))[:, None]
    # warm it: gentle low-pass + saturation
    mix = np.tanh(np.apply_along_axis(lambda c: np.convolve(c, np.ones(3) / 3, "same"), 0, mix) * 1.3)
    mix /= np.abs(mix).max() / 0.85
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print(f"wrote {a.out}: {a.dur}s, {a.bpm} bpm swing, full drums from {a.drop}s")


if __name__ == "__main__":
    main()
