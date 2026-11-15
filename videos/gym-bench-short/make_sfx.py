"""Builds assets/sfx.wav for this short. Beats are converted to seconds at 87 BPM."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "_shared"))
from sfx import render

K = 60 / 87
T0, T1 = 1.5, 30
ev = []
b = lambda beat, name, g: ev.append((beat * K, name, g))
for w in range(1, 12):                                       # a tick every new week
    b(T0 + w * (T1 - T0) / 12, "tick", 0.35)
for i in range(int(T1 - T0)):                                 # EVERY WEEK: one rep per beat, bar touches at the half beat
    b(T0 + i + 0.5, "clank", 0.22)
for i in range(int((11 - T0) * 2)):                           # QUIT AT WEEK 4: two reps per beat
    b(T0 + i * 0.5 + 0.25, "clank", 0.12)
for i in range(6):
    b(12.4 + i * 0.36, "step", 0.5)                           # ...and walks out
b(3.95, "thud", 1.0); b(3.95, "clank", 0.8); b(4.1, "buzz", 0.5)   # EGO LIFT: the bar crashes onto the hooks
x = T0 + 1.45
while x < T1:                                                 # SELFIE FIRST: shutter on every photo
    b(x, "click", 0.6); x += 2
b(T1, "ding", 0.7)
for i in range(4):
    b(31.0 + i, "pop", 0.6)
b(34.2, "sparkle", 0.6); b(34.2, "cheer", 0.7)
render(ev, 24.828, os.path.join(os.path.dirname(__file__), "assets", "sfx.wav"))
