#!/usr/bin/env python3
"""Thai speech -> word timestamps (words.json) with Whisper.

usage: transcribe.py IN.(mp4|wav|m4a) words.json [--model medium] [--lang th]

Uses faster-whisper if installed, otherwise openai-whisper.
Output: [{"start": s, "end": s, "word": "..."}]
Install: pip install openai-whisper   (or: pip install faster-whisper)
The first run downloads the model from the internet (HuggingFace / openaipublic).

If HuggingFace is blocked but github.com is not, use the ONNX build of Whisper from sherpa-onnx:
  pip install sherpa-onnx
  curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.tar.bz2
  tar xjf sherpa-onnx-whisper-small.tar.bz2
  transcribe.py voice_tight.wav segments.json --sherpa sherpa-onnx-whisper-small --cuts cuts.json
That mode gives text per speech chunk (the --cuts ranges from tighten.py, run on the
untightened file), not per word: use the chunk start times as --anchors for align_script.py.
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


def with_sherpa(path, model_dir, cuts, lang):
    import subprocess

    import numpy as np
    import sherpa_onnx

    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{model_dir}/small-encoder.onnx", decoder=f"{model_dir}/small-decoder.onnx",
        tokens=f"{model_dir}/small-tokens.txt", language=lang, task="transcribe", num_threads=4,
    )
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    out, t = [], 0.0
    for c in cuts:
        d = c["end"] - c["start"]
        if d >= 0.2:
            pad = np.zeros(3200, np.float32)
            s = rec.create_stream()
            s.accept_waveform(16000, np.concatenate([pad, x[int(c["start"] * 16000): int(c["end"] * 16000)], pad]))
            rec.decode_stream(s)
            out.append({"start": round(t, 3), "end": round(t + d, 3), "text": s.result.text.strip()})
        t += d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--lang", default="th")
    ap.add_argument("--sherpa", help="sherpa-onnx Whisper model dir (chunk-level text, see above)")
    ap.add_argument("--cuts", help="tighten.py --cuts JSON (required with --sherpa; src = the untightened file)")
    a = ap.parse_args()
    if a.sherpa:
        segs = with_sherpa(a.src, a.sherpa, json.load(open(a.cuts)), a.lang)
        json.dump(segs, open(a.out, "w"), ensure_ascii=False, indent=1)
        for x in segs:
            print(f"{x['start']:6.2f}-{x['end']:6.2f}  {x['text']}")
        return
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
