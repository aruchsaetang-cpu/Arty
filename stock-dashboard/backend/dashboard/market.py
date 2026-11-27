"""NYSE session logic: weekends, holidays, early closes, last completed regular session, quote freshness."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import pandas as pd

from .config import OPEN_SESSION_STALE_EXTRA_MIN, QUOTE_GRACE_MIN_AFTER_CLOSE, TZ_NY


@lru_cache(maxsize=1)
def _cal():
    import exchange_calendars as xc
    return xc.get_calendar("XNYS")


def now_utc() -> pd.Timestamp:
    return pd.Timestamp.now(tz="UTC")


def ny(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert(TZ_NY)


def fmt_ny(epoch_or_ts) -> str | None:
    if epoch_or_ts is None:
        return None
    ts = pd.Timestamp(epoch_or_ts, unit="s", tz="UTC") if isinstance(epoch_or_ts, (int, float)) else ny(epoch_or_ts)
    return ny(ts).strftime("%Y-%m-%d %H:%M:%S ET")


def session_state(now: pd.Timestamp | None = None) -> dict:
    """Exchange state at `now`, derived from the calendar (not from any quote)."""
    cal = _cal()
    now = now_utc() if now is None else pd.Timestamp(now)
    today = ny(now).normalize().tz_localize(None)
    is_session = bool(cal.is_session(today))
    state = {"now_et": fmt_ny(now), "today": str(today.date()), "is_trading_day": is_session}
    if is_session:
        o, c = cal.session_open(today), cal.session_close(today)
        state.update(open_et=fmt_ny(o), close_et=fmt_ny(c),
                     early_close=bool(c.tz_convert(TZ_NY).hour < 16))
        if now < o:
            phase = "PRE_OPEN"
        elif now < c:
            phase = "OPEN"
        else:
            phase = "CLOSED_AFTER_SESSION"
        last_done = today if now >= c else cal.previous_session(today)
    else:
        phase = "CLOSED_NON_TRADING_DAY"
        last_done = cal.date_to_session(today, direction="previous")
        reason = "weekend" if today.weekday() >= 5 else "exchange holiday"
        state["closed_reason"] = reason
    last_close = cal.session_close(last_done)
    nxt = cal.date_to_session(today + pd.Timedelta(days=0 if (is_session and now < cal.session_close(today)) else 1),
                              direction="next")
    state.update(phase=phase, last_completed_session=str(pd.Timestamp(last_done).date()),
                 last_completed_close_et=fmt_ny(last_close), last_completed_close_epoch=int(last_close.timestamp()),
                 next_session=str(pd.Timestamp(nxt).date()))
    return state


def freshness(regular_time_epoch: int | None, last_bar_date: str | None, delayed_by_min: int | None,
              now: pd.Timestamp | None = None) -> dict:
    """Decide whether a regular-session quote is current for the trading session.

    status: current | delayed (current but flagged) | stale
    Exclusion rule: a newer completed regular session than the quote's -> stale.
    """
    now = now_utc() if now is None else pd.Timestamp(now)
    st = session_state(now)
    last_done = st["last_completed_session"]
    if regular_time_epoch is None and last_bar_date is None:
        return {"status": "stale", "reason": "No regular-session quote timestamp available", "session": st}
    if regular_time_epoch is not None:
        q_ts = pd.Timestamp(regular_time_epoch, unit="s", tz="UTC")
        q_date = str(ny(q_ts).date())
    else:
        q_ts, q_date = None, last_bar_date
    delay = delayed_by_min or 0
    if st["phase"] == "OPEN":
        today = st["today"]
        if q_ts is not None:
            age = (now - q_ts).total_seconds() / 60
            if q_date == today and age <= delay + OPEN_SESSION_STALE_EXTRA_MIN:
                status = "delayed" if delay > 0 else "current"
                return {"status": status, "reason": (f"Intraday quote delayed ~{delay} min" if delay else "Intraday quote"),
                        "intraday": True, "session": st}
        # no intraday print yet today: latest bar must at least be the last completed session
        if q_date == today:
            return {"status": "delayed", "reason": "Intraday print is older than the exchange delay; treat as latest available",
                    "intraday": True, "session": st}
        prior_close_ok = (q_ts is None) or q_ts.timestamp() >= st["last_completed_close_epoch"] - QUOTE_GRACE_MIN_AFTER_CLOSE * 60
        if q_date == last_done and prior_close_ok:
            return {"status": "delayed", "reason": "Session is open; only the prior completed close is available",
                    "intraday": True, "session": st}
        return {"status": "stale", "reason": f"Quote from {q_date}; newer completed session {last_done} is missing", "session": st}
    # market closed
    if q_ts is not None:
        ok = q_ts.timestamp() >= st["last_completed_close_epoch"] - QUOTE_GRACE_MIN_AFTER_CLOSE * 60
        if ok:
            return {"status": "current", "reason": f"Official close of completed session {last_done}", "session": st}
        return {"status": "stale", "reason": f"Quote from {q_date}; newer completed session {last_done} is missing",
                "session": st}
    if q_date >= last_done:
        return {"status": "current", "reason": f"Daily bar for completed session {last_done}", "session": st}
    return {"status": "stale", "reason": f"Latest daily bar {q_date}; newer completed session {last_done} is missing",
            "session": st}
