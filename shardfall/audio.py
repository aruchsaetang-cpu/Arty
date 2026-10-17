"""Score + sound design for SHARDFALL, synthesized and locked to film.STARTS."""
import math, os, sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film import STARTS, TOTAL  # noqa: E402

SR = 48000
N = int(TOTAL * SR) + SR
rng = np.random.default_rng(7)
MUS = np.zeros((2, N), np.float32)   # music bus (gets big reverb)
SFX = np.zeros((2, N), np.float32)   # sfx bus (short reverb)
DRY = np.zeros((2, N), np.float32)   # impacts, no reverb


def S(name, off=0.0): return STARTS[name] + off


def hz(midi): return 440.0 * 2 ** ((midi - 69) / 12)


def tt(dur): return np.arange(int(dur * SR)) / SR


def env_adsr(n, a, d, s, r):
    e = np.ones(n, np.float32) * s
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    A = min(A, n); e[:A] = np.linspace(0, 1, A)
    D = min(D, n - A); e[A:A + D] = np.linspace(1, s, D)
    R = min(R, n)
    if R: e[-R:] *= np.linspace(1, 0, R)
    return e


def put(bus, t0, sig, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i + len(sig) <= 0: return
    if i < 0: sig = sig[-i:]; i = 0
    sig = sig[:N - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    bus[0, i:i + len(sig)] += sig * gain * l * 1.41
    bus[1, i:i + len(sig)] += sig * gain * r * 1.41


def lp(x, f, order=2): return sosfilt(butter(order, min(f, SR / 2 - 100) / (SR / 2), "low", output="sos"), x)
def hp(x, f, order=2): return sosfilt(butter(order, f / (SR / 2), "high", output="sos"), x)
def bp(x, f0, f1, order=2): return sosfilt(butter(order, [f0 / (SR / 2), min(f1, SR / 2 - 100) / (SR / 2)], "band", output="sos"), x)
def noise(dur): return rng.standard_normal(int(dur * SR)).astype(np.float32)


# ------------------------------------------------------------------ instruments
def saw(f, dur, harm=10, detune=0.0):
    t = tt(dur); out = np.zeros_like(t)
    for k in range(1, harm + 1):
        if f * k > 16000: break
        out += np.sin(2 * np.pi * f * k * (1 + detune) * t) / k
    return out.astype(np.float32)


def pad(notes, dur, gain=1.0, harm=6, a=1.5, r=2.0):
    out = np.zeros(int(dur * SR), np.float32)
    for m in notes:
        for d in (-0.004, 0.0, 0.0045):
            out += saw(hz(m), dur, harm, d)
    out *= env_adsr(len(out), a, .5, .9, r)
    return out * gain / (len(notes) * 3)


def piano(m, dur=2.5, vel=1.0):
    f = hz(m); t = tt(dur)
    out = np.zeros_like(t)
    for k, amp in enumerate((1, .5, .3, .18, .1, .06), 1):
        fk = f * k * math.sqrt(1 + 0.0004 * k * k)
        out += amp * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.2 + k * .9))
    att = np.minimum(1, t / .004)
    return (out * att * vel * .35).astype(np.float32)


def bell(f, dur=3.0, vel=1.0):
    t = tt(dur); out = np.zeros_like(t)
    for ratio, amp, dec in ((1, 1, 1.2), (2.76, .5, 2.0), (5.4, .3, 3.2), (8.93, .18, 4.5)):
        out += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dec)
    return (out * vel * .25 * np.minimum(1, t / .002)).astype(np.float32)


def glass_ping(f=None, vel=1.0):
    f = f or rng.uniform(2200, 6500)
    t = tt(.6); out = np.zeros_like(t)
    for ratio in (1, 1.47, 2.31, 3.07):
        out += np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 6)) * np.exp(-t * rng.uniform(8, 18)) / ratio
    return (out * vel * .3).astype(np.float32)


def glass_shatter(dur=1.6, vel=1.0, density=90):
    out = np.zeros(int(dur * SR), np.float32)
    nb = hp(noise(dur), 2500) * np.exp(-tt(dur) * 5)
    out += nb * .35
    for _ in range(density):
        t0 = abs(rng.normal(0, dur * .22))
        p = glass_ping(vel=rng.uniform(.3, 1))
        i = int(t0 * SR)
        if i < len(out): out[i:i + len(p)] += p[:len(out) - i]
    return out * vel


def crack(vel=1.0):
    d = .5; t = tt(d)
    clicks = np.zeros_like(t)
    for _ in range(25):
        i = int(abs(rng.normal(0, .06)) * SR)
        if i < len(t) - 50: clicks[i:i + 40] += rng.uniform(-1, 1) * np.hanning(40)
    body = hp(noise(d), 1200) * np.exp(-t * 14)
    return ((clicks * 1.5 + body * .6) * vel).astype(np.float32)


def boom(vel=1.0, f0=70, f1=32, dur=2.5):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * np.exp(-t * 1.6)
    hit = lp(noise(dur), 900) * np.exp(-t * 9)
    return (np.tanh((sub * 1.2 + hit * .8) * 1.5) * vel * .8).astype(np.float32)


def taiko(vel=1.0):
    t = tt(.9)
    f = 55 + 70 * np.exp(-t * 25)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    skin = bp(noise(.9), 150, 1200) * np.exp(-t * 30)
    return ((body + skin * .5) * vel * .7).astype(np.float32)


def snare(vel=1.0):
    t = tt(.3)
    return ((bp(noise(.3), 1500, 9000) * np.exp(-t * 22) * .5 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * .4) * vel).astype(np.float32)


def whoosh(dur=.8, up=True, vel=1.0):
    n = noise(dur); t = tt(dur)
    seg = 8; out = np.zeros_like(n); L = len(n) // seg
    for k in range(seg):
        x = k / (seg - 1) if up else 1 - k / (seg - 1)
        fc = 300 + 4000 * x
        out[k * L:(k + 1) * L] = bp(n[k * L:(k + 1) * L], fc * .6, fc * 1.4)
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (out * e * vel * .8).astype(np.float32)


def riser(dur, vel=1.0):
    t = tt(dur)
    f = 200 * 2 ** (3 * t / dur)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .3
    nz = hp(noise(dur), 2000) * .4
    return ((tone + nz) * (t / dur) ** 2 * vel).astype(np.float32)


def roar(dur=2.5, vel=1.0):
    t = tt(dur)
    f = 62 + 8 * np.sin(2 * np.pi * 5 * t) + 20 * np.exp(-t * 2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = sum(np.sin(ph * k) / k for k in range(1, 14))
    grit = bp(noise(dur), 200, 2400) * (1 + .5 * np.sin(2 * np.pi * 23 * t))
    sig = np.tanh((tone * .6 + grit * .8) * 2.5)
    e = env_adsr(len(t), .15, .3, .8, dur * .5)
    shimmer = glass_shatter(dur, .25, 30)
    return ((lp(sig, 2500) * e + shimmer) * vel * .7).astype(np.float32)


def wind(dur, vel=1.0):
    t = tt(dur)
    m = .6 + .4 * np.sin(2 * np.pi * .13 * t) * np.sin(2 * np.pi * .07 * t + 1)
    return (bp(noise(dur), 150, 900) * m * vel * .25).astype(np.float32)


def hum(dur, vel=1.0, f=55):
    t = tt(dur)
    s = np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 2.01 * t) + .25 * np.sin(2 * np.pi * f * 3.02 * t)
    return (s * vel * .25).astype(np.float32)


def chirp(vel=1.0):
    t = tt(.12)
    f = 3200 + 1600 * np.sin(np.pi * t / .12)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / .12) * vel * .12).astype(np.float32)


def heartbeat(vel=1.0):
    out = np.zeros(int(.6 * SR), np.float32)
    for o, v in ((0, 1), (.18, .7)):
        b = boom(v, 60, 40, .4) * .6
        i = int(o * SR); out[i:i + len(b)] += b[:len(out) - i]
    return out * vel


# ------------------------------------------------------------------ helpers for patterns
Dm, Bb, F, C, Gm, A = [50, 57, 62, 65], [46, 58, 62, 65], [41, 57, 60, 65], [48, 55, 60, 64], [43, 55, 58, 62], [45, 57, 61, 64]
D_, G_, Bm, A_ = [50, 57, 62, 66], [43, 59, 62, 67], [47, 54, 59, 62], [45, 57, 61, 64]


def arp(t0, t1, chords, bar, vel=.8, octave=12, pattern=(0, 1, 2, 3, 2, 1), pan=0):
    t = t0; ci = 0; step = bar / len(pattern)
    while t < t1:
        ch = chords[ci % len(chords)]
        for k, p in enumerate(pattern):
            tn = t + k * step
            if tn >= t1: break
            put(MUS, tn, piano(ch[p % len(ch)] + octave, 2.2, vel * (1 - .15 * (k % 2))), 1, pan + .3 * math.sin(tn))
        t += bar; ci += 1


def pads(t0, t1, chords, bar, gain=.5, harm=6):
    t = t0; ci = 0
    while t < t1 - .1:
        d = min(bar, t1 - t) + 1.5
        put(MUS, t, pad(chords[ci % len(chords)], d, gain, harm, a=min(1.2, bar / 2), r=1.5))
        t += bar; ci += 1


# ================================================================== CUE SHEET
# ---- ACT 0
put(SFX, 0, hum(1.5, .6) * np.linspace(0, 1, int(1.5 * SR)))
put(SFX, 0.3, riser(1.2, .5))
t = S("s_cold_clash")
put(DRY, t, boom(1.3)); put(SFX, t, glass_shatter(1.4, .9))
for k in range(6): put(DRY, t + k / 6 * 1.5, taiko(.7), 1, (-1) ** k * .3)
put(SFX, S("s_cold_ren"), whoosh(.6, True, 1.1), 1, -.4)
put(SFX, S("s_cold_beast"), roar(.9, .9))
put(SFX, S("s_cold_beast", .4), riser(.35, .8))
t = S("s_title")
for i in range(9): put(SFX, t + .35 + i * .13, glass_ping(1800 + i * 300, 1.2), 1, (i - 4) / 5); put(DRY, t + .35 + i * .13, taiko(.35))
put(DRY, t + .35 + 8 * .13, boom(1.2)); put(MUS, t + .35 + 8 * .13, pad([38, 45, 50, 57, 62], 5, .9, 8, .02, 3))
put(SFX, t + 2.6, whoosh(1.2, True, .5))
put(SFX, t + 5.6, glass_shatter(2.0, 1.0, 140)); put(DRY, t + 5.6, boom(.7, 90, 40, 1.5))

# ---- ACT 1: dusk (72 bpm, bar = 3.333s)
a1, a1e = S("s_city_pan"), S("s_ren_push")
bar = 60 / 72 * 4
pads(a1, a1e + 2, [Dm, Bb, F, C], bar, .35)
arp(a1 + .4, a1e, [Dm, Bb, F, C], bar, .55)
put(SFX, a1, wind(S("s_hana_flash") - a1, .7))
put(SFX, a1, lp(noise(S("s_point") - a1), 300) * .05)  # distant city bed
for k in range(10): put(SFX, a1 + 1.5 + k * .55 + rng.uniform(0, .3), chirp(rng.uniform(.5, 1)), 1, rng.uniform(-.8, .8))
for k in range(30): put(SFX, a1 + rng.uniform(0, 8), glass_ping(rng.uniform(5000, 7000), .05), 1, rng.uniform(-1, 1))  # window clicks
# Ren senses it: music thins, hum creeps up
t = S("s_ren_push")
put(MUS, t, pad([38, 45], 8.5, .35, 4, 2, 2))
put(SFX, t, hum(8.0, .5, 55) * np.linspace(0, 1, int(8 * SR)) ** 2)
put(SFX, t + 4.6, bell(hz(81), 2, .5), 1, .2)
put(SFX, S("s_ren_eyes"), whoosh(1.6, True, .5))
# flashback: bright D major, music box + strings
fb, fbe = S("s_hana_flash"), S("s_ren_back")
put(SFX, fb, glass_shatter(1.0, .15, 20))
pads(fb, fbe, [D_, G_, Bm, A_], 2.0, .32, 5)
melody = [74, 76, 78, 81, 79, 78, 76, 74, 73, 74, 76, 78, 74, 71, 73, 74]
for i, m in enumerate(melody):
    put(MUS, fb + .2 + i * .48, bell(hz(m), 2.2, .6), 1, .2 * math.sin(i))
for k in range(6): put(SFX, fb + rng.uniform(0, 7), chirp(.4), 1, rng.uniform(-1, 1))
t = S("s_ren_back")
put(SFX, t + .8, riser(1.2, .4)); put(DRY, t + 2.0, boom(.6, 100, 50, 1.0)); put(SFX, t + 2.0, glass_ping(5200, .8))

# ---- ACT 2: crack + beast
t = S("s_point")
tn = tt(2.5)
put(SFX, t, (np.sin(2 * np.pi * (3000 + 1500 * tn / 2.5) * tn) * .06 * (tn / 2.5)).astype(np.float32))
put(SFX, t, hum(2.5, .35, 41))
t = S("s_sky_cracks")
put(DRY, t, boom(1.5, 80, 28, 4)); put(SFX, t, glass_shatter(3.0, 1.2, 200))
for k in range(16): put(SFX, t + k * .15 + rng.uniform(0, .1), crack(rng.uniform(.4, 1)), 1, rng.uniform(-.9, .9))
rain_end = S("s_beast_reveal") + 8
for k in range(int((rain_end - t) * 14)): put(SFX, t + 1 + rng.uniform(0, rain_end - t - 1), glass_ping(None, rng.uniform(.05, .25)), 1, rng.uniform(-1, 1))
# dread cluster drone
put(MUS, t, pad([26, 38, 39, 45, 50, 51], S("s_ren_resolve") - t + 1, .6, 9, 3, 2))
for k in range(3): put(DRY, S("s_city_rain") + .8 + k * 1.6, boom(.35, 120, 60, .8))
put(SFX, S("s_heads_wind"), wind(2.2, 2.4))
put(SFX, S("s_heads_wind"), whoosh(1.8, False, .8))
t = S("s_beast_reveal")
for k in range(4): put(DRY, t + k * 1.6, taiko(.9 - k * .1))
put(SFX, t, hum(8, .5, 36))
for k in range(12): put(SFX, t + rng.uniform(0, 7), crack(.25), 1, rng.uniform(-.5, .5))
put(SFX, t + 6.2, roar(1.6, .7))
t = S("s_beast_roar")
put(SFX, t + .3, roar(3.0, 1.3)); put(DRY, t + .4, boom(1.0, 60, 25, 3))
put(SFX, S("s_beast_wide_roar"), glass_shatter(2.5, .5, 80))
# resolve: taiko roll accelerating into the fight
t, te = S("s_ren_resolve"), S("s_ren_leap")
x = t
while x < te:
    p = (x - t) / (te - t)
    put(DRY, x, taiko(.4 + .5 * p), 1, (-1) ** int(x * 10) * .2)
    x += .5 - .38 * p
put(SFX, t + 2.4, whoosh(.5, True, .7))
put(MUS, t, pad([38, 45, 50, 57], te - t + .5, .55, 10, 1.5, .5))
put(SFX, S("s_hana_ready"), riser(3.0, .5))
put(SFX, S("s_hana_ready"), bell(hz(86), 3, .3))

# ---- ACT 3: fight (150 bpm)
f0, f1 = S("s_ren_leap"), S("s_ma")
beat = 60 / 150
prog = [Dm, Dm, Bb, C, Gm, Bb, A, A]
b = 0
x = f0
while x < f1 - 1e-3:
    bar_i = b // 4
    ch = prog[bar_i % len(prog)]
    # drums
    if b % 4 in (0, 3) or (b % 8 == 6): put(DRY, x, taiko(.9 if b % 4 == 0 else .6))
    if b % 2 == 1: put(DRY, x, snare(.55), 1, .15)
    if b % 8 == 7: put(DRY, x + beat / 2, snare(.4), 1, -.15)
    # string ostinato 16ths
    for s in range(4):
        m = ch[0] + 12 + (0, 12, 7, 12)[s]
        sig = saw(hz(m), beat / 4 * .9, 9) * env_adsr(int(beat / 4 * .9 * SR), .003, .05, .5, .03) * .12
        put(MUS, x + s * beat / 4, sig, 1, (-.4, .4)[s % 2])
    # brass stab on bar starts
    if b % 4 == 0:
        st = sum(saw(hz(m + 12), .5, 14) for m in ch[1:]) * env_adsr(int(.5 * SR), .01, .25, .3, .1) * .12
        put(MUS, x, lp(st, 3500))
        put(MUS, x, saw(hz(ch[0] - 12), beat * 4, 8) * env_adsr(int(beat * 4 * SR), .01, .3, .6, .2) * .2)
    x += beat; b += 1
put(SFX, f0, whoosh(1.0, True, 1.2), 1, -.5)
put(SFX, f0 + .1, wind(4.8, 2.0))
t = S("s_blade")
tn = tt(1.4)
shing = (np.sin(2 * np.pi * 2400 * tn) + .6 * np.sin(2 * np.pi * 3610 * tn) + .3 * np.sin(2 * np.pi * 5120 * tn)) * np.exp(-tn * 2.5) * .18
put(SFX, t + .05, shing.astype(np.float32)); put(SFX, t, whoosh(.5, True, .6))
t = S("s_hana_barrier")
for i in range(24): put(MUS, t + .1 + i * .05, bell(hz(62 + [0, 4, 7, 11, 14][i % 5] + 12 * (i // 5)), 1.5, .35), 1, (i % 5 - 2) / 3)
put(SFX, t, riser(5.5, .35))
put(SFX, S("s_threads_burst", .3), whoosh(.7, False, 1.0)); put(DRY, S("s_threads_burst", .3), boom(.4, 140, 70, .8))
t = S("s_bind_beast")
for k in range(9): put(SFX, t + k * .14, whoosh(.35, True, .35), 1, rng.uniform(-.7, .7))
put(SFX, t + 2.5, roar(1.4, .7)); put(SFX, t + 1, crack(.6))
put(SFX, S("s_ren_charge"), riser(2.0, 1.0)); put(SFX, S("s_ren_charge"), whoosh(2.0, True, .9))

# ---- MA: one second of silence (+ heartbeat), then the clash
put(DRY, S("s_ma", .1), heartbeat(.9))
t = S("s_clash")
put(DRY, t, boom(2.2, 90, 22, 4.5)); put(SFX, t, glass_shatter(3.0, 1.6, 260))
put(SFX, t, hp(noise(.5), 600) * np.exp(-tt(.5) * 6) * 1.2)
for k in range(9): put(DRY, t + .25 + k / 12, taiko(.8), 1, (-1) ** k * .4)
tn = tt(1.0)
put(MUS, t + 3.0, (pad([26, 33, 38], 1.0, 1.0, 5, .9, .05) * tn).astype(np.float32))  # slow push swell
put(DRY, t + 4.0, boom(2.4, 100, 20, 5)); put(SFX, t + 4.0, glass_shatter(3.5, 1.7, 300))
for k in range(7): put(DRY, t + 4.0 + k / 12, taiko(.7), 1, (-1) ** k * .4)
t = S("s_beast_fracture")
for k in range(24): put(SFX, t + k * .09, crack(.4 + k / 30), 1, rng.uniform(-1, 1))
put(SFX, t + 1.3, riser(1.0, .9)); put(DRY, t + 2.3, boom(1.4, 90, 30, 2.5))
put(SFX, S("s_hana_shout"), whoosh(.8, False, .8))
# mirror dive
t = S("s_mirror_dive")
put(SFX, t, whoosh(2.4, False, 1.0))
put(MUS, t, pad([50, 57, 62, 69, 74], 8.0, .35, 3, 2, 2))
put(DRY, t + 2.5, boom(.9, 140, 45, 2.0))
tn = tt(2.5)
put(SFX, t + 2.5, (lp(noise(2.5), 1200) * np.exp(-tn * 2) * .6).astype(np.float32))
for k in range(8): put(SFX, t + 2.6 + k * .28, (np.sin(2 * np.pi * (700 - 400 * tt(.25) / .25) * tt(.25)) * np.exp(-tt(.25) * 10) * .3 * (1 - k / 9)).astype(np.float32), 1, (-1) ** k * .5)
# reversed bell rising into contact
rb = bell(hz(86), 2.0, 1.0)[::-1].copy()
put(SFX, S("s_mirror_contact"), rb)
# the shatter
t = S("s_shatter")
put(DRY, t, boom(2.6, 70, 18, 6)); put(SFX, t, glass_shatter(5.0, 2.0, 420))
for k in range(60): put(SFX, t + 1 + rng.uniform(0, 7), glass_ping(None, rng.uniform(.05, .2)), 1, rng.uniform(-1, 1))
# memories: lone piano motif
t = S("s_memories")
for i, m in enumerate([74, 76, 78, 81, 79, 78, 76, 74]):
    put(MUS, t + .2 + i * .45, piano(m, 3.0, .7), 1, .3 * math.sin(i))
put(MUS, t, pad([50, 57, 62], 4.5, .25, 3, 1.5, 2))

# ---- ACT 4: aftermath, D major resolution
t, te = S("s_shard_snow"), S("s_morning")
pads(t, te + 1, [D_, Bm, G_, A_], 3.5, .32, 4)
arp(t + 1.0, te, [D_, Bm, G_, A_], 3.5, .4, 12, (0, 2, 3, 2))
for k in range(int((te - t) * 4)): put(SFX, t + rng.uniform(0, te - t), glass_ping(rng.uniform(3000, 6000), rng.uniform(.03, .1)), 1, rng.uniform(-1, 1))
put(SFX, t, wind(te - t, .3))
t, te = S("s_morning"), S("s_end")
put(SFX, t, glass_shatter(.6, .2, 10))
pads(t, te + 1, [D_, G_, Bm, A_, G_, D_], 2.3, .4, 6)
theme = [74, 76, 78, 81, 79, 78, 76, 74, 73, 74, 76, 78, 81, 83, 81, 78, 76, 74]
for i, m in enumerate(theme): put(MUS, t + 1.0 + i * .6, piano(m, 3.0, .75), 1, .25 * math.sin(i))
for k in range(14): put(SFX, t + rng.uniform(0, 12), chirp(rng.uniform(.4, .9)), 1, rng.uniform(-.9, .9))
put(SFX, t + 10.2, bell(hz(93), 2.5, .6), 1, .4)
t = S("s_end")
put(MUS, t, pad([38, 50, 54, 57, 62, 66, 69], 11.5, .7, 7, 2, 6))
for i, m in enumerate([62, 66, 69, 74]): put(MUS, t + .5 + i * .3, bell(hz(m + 12), 4, .5), 1, (i - 1.5) / 3)
put(SFX, t + 7, glass_ping(5600, .5))


# ------------------------------------------------------------------ mix
def reverb(x, seconds, damp=3.5):
    n = int(seconds * SR); t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n) * np.exp(-t * damp) for _ in range(2)]).astype(np.float32)
    ir[:, :int(.01 * SR)] *= np.linspace(0, 1, int(.01 * SR))
    ir /= np.sqrt((ir ** 2).sum(1, keepdims=True))
    return np.stack([fftconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])


mus = MUS + reverb(MUS, 3.5, 2.2) * .45
sfx = SFX + reverb(SFX, 1.6, 4) * .25
mix = mus * .55 + sfx * .7 + DRY * .8
mix = np.tanh(mix * 1.1) / 1.1
mix /= np.abs(mix).max() / .95
mix[:, :int(.02 * SR)] *= np.linspace(0, 1, int(.02 * SR))
fade = int(2.5 * SR); end = int(TOTAL * SR)
mix[:, end - fade:end] *= np.linspace(1, 0, fade)
mix = mix[:, :end]
wavfile.write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "score.wav"), SR, (mix.T * 32767).astype(np.int16))
print("wrote score.wav", mix.shape[1] / SR, "s")
