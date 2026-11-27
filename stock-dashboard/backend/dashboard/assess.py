"""Orchestration: fundamentals -> quality -> valuation (standard scenarios, price-independent) and
price_view (price-dependent: margin of safety, labels, rules, reverse DCF, narrative)."""
from __future__ import annotations

import re
import statistics as st
import time

from . import config as C
from . import fundamentals as F
from . import quality as Q
from . import valuation as V

CLASS_BASIS_UNVERIFIED = {"BRK-A", "BRK-B"}
ADR_PATTERN = re.compile(r"\bADR\b|\bADS\b|depositary", re.I)

ASSUMPTION_SPECS = {
    "operating": [
        {"key": "g1", "label": "Year-1 revenue growth", "unit": "pct", "min": -0.10, "max": 0.30, "step": 0.005},
        {"key": "g_term", "label": "Terminal growth", "unit": "pct", "min": 0.0, "max": 0.04, "step": 0.0025},
        {"key": "margin_target", "label": "Normalized operating margin", "unit": "pct", "min": 0.0, "max": 0.60, "step": 0.005},
        {"key": "ramp_years", "label": "Years to reach that margin", "unit": "years", "min": 0, "max": 10, "step": 1},
        {"key": "capex_target", "label": "Steady-state capex (% revenue)", "unit": "pct", "min": 0.0, "max": 0.50, "step": 0.005},
        {"key": "da_pct", "label": "D&A (% revenue)", "unit": "pct", "min": 0.0, "max": 0.40, "step": 0.005},
        {"key": "tax", "label": "Tax rate on operating income", "unit": "pct", "min": 0.0, "max": 0.40, "step": 0.005},
        {"key": "r", "label": "Discount rate", "unit": "pct", "min": 0.05, "max": 0.16, "step": 0.0025},
    ],
    "financial": [
        {"key": "roe", "label": "Sustainable ROE", "unit": "pct", "min": 0.0, "max": 0.30, "step": 0.005},
        {"key": "g", "label": "Long-run growth", "unit": "pct", "min": 0.0, "max": 0.05, "step": 0.0025},
        {"key": "r", "label": "Cost of equity", "unit": "pct", "min": 0.05, "max": 0.16, "step": 0.0025},
    ],
    "reit": [
        {"key": "affo_ps", "label": "AFFO per share (proxy)", "unit": "money", "min": 0.0, "max": None, "step": 0.05},
        {"key": "g", "label": "Long-run AFFO growth", "unit": "pct", "min": 0.0, "max": 0.05, "step": 0.0025},
        {"key": "r", "label": "Discount rate", "unit": "pct", "min": 0.05, "max": 0.16, "step": 0.0025},
    ],
}


def _med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None


def last_idx(cols):
    return max(i for i, c in enumerate(cols) if c["end"])


def build_tables(info, statements, imported):
    merged = F.merged_raw(statements, imported)
    canon = F.canonical(merged["statements"])
    core_dates = sorted({dt for f in ("revenue", "net_income", "ni_common", "assets", "equity", "ocf") for dt in canon[f]})
    all_dates = sorted({dt for st_ in merged["statements"].values() for v in st_.values() for dt in v})
    cols = F.make_columns(all_dates, anchor=core_dates[-1] if core_dates else None)
    d = F.derive(canon, cols)
    return merged, canon, cols, d


def coverage_years(d, cols, kind):
    keys = {"operating": ["revenue", "net_income"], "financial": ["net_income", "equity"], "reit": ["net_income", "assets"]}[kind]
    return sum(1 for i, c in enumerate(cols) if c["end"] and all(d[k][i] is not None for k in keys))


# ------------------------------------------------------------------ parameter construction
def op_history(d, cols, info, shares_used, fx):
    li = last_idx(cols)
    opm = [v for v in d["op_margin"] if v is not None]
    cxp = [v for v in d["capex_pct_rev"] if v is not None]
    dap = [abs(v) for v in d["da_pct_rev"] if v is not None]
    rev = [(c["end"], d["revenue"][i]) for i, c in enumerate(cols) if c["end"] and d["revenue"][i]]
    g_hist, g_why = (None, "too few years")
    if len(rev) > 1:
        g_hist, g_why = F.cagr(rev[0][1], rev[-1][1], rev[0][0], rev[-1][0])
    nwc = []
    for i, c in enumerate(cols):
        if c["end"] and d["revenue"][i] and d["receivables"][i] is not None and d["inventory"][i] is not None and d["payables"][i] is not None:
            nwc.append((d["receivables"][i] + d["inventory"][i] - d["payables"][i]) / d["revenue"][i])
    taxes = [t for t in d["tax_rate"] if t is not None]
    debt = d["debt"][li] or 0.0
    cash = d["cash"][li] or 0.0
    return {"opm": opm, "capex_pct": cxp, "da_pct": dap, "g_hist": g_hist, "g_why": g_why,
            "nwc_pct": min(max(_med(nwc) or 0.0, 0.0), 0.35), "nwc_known": bool(nwc),
            "tax": min(max(_med(taxes) or 0.21, 0.10), 0.30), "revenue0": d["revenue"][li] * fx,
            "margin_last": d["op_margin"][li], "capex_last": d["capex_pct_rev"][li],
            "net_debt": (debt - cash) * fx, "shares": shares_used, "li": li}


def op_params(h, r_base, scenario):
    m_norm = V.shrunk_norm(h["opm"])
    m_min, m_max = min(h["opm"]), max(h["opm"])
    cx_med, da_med = _med(h["capex_pct"]) or 0.0, _med(h["da_pct"]) or 0.0
    g_base = V.clip(h["g_hist"] if h["g_hist"] is not None else 0.03, 0.02, 0.10)
    cx_last = h["capex_last"] if h["capex_last"] is not None else cx_med
    if scenario == "bear":
        g1 = max(g_base - 0.03, -0.02)
        mt = m_norm - 0.5 * (m_norm - m_min)
        ramp, cxt, cxr = 5, max(cx_med, cx_last), 5
        r, gt = r_base + 0.01, C.TERMINAL_GROWTH["bear"]
    elif scenario == "bull":
        g1 = min(g_base + 0.04, 0.15)
        mt = m_norm + 0.5 * (max(m_max, m_norm) - m_norm)
        ramp, cxt, cxr = 2, (da_med * 1.05 if cx_med > da_med else cx_med * 0.95), 2
        r, gt = r_base - 0.005, C.TERMINAL_GROWTH["bull"]
    else:
        g1, mt = g_base, m_norm
        ramp, cxr = 3, 3
        cxt = (cx_med + da_med) / 2 if cx_med > da_med else cx_med
        r, gt = r_base, C.TERMINAL_GROWTH["base"]
    return {"revenue0": h["revenue0"], "g1": g1, "g_term": gt, "margin_start": h["margin_last"], "margin_target": mt,
            "ramp_years": ramp, "tax": h["tax"], "capex_start": cx_last, "capex_target": cxt, "capex_ramp_years": cxr,
            "da_pct": da_med, "nwc_pct": h["nwc_pct"], "r": r, "net_debt": h["net_debt"], "shares": h["shares"]}


def fin_history(d, cols, shares_used, fx):
    li = last_idx(cols)
    roe = [v for *_, v in Q.roe_series(d, cols)]
    eps = [v for v in d["eps"] if v is not None]
    bvps = (d["equity"][li] * fx) / shares_used if d["equity"][li] and shares_used else None
    return {"roe": roe, "eps": [e * fx for e in eps], "bvps": bvps, "li": li}


def fin_params(h, r_base, scenario):
    roe_n = V.clip(V.shrunk_norm(h["roe"]), 0.0, 0.25)
    rmin, rmax = min(h["roe"]), max(h["roe"])
    if scenario == "bear":
        roe, r, g = roe_n - 0.5 * (roe_n - min(rmin, roe_n)), r_base + 0.01, C.TERMINAL_GROWTH["bear"]
    elif scenario == "bull":
        roe, r, g = min(roe_n + 0.5 * (max(rmax, roe_n) - roe_n), 0.25), r_base - 0.005, C.TERMINAL_GROWTH["bull"]
    else:
        roe, r, g = roe_n, r_base, C.TERMINAL_GROWTH["base"]
    return {"bvps": h["bvps"], "roe": max(roe, 0.0), "g": g, "r": r, "eps_norm": V.shrunk_norm(h["eps"])}


def reit_history(d, cols, fx):
    ffo_ps = [v for v in d["ffo_ps"] if v is not None]
    dps = None
    li = last_idx(cols)
    if d["dividends"][li] is not None and d["shares"][li]:
        dps = abs(d["dividends"][li]) / d["shares"][li] * fx
    return {"affo_ps_hist": [v * 0.9 * fx for v in ffo_ps], "dps": dps, "li": li}


def reit_params(h, r_base, scenario):
    a = V.shrunk_norm(h["affo_ps_hist"])
    g = {"bear": 0.01, "base": 0.02, "bull": 0.03}[scenario]
    r = r_base + (0.01 if scenario == "bear" else -0.005 if scenario == "bull" else 0)
    return {"affo_ps": a, "g": g, "r": r, "dps": h["dps"]}


# ------------------------------------------------------------------ main assessment
def assess(ticker, info, statements, imported, rf, fx_rate=None, fx_pair=None):
    t0 = time.time()
    merged, canon, cols, d = build_tables(info, statements, imported)
    kind = Q.classify(info)
    out = {"ticker": ticker, "kind": kind, "model_version": C.MODEL_VERSION, "assessed_at": t0,
           "name": info.get("longName") or info.get("shortName") or ticker, "sector": info.get("sector"), "industry": info.get("industry"),
           "quote_currency": info.get("currency"), "financial_currency": info.get("financialCurrency"),
           "has_import": bool(imported and imported.get("statements"))}
    if not cols or not any(c["end"] for c in cols):
        out.update(quality={"label": "Insufficient evidence", "score": None, "pillars": [], "reason": "no annual statements", "kind": kind,
                            "years": 0, "rule_text": Q.LABEL_RULE, "pillar_rules": [], "moat": {"supports": [], "weakens": [], "caveat": Q.MOAT_CAVEAT}},
                   valuation={"usable": False, "blockers": ["No annual statements from Yahoo"], "confidence": V.confidence(0, 0, 0, False, ["No annual statements"])},
                   years=0)
        return out
    years = coverage_years(d, cols, kind)
    qual = Q.assess_quality(kind, d, cols, info)
    out["years"] = years
    out["quality"] = qual
    out["fiscal_years"] = [c["label"] for c in cols if c["end"]]
    out["latest_fy_end"] = cols[last_idx(cols)]["end"]
    out["valuation"] = value_company(kind, d, cols, info, rf, years, fx_rate, fx_pair)
    out["d_summary"] = {"revenue": d["revenue"], "op_margin": d["op_margin"], "fcf": d["fcf"], "eps": d["eps"]}
    return out


def value_company(kind, d, cols, info, rf, years, fx_rate, fx_pair):
    blockers: list[str] = []
    notes: list[str] = []
    fin_ccy, q_ccy = info.get("financialCurrency"), info.get("currency")
    fx = 1.0
    if fin_ccy and q_ccy and fin_ccy != q_ccy:
        if fx_rate:
            fx = fx_rate
            notes.append(f"Statements are in {fin_ccy}; per-share values converted to {q_ccy} at {fx:.4f} ({fx_pair}).")
        else:
            blockers.append(f"Reporting currency {fin_ccy} differs from quote currency {q_ccy} and no FX rate was available")
    if not fin_ccy:
        notes.append("Yahoo did not state the reporting currency; assumed equal to the quote currency.")
    if info.get("symbol") in CLASS_BASIS_UNVERIFIED or info.get("underlyingSymbol") in CLASS_BASIS_UNVERIFIED:
        blockers.append("Share classes have different economic claims (A vs B); Yahoo's per-share basis could not be verified")
    if ADR_PATTERN.search(info.get("longName") or ""):
        blockers.append("Security looks like an ADR/ADS and the ADR-to-ordinary ratio is not available from Yahoo")
    li = last_idx(cols)
    fy_sh = d["shares"][li]
    info_sh = info.get("impliedSharesOutstanding") or info.get("sharesOutstanding")
    shares_used, share_basis = None, None
    if info_sh and fy_sh:
        ratio = info_sh / fy_sh
        if 0.8 <= ratio <= 1.25:
            shares_used, share_basis = info_sh, f"Yahoo shares outstanding ({info_sh/1e6:,.0f}M)"
        elif 0.5 <= ratio <= 2:
            shares_used, share_basis = fy_sh, f"FY diluted average shares ({fy_sh/1e6:,.0f}M); Yahoo's outstanding count differs by {ratio-1:+.0%}"
            notes.append(share_basis)
        else:
            blockers.append(f"Share count basis mismatch: Yahoo outstanding {info_sh/1e6:,.0f}M vs diluted average {fy_sh/1e6:,.0f}M (share class / ADR basis?)")
    elif fy_sh or info_sh:
        shares_used = fy_sh or info_sh
        share_basis = "single share-count source"
    else:
        blockers.append("No share count available")
    if years < C.MIN_YEARS_FOR_ASSESSMENT:
        blockers.append(f"Only {years} fiscal years of data (need {C.MIN_YEARS_FOR_ASSESSMENT}); import older Yahoo CSVs to extend")
    r_base = V.discount_rate(rf, info.get("beta"))
    base_info = {"rf": rf, "beta": info.get("beta"), "r": r_base, "currency": q_ccy, "shares_used": shares_used, "share_basis": share_basis,
                 "fx_rate": fx if fx != 1.0 else None, "notes": notes}
    res = {"usable": False, "kind": kind, "blockers": blockers, **base_info, "assumption_spec": ASSUMPTION_SPECS[kind]}
    if blockers:
        res["confidence"] = V.confidence(years, 0, 1, False, blockers)
        return res
    try:
        if kind == "operating":
            res.update(_value_operating(d, cols, info, shares_used, fx, r_base, years))
        elif kind == "financial":
            res.update(_value_financial(d, cols, shares_used, fx, r_base, years))
        else:
            Q._q_reit(d, cols, info)  # ensures ffo/ffo_ps are populated on d
            res.update(_value_reit(d, cols, shares_used, fx, r_base, years))
    except (ValueError, TypeError, ZeroDivisionError, KeyError) as e:
        res["blockers"] = [f"Valuation inputs incomplete ({type(e).__name__}: {e})"]
        res["confidence"] = V.confidence(years, 0, 1, False, res["blockers"])
        return res
    base_fv = res["scenarios"]["base"]["fair_value"]
    if base_fv is None or base_fv <= 0:
        res["blockers"] = [f"Base-case model value is not positive ({base_fv:.2f}): normalized margins/returns are zero or negative once anchored toward the "
                           f"weakest of the {years} fiscal years available (a loss year or one-off charge, or capex above cash earnings), so this method is unsuitable"
                           if base_fv is not None else "No base value"]
        res["confidence"] = V.confidence(years, 0, 1, False, res["blockers"])
        res["usable"] = False
        return res
    res["usable"] = True
    return res


def _sens(fn, base_params, r, xkey, xs, xfmt):
    rs = [r - 0.02, r - 0.01, r, r + 0.01, r + 0.02]

    def call(rr, x):
        p = dict(base_params)
        p["r"], p[xkey] = rr, x
        try:
            return fn(p)
        except ZeroDivisionError:
            return None
    return {"rows": rs, "cols": xs, "col_key": xkey, "values": V.grid(call, rs, xs), "base_r": r}


def _spread(sens, base_fv):
    vals = [sens["values"][i][j] for i in (1, 2, 3) for j in (1, 2, 3) if sens["values"][i][j] is not None]
    return (max(vals) - min(vals)) / base_fv if (vals and base_fv > 0) else 9.9


def _value_operating(d, cols, info, shares, fx, r_base, years):
    h = op_history(d, cols, info, shares, fx)
    if len(h["opm"]) < 3 or h["margin_last"] is None or not h["revenue0"]:
        raise ValueError("operating margin history too short")
    scen = {}
    params = {}
    for s in ("bear", "base", "bull"):
        p = op_params(h, r_base, s)
        params[s] = p
        out = V.dcf_operating(p)
        scen[s] = {"fair_value": out["per_share"], "params": _describe_op(p), "terminal_share_of_ev": out["terminal_share_of_ev"],
                   "projection": out["rows"] if s == "base" else None}
    pb = params["base"]
    epv = V.epv_operating(pb)
    primary = scen["base"]["fair_value"]
    agree = primary > 0 and epv > 0 and abs(epv - primary) / primary <= 0.35
    disagreement = None
    if not agree:
        share_tv = scen["base"]["terminal_share_of_ev"]
        disagreement = (f"The 10-year cash-flow model gives {primary:.2f} but earnings-power value (no growth, maintenance capex = D&A) gives {epv:.2f}. "
                        f"{abs(1-epv/primary):.0%} gap: the cash-flow model counts growth and a margin path ({share_tv:.0%} of its enterprise value is terminal), "
                        "while EPV pays for today's normalized earnings only. Treat the lower value as the floor and the higher as contingent on growth.")
    sens = _sens(lambda p: V.dcf_operating(p)["per_share"], pb, pb["r"], "g1",
                 [pb["g1"] + x for x in (-0.04, -0.02, 0, 0.02, 0.04)], "pct")
    fcf_pos = [v for v in d["fcf"] if v is not None]
    oi_pos = [v for v in d["op_income"] if v is not None]
    good = sum(1 for a in fcf_pos if a > 0) / len(fcf_pos) if fcf_pos else 0
    suit = 2 if (good >= .99 and all(v > 0 for v in oi_pos)) else 1 if good >= .6 else 0
    spread = _spread(sens, primary) if primary > 0 else 9.9
    conf = V.confidence(years, suit, spread, agree, [])
    hist = {"revenue_cagr": h["g_hist"], "revenue_cagr_note": h["g_why"], "op_margin_history": h["opm"], "median_op_margin": _med(h["opm"]),
            "normalized_op_margin": V.shrunk_norm(h["opm"]), "min_op_margin": min(h["opm"]), "max_op_margin": max(h["opm"]),
            "nwc_assumption_known": h["nwc_known"]}
    mid = midcycle(d, cols, h, params, shares, fx, info)
    return {"method": "10-year free-cash-flow-to-firm DCF with fading growth (normalized margins)",
            "cross_method": "Earnings power value (no-growth, maintenance capex = D&A)",
            "cross_value": epv, "agree": agree, "disagreement": disagreement, "scenarios": scen, "base_params": pb,
            "sensitivity": sens, "spread": spread, "confidence": conf, "history": hist, "midcycle": mid,
            "suitability_points": suit, "owner_earnings_note": OWNER_EARNINGS_NOTE}


OWNER_EARNINGS_NOTE = ("Owner-earnings proxy = net income + D&A - TOTAL capex. Yahoo does not split maintenance from growth capex, so "
                       "this proxy understates owner earnings for companies investing heavily for growth (e.g. fab or data-centre build-outs) "
                       "and overstates them if reported capex is below true maintenance needs.")


def _describe_op(p):
    return [{"label": "Year-1 revenue growth (fades to terminal over 10 yrs)", "value": p["g1"], "unit": "pct"},
            {"label": "Terminal growth", "value": p["g_term"], "unit": "pct"},
            {"label": "Operating margin: start -> target", "value": [p["margin_start"], p["margin_target"]], "unit": "pct2"},
            {"label": "Years to reach target margin", "value": p["ramp_years"], "unit": "years"},
            {"label": "Capex % revenue: start -> steady state", "value": [p["capex_start"], p["capex_target"]], "unit": "pct2"},
            {"label": "D&A % revenue", "value": p["da_pct"], "unit": "pct"},
            {"label": "Tax rate", "value": p["tax"], "unit": "pct"},
            {"label": "Working capital % of revenue change", "value": p["nwc_pct"], "unit": "pct"},
            {"label": "Discount rate", "value": p["r"], "unit": "pct"}]


def midcycle(d, cols, h, params, shares, fx, info):
    opm = h["opm"]
    rng = max(opm) - min(opm)
    cyclical = rng >= 0.10 or info.get("symbol") == "STM"
    if not cyclical:
        return None
    m_norm = V.shrunk_norm(opm)
    pb = params["base"]
    rows = []
    for i, c in enumerate(cols):
        if c["end"] and d["op_margin"][i] is not None:
            m = d["op_margin"][i]
            rows.append({"fy": c["label"], "end": c["end"], "revenue": d["revenue"][i], "op_margin": m, "eps": d["eps"][i],
                         "position": "peak" if m > m_norm + .05 else "trough" if m < m_norm - .05 else "near mid-cycle",
                         "supports_normalization": True})
    li = h["li"]
    mid_eps = pb["revenue0"] * m_norm * (1 - pb["tax"]) / shares
    scen = {}
    for rname, ramp in (("recover_base", 3), ("recover_slow", 6)):
        for cname, cx in (("capex_base", pb["capex_target"]), ("capex_elevated", max(h["capex_last"] or 0, pb["capex_target"]))):
            p = dict(pb)
            p["ramp_years"], p["capex_target"], p["capex_ramp_years"] = ramp, cx, ramp
            scen[f"{rname}|{cname}"] = V.dcf_operating(p)["per_share"]
    return {"reported_eps_latest": d["eps"][li], "reported_op_margin_latest": h["margin_last"], "normalized_op_margin": m_norm,
            "midcycle_eps_estimate": mid_eps, "years": rows, "range_pp": rng * 100,
            "window_note": (f"Normalization uses the only {len(opm)} fiscal years Yahoo provides ({rows[0]['fy']}-{rows[-1]['fy']}). "
                            "Because fewer than 8 years cannot cover a full cycle, the normalized margin is shrunk halfway toward the weakest year."),
            "grid": scen, "grid_note": "Fair value per share if margins recover over 3 vs 6 years, and if capex converges to the base steady state vs stays at the latest FY level."}


def _value_financial(d, cols, shares, fx, r_base, years):
    h = fin_history(d, cols, shares, fx)
    if len(h["roe"]) < 3 or not h["bvps"] or h["bvps"] <= 0:
        raise ValueError("ROE or book value history too short")
    scen, params = {}, {}
    for s in ("bear", "base", "bull"):
        p = fin_params(h, r_base, s)
        params[s] = p
        scen[s] = {"fair_value": V.pb_financial(p), "params": [
            {"label": "Sustainable ROE", "value": p["roe"], "unit": "pct"}, {"label": "Long-run growth", "value": p["g"], "unit": "pct"},
            {"label": "Cost of equity", "value": p["r"], "unit": "pct"}, {"label": "Book value per share", "value": p["bvps"], "unit": "money"},
            {"label": "Implied justified P/B", "value": (p["roe"] - p["g"]) / (p["r"] - p["g"]), "unit": "x"}]}
    pb = params["base"]
    alt = V.payout_ddm_financial(pb)
    primary = scen["base"]["fair_value"]
    agree = primary > 0 and alt > 0 and abs(alt - primary) / primary <= 0.35
    dis = None if agree else (f"Justified price-to-book gives {primary:.2f}; the sustainable-payout earnings model gives {alt:.2f}. They share ROE and growth "
                              "but start from book value vs normalized EPS, so a gap means recent earnings differ from ROE x book value (buybacks, a changing equity base).")
    sens = _sens(V.pb_financial, pb, pb["r"], "roe", [pb["roe"] + x for x in (-0.04, -0.02, 0, 0.02, 0.04)], "pct")
    ni = [v for v in d["ni_common"] if v is not None]
    suit = 2 if (all(v > 0 for v in ni) and h["bvps"] > 0) else 1 if sum(v > 0 for v in ni) / len(ni) >= .75 else 0
    spread = _spread(sens, primary) if primary > 0 else 9.9
    return {"method": "Equity-based: justified price-to-book from ROE, growth and cost of equity (residual income)",
            "cross_method": "Sustainable-payout earnings model (normalized EPS x (1 - g/ROE) x (1+g) / (r - g))", "cross_value": alt,
            "agree": agree, "disagreement": dis, "scenarios": scen, "base_params": pb, "sensitivity": sens, "spread": spread,
            "confidence": V.confidence(years, suit, spread, agree, []), "suitability_points": suit,
            "history": {"roe_history": h["roe"], "median_roe": _med(h["roe"]), "bvps": h["bvps"]}, "midcycle": None,
            "owner_earnings_note": "Free cash flow is not used for banks and insurers: operating cash flow includes deposit, loan and trading balances."}


def _value_reit(d, cols, shares, fx, r_base, years):
    h = reit_history(d, cols, fx)
    if len(h["affo_ps_hist"]) < 3 or not (V.shrunk_norm(h["affo_ps_hist"]) or 0) > 0:
        raise ValueError("FFO history too short or non-positive")
    scen, params = {}, {}
    for s in ("bear", "base", "bull"):
        p = reit_params(h, r_base, s)
        params[s] = p
        scen[s] = {"fair_value": V.affo_reit(p), "params": [
            {"label": "AFFO per share (proxy = 90% of FFO)", "value": p["affo_ps"], "unit": "money"}, {"label": "Long-run growth", "value": p["g"], "unit": "pct"},
            {"label": "Discount rate", "value": p["r"], "unit": "pct"}]}
    pb = params["base"]
    alt = V.ddm_reit(pb)
    primary = scen["base"]["fair_value"]
    agree = bool(alt) and abs(alt - primary) / primary <= 0.35
    dis = None if agree else (f"AFFO-proxy capitalisation gives {primary:.2f}; the dividend-discount cross-check gives "
                              f"{'n/a' if not alt else f'{alt:.2f}'}. A gap means the payout is far from AFFO (retention, or a payout above AFFO).")
    sens = _sens(V.affo_reit, pb, pb["r"], "g", [pb["g"] + x for x in (-0.02, -0.01, 0, 0.01, 0.02)], "pct")
    ffo = [v for v in d["ffo"] if v is not None]
    suit = 2 if all(v > 0 for v in ffo) else 1
    spread = _spread(sens, primary)
    return {"method": "REIT: capitalised AFFO-per-share proxy (FFO = net income + D&A - gains on sale, less 10% recurring-capex haircut)",
            "cross_method": "Dividend-discount model on latest dividends per share", "cross_value": alt, "agree": agree, "disagreement": dis,
            "scenarios": scen, "base_params": pb, "sensitivity": sens, "spread": spread,
            "confidence": V.confidence(years, suit, spread, agree, []), "suitability_points": suit,
            "history": {"affo_ps_history": h["affo_ps_hist"]}, "midcycle": None,
            "owner_earnings_note": ("Reliable AFFO (straight-line rent, maintenance capex, lease costs) is NOT in Yahoo's statements. "
                                    "AFFO here is a proxy: FFO less a 10% recurring-capex haircut that is a model assumption.")}


# ------------------------------------------------------------------ custom (user) scenarios
def custom_valuation(a: dict, overrides: dict, price: float | None, required_mos: float):
    v = a["valuation"]
    if not v.get("usable"):
        raise ValueError("No usable standard valuation to customise")
    kind = v["kind"]
    p = dict(v["base_params"])
    for k, x in overrides.items():
        if k in p and x is not None:
            p[k] = float(x)
    fn = {"operating": lambda q: V.dcf_operating(q)["per_share"], "financial": V.pb_financial, "reit": V.affo_reit}[kind]
    if kind == "operating":
        p["capex_ramp_years"] = p["ramp_years"] if "ramp_years" in overrides else p["capex_ramp_years"]
        if p["r"] <= p["g_term"]:
            raise ValueError("Discount rate must exceed terminal growth")
    elif p["r"] <= p["g"]:
        raise ValueError("Discount rate must exceed growth")
    fv = fn(p)
    xkey = {"operating": "g1", "financial": "roe", "reit": "g"}[kind]
    step = {"operating": 0.02, "financial": 0.02, "reit": 0.01}[kind]
    sens = _sens(fn, p, p["r"], xkey, [p[xkey] + step * k for k in (-2, -1, 0, 1, 2)], "pct")
    return {"fair_value": fv, "params": p, "sensitivity": sens, "is_custom": True,
            "metrics": price_metrics(fv, price, required_mos),
            "label": V.valuation_label(fv, price, "ok"), "standard_base_fair_value": v["scenarios"]["base"]["fair_value"]}


def price_metrics(fv, price, required_mos):
    mos = V.margin_of_safety(fv, price)
    w = V.watch_price(fv, required_mos)
    return {"margin_of_safety": mos, "upside": V.upside_to_fair_value(fv, price), "watch_price": w,
            "decline_to_watch": V.decline_to_watch(price, w), "meets_required_mos": mos is not None and mos >= required_mos}


def reverse(a: dict, price: float):
    v = a["valuation"]
    if not v.get("usable") or not price:
        return None
    kind, p = v["kind"], dict(v["base_params"])
    if kind == "operating":
        def f_g(g):
            q = dict(p); q["g1"] = g
            return V.dcf_operating(q)["per_share"]

        def f_m(m):
            q = dict(p); q["margin_target"] = m; q["margin_start"] = m if p["ramp_years"] == 0 else p["margin_start"]
            return V.dcf_operating(q)["per_share"]
        g_req = V.bisect(f_g, -0.25, 0.60, price)
        m_req = V.bisect(f_m, 0.0, 0.90, price)
        h = v["history"]
        return {"kind": kind, "required_year1_growth": g_req, "required_margin": m_req,
                "history": {"revenue_cagr": h["revenue_cagr"], "median_margin": h["median_op_margin"], "max_margin": h["max_op_margin"],
                            "min_margin": h["min_op_margin"]},
                "text": _reverse_text_op(g_req, m_req, h, p)}
    if kind == "financial":
        roe = p["g"] + (price / p["bvps"]) * (p["r"] - p["g"])
        h = v["history"]
        return {"kind": kind, "required_roe": roe, "history": {"median_roe": h["median_roe"]},
                "text": f"At {price:.2f} the market needs a sustainable ROE of about {roe:.1%} (growth {p['g']:.1%}, cost of equity {p['r']:.1%}); "
                        f"verified history: median ROE {h['median_roe']:.1%}."}
    g = (price * p["r"] - p["affo_ps"]) / (price + p["affo_ps"])
    return {"kind": kind, "required_growth": g,
            "text": f"At {price:.2f} the market needs perpetual AFFO growth of about {g:.1%} (discount rate {p['r']:.1%}, AFFO/share {p['affo_ps']:.2f})."}


def _reverse_text_op(g, m, h, p):
    rc = "n/m" if h["revenue_cagr"] is None else f"{h['revenue_cagr']:.1%}"
    a = (f"Holding the base margin path ({p['margin_target']:.1%}) and discount rate ({p['r']:.1%}), today's price requires "
         + (f"year-1 revenue growth of {g:.1%} (fading to {p['g_term']:.1%})" if g is not None
            else "more year-1 revenue growth than the solver range allows (above 60%)")
         + f"; verified revenue CAGR is {rc}.")
    b = (f" Holding base growth ({p['g1']:.1%}), it requires "
         + (f"a sustained operating margin of {m:.1%}" if m is not None else "a margin above 90%, which is not achievable")
         + f"; verified margins ranged {h['min_op_margin']:.1%} to {h['max_op_margin']:.1%} (median {h['median_op_margin']:.1%}).")
    return a + b


# ------------------------------------------------------------------ price-dependent view + rules
CONF_RANK = {"high": 3, "medium": 2, "low": 1, "insufficient": 0}


def price_view(a: dict, quote: dict | None, required_mos: float) -> dict:
    v = a.get("valuation", {})
    price = quote.get("price") if quote else None
    fresh = (quote or {}).get("freshness") or {"status": "stale", "reason": "No quote available"}
    conf = v.get("confidence", {"level": "insufficient"})["level"]
    out = {"price": price, "freshness": fresh, "usable": bool(v.get("usable")) and price is not None, "confidence": conf,
           "quality_label": a["quality"]["label"], "quality_score": a["quality"].get("score")}
    if v.get("usable") and price:
        sc = v["scenarios"]
        base, bear, bull = (sc[k]["fair_value"] for k in ("base", "bear", "bull"))
        out.update(fv_bear=bear, fv_base=base, fv_bull=bull, **price_metrics(base, price, required_mos),
                   bear_discount=V.margin_of_safety(bear, price))
        out["valuation_label"] = V.valuation_label(base, price, conf)
    else:
        out.update(fv_bear=None, fv_base=None, fv_bull=None, margin_of_safety=None, upside=None, watch_price=None,
                   decline_to_watch=None, bear_discount=None, valuation_label="Insufficient evidence", meets_required_mos=False)
    rules = [
        {"key": "quality", "rule": "Business quality is Strong", "passed": a["quality"]["label"] == "Strong",
         "detail": f"Quality: {a['quality']['label']}" + (f" ({a['quality']['score']}/100)" if a["quality"].get("score") is not None else
                                                       f" - {a['quality'].get('reason')}")},
        {"key": "margin", "rule": f"Price at least {required_mos:.0%} below base fair value (dashboard assumption)",
         "passed": bool(out.get("meets_required_mos")),
         "detail": ("No usable valuation" if out["margin_of_safety"] is None else f"Margin of safety {out['margin_of_safety']:.1%}; needs {required_mos:.0%}")},
        {"key": "confidence", "rule": "Valuation confidence is Medium or High", "passed": conf in ("medium", "high"), "detail": f"Confidence: {conf}"},
        {"key": "quote", "rule": "Quote is current for the trading session", "passed": fresh["status"] in ("current", "delayed"),
         "detail": f"{fresh['status']}: {fresh.get('reason', '')}"},
    ]
    out["rules"] = rules
    out["missed"] = [r["rule"] for r in rules if not r["passed"]]
    out["qualifies"] = not out["missed"]
    return out


def rank_key(pv):
    return (-CONF_RANK[pv["confidence"]], -(pv["bear_discount"] if pv["bear_discount"] is not None else -9), -(pv["quality_score"] or 0))


def reason_and_risk(a, pv):
    """One specific reason it qualifies (from this company's own figures) and its biggest risk."""
    q, v = a["quality"], a.get("valuation", {})
    fig = {p["key"]: p for p in q.get("pillars", [])}
    reason_bits = []
    if "returns" in fig:
        reason_bits.append(fig["returns"]["summary"].rstrip("."))
    if "balance_sheet" in fig and fig["balance_sheet"]["status"] == "pass":
        reason_bits.append(fig["balance_sheet"]["summary"].split(":", 1)[-1].strip().rstrip("."))
    reason = "; ".join(reason_bits[:2])
    if pv.get("margin_of_safety") is not None:
        reason += f". Price is {pv['margin_of_safety']:.0%} below base fair value ({pv['fv_base']:.2f})" if pv["margin_of_safety"] > 0 else ""
    risk = "Model risk: fair value rests on Yahoo's statements and the listed assumptions."
    if v.get("usable"):
        bear = pv.get("fv_bear")
        weakest = sorted((p for p in q.get("pillars", [])), key=lambda p: p["points"])
        if bear is not None and bear <= 0:
            risk = ("In the bear case the model value is zero or negative: capital spending and working capital absorb more cash than "
                    "the thinner margins generate, so equity would have no model value under those assumptions.")
        elif bear is not None and pv["price"] and bear < pv["price"]:
            risk = (f"In the bear case fair value is {bear:.2f}, {1 - bear / pv['price']:.0%} below today's price - "
                    f"the margin of safety depends on margins and growth holding up.")
        elif weakest and weakest[0]["status"] != "pass":
            risk = f"Weakest quality pillar - {weakest[0]['name']}: {weakest[0]['summary']}"
        else:
            sp = v.get("spread")
            if sp and sp > 0.5:
                risk = f"Fair value is sensitive: ±1 pp discount rate and ±2 pp growth moves it by {sp:.0%} of base."
            elif pv.get("margin_of_safety") is not None and pv["margin_of_safety"] >= 0.4:
                rv = reverse(a, pv["price"])
                risk = (f"A {pv['margin_of_safety']:.0%} margin of safety means the market disagrees with this model, and the history it uses ends at the "
                        f"last fiscal year-end. " + (rv["text"] if rv else "") +
                        " If something has changed since then (guidance, competition, demand), the history overstates what the business will deliver.")
        if v.get("midcycle") and v["midcycle"]["range_pp"] >= 10:
            risk = f"Cyclical earnings: operating margin ranged {v['midcycle']['range_pp']:.0f} pp across the available years. " + risk
    return reason, risk


def thesis(a, pv):
    q, v = a["quality"], a.get("valuation", {})
    kind = a["kind"]
    if not v.get("usable"):
        why = "; ".join(v.get("blockers", ["insufficient data"]))
        return {"thesis": f"No credible long-term valuation can be made from the available data: {why}.",
                "risk": "Missing or inconsistent data is itself the main risk - do not act on this page without importing more history.",
                "watch": "Import older annual statements (Yahoo CSV) or wait for more fiscal years so coverage reaches 4+ years."}
    reason, risk = reason_and_risk(a, pv)
    mid = v.get("midcycle")
    bp = v["base_params"]
    if kind == "operating":
        watch = (f"Operating margin reaching the base target of {bp['margin_target']:.1%} within {bp['ramp_years']} years "
                 f"(it was {bp['margin_start']:.1%} in the latest fiscal year) would confirm the base case; staying below "
                 f"{v['scenarios']['bear']['params'][2]['value'][1]:.1%} would confirm the bear case.")
    elif kind == "financial":
        watch = f"Return on equity holding at or above {bp['roe']:.1%} (the model's sustainable ROE); a fall toward {bp['r']:.1%} (cost of equity) would remove the premium to book."
    else:
        watch = f"AFFO-proxy per share growing at {bp['g']:.1%} or better with dividends covered (<= 100% of AFFO)."
    t = (f"{a['name']} is rated {q['label']} on business quality and {pv['valuation_label']} on valuation "
         f"(base fair value {pv['fv_base']:.2f} vs price {pv['price']:.2f}). "
         + ("It cleared every shortlist rule." if pv["qualifies"] else f"It misses: {'; '.join(pv['missed'])}.")
         + (f" Reported latest EPS is {mid['reported_eps_latest']:.2f} versus an approximate mid-cycle EPS of {mid['midcycle_eps_estimate']:.2f}." if mid else ""))
    return {"thesis": t, "risk": risk, "watch": watch}
