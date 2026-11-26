"""Write subs.ass from sentences.json (one sentence at a time).   python3 shorts/aura/subs.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
sents = json.load(open(os.path.join(HERE, "sentences.json")))

def ts(t):
    h, r = divmod(max(0.0, t), 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def wrap(s, width=26):
    rows, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > width and cur:
            rows.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    rows.append(cur)
    return "\\N".join(rows)

hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,DejaVu Sans,62,&H00FFFFFF,&H00FFFFFF,&H00101010,&H64000000,-1,0,0,0,100,100,1,0,1,4,2,2,90,90,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
with open(os.path.join(HERE, "subs.ass"), "w") as f:
    f.write(hdr)
    for k, s in enumerate(sents):   # keep each line up until the next one starts (no flicker in short pauses)
        end = sents[k + 1]["start"] - 0.03 if k + 1 < len(sents) and sents[k + 1]["start"] - s["end"] < 0.8 else s["end"] + 0.25
        f.write(f"Dialogue: 0,{ts(s['start'] - 0.05)},{ts(end)},Sub,,0,0,0,{{\\fad(70,70)}},{wrap(s['text'])}\n")
print("subs.ass:", len(sents), "lines")
