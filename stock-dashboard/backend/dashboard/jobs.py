"""Background refresh, independent of any UI session: membership, universe quotes (rate-limited batches),
annual statements (separately, long TTL), reassessment when the risk-free rate / model / imports change."""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import config as C
from . import market, membership, service, yahoo
from .store import store

_state = {"quotes": {"running": False}, "fundamentals": {"running": False}}
_stop = threading.Event()


def _status():
    store().set("jobs:status", {k: dict(v) for k, v in _state.items()})


def _tick(job, **kw):
    _state[job].update(kw)
    _status()


def refresh_quotes(tickers=None):
    if _state["quotes"]["running"]:
        return
    m = membership.load_membership()
    tickers = tickers or [x["ticker"] for x in m["members"]]
    _tick("quotes", running=True, started=time.time(), total=len(tickers), done=0, failed=0, error=None)
    s = store()
    try:
        for i in range(0, len(tickers), 100):
            chunk = tickers[i:i + 100]
            try:
                bars = yahoo.fetch_bars(chunk)
            except Exception as e:  # noqa: BLE001
                _state["quotes"]["failed"] += len(chunk)
                _state["quotes"]["error"] = f"{type(e).__name__} (kept last good quotes)"
                time.sleep(C.BATCH_PAUSE_SEC * 3)
                continue
            for tk, b in bars.items():
                cur = s.val(f"quote:{tk}")
                # keep a richer info-based quote if it is newer than this daily-bar quote
                if cur and cur.get("regular_time_epoch") and cur.get("price_date") == b["last_date"]:
                    continue
                s.set(f"quote:{tk}", {"price": b["price"], "previous_close": b["previous_close"], "change": (b["price"] - b["previous_close"]) if b["previous_close"] else None,
                                      "change_pct": ((b["price"] / b["previous_close"] - 1) * 100) if b["previous_close"] else None, "last_date": b["last_date"],
                                      "price_date": b["last_date"], "currency": None, "market_state": None, "delay_minutes": None,
                                      "source": b["source"], "fetched_at": b["fetched_at"]})
            _state["quotes"]["done"] += len(chunk)
            _status()
            time.sleep(C.BATCH_PAUSE_SEC)
    finally:
        _tick("quotes", running=False, finished=time.time())
        s.set("jobs:quotes_last", time.time())


def _needs_fundamentals(t, now):
    s = store()
    _, ts = s.get(f"fund:{t}")
    fail = s.val(f"fail:{t}")
    if ts is None:
        return not (fail and now - fail["at"] < 3600)  # back off an hour after a failure
    return now - ts > C.FUNDAMENTALS_TTL_HOURS * 3600


def refresh_fundamentals(tickers=None, force=False):
    if _state["fundamentals"]["running"]:
        return
    m = membership.load_membership()
    now = time.time()
    all_t = tickers or [x["ticker"] for x in m["members"]]
    todo = [t for t in all_t if force or _needs_fundamentals(t, now)]
    _tick("fundamentals", running=True, started=now, total=len(todo), done=0, failed=0, error=None, universe=len(all_t))
    try:
        for i in range(0, len(todo), C.BATCH_SIZE):
            if _stop.is_set():
                break
            chunk = todo[i:i + C.BATCH_SIZE]

            def work(t):
                try:
                    service.analyze(t, force=True)
                    return True
                except Exception:  # noqa: BLE001
                    return False
            with ThreadPoolExecutor(C.WORKERS) as ex:
                res = list(ex.map(work, chunk))
            _state["fundamentals"]["done"] += sum(res)
            _state["fundamentals"]["failed"] += len(res) - sum(res)
            _status()
            time.sleep(C.BATCH_PAUSE_SEC)
    finally:
        _tick("fundamentals", running=False, finished=time.time())


def reassess_cached(tickers=None):
    """Recompute assessments from cached raw data (no network): after rf / model-version / import changes."""
    s = store()
    n = 0
    for t in tickers or [k[5:] for k in s.keys("fund:")]:
        a = s.val(f"assess:{t}")
        if a is None or a.get("model_version") != C.MODEL_VERSION or abs((a.get("rf") or 0) - service.risk_free()["rate"]) > 0.0025:
            try:
                service.build_assessment(t)
                n += 1
            except Exception:  # noqa: BLE001
                pass
    return n


def loop():
    time.sleep(2)
    while not _stop.is_set():
        try:
            membership.load_membership()
            reassess_cached()
            st = market.session_state()
            ttl = (C.UNIVERSE_QUOTE_TTL_MIN_OPEN if st["phase"] == "OPEN" else C.UNIVERSE_QUOTE_TTL_MIN_CLOSED) * 60
            last = store().val("jobs:quotes_last", 0)
            if time.time() - last > ttl:
                refresh_quotes()
            refresh_fundamentals()
        except Exception as e:  # noqa: BLE001
            _state["fundamentals"]["error"] = f"{type(e).__name__}: {e}"[:200]
        _stop.wait(60)


def start():
    th = threading.Thread(target=loop, name="refresher", daemon=True)
    th.start()
    return th


def status():
    return {k: dict(v) for k, v in _state.items()}
