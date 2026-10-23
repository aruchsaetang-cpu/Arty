#!/usr/bin/env python3
"""Group Whisper words into caption cards like the reference: 1 phrase, 1 line.

usage: chunk_captions.py words.json captions.json [--fix fixes.json]

Rules (style-guide.md §3):
  * target 0.74 s per card, never shorter than 0.43 s nor longer than 1.47 s
  * at most 13 base Thai characters (upper/lower vowels and tone marks don't count)
    or 13 Latin characters
  * cards are phrases: a card prefers to start on a phrase-opening word (ใน, ถ้า, ที่ ...)
    and to end on a phrase-closing word (ว่า, นี้, เลย ...); never ends on an opener
  * Thai and Latin words are not mixed in one card when it can be avoided
  * cards butt against each other; the composition leaves the 1-frame gap
Segmentation is a dynamic program over all split points (cost = timing + phrase penalties).
--fix: optional {"wrong": "right"} map applied to each word (fix Whisper typos, brand names).
"""
import argparse
import json
import re

# Thai combining marks: mai han-akat, sara i..u, phinthu, maitaikhu..yamakkan
COMBINING = re.compile("[ัิ-ฺ็-๎]")
MAX_BASE, MAX_LATIN = 13, 13
TARGET, MIN_DUR, MAX_DUR = 0.74, 0.43, 1.47
OPENERS = {
    "ใน", "ถ้า", "ที่", "ซึ่ง", "เพราะ", "ทำให้", "แม้แต่", "แม้", "จึง", "ตอน", "ระหว่าง", "เป็น", "มี",
    "เขา", "แต่", "และ", "หรือ", "เมื่อ", "ให้", "คือ", "โดย", "เพื่อ", "จาก", "ถึง", "หลังจาก", "ก่อน",
    "ทั้งที่", "พอ", "เลยทำให้", "ส่วน", "ตั้งแต่", "จนถึง", "นอกจาก", "ไม่ใช่", "เรา", "คุณ", "ผม", "ฉัน",
    "เพื่อนๆ", "ผู้กำกับ",
}
CLOSERS = {"ว่า", "นี้", "นั้น", "เลย", "มาก", "กัน", "ด้วย", "แล้ว", "ครับ", "ค่ะ", "นะ", "ไหม", "มั้ย", "อีก", "ได้"}


def is_latin(w):
    return bool(re.match(r"[A-Za-z0-9]", w))


def width(text):
    if re.search("[฀-๿]", text):
        return len(COMBINING.sub("", text.replace(" ", "")))
    return len(text) * MAX_BASE / MAX_LATIN


def join(a, b):
    if not a:
        return b
    if is_latin(a[-1]) or is_latin(b[0]) or a.endswith("ๆ"):
        return a + " " + b
    return a + b


def card_cost(words, i, j):
    """cost of one card made of words[i:j]"""
    if any(w.get("brk") for w in words[i : j - 1]):
        return None  # a marked break (align_script.py "/" or line end) falls inside this card
    text = ""
    for w in words[i:j]:
        text = join(text, w["word"])
    dur = words[j - 1]["end"] - words[i]["start"]
    if width(text) > MAX_BASE and j - i > 1:
        return None
    if dur > MAX_DUR and j - i > 1:
        return None
    c = ((dur - TARGET) / 0.25) ** 2
    if dur < MIN_DUR:
        c += 4
    last, first = words[j - 1]["word"], words[i]["word"]
    if last in OPENERS and j - i > 1:
        c += 6  # never end on an opener ("...ใน")
    if words[j - 1].get("brk"):
        c -= 3  # ending on a marked break is what the author asked for
    elif j < len(words):
        nxt = words[j]["word"]
        if nxt in OPENERS:
            c -= 1.5
        elif last in CLOSERS:
            c -= 1.0
        else:
            c += 1.5  # splitting inside a phrase
        if nxt in CLOSERS:
            c += 3  # a closer belongs to the card before it
    if first in OPENERS:
        c -= 0.5
    kinds = {is_latin(w["word"]) for w in words[i:j]}
    if len(kinds) > 1:
        c += 2.5
    return c


def chunk(words):
    n = len(words)
    best = [0.0] + [float("inf")] * n
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - 12), j):
            if best[i] == float("inf"):
                continue
            c = card_cost(words, i, j)
            if c is not None and best[i] + c < best[j]:
                best[j], back[j] = best[i] + c, i
    cuts, j = [], n
    while j > 0:
        cuts.append((back[j], j))
        j = back[j]
    cards = []
    for i, j in reversed(cuts):
        text = ""
        for w in words[i:j]:
            text = join(text, w["word"])
        cards.append({"start": words[i]["start"], "end": words[j - 1]["end"], "text": text})
    # cards butt against each other; only the last card is held to the minimum length
    for a, b in zip(cards, cards[1:]):
        a["end"] = b["start"]
    cards[-1]["end"] = max(cards[-1]["end"], cards[-1]["start"] + MIN_DUR)
    for c in cards:
        c["start"], c["end"] = round(c["start"], 3), round(c["end"], 3)
    return cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("out")
    ap.add_argument("--fix")
    a = ap.parse_args()
    words = [w for w in json.load(open(a.words)) if w["word"].strip()]
    if a.fix:
        fixes = json.load(open(a.fix))
        for w in words:
            for k, v in fixes.items():
                w["word"] = w["word"].replace(k, v)
    cards = chunk(words)
    json.dump(cards, open(a.out, "w"), ensure_ascii=False, indent=1)
    durs = [c["end"] - c["start"] for c in cards]
    print(f"{len(cards)} cards, mean {sum(durs) / len(durs):.2f}s, min {min(durs):.2f}s, max {max(durs):.2f}s")


if __name__ == "__main__":
    main()
