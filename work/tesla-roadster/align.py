#!/usr/bin/env python3
"""Word timings for a known script without Whisper.

With --audio: detect pauses in the voiceover, cut every pause down to GAP seconds
(Zack D pacing), loudness-normalise, and spread the script's words across each
speech segment proportionally to their length.
Without --audio: fake a 3 words/s read and write a silent track (for a draft).

Writes <out>/vo.wav and <out>/vo.json (Whisper-style segments[].words[]).
usage: align.py --script lines.txt --out dir [--audio vo.mp3]
"""
import argparse, json, os, re, subprocess

GAP = 0.10          # pause kept between phrases
WPS = 3.0           # draft reading speed


def words_of(text):
    return [w for w in re.split(r"\s+", text.replace("…", "… ").strip()) if w]


def weight(w):
    return 0.12 + len(re.sub(r"[^\w]", "", w)) * 0.055


def spread(words, t0, t1):
    tot = sum(weight(w) for w in words); t = t0; out = []
    for w in words:
        d = (t1 - t0) * weight(w) / tot
        out.append({"word": " " + w, "start": round(t, 3), "end": round(t + d * 0.92, 3)}); t += d
    return out


def speech_segments(path):
    log = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=n=-38dB:d=0.18", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    segs, cur = [], 0.0
    for s, e in zip(starts, ends + [dur] * (len(starts) - len(ends))):
        if s - cur > 0.05:
            segs.append((cur, s))
        cur = e
    if dur - cur > 0.05:
        segs.append((cur, dur))
    return [(max(0, a - 0.03), min(dur, b + 0.05)) for a, b in segs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, help="text file, one sentence/phrase per line")
    ap.add_argument("--audio")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lines = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip()]
    # phrases = split lines at commas / ellipses / question marks: natural pause points
    phrases = [p for l in lines for p in re.split(r"(?<=[,?…;])\s+", l) if p]
    wav = os.path.join(a.out, "vo.wav")

    if not a.audio:
        words, t = [], 0.0
        for p in phrases:
            ws = words_of(p); d = len(ws) / WPS
            words += spread(ws, t, t + d); t += d + GAP
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                        "-t", f"{t + 0.6:.2f}", wav], check=True)
    else:
        segs = speech_segments(a.audio)
        # build the tightened track: speech segments joined with GAP silence
        parts = "".join(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,apad=pad_dur={GAP}[s{i}];" for i, (s, e) in enumerate(segs))
        fc = parts + "".join(f"[s{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1,highpass=f=70," \
             "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5:LRA=4[o]"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.audio, "-filter_complex", fc, "-map", "[o]",
                        "-ac", "1", "-ar", "48000", wav], check=True)
        new, t = [], 0.0
        for s, e in segs:
            new.append((t, t + e - s)); t += e - s + GAP
        # map phrases onto speech segments: equal counts -> 1:1, otherwise by share of total length
        allw = [words_of(p) for p in phrases]
        if len(new) == len(phrases):
            groups = list(zip(allw, new))
        else:
            flat = [w for ws in allw for w in ws]
            tot_w = sum(weight(w) for w in flat); tot_t = sum(b - x for x, b in new)
            groups, i = [], 0
            for (x, b) in new:                       # fill each segment with words until its time share
                share, got = (b - x) / tot_t * tot_w, []
                while i < len(flat) and (sum(weight(w) for w in got) < share * 0.97 or not got):
                    got.append(flat[i]); i += 1
                groups.append((got, (x, b)))
            if i < len(flat):
                groups[-1] = (groups[-1][0] + flat[i:], groups[-1][1])
        words = [w for ws, (x, b) in groups if ws for w in spread(ws, x, b)]
        print(f"{len(segs)} speech segments, {len(phrases)} phrases -> {'1:1' if len(new) == len(phrases) else 'proportional'} mapping")
    json.dump({"segments": [{"words": words}]}, open(os.path.join(a.out, "vo.json"), "w"), indent=1)
    print(f"{len(words)} words, ends at {words[-1]['end']:.2f}s -> {a.out}/vo.json, vo.wav")


if __name__ == "__main__":
    main()
