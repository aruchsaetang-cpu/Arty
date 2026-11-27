"""Independent verification: (1) STM FY figures vs a FRESH Yahoo pull; (2) re-derive fair value / margin of safety /
watch price for a qualifying stock with code that does NOT import dashboard.valuation or dashboard.assess.
Usage: python3 scripts/verify_independent.py STM LULU"""
import json, math, statistics as st, sys, urllib.request
import yfinance as yf

BASE = "http://localhost:8765"
def api(path): return json.load(urllib.request.urlopen(BASE + path, timeout=120))
def pick(df, labels, col):
    for l in labels:
        if l in df.index and col in df.columns and not math.isnan(df.loc[l, col]): return float(df.loc[l, col])
    return None

def stm_check():
    tk = yf.Ticker("STM"); inc, cf = tk.income_stmt, tk.cashflow
    d = api("/api/stock/STM")
    cols = d["columns"]; i = [c["end"] for c in cols].index("2025-12-31")
    col = next(c for c in inc.columns if str(c.date()) == "2025-12-31")
    rev, oi = pick(inc, ["Total Revenue"], col), pick(inc, ["Operating Income"], col)
    ocf = pick(cf, ["Operating Cash Flow"], col)
    capex = pick(cf, ["Capital Expenditure"], col)
    if capex is None: capex = (pick(cf, ["Purchase Of PPE"], col) or 0) + (pick(cf, ["Purchase Of Intangibles"], col) or 0)
    fcf_y = pick(cf, ["Free Cash Flow"], col)
    sp = {r["key"]: r for r in d["tables"]["income"]["spec"] + d["tables"]["cashflow"]["spec"]}
    rows = [("Revenue FY2025", rev, sp["revenue"]["values"][i]), ("Operating income", oi, sp["op_income"]["values"][i]),
            ("Operating margin", oi / rev, sp["op_margin"]["values"][i]), ("Operating cash flow", ocf, sp["ocf"]["values"][i]),
            ("Free cash flow (Yahoo reported)", fcf_y, sp["fcf_yahoo"]["values"][i]),
            ("Free cash flow (OCF - |capex|, ours)", ocf - abs(capex), sp["fcf"]["values"][i])]
    ok = True
    print("STM FY2025 - fresh yfinance vs dashboard")
    for n, a, b in rows:
        good = a is not None and b is not None and abs(a - b) <= 1e-6 * max(1, abs(a))
        ok &= good; print(f"  {'OK ' if good else 'XX '} {n:<40} yahoo={a:,.4f}  dashboard={b:,.4f}")
    return ok

def clip(x, lo, hi): return max(lo, min(hi, x))
def independent_operating(t):
    tk = yf.Ticker(t); inc, bal, cf, info = tk.income_stmt, tk.balance_sheet, tk.cashflow, tk.info
    dash = api(f"/api/stock/{t}?mos=0.2")
    v = dash["valuation"]; price = dash["price_view"]["price"]; rf = v["rf"]; beta = info.get("beta")
    cols = sorted(c for c in inc.columns if not math.isnan(inc.loc["Total Revenue", c]))
    rev = [pick(inc, ["Total Revenue"], c) for c in cols]; oi = [pick(inc, ["Operating Income"], c) for c in cols]
    opm = [o / r for o, r in zip(oi, rev)]
    cx = []
    for c in cols:
        x = pick(cf, ["Capital Expenditure"], c)
        if x is None: x = (pick(cf, ["Purchase Of PPE"], c) or 0) + (pick(cf, ["Purchase Of Intangibles"], c) or 0)
        cx.append(abs(x))
    da = [abs(pick(cf, ["Depreciation And Amortization", "Depreciation Amortization Depletion"], c) or pick(inc, ["Reconciled Depreciation"], c) or 0) for c in cols]
    cxp = [a / r for a, r in zip(cx, rev)]; dap = [a / r for a, r in zip(da, rev)]
    nwc = []
    for c, r in zip(cols, rev):
        ar = pick(bal, ["Accounts Receivable", "Receivables"], c); inv = pick(bal, ["Inventory"], c); ap = pick(bal, ["Accounts Payable", "Payables"], c)
        if None not in (ar, inv, ap): nwc.append((ar + inv - ap) / r)
    nwc_pct = clip(st.median(nwc) if nwc else 0, 0, .35)
    taxes = [pick(inc, ["Tax Rate For Calcs"], c) for c in cols]; taxes = [x for x in taxes if x is not None]
    tax = clip(st.median(taxes) if taxes else .21, .10, .30)
    yrs = (cols[-1] - cols[0]).days / 365.25
    g_hist = (rev[-1] / rev[0]) ** (1 / yrs) - 1
    g_base = clip(g_hist, .02, .10)
    med = st.median(opm); m_norm = med if len(opm) >= 8 else .5 * (med + min(opm))
    cx_med, da_med = st.median(cxp), st.median(dap)
    cx_t = (cx_med + da_med) / 2 if cx_med > da_med else cx_med
    r = clip(rf + clip(beta, .8, 1.4) * .05, .08, .12)
    last = cols[-1]
    debt = pick(bal, ["Total Debt"], last) or 0; cash = pick(bal, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"], last) or 0
    dil = pick(inc, ["Diluted Average Shares"], last); out_sh = info.get("impliedSharesOutstanding") or info.get("sharesOutstanding")
    shares = out_sh if 0.8 <= out_sh / dil <= 1.25 else dil
    # explicit year loop (independent structure)
    R, pv = rev[-1], 0.0
    m0, cx0 = opm[-1], cxp[-1]
    for y in range(1, 11):
        g = g_base + (.025 - g_base) * (y - 1) / 9
        Rn = R * (1 + g)
        m = m0 + (m_norm - m0) * min(y, 3) / 3
        c_ = cx0 + (cx_t - cx0) * min(y, 3) / 3
        if y == 10: c_ = max(c_, da_med)
        f = Rn * m * (1 - tax) + Rn * da_med - Rn * c_ - nwc_pct * (Rn - R)
        pv += f / (1 + r) ** y; R = Rn; last_f = f
    tv = last_f * 1.025 / (r - .025) / (1 + r) ** 10
    fv = (pv + tv - (debt - cash)) / shares
    mos = (fv - price) / fv; watch = fv * (1 - .20); upside = (fv - price) / price
    d_fv = v["scenarios"]["base"]["fair_value"]; pvw = dash["price_view"]
    print(f"\n{t}: independent re-derivation (rf={rf:.4%} taken from dashboard, everything else recomputed from fresh Yahoo data)")
    print(f"  price used            {price:.2f}  @ {dash['price_timestamp']}")
    rows = [("base fair value", fv, d_fv), ("margin of safety", mos, pvw["margin_of_safety"]), ("upside to fair value", upside, pvw["upside"]), ("watch price (20%)", watch, pvw["watch_price"])]
    ok = True
    for n, a, b in rows:
        good = abs(a - b) <= 0.005 * abs(b); ok &= good
        print(f"  {'OK ' if good else 'XX '} {n:<22} independent={a:,.4f}  dashboard={b:,.4f}")
    print(f"  discount rate {r:.4%}, g1 {g_base:.2%}, margin target {m_norm:.2%}, capex target {cx_t:.2%}, D&A {da_med:.2%}, tax {tax:.1%}, shares {shares/1e6:,.1f}M")
    return ok

if __name__ == "__main__":
    ok = True
    for t in sys.argv[1:] or ["STM", "LULU"]:
        ok &= stm_check() if t == "STM" else independent_operating(t)
    print("\nALL VERIFICATIONS PASSED" if ok else "\nMISMATCH FOUND"); sys.exit(0 if ok else 1)
