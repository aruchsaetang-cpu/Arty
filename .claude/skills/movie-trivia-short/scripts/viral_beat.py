#!/usr/bin/env python3
"""Synthesise a short phonk-style beat (cowbell riff, 808, kick, snare, hats) — no samples, no licensing.

usage: viral_beat.py OUT.wav [--dur 20.5] [--bpm 130] [--drop 4.0] [--seed 1]

Intro (filtered cowbell riff only) until --drop, then the full beat; 1.5 s fade at the end.
Put the drop on the "แต่" line or right after the hook. Mix it under the voice at about
data-volume 0.10–0.14 after loudnorm to -16 LUFS.
"""
import argparse
import wave

import numpy as np

SR = 48000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=20.5)
    ap.add_argument("--bpm", type=float, default=130)
    ap.add_argument("--drop", type=float, default=4.0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    n = int(a.dur * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(a.seed)
    beat = 60 / a.bpm
    step = beat / 4  # 16th notes

    def place(sig, t, g=1.0):
        s = int(t * SR)
        if s >= n:
            return
        e = min(n, s + len(sig))
        out[s:e] += sig[: e - s] * g

    def env(length, decay):
        k = np.arange(int(length * SR)) / SR
        return k, np.exp(-k / decay)

    # cowbell: two detuned square-ish partials, short decay (the phonk signature)
    def cowbell(freq):
        k, e = env(0.25, 0.07)
        x = np.sign(np.sin(2 * np.pi * freq * k)) * 0.5 + np.sign(np.sin(2 * np.pi * freq * 1.48 * k)) * 0.5
        return x * e * 0.35

    def kick():
        k, e = env(0.35, 0.09)
        return np.sin(2 * np.pi * (45 + 110 * np.exp(-k * 35)) * k) * e

    def snare():
        k, e = env(0.2, 0.05)
        return (rng.standard_normal(len(k)) * 0.6 + np.sin(2 * np.pi * 190 * k) * 0.4) * e

    def hat():
        k, e = env(0.05, 0.012)
        return rng.standard_normal(len(k)) * e * 0.25

    def bass(freq, length):
        k, e = env(length, length * 0.8)
        x = np.tanh(2.5 * np.sin(2 * np.pi * freq * k))  # saturated 808
        return x * e * 0.6

    # 2-bar cowbell riff in A minor (semitones from A4), 16th-note grid
    riff = [0, None, 0, 3, None, 5, None, 3, 7, None, 5, None, 3, None, 0, None,
            0, None, 0, 3, None, 5, None, 7, 10, None, 7, None, 5, None, 3, None]
    roots = [55.0, 55.0, 43.65, 49.0]  # A1, A1, F1, G1 per bar
    t, i = 0.0, 0
    while t < a.dur:
        bar = int(t / (beat * 4))
        pos = i % 32
        semi = riff[pos]
        dropped = t >= a.drop
        if semi is not None:
            place(cowbell(440 * 2 ** (semi / 12)), t, 1.0 if dropped else 0.55)
        if dropped:
            sixteenth = i % 16
            if sixteenth in (0, 6, 10):
                place(kick(), t)
            if sixteenth in (4, 12):
                place(snare(), t, 0.8)
            if sixteenth % 2 == 0 or (sixteenth in (13, 15)):
                place(hat(), t)
            if sixteenth == 0:
                place(bass(roots[bar % 4], beat * 3.5), t)
        t += step
        i += 1
    # fade in/out, normalise
    tt = np.arange(n) / SR
    out *= np.clip(tt / 0.05, 0, 1) * np.clip((a.dur - tt) / 1.5, 0, 1)
    out = np.tanh(out * 1.2)
    out /= np.abs(out).max() / 0.85
    pcm = (np.stack([out, out], 1) * 32767).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {a.out}: {a.dur}s, {a.bpm} bpm, drop at {a.drop}s")


if __name__ == "__main__":
    main()
