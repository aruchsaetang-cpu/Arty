import pytest
from dashboard import fundamentals as F, yahoo

COLS = [{"slot": i, "label": f"FY{2022+i}", "end": f"{2022+i}-12-31", "available": True} for i in range(4)]


def test_capex_sign_normalised_and_fcf_deducted_once():
    raw = {"income": {"Total Revenue": {"2024-12-31": 100.0}}, "balance": {},
           "cashflow": {"Operating Cash Flow": {"2024-12-31": 30.0}, "Capital Expenditure": {"2024-12-31": -12.0}}}
    c = F.canonical(raw)
    cols = F.make_columns(["2024-12-31"])
    d = F.derive(c, cols)
    assert d["capex_abs"][-1] == 12.0 and d["fcf"][-1] == 18.0
    raw["cashflow"]["Capital Expenditure"]["2024-12-31"] = 12.0           # positive-signed source
    d = F.derive(F.canonical(raw), cols)
    assert d["fcf"][-1] == 18.0


def test_capex_fallback_matches_yahoo_fcf_definition():
    raw = {"income": {}, "balance": {}, "cashflow": {"Operating Cash Flow": {"2023-12-31": 5992.0},
           "Purchase Of PPE": {"2023-12-31": -4439.0}, "Purchase Of Intangibles": {"2023-12-31": -97.0}}}
    c = F.canonical(raw)
    assert c["capex"]["2023-12-31"] == -4536.0
    d = F.derive(c, F.make_columns(["2023-12-31"]))
    assert d["fcf"][-1] == pytest.approx(1456.0)       # == Yahoo's reported FreeCashFlow for STM FY2023


def test_zero_is_not_missing():
    d = F.derive(F.canonical({"income": {"Total Revenue": {"2024-12-31": 0.0}, "Research And Development": {"2024-12-31": 0.0}},
                              "balance": {}, "cashflow": {}}), F.make_columns(["2024-12-31"]))
    assert d["rnd"][-1] == 0.0 and d["rnd"][-2] is None


def test_ten_columns_with_gaps():
    cols = F.make_columns(["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"])
    assert len(cols) == 10 and [c["label"] for c in cols][0] == "FY2016" and cols[-1]["label"] == "FY2025"
    assert sum(c["available"] for c in cols) == 4


def test_cagr_uses_elapsed_years_and_handles_bad_baseline():
    g, _ = F.cagr(100, 121, "2022-12-31", "2024-12-31")
    assert g == pytest.approx(0.10, abs=1e-3)
    g, why = F.cagr(100, 150, "2022-12-31", "2025-06-30")                # 2.5 years, not 3 columns
    assert g == pytest.approx((1.5) ** (1 / 2.4959) - 1, abs=1e-4)
    assert F.cagr(-5, 10, "2022-12-31", "2025-12-31") == (None, "baseline zero/negative")
    assert F.cagr(0, 10, "2022-12-31", "2025-12-31")[0] is None


def test_yoy_consecutive_only_and_transitions():
    cols = [{"end": "2021-12-31"}, {"end": "2022-12-31"}, {"end": "2024-12-31"}, {"end": "2025-12-31"}, {"end": "2026-12-31"}]
    y = F.yoy([10, -5, 3, 4, None], cols)
    assert y[1]["transition"] == "profit->loss" and y[1]["pct"] == pytest.approx(-1.5)
    assert y[2] is None                                   # 2022 -> 2024 not consecutive
    assert y[3]["pct"] == pytest.approx(1 / 3)
    assert y[4] is None
    z = F.yoy([-5, 3], cols[:2])
    assert z[1]["pct"] is None and z[1]["transition"] == "loss->profit" and z[1]["abs"] == 8


def test_margin_change_in_percentage_points():
    assert F.pp_change(0.20, 0.25) == pytest.approx(5.0)
    assert F.pp_change(None, 0.2) is None


CSV = "name,ttm,12/31/2019,12/31/2018\nTotal Revenue,100,\"1,000\",900\nNet Income,1,100,--\n"

def test_import_validation():
    ok = F.parse_import(CSV, "STM", None, "USD", "thousands", "income", "USD", {"income": {}})
    assert ok["ok"] and ok["statements"]["income"]["Total Revenue"]["2019-12-31"] == 1_000_000
    assert "2018-12-31" not in ok["statements"]["income"]["Net Income"]       # '--' = missing, not zero
    assert not F.parse_import(CSV, "STM", "AAPL", "USD", "units", "income", "USD", {})["ok"]          # ticker mismatch
    assert not F.parse_import(CSV, "STM", None, "EUR", "units", "income", "USD", {})["ok"]            # currency mismatch
    assert not F.parse_import(CSV, "STM", None, "USD", "furlongs", "income", "USD", {})["ok"]         # bad units
    q = "name,3/31/2019,6/30/2019\nTotal Revenue,1,2\n"
    assert not F.parse_import(q, "STM", None, "USD", "units", "income", "USD", {})["ok"]              # quarterly gap
    dup = "name,12/31/2019,12/31/2019\nTotal Revenue,1,2\n"
    assert not F.parse_import(dup, "STM", None, "USD", "units", "income", "USD", {})["ok"]
    dl = "name,12/31/2019\nTotal Revenue,1\nTotal Revenue,2\n"
    assert not F.parse_import(dl, "STM", None, "USD", "units", "income", "USD", {})["ok"]
    conflict = F.parse_import(CSV, "STM", None, "USD", "units", "income", "USD", {"income": {"Total Revenue": {"2019-12-31": 5.0}}})
    assert conflict["conflicts"] and conflict["conflicts"][0]["yahoo"] == 5.0


def test_imported_values_fill_gaps_only_unless_overridden():
    st = {"income": {"Total Revenue": {"2024-12-31": 10.0}}, "balance": {}, "cashflow": {}}
    imp = {"statements": {"income": {"Total Revenue": {"2024-12-31": 99.0, "2015-12-31": 7.0}}, "balance": {}, "cashflow": {}}, "override": []}
    m = F.merged_raw(st, imp)["statements"]["income"]["Total Revenue"]
    assert m["2024-12-31"] == 10.0 and m["2015-12-31"] == 7.0
    imp["override"] = [["income", "Total Revenue", "2024-12-31"]]
    assert F.merged_raw(st, imp)["statements"]["income"]["Total Revenue"]["2024-12-31"] == 99.0


def test_quote_labels_real_time_only_when_yahoo_confirms():
    base = {"regularMarketPrice": 10, "regularMarketPreviousClose": 9, "regularMarketTime": 1795640402, "marketState": "REGULAR"}
    assert yahoo.quote_from_info({**base, "exchangeDataDelayedBy": 0})["price_label"] == "Real-time"
    assert yahoo.quote_from_info({**base, "exchangeDataDelayedBy": 20})["price_label"] == "Delayed 20 min"
    assert yahoo.quote_from_info(base)["price_label"] == "Latest available"
    q = yahoo.quote_from_info({**base, "preMarketPrice": 10.5, "preMarketTime": 1795640402})
    assert q["pre_market"]["change_vs_regular_close"] == pytest.approx(0.5)      # measured against the regular close
