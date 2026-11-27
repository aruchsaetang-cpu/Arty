"""S&P 500 membership. Official S&P DJI constituents file wins; otherwise a clearly-labelled secondary source.

The S&P DJI website sits behind bot protection, so the official list is supplied as an uploaded/placed file
(data/sp500_official.xlsx|csv). Nothing here ever claims verification it did not perform."""
from __future__ import annotations

import io
import re
import time
from pathlib import Path

import pandas as pd
import requests

from .config import DATA_DIR, SOURCES
from .store import store

OFFICIAL_CANDIDATES = [DATA_DIR / "sp500_official.xlsx", DATA_DIR / "sp500_official.csv"]


def to_yahoo_symbol(sym: str) -> str:
    return str(sym).strip().upper().replace(".", "-")


def _from_official(path: Path) -> dict:
    if path.suffix.lower() == ".csv":
        raw = pd.read_csv(path)
    else:
        raw = pd.read_excel(path, header=None)
        # S&P DJI downloads have title rows above the header; find the header row
        for i in range(min(15, len(raw))):
            vals = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
            if any(v in ("ticker", "symbol", "constituent symbol") for v in vals):
                raw.columns = [str(v).strip() for v in raw.iloc[i].tolist()]
                raw = raw.iloc[i + 1:]
                break
    cols = {str(c).strip().lower(): c for c in raw.columns}
    sym = next((cols[k] for k in ("ticker", "symbol", "constituent symbol") if k in cols), None)
    name = next((cols[k] for k in ("company", "name", "constituent name", "security") if k in cols), None)
    sec = next((cols[k] for k in ("gics sector", "sector") if k in cols), None)
    if sym is None:
        raise ValueError("Official file has no Ticker/Symbol column")
    members = []
    for _, r in raw.dropna(subset=[sym]).iterrows():
        s = str(r[sym]).strip()
        if not s or s.lower() == "nan":
            continue
        members.append({"ticker": to_yahoo_symbol(s), "listed_symbol": s,
                        "name": str(r[name]).strip() if name else None, "sector": str(r[sec]).strip() if sec else None})
    return {"members": members, "source": "spdji", "verified": True,
            "label": f"Official S&P DJI constituents file ({path.name})",
            "url": SOURCES["spdji"]["url"], "as_of": time.strftime("%Y-%m-%d", time.gmtime(path.stat().st_mtime)),
            "note": "File modified date used as 'as of' date; confirm the date printed inside the S&P file."}


def _from_wikipedia() -> dict:
    r = requests.get(SOURCES["wikipedia"]["url"], timeout=30,
                     headers={"User-Agent": "stock-research-dashboard/1.0 (personal research tool)"})
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    t = tables[0]
    if "Symbol" not in t.columns:
        raise ValueError("Unexpected Wikipedia table layout")
    members = [{"ticker": to_yahoo_symbol(row["Symbol"]), "listed_symbol": str(row["Symbol"]).strip(),
                "name": row.get("Security"), "sector": row.get("GICS Sector")} for _, row in t.iterrows()]
    return {"members": members, "source": "wikipedia", "verified": False,
            "label": "Wikipedia 'List of S&P 500 companies' - UNOFFICIAL secondary source, not verified against S&P DJI",
            "url": SOURCES["wikipedia"]["url"], "as_of": time.strftime("%Y-%m-%d", time.gmtime()),
            "note": "Fetched today; Wikipedia can lag index changes. Supply the official S&P DJI file to verify."}


def load_membership(refresh=False) -> dict:
    st = store()
    for p in OFFICIAL_CANDIDATES:
        if p.exists():
            cached, t = st.get("membership")
            if cached and cached.get("source") == "spdji" and t and t >= p.stat().st_mtime and not refresh:
                return cached
            m = _from_official(p)
            st.set("membership", m)
            return m
    cached, t = st.get("membership")
    if cached and not refresh and time.time() - t < 24 * 3600:
        return cached
    try:
        m = _from_wikipedia()
        st.set("membership", m)
        return m
    except Exception as e:  # noqa: BLE001
        if cached:
            cached["stale_error"] = f"Refresh failed ({type(e).__name__}); showing last good list"
            return cached
        raise


def import_official(content: bytes, filename: str) -> dict:
    ext = ".csv" if filename.lower().endswith(".csv") else ".xlsx"
    p = DATA_DIR / f"sp500_official{ext}"
    for other in OFFICIAL_CANDIDATES:
        if other.exists() and other != p:
            other.unlink()
    p.write_bytes(content)
    m = _from_official(p)
    if not 480 <= len({x["ticker"] for x in m["members"]}) <= 520:
        p.unlink()
        raise ValueError(f"File has {len(m['members'])} constituents; an S&P 500 file should hold ~500-505 securities")
    store().set("membership", m)
    return m
