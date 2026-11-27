"""Integration: CSV import preview/commit/conflicts through the real API, against an ISOLATED temp store seeded with
SYNTHETIC test-only figures (ticker TESTCO). Never touches the real cache."""
import io, time
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import dashboard.store as S
    monkeypatch.setattr(S, "_store", S.Store(tmp_path / "t.db"))
    from dashboard import service
    st = S.store()
    st.set("rf", {"rate": 0.045, "as_of": "2026-11-25", "source": "test"})
    st.set("membership", {"members": [{"ticker": "TESTCO", "name": "Test Co", "sector": "Tech"}], "source": "wikipedia", "verified": False,
                          "label": "test", "url": "x", "as_of": "2026-11-27"})
    dates = ["2018-12-31", "2019-12-31", "2020-12-31", "2021-12-31"]
    def row(vals): return dict(zip(dates, vals))
    fund = {"fetched_at": time.time(), "income": {
        "Total Revenue": row([1000e6, 1100e6, 1210e6, 1331e6]), "Operating Income": row([200e6, 220e6, 242e6, 266e6]),
        "Net Income": row([150e6, 165e6, 180e6, 200e6]), "Diluted EPS": row([1.5, 1.65, 1.8, 2.0]),
        "Diluted Average Shares": row([100e6] * 4), "Tax Rate For Calcs": row([.21] * 4)},
        "balance": {"Stockholders Equity": row([600e6, 650e6, 700e6, 760e6]), "Total Debt": row([100e6] * 4),
                    "Cash Cash Equivalents And Short Term Investments": row([200e6] * 4), "Total Assets": row([900e6] * 4)},
        "cashflow": {"Operating Cash Flow": row([230e6, 250e6, 270e6, 300e6]), "Capital Expenditure": row([-40e6] * 4),
                     "Depreciation And Amortization": row([40e6] * 4)}}
    info = {"longName": "Test Co", "symbol": "TESTCO", "currency": "USD", "financialCurrency": "USD", "sector": "Technology", "industry": "Software",
            "beta": 1.0, "sharesOutstanding": 100e6, "regularMarketPrice": 20.0, "_fetched_at": time.time()}
    st.set("fund:TESTCO", fund); st.set("info:TESTCO", info)
    st.set("quote:TESTCO", {"price": 20.0, "previous_close": 19.0, "regular_time_epoch": int(time.time()) - 60, "delay_minutes": 20, "price_label": "Delayed 20 min", "source": "Yahoo Finance via yfinance"})
    from dashboard.app import app
    return TestClient(app)


def csv(rows, cols):
    return "name," + ",".join(cols) + "\n" + "\n".join(f"{n}," + ",".join(str(v) for v in vals) for n, vals in rows) + "\n"


def post(c, text, commit=False, resolve="", statement="income", currency="USD", units="thousands", name="TESTCO_income.csv"):
    return c.post("/api/import/TESTCO", files={"file": (name, io.BytesIO(text.encode()), "text/csv")},
                  data={"currency": currency, "units": units, "statement": statement, "commit": str(commit).lower(), "resolve": resolve})


def test_import_extends_history_and_confidence(client):
    before = client.get("/api/stock/TESTCO").json()
    assert before["valuation"]["confidence"]["breakdown"][0]["points"] == 1       # 4 years -> coverage 1/2
    older = ["12/31/2017", "12/31/2016", "12/31/2015", "12/31/2014"]
    inc = csv([("Total Revenue", [909091, 826446, 751315, 683013]), ("Operating Income", [181818, 165289, 150263, 136603]),
               ("Net Income", [136364, 123967, 112697, 102460]), ("Diluted EPS", [1.36, 1.24, 1.13, 1.02]),
               ("Diluted Average Shares", [100000000] * 4)], older)
    bal = csv([("Stockholders Equity", [560000, 520000, 480000, 440000]), ("Total Debt", [100000] * 4),
               ("Cash Cash Equivalents And Short Term Investments", [200000] * 4), ("Total Assets", [900000] * 4)], older)
    cf = csv([("Operating Cash Flow", [210000, 190000, 175000, 160000]), ("Capital Expenditure", [-40000] * 4),
              ("Depreciation And Amortization", [40000] * 4)], older)
    r = post(client, inc)
    assert r.status_code == 200 and r.json()["ok"] and not r.json()["committed"]
    for text, st in ((inc, "income"), (bal, "balance"), (cf, "cashflow")):
        r = post(client, text, commit=True, statement=st)
        assert r.status_code == 200, r.text
    after = client.get("/api/stock/TESTCO").json()
    assert sum(c["available"] for c in after["columns"]) == 8
    assert after["valuation"]["confidence"]["breakdown"][0]["points"] == 2        # >= 8 years -> coverage 2/2
    rev = next(r for r in after["tables"]["income"]["spec"] if r["key"] == "revenue")
    assert rev["values"][-8] == pytest.approx(683013e3)                           # FY2014 filled from the import (thousands -> units)
    imp = [r for r in after["tables"]["income"]["detail"] if r["label"] == "Total Revenue"][0]
    assert imp["imported"][-8] is True and imp["imported"][-1] is False


def test_conflicts_require_a_decision_and_yahoo_wins_by_default(client):
    conflict = csv([("Total Revenue", [999999])], ["12/31/2021"])                 # Yahoo says 1,331,000 thousands
    pre = post(client, conflict).json()
    assert pre["ok"] and len(pre["conflicts"]) == 1
    assert post(client, conflict, commit=True).status_code == 409
    assert post(client, conflict, commit=True, resolve="keep_yahoo").status_code == 200
    rev = lambda: next(r for r in client.get("/api/stock/TESTCO").json()["tables"]["income"]["spec"] if r["key"] == "revenue")["values"][-1]
    assert rev() == pytest.approx(1331e6)
    assert post(client, conflict, commit=True, resolve="prefer_import").status_code == 200
    assert rev() == pytest.approx(999999e3)


def test_rejects_bad_files(client):
    assert post(client, csv([("Total Revenue", [1])], ["12/31/2017"]), currency="EUR").status_code == 200
    assert post(client, csv([("Total Revenue", [1])], ["12/31/2017"]), currency="EUR").json()["ok"] is False
    assert post(client, csv([("Total Revenue", [1])], ["12/31/2017"]), commit=True, currency="EUR").status_code == 422
    r = post(client, csv([("Total Revenue", [1])], ["12/31/2017"]), name="AAPL_income.csv").json()
    assert not r["ok"] and "Ticker mismatch" in r["errors"][0]
    q = post(client, csv([("Total Revenue", [1, 2])], ["3/31/2017", "6/30/2017"])).json()
    assert not q["ok"]


def test_ownership_is_not_a_backend_concept(client):
    # ranking endpoints take no holdings input at all: ownership cannot influence valuation or rank
    import inspect
    from dashboard import service
    assert "hold" not in inspect.getsource(service.shortlist).lower() and "owned" not in inspect.getsource(service.row_for).lower()
