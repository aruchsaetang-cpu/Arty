"""Mix voice (1.2x) + music + rain + SFX, levels relative to the voice's gated RMS: music -9 dB, rain -18 dB,
SFX hits -10 dB with peaks <= 0.6x voice peak, cut sounds and cinematic hits on their own stems, everything
ducked under the voice (sidechain), so the narration always stays on top.
Then one linear gain to -14 LUFS and a -1 dBFS limiter (ffmpeg).   python3 shorts/aura/mix.py
The voice is only the level reference: mix.wav holds music + rain + SFX (the narrator records the voice himself);
VOICE=1 puts the voice track in too. The loudness gain is measured with the voice, so a real take drops in at level."""
import os, re, subprocess, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, "audio"); SR = 48000

def load(path):
    tmp = path + ".48k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ar", str(SR), "-ac", "2", tmp], check=True)
    with wave.open(tmp) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64).reshape(-1, 2) / 32768
    os.remove(tmp); return x

def gated_rms(x, gate_db=-40):
    m = x.mean(1); win = SR // 20; k = len(m) // win
    r = np.sqrt((m[:k * win].reshape(k, win) ** 2).mean(1))
    keep = r[r > 10 ** (gate_db / 20)]
    return np.sqrt((keep ** 2).mean()) if len(keep) else 1e-9

voice, music, sfx, rain = [load(os.path.join(A, f)) for f in ("voice_fast.wav", "music.wav", "sfx.wav", "rain.wav")]
n = len(voice)
fit = lambda x: np.pad(x[:n], ((0, max(0, n - len(x))), (0, 0)))
music, sfx, rain = fit(music), fit(sfx), fit(rain)
SPATH = os.path.join(A, "steps.wav")      # the user's footsteps on every heel strike (audio.py), peaks <= 0.4x voice peak
steps = fit(load(SPATH)) if os.path.exists(SPATH) else np.zeros_like(music)
vr = gated_rms(voice); vp = np.abs(voice).max()
db = lambda d: 10 ** (d / 20)
music *= db(-9) * vr / gated_rms(music)
rain *= db(-18) * vr / gated_rms(rain)
sfx *= db(-10) * vr / gated_rms(sfx)
if np.abs(sfx).max() > 0.6 * vp:
    sfx *= 0.6 * vp / np.abs(sfx).max()
if np.abs(steps).max() > 0:
    steps *= 0.4 * vp / np.abs(steps).max()
WPATH = os.path.join(A, "whoosh.wav")     # a whoosh on every scene change (audio.py), peaks 0.55x voice peak
whoosh = fit(load(WPATH)) if os.path.exists(WPATH) else np.zeros_like(music)
if np.abs(whoosh).max() > 0:
    whoosh *= 0.55 * vp / np.abs(whoosh).max()
CPATH = os.path.join(A, "cine.wav")       # anime-film hits/risers/glints (audio.py), peaks 0.7x voice peak
cine = fit(load(CPATH)) if os.path.exists(CPATH) else np.zeros_like(music)
if np.abs(cine).max() > 0:
    cine *= 0.7 * vp / np.abs(cine).max()
# sidechain duck: while the narrator speaks, SFX/cinematic hits drop up to 9 dB and music 3 dB (fast attack,
# slow release), so big moments swell in the gaps between words and never cover a line
from scipy.signal import lfilter
def follow(x, ms):
    a = np.exp(-1 / (SR * ms / 1000)); return lfilter([1 - a], [1, -a], x)
env = np.sqrt(follow(voice.mean(1) ** 2, 30)); on = np.clip(env / (0.35 * vr), 0, 1)
att, rel = np.exp(-1 / (SR * 0.015)), np.exp(-1 / (SR * 0.35))
sm = np.empty_like(on); y = 0.0
for i0 in range(0, len(on), 4800):                      # attack/release smoother (blocks of 0.1 s, vectorised inside)
    seg = on[i0:i0 + 4800]
    up = lfilter([1 - att], [1, -att], seg, zi=[y * att])[0]; dn = lfilter([1 - rel], [1, -rel], seg, zi=[y * rel])[0]
    out = np.where(seg > y, np.maximum(up, dn), dn); sm[i0:i0 + len(seg)] = out; y = out[-1]
duck_fx = (1 - (1 - db(-9)) * sm)[:, None]; duck_mu = (1 - (1 - db(-3)) * sm)[:, None]
KPATH = os.path.join(A, "clicks.wav")     # the user's click on scene changes: loud (peaks 0.9x voice peak), never ducked
clicks = fit(load(KPATH)) if os.path.exists(KPATH) else np.zeros_like(music)
if np.abs(clicks).max() > 0:
    clicks *= 0.9 * vp / np.abs(clicks).max()
RPATH = os.path.join(A, "riser.wav")      # the user's riser over the opening: its loudest half-second as loud as the music bed's
riser = fit(load(RPATH)) if os.path.exists(RPATH) else np.zeros_like(music)          # average, only lightly ducked (-4 dB)
if np.abs(riser).max() > 0:
    win = SR // 2; e = np.sqrt(np.convolve(riser.mean(1) ** 2, np.ones(win) / win, "same"))
    riser *= db(-1) * vr / e.max()                                              # loud: about as loud as the voice
duck_rs = (1 - (1 - db(-3)) * sm)[:, None]
sfx = (sfx + whoosh + cine) * duck_fx + steps + clicks + riser * duck_rs; music = music * duck_mu
for name, x in (("music", music), ("rain", rain), ("sfx", sfx)):
    print(f"{name}: {20 * np.log10(gated_rms(x) / vr):+.1f} dB vs voice (gated RMS), peak {np.abs(x).max() / vp:.2f}x voice peak")
mix = voice + music + rain + sfx
raw = os.path.join(A, "mix_raw.wav")
with wave.open(raw, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix / max(1.0, np.abs(mix).max() * 1.01), -1, 1) * 32767).astype("<i2").tobytes())
meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", meas)[-1])
gain = -14.0 - I
if not os.environ.get("VOICE"):          # bed only, same gain and the same headroom as the full mix
    bed = music + rain + sfx
    with wave.open(raw, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(bed / max(1.0, np.abs(mix).max() * 1.01), -1, 1) * 32767).astype("<i2").tobytes())
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.891:level=false",
                os.path.join(A, "mix.wav")], check=True)
print(f"integrated {I:.1f} LUFS -> gain {gain:+.1f} dB -> mix.wav ({'with' if os.environ.get('VOICE') else 'without'} voice)")
