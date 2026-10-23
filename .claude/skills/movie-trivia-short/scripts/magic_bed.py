#!/usr/bin/env python3
"""Synthesise a light, magical music bed for animated / fairy-tale topics (music box + soft pad +
sparkles) — no samples, no licensing.

usage: magic_bed.py OUT.wav [--dur 18.9] [--reveal 8.1] [--bpm 96] [--seed 2]

A gentle music-box waltz (3/4) over a warm pad, a soft chime build into --reveal (put it on the
"แต่" line), a sparkle sweep on the reveal, then fuller voicing until a short fade at the end.
Mix it under the voice at about data-volume 0.12–0.16 after loudnorm to -16 LUFS.
"""
import argparse
import wave

import numpy as np

SR = 48000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=18.9)
    ap.add_argument("--reveal", type=float, default=8.1)
    ap.add_argument("--bpm", type=float, default=96)
    ap.add_argument("--seed", type=int, default=2)
    a = ap.parse_args()
    n = int(a.dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(a.seed)
    L, R = np.zeros(n), np.zeros(n)

    def place(sig, start, g=1.0, pan=0.0):
        s = int(start * SR)
        if s >= n:
            return
        e = min(n, s + len(sig))
        L[s:e] += sig[: e - s] * g * (1 - max(0.0, pan))
        R[s:e] += sig[: e - s] * g * (1 + min(0.0, pan))

    def musicbox(freq, length=1.6):
        k = np.arange(int(length * SR)) / SR
        env = np.exp(-k * 3.2) * np.clip(k / 0.004, 0, 1)
        # bright, slightly inharmonic partials like a tine
        x = np.sin(2 * np.pi * freq * k) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * k) * np.exp(-k * 6) \
            + 0.12 * np.sin(2 * np.pi * freq * 5.4 * k) * np.exp(-k * 10)
        return x * env * 0.32

    def hz(semi):  # semitones from A4
        return 440 * 2 ** (semi / 12)

    beat = 60 / a.bpm
    bar = beat * 3
    # D major waltz: chord roots per bar (D, Bm, G, A) and a 6-note melody per bar (8th notes)
    chords = [[-7, -3, 0], [-10, -7, -3], [-14, -10, -7], [-12, -8, -5]]   # D, Bm, G, A (around A3–D4)
    melody = [[5, 9, 12, 9, 7, 5], [2, 5, 9, 5, 4, 2], [-2, 2, 5, 9, 7, 5], [4, 7, 11, 7, 9, 12]]
    b, start = 0, 0.0
    while start < a.dur:
        ch, mel = chords[b % 4], melody[b % 4]
        after = start >= a.reveal
        # pad: soft sustained chord across the bar
        k = np.arange(int(bar * 1.05 * SR)) / SR
        pad = sum(np.sin(2 * np.pi * hz(s - 12) * k) + 0.3 * np.sin(2 * np.pi * hz(s) * k) for s in ch) / len(ch)
        pad *= np.sin(np.pi * np.clip(k / (bar * 1.05), 0, 1)) * (0.22 if after else 0.14)
        place(pad, start, 1.0, 0.0)
        # waltz bass "oom-pah-pah" on the music box an octave down
        place(musicbox(hz(ch[0] - 12), 1.2), start, 0.8)
        for j in (1, 2):
            for s in ch[1:]:
                place(musicbox(hz(s), 0.6), start + j * beat, 0.35, 0.2 * (j - 1.5))
        # melody: sparse before the reveal (quarter notes), full 8ths after
        step = beat / 2
        for j, s in enumerate(mel):
            if not after and j % 2:
                continue
            place(musicbox(hz(s + 12)), start + j * step, 0.9, 0.3 * np.sin(j))
        start += bar
        b += 1
    # chime build into the reveal: rising arpeggio over the last bar before it
    arp = [5, 9, 12, 17, 21, 24]
    for j, s in enumerate(arp):
        place(musicbox(hz(s + 12), 1.0), a.reveal - bar + j * bar / len(arp), 0.5 + 0.1 * j, 0.4 * (-1) ** j)
    # sparkle sweep on the reveal: shimmering high noise + glints
    k = np.arange(int(1.4 * SR)) / SR
    shimmer = rng.standard_normal(len(k))
    shimmer = np.convolve(shimmer, np.ones(8) / 8, "same") * np.exp(-k * 3) * 0.18
    place(shimmer - np.convolve(shimmer, np.ones(64) / 64, "same"), a.reveal, 1.0)  # crude high-pass
    for j in range(10):
        place(musicbox(hz(24 + rng.integers(0, 12)), 0.5), a.reveal + rng.uniform(0, 1.0), 0.35, rng.uniform(-0.8, 0.8))

    mix = np.stack([L, R], 1)
    fade = np.clip(t / 0.3, 0, 1) * np.clip((a.dur - t) / 1.2, 0, 1)
    mix *= fade[:, None]
    mix = np.tanh(mix * 1.1)
    mix /= np.abs(mix).max() / 0.85
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print(f"wrote {a.out}: {a.dur}s, reveal sparkle at {a.reveal}s")


if __name__ == "__main__":
    main()
