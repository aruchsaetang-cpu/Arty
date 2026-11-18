"""Mix voice (1.2x) + music + rain + SFX, levels relative to the voice's gated RMS: music -9 dB, rain -18 dB,
SFX hits -10 dB with peaks <= 0.6x voice peak, so the narration always stays on top.
Then one linear gain to -14 LUFS and a -1 dBFS limiter (ffmpeg).   python3 shorts/aura/mix.py"""
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
vr = gated_rms(voice); vp = np.abs(voice).max()
db = lambda d: 10 ** (d / 20)
music *= db(-9) * vr / gated_rms(music)
rain *= db(-18) * vr / gated_rms(rain)
sfx *= db(-10) * vr / gated_rms(sfx)
if np.abs(sfx).max() > 0.6 * vp:
    sfx *= 0.6 * vp / np.abs(sfx).max()
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
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.891:level=false",
                os.path.join(A, "mix.wav")], check=True)
print(f"integrated {I:.1f} LUFS -> gain {gain:+.1f} dB -> mix.wav")
