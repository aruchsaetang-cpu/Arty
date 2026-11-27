"""Service layer: cached Yahoo data with last-good preservation, assessments, detail payloads, universe rows."""
from __future__ import annotations

import threading
import time

from . import assess as A
from . import config as C
from . import fundamentals as F
from . import market, membership, yahoo
from . import valuation as V
from .store import store

_locks: dict[str, threading.Lock] = {}
_glock = threading.Lock()


def lock_for(key: str) -> threading.Lock:
    with _glock:
        return _locks.setdefault(key, threading.Lock())


def norm_ticker(t: str) -> str:
    return t.strip().upper().replace(".", "-")


# ------------------------------------------------------------------ cached fetchers (never lose last-good data)
def risk_free() -> dict:
    s = store()
    cur, t = s.get("rf")
    if cur and time.time() - t < 6 * 3600:
        return cur
    try:
        new = yahoo.fetch_risk_free()
        s.set("rf", new)
        return new
    except Exception as e:  # noqa: BLE001
        if cur:
            cur["stale_error"] = f"{type(e).__name__}; using last good value"
            return cur
        return {"rate": 0.045, "as_of": None, "source": "FALLBACK constant 4.5% (Yahoo ^TNX unavailable)", "fallback": True}


def fx(from_ccy, to_ccy):
    s, key = store(), f"fx:{from_ccy}{to_ccy}"
    cur, t = s.get(key)
    if cur and time.time() - t < 6 * 3600:
        return cur
    try:
        new = yahoo.fetch_fx(from_ccy, to_ccy)
        s.set(key, new)
        return new
    except Exception:  # noqa: BLE001
        return cur


def load_info(t: str, max_age=None, allow_fetch=True):
    s = store()
    cur, ts = s.get(f"info:{t}")
    if cur and (max_age is None or time.time() - ts < max_age):
        return cur
    if not allow_fetch:
        return cur
    try:
        new = yahoo.fetch_info(t)
        s.set(f"info:{t}", new)
        save_quote_from_info(t, new)
        return new
    except Exception:
        if cur:
            return cur
        raise


def load_statements(t: str, max_age=C.FUNDAMENTALS_TTL_HOURS * 3600, allow_fetch=True):
    s = store()
    cur, ts = s.get(f"fund:{t}")
    if cur and (max_age is None or time.time() - ts < max_age):
        return cur
    if not allow_fetch:
        return cur
    try:
        new = yahoo.fetch_statements(t)
        s.set(f"fund:{t}", new)
        return new
    except Exception:
        if cur:
            return cur
        raise


def save_quote_from_info(t, info):
    q = yahoo.quote_from_info(info)
    q["raw_time"] = info.get("regularMarketTime")
    store().set(f"quote:{t}", {k: v for k, v in q.items() if k not in ("freshness", "session")})
    return q


def load_quote(t: str, force=False, allow_fetch=True) -> dict | None:
    """Return the latest quote with freshness recomputed against NOW (freshness is never cached)."""
    s = store()
    cur, ts = s.get(f"quote:{t}")
    if force or (cur is None and allow_fetch):
        try:
            info = yahoo.fetch_info(t)
            s.set(f"info:{t}", info)
            save_quote_from_info(t, info)
            cur, ts = s.get(f"quote:{t}")
        except Exception as e:  # noqa: BLE001
            if cur:
                cur = dict(cur)
                cur["refresh_error"] = f"{type(e).__name__}: refresh failed; showing last successful quote"
            elif force:
                raise
    if not cur:
        return None
    cur = dict(cur)
    if cur.get("regular_time_epoch"):
        fr = market.freshness(cur["regular_time_epoch"], None, cur.get("delay_minutes"))
    else:
        fr = market.freshness(None, cur.get("last_date"), None)
    cur["freshness"] = {k: v for k, v in fr.items() if k != "session"}
    cur["session"] = fr["session"]
    cur["stored_at"] = ts
    cur["stored_at_et"] = market.fmt_ny(ts)
    if cur.get("source", "").startswith("Yahoo Finance daily bars"):
        cur["price_label"] = "Latest available (daily bar)"
        cur["regular_time_et"] = cur.get("last_date")
    return cur


# ------------------------------------------------------------------ imports
def load_import(t):
    return store().val(f"import:{t}")


def raw_for_conflicts(t):
    st_ = load_statements(t, max_age=None, allow_fetch=False) or {}
    return {k: st_.get(k, {}) for k in ("income", "balance", "cashflow")}


# ------------------------------------------------------------------ assessment
def build_assessment(t: str, info=None, statements=None, persist=True):
    info = info or load_info(t, max_age=None, allow_fetch=False)
    statements = statements or load_statements(t, max_age=None, allow_fetch=False)
    if not info or not statements:
        return None
    rf = risk_free()["rate"]
    fxr, pair = None, None
    fc, qc = info.get("financialCurrency"), info.get("currency")
    if fc and qc and fc != qc:
        r = fx(fc, qc)
        if r:
            fxr, pair = r["rate"], r.get("pair")
    a = A.assess(t, info, statements, load_import(t), rf, fxr, pair)
    a["rf"] = rf
    a["data_as_of"] = {"statements_fetched_at": statements.get("fetched_at"), "info_fetched_at": info.get("_fetched_at")}
    if persist:
        s = store()
        s.set(f"assess:{t}", a)
        v = a.get("valuation", {})
        q = a["quality"]
        s.set(f"summ:{t}", {
            "ticker": t, "name": a["name"], "sector": a.get("sector"), "industry": a.get("industry"), "kind": a["kind"],
            "quality": q["label"], "quality_score": q.get("score"), "years": a.get("years"),
            "confidence": v.get("confidence", {}).get("level", "insufficient"),
            "usable": bool(v.get("usable")), "fv_bear": (v.get("scenarios") or {}).get("bear", {}).get("fair_value"),
            "fv_base": (v.get("scenarios") or {}).get("base", {}).get("fair_value"),
            "fv_bull": (v.get("scenarios") or {}).get("bull", {}).get("fair_value"),
            "pillars": [{"key": p["key"], "status": p["status"], "summary": p["summary"], "name": p["name"]} for p in q.get("pillars", [])],
            "spread": v.get("spread"), "blockers": v.get("blockers", []), "currency": v.get("currency") or info.get("currency"),
            "midcycle_flag": bool(v.get("midcycle")), "model_version": C.MODEL_VERSION, "assessed_at": a["assessed_at"]})
        s.delete(f"fail:{t}")
    return a


def analyze(t: str, force=False):
    """Fetch (if needed) and assess one ticker; failure keeps last-good assessment."""
    t = norm_ticker(t)
    with lock_for(t):
        try:
            info = load_info(t, max_age=(0 if force else 24 * 3600))
            stm = load_statements(t, max_age=(0 if force else C.FUNDAMENTALS_TTL_HOURS * 3600))
            a = build_assessment(t, info, stm)
            if a is None:
                raise ValueError("no data")
            return a
        except Exception as e:  # noqa: BLE001
            store().set(f"fail:{t}", {"error": f"{type(e).__name__}: {e}"[:300], "at": time.time()})
            cur = store().val(f"assess:{t}")
            if cur:
                return cur
            raise


def get_assessment(t: str, allow_fetch=True):
    a = store().val(f"assess:{t}")
    if a and a.get("model_version") == C.MODEL_VERSION:
        return a
    if a is None and not allow_fetch:
        return None
    return analyze(t) if allow_fetch else a


# ------------------------------------------------------------------ rows for lists
def row_for(t: str, meta: dict | None, mos: float) -> dict:
    s = store()
    summ = s.val(f"summ:{t}")
    q = load_quote(t, allow_fetch=False)
    fail = s.val(f"fail:{t}")
    row = {"ticker": t, "name": (meta or {}).get("name") or (summ or {}).get("name") or t,
           "sector": (summ or {}).get("sector") or (meta or {}).get("sector"), "in_index": bool(meta)}
    if not summ:
        row.update(status="failed_fetch" if fail else "awaiting", status_detail=(fail or {}).get("error"), quality=None, confidence=None,
                   valuation_label=None, price=q["price"] if q else None, quote_status=(q or {}).get("freshness", {}).get("status"),
                   qualifies=False, missed=[], margin_of_safety=None)
        return row
    a_like = {"quality": {"label": summ["quality"], "score": summ["quality_score"], "pillars": summ["pillars"], "reason": None},
              "valuation": {"usable": summ["usable"], "confidence": {"level": summ["confidence"]},
                            "scenarios": {k: {"fair_value": summ[f"fv_{k}"]} for k in ("bear", "base", "bull")}}}
    pv = A.price_view(a_like, q, mos)
    status = ("qualified" if pv["qualifies"] else "assessed_failed_rule" if summ["usable"] else "assessed_no_valuation")
    row.update(
        status=status, kind=summ["kind"], industry=summ["industry"], quality=summ["quality"], quality_score=summ["quality_score"],
        years=summ["years"], confidence=summ["confidence"], usable=summ["usable"], currency=summ["currency"],
        price=pv["price"], price_time=(q or {}).get("regular_time_et"), quote_status=pv["freshness"]["status"],
        quote_reason=pv["freshness"].get("reason"), fv_bear=pv["fv_bear"], fv_base=pv["fv_base"], fv_bull=pv["fv_bull"],
        margin_of_safety=pv["margin_of_safety"], upside=pv["upside"], watch_price=pv["watch_price"],
        decline_to_watch=pv["decline_to_watch"], bear_discount=pv["bear_discount"], valuation_label=pv["valuation_label"],
        qualifies=pv["qualifies"], missed=pv["missed"], rules=pv["rules"], blockers=summ["blockers"],
        weakest=min(summ["pillars"], key=lambda p: {"pass": 2, "partial": 1, "fail": 0}[p["status"]])["summary"] if summ["pillars"] else None,
        _rank=A.rank_key(pv), _pillars=summ["pillars"])
    if pv["qualifies"]:
        # specific reason and biggest risk from the cached assessment
        a = s.val(f"assess:{t}")
        if a:
            row["reason"], row["risk"] = A.reason_and_risk(a, pv)
    return row


def universe_rows(mos: float) -> tuple[list[dict], dict]:
    m = membership.load_membership()
    rows = [row_for(x["ticker"], x, mos) for x in m["members"]]
    return rows, m


def coverage(rows: list[dict]) -> dict:
    n = len(rows)
    assessed = [r for r in rows if r["status"] not in ("awaiting", "failed_fetch")]
    return {"universe": n, "assessed": len(assessed), "usable_valuation": sum(1 for r in assessed if r.get("usable")),
            "qualifying": sum(1 for r in rows if r["qualifies"]), "awaiting": sum(1 for r in rows if r["status"] == "awaiting"),
            "failed_fetch": sum(1 for r in rows if r["status"] == "failed_fetch"),
            "failed_rule": sum(1 for r in rows if r["status"] == "assessed_failed_rule"),
            "no_valuation": sum(1 for r in rows if r["status"] == "assessed_no_valuation"),
            "stale_quotes": sum(1 for r in assessed if r.get("quote_status") == "stale"),
            "with_quote": sum(1 for r in rows if r.get("price") is not None)}


RANK_EXPLANATION = ("Qualifying stocks are ordered by (1) valuation confidence: High, then Medium; (2) the discount of the latest regular-session price to "
                    "the BEAR-case fair value (larger discount first; a bear value of zero or below ranks last); (3) the business-quality score. "
                    "Ownership has no effect on rank.")


def shortlist(mos: float) -> dict:
    rows, m = universe_rows(mos)
    qual = sorted((r for r in rows if r["qualifies"]), key=lambda r: r["_rank"])
    closest = sorted((r for r in rows if r.get("usable") and not r["qualifies"] and r["quote_status"] != "stale" or
                      (r.get("usable") and not r["qualifies"])), key=lambda r: (len(r["missed"]), -(r["margin_of_safety"] or -9)))
    cov = coverage(rows)
    stm = row_for("STM", None, mos)
    return {"as_of": market.fmt_ny(time.time()), "as_of_epoch": time.time(), "coverage": cov, "required_mos": mos,
            "ranking_explanation": RANK_EXPLANATION, "qualifying": [_strip(r) for r in qual[:10]], "qualifying_total": len(qual),
            "closest": [_strip(r) for r in closest[:10]], "stm": _strip(stm), "membership": _mem_meta(m),
            "session": market.session_state(), "jobs": store().val("jobs:status", {})}


def _strip(r):
    return {k: v for k, v in r.items() if not k.startswith("_")}


def _mem_meta(m):
    return {k: m.get(k) for k in ("source", "verified", "label", "url", "as_of", "note", "stale_error")} | {"count": len(m["members"])}
