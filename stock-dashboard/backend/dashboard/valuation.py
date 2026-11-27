"""Fair-value engine: scenario DCF (operating), residual-income / justified P/B (banks, insurers),
AFFO-proxy capitalisation (REITs), cross-check methods, sensitivity, reverse DCF, confidence.
All formulas are pure functions so they can be recomputed independently (see tests)."""
from __future__ import annotations

import statistics as st

from . import config as C


# ------------------------------------------------------------------ price maths (spec formulas)
def margin_of_safety(fv, price):
    return None if (fv is None or fv <= 0 or price is None) else (fv - price) / fv


def upside_to_fair_value(fv, price):
    return None if (fv is None or price is None or price <= 0) else (fv - price) / price


def watch_price(fv, required_mos):
    return None if (fv is None or fv <= 0) else fv * (1 - required_mos)


def decline_to_watch(price, watch):
    """% price must fall to reach the watch price (None if already at/below it)."""
    if price is None or watch is None or price <= watch:
        return None
    return (price - watch) / price


def valuation_label(fv, price, confidence_level):
    if fv is None or fv <= 0 or price is None or confidence_level == "insufficient":
        return "Insufficient evidence"
    mos = margin_of_safety(fv, price)
    if mos >= C.LABEL_UNDERVALUED_MIN_MOS:
        return "Undervalued"
    if mos < C.LABEL_EXPENSIVE_MAX_MOS:
        return "Expensive"
    return "Moderate / Fairly valued"


def label_boundaries():
    u, e = C.LABEL_UNDERVALUED_MIN_MOS, C.LABEL_EXPENSIVE_MAX_MOS
    return [
        {"label": "Undervalued", "rule": f"margin of safety >= {u:.0%}  (price <= {1-u:.0%} of base fair value)"},
        {"label": "Moderate / Fairly valued", "rule": f"margin of safety between {e:.0%} and {u:.0%}"},
        {"label": "Expensive", "rule": f"margin of safety < {e:.0%}  (price more than {-e:.0%} of fair value ABOVE fair value)"},
        {"label": "Insufficient evidence", "rule": "no positive base fair value, confidence 'insufficient', or no usable price"},
    ]


# ------------------------------------------------------------------ helpers
def discount_rate(rf, beta):
    b = min(max(beta if beta is not None else 1.0, C.BETA_CLIP[0]), C.BETA_CLIP[1])
    r = rf + b * C.EQUITY_RISK_PREMIUM
    return min(max(r, C.DISCOUNT_FLOOR), C.DISCOUNT_CAP)


def shrunk_norm(vals):
    """Normalised level: median if >= 8 observations, else halfway between median and the weakest year
    (fewer than 8 years cannot cover a full cycle, so we shrink toward the worst observed year)."""
    v = [x for x in vals if x is not None]
    if not v:
        return None
    med = st.median(v)
    return med if len(v) >= C.YEARS_FOR_HIGH_COVERAGE else 0.5 * (med + min(v))


def clip(x, lo, hi):
    return max(lo, min(hi, x))


# ------------------------------------------------------------------ operating company DCF (FCFF, 10y fade)
def dcf_operating(p: dict) -> dict:
    """p: revenue0, g1, g_term, margin_start, margin_target, ramp_years, tax, capex_start, capex_target,
    capex_ramp_years, da_pct, nwc_pct, r, net_debt, shares. Returns per-share fair value + projection."""
    n = C.PROJECTION_YEARS
    rev_prev = p["revenue0"]
    pv_sum, rows = 0.0, []
    fcf_last = None
    for t in range(1, n + 1):
        g_t = p["g1"] + (p["g_term"] - p["g1"]) * (t - 1) / (n - 1)
        rev = rev_prev * (1 + g_t)
        m = _lerp(p["margin_start"], p["margin_target"], t, p["ramp_years"])
        cx = _lerp(p["capex_start"], p["capex_target"], t, p["capex_ramp_years"])
        if t == n:
            cx = max(cx, p["da_pct"])  # terminal year: net reinvestment cannot be negative
        nopat = rev * m * (1 - p["tax"])
        fcf = nopat + rev * p["da_pct"] - rev * cx - p["nwc_pct"] * (rev - rev_prev)
        pv = fcf / (1 + p["r"]) ** t
        pv_sum += pv
        rows.append({"year": t, "growth": g_t, "revenue": rev, "op_margin": m, "capex_pct": cx, "fcf": fcf, "pv": pv})
        rev_prev, fcf_last = rev, fcf
    tv = fcf_last * (1 + p["g_term"]) / (p["r"] - p["g_term"])
    pv_tv = tv / (1 + p["r"]) ** n
    ev = pv_sum + pv_tv
    equity = ev - p["net_debt"]
    return {"enterprise_value": ev, "equity_value": equity, "per_share": equity / p["shares"],
            "pv_explicit": pv_sum, "pv_terminal": pv_tv, "terminal_share_of_ev": pv_tv / ev if ev else None, "rows": rows}


def _lerp(a, b, t, ramp):
    if ramp <= 0:
        return b
    return a + (b - a) * min(t, ramp) / ramp


def epv_operating(p: dict) -> float:
    """Earnings power value (Greenwald): no-growth, maintenance capex = D&A. Equity per share."""
    nopat = p["revenue0"] * p["margin_target"] * (1 - p["tax"])
    return (nopat / p["r"] - p["net_debt"]) / p["shares"]


# ------------------------------------------------------------------ financials: justified P/B and sustainable payout
def pb_financial(p: dict) -> float:
    """Residual-income closed form: value = BVPS * (ROE - g) / (r - g)."""
    return p["bvps"] * (p["roe"] - p["g"]) / (p["r"] - p["g"])


def payout_ddm_financial(p: dict) -> float:
    d1 = p["eps_norm"] * (1 + p["g"]) * max(0.0, 1 - p["g"] / p["roe"]) if p["roe"] > 0 else 0.0
    return d1 / (p["r"] - p["g"])


# ------------------------------------------------------------------ REIT
def affo_reit(p: dict) -> float:
    return p["affo_ps"] * (1 + p["g"]) / (p["r"] - p["g"])


def ddm_reit(p: dict) -> float:
    return p["dps"] * (1 + p["g"]) / (p["r"] - p["g"]) if p["dps"] else None


# ------------------------------------------------------------------ sensitivity and reverse solving
def grid(fn, rs, xs):
    return [[fn(r, x) for x in xs] for r in rs]


def bisect(fn, lo, hi, target, iters=80):
    flo, fhi = fn(lo) - target, fn(hi) - target
    if flo * fhi > 0:
        return None
    for _ in range(iters):
        mid = (lo + hi) / 2
        fm = fn(mid) - target
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def confidence(coverage_years, suitability_pts, spread, agreement_ok, blockers: list[str]):
    """Published scoring (max 7): coverage 0-2, suitability 0-2, sensitivity 0-2, method agreement 0-1.
    High  >= 6 AND >= 8 fiscal years;  Medium 4-5 (or >= 6 with < 8 years);  Low < 4;  insufficient if blockers."""
    if blockers:
        return {"level": "insufficient", "points": 0, "max": 7, "breakdown": [], "blockers": blockers}
    cov = 2 if coverage_years >= C.YEARS_FOR_HIGH_COVERAGE else (1 if coverage_years >= C.MIN_YEARS_FOR_ASSESSMENT else 0)
    sens = 2 if spread <= 0.5 else (1 if spread <= 1.0 else 0)
    agr = 1 if agreement_ok else 0
    pts = cov + suitability_pts + sens + agr
    if pts >= 6 and coverage_years >= C.YEARS_FOR_HIGH_COVERAGE:
        level = "high"
    elif pts >= 4:
        level = "medium"
    else:
        level = "low"
    return {"level": level, "points": pts, "max": 7, "blockers": [],
            "breakdown": [
                {"factor": "Data coverage", "points": cov, "max": 2,
                 "detail": f"{coverage_years} fiscal years with core lines (>=8 -> 2, 4-7 -> 1, <4 -> 0)"},
                {"factor": "Model suitability", "points": suitability_pts, "max": 2,
                 "detail": "Does the method fit this business and are its inputs consistently positive?"},
                {"factor": "Sensitivity", "points": sens, "max": 2,
                 "detail": f"Fair-value spread across the r/growth grid = {spread:.0%} of base (<=50% -> 2, <=100% -> 1)"},
                {"factor": "Method agreement", "points": agr, "max": 1,
                 "detail": "Cross-check method within 35% of primary" if agreement_ok else "Cross-check differs >35% from primary"},
            ]}


CONFIDENCE_RULES = [
    "Confidence is a 0-7 score: data coverage (0-2) + model suitability (0-2) + sensitivity (0-2) + method agreement (0-1).",
    "High = score >= 6 AND at least 8 fiscal years of data; Medium = 4-5 (or 6-7 with fewer than 8 years); Low = below 4.",
    "Insufficient evidence = fewer than 4 fiscal years, missing core lines, non-positive model value, currency/share-class "
    "basis that cannot be reconciled, or an unverified ADR ratio.",
    "Yahoo normally provides only 4-5 annual periods, so 'High' is reachable only after importing older annual CSV data.",
]
