#!/usr/bin/env python3
"""Export a frozen data snapshot from the running server for the static (artifact) build.
Usage: python3 scripts/export_snapshot.py OUT_DIR   (server must be running on BASE, default http://localhost:8765)
Writes OUT_DIR/data/snapshot.json and OUT_DIR/data/d/NN.json (full per-stock analyses, chunked)."""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("BASE", "http://localhost:8765")
OUT = sys.argv[1]
CHUNK = 24
os.makedirs(os.path.join(OUT, "data", "d"), exist_ok=True)
get = lambda p: json.load(urllib.request.urlopen(BASE + p, timeout=180))

meta = get("/api/meta")
uni = get("/api/universe?mos=0.2&extra=STM")
sl = get("/api/shortlist?mos=0.2")
tickers = [r["ticker"] for r in uni["rows"]] + [r["ticker"] for r in uni["extra_rows"]]
SHARED = ("principles", "confidence_rules", "label_boundaries")

def one(t):
    try:
        d = get(f"/api/stock/{t}?mos=0.2")
        for k in SHARED:
            d.pop(k, None)
        return t, d
    except Exception as e:  # noqa: BLE001
        return t, None

with ThreadPoolExecutor(6) as ex:
    details = dict(ex.map(one, tickers))
first = next(d for d in details.values() if d)
shared = {k: get(f"/api/stock/{tickers[0]}?mos=0.2")[k] for k in SHARED}
index, missing = {}, [t for t, d in details.items() if not d]
ok = [t for t in tickers if details.get(t)]
for n in range(0, len(ok), CHUNK):
    name = f"d/{n // CHUNK:02d}.json"
    part = {t: details[t] for t in ok[n:n + CHUNK]}
    with open(os.path.join(OUT, "data", name), "w") as f:
        json.dump(part, f, separators=(",", ":"))
    for t in part:
        index[t] = name
extras = {}
for t in [r["ticker"] for r in sl["qualifying"]] + ["STM", "JPM", "O", "AAPL"]:
    try:
        extras[t] = get(f"/api/extra/{t}")
    except Exception:  # noqa: BLE001
        pass
snap = {"generated_at": time.time(), "generated_at_et": sl["as_of"], "meta": meta, "universe": uni,
        "shortlist_static": {k: sl[k] for k in ("as_of", "ranking_explanation", "membership", "session", "jobs")},
        "detail_index": index, "shared": shared, "extras": extras}
with open(os.path.join(OUT, "data", "snapshot.json"), "w") as f:
    json.dump(snap, f, separators=(",", ":"))
print(f"snapshot {sl['as_of']}: {len(ok)} analyses in {len(set(index.values()))} chunks; missing {missing}; extras {list(extras)}")
