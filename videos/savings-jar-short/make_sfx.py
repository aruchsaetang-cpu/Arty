"""Builds assets/sfx.wav for this short. Beats are converted to seconds at 87 BPM."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "_shared"))
from sfx import render

K = 60 / 87
T0, T1 = 1.5, 30
MW = (T1 - T0) / 12
ev = []
b = lambda beat, name, g: ev.append((beat * K, name, g))
for m in range(12):
    p = T0 + m * MW
    b(p, "paper", 0.25)                       # new month, page turns
    b(p + 0.9, "coin", 0.6)                   # saves first: coin lands in the jar
    b(p + 0.35, "kaching", 0.35)              # buys first: another bag
    b(p + 1.25, "paper", 0.35)                # lottery: ticket thrown away
    if m + 1 in (1, 5, 9):
        b(p + 2.3, "coin", 0.6)               # saves what's left: only some months
b(T0 + 6 * MW + 0.5, "sparkle", 0.6)          # the one small lottery win
b(T1, "ding", 0.6)
for i in range(4):
    b(31.0 + i, "chalk", 0.7)                 # red pen circles the rank
b(34.3, "sparkle", 0.6); b(34.3, "cheer", 0.6)
render(ev, 24.828, os.path.join(os.path.dirname(__file__), "assets", "sfx.wav"))
