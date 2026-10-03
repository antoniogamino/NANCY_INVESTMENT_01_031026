from datetime import date

from app.engines.decay import opportunity_decay
from app.engines.scoring import classify, instrument_structure
from app.engines.technicals import rsi


def test_decay_user_example_100_118_124():
    d = opportunity_decay(100, 118, 124, 10, "BUY")
    assert round(d["move_before_disclosure"] * 100, 1) == 18.0
    assert round(d["move_after_disclosure"] * 100, 1) == 5.1
    assert round(d["move_total"] * 100, 1) == 24.0


def test_decay_nvda_120_138_145():
    d = opportunity_decay(120, 138, 145, 52, "BUY")
    assert round(d["move_before_disclosure"] * 100, 1) == 15.0
    assert round(d["move_after_disclosure"] * 100, 2) == 5.07
    assert round(d["move_total"] * 100, 2) == 20.83
    assert 0 <= d["score"] <= 100


def test_decay_sell_is_mirrored():
    d = opportunity_decay(100, 90, 85, 5, "SELL")
    assert d["favourable_before"] > 0 and d["favourable_after"] > 0


def test_classification_thresholds():
    assert classify(80)[0] == "STRONG WATCH"
    assert classify(65)[0] == "INTERESTING"
    assert classify(50)[0] == "NEUTRAL"
    assert classify(35)[0] == "WEAK"
    assert classify(34.9)[0] == "AVOID / LOW RELEVANCE"


def test_instrument_expired_option():
    i = instrument_structure("leaps_call", 100, date(2020, 1, 17), date(2018, 1, 1), 150, date(2026, 1, 1))
    assert i["score"] == 20 and "EXPIRED" in i["nature"]


def test_rsi_bounds():
    up = [float(i) for i in range(1, 60)]
    assert rsi(up) == 100.0
