import pandas as pd
from dashboard import market as M

NY = "America/New_York"
def ts(s): return pd.Timestamp(s, tz=NY)


def test_weekend_and_holiday():
    s = M.session_state(ts("2026-11-28 12:00"))
    assert s["phase"] == "CLOSED_NON_TRADING_DAY" and s["closed_reason"] == "weekend" and s["last_completed_session"] == "2026-11-27"
    s = M.session_state(ts("2026-11-26 12:00"))   # Thanksgiving
    assert s["closed_reason"] == "exchange holiday" and s["last_completed_session"] == "2026-11-25"
    s = M.session_state(ts("2026-12-25 12:00"))
    assert s["closed_reason"] == "exchange holiday" and s["last_completed_session"] == "2026-12-24"


def test_early_close_day_after_thanksgiving():
    s = M.session_state(ts("2026-11-27 13:30"))
    assert s["early_close"] and s["phase"] == "CLOSED_AFTER_SESSION" and s["last_completed_session"] == "2026-11-27"
    assert M.session_state(ts("2026-11-27 12:00"))["phase"] == "OPEN"


def test_stale_when_newer_completed_session_missing():
    now = ts("2026-11-30 08:00")                      # Monday pre-open; last completed = Fri 11-27 (early close 13:00)
    fri_close = int(ts("2026-11-27 13:00").timestamp())
    wed_close = int(ts("2026-11-25 16:00").timestamp())
    assert M.freshness(fri_close, None, 20, now)["status"] == "current"
    f = M.freshness(wed_close, None, 20, now)
    assert f["status"] == "stale" and "2026-11-27" in f["reason"]
    assert M.freshness(None, "2026-11-25", None, now)["status"] == "stale"
    assert M.freshness(None, "2026-11-27", None, now)["status"] == "current"


def test_weekend_quote_from_friday_is_current():
    now = ts("2026-11-28 10:00")
    assert M.freshness(int(ts("2026-11-27 13:00").timestamp()), None, 20, now)["status"] == "current"


def test_intraday_is_flagged_delayed():
    now = ts("2026-12-01 11:00")
    q = int(ts("2026-12-01 10:45").timestamp())
    f = M.freshness(q, None, 20, now)
    assert f["status"] == "delayed" and f["intraday"]
    # open session but quote hours old -> stale
    assert M.freshness(int(ts("2026-12-01 09:31").timestamp()) - 3600 * 20, None, 20, now)["status"] == "stale"
