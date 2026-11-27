from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import assess as A
from . import config as C
from . import detail, fundamentals as F, jobs, market, membership, quality as Q, service, yahoo
from . import valuation as V
from .store import store


@asynccontextmanager
async def lifespan(app):
    if os.environ.get("DASH_JOBS", "1") == "1":
        jobs.start()
    yield
    jobs._stop.set()


app = FastAPI(title="Stock research dashboard", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
POOL = ThreadPoolExecutor(4)


def clean(o):
    """JSON-safe: NaN/inf -> None."""
    import math
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def ok(data):
    return JSONResponse(clean(data))


@app.get("/api/health")
def health():
    return {"ok": True, "now_et": market.fmt_ny(time.time()), "model_version": C.MODEL_VERSION}


@app.get("/api/meta")
def meta():
    m = membership.load_membership()
    return ok({"model_version": C.MODEL_VERSION, "default_required_mos": C.DEFAULT_REQUIRED_MOS, "session": market.session_state(),
               "membership": service._mem_meta(m), "sources": C.SOURCES, "principles": C.PRINCIPLES,
               "label_boundaries": V.label_boundaries(), "confidence_rules": V.CONFIDENCE_RULES, "ranking_explanation": service.RANK_EXPLANATION,
               "quality_rules": {k: [{"key": a, "name": b, "rule": c} for a, b, c in v] for k, v in Q.RULES.items()},
               "quality_label_rule": Q.LABEL_RULE, "rf": service.risk_free(), "jobs": jobs.status(),
               "discount_rule": f"Discount rate = 10y Treasury yield (Yahoo ^TNX) + beta (clipped {C.BETA_CLIP[0]}-{C.BETA_CLIP[1]}) x {C.EQUITY_RISK_PREMIUM:.0%} equity risk premium, floored at {C.DISCOUNT_FLOOR:.0%} and capped at {C.DISCOUNT_CAP:.0%}.",
               "formulas": {"margin_of_safety": "(base fair value - price) / base fair value", "upside": "(base fair value - price) / price",
                            "watch_price": "base fair value x (1 - required margin of safety)"}})


@app.get("/api/shortlist")
def api_shortlist(mos: float = Query(C.DEFAULT_REQUIRED_MOS, ge=0, le=0.9)):
    return ok(service.shortlist(mos))


@app.get("/api/universe")
def api_universe(mos: float = Query(C.DEFAULT_REQUIRED_MOS, ge=0, le=0.9), extra: str = ""):
    """All S&P 500 securities, plus (separately flagged, excluded from coverage/ranking) extra tickers such as STM or holdings."""
    rows, m = service.universe_rows(mos)
    idx = {r["ticker"] for r in rows}
    wanted = ["STM"] + [service.norm_ticker(t) for t in extra.split(",") if t.strip()]
    extras = []
    for t in dict.fromkeys(wanted):
        if t not in idx:
            r = service.row_for(t, None, mos)
            r["extra"] = True
            extras.append(service._strip(r))
    return ok({"rows": [service._strip(r) for r in rows], "extra_rows": extras, "coverage": service.coverage(rows),
               "membership": service._mem_meta(m), "as_of": market.fmt_ny(time.time())})


@app.get("/api/summaries")
def api_summaries(tickers: str, mos: float = Query(C.DEFAULT_REQUIRED_MOS, ge=0, le=0.9)):
    """Rows for arbitrary tickers (holdings), analysing any that are not yet cached - regardless of index membership."""
    ts = [service.norm_ticker(t) for t in tickers.split(",") if t.strip()][:200]
    members = {m["ticker"]: m for m in membership.load_membership()["members"]}
    need = [t for t in ts if not store().val(f"summ:{t}")]

    def go(t):
        try:
            service.analyze(t)
        except Exception:  # noqa: BLE001
            pass
    list(POOL.map(go, need[:12]))
    rows = [service._strip(service.row_for(t, members.get(t), mos)) for t in ts]
    return ok({"rows": rows, "as_of": market.fmt_ny(time.time())})


@app.get("/api/search")
def search(q: str):
    qn = q.strip()
    if not qn:
        return ok({"results": []})
    ql = qn.lower()
    members = membership.load_membership()["members"]
    res = []
    for m in members:
        t = m["ticker"]
        score = 0 if t.lower() == ql else 1 if t.lower().startswith(ql) else 2 if ql in (m.get("name") or "").lower() else None
        if score is not None:
            res.append((score, t, m))
    res.sort(key=lambda x: (x[0], x[1]))
    out = [{"ticker": t, "name": m.get("name"), "in_index": True, "sector": m.get("sector")} for _, t, m in res[:20]]
    tk = service.norm_ticker(qn)
    if re.fullmatch(r"[A-Z0-9\-\^=]{1,10}", tk) and not any(r["ticker"] == tk for r in out):
        out.insert(0, {"ticker": tk, "name": None, "in_index": False, "external": True})
    if len(out) < 3:
        try:
            import yfinance as yf
            for x in (yf.Search(qn, max_results=6).quotes or []):
                if x.get("quoteType") == "EQUITY" and not any(r["ticker"] == x["symbol"] for r in out):
                    out.append({"ticker": x["symbol"], "name": x.get("longname") or x.get("shortname"), "in_index": x["symbol"] in {m["ticker"] for m in members},
                                "external": True})
        except Exception:  # noqa: BLE001
            pass
    return ok({"results": out})


@app.get("/api/stock/{ticker}")
def api_stock(ticker: str, mos: float = Query(C.DEFAULT_REQUIRED_MOS, ge=0, le=0.9)):
    try:
        return ok(detail.build(ticker, mos))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Could not analyse {ticker}: {type(e).__name__}: {str(e)[:160]}")


@app.get("/api/quote/{ticker}")
def api_quote(ticker: str, force: bool = False):
    t = service.norm_ticker(ticker)
    try:
        q = service.load_quote(t, force=force)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Quote refresh failed: {type(e).__name__}")
    if not q:
        raise HTTPException(404, "No quote")
    return ok(q)


@app.get("/api/pricing/{ticker}")
def api_pricing(ticker: str, mos: float = Query(C.DEFAULT_REQUIRED_MOS, ge=0, le=0.9), force: bool = False):
    """Light endpoint for the 60-second refresh and for threshold changes: quote + price-dependent metrics only."""
    t = service.norm_ticker(ticker)
    a = service.get_assessment(t)
    try:
        q = service.load_quote(t, force=force)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Quote refresh failed: {type(e).__name__}")
    pv = A.price_view(a, q, mos)
    return ok({"quote": q, "price_view": pv, "reverse": A.reverse(a, pv["price"]) if pv["price"] else None,
               "narrative": A.thesis(a, pv), "session": market.session_state()})


@app.get("/api/ceo/{ticker}")
def api_ceo(ticker: str):
    t = service.norm_ticker(ticker)
    info = store().val(f"info:{t}") or {}
    return ok({**detail.ceo_block(t, info), "news": detail.ceo_news(t)})


@app.get("/api/extra/{ticker}")
def api_extra(ticker: str):
    t = service.norm_ticker(ticker)
    return ok({"trailing_and_estimates": detail.trailing_and_estimates(t), "news": detail.news(t)})


class ValBody(BaseModel):
    overrides: dict = {}
    mos: float = C.DEFAULT_REQUIRED_MOS


@app.post("/api/valuation/{ticker}")
def api_valuation(ticker: str, body: ValBody):
    t = service.norm_ticker(ticker)
    a = service.get_assessment(t)
    q = service.load_quote(t)
    try:
        res = A.custom_valuation(a, body.overrides, q["price"] if q else None, body.mos)
    except ValueError as e:
        raise HTTPException(422, str(e))
    res["reverse"] = None
    return ok(res)


@app.get("/api/compare/{ticker}")
def api_compare(ticker: str, a: str, b: str):
    t = service.norm_ticker(ticker)
    info = store().val(f"info:{t}") or {}
    merged, canon, cols, d = A.build_tables(info, store().val(f"fund:{t}"), service.load_import(t))
    return ok({"a": a, "b": b, "rows": F.compare_years(merged["statements"], cols, a, b)})


@app.post("/api/import/{ticker}")
async def api_import(ticker: str, file: UploadFile = File(...), currency: str = Form(...), units: str = Form("units"),
                     statement: str = Form(""), commit: bool = Form(False), resolve: str = Form("")):
    t = service.norm_ticker(ticker)
    info = service.load_info(t, max_age=None)
    text = (await file.read()).decode("utf-8", errors="replace")
    m = re.match(r"^([A-Z]{1,5}(?:-[A-Z])?)[_\-. ]", file.filename or "")
    existing = A.build_tables(info, service.load_statements(t, max_age=None), service.load_import(t))[0]["statements"]
    res = F.parse_import(text, t, m.group(1) if m else None, currency, units, statement or None, info.get("financialCurrency"), existing)
    if not commit:
        return ok({**res, "committed": False})
    if not res["ok"]:
        raise HTTPException(422, {"errors": res["errors"]})
    if res["conflicts"] and resolve not in ("keep_yahoo", "prefer_import"):
        raise HTTPException(409, {"conflicts": res["conflicts"], "message": "Imported figures conflict with existing data. Choose keep_yahoo or prefer_import."})
    cur = service.load_import(t) or {"statements": {"income": {}, "balance": {}, "cashflow": {}}, "files": [], "override": []}
    for st, rows in res["statements"].items():
        for lab, vals in rows.items():
            cur["statements"][st].setdefault(lab, {}).update(vals)
    if resolve == "prefer_import":
        cur["override"] = cur.get("override", []) + [[c["statement"], c["label"], c["period"]] for c in res["conflicts"]]
    cur["files"].append({"name": file.filename, "uploaded_at": market.fmt_ny(time.time()), "periods": res["summary"]["periods"],
                         "rows": res["summary"]["rows"], "currency": currency, "units": units, "conflicts_resolved": resolve or None})
    store().set(f"import:{t}", cur)
    a = service.build_assessment(t)
    return ok({**res, "committed": True, "years_now": a["years"], "confidence": a["valuation"].get("confidence", {}).get("level")})


@app.delete("/api/import/{ticker}")
def api_import_clear(ticker: str):
    t = service.norm_ticker(ticker)
    store().delete(f"import:{t}")
    service.build_assessment(t)
    return {"ok": True}


@app.post("/api/membership/import")
async def api_membership_import(file: UploadFile = File(...)):
    try:
        m = membership.import_official(await file.read(), file.filename or "sp500.xlsx")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, f"{type(e).__name__}: {e}")
    return ok(service._mem_meta(m))


@app.post("/api/jobs/{job}")
def run_job(job: str, force: bool = False):
    import threading
    if job == "quotes":
        threading.Thread(target=jobs.refresh_quotes, daemon=True).start()
    elif job == "fundamentals":
        threading.Thread(target=jobs.refresh_fundamentals, kwargs={"force": force}, daemon=True).start()
    elif job == "reassess":
        return {"reassessed": jobs.reassess_cached()}
    else:
        raise HTTPException(404, "unknown job")
    return {"started": job}


@app.get("/api/jobs")
def api_jobs():
    return ok(jobs.status())


DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
