"""v2 story: build the voice track from per-line takes, then sentence cues and the shot list.

    python3 shorts/aura/cues2.py
Inputs: script_v2.json  [beat, text, pause-after-seconds] per line
        audio/lines/lNN.wav   one take per line (scratch: Kokoro TTS; later the user's own recording, cut per line)
Outputs: audio/voice_fast.wav (the voice track), sentences.json, beats.json (shots, frames, slow-mo window).
Each line's slot = its take trimmed of silence + its pause. A replacement take that runs longer than the slot
is sped up (atempo) to fit, so the picture never needs re-rendering when the real voiceover arrives."""
import json, os, subprocess, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(HERE, "audio"); SR = 48000; FPS = 30
L = json.load(open(os.path.join(HERE, "script_v2.json")))
LEAD = 0.3                                   # silence before the first word
SLOTS = os.path.join(HERE, "slots.json")     # frozen slot lengths once the picture is rendered

def load(path):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, "<i2").astype(np.float32) / 32768

def trim(x, db=-42):
    win = SR // 100; k = len(x) // win
    e = np.sqrt((x[:k * win].reshape(k, win) ** 2).mean(1)); on = np.where(e > 10 ** (db / 20))[0]
    return x[max(0, on[0] - 2) * win:(on[-1] + 3) * win] if len(on) else x

def atempo(x, r):
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", f"atempo={r:.4f}",
                        "-f", "f32le", "-"], input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32)

takes = [trim(load(os.path.join(A, "lines", f"l{k:02d}.wav"))) for k in range(len(L))]
frozen = json.load(open(SLOTS)) if os.path.exists(SLOTS) else None
t = LEAD; sents = []; track = [np.zeros(int(LEAD * SR), np.float32)]
for k, ((beat, text, pause), x) in enumerate(zip(L, takes)):
    d = len(x) / SR
    if frozen:                               # fit a new take into the slot the picture was cut to
        speak = frozen[k]["speak"]
        if d > speak:
            x = atempo(x, d / speak); d = len(x) / SR
        gap = frozen[k]["slot"] - d
    else:                                    # room for a slower human read: each slot is 20% longer than the scratch take
        gap = pause + 0.2 * d
    sents.append(dict(beat=beat, text=text, start=round(t, 3), end=round(t + d, 3)))
    track += [x, np.zeros(int(round(gap * SR)), np.float32)]
    t += d + gap
if not frozen:
    json.dump([dict(speak=round(1.2 * (s["end"] - s["start"]), 3), slot=round(1.2 * (s["end"] - s["start"]) + p, 3))
               for s, (_, _, p) in zip(sents, L)], open(SLOTS, "w"), indent=1)
v = np.concatenate(track)
v = v / max(1e-6, np.abs(v).max()) * 0.89
with wave.open(os.path.join(A, "voice_fast.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((v * 32767).astype("<i2").tobytes())
DUR = round(len(v) / SR, 3)
json.dump(sents, open(os.path.join(HERE, "sentences.json"), "w"), indent=1)

# shots: (id, sentence index that opens it) - each cut lands 0.15 s before its first word
SHOTS = [("hook_wide", 0), ("hook_feet", 1), ("name_close", 2), ("name_med", 3), ("shop", 4), ("cop", 5), ("kids", 6),
         ("follow", 7), ("alley_pov", 8), ("reveal_low", 9), ("reveal_close", 10), ("turn", 11), ("teach", 13),
         ("train_roof", 14), ("train_umb", 15), ("train_mont", 16), ("close", 17), ("payoff_two", 18), ("payoff_wide", 19)]
shots = []
for k, (sid, si) in enumerate(SHOTS):
    s0 = 0.0 if k == 0 else sents[si]["start"] - 0.15
    s1 = DUR if k == len(SHOTS) - 1 else sents[SHOTS[k + 1][1]]["start"] - 0.15
    shots.append(dict(id=sid, start=round(s0, 3), end=round(s1, 3), f0=round(s0 * FPS) + 1, f1=round(s1 * FPS)))
B = {s["id"]: s for s in shots}
# slow motion ("Then I saw it" -> "...too fast for the storm to touch him"): the rain crawls, he doesn't
json.dump(dict(duration=DUR, frames=round(DUR * FPS), slow0=B["alley_pov"]["f0"] + 12, slow1=B["reveal_close"]["f1"],
               shots=shots), open(os.path.join(HERE, "beats.json"), "w"), indent=1)
for b in shots:
    print(f'{b["id"]:13s} {b["start"]:6.2f}-{b["end"]:6.2f}s ({b["end"] - b["start"]:4.2f}s) frames {b["f0"]:4d}-{b["f1"]:4d}')
print("total", DUR, "s,", round(DUR * FPS), "frames")
