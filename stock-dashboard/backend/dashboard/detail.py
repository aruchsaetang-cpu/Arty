"""Stock-detail payload: 10-year tables, growth maths, perspectives, narrative, sources."""
from __future__ import annotations

import time

from . import assess as A
from . import config as C
from . import fundamentals as F
from . import market, quality as Q, service, yahoo
from . import valuation as V
from .store import store

SPEC_ROWS = {
    "income": [("revenue", "Revenue", "money"), ("cogs", "Cost of revenue", "money"), ("gross_profit", "Gross profit", "money"),
               ("rnd", "R&D", "money"), ("op_income", "Operating income", "money"), ("net_income", "Net income", "money"),
               ("eps", "Diluted EPS", "pershare"), ("shares", "Diluted average shares", "shares"),
               ("gross_margin", "Gross margin", "pct"), ("op_margin", "Operating margin", "pct"), ("net_margin", "Net margin", "pct")],
    "balance": [("cash", "Cash & short-term investments", "money"), ("receivables", "Receivables", "money"), ("inventory", "Inventory", "money"),
                ("cur_assets", "Current assets", "money"), ("assets", "Total assets", "money"), ("cur_liab", "Current liabilities", "money"),
                ("liab", "Total liabilities", "money"), ("debt", "Total debt", "money"), ("equity", "Stockholders' equity", "money"),
                ("working_capital", "Working capital", "money"), ("current_ratio", "Current ratio", "ratio"),
                ("debt_to_equity", "Debt-to-equity", "ratio")],
    "cashflow": [("ocf", "Operating cash flow", "money"), ("capex_abs", "Capital expenditure (spend, shown positive; deducted once)", "money"),
                 ("fcf", "Free cash flow (OCF - capex)", "money"), ("fcf_yahoo", "Free cash flow as reported by Yahoo", "money"),
                 ("fcf_ps", "Free cash flow per diluted share", "pershare"), ("shares", "Diluted average shares", "shares"),
                 ("owner_earnings_proxy", "Owner-earnings proxy (NI + D&A - total capex)", "money")],
}
MARGIN_ROWS = {"gross_margin", "op_margin", "net_margin"}
CAGR_ROWS = {"revenue", "gross_profit", "op_income", "net_income", "eps", "fcf", "fcf_ps", "equity", "shares"}


def _row(key, label, kind, d, cols, prov_keys):
    vals = d[key]
    r = {"key": key, "label": label, "kind": kind, "values": vals}
    if kind == "pct":
        r["pp"] = [None if i == 0 else F.pp_change(vals[i - 1], vals[i]) for i in range(len(vals))]
    elif kind in ("money", "pershare", "shares"):
        r["yoy"] = F.yoy(vals, cols)
        pts = [(c["end"], v) for c, v in zip(cols, vals) if v is not None and c["end"]]
        if key in CAGR_ROWS and len(pts) > 1:
            g, why = F.cagr(pts[0][1], pts[-1][1], pts[0][0], pts[-1][0])
            r["cagr"] = {"value": g, "reason": why, "from": pts[0][0], "to": pts[-1][0],
                         "years": round(F.years_between(pts[0][0], pts[-1][0]), 2)}
    return r


def tables(merged, canon, cols, d, info):
    out = {}
    for st, rows in SPEC_ROWS.items():
        out[st] = {"spec": [_row(k, l, kd, d, cols, None) for k, l, kd in rows]}
        det = []
        for lab, vals in merged["statements"].get(st, {}).items():
            det.append({"label": lab, "values": [vals.get(c["end"]) if c["end"] else None for c in cols],
                        "imported": [bool(c["end"] and merged["prov"].get((st, lab, c["end"]))) for c in cols]})
        out[st]["detail"] = det
        have = [i for i, c in enumerate(cols) if c["end"] and any(r["values"][i] is not None for r in out[st]["spec"] if r["kind"] == "money")]
        out[st]["coverage"] = {"years_with_data": len(have), "first": cols[have[0]]["label"] if have else None,
                               "last": cols[have[-1]]["label"] if have else None, "slots": F.SLOTS}
    return out


def build(t: str, mos: float, quote_force=False) -> dict:
    t = service.norm_ticker(t)
    a = service.get_assessment(t)
    info = store().val(f"info:{t}") or {}
    statements = store().val(f"fund:{t}")
    quote = service.load_quote(t, force=quote_force)
    merged, canon, cols, d = A.build_tables(info, statements, service.load_import(t))
    kind = a["kind"]
    if kind == "reit":
        Q._q_reit(d, cols, info)
    pv = A.price_view(a, quote, mos)
    reason, risk = A.reason_and_risk(a, pv) if a["valuation"].get("usable") and pv["price"] else (None, None)
    price = pv["price"]
    members = {m["ticker"]: m for m in __import__("dashboard.membership", fromlist=["x"]).load_membership()["members"]}
    meta = members.get(t)
    li = A.last_idx(cols)
    detail = {
        "ticker": t, "name": a["name"], "sector": a.get("sector"), "industry": a.get("industry"), "kind": kind,
        "in_sp500_list": bool(meta), "membership": service._mem_meta(__import__("dashboard.membership", fromlist=["x"]).load_membership()),
        "exchange": info.get("fullExchangeName"), "country": info.get("country"), "website": info.get("website"),
        "summary": (info.get("longBusinessSummary") or "")[:700], "basis": {
            "quote_currency": info.get("currency"), "reporting_currency": info.get("financialCurrency"),
            "share_class_note": "Quote and per-share values refer to this exact listed line; share count used: " + str(a["valuation"].get("share_basis")),
            "adr_note": ("This line is an ADR/ADS - ratio unverified" if A.ADR_PATTERN.search(a["name"] or "") else "Not an ADR/ADS line (ordinary share)."),
            "units": f"Statement values in {info.get('financialCurrency') or 'reporting currency'}, full units (UI shows millions)"},
        "quote": quote, "price_view": pv, "quality": a["quality"], "valuation": a["valuation"], "required_mos": mos,
        "label_boundaries": V.label_boundaries(), "reverse": A.reverse(a, price) if price else None,
        "columns": cols, "tables": tables(merged, canon, cols, d, info), "latest_fy": cols[li]["label"],
        "graham": Q.graham(kind, d, cols, price, info), "lynch": Q.lynch(kind, d, cols, price, info),
        "narrative": A.thesis(a, pv), "reason": reason, "risk": risk,
        "ratios": buffett_ratios(kind, d, cols, info, price, a.get("rf")), "ceo": ceo_block(t, info),
        "pe_yahoo": info.get("trailingPE"), "employees": info.get("fullTimeEmployees"),
        "imports": (service.load_import(t) or {}).get("files", []), "has_import": a.get("has_import"),
        "sources": {
            "quote": {"label": "Yahoo Finance quote", "url": f"https://finance.yahoo.com/quote/{t}", "fetched": market.fmt_ny((quote or {}).get("stored_at")), "type": "reported (market data)"},
            "income": {"label": "Yahoo Finance - Income statement (annual)", "url": f"https://finance.yahoo.com/quote/{t}/financials/", "type": "reported",
                       "fetched": market.fmt_ny((statements or {}).get("fetched_at"))},
            "balance": {"label": "Yahoo Finance - Balance sheet (annual)", "url": f"https://finance.yahoo.com/quote/{t}/balance-sheet/", "type": "reported",
                        "fetched": market.fmt_ny((statements or {}).get("fetched_at"))},
            "cashflow": {"label": "Yahoo Finance - Cash flow (annual)", "url": f"https://finance.yahoo.com/quote/{t}/cash-flow/", "type": "reported",
                         "fetched": market.fmt_ny((statements or {}).get("fetched_at"))},
            "estimates": {"label": "Yahoo Finance - Analysis (analyst estimates)", "url": f"https://finance.yahoo.com/quote/{t}/analysis/", "type": "analyst estimates"},
            "news": {"label": "Yahoo Finance - Company news", "url": f"https://finance.yahoo.com/quote/{t}/news/", "type": "news"},
            "model": {"label": "Dashboard model (Buffett-inspired model assessment)", "type": "model assumptions", "version": C.MODEL_VERSION},
        },
        "data_kinds": "Reported = Yahoo statements. Analyst estimates = Yahoo consensus (shown separately, never used in the ranking). Model assumptions = this dashboard.",
        "valuation_date": market.fmt_ny(a["assessed_at"]), "price_timestamp": (quote or {}).get("regular_time_et"),
        "principles": C.PRINCIPLES, "confidence_rules": V.CONFIDENCE_RULES,
        "limits": ([f"Yahoo supplied {a['years']} fiscal years; the 10-year view keeps all 10 columns with N/A gaps. "
                    "Import older annual CSVs to extend history."] if a["years"] < F.SLOTS else []),
    }
    return detail


def trailing_and_estimates(t: str) -> dict:
    s = store()
    cur, ts = s.get(f"ttm:{t}")
    if cur and time.time() - ts < 6 * 3600:
        return cur
    try:
        new = yahoo.fetch_ttm_and_estimates(t)
        s.set(f"ttm:{t}", new)
        return new
    except Exception as e:  # noqa: BLE001
        if cur:
            cur["stale_error"] = f"{type(e).__name__}; showing last good data"
            return cur
        return {"error": f"{type(e).__name__}", "ttm_income": {}, "ttm_cashflow": {}, "earnings_estimate": {}, "revenue_estimate": {}}


def news(t: str):
    s = store()
    cur, ts = s.get(f"news:{t}")
    if cur and time.time() - ts < 900:
        return {"items": cur, "fetched_at": market.fmt_ny(ts)}
    try:
        new = yahoo.fetch_news(t)
        s.set(f"news:{t}", new)
        return {"items": new, "fetched_at": market.fmt_ny(time.time())}
    except Exception as e:  # noqa: BLE001
        return {"items": cur or [], "fetched_at": market.fmt_ny(ts) if ts else None, "error": f"{type(e).__name__}: news refresh failed"}


# ------------------------------------------------------------------ Buffett-benchmark ratio table + CEO
import json as _json
import os as _os

BOOK = "Mary Buffett & David Clark, Warren Buffett and the Interpretation of Financial Statements (2008)"
BOOK_URL = "https://en.wikipedia.org/wiki/Mary_Buffett"
L1979 = "https://www.berkshirehathaway.com/letters/1979.html"
L2007 = "https://www.berkshirehathaway.com/letters/2007ltr.pdf"
OWN = "https://www.berkshirehathaway.com/owners.html"
_PROFILES = None


def profiles():
    global _PROFILES
    if _PROFILES is None:
        with open(_os.path.join(_os.path.dirname(__file__), "ceo_profiles.json")) as f:
            _PROFILES = _json.load(f)
    return _PROFILES


def _avg_ratio(num, den, cols):
    """Per-year num / average(den_t, den_{t-1}); first year uses the year-end value."""
    out, prev = [], None
    for i, c in enumerate(cols):
        n, dd = num[i], den[i]
        if c["end"] and n is not None and dd:
            base = (dd + prev) / 2 if prev else dd
            out.append((c["label"], n / base if base else None))
        if dd:
            prev = dd
    return [(fy, v) for fy, v in out if v is not None]


def buffett_ratios(kind, d, cols, info, price, rf):
    yrs = lambda key: [(c["label"], d[key][i]) for i, c in enumerate(cols) if c["end"] and d[key][i] is not None]
    rows = []

    def add(key, name, formula, series, target_txt, test, basis, url, unit="pct", latest=None, status=None):
        vals = [v for _, v in series]
        lt = latest if latest is not None else (series[-1][1] if series else None)
        st = status or ("n/a" if not vals else "pass" if test(vals, lt) else "fail")
        rows.append({"key": key, "name": name, "formula": formula, "latest": lt, "latest_fy": series[-1][0] if series else None,
                     "avg": (sum(vals) / len(vals)) if vals else None, "years": len(vals), "target": target_txt, "status": st,
                     "basis": basis, "url": url, "unit": unit})
    every = lambda th: (lambda v, lt: all(x >= th for x in v))
    fin = kind == "financial"
    add("gross_margin", "Gross margin", "Gross profit / revenue", yrs("gross_margin"), "≥ 40% every year", every(.40), BOOK, BOOK_URL)
    add("op_margin", "Operating margin", "Operating income / revenue", yrs("op_margin"), "≥ 20% every year", every(.20),
        "Dashboard assumption (follows the 40% gross-margin rule)", BOOK_URL)
    add("net_margin", "Net margin", "Net income / revenue", yrs("net_margin"), "≥ 20% every year", every(.20), BOOK, BOOK_URL)
    roa_th = .01 if fin else .10
    add("roa", "Return on assets", "Net income / avg total assets", _avg_ratio(d["net_income"], d["assets"], cols),
        f"≥ {roa_th:.0%} every year", every(roa_th), "Dashboard assumption (Buffett judges returns on capital, 2007 letter)", L2007)
    add("roe", "Return on equity", "Net income / avg equity", _avg_ratio(d["ni_common"], d["equity"], cols), "≥ 15% every year", every(.15),
        "Buffett: ROE is the primary test (1979 letter); 15% threshold is a dashboard assumption", L1979)
    de = yrs("debt_to_equity")
    add("debt_equity", "Debt / equity", "Total debt / equity", de, "≤ 0.80", lambda v, lt: lt <= .80, BOOK, BOOK_URL, unit="x",
        status="n/a" if fin else None)
    eps = yrs("eps")
    rising = all(b > a for (_, a), (_, b) in zip(eps, eps[1:])) and len(eps) > 1 and all(v > 0 for _, v in eps)
    add("eps", "EPS (diluted)", "(Net income − pref. dividends) / shares", eps, "Rising every year", lambda v, lt: rising, BOOK, BOOK_URL,
        unit="money", status=None if eps else "n/a")
    dps = info.get("trailingAnnualDividendRate")
    dy = (dps / price) if (dps is not None and price) else None
    rows.append({"key": "div_yield", "name": "Dividend yield", "formula": "Dividends per share / price", "latest": dy, "latest_fy": "TTM",
                 "avg": None, "years": None, "target": "No target", "status": "info", "unit": "pct",
                 "basis": "Buffett prefers retained earnings when each $1 kept creates ≥ $1 of value (Owner's Manual)", "url": OWN})
    last_eps = eps[-1][1] if eps else None
    pe = price / last_eps if (price and last_eps and last_eps > 0) else None
    rows.append({"key": "pe", "name": "P/E", "formula": "Price / latest FY EPS", "latest": pe, "latest_fy": eps[-1][0] if eps else None,
                 "avg": None, "years": None, "target": f"Earnings yield ≥ 10y Treasury ({rf:.1%}) → P/E ≤ {1/rf:.0f}" if rf else "n/a",
                 "status": "n/a" if pe is None or not rf else ("pass" if 1 / pe >= rf else "fail"), "unit": "x",
                 "basis": "Dashboard assumption (earnings yield vs bond yield)", "url": OWN, "yahoo_trailing_pe": info.get("trailingPE")})
    return rows


def ceo_block(t, info):
    ceos = info.get("ceos") or []
    prof = profiles().get(t)
    return {"officers": ceos, "profile": prof, "listed": bool(ceos), "profiles_note": profiles().get("_about")}


def ceo_news(t):
    s = store()
    cur, ts = s.get(f"ceonews:{t}")
    if cur is not None and time.time() - ts < 3600:
        return {"items": cur, "fetched_at": market.fmt_ny(ts)}
    info = s.val(f"info:{t}") or {}
    ceos = info.get("ceos") or []
    if not ceos:
        return {"items": [], "fetched_at": None}
    raw = (info.get("shortName") or info.get("longName") or t).split(",")[0]
    company = " ".join(w for w in raw.replace(".", " ").split() if w.lower() not in ("inc", "corp", "corporation", "nv", "plc", "ltd", "co", "company", "group", "holdings", "athletica")) or t
    clean = lambda n: " ".join(w for w in n.split() if len(w.rstrip(".")) > 1)  # drop middle initials
    prof = profiles().get(t)
    if prof:
        names = [n.split("(")[0].strip() for n in prof["name"].split("&")]
    else:
        names = [clean(c["name"]) for c in ceos[:2]]
    try:
        items = []
        for n in names[:2]:
            got = yahoo.fetch_ceo_news(n, "")
            items += got if got else yahoo.fetch_ceo_news(n, company)
        seen, uniq = set(), []
        for it in items:
            if it["url"] not in seen:
                seen.add(it["url"]); uniq.append(it)
        s.set(f"ceonews:{t}", uniq)
        return {"items": uniq, "fetched_at": market.fmt_ny(time.time())}
    except Exception as e:  # noqa: BLE001
        return {"items": cur or [], "fetched_at": market.fmt_ny(ts) if ts else None, "error": f"{type(e).__name__}"}
