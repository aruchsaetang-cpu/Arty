#!/usr/bin/env python3
"""Thai speech -> word timestamps (words.json) with Whisper.

usage: transcribe.py IN.(mp4|wav|m4a) words.json [--model medium] [--lang th]

Uses faster-whisper if installed, otherwise openai-whisper.
Output: [{"start": s, "end": s, "word": "..."}]
Install: pip install openai-whisper   (or: pip install faster-whisper)
The first run downloads the model from the internet (HuggingFace / openaipublic).
"""
import argparse
import json


def with_faster_whisper(path, model, lang):
    from faster_whisper import WhisperModel

    m = WhisperModel(model, device="auto", compute_type="int8")
    segs, _ = m.transcribe(path, language=lang, word_timestamps=True, vad_filter=False)
    return [{"start": w.start, "end": w.end, "word": w.word} for s in segs for w in (s.words or [])]


def with_openai_whisper(path, model, lang):
    import whisper

    r = whisper.load_model(model).transcribe(path, language=lang, word_timestamps=True)
    return [{"start": w["start"], "end": w["end"], "word": w["word"]} for s in r["segments"] for w in s.get("words", [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--lang", default="th")
    a = ap.parse_args()
    try:
        words = with_faster_whisper(a.src, a.model, a.lang)
    except ImportError:
        words = with_openai_whisper(a.src, a.model, a.lang)
    words = [
        {"start": round(w["start"], 3), "end": round(w["end"], 3), "word": w["word"].strip()}
        for w in words
        if w["word"].strip()
    ]
    json.dump(words, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(words)} words -> {a.out}")


if __name__ == "__main__":
    main()
