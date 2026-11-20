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
place(whoosh, FREEZE - 1.15, 0.9)      # ("Then I saw it" sits on the time-stop: keep the mids clear)
tb = np.arange(int(SR * 2.5)) / SR
boom = (np.sin(2 * np.pi * (55 - 20 * tb) * tb) * np.exp(-tb * 2.2) + lp(rng.standard_normal(len(tb)), 90) * np.exp(-tb * 3))
place(boom, FREEZE, 2.6)
ring = np.sin(2 * np.pi * 1760 * tb) * np.exp(-tb * 1.6) * 0.25 + np.sin(2 * np.pi * 2637 * tb) * np.exp(-tb * 2.2) * 0.15
place(ring, FREEZE + 0.05, 0.55)                                                          # glassy shimmer of slowed drops
place(whoosh[::-1] * 0.8, SLOW1 - 0.05, 1.2)                                             # time snaps back
tc = np.arange(int(SR * 3.0)) / SR                                                       # a car passing (hook)
car = lp(rng.standard_normal(len(tc)), 900) * np.exp(-((tc - 1.5) / 0.6) ** 2)
place(car, 2.0, 1.2, 0.8)
sting = np.sin(2 * np.pi * 880 * tb) * np.exp(-tb * 2.0) + 0.5 * np.sin(2 * np.pi * 1318.5 * tb) * np.exp(-tb * 2.6)
place(sting, next(x["start"] for x in SENTS if "Teach me" in x["text"]) + 0.05, 0.8)       # "Teach me."
tu = np.arange(int(SR * 0.5)) / SR                                                       # the umbrella snaps shut
fwump = lp(rng.standard_normal(len(tu)), 1400) * np.exp(-tu * 14) + np.sin(2 * np.pi * 90 * tu) * np.exp(-tu * 18)
WORDS = json.load(open(os.path.join(HERE, "words.json")))
cf0, cf1 = B["close"]["f0"], B["close"]["f1"]
FOLD = (cf0 + int(0.45 * (cf1 - cf0)) - 1) / FPS                # the frame the umbrella folds (film.py FOLD)
EYES = FOLD + 4 / FPS                                           # his eyes turn and the yellow aura lights
LAST = WORDS[-1]["e"]                                           # right after "...wet.": the line, then the hit
place(fwump, FOLD, 1.4)
place(sting * 0.7, EYES + 0.02, 0.6)
place(boom * 0.6, LAST, 1.2)                                                             # last word lands

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
    """The user's own click (audio/sfx/click_user.wav: press + release, ~115 ms apart), lined up so the press lands
    on the cut. It is the only click sound in the film."""
    u = rec("click_user")
    on = int(np.argmax(np.abs(u) > 0.3 * np.abs(u).max()))          # the press transient
    return u / np.abs(u).max(), on / SR

cuts = [b["start"] for b in beats["shots"][1:]]
kinds = (["whoosh", "click", "shutter"] * (len(cuts) // 3 + 1))[:len(cuts)]
np.random.default_rng(11).shuffle(kinds)                      # scene changes swap whoosh / click, no set order
kinds = ["click" if k == "shutter" else k for k in kinds]     # the user's click replaces every other click-type sound
duck = np.ones(n); WH = np.zeros((n, 2))                      # own stem: mix.py sets its level
CL = np.zeros((n, 2))                                          # the user's click: its own loud stem, not ducked (clicks.wav)
for k, (c, kind) in enumerate(zip(cuts, kinds)):
    slowmo = FREEZE - 0.05 < c < SLOW1 + 0.1
    if kind == "click" and FREEZE - 0.5 < c < SLOW1 - 0.1 and rec("dodge_user") is not None:
        kind = "dodge"; kinds[k] = "cinematic"                  # while he dodges: the cinematic swoosh, not the click
    if kind == "whoosh": x, pk = cut_whoosh(k, 0.45 + 0.08 * (k % 3)); g = 1.0
    elif kind == "dodge":
        x = rec("dodge_user"); x = x / np.abs(x).max(); pk = int(np.argmax(np.convolve(np.abs(x), np.ones(480) / 480, "same"))) / SR; g = 0.9
    else: x, pk = click_sfx(k); g = 1.0
    if slowmo and kind == "whoosh": x = lp(x, 1100); g *= 0.8  # slow motion: heavier, duller (click and swoosh stay crisp)
    i0 = int((c - pk) * SR); i0, x = max(0, i0), x[max(0, -i0):]; L = min(len(x), n - i0)
    pan = (np.linspace(-0.7, 0.7, L) * (1 if k % 2 else -1)) if kind == "whoosh" else np.full(L, 0.25 * (1 if k % 2 else -1))
    DST = CL if kind in ("click", "dodge") else WH
    DST[i0:i0 + L, 0] += x[:L] * g * (1 - pan); DST[i0:i0 + L, 1] += x[:L] * g * (1 + pan)
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
put(dive / np.abs(dive).max(), FREEZE - 0.1, 0.3)
_ud = rec("dodge_user")                                         # the user's dodge swoosh, its peak on the side-step
if _ud is not None and len(_ud):
    _env = np.convolve(np.abs(_ud), np.ones(480) / 480, "same"); _pk = int(np.argmax(_env)) / SR
    _i = int((DODGE - _pk) * SR); _x = _ud / np.abs(_ud).max(); _L = min(len(_x), n - _i)
    CL[_i:_i + _L, 0] += _x[:_L] * 0.8; CL[_i:_i + _L, 1] += _x[:_L] * 1.0     # loud stem with the clicks (never ducked)
else:
    put(sw, DODGE - swp, 0.4, 0.3)
    put(stereo(shim, 0.5, 4)[:, 0], DODGE, 0.4, -0.2)
print(f"first dodge at {DODGE:.2f}s (frame {pk_f})")

# ------------------------------------------------------------------ cinematic layer (anime-film style): its own stem
# braams and sub drops on the big beats, risers into them, a reverse swell, taiko hits for the training, the "kiin"
# glint when eyes catch light, a heartbeat while he follows, the aura's roar, and a held breath of silence before
# the umbrella folds
from scipy.signal import fftconvolve
CINE = np.zeros((n, 2))
def word_t(w): return next(x["s"] for x in WORDS if x["w"].strip('.,"“”!?').lower() == w)
def verb(x, secs=2.2, seed=0, wet=0.5, bright=3500):
    if x.ndim == 2: x = x.mean(1)
    r = np.random.default_rng(500 + seed); m = int(SR * secs); tt = np.arange(m) / SR
    out = []
    for ch in range(2):
        ir = lp(r.standard_normal(m), bright) * np.exp(-tt * 6.9 / secs); ir /= np.sqrt((ir ** 2).sum())
        out.append(x * (1 - wet) + fftconvolve(np.pad(x, (0, m)), ir)[:len(x) + m][:len(x)] * wet * 3)
    return np.stack(out, 1)
def cput(x, at, g=1.0):
    if x.ndim == 1: x = np.stack([x, x], 1)
    i0 = int(at * SR); i0, x = max(0, i0), x[max(0, -i0):]; L = min(len(x), n - i0); CINE[i0:i0 + L] += x[:L] * g
def braam(secs=3.0, root=55.0, seed=0):
    r = np.random.default_rng(600 + seed); tt = np.arange(int(SR * secs)) / SR; x = np.zeros(len(tt))
    for f in (root, root * 1.5, root * 2, root * 3):                          # power chord of detuned saws
        for det in (-0.6, 0.0, 0.7):
            ph = 2 * np.pi * (f + det) * tt + r.random() * 6.28; x += (2 * ((ph / (2 * np.pi)) % 1) - 1) / (1 + f / 150)
    x = np.tanh(1.8 * x / np.abs(x).max())
    cut = 300 + 2600 * np.exp(-tt * 1.6)                                      # brassy "bwaah" closing down
    y = np.zeros_like(x); a = np.exp(-2 * np.pi * cut / SR); acc = 0.0
    for i in range(0, len(x), 256):                                           # block-wise sweeping low-pass
        seg = x[i:i + 256]; ai = a[i]; from scipy.signal import lfilter
        z, _ = lfilter([1 - ai], [1, -ai], seg, zi=[acc * ai]); y[i:i + 256] = z; acc = z[-1]
    return y * np.minimum(1, tt / 0.03) * np.exp(-tt * 1.1)
def subdrop(secs=1.6, f0=90, f1=28):
    tt = np.arange(int(SR * secs)) / SR; f = f1 + (f0 - f1) * np.exp(-tt * 3.0)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.4) * np.minimum(1, tt / 0.005)
def riser(secs=2.0, seed=0):
    r = np.random.default_rng(700 + seed); tt = np.arange(int(SR * secs)) / SR; u = tt / secs
    tone = sum(np.sin(2 * np.pi * np.cumsum(f * (1 + 3 * u ** 2)) / SR) for f in (220, 330.5, 441))
    nz = r.standard_normal(len(tt)); air = hp(lp(nz, 1500) * (1 - u) + lp(nz, 7500) * u, 400)   # brightens as it climbs
    return (0.25 * tone + air) * u ** 2.2
def reverse_swell(secs=1.4, seed=0):
    tt = np.arange(int(SR * secs)) / SR
    x = sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3) for f in (220, 329.6, 440, 659.3))
    return verb(x, 2.5, seed, 0.9)[::-1]
def taiko(seed=0):
    r = np.random.default_rng(800 + seed); tt = np.arange(int(SR * 1.2)) / SR
    body = np.sin(2 * np.pi * np.cumsum(62 + 60 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 5)
    slap = lp(r.standard_normal(len(tt)), 2200) * np.exp(-tt * 60)
    return verb(body + 0.5 * slap, 1.8, seed, 0.4, 1800)
def glint(seed=0):                                                            # the anime "kiin"
    tt = np.arange(int(SR * 1.4)) / SR
    x = sum(np.sin(2 * np.pi * f * tt + 0.8 * np.sin(2 * np.pi * 6 * tt)) * np.exp(-tt * d)
            for f, d in ((2793.8, 2.5), (4186.0, 3.2), (5587.7, 4.0), (8372.0, 6.0)))
    return verb(x * np.minimum(1, tt / 0.002) / 4, 1.6, seed, 0.45, 9000)
def heartbeat(at, beats_, period0, period1):
    tt = np.arange(int(SR * 0.5)) / SR
    thump = lambda: np.sin(2 * np.pi * np.cumsum(48 + 25 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 14)
    t_ = at
    for k in range(beats_):
        p = period0 + (period1 - period0) * k / max(1, beats_ - 1)
        cput(thump(), t_, 0.55); cput(thump() * 0.6, t_ + 0.26 * p, 0.55); t_ += p
def roar(secs=1.6, seed=0):                                                   # an aura igniting: a rushing flame
    r = np.random.default_rng(900 + seed); tt = np.arange(int(SR * secs)) / SR
    x = lp(r.standard_normal(len(tt)), 900) * (1 + 0.5 * np.sin(2 * np.pi * 11 * tt)) + 0.4 * hp(lp(r.standard_normal(len(tt)), 4000), 1200)
    return x * np.minimum(1, tt / 0.08) * np.exp(-tt * 1.6)

MON = word_t("monster")                                                       # title: riser -> braam + sub drop
_ur = rec("riser_user")                                                      # the user's riser opens the clip (own stem)
if _ur is not None and len(_ur):
    _end = int(np.where(np.abs(_ur) > 0.05 * np.abs(_ur).max())[0][-1]); _ur = _ur[:_end + 1] / np.abs(_ur).max()
    def _voiced_onset(t0, t1, frac=0.2):
        """Where the voice track really starts a word: first 5 ms frame after t0 above `frac` of the peak in [t0, t1].
        (Whisper's start time for "years" is 0.4 s early: it includes "nine"'s tail and the pause before the word.)"""
        with wave.open(os.path.join(HERE, "audio", "voice_fast.wav")) as w_:
            v = np.frombuffer(w_.readframes(w_.getnframes()), "<i2").astype(np.float64) / 32768; vs = w_.getframerate()
        win = int(vs * 0.005); e = np.sqrt((v[:len(v) // win * win].reshape(-1, win) ** 2).mean(1))
        a_, b_ = int(t0 / 0.005), int(t1 / 0.005); seg = e[a_:b_]
        return (a_ + int(np.argmax(seg > frac * seg.max()))) * 0.005 - 0.01
    RISER_DELAY = 0.10                                                        # seconds later than the voiced onset (user: "delay a bit")
    _y0 = word_t("years"); YEARS = _voiced_onset(_y0 + 0.30, _y0 + 1.0) + RISER_DELAY   # the riser ends as "years" is said
    print(f"riser ends at {YEARS:.3f}s incl. {RISER_DELAY}s delay (Whisper says 'years' starts {_y0:.2f}s; voiced onset measured in the voice track)")
    _tempo = (len(_ur) / SR) / YEARS                                 # (compressed, pitch kept: two atempo stages)
    import subprocess as _sp
    _af = ",".join(f"atempo={t:.4f}" for t in ((2.0, _tempo / 2.0) if _tempo > 2.0 else (_tempo,)))
    _ur = np.frombuffer(_sp.run(["ffmpeg", "-v", "error", "-f", "f64le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", _af,
                                 "-f", "f64le", "-ar", str(SR), "-ac", "1", "-"], input=_ur.astype("<f8").tobytes(), capture_output=True, check=True).stdout, "<f8")
    _ur = _ur[:int(YEARS * SR)]                                                 # ends exactly where "years" starts
    _ur = _ur * np.minimum(1, (len(_ur) - np.arange(len(_ur))) / (0.003 * SR))      # 3 ms fade only: no click, no early stop
    _env = np.sqrt(np.convolve(_ur ** 2, np.ones(4800) / 4800, "same")) + 1e-4      # nearly even, so it is loud from 0 s
    _ur = _ur * (np.max(_env) / _env) ** 0.85                                   # loudness, so it is loud from the first second
    _ur = _ur / np.abs(_ur).max()
    RISER = np.zeros(n); RISER[:len(_ur)] = _ur[:n]                              # its own stem (riser.wav, levelled in mix.py)
else:
    cput(riser(1.6, 1), MON - 1.6, 0.30)
cput(verb(braam(3.2, 55.0, 1), 2.8, 1, 0.35), MON, 0.85)
cput(subdrop(), MON, 0.9); cput(glint(1), MON + 0.05, 0.35)
heartbeat(B["follow"]["start"] + 0.2, 4, 0.95, 0.62)                          # he follows: heartbeat quickening
cput(subdrop(2.0, 70, 24), FREEZE, 0.8)
cput(glint(2), word_t("dodging"), 0.25)                                        # "...dodging it."
cput(taiko(1), SLOW1, 0.7)                                                    # time snaps back: a hit
cput(glint(3), (B["turn"]["f0"] + 10 - 1) / FPS + 0.05, 0.45)                 # he turns: eyes catch the light
cput(reverse_swell(1.2, 1), word_t("teach") - 1.2, 0.35)                      # "Teach me," with a swell and a big drum
cput(taiko(2), word_t("teach"), 0.9); cput(subdrop(1.2, 80, 30), word_t("teach"), 0.5)
m0, m1 = B["train_mont"]["f0"], B["train_mont"]["f1"]; ml = (m1 - m0 + 1) // 3
for k, at in enumerate([B["train_roof"]["start"], B["train_umb"]["start"]] + [(m0 + i * ml - 1) / FPS for i in range(3)]):
    cput(taiko(3 + k), at, 0.55 + 0.08 * k)                                   # training: drums build night by night
cput(riser(1.4, 3), FOLD - 1.6, 0.28)                                         # the fold: rise, hold the breath, hit
cput(reverse_swell(1.0, 2), FOLD - 1.0, 0.3)
cput(verb(braam(4.0, 49.0, 2), 3.2, 2, 0.4), FOLD, 1.0); cput(subdrop(2.2, 95, 24), FOLD, 1.0)
cput(glint(4), EYES, 0.55); cput(roar(1.8, 1), EYES, 0.5)                     # eyes turn void, the yellow aura roars up
cput(verb(taiko(9), 2.5), LAST, 0.6); cput(verb(braam(4.5, 55.0, 3), 4.0, 3, 0.55), LAST, 0.45)   # "...never get wet."
# the held breath: rain falls away in the half second before the fold, music and rain come back with the hit
b0, b1 = int((FOLD - 0.55) * SR), int((FOLD + 0.05) * SR)
duck[b0:b1] = np.minimum(duck[b0:b1], 1 - 0.75 * np.sin(np.linspace(0, np.pi, b1 - b0)) ** 0.5)
print(f"cinematic: title {MON:.2f}s, fold {FOLD:.2f}s, eyes {EYES:.2f}s, last word {LAST:.2f}s")

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
    F0, F1 = B["follow"]["start"], B["reveal_low"]["start"]                   # footsteps only while the narrator follows him
    for i, ev in enumerate(e for e in json.load(open(SP)) if F0 <= e["t"] < F1):
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
write(os.path.join(HERE, "audio", "whoosh.wav"), WH)                           # scene-change whooshes
if "RISER" in globals(): write(os.path.join(HERE, "audio", "riser.wav"), RISER)   # the user's riser opening the clip
write(os.path.join(HERE, "audio", "clicks.wav"), CL)                           # scene-change clicks (the user's recording)
write(os.path.join(HERE, "audio", "cine.wav"), CINE)                           # anime-film hits, risers, glints
if np.abs(steps).max() > 0:
    write(os.path.join(HERE, "audio", "steps.wav"), steps)
print(f"stems written: {DUR:.2f}s, slow {FREEZE:.2f}-{SLOW1:.2f}s, close at {CLOSE:.2f}s, payoff at {PAYOFF:.2f}s")
