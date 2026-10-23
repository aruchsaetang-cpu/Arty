"""Synthesise a quiet tension bed for the BTTF short (no samples, no licensing).

usage: python3 music.py OUT.wav [duration]
A-minor pad with a held high tone (like the reference's ~700 Hz / 1.2 kHz bed), a soft
heartbeat pulse, a riser into the turn at 15.07 s ("แต่มีเทคหนึ่ง"), a low hit on the turn,
then a resolve to A major at 25.28 s ("โชคดี") and a fade out.
"""
import sys
import wave

import numpy as np

SR = 48000
OUT = sys.argv[1]
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 30.2
TURN, RESOLVE = 15.07, 25.28
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(3)


def smoothstep(a, b):
    x = np.clip((t - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


def tone(freq, detune=0.0, vib=0.0):
    ph = 2 * np.pi * (freq + detune) * t + vib * np.sin(2 * np.pi * 0.21 * t)
    return np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)


def onepole(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


# pad: A minor until the resolve, then A major (C -> C#)
minor = smoothstep(RESOLVE + 0.6, RESOLVE - 0.4)
major = 1 - minor
pad = (tone(110, 0.0) + tone(220, 0.3) + tone(329.63, -0.4)
       + minor * tone(261.63, 0.2) + major * tone(277.18, 0.2)) / 5
pad *= 0.55 + 0.15 * np.sin(2 * np.pi * 0.11 * t)  # slow breathing
# held high tones (reference bed sits around 700 Hz and 1.2 kHz)
high = 0.18 * np.sin(2 * np.pi * 659.25 * t + 0.6 * np.sin(2 * np.pi * 4.5 * t)) \
    + 0.08 * np.sin(2 * np.pi * 1318.5 * t)
high *= 0.6 + 0.4 * smoothstep(8, TURN)

# heartbeat pulse at 80 bpm, louder as the turn approaches, gone after the resolve
pulse = np.zeros(N)
beat = 60 / 80
k = np.arange(int(0.18 * SR)) / SR
thump = np.sin(2 * np.pi * (55 + 40 * np.exp(-k * 30)) * k) * np.exp(-k * 18)
for start in np.arange(0.0, RESOLVE, beat):
    for off, g in ((0.0, 1.0), (0.22, 0.6)):
        s = int((start + off) * SR)
        e = min(N, s + len(thump))
        pulse[s:e] += thump[: e - s] * g
pulse *= 0.25 + 0.75 * smoothstep(4, TURN)
pulse *= 1 - smoothstep(RESOLVE - 1.0, RESOLVE)

# riser: filtered noise sweeping up over the 3 s before the turn, cut at the turn
noise = rng.standard_normal(N)
riser = onepole(noise, 2500) * smoothstep(TURN - 3, TURN) * (t < TURN)
# hit on the turn: low boom + short noise burst
hit = np.zeros(N)
s = int(TURN * SR)
k = np.arange(int(2.5 * SR)) / SR
boom = np.sin(2 * np.pi * (45 + 30 * np.exp(-k * 8)) * k) * np.exp(-k * 1.6)
burst = onepole(rng.standard_normal(len(k)), 1800) * np.exp(-k * 10)
e = min(N, s + len(k))
hit[s:e] = (boom + 0.6 * burst)[: e - s]

mix = 0.55 * pad + high + 0.9 * pulse + 0.35 * riser + 0.8 * hit
# duck the bed a little right after the hit so the "แต่" line reads
mix *= 1 - 0.35 * (smoothstep(TURN, TURN + 0.2) - smoothstep(TURN + 2, TURN + 4))
mix *= smoothstep(0, 0.8) * (1 - smoothstep(DUR - 2.5, DUR))  # fade in/out
mix /= np.abs(mix).max() / 0.8

# light stereo width: delay the right channel by 11 ms
d = int(0.011 * SR)
left, right = mix, np.concatenate([np.zeros(d), mix[:-d]])
pcm = (np.stack([left, right], 1) * 32767).astype(np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {OUT} ({DUR}s)")
