"""Word timings for captions: align the script (sentences.json) to Whisper's word timestamps (whisper_words.json,
from `whisper small.en` on audio/voice_fast.wav). Script spelling wins (Whisper hears "Seoul", "Oramonster").
Writes words.json: [{w, s, e, sent, key}] and chunks.json (caption groups of <=3 words, split at punctuation).
    python3 shorts/aura/words.py"""
import difflib, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
sents = json.load(open(os.path.join(HERE, "sentences.json")))
wh = json.load(open(os.path.join(HERE, "whisper_words.json")))
norm = lambda w: re.sub(r"[^a-z']", "", w.lower().replace("’", "'"))
script = [(w, k) for k, s in enumerate(sents) for w in s["text"].replace("“", "").replace("”", "").split()]
a, b = [norm(w) for w, _ in script], [norm(x["w"]) for x in wh]
out = [None] * len(script)
for tag, i0, i1, j0, j1 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
    if tag == "equal":
        for d in range(i1 - i0): out[i0 + d] = (wh[j0 + d]["s"], wh[j0 + d]["e"])
    elif j1 > j0:   # replaced span: spread Whisper's time range over the script words by length
        s0, s1 = wh[j0]["s"], wh[j1 - 1]["e"]; L = [len(a[i]) + 1 for i in range(i0, i1)]; t = s0
        for i, l in zip(range(i0, i1), L):
            d = (s1 - s0) * l / sum(L); out[i] = (t, t + d); t += d
for i in range(len(out)):   # words Whisper missed: squeeze between neighbours
    if out[i] is None:
        p = out[i - 1][1] if i else 0.0
        n = next((o[0] for o in out[i + 1:] if o), p + 0.3); out[i] = (p, max(p + 0.05, n))
KEY = {"wet.", "aura", "monster.", "dry.", "luck.", "trick.", "magic.", "dodging", "storm", "kid.", "teach", "closed", "two", "wet."}
words = [dict(w=w, s=round(s, 3), e=round(e, 3), sent=k, key=w.lower().strip('“”"') in KEY)
         for (w, k), (s, e) in zip(script, out)]
json.dump(words, open(os.path.join(HERE, "words.json"), "w"), indent=0)
chunks, cur = [], []
for i, w in enumerate(words):
    cur.append(i)
    nxt = words[i + 1] if i + 1 < len(words) else None
    if len(cur) == 3 or re.search(r"[.,!?”]$", w["w"]) or not nxt or nxt["sent"] != w["sent"]:
        chunks.append(cur); cur = []
json.dump([dict(words=c, s=words[c[0]]["s"], e=words[c[-1]]["e"]) for c in chunks], open(os.path.join(HERE, "chunks.json"), "w"), indent=0)
print(len(words), "words,", len(chunks), "chunks")
for c in chunks[:6]: print(f'{words[c[0]]["s"]:6.2f}', " ".join(words[i]["w"] for i in c))
