"""Cut the user's voiceover recording into per-line takes for cues2.py.

    python3 shorts/aura/cut_vo.py NARRATION.wav NARRATION.json HERO.wav [TEMPO]
NARRATION.json: Whisper word timestamps of the narration (whisper --word_timestamps True --output_format json).
The narration holds every script line except the hero's ("You'll catch a cold, kid."), which is its own file.
Each line is cut at the quietest point between its last word and the next line's first word, trimmed of
silence, sped up by TEMPO (default 1.2, pitch kept) and written to audio/lines/lNN.wav."""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
L = json.load(open(os.path.join(HERE, "script_v2.json")))
HERO_LINE = 12
narr, narr_json, hero = sys.argv[1:4]; TEMPO = float(sys.argv[4]) if len(sys.argv) > 4 else 1.2

def load(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, "<i2").astype(np.float32) / 32768

def trim(x, db=-42):
    win = SR // 100; k = len(x) // win
    e = np.sqrt((x[:k * win].reshape(k, win) ** 2).mean(1)); on = np.where(e > 10 ** (db / 20))[0]
    return x[max(0, on[0] - 2) * win:(on[-1] + 3) * win] if len(on) else x

def squeeze(x, db=-45, longest=0.18, keep=0.1):
    """Shorten every pause inside a line that is longer than `longest` s to `keep` s (5 ms fades at the joins)."""
    win = SR // 100; k = len(x) // win
    quiet = 20 * np.log10(np.sqrt((x[:k * win].reshape(k, win) ** 2).mean(1)) + 1e-9) < db
    out, pos, f, fade = [], 0, 0, np.linspace(0, 1, SR // 200)
    while f < k:
        if not quiet[f]: f += 1; continue
        g = f
        while g < k and quiet[g]: g += 1
        if (g - f) * win > longest * SR:
            cut0, cut1 = f * win + int(keep / 2 * SR), g * win - int(keep / 2 * SR)
            a = x[pos:cut0].copy(); a[-len(fade):] *= fade[::-1]; out.append(a); pos = cut1
            x = x.copy(); x[pos:pos + len(fade)] *= fade
        f = g
    out.append(x[pos:]); return np.concatenate(out)

def save(path, x):
    x = squeeze(trim(x))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-af", f"atempo={TEMPO:.4f}", "-c:a", "pcm_s16le", path], input=x.astype(np.float32).tobytes(), check=True)

x = load(narr)
words = [w for s in json.load(open(narr_json))["segments"] for w in s["words"]]
lines = [k for k in range(len(L)) if k != HERO_LINE]
counts = [len(L[k][1].split()) for k in lines]
assert sum(counts) == len(words), f"script has {sum(counts)} words, recording has {len(words)}"
win = SR // 100
env = np.convolve(x ** 2, np.ones(win) / win, "same")
bounds, i = [0], 0
for c in counts[:-1]:
    i += c
    a, b = words[i - 1]["end"] - 0.05, words[i]["start"] + 0.05     # search the gap (Whisper edges are loose)
    a, b = int(min(a, b - 0.2) * SR), int(max(b, a + 0.2) * SR)
    bounds.append(a + int(np.argmin(env[a:b])))
bounds.append(len(x))
os.makedirs(os.path.join(HERE, "audio", "lines"), exist_ok=True)
for k, s, e in zip(lines, bounds[:-1], bounds[1:]):
    save(os.path.join(HERE, "audio", "lines", f"l{k:02d}.wav"), x[s:e])
save(os.path.join(HERE, "audio", "lines", f"l{HERO_LINE:02d}.wav"), load(hero))
print("wrote", len(L), "lines at", TEMPO, "x")
