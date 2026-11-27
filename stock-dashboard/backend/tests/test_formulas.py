import pytest
from dashboard import valuation as V, assess as A


def test_spec_example_80_vs_100():
    assert V.margin_of_safety(100, 80) == pytest.approx(0.20)
    assert V.upside_to_fair_value(100, 80) == pytest.approx(0.25)
    assert V.watch_price(100, 0.20) == pytest.approx(80)
    assert V.decline_to_watch(90, 80) == pytest.approx(10 / 90)
    assert V.decline_to_watch(80, 80) is None and V.decline_to_watch(70, 80) is None


def test_labels_and_buy_threshold_are_separate():
    # 12% margin of safety: Undervalued, yet short of a 20% requirement
    assert V.valuation_label(100, 88, "medium") == "Undervalued"
    m = A.price_metrics(100, 88, 0.20)
    assert m["meets_required_mos"] is False
    assert V.valuation_label(100, 95, "medium") == "Moderate / Fairly valued"
    assert V.valuation_label(100, 120, "medium") == "Expensive"      # MoS -20%
    assert V.valuation_label(100, 110, "medium") == "Moderate / Fairly valued"  # MoS -10%
    assert V.valuation_label(100, 80, "insufficient") == "Insufficient evidence"
    assert V.valuation_label(-5, 80, "medium") == "Insufficient evidence"


def test_dcf_recomputes_by_hand():
    p = dict(revenue0=1000.0, g1=0.0, g_term=0.0, margin_start=0.2, margin_target=0.2, ramp_years=0, tax=0.25,
             capex_start=0.05, capex_target=0.05, capex_ramp_years=0, da_pct=0.05, nwc_pct=0.0, r=0.10, net_debt=0.0, shares=10.0)
    out = V.dcf_operating(p)
    fcf = 1000 * 0.2 * 0.75                      # 150, flat
    pv = sum(fcf / 1.1 ** t for t in range(1, 11)) + fcf / 0.10 / 1.1 ** 10
    assert out["enterprise_value"] == pytest.approx(pv)
    assert out["per_share"] == pytest.approx(pv / 10)
    assert V.epv_operating(p) == pytest.approx(150 / 0.10 / 10)


def test_pb_and_reit_closed_forms():
    assert V.pb_financial(dict(bvps=50, roe=0.12, g=0.02, r=0.10)) == pytest.approx(50 * 0.10 / 0.08)
    assert V.affo_reit(dict(affo_ps=4.0, g=0.02, r=0.08)) == pytest.approx(4 * 1.02 / 0.06)


def test_confidence_rules():
    c = V.confidence(4, 2, 0.3, True, [])
    assert c["level"] == "medium" and c["points"] == 6         # 6 points but only 4 years -> never High
    assert V.confidence(10, 2, 0.3, True, [])["level"] == "high"
    assert V.confidence(4, 0, 2.0, False, [])["level"] == "low"
    assert V.confidence(4, 2, 0.3, True, ["currency"])["level"] == "insufficient"


def test_bisect_reverse():
    assert V.bisect(lambda x: x * 2, 0, 10, 8) == pytest.approx(4)
    assert V.bisect(lambda x: x, 0, 1, 5) is None
