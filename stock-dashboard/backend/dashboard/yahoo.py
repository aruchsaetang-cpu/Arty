"""All Yahoo Finance access (via yfinance). Every function returns plain JSON-able data and raises on failure;
callers keep the last good value + timestamp when a refresh fails."""
from __future__ import annotations

import math
import time

import pandas as pd
import yfinance as yf

from . import market

INFO_KEYS = [
    "longName", "shortName", "symbol", "quoteType", "exchange", "fullExchangeName", "exchangeTimezoneName", "currency",
    "financialCurrency", "sector", "industry", "beta", "sharesOutstanding", "impliedSharesOutstanding", "marketCap",
    "trailingEps", "forwardEps", "trailingPE", "forwardPE", "bookValue", "priceToBook", "dividendRate", "dividendYield",
    "trailingAnnualDividendRate", "revenueGrowth", "earningsGrowth", "longBusinessSummary", "website", "country",
    "regularMarketPrice", "regularMarketPreviousClose", "regularMarketTime", "regularMarketChange",
    "regularMarketChangePercent", "regularMarketDayHigh", "regularMarketDayLow", "regularMarketVolume",
    "marketState", "preMarketPrice", "preMarketTime", "postMarketPrice", "postMarketTime",
    "exchangeDataDelayedBy", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "averageDailyVolume3Month",
    "lastFiscalYearEnd", "mostRecentQuarter", "underlyingSymbol",
]


def retry(fn, tries=3, base=1.5):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(base * (2 ** i))
    raise last


def _num(x):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def fetch_info(ticker: str) -> dict:
    info = retry(lambda: yf.Ticker(ticker).info) or {}
    out = {k: info.get(k) for k in INFO_KEYS if info.get(k) is not None}
    if "regularMarketPrice" not in out and "currentPrice" in info:
        out["regularMarketPrice"] = info["currentPrice"]
    if not out.get("regularMarketPrice") and not out.get("longName"):
        raise ValueError(f"Yahoo returned no data for {ticker}")
    out["_fetched_at"] = time.time()
    return out


def _frame_to_dict(df: pd.DataFrame | None) -> dict:
    """{yahoo_label: {'YYYY-MM-DD': float | None}} - None = missing, 0.0 = reported zero."""
    out: dict = {}
    if df is None or df.empty:
        return out
    for label, row in df.iterrows():
        vals = {}
        for col, v in row.items():
            vals[str(pd.Timestamp(col).date())] = _num(v)
        if any(v is not None for v in vals.values()):
            out[str(label)] = vals
    return out


def fetch_statements(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    inc = retry(lambda: t.get_income_stmt(freq="yearly", pretty=True))
    bal = retry(lambda: t.get_balance_sheet(freq="yearly", pretty=True))
    cf = retry(lambda: t.get_cashflow(freq="yearly", pretty=True))
    res = {"income": _frame_to_dict(inc), "balance": _frame_to_dict(bal), "cashflow": _frame_to_dict(cf),
           "fetched_at": time.time(), "source": "Yahoo Finance via yfinance (annual)"}
    if not res["income"] and not res["balance"] and not res["cashflow"]:
        raise ValueError(f"No annual statements returned for {ticker}")
    return res


def fetch_ttm_and_estimates(ticker: str) -> dict:
    """Trailing-twelve-month statements and forward analyst estimates (detail page only)."""
    t = yf.Ticker(ticker)
    out: dict = {"fetched_at": time.time()}
    for name, fn in (("ttm_income", lambda: t.get_income_stmt(freq="trailing", pretty=True)),
                     ("ttm_cashflow", lambda: t.get_cashflow(freq="trailing", pretty=True))):
        try:
            out[name] = _frame_to_dict(fn())
        except Exception as e:  # noqa: BLE001
            out[name] = {}
            out.setdefault("errors", []).append(f"{name}: {type(e).__name__}")
    for name, attr in (("earnings_estimate", "earnings_estimate"), ("revenue_estimate", "revenue_estimate")):
        try:
            df = getattr(t, attr)
            out[name] = ({} if df is None or df.empty else
                         {str(i): {c: _num(v) for c, v in r.items()} for i, r in df.iterrows()})
        except Exception as e:  # noqa: BLE001
            out[name] = {}
            out.setdefault("errors", []).append(f"{name}: {type(e).__name__}")
    return out


def fetch_news(ticker: str, limit=8) -> list[dict]:
    items = retry(lambda: yf.Ticker(ticker).news) or []
    res = []
    for it in items[:limit]:
        c = it.get("content", it)
        link = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") or it.get("link")
        res.append({"title": c.get("title"), "publisher": (c.get("provider") or {}).get("displayName") or it.get("publisher"),
                    "published": c.get("pubDate") or it.get("providerPublishTime"), "url": link})
    return [r for r in res if r["title"]]


def quote_from_info(info: dict) -> dict:
    """Normalize Yahoo's quote fields. 'Real-time' only if Yahoo reports a zero exchange delay."""
    price = _num(info.get("regularMarketPrice"))
    prev = _num(info.get("regularMarketPreviousClose"))
    rtime = info.get("regularMarketTime")
    delay = info.get("exchangeDataDelayedBy")
    state = info.get("marketState")
    chg = _num(info.get("regularMarketChange"))
    pct = _num(info.get("regularMarketChangePercent"))
    if price is not None and prev:
        chg = price - prev
        pct = chg / prev * 100
    if delay == 0:
        label = "Real-time"
    elif delay:
        label = f"Delayed {int(delay)} min"
    else:
        label = "Latest available"

    def ext(px_key, t_key):
        px = _num(info.get(px_key))
        if px is None or price is None:
            return None
        return {"price": px, "time_et": market.fmt_ny(info.get(t_key)) if info.get(t_key) else None,
                "change_vs_regular_close": px - price, "pct_vs_regular_close": (px - price) / price * 100}

    fresh = market.freshness(int(rtime) if rtime else None, None, delay)
    return {
        "price": price, "previous_close": prev, "change": chg, "change_pct": pct,
        "regular_time_epoch": int(rtime) if rtime else None, "regular_time_et": market.fmt_ny(int(rtime)) if rtime else None,
        "currency": info.get("currency"), "market_state": state, "delay_minutes": delay, "price_label": label,
        "pre_market": ext("preMarketPrice", "preMarketTime"), "post_market": ext("postMarketPrice", "postMarketTime"),
        "freshness": {k: v for k, v in fresh.items() if k != "session"}, "session": fresh["session"],
        "fetched_at": time.time(), "source": "Yahoo Finance via yfinance",
    }


def fetch_quote(ticker: str) -> dict:
    return quote_from_info(fetch_info(ticker))


def fetch_bars(tickers: list[str]) -> dict:
    """Batch daily bars -> {ticker: {last_date, last_close, prev_close, currency?}} for the wider universe."""
    df = retry(lambda: yf.download(tickers, period="10d", interval="1d", auto_adjust=False, group_by="ticker",
                                   threads=True, progress=False))
    res = {}
    for tk in tickers:
        try:
            sub = df[tk] if len(tickers) > 1 else df
            closes = sub["Close"].dropna()
            if closes.empty:
                continue
            res[tk] = {"last_date": str(closes.index[-1].date()), "price": float(closes.iloc[-1]),
                       "previous_close": float(closes.iloc[-2]) if len(closes) > 1 else None,
                       "fetched_at": time.time(), "source": "Yahoo Finance daily bars"}
        except Exception:  # noqa: BLE001
            continue
    return res


def fetch_risk_free() -> dict:
    """10-year US Treasury yield from Yahoo (^TNX, quoted in percent)."""
    h = retry(lambda: yf.Ticker("^TNX").history(period="5d"))
    v = float(h["Close"].dropna().iloc[-1])
    if not 0.2 <= v <= 20:
        raise ValueError(f"Implausible ^TNX value {v}")
    return {"rate": v / 100, "as_of": str(h.index[-1].date()), "source": "Yahoo Finance ^TNX", "fetched_at": time.time()}


def fetch_fx(from_ccy: str, to_ccy: str) -> dict:
    if from_ccy == to_ccy:
        return {"rate": 1.0, "pair": None}
    pair = f"{from_ccy}{to_ccy}=X"
    h = retry(lambda: yf.Ticker(pair).history(period="5d"))
    return {"rate": float(h["Close"].dropna().iloc[-1]), "pair": pair, "as_of": str(h.index[-1].date()),
            "source": "Yahoo Finance FX", "fetched_at": time.time()}
