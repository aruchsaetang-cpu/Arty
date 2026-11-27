"""Statement normalisation: canonical fields, 10 fiscal-year columns, derived ratios, growth maths,
and Yahoo-CSV import validation/merge.  None = missing, 0.0 = reported zero (never conflated)."""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime

import pandas as pd

SLOTS = 10


def norm(label: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(label).lower())


ALIASES = {
    "income": {
        "revenue": ["totalrevenue", "operatingrevenue"],
        "cogs": ["costofrevenue", "reconciledcostofrevenue"],
        "gross_profit": ["grossprofit"],
        "rnd": ["researchanddevelopment"],
        "op_income": ["operatingincome", "totaloperatingincomeasreported"],
        "pretax": ["pretaxincome"],
        "net_income": ["netincome", "netincomecommonstockholders", "netincomefromcontinuingoperationnetminorityinterest"],
        "ni_common": ["netincomecommonstockholders", "netincome"],
        "eps": ["dilutedeps"],
        "shares": ["dilutedaveragershares", "dilutedaverageshares"],
        "interest_expense": ["interestexpense", "interestexpensenonoperating"],
        "tax_rate": ["taxrateforcalcs"],
        "da_is": ["reconcileddepreciation"],
        "gain_on_sale": ["gainonsaleofsecurity", "gainonsaleofppe", "gainonsaleofbusiness"],
    },
    "balance": {
        "cash": ["cashcashequivalentsandshortterminvestments", "cashandcashequivalents"],
        "receivables": ["accountsreceivable", "receivables"],
        "inventory": ["inventory"],
        "cur_assets": ["currentassets"],
        "assets": ["totalassets"],
        "cur_liab": ["currentliabilities"],
        "liab": ["totalliabilitiesnetminorityinterest"],
        "debt": ["totaldebt"],
        "equity": ["commonstockequity", "stockholdersequity"],
        "payables": ["accountspayable", "payables"],
    },
    "cashflow": {
        "ocf": ["operatingcashflow", "cashflowfromcontinuingoperatingactivities"],
        "capex": ["capitalexpenditure"],
        "purchase_ppe": ["purchaseofppe", "netppepurchaseandsale"],
        "purchase_intang": ["purchaseofintangibles"],
        "fcf_yahoo": ["freecashflow"],
        "da_cf": ["depreciationandamortization", "depreciationamortizationdepletion"],
        "dividends": ["cashdividendspaid", "commonstockdividendpaid"],
        "buybacks": ["repurchaseofcapitalstock"],
    },
}


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def merged_raw(fund: dict, imported: dict | None) -> dict:
    """Overlay imported rows (only where Yahoo has no value) and tag provenance per (stmt,label,date)."""
    out = {k: {lab: dict(v) for lab, v in fund.get(k, {}).items()} for k in ("income", "balance", "cashflow")}
    prov: dict = {}
    for st, rows in (imported or {}).get("statements", {}).items():
        for lab, vals in rows.items():
            tgt = out[st].setdefault(lab, {})
            for dte, v in vals.items():
                forced = [st, lab, dte] in (imported.get("override") or [])
                if tgt.get(dte) is None or forced:
                    tgt[dte] = v
                    prov[(st, lab, dte)] = "import"
    return {"statements": out, "prov": prov}


def canonical(raw_statements: dict) -> dict:
    """{field: {date: value}} using the first alias that has a value for each date."""
    out: dict = {}
    for st, fields in ALIASES.items():
        by_norm = {norm(l): v for l, v in raw_statements.get(st, {}).items()}
        for field, names in fields.items():
            merged: dict = {}
            for n in names:
                for dte, v in by_norm.get(n, {}).items():
                    if v is not None and dte not in merged:
                        merged[dte] = v
            out[field] = merged
    # Yahoo omits 'Capital Expenditure' for some years but its own Free Cash Flow = OCF - PP&E - intangibles purchases.
    for dte, ppe in out.get("purchase_ppe", {}).items():
        if dte not in out["capex"]:
            out["capex"][dte] = ppe + (out.get("purchase_intang", {}).get(dte) or 0.0)
    return out


def make_columns(dates: list[str], anchor: str | None = None) -> list[dict]:
    """10 most recent completed fiscal-year slots, oldest -> newest, anchored on the latest period end."""
    ds = sorted({d for d in dates})
    if not ds:
        return []
    latest = _d(anchor or ds[-1])
    cols = []
    for i in range(SLOTS - 1, -1, -1):
        y = latest.year - i
        exp = date(y, latest.month, min(latest.day, 28))
        match = next((d for d in ds if abs((_d(d) - exp).days) <= 45), None)
        cols.append({"slot": SLOTS - 1 - i, "label": f"FY{y}", "expected_end": str(exp), "end": match,
                     "available": match is not None})
    return cols


def aligned(canon: dict, cols: list[dict]) -> dict:
    return {f: [canon[f].get(c["end"]) if c["end"] else None for c in cols] for f in canon}


def derive(canon: dict, cols: list[dict]) -> dict:
    a = aligned(canon, cols)
    n = len(cols)

    def op(fn, *keys):
        res = []
        for i in range(n):
            vs = [a[k][i] if k in a else None for k in keys]
            res.append(None if any(v is None for v in vs) else fn(*vs))
        return res

    d = dict(a)
    d["gross_profit"] = [g if g is not None else r for g, r in
                         zip(a["gross_profit"], op(lambda r, c: r - c, "revenue", "cogs"))]
    d["capex_abs"] = [abs(x) if x is not None else None for x in a["capex"]]  # spend deducted once, sign-normalised
    d["fcf"] = op(lambda o, c: o - abs(c), "ocf", "capex")
    d["fcf_ps"] = [None if (f is None or not s) else f / s for f, s in zip(d["fcf"], a["shares"])]
    d["gross_margin"] = op(lambda g, r: g / r if r else None, "gross_profit", "revenue") if False else \
        [None if (g is None or not r) else g / r for g, r in zip(d["gross_profit"], a["revenue"])]
    d["op_margin"] = op(lambda o, r: o / r if r else None, "op_income", "revenue")
    d["net_margin"] = op(lambda o, r: o / r if r else None, "net_income", "revenue")
    d["fcf_margin"] = [None if (f is None or not r) else f / r for f, r in zip(d["fcf"], a["revenue"])]
    d["working_capital"] = op(lambda ca, cl: ca - cl, "cur_assets", "cur_liab")
    d["current_ratio"] = op(lambda ca, cl: ca / cl if cl else None, "cur_assets", "cur_liab")
    d["debt_to_equity"] = [x if (e is not None and e > 0) else None for x, e in
                           zip(op(lambda dbt, e: dbt / e if e else None, "debt", "equity"), a["equity"])]
    d["net_cash"] = op(lambda c, dbt: c - dbt, "cash", "debt")
    d["capex_pct_rev"] = [None if (c is None or not r) else c / r for c, r in zip(d["capex_abs"], a["revenue"])]
    d["da"] = [x if x is not None else y for x, y in zip(a["da_cf"], a["da_is"])]
    d["da_pct_rev"] = [None if (c is None or not r) else abs(c) / r for c, r in zip(d["da"], a["revenue"])]
    d["owner_earnings_proxy"] = [None if (ni is None or da is None or cx is None) else ni + abs(da) - cx
                                 for ni, da, cx in zip(a["net_income"], d["da"], d["capex_abs"])]
    return d


# ---------------------------- growth maths ---------------------------------------------------
def years_between(d0: str, d1: str) -> float:
    return (_d(d1) - _d(d0)).days / 365.25


def cagr(v0, v1, d0: str, d1: str):
    """CAGR over ACTUAL elapsed years. Returns (value|None, reason|None)."""
    if v0 is None or v1 is None:
        return None, "missing data"
    yrs = years_between(d0, d1)
    if yrs <= 0.5:
        return None, "period too short"
    if v0 <= 0:
        return None, "baseline zero/negative"
    if v1 <= 0:
        return None, "ending value zero/negative"
    return (v1 / v0) ** (1 / yrs) - 1, None


def yoy(vals: list, cols: list[dict], pct=True):
    """Consecutive-year change only; if either neighbour is missing/non-consecutive -> None.
    Zero/negative baselines: percentage is None and an absolute change + transition flag is given."""
    out = []
    for i in range(len(vals)):
        if i == 0 or vals[i] is None or vals[i - 1] is None or not cols[i]["end"] or not cols[i - 1]["end"]:
            out.append(None)
            continue
        gap = years_between(cols[i - 1]["end"], cols[i]["end"])
        if not 0.85 <= gap <= 1.15:
            out.append(None)
            continue
        a, b = vals[i - 1], vals[i]
        if a > 0:
            out.append({"pct": (b - a) / a, "abs": b - a, "transition": "profit->loss" if b < 0 else None})
        else:
            tr = ("loss->profit" if b > 0 and a < 0 else "zero baseline" if a == 0 else "loss->larger/smaller loss")
            out.append({"pct": None, "abs": b - a, "transition": tr})
    return out


def pp_change(m0, m1):
    return None if (m0 is None or m1 is None) else (m1 - m0) * 100


def compare_years(raw_statements: dict, canon_cols: list[dict], k0: str, k1: str) -> dict:
    """Every reported line item side-by-side for two fiscal-year end dates (Yahoo labels preserved)."""
    res = {}
    for st in ("income", "balance", "cashflow"):
        rows = []
        for lab, vals in raw_statements.get(st, {}).items():
            a, b = vals.get(k0), vals.get(k1)
            if a is None and b is None and k0 not in vals and k1 not in vals:
                continue
            row = {"label": lab, "a": a, "b": b, "abs": None, "pct": None, "note": None}
            if a is not None and b is not None:
                row["abs"] = b - a
                if a > 0:
                    row["pct"] = (b - a) / a
                elif a == 0:
                    row["note"] = "zero baseline"
                else:
                    row["note"] = "loss->profit" if b > 0 else "negative baseline"
                if a > 0 and b < 0:
                    row["note"] = "profit->loss"
            elif a is None or b is None:
                row["note"] = "missing in one year (N/A)"
            rows.append(row)
        res[st] = rows
    return res


# ---------------------------- CSV import --------------------------------------------------
IMPORT_ALIASES = {"totalrevenue": "income", "operatingincome": "income", "netincome": "income", "dilutedeps": "income",
                  "grossprofit": "income", "costofrevenue": "income", "researchanddevelopment": "income",
                  "totalassets": "balance", "totaldebt": "balance", "operatingcashflow": "cashflow",
                  "capitalexpenditure": "cashflow", "freecashflow": "cashflow"}
UNIT_FACTORS = {"units": 1.0, "thousands": 1e3, "millions": 1e6}
_PERIOD = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$|^(\d{4})-(\d{2})-(\d{2})$")


def _parse_period(h: str):
    m = _PERIOD.match(h.strip())
    if not m:
        return None
    if m.group(1):
        return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return date(int(m.group(4)), int(m.group(5)), int(m.group(6)))


def _statement_for(label: str, hint: str | None):
    if hint in ("income", "balance", "cashflow"):
        return hint
    return IMPORT_ALIASES.get(norm(label))


def parse_import(text: str, ticker: str, csv_ticker: str | None, currency: str, units: str, statement: str | None,
                 yahoo_currency: str | None, existing_canon_raw: dict) -> dict:
    """Validate a Yahoo Finance annual CSV export. Returns {ok, errors, warnings, conflicts, statements, summary}."""
    errors, warnings = [], []
    if units not in UNIT_FACTORS:
        errors.append(f"Units must be one of {list(UNIT_FACTORS)}; got {units!r}")
    if csv_ticker and csv_ticker.strip().upper() != ticker.upper():
        errors.append(f"Ticker mismatch: file says {csv_ticker.strip().upper()}, target is {ticker.upper()}")
    if yahoo_currency and currency.upper() != yahoo_currency.upper():
        errors.append(f"Currency mismatch: import is {currency.upper()} but Yahoo reports {yahoo_currency.upper()} "
                      "(refusing to mix currencies)")
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if len(rows) < 2:
        return {"ok": False, "errors": errors + ["CSV has no data rows"], "warnings": warnings, "conflicts": [],
                "statements": {}, "summary": {}}
    header = [h.strip() for h in rows[0]]
    period_cols = []
    seen = set()
    for i, h in enumerate(header[1:], 1):
        if h.lower() in ("ttm", "trailing"):
            warnings.append("TTM column ignored (annual data only)")
            continue
        p = _parse_period(h)
        if p is None:
            warnings.append(f"Column '{h}' is not a period date; ignored")
            continue
        if p in seen:
            errors.append(f"Duplicate period column {p}")
        seen.add(p)
        period_cols.append((i, p))
    if not period_cols:
        errors.append("No annual period columns found (expected e.g. 12/31/2019)")
    ps = sorted(p for _, p in period_cols)
    for a, b in zip(ps, ps[1:]):
        gap = (b - a).days
        if not 340 <= gap <= 390:
            errors.append(f"Periods {a} and {b} are {gap} days apart - not consecutive annual periods "
                          "(quarterly or non-annual export?)")
    if ps and ps[-1] > date.today():
        errors.append(f"Period {ps[-1]} is in the future")
    factor = UNIT_FACTORS.get(units, 1.0)
    out: dict = {"income": {}, "balance": {}, "cashflow": {}}
    labels_seen = set()
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        lab = r[0].strip()
        if norm(lab) in labels_seen:
            errors.append(f"Duplicate line item '{lab}'")
            continue
        labels_seen.add(norm(lab))
        st = _statement_for(lab, statement)
        if st is None:
            warnings.append(f"Line '{lab}': statement unknown (choose a statement type); skipped")
            continue
        per_share = "eps" in norm(lab) or "pershare" in norm(lab) or "shares" in norm(lab)
        vals = {}
        for i, p in period_cols:
            if i >= len(r):
                continue
            cell = r[i].strip().replace(",", "")
            if cell in ("", "--", "-", "N/A", "nan"):
                continue  # missing, NOT zero
            try:
                v = float(cell)
            except ValueError:
                errors.append(f"Non-numeric value '{cell}' for {lab} {p}")
                continue
            vals[str(p)] = v if per_share else v * factor
        if vals:
            out[st][lab] = vals
    conflicts = []
    for st, rws in out.items():
        for lab, vals in rws.items():
            ex = existing_canon_raw.get(st, {}).get(lab, {})
            for dte, v in vals.items():
                ev = ex.get(dte)
                if ev is not None and abs(ev - v) > max(1e-6, 0.005 * abs(ev)):
                    conflicts.append({"statement": st, "label": lab, "period": dte, "yahoo": ev, "imported": v})
    summary = {"periods": [str(p) for p in ps],
               "rows": {st: len(r) for st, r in out.items()}, "conflicts": len(conflicts)}
    return {"ok": not errors, "errors": errors, "warnings": warnings, "conflicts": conflicts,
            "statements": out, "summary": summary}
