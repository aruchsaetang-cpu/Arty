#!/usr/bin/env python3
"""Openverse sound effects: search openly licensed audio and download it, with credits, for a video project.

    openverse.py search "umbrella open" [--n 10] [--min-sec 1] [--max-sec 8] [--source wikimedia_audio] [--any-license]
    openverse.py get ID [ID ...] --out DIR [--name NAME]
    openverse.py add ID FILE --out DIR [--name NAME]    (a file the user downloaded from the Openverse page)

search  lists matches (id, seconds, license, source, title, creator). By default only licenses that allow
        commercial use and modification (CC0, CC BY, CC BY-SA, PDM) are returned, so the sound can go in a
        published video. --any-license drops that filter (NC/ND sounds then need care).
get     downloads each sound, converts it to 48 kHz WAV (DIR/NAME.wav, NAME defaults to a slug of the
        title) and appends its attribution line to DIR/CREDITS.md. CC BY / BY-SA sounds must be credited
        in the video description; CC0 / PDM need no credit but are listed anyway.
Uses only the anonymous Openverse API (api.openverse.org); files come from the source hosts
(cdn.freesound.org, upload.wikimedia.org, ...), which the network must allow."""
import argparse, json, os, re, ssl, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request

API = "https://api.openverse.org/v1/audio/"
UA = "openverse-sfx/1.0 (+https://openverse.org; video sound-effects tool)"

def ctx():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if not ca and os.path.exists("/root/.ccr/ca-bundle.crt"): ca = "/root/.ccr/ca-bundle.crt"
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()

def fetch(url, tries=5):
    """GET with backoff: the anonymous API answers 500/429 under load, Wikimedia answers 429 with Retry-After."""
    import time
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120, context=ctx()) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or k == tries - 1: raise
            time.sleep(min(60, int(e.headers.get("Retry-After") or 0) or 3 * 2 ** k))

def search(q, n=10, max_sec=None, any_license=False, source=None, min_sec=None):
    p = {"q": q, "page_size": 20 if (max_sec or min_sec) else min(n, 20)}   # anonymous API: at most 20 per page
    if source: p["source"] = source
    if not any_license: p["license_type"] = "commercial,modification"
    rs = json.loads(fetch(API + "?" + urllib.parse.urlencode(p)))["results"]
    if max_sec: rs = [r for r in rs if r.get("duration") and r["duration"] <= max_sec * 1000]
    if min_sec: rs = [r for r in rs if r.get("duration") and r["duration"] >= min_sec * 1000]
    return rs[:n]

def credit(r):
    lic = r["license"].upper() if r["license"] in ("cc0", "pdm") else f'CC {r["license"].upper()} {r["license_version"]}'
    return f'- "{r["title"]}" by {r.get("creator") or "unknown"} ({r["source"]}), {lic}: {r["foreign_landing_url"]}'

def slug(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "sound"

def save(r, src, out, nm):
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, nm + ".wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", "48000", "-c:a", "pcm_s16le", dst], check=True)
    cred = os.path.join(out, "CREDITS.md")
    if not os.path.exists(cred): open(cred, "w").write("# Sound effects (via Openverse)\n\n")
    line = f"- `{nm}.wav`: " + credit(r)[2:]
    if line not in open(cred).read(): open(cred, "a").write(line + "\n")
    print("saved", dst, "|", credit(r)[2:])

def get(ids, out, name=None):
    for k, i in enumerate(ids):
        r = json.loads(fetch(API + i + "/"))
        nm = (f"{name}_{k + 1}" if len(ids) > 1 else name) if name else slug(r["title"])
        try: data = fetch(r["url"])
        except urllib.error.HTTPError as e:
            sys.exit(f"{r['url']} answered {e.code} ({'rate-limited' if e.code == 429 else 'refused'}). Retry later, or download it from "
                     f"{r['foreign_landing_url']} and run: openverse.py add {i} FILE --out {out} --name {nm}")
        with tempfile.NamedTemporaryFile(suffix="." + (r.get("filetype") or "mp3")) as f:
            f.write(data); f.flush(); save(r, f.name, out, nm)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("search"); s.add_argument("q"); s.add_argument("--n", type=int, default=10)
    s.add_argument("--max-sec", type=float); s.add_argument("--min-sec", type=float)
    s.add_argument("--source", help="e.g. wikimedia_audio, freesound, jamendo"); s.add_argument("--any-license", action="store_true")
    g = sp.add_parser("get"); g.add_argument("ids", nargs="+"); g.add_argument("--out", required=True); g.add_argument("--name")
    d = sp.add_parser("add"); d.add_argument("id"); d.add_argument("file"); d.add_argument("--out", required=True); d.add_argument("--name")
    a = ap.parse_args()
    if a.cmd == "search":
        for r in search(a.q, a.n, a.max_sec, a.any_license, a.source, a.min_sec):
            print(f'{r["id"]}  {(r.get("duration") or 0) / 1000:6.1f}s  {r["license"]:6s} {r["source"]:10s} {r["title"][:48]}  — {r.get("creator") or ""}')
    elif a.cmd == "add":
        r = json.loads(fetch(API + a.id + "/")); save(r, a.file, a.out, a.name or slug(r["title"]))
    else:
        get(a.ids, a.out, a.name)
