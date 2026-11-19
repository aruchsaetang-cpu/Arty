"""Synthesize the music bed and SFX stems for "Aura Monster" (numpy), with real recordings layered in where present:
the user's footsteps (audio/footsteps/) and Openverse sounds (audio/sfx/, credits in audio/sfx/CREDITS.md).

    python3 shorts/aura/audio.py   -> shorts/aura/audio/music.wav, sfx.wav  (48 kHz stereo)
Timing follows beats.json (v2): the rain slows and muffles in the slow-motion reveal, the music drops out at the turn,
comes back warm for the training, swells when the umbrella closes, and resolves for the payoff.
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
beats = json.load(open(os.path.join(HERE, "beats.json")))
DUR = beats["duration"]; n = int(DUR * SR)
B = {b["id"]: b for b in beats["shots"]}
FPS = 30
SENTS = json.load(open(os.path.join(HERE, "sentences.json")))
FREEZE = beats["slow0"] / FPS; SLOW1 = beats["slow1"] / FPS          # slow-motion window (rain crawls)
PAYOFF = B["payoff_two"]["start"]; TURN = B["turn"]["start"]; REVEAL = B["reveal_low"]["start"]
TRAIN = B["train_roof"]["start"]; CLOSE = B["close"]["start"]
rng = np.random.default_rng(3)
t = np.arange(n) / SR

def env(points):
    """Piecewise-linear envelope from [(time, gain), ...]."""
    ts, gs = zip(*points); return np.interp(t, ts, gs)

def lp(x, cutoff):  # fast one-pole via cumulative filter in blocks
    from scipy.signal import lfilter
    a = np.exp(-2 * np.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], x)

def hp(x, cutoff):
    return x - lp(x, cutoff)

def stereo(x, width=0.3, seed=0):
    d = int(SR * 0.011 * (1 + seed % 3))
    r = np.concatenate([np.zeros(d), x[:-d]])
    return np.stack([x, (1 - width) * x + width * r], 1)

# ------------------------------------------------------------------ music: slow minor pad + plucked motif
def pad(freqs, start, end, gain=1.0):
    out = np.zeros(n)
    i0, i1 = int(start * SR), min(n, int(end * SR)); tt = t[i0:i1] - start
    for k, f in enumerate(freqs):
        for det in (-0.12, 0.0, 0.13):          # detuned saw-ish stack, softened
            ph = 2 * np.pi * f * (1 + det / 100) * tt
            out[i0:i1] += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)) / (1 + k * 0.3)
    a = np.clip(np.minimum((t - start) / 1.6, (end - t) / 1.6), 0, 1)
    return out * a * gain

def pluck(f, at, gain=1.0, decay=1.4):
    i0 = int(at * SR); L = min(n - i0, int(SR * 3.0)); tt = np.arange(L) / SR
    x = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 6)) * np.exp(-tt / decay * 3)
    out = np.zeros(n); out[i0:i0 + L] = x * gain; return out

A2, C3, D3, E3, F3, G3, A3, C4, E4, G4, A4, B3 = 110, 130.81, 146.83, 164.81, 174.61, 196, 220, 261.63, 329.63, 392, 440, 246.94
prog = [(A2, E3, A3, C4), (F3 / 2, C3, F3, A3), (C3, G3, C4, E4), (G3 / 2, D3, G3, B3)]
music = np.zeros(n); bar = 3.4
tt0 = 0.0; k = 0
while tt0 < TURN + 0.4:
    ch = prog[k % 4]; music += pad(ch, tt0, min(tt0 + bar + 0.8, TURN + 0.8), 0.35 if tt0 < REVEAL else 0.55)
    tt0 += bar; k += 1
motif = [A4, E4, G4, E4, C4 * 2, B3 * 2, A4, E4]
for i, at in enumerate(np.arange(1.0, TURN, 0.85)):
    if FREEZE - 0.2 < at < FREEZE + 1.6:  # hold the breath when time stops
        continue
    music += pluck(motif[i % len(motif)] / 2, at, 0.18)
tt0 = TRAIN - 0.3; k = 0                                               # training: the progression comes back, warmer
while tt0 < CLOSE:
    music += pad(prog[k % 4], tt0, min(tt0 + bar + 0.8, CLOSE + 0.6), 0.45); tt0 += bar; k += 1
for i, at in enumerate(np.arange(TRAIN + 0.4, CLOSE - 0.3, 0.85)):
    music += pluck(motif[i % len(motif)] / 2, at, 0.15)
music += pad((A2, E3, A3, C4, E4), CLOSE - 0.1, DUR, 0.5)             # the umbrella closes: resolve through the payoff
music += pad((A2 / 2,), 0.0, DUR, 0.25)                                # sub drone under everything
music *= env([(0, 0), (1.2, 1), (FREEZE - 0.1, 1), (FREEZE + 0.2, 0.55), (TURN - 0.3, 0.9), (TURN + 0.6, 0.15),
              (TRAIN - 0.3, 0.2), (TRAIN + 1.0, 0.8), (CLOSE - 0.2, 0.7), (CLOSE + 1.2, 1), (DUR - 1.5, 1), (DUR, 0)])
music = lp(music, 2800)

# ------------------------------------------------------------------ SFX
sfx = np.zeros((n, 2))
rain = rng.standard_normal(n); rain = hp(lp(rain, 3800), 500) * 0.5 + lp(rng.standard_normal(n), 250) * 0.5
drops = (rng.random(n) < 0.0009) * rng.standard_normal(n) * 3.0
rain = rain + lp(drops, 4000)
SFXD = os.path.join(HERE, "audio", "sfx")
def rec(name, t0=0.0, dur=None):
    """A recording from audio/sfx/ (Openverse, see CREDITS.md) as mono float at SR, or None when absent."""
    import subprocess
    path = os.path.join(SFXD, name + ".wav")
    if not os.path.exists(path): return None
    a = ["ffmpeg", "-v", "error", "-ss", str(t0)] + (["-t", str(dur)] if dur else []) + ["-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    return np.frombuffer(subprocess.run(a, capture_output=True, check=True).stdout, "<i2").astype(np.float64) / 32768
def rms(x): return np.sqrt((x ** 2).mean()) + 1e-12
real = rec("storm_cc0", 16.0, DUR + 0.5)                               # real rain (the steady middle of the take, no gusts)
if real is not None and len(real) >= n:
    real = hp(real[:n], 250); real *= rms(rain) / rms(real)
    rain = 0.45 * rain + 0.85 * real                                   # recorded rain on top, the synth fills the low end
slow = env([(0, 0), (FREEZE - 0.05, 0), (FREEZE + 0.25, 1), (SLOW1 - 0.2, 1), (SLOW1 + 0.15, 0), (DUR, 0)])
rain = rain * (1 - slow) + lp(rain, 520) * slow * 1.6                  # slow motion: the storm goes dull and heavy
rain *= env([(0, 0), (0.8, 1), (FREEZE - 0.05, 1), (FREEZE + 0.25, 0.55), (SLOW1 - 0.2, 0.55), (SLOW1 + 0.15, 1),
             (DUR - 0.8, 1), (DUR, 0.6)])
RAIN = stereo(rain, 0.6, 1)

def place(x, at, gain=1.0, width=0.4, seed=2):
    i0 = int(at * SR); L = min(len(x), n - i0); s = stereo(x[:L], width, seed) * gain
    sfx[i0:i0 + L] += s

tl = np.arange(int(SR * 4.0)) / SR
thunder = lp(rng.standard_normal(len(tl)), 180) * np.exp(-tl * 0.9) * (1 + 0.6 * np.sin(2 * np.pi * 2.3 * tl))
far = lp(rng.standard_normal(len(tl)), 140) * np.exp(-tl * 1.1)
real = rec("thunder", 0.0, 9.0)                                        # real thunder (Openverse / Wikimedia, CC BY)
if real is not None:
    fade = np.minimum(1, np.linspace(9, 0, len(real)) / 2.5)
    real = real * fade * rms(thunder[:2 * SR]) / rms(real[:2 * SR])
    thunder = 0.35 * np.pad(thunder, (0, max(0, len(real) - len(thunder))))[:len(real)] + real
    far = lp(real, 500) * 0.7
place(thunder, 0.4, 2.2)
place(far, REVEAL + 1.0, 1.4)                                                            # far thunder during the reveal
tw = np.arange(int(SR * 1.2)) / SR                                                       # time-stop: reverse whoosh into a low boom
whoosh = hp(lp(rng.standard_normal(len(tw)), 2400), 200) * (tw / tw[-1]) ** 3
place(whoosh, FREEZE - 1.15, 1.6)
tb = np.arange(int(SR * 2.5)) / SR
boom = (np.sin(2 * np.pi * (55 - 20 * tb) * tb) * np.exp(-tb * 2.2) + lp(rng.standard_normal(len(tb)), 90) * np.exp(-tb * 3))
place(boom, FREEZE, 2.6)
ring = np.sin(2 * np.pi * 1760 * tb) * np.exp(-tb * 1.6) * 0.25 + np.sin(2 * np.pi * 2637 * tb) * np.exp(-tb * 2.2) * 0.15
place(ring, FREEZE + 0.05, 1.0)                                                          # glassy shimmer of slowed drops
place(whoosh[::-1] * 0.8, SLOW1 - 0.05, 1.2)                                             # time snaps back
tc = np.arange(int(SR * 3.0)) / SR                                                       # a car passing (hook)
car = lp(rng.standard_normal(len(tc)), 900) * np.exp(-((tc - 1.5) / 0.6) ** 2)
place(car, 2.0, 1.2, 0.8)
sting = np.sin(2 * np.pi * 880 * tb) * np.exp(-tb * 2.0) + 0.5 * np.sin(2 * np.pi * 1318.5 * tb) * np.exp(-tb * 2.6)
place(sting, next(x["start"] for x in SENTS if "Teach me" in x["text"]) + 0.05, 0.8)       # "Teach me."
tu = np.arange(int(SR * 0.5)) / SR                                                       # the umbrella snaps shut
fwump = lp(rng.standard_normal(len(tu)), 1400) * np.exp(-tu * 14) + np.sin(2 * np.pi * 90 * tu) * np.exp(-tu * 18)
place(fwump, next(x["start"] for x in SENTS if "closed it" in x["text"]) + 1.0, 1.4)
place(sting * 0.7, CLOSE + 1.05, 0.6)
place(boom * 0.6, DUR - 2.4, 1.2)                                                        # last word lands

# a whoosh on every scene change: band-passed air sweeping up in pitch into the cut, panned across, peak on the cut
# frame; the rain dips a little under it so it reads through the storm
from scipy.signal import butter, sosfilt
def cut_whoosh(seed, length):
    r = np.random.default_rng(100 + seed); m = int(SR * length); tt = np.arange(m) / SR; pk = 0.75 * length
    x = np.zeros(m)
    for j, fc in enumerate((260, 480, 900, 1700, 3200, 6000)):        # bands light up one after another: a rising sweep
        at = pk * (0.35 + 0.65 * j / 5)
        w = np.exp(-((tt - at) / (0.09 + 0.05 * (j < 2))) ** 2) * np.where(tt > pk, np.exp(-(tt - pk) / 0.06), 1)
        x += sosfilt(butter(2, [fc / 1.5, min(fc * 1.5, 0.45 * SR)], "bandpass", fs=SR, output="sos"), r.standard_normal(m)) * w
    return x / (np.abs(x).max() + 1e-9), pk
def click_sfx(seed):
    """A crisp UI-style click: press and release, a few ms each, ~35 ms apart."""
    r = np.random.default_rng(200 + seed); m = int(SR * 0.12); tt = np.arange(m) / SR; x = np.zeros(m)
    for at, g, f in ((0.0, 1.0, 3400), (0.035 + 0.01 * r.random(), 0.55, 2600)):
        u = np.clip(tt - at, 0, None); on = tt >= at
        x += on * g * (np.sin(2 * np.pi * f * u) * np.exp(-u * 900) + hp(r.standard_normal(m), 2500) * np.exp(-u * 1400) * 0.6)
    return x / np.abs(x).max(), 0.0

def shutter_sfx(seed):
    """A camera shutter: the mirror slap ("ka") on the cut, the shutter closing ("chk") ~80 ms later, with a little rattle."""
    r = np.random.default_rng(300 + seed); m = int(SR * 0.3); tt = np.arange(m) / SR; x = np.zeros(m)
    for at, g, bright in ((0.0, 1.0, 1800), (0.075 + 0.015 * r.random(), 0.8, 2600)):
        u = np.clip(tt - at, 0, None); on = tt >= at
        burst = sosfilt(butter(2, [bright, 7500], "bandpass", fs=SR, output="sos"), r.standard_normal(m))
        x += on * g * (burst * np.exp(-u * 160) + np.sin(2 * np.pi * 180 * u) * np.exp(-u * 70) * 0.5)
    x += hp(r.standard_normal(m), 3000) * np.exp(-((tt - 0.04) / 0.03) ** 2) * 0.15   # spring rattle between
    return x / np.abs(x).max(), 0.0

cuts = [b["start"] for b in beats["shots"][1:]]
kinds = (["whoosh", "click", "shutter"] * (len(cuts) // 3 + 1))[:len(cuts)]
np.random.default_rng(11).shuffle(kinds)                      # scene changes swap whoosh / click / shutter, no set order
duck = np.ones(n); WH = np.zeros((n, 2))                      # own stem: mix.py sets its level
for k, (c, kind) in enumerate(zip(cuts, kinds)):
    slowmo = FREEZE - 0.05 < c < SLOW1 + 0.1
    if kind == "whoosh": x, pk = cut_whoosh(k, 0.45 + 0.08 * (k % 3)); g = 1.0
    elif kind == "click": x, pk = click_sfx(k); g = 0.8
    else: x, pk = shutter_sfx(k); g = 0.9
    if slowmo: x = lp(x, 1100); g *= 0.8                        # slow motion: heavier, duller
    i0 = int((c - pk) * SR); i0, x = max(0, i0), x[max(0, -i0):]; L = min(len(x), n - i0)
    pan = (np.linspace(-0.7, 0.7, L) * (1 if k % 2 else -1)) if kind == "whoosh" else np.full(L, 0.25 * (1 if k % 2 else -1))
    WH[i0:i0 + L, 0] += x[:L] * g * (1 - pan); WH[i0:i0 + L, 1] += x[:L] * g * (1 + pan)
    d0, d1 = int((c - 0.3) * SR), min(n, int((c + 0.15) * SR))
    if d0 > 0: duck[d0:d1] = np.minimum(duck[d0:d1], 1 - (0.35 if kind == "whoosh" else 0.15) * np.sin(np.linspace(0, np.pi, d1 - d0)))
print("scene changes:", " ".join(f"{c:.2f}s {kind}" for c, kind in zip(cuts, kinds)))

# the first time Aura Monster dodges: time bends (a tape-stop dive), then a bright swish and a shimmer on the side-step
def weave(f):                                                   # the same side-step curve as film.py
    S0, S1 = beats["slow0"], beats["slow1"]
    if f < S0 or f > S1: return 0.0
    k = min(1.0, (f - S0) / 12.0) * min(1.0, (S1 - f) / 12.0)
    return k * (0.15 * np.sin(2 * np.pi * f / 17.0) + 0.06 * np.sin(2 * np.pi * f / 7.3))
wv = [abs(weave(f)) for f in range(beats["slow0"], beats["slow1"])]
pk_f = next(beats["slow0"] + i for i in range(1, len(wv) - 1) if wv[i] >= wv[i - 1] and wv[i] > wv[i + 1] and wv[i] > 0.05)
DODGE = (pk_f - 1) / FPS
tt = np.arange(int(SR * 0.7)) / SR                              # tape-stop: a falling tone into the slow motion
dive = np.sin(2 * np.pi * np.cumsum(520 * np.exp(-tt * 4.2) + 40) / SR) * np.exp(-tt * 2.5) * np.minimum(1, tt / 0.02)
dive = lp(dive + 0.4 * lp(rng.standard_normal(len(tt)), 900) * np.exp(-tt * 3), 2500)
ts = np.arange(int(SR * 1.6)) / SR                              # swish into the dodge, shimmer as he slips the drop
sw, swp = cut_whoosh(99, 0.35)
shim = sum(np.sin(2 * np.pi * f * ts) * np.exp(-ts * d) for f, d in ((1318.5, 2.2), (1975.5, 2.8), (2637.0, 3.4), (3951.1, 4.0)))
shim *= np.minimum(1, ts / 0.004) / 4
def put(x, at, g, pan=0.0):
    i0 = int(at * SR); i0, x = max(0, i0), x[max(0, -i0):]; L = min(len(x), n - i0)
    WH[i0:i0 + L, 0] += x[:L] * g * (1 - pan); WH[i0:i0 + L, 1] += x[:L] * g * (1 + pan)
put(dive / np.abs(dive).max(), FREEZE - 0.1, 0.8)
put(sw, DODGE - swp, 0.9, 0.3)
put(stereo(shim, 0.5, 4)[:, 0], DODGE, 0.7, -0.2)
print(f"first dodge at {DODGE:.2f}s (frame {pk_f})")

def write(path, x):
    x = x / max(1e-9, np.abs(x).max()) * 0.9
    if x.ndim == 1: x = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
# footsteps: the user's recorded steps (audio/footsteps/step_N.wav) on every heel strike film.py exported (steps.json),
# louder the closer the walker is to the camera; the eight takes rotate, with a touch of pitch and pan variety
steps = np.zeros((n, 2)); SP = os.path.join(HERE, "steps.json"); FS = os.path.join(HERE, "audio", "footsteps")
takes = []
for k in range(1, 9):
    fp = os.path.join(FS, f"step_{k}.wav")
    if os.path.exists(fp):
        with wave.open(fp) as w_:
            takes.append(np.frombuffer(w_.readframes(w_.getnframes()), "<i2").astype(np.float64) / 32768)
if takes and os.path.exists(SP):
    side = {}
    for i, ev in enumerate(json.load(open(SP))):
        x = takes[i % len(takes)]; r = 1 + rng.uniform(-0.04, 0.04)
        x = np.interp(np.arange(0, len(x) - 1, r), np.arange(len(x)), x)       # small pitch variety
        if FREEZE <= ev["t"] <= SLOW1:                                         # slow motion: heavier, duller steps
            x = lp(np.interp(np.arange(0, len(x) - 1, 0.8), np.arange(len(x)), x), 1800)
        side[ev["rig"]] = -side.get(ev["rig"], 0.15) or 0.15                   # alternate feet left / right
        i0 = int(ev["t"] * SR); L = min(len(x), n - i0)
        if L > 0:
            g = ev["gain"]; pan = side[ev["rig"]]
            steps[i0:i0 + L, 0] += x[:L] * g * (1 - pan); steps[i0:i0 + L, 1] += x[:L] * g * (1 + pan)
os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)
write(os.path.join(HERE, "audio", "music.wav"), stereo(music, 0.35, 2))
write(os.path.join(HERE, "audio", "sfx.wav"), sfx)
write(os.path.join(HERE, "audio", "rain.wav"), RAIN * duck[:, None])
write(os.path.join(HERE, "audio", "whoosh.wav"), WH)                           # scene-change whooshes   # dips under each cut whoosh
if np.abs(steps).max() > 0:
    write(os.path.join(HERE, "audio", "steps.wav"), steps)
print(f"stems written: {DUR:.2f}s, slow {FREEZE:.2f}-{SLOW1:.2f}s, close at {CLOSE:.2f}s, payoff at {PAYOFF:.2f}s")
