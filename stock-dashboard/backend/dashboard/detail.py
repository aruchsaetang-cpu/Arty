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
