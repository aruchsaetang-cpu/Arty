"""Builds assets/sfx.wav for this short. Beats are converted to seconds at 87 BPM."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "_shared"))
from sfx import render

K = 60 / 87
T0, T1, DAYS = 1.5, 30, 30
DW = (T1 - T0) / DAYS
runs = {"H": [1], "G": [10, 25], "W": [6, 7, 13, 14, 20, 21, 27, 28], "E": list(range(1, 31))}
ev = []
b = lambda beat, name, g: ev.append((beat * K, name, g))
for d in range(1, DAYS + 1):
    n = sum(d in v for v in runs.values())             # one chalk stroke per X; louder when several land together
    b(T0 + (d - 1) * DW + 0.45 * DW, "chalk", 0.35 + 0.12 * (n - 1))
b(T0 + 0.3, "kaching", 0.4)                             # gear first: buys the shoes
b(T0 + DW, "thud", 0.7); b(T0 + DW + 0.1, "buzz", 0.4)  # hero: day 2, cannot walk
b(T1, "ding", 0.6)
for i in range(4):
    b(31.0 + i, "chalk", 0.8); b(31.0 + i, "pop", 0.35)
b(34.2, "sparkle", 0.6); b(34.2, "cheer", 0.6)
render(ev, 24.828, os.path.join(os.path.dirname(__file__), "assets", "sfx.wav"))
