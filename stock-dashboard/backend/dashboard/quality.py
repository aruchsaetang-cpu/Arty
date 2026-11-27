"""Buffett-inspired business-quality rules. Published thresholds, sector-specific pillars, figures with fiscal years."""
from __future__ import annotations

import statistics as st

from . import config as C
from .fundamentals import cagr

PILLAR_POINTS = {"pass": 20, "partial": 10, "fail": 0}

RULES = {
    "operating": [
        ("earning_power", "Durable earning power",
         "PASS: operating and net income positive in every year AND operating-margin std-dev <= 6 pp. PARTIAL: profitable every year but volatile, or one loss year with stable margins."),
        ("returns", "Returns on capital",
         "ROIC = operating income x (1 - tax) / (equity + debt). PASS: average >= 12% and minimum >= 8%. PARTIAL: average >= 8%."),
        ("reinvestment", "Cash required for reinvestment",
         "PASS: free cash flow positive every year and capex <= 50% of operating cash flow. PARTIAL: FCF positive in >= 75% of years and capex <= 70% of OCF."),
        ("balance_sheet", "Balance-sheet strength",
         "PASS: net debt / EBITDA <= 2.5 (or net cash) and EBIT / interest >= 6. PARTIAL: net debt / EBITDA <= 4."),
        ("per_share", "Value created per share",
         "PASS: diluted EPS CAGR >= 5% and diluted share count growth <= 1%/yr. PARTIAL: EPS CAGR >= 0 and share growth <= 2%/yr."),
    ],
    "financial": [
        ("earning_power", "Durable earning power", "PASS: net income positive every year and average ROA >= 0.7%. PARTIAL: profitable every year."),
        ("returns", "Returns on capital", "ROE = net income to common / average common equity. PASS: average >= 10% and minimum >= 6%. PARTIAL: average >= 7%."),
        ("reinvestment", "Retained capital growth", "PASS: book value per share CAGR >= 4%. PARTIAL: >= 0%."),
        ("balance_sheet", "Balance-sheet strength", "Common equity / total assets. PASS: >= 8%. PARTIAL: >= 5%. (Yahoo has no regulatory capital ratios.)"),
        ("per_share", "Value created per share", "PASS: diluted EPS CAGR >= 5% and share CAGR <= 0.5%/yr. PARTIAL: EPS CAGR >= 0 and share CAGR <= 2%/yr."),
    ],
    "reit": [
        ("earning_power", "Durable earning power", "FFO proxy = net income + D&A - gains on sale. PASS: positive every year and FFO CAGR >= 0. PARTIAL: positive every year."),
        ("returns", "Returns on capital", "Operating income / total assets. PASS: average >= 4%. PARTIAL: >= 2.5%."),
        ("reinvestment", "Cash required for reinvestment", "Dividends paid / AFFO proxy (FFO less 10% recurring-capex haircut). PASS: <= 85% (cash retained). PARTIAL: <= 100%."),
        ("balance_sheet", "Balance-sheet strength", "PASS: net debt / EBITDA <= 6.0 and EBIT / interest >= 2.5. PARTIAL: net debt / EBITDA <= 7.5."),
        ("per_share", "Value created per share", "PASS: FFO-per-share CAGR >= 3% and share CAGR <= 3%/yr. PARTIAL: FFO-per-share CAGR >= 0."),
    ],
}

LABEL_RULE = ("Strong: total >= 80/100, no pillar scoring 0, BOTH 'Durable earning power' and 'Returns on capital' passing outright, and >= 4 fiscal years of core data. "
              "Mixed: total 50-79 (or >= 80 without meeting those conditions). "
              "Weak: total < 50. Insufficient evidence: fewer than 4 fiscal years or core lines missing.")
CORE_LINES = {"operating": ["revenue", "op_income", "net_income", "equity", "ocf", "capex", "shares"],
              "financial": ["net_income", "equity", "assets", "shares"],
              "reit": ["net_income", "assets", "shares"]}

MOAT_CAVEAT = ("This is an inference from financial statements only. Yahoo Finance supplies no market-share, switching-cost, brand or "
               "regulatory evidence, so a moat can be suggested by the numbers but never confirmed by them.")


def classify(info: dict) -> str:
    ind = (info.get("industry") or "").lower()
    sec = (info.get("sector") or "").lower()
    if "reit" in ind:
        return "reit"
    if sec == "financial services" and any(k in ind for k in
            ("bank", "insurance", "credit services", "mortgage finance", "capital markets", "financial conglomerate")):
        return "financial"
    return "operating"


def _series(d, cols, key):
    return [(c["label"], c["end"], v) for c, v in zip(cols, d.get(key, [])) if v is not None and c["end"]]


def _fig(name, pairs, kind="num"):
    return {"name": name, "kind": kind, "points": [{"fy": fy, "end": end, "value": v} for fy, end, v in pairs]}


def _cagr_pair(pairs):
    if len(pairs) < 2:
        return None, "needs >= 2 years"
    (_, e0, v0), (_, e1, v1) = pairs[0], pairs[-1]
    return cagr(v0, v1, e0, e1)


def tax_rate(d, i):
    t = d["tax_rate"][i]
    return min(max(t, 0.0), 0.35) if t is not None else 0.21


def _grade(key, name, status, summary, figs):
    return {"key": key, "name": name, "status": status, "points": PILLAR_POINTS[status], "summary": summary, "figures": figs}


def last_index(cols):
    return max(i for i, c in enumerate(cols) if c["end"])


def assess_quality(kind: str, d: dict, cols: list[dict], info: dict) -> dict:
    n_years = sum(1 for c in cols if c["end"])
    need = min(max(n_years, 1), C.MIN_YEARS_FOR_ASSESSMENT)
    missing = [k for k in CORE_LINES[kind] if sum(v is not None for v in d.get(k, [])) < need]
    base = {"kind": kind, "years": n_years, "rule_text": LABEL_RULE,
            "pillar_rules": [{"key": k, "name": n, "rule": r} for k, n, r in RULES[kind]]}
    if n_years < C.MIN_YEARS_FOR_ASSESSMENT or missing:
        why = (f"only {n_years} fiscal years of data (need {C.MIN_YEARS_FOR_ASSESSMENT})" if n_years < C.MIN_YEARS_FOR_ASSESSMENT
               else f"core lines missing: {', '.join(missing)}")
        return {**base, "label": "Insufficient evidence", "score": None, "pillars": [], "reason": why,
                "moat": {"supports": [], "weakens": [], "caveat": MOAT_CAVEAT}}
    fn = {"operating": _q_operating, "financial": _q_financial, "reit": _q_reit}[kind]
    pillars = fn(d, cols, info)
    total = sum(p["points"] for p in pillars)
    zero = any(p["points"] == 0 for p in pillars)
    core_pass = all(p["status"] == "pass" for p in pillars if p["key"] in ("earning_power", "returns"))
    label = "Strong" if (total >= 80 and not zero and core_pass) else "Mixed" if total >= 50 else "Weak"
    return {**base, "label": label, "score": total, "pillars": pillars, "reason": None,
            "moat": moat_inference(kind, d, cols)}


def _per_share_pillar(d, cols, key, g_pass, sh_pass, g_part, sh_part, name="Value created per share"):
    eps = _series(d, cols, key)
    sh = _series(d, cols, "shares")
    ge, why = _cagr_pair(eps)
    gs, _ = _cagr_pair(sh)
    if ge is None:
        s, txt = "fail", f"Per-share growth not meaningful ({why})."
    else:
        gs_v = gs if gs is not None else 0
        s = "pass" if (ge >= g_pass and gs_v <= sh_pass) else "partial" if (ge >= g_part and gs_v <= sh_part) else "fail"
        txt = (f"Per-share CAGR {ge:.1%} ({eps[0][0]}-{eps[-1][0]}); diluted shares "
               f"{'n/a' if gs is None else f'{gs:+.1%}/yr'}.")
    return _grade("per_share", name, s, txt, [_fig("Per-share metric", eps, "num"), _fig("Diluted shares", sh, "shares")])


def _q_operating(d, cols, info):
    out = []
    opm = _series(d, cols, "op_margin")
    oi = _series(d, cols, "op_income")
    ni = _series(d, cols, "net_income")
    sd = st.pstdev([v * 100 for _, _, v in opm]) if len(opm) > 1 else 0.0
    prof_all = all(v > 0 for *_, v in oi) and all(v > 0 for *_, v in ni)
    loss_years = sum(1 for *_, v in oi if v <= 0)
    s = "pass" if (prof_all and sd <= 6) else "partial" if (prof_all or (loss_years <= 1 and sd <= 6)) else "fail"
    out.append(_grade("earning_power", "Durable earning power", s,
                      f"Operating margin std-dev {sd:.1f} pp over {len(opm)} years; "
                      f"{'profitable every year' if prof_all else 'at least one loss year'}.",
                      [_fig("Operating margin", opm, "pct"), _fig("Net income", ni, "money")]))
    roic = []
    for i, c in enumerate(cols):
        if not c["end"] or d["op_income"][i] is None or d["equity"][i] is None:
            continue
        cap = d["equity"][i] + (d["debt"][i] or 0)
        if cap > 0:
            roic.append((c["label"], c["end"], d["op_income"][i] * (1 - tax_rate(d, i)) / cap))
    avg = st.mean(v for *_, v in roic) if roic else None
    mn = min(v for *_, v in roic) if roic else None
    s = "fail" if avg is None else "pass" if (avg >= .12 and mn >= .08) else "partial" if avg >= .08 else "fail"
    out.append(_grade("returns", "Returns on capital", s,
                      "ROIC unavailable" if avg is None else f"ROIC average {avg:.1%}, minimum {mn:.1%}.", [_fig("ROIC", roic, "pct")]))
    ocf, cx = d["ocf"], d["capex_abs"]
    ratio = [(c["label"], c["end"], cx[i] / ocf[i]) for i, c in enumerate(cols)
             if c["end"] and ocf[i] and ocf[i] > 0 and cx[i] is not None]
    fcfp = _series(d, cols, "fcf")
    pos_share = sum(v > 0 for *_, v in fcfp) / len(fcfp) if fcfp else 0
    avg_r = st.mean(v for *_, v in ratio) if ratio else None
    s = ("fail" if avg_r is None else "pass" if (pos_share == 1 and avg_r <= .5)
         else "partial" if (pos_share >= .75 and avg_r <= .7) else "fail")
    out.append(_grade("reinvestment", "Cash required for reinvestment", s,
                      "Capex / OCF unavailable" if avg_r is None else
                      f"Capex consumed {avg_r:.0%} of operating cash flow on average; FCF positive in {pos_share:.0%} of years.",
                      [_fig("Capex / operating cash flow", ratio, "pct"), _fig("Free cash flow", fcfp, "money")]))
    i = last_index(cols)
    ebitda = (d["op_income"][i] or 0) + abs(d["da"][i] or 0)
    nd = (d["debt"][i] or 0) - (d["cash"][i] or 0)
    lev = nd / ebitda if ebitda > 0 else None
    ie = d["interest_expense"][i]
    cov = d["op_income"][i] / abs(ie) if ie and d["op_income"][i] is not None else None
    if lev is None and nd <= 0:
        lev = 0.0
    s = "fail" if lev is None else "pass" if (lev <= 2.5 and (cov is None or cov >= 6)) else "partial" if lev <= 4 else "fail"
    out.append(_grade("balance_sheet", "Balance-sheet strength", s,
                      f"{cols[i]['label']}: {'net cash' if nd <= 0 else ('net debt/EBITDA n/m' if lev is None else f'net debt/EBITDA {lev:.1f}x')}; "
                      f"interest cover {'n/a' if cov is None else f'{cov:.1f}x'}.",
                      [_fig("Net cash (cash - debt)", _series(d, cols, "net_cash"), "money")]))
    out.append(_per_share_pillar(d, cols, "eps", .05, .01, .0, .02))
    return out


def _q_financial(d, cols, info):
    out = []
    ni = _series(d, cols, "ni_common")
    roa = [(c["label"], c["end"], d["ni_common"][i] / d["assets"][i]) for i, c in enumerate(cols)
           if c["end"] and d["ni_common"][i] is not None and d["assets"][i]]
    avg_roa = st.mean(v for *_, v in roa) if roa else None
    allpos = all(v > 0 for *_, v in ni)
    s = "pass" if (allpos and avg_roa is not None and avg_roa >= .007) else "partial" if allpos else "fail"
    out.append(_grade("earning_power", "Durable earning power", s,
                      f"{'Profitable every year' if allpos else 'A loss year exists'}; average ROA "
                      f"{'n/a' if avg_roa is None else f'{avg_roa:.2%}'}.",
                      [_fig("Net income to common", ni, "money"), _fig("ROA", roa, "pct")]))
    roe = roe_series(d, cols)
    avg = st.mean(v for *_, v in roe) if roe else None
    mn = min(v for *_, v in roe) if roe else None
    s = "fail" if avg is None else "pass" if (avg >= .10 and mn >= .06) else "partial" if avg >= .07 else "fail"
    out.append(_grade("returns", "Returns on capital", s,
                      "ROE unavailable" if avg is None else f"ROE average {avg:.1%}, minimum {mn:.1%}.", [_fig("ROE", roe, "pct")]))
    bv = [(c["label"], c["end"], d["equity"][i] / d["shares"][i]) for i, c in enumerate(cols)
          if c["end"] and d["equity"][i] and d["shares"][i]]
    g, r = _cagr_pair(bv)
    s = "fail" if g is None else "pass" if g >= .04 else "partial" if g >= 0 else "fail"
    out.append(_grade("reinvestment", "Retained capital growth", s,
                      f"Book value/share CAGR {'n/m (' + str(r) + ')' if g is None else f'{g:.1%}'}.", [_fig("Book value per share", bv, "num")]))
    lev = [(c["label"], c["end"], d["equity"][i] / d["assets"][i]) for i, c in enumerate(cols)
           if c["end"] and d["equity"][i] is not None and d["assets"][i]]
    last = lev[-1][2] if lev else None
    s = "fail" if last is None else "pass" if last >= .08 else "partial" if last >= .05 else "fail"
    out.append(_grade("balance_sheet", "Balance-sheet strength", s,
                      "n/a" if last is None else f"Common equity / assets {last:.1%} in {lev[-1][0]}.", [_fig("Equity / assets", lev, "pct")]))
    out.append(_per_share_pillar(d, cols, "eps", .05, .005, 0, .02))
    return out


def roe_series(d, cols):
    roe = []
    idxs = [i for i, c in enumerate(cols) if c["end"]]
    for k, i in enumerate(idxs):
        eq, ni_i = d["equity"][i], d["ni_common"][i]
        if eq is None or ni_i is None:
            continue
        prev = d["equity"][idxs[k - 1]] if k else None
        den = (eq + prev) / 2 if prev else eq
        if den > 0:
            roe.append((cols[i]["label"], cols[i]["end"], ni_i / den))
    return roe


def ffo_series(d, cols):
    res = []
    for i, c in enumerate(cols):
        if not c["end"] or d["net_income"][i] is None or d["da"][i] is None:
            res.append(None)
            continue
        gain = d["gain_on_sale"][i] or 0.0
        res.append(d["net_income"][i] + abs(d["da"][i]) - gain)
    return res


def _q_reit(d, cols, info):
    out = []
    ffo = ffo_series(d, cols)
    d["ffo"] = ffo
    d["ffo_ps"] = [None if (f is None or not s) else f / s for f, s in zip(ffo, d["shares"])]
    ffo_p = [(c["label"], c["end"], v) for c, v in zip(cols, ffo) if v is not None and c["end"]]
    g, _ = _cagr_pair(ffo_p)
    allpos = bool(ffo_p) and all(v > 0 for *_, v in ffo_p)
    s = "pass" if (allpos and g is not None and g >= 0) else "partial" if allpos else "fail"
    out.append(_grade("earning_power", "Durable earning power", s,
                      f"FFO proxy positive every year: {allpos}; FFO CAGR {'n/m' if g is None else f'{g:.1%}'}.",
                      [_fig("FFO proxy", ffo_p, "money")]))
    roa = [(c["label"], c["end"], d["op_income"][i] / d["assets"][i]) for i, c in enumerate(cols)
           if c["end"] and d["op_income"][i] is not None and d["assets"][i]]
    avg = st.mean(v for *_, v in roa) if roa else None
    s = "fail" if avg is None else "pass" if avg >= .04 else "partial" if avg >= .025 else "fail"
    out.append(_grade("returns", "Returns on capital", s,
                      "n/a" if avg is None else f"Operating income / assets averaged {avg:.1%}.", [_fig("Operating income / assets", roa, "pct")]))
    pay = [(c["label"], c["end"], abs(d["dividends"][i]) / (0.9 * ffo[i])) for i, c in enumerate(cols)
           if c["end"] and d["dividends"][i] is not None and ffo[i] and ffo[i] > 0]
    last = pay[-1][2] if pay else None
    s = "fail" if last is None else "pass" if last <= .85 else "partial" if last <= 1.0 else "fail"
    out.append(_grade("reinvestment", "Cash required for reinvestment", s,
                      "n/a" if last is None else f"Dividends = {last:.0%} of AFFO proxy in {pay[-1][0]}.", [_fig("Dividends / AFFO proxy", pay, "pct")]))
    i = last_index(cols)
    ebitda = (d["op_income"][i] or 0) + abs(d["da"][i] or 0)
    nd = (d["debt"][i] or 0) - (d["cash"][i] or 0)
    lev = nd / ebitda if ebitda > 0 else None
    ie = d["interest_expense"][i]
    cov = d["op_income"][i] / abs(ie) if ie and d["op_income"][i] is not None else None
    s = "fail" if lev is None else "pass" if (lev <= 6 and (cov is None or cov >= 2.5)) else "partial" if lev <= 7.5 else "fail"
    out.append(_grade("balance_sheet", "Balance-sheet strength", s,
                      f"{cols[i]['label']}: net debt/EBITDA {'n/m' if lev is None else f'{lev:.1f}x'}; "
                      f"interest cover {'n/a' if cov is None else f'{cov:.1f}x'}.",
                      [_fig("Net cash (cash - debt)", _series(d, cols, "net_cash"), "money")]))
    out.append(_per_share_pillar(d, cols, "ffo_ps", .03, .03, 0, .06, "Value created per share (FFO/share)"))
    return out


def moat_inference(kind, d, cols):
    sup, weak = [], []
    gm = _series(d, cols, "gross_margin")
    opm = _series(d, cols, "op_margin")
    if kind == "operating":
        if gm:
            vals = [v for *_, v in gm]
            if min(vals) >= .40 and (max(vals) - min(vals)) <= .05:
                sup.append(f"Gross margin stayed between {min(vals):.0%} and {max(vals):.0%} ({gm[0][0]}-{gm[-1][0]}): consistent with pricing power.")
            if len(vals) > 1 and vals[-1] < vals[0] - .05:
                weak.append(f"Gross margin fell {100*(vals[0]-vals[-1]):.1f} pp from {gm[0][0]} to {gm[-1][0]}.")
        if opm:
            vals = [v for *_, v in opm]
            if len(vals) > 1 and vals[-1] < vals[0] - .05:
                weak.append(f"Operating margin fell {100*(vals[0]-vals[-1]):.1f} pp ({opm[0][0]}-{opm[-1][0]}): competitive or cyclical pressure.")
            if min(vals) >= .15:
                sup.append(f"Operating margin never below {min(vals):.0%} across {len(vals)} years.")
        rd = _series(d, cols, "rnd")
        rev = {fy: v for fy, _, v in _series(d, cols, "revenue")}
        if rd and rev:
            inten = [v / rev[fy] for fy, _, v in rd if fy in rev and rev[fy]]
            if inten and min(inten) >= .08:
                sup.append(f"R&D steady at >= {min(inten):.0%} of revenue - reinvestment in the franchise (not proof of an advantage).")
        sh = _series(d, cols, "shares")
        if len(sh) > 1 and sh[-1][2] > sh[0][2] * 1.05:
            weak.append("Diluted share count grew more than 5% - value may be leaking to new holders.")
        cx = _series(d, cols, "capex_pct_rev")
        if cx and min(v for *_, v in cx) <= .05:
            sup.append("Capex below 5% of revenue: growth does not demand heavy reinvestment.")
        if len(cx) > 1 and cx[-1][2] > cx[0][2] + .05:
            weak.append("Capex intensity rose by more than 5 pp of revenue - the franchise needs more capital to hold its position.")
    elif kind == "financial":
        sup.append("Consistently positive ROE above ~10% (see Returns pillar) can reflect a low-cost funding or underwriting advantage.")
        weak.append("ROE falling below the cost of equity, or book value per share declining, would weaken that inference.")
    else:
        sup.append("Stable FFO per share with covered dividends suggests durable tenant demand and lease economics.")
        weak.append("Rising leverage, a payout above 100% of AFFO, or falling FFO per share would weaken the inference.")
    if not sup:
        sup.append("No statement-based evidence of a durable advantage was found under these rules.")
    if not weak:
        weak.append("Falling gross/operating margins, ROIC dropping toward the cost of capital, or rising capex intensity would weaken it.")
    return {"supports": sup, "weakens": weak, "caveat": MOAT_CAVEAT}


# ------------------------------------------------------------------ Graham and Lynch (secondary)
def graham(kind, d, cols, price, info):
    eps_all = [v for v in d["eps"] if v is not None]
    eps3 = eps_all[-3:]
    eps_avg = st.mean(eps3) if eps3 else None
    last = last_index(cols)
    bvps = d["equity"][last] / d["shares"][last] if d["equity"][last] and d["shares"][last] else None
    rev = d["revenue"][last]
    tests = []

    def T(name, ok, detail, source="The Intelligent Investor (1973), ch.14"):
        tests.append({"test": name, "result": "n/a" if ok is None else ("pass" if ok else "fail"), "detail": detail, "source": source})

    T("Adequate size (revenue >= $2B, a modern stand-in for Graham's $100M)", None if rev is None else rev >= 2e9,
      "n/a" if rev is None else f"{cols[last]['label']} revenue {rev/1e9:.1f}B (reporting currency)")
    cr = d["current_ratio"][last]
    if kind == "operating":
        T("Strong financial condition: current ratio >= 2", None if cr is None else cr >= 2, "n/a" if cr is None else f"current ratio {cr:.2f}")
    else:
        T("Strong financial condition: current ratio >= 2", None, "not meaningful for banks, insurers and REITs")
    ni = [v for v in d["net_income"] if v is not None]
    T("Earnings stability: profit in every available year (Graham asks for 10)", all(v > 0 for v in ni) if ni else None,
      f"{len(ni)} years of data - fewer than the 10 Graham requires")
    T("Dividend record (20 uninterrupted years)", None, "Yahoo statements do not carry 20 years of dividend history")
    pairs = [(c["end"], d["eps"][i]) for i, c in enumerate(cols) if c["end"] and d["eps"][i] is not None]
    g = None
    if len(pairs) > 1:
        g, _ = cagr(pairs[0][1], pairs[-1][1], pairs[0][0], pairs[-1][0])
    T("Earnings growth >= ~2.9%/yr (Graham: >= 33% over 10 years)", None if g is None else g >= .029,
      "n/m (baseline <= 0 or too few years)" if g is None else f"EPS CAGR {g:.1%} over {len(pairs)} years")
    pe = price / eps_avg if (price and eps_avg and eps_avg > 0) else None
    T("Moderate P/E <= 15 on 3-year average EPS", None if pe is None else pe <= 15,
      "n/m" if pe is None else f"P/E {pe:.1f} on average EPS {eps_avg:.2f}")
    pb = price / bvps if (price and bvps and bvps > 0) else None
    T("Moderate P/B <= 1.5, or P/E x P/B <= 22.5", None if (pe is None or pb is None) else (pb <= 1.5 or pe * pb <= 22.5),
      "n/m" if (pe is None or pb is None) else f"P/B {pb:.2f}, P/E x P/B {pe*pb:.1f}")
    gn = (22.5 * eps_avg * bvps) ** .5 if (eps_avg and bvps and eps_avg > 0 and bvps > 0) else None
    scored = [t for t in tests if t["result"] != "n/a"]
    passed = sum(t["result"] == "pass" for t in scored)
    return {"tests": tests, "passed": passed, "applicable": len(scored), "graham_number": gn,
            "graham_mos": (gn - price) / gn if (gn and price) else None,
            "verdict": ("Meets most defensive criteria" if scored and passed / len(scored) >= .75 else
                        "Meets some criteria" if scored and passed / len(scored) >= .5 else "Does not meet the defensive criteria"),
            "note": "Normalized earnings = average of up to the last 3 available fiscal years. Graham's 10-year and 20-year tests cannot be fully run on Yahoo's 4-5 years."}


CYCLICAL_INDUSTRIES = ("semiconductor", "auto", "steel", "chemical", "airline", "oil", "gas", "mining", "metals", "building",
                       "homebuilding", "trucking")


def lynch(kind, d, cols, price, info):
    pairs = [(c["end"], d["eps"][i]) for i, c in enumerate(cols) if c["end"] and d["eps"][i] is not None]
    g, why = None, "too few years"
    if len(pairs) > 1:
        g, why = cagr(pairs[0][1], pairs[-1][1], pairs[0][0], pairs[-1][0])
    opm = [v for v in d["op_margin"] if v is not None]
    rng = (max(opm) - min(opm)) if opm else 0
    ind = (info.get("industry") or "").lower()
    last_eps = pairs[-1][1] if pairs else None
    last = last_index(cols)
    bvps = d["equity"][last] / d["shares"][last] if d["equity"][last] and d["shares"][last] else None
    pbv = price / bvps if (price and bvps and bvps > 0) else None
    if rng >= .10 or (any(k in ind for k in CYCLICAL_INDUSTRIES) and rng >= .06):
        cat, why_cat = "Cyclical", f"operating margin ranged {rng*100:.0f} pp across the available years (industry: {info.get('industry')})"
    elif last_eps is not None and pairs and pairs[0][1] and last_eps < pairs[0][1] * 0.6:
        cat, why_cat = "Turnaround / recovery candidate", "latest EPS is far below its earlier level"
    elif pbv is not None and pbv < 0.8:
        cat, why_cat = "Asset play", f"trades at {pbv:.2f}x book value"
    elif g is None:
        cat, why_cat = "Unclassified", f"EPS CAGR not meaningful ({why})"
    elif g >= .20:
        cat, why_cat = "Fast grower", f"EPS CAGR {g:.0%}"
    elif g >= .10:
        cat, why_cat = "Stalwart", f"EPS CAGR {g:.0%}"
    else:
        cat, why_cat = "Slow grower", f"EPS CAGR {g:.0%}"
    pe = info.get("trailingPE")
    peg = pe / (g * 100) if (pe and g and g > 0) else None
    checks = []
    if peg is not None:
        checks.append({"test": "PEG (P/E / EPS growth)", "result": "pass" if peg < 1 else "neutral" if peg <= 2 else "fail",
                       "detail": f"PEG {peg:.2f} from Yahoo trailing P/E {pe:.1f} and EPS CAGR {g:.1%} (<1 attractive, >2 expensive)"})
    else:
        checks.append({"test": "PEG (P/E / EPS growth)", "result": "n/a", "detail": "needs positive trailing P/E and positive EPS growth"})
    de = d["debt_to_equity"][last]
    checks.append({"test": "Balance sheet: debt / equity < 0.8", "result": "n/a" if de is None else "pass" if de < .8 else "fail",
                   "detail": "n/a" if de is None else f"debt/equity {de:.2f}"})
    inv = [(c["end"], d["inventory"][i]) for i, c in enumerate(cols) if c["end"] and d["inventory"][i]]
    rev = [(c["end"], d["revenue"][i]) for i, c in enumerate(cols) if c["end"] and d["revenue"][i]]
    if len(inv) > 1 and len(rev) > 1:
        gi, _ = cagr(inv[0][1], inv[-1][1], inv[0][0], inv[-1][0])
        gr, _ = cagr(rev[0][1], rev[-1][1], rev[0][0], rev[-1][0])
        if gi is not None and gr is not None:
            checks.append({"test": "Inventory growing faster than sales (Lynch warning)", "result": "fail" if gi > gr + .05 else "pass",
                           "detail": f"inventory CAGR {gi:.1%} vs revenue CAGR {gr:.1%}"})
    sh = [(c["end"], d["shares"][i]) for i, c in enumerate(cols) if c["end"] and d["shares"][i]]
    if len(sh) > 1:
        gs, _ = cagr(sh[0][1], sh[-1][1], sh[0][0], sh[-1][0])
        if gs is not None:
            checks.append({"test": "Share count shrinking or flat (per-share growth is real)", "result": "pass" if gs <= .005 else "fail",
                           "detail": f"diluted shares {gs:+.1%}/yr"})
    cyc = " Cyclical earnings are best judged at mid-cycle, not on peak or trough EPS (One Up on Wall Street, ch.7)." if cat == "Cyclical" else ""
    return {"category": cat, "category_reason": why_cat, "eps_cagr": g, "peg": peg, "checks": checks,
            "note": f"Lynch's six stock categories (One Up on Wall Street, 1989).{cyc}"}
