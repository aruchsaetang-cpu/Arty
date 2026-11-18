"""Sentence cues for the "Aura Monster" voiceover -> sentences.json + beats.json.

Times were read from the voiceover's speech segments (silencedetect, -38 dB, 0.25 s) and the syllable
beats inside each segment (energy-envelope peaks). The narrator pauses at commas as well as full stops,
which pins each sentence to its segments, e.g. "Midnight, | no coat, | no hat," and "Then I | saw why."
    python3 shorts/aura/cues.py"""
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
sents = [dict(beat=b, start=s, end=e, text=t) for b, s, e, t in CUES]
json.dump(sents, open(os.path.join(HERE, "sentences.json"), "w"), indent=1)
order = []
for c in CUES:
    if c[0] not in order: order.append(c[0])
first = {b: min(c[1] for c in CUES if c[0] == b) for b in order}
beats = []
for k, b in enumerate(order):
    s0 = 0.0 if k == 0 else first[b] - 0.15                       # cut just before the first word of the shot
    s1 = DUR if k == len(order) - 1 else first[order[k + 1]] - 0.15
    beats.append(dict(id=b, text=" ".join(c[3] for c in CUES if c[0] == b), start=round(s0, 3), end=round(s1, 3),
                      f0=round(s0 * 30) + 1, f1=round(s1 * 30)))
freeze = next(c[1] for c in CUES if c[3].startswith("The rain stopped"))
json.dump(dict(duration=DUR, frames=round(DUR * 30), freeze=freeze, freeze_frame=round(freeze * 30) + 1, beats=beats),
          open(os.path.join(HERE, "beats.json"), "w"), indent=1)
for b in beats:
    print(f'{b["id"]:7s} {b["start"]:6.2f}-{b["end"]:6.2f}s frames {b["f0"]:4d}-{b["f1"]:4d}')
print("rain freezes at", freeze, "s")
