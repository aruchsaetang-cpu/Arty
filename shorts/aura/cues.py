"""Sentence cues for the "Aura Monster" voiceover -> sentences.json + beats.json.

Times were read from the voiceover's speech segments (silencedetect, -38 dB, 0.25 s) and the syllable
beats inside each segment (energy-envelope peaks). The narrator pauses at commas as well as full stops,
which pins each sentence to its segments, e.g. "Midnight, | no coat, | no hat," and "Then I | saw why."
    python3 shorts/aura/cues.py
Times below are measured on the original take; they are divided by TEMPO for the 1.2x voice."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CUES = [  # beat, start, end, text
    ("hook",   0.28,  3.96, "It had rained in Sol for nine years."),
    ("hook",   4.23,  6.45, "One man never got wet."),
    ("name",   6.92,  9.45, "They called him Aura monster."),
    ("name",   9.76, 12.65, "Midnight, no coat, no hat, bone dry."),
    ("theory", 13.15, 14.86, "The shopkeepers said luck."),
    ("theory", 14.86, 16.56, "The police said a trick."),
    ("theory", 16.92, 19.02, "The kids said magic."),
    ("follow", 19.28, 20.76, "So one night I followed him."),
    ("follow", 21.22, 22.53, "The rain stopped around me."),
    ("follow", 22.93, 24.28, "Then I saw why."),
    ("reveal", 24.78, 26.33, "He wasn't dodging the storm."),
    ("reveal", 26.33, 30.52, "He was holding it up, one walk at a time, so the city could sleep."),
    ("turn",   31.16, 33.19, "He turned, tired, and smiled."),
    ("turn",   33.69, 34.15, "“Your turn.”"),
    ("payoff", 34.89, 37.19, "Now I walk these streets at midnight."),
    ("payoff", 37.67, 39.33, "And I never get wet."),
]
DUR = 39.68
TEMPO = 1.2          # voiceover sped up with ffmpeg atempo (audio/voice_fast.wav); pauses scale exactly by 1/TEMPO
CUES = [(b, round(s0 / TEMPO, 3), round(s1 / TEMPO, 3), t) for b, s0, s1, t in CUES]
DUR = round(DUR / TEMPO, 3)
sents = [dict(beat=b, start=s, end=e, text=t) for b, s, e, t in CUES]
json.dump(sents, open(os.path.join(HERE, "sentences.json"), "w"), indent=1)
# ~3 s shots, each cut 0.15 s before the first word of its sentence
SHOTS = [("hook_wide", 0), ("hook_feet", 1), ("name_med", 2), ("name_close", 3), ("shop", 4), ("cop", 5), ("kids", 6),
         ("follow", 7), ("freeze", 8), ("reveal_low", 10), ("reveal_crane", 11), ("turn", 12), ("payoff_side", 14),
         ("payoff_wide", 15)]
shots = []
for k, (sid, si) in enumerate(SHOTS):
    s0 = 0.0 if k == 0 else CUES[si][1] - 0.15
    s1 = DUR if k == len(SHOTS) - 1 else CUES[SHOTS[k + 1][1]][1] - 0.15
    shots.append(dict(id=sid, start=round(s0, 3), end=round(s1, 3), f0=round(s0 * 30) + 1, f1=round(s1 * 30)))
freeze = next(c[1] for c in CUES if c[3].startswith("The rain stopped"))
json.dump(dict(duration=DUR, frames=round(DUR * 30), freeze=freeze, freeze_frame=round(freeze * 30) + 1, shots=shots),
          open(os.path.join(HERE, "beats.json"), "w"), indent=1)
for b in shots:
    print(f'{b["id"]:13s} {b["start"]:6.2f}-{b["end"]:6.2f}s ({b["end"] - b["start"]:4.2f}s) frames {b["f0"]:4d}-{b["f1"]:4d}')
print("rain freezes at", freeze, "s; total", DUR, "s")
