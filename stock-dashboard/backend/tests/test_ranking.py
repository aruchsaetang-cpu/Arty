"""Shortlist rules: expensive high-quality and stale-quote stocks can never qualify; ownership never changes rank."""
from dashboard import assess as A


def fake(quality="Strong", conf="medium", fv=(60.0, 100.0, 140.0), usable=True, score=100):
    return {"quality": {"label": quality, "score": score, "pillars": [], "reason": None},
            "valuation": {"usable": usable, "confidence": {"level": conf},
                          "scenarios": {k: {"fair_value": v} for k, v in zip(("bear", "base", "bull"), fv)}}}

def quote(price, status="current"):
    return {"price": price, "freshness": {"status": status, "reason": "x"}}


def test_cheap_strong_current_qualifies():
    pv = A.price_view(fake(), quote(75), 0.20)
    assert pv["qualifies"] and pv["margin_of_safety"] == 0.25 and pv["valuation_label"] == "Undervalued"


def test_expensive_high_quality_cannot_qualify():
    pv = A.price_view(fake(), quote(130), 0.20)
    assert not pv["qualifies"] and pv["valuation_label"] == "Expensive"
    assert any("20% below" in m for m in pv["missed"])


def test_modestly_undervalued_but_short_of_requirement():
    pv = A.price_view(fake(), quote(88), 0.20)
    assert pv["valuation_label"] == "Undervalued" and not pv["qualifies"]
    assert A.price_view(fake(), quote(88), 0.10)["qualifies"]          # editable preference


def test_stale_quote_cannot_qualify():
    pv = A.price_view(fake(), quote(50, "stale"), 0.20)
    assert not pv["qualifies"] and pv["missed"] == ["Quote is current for the trading session"]


def test_delayed_intraday_quote_is_allowed_but_flagged():
    assert A.price_view(fake(), quote(75, "delayed"), 0.20)["qualifies"]


def test_low_confidence_or_non_strong_fail():
    assert not A.price_view(fake(conf="low"), quote(60), 0.2)["qualifies"]
    assert not A.price_view(fake(quality="Mixed"), quote(60), 0.2)["qualifies"]
    assert not A.price_view(fake(usable=False), quote(60), 0.2)["qualifies"]


def test_ranking_order_confidence_then_bear_discount_then_quality():
    rows = {
        "A": A.price_view(fake(conf="medium", fv=(90, 100, 120), score=90), quote(70), 0.2),      # bear discount 22%
        "B": A.price_view(fake(conf="high", fv=(72, 100, 120), score=80), quote(70), 0.2),        # high conf, bear 2.8%
        "C": A.price_view(fake(conf="medium", fv=(90, 100, 120), score=100), quote(70), 0.2),     # same as A, better quality
        "D": A.price_view(fake(conf="medium", fv=(0, 100, 120), score=100), quote(70), 0.2),      # bear <= 0 -> last of medium
    }
    order = sorted(rows, key=lambda k: A.rank_key(rows[k]))
    assert order == ["B", "C", "A", "D"]
