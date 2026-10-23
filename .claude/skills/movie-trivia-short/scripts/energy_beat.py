#!/usr/bin/env python3
"""Synthesise a high-energy electro/EDM beat (four-on-the-floor kick, offbeat hats, claps, pumping
supersaw chords, bright pluck lead, snare-roll riser into a drop) — no samples, no licensing.

usage: energy_beat.py OUT.wav [--dur 18.9] [--bpm 150] [--drop 8.1] [--seed 5]

Energetic from the first frame (the hook); a snare roll and noise riser build over the bar before
--drop (put it on the "แต่" line), then the full drop with lead and wider chords.
Mix about 8 dB under the voice (data-volume ~0.22 after loudnorm to -16 LUFS).
"""
import argparse
import wave

import numpy as np

SR = 48000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=18.9)
    ap.add_argument("--bpm", type=float, default=150)
    ap.add_argument("--drop", type=float, default=8.1)
    ap.add_argument("--seed", type=int, default=5)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    n = int(a.dur * SR)
    t = np.arange(n) / SR
    L, R = np.zeros(n), np.zeros(n)
    beat = 60 / a.bpm
    s16 = beat / 4

    def place(sig, at, g=1.0, pan=0.0):
        s = int(at * SR)
        if s >= n or s < 0:
            return
        e = min(n, s + len(sig))
        L[s:e] += sig[: e - s] * g * (1 - max(0.0, pan))
        R[s:e] += sig[: e - s] * g * (1 + min(0.0, pan))

    def env(length, decay):
        k = np.arange(int(length * SR)) / SR
        return k, np.exp(-k / decay)

    def kick():
        k, e = env(0.3, 0.08)
        return np.tanh(3 * np.sin(2 * np.pi * (50 + 160 * np.exp(-k * 40)) * k)) * e

    def clap():
        k, e = env(0.2, 0.05)
        noise = rng.standard_normal(len(k))
        noise -= np.convolve(noise, np.ones(10) / 10, "same")
        burst = np.ones(len(k))
        for off in (0.0, 0.01, 0.02):  # three quick hits = clap
            burst[int(off * SR): int(off * SR) + 200] *= 1.6
        return noise * e * burst * 0.6

    def hat(open_=False):
        k, e = env(0.15 if open_ else 0.04, 0.06 if open_ else 0.01)
        noise = rng.standard_normal(len(k))
        return (noise - np.convolve(noise, np.ones(3) / 3, "same")) * e * 0.4

    def saw(freq, length):
        k = np.arange(int(length * SR)) / SR
        x = np.zeros(len(k))
        for det in (-0.12, -0.05, 0, 0.05, 0.12):  # supersaw: 5 detuned saws
            f = freq * 2 ** (det / 12)
            x += 2 * ((k * f + rng.uniform()) % 1) - 1
        return x / 5

    def pluck(freq, length=0.18):
        k, e = env(length, 0.06)
        return (2 * ((k * freq) % 1) - 1 + 0.5 * np.sign(np.sin(2 * np.pi * freq * 2 * k))) * e * 0.5

    def hz(m):
        return 440 * 2 ** ((m - 69) / 12)

    # i - VI - III - VII in E minor: Em, C, G, D (bright, driving)
    prog = [[52, 55, 59, 64], [48, 52, 55, 60], [55, 59, 62, 67], [50, 54, 57, 62]]
    roots = [40, 36, 43, 38]
    lead = [76, 79, 83, 79, 76, 74, 76, 79, 72, 76, 79, 76, 74, 71, 74, 79]  # 16th-note riff per bar
    bar = 4 * beat
    pump = np.ones(n)  # sidechain envelope: duck the chords on every kick
    b, bt = 0, 0.0
    while bt < a.dur:
        dropped = bt >= a.drop
        building = a.drop - bar <= bt < a.drop
        chord = prog[b % 4]
        # chords: offbeat stabs before the drop, sustained pumping saws after
        if dropped:
            pad = sum(saw(hz(m), bar) for m in chord) / len(chord)
            place(pad, bt, 0.45, 0.0)
            place(saw(hz(chord[-1] + 12), bar), bt, 0.12, 0.5)
        else:
            for q in range(4):
                stab = sum(saw(hz(m), beat * 0.35) for m in chord) / len(chord)
                stab *= np.exp(-np.arange(len(stab)) / SR / 0.08)
                place(stab, bt + q * beat + beat / 2, 0.55, 0.0)
        # bass: driving 8ths on the root
        for e8 in range(8):
            k, e = env(beat / 2, beat / 3)
            place(np.tanh(2 * np.sin(2 * np.pi * hz(roots[b % 4]) * k)) * e * 0.7, bt + e8 * beat / 2,
                  1.0 if dropped else 0.75)
        # drums
        for q in range(4):
            tq = bt + q * beat
            if not building or q < 2:
                place(kick(), tq, 1.0)
                s = int(tq * SR)
                k = np.arange(min(int(beat * SR), n - s)) / SR
                pump[s: s + len(k)] = np.minimum(pump[s: s + len(k)], 0.25 + 0.75 * np.clip(k / (beat * 0.6), 0, 1))
            if q in (1, 3):
                place(clap(), tq, 0.9)
            place(hat(open_=True), tq + beat / 2, 0.55 if dropped else 0.4, 0.3)
            for sx in (1, 3):
                place(hat(), tq + sx * s16, 0.4, -0.3)
        # lead riff after the drop
        if dropped:
            for i, m in enumerate(lead):
                place(pluck(hz(m)), bt + i * s16, 0.32, 0.25 * np.sin(i))
        # build: snare roll speeding up + noise riser over the bar before the drop
        if building:
            steps = 16
            for i in range(steps):
                frac = i / steps
                place(clap(), bt + frac * bar, 0.3 + 0.6 * frac)
        bt += bar
        b += 1
    k = np.arange(int(bar * SR)) / SR
    riser = rng.standard_normal(len(k)) * (k / bar) ** 2 * 0.35
    riser -= np.convolve(riser, np.ones(30) / 30, "same")
    place(riser, a.drop - bar, 1.0)
    # crash-ish impact on the drop
    k, e = env(1.5, 0.4)
    place((rng.standard_normal(len(k)) * 0.5 + np.sin(2 * np.pi * 45 * k)) * e * 0.6, a.drop, 1.0)

    # apply sidechain pump to everything except it's already summed: approximate by mixing
    mix = np.stack([L, R], 1) * (0.55 + 0.45 * pump)[:, None]
    mix *= (np.clip(t / 0.01, 0, 1) * np.clip((a.dur - t) / 0.4, 0, 1))[:, None]
    mix = np.tanh(mix * 1.6)  # loud, glued
    mix /= np.abs(mix).max() / 0.9
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print(f"wrote {a.out}: {a.dur}s, {a.bpm} bpm, drop at {a.drop}s")


if __name__ == "__main__":
    main()
