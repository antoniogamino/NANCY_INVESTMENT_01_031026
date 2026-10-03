"""TRADE INTELLIGENCE SCORE (0-100).

Measures how *relevant* a disclosed trade still is today — it is NOT a buy/sell signal.
Ten factors (A-J) plus Opportunity Decay (K) are scored 0-100 and combined by weight.
Directional factors are mirrored for SELL disclosures (e.g. weak momentum makes a
disclosed sale *more* relevant). An age discount is applied to old disclosures.
"""
from __future__ import annotations

from datetime import date

from .util import clamp, direction, interp, pct

WEIGHTS = {
    "A_delay": 8, "B_drift": 12, "C_valuation": 10, "D_momentum": 12, "E_technical": 12,
    "F_analyst": 8, "G_earnings": 6, "H_sector": 8, "I_market": 8, "J_instrument": 8, "K_decay": 8,
}
LABELS = {
    "A_delay": "Disclosure Delay", "B_drift": "Price Drift", "C_valuation": "Valuation Context",
    "D_momentum": "Momentum", "E_technical": "Technical Position", "F_analyst": "Analyst Consensus",
    "G_earnings": "Earnings Risk", "H_sector": "Sector Momentum", "I_market": "Market Context",
    "J_instrument": "Instrument Structure", "K_decay": "Opportunity Decay",
}
DIRECTIONAL = {"B_drift", "C_valuation", "D_momentum", "E_technical", "F_analyst", "H_sector", "I_market"}

CLASSES = [(80, "STRONG WATCH", "positive"), (65, "INTERESTING", "positive"), (50, "NEUTRAL", "neutral"),
           (35, "WEAK", "warning"), (0, "AVOID / LOW RELEVANCE", "negative")]


def classify(score: float) -> tuple[str, str]:
    for th, lab, tone in CLASSES:
        if score >= th:
            return lab, tone
    return CLASSES[-1][1], CLASSES[-1][2]


# ---------- individual factors (each returns score, detail) -------------------------------

def f_delay(days: int) -> tuple[float, str]:
    s = 15.0 if days > 45 else interp(days, [(0, 100), (7, 100), (20, 75), (30, 60), (45, 35)])
    note = " — exceeds 45-day STOCK Act window" if days > 45 else ""
    return s, f"{days} days between transaction and public disclosure{note}"


def f_drift(fav_drift: float | None) -> tuple[float, str]:
    if fav_drift is None:
        return 50, "Price at transaction unavailable"
    s = interp(fav_drift * 100, [(-30, 35), (-15, 60), (-5, 85), (0, 80), (10, 65), (25, 45), (50, 25), (100, 10)])
    return s, f"Favourable move since transaction: {pct(fav_drift)}"


def f_valuation(f: dict) -> tuple[float, str, bool]:
    parts, txt = [], []
    if f.get("peg") is not None:
        parts.append(interp(f["peg"], [(0.5, 95), (1, 80), (2, 55), (3, 35), (5, 15)])); txt.append(f"PEG {f['peg']:.1f}")
    if f.get("forward_pe") is not None:
        parts.append(interp(f["forward_pe"], [(10, 90), (20, 75), (30, 55), (50, 35), (100, 15)])); txt.append(f"Fwd P/E {f['forward_pe']:.0f}")
    if f.get("price_to_sales") is not None:
        parts.append(interp(f["price_to_sales"], [(2, 85), (8, 65), (15, 45), (30, 20)])); txt.append(f"P/S {f['price_to_sales']:.1f}")
    if f.get("ev_ebitda") is not None:
        parts.append(interp(f["ev_ebitda"], [(8, 90), (15, 75), (25, 55), (50, 30), (100, 10)])); txt.append(f"EV/EBITDA {f['ev_ebitda']:.0f}")
    if not parts:
        return 50, "Valuation data unavailable (neutral)", False
    return sum(parts) / len(parts), ", ".join(txt), True


def momentum_composite(m: dict) -> float | None:
    w = {"1w": .1, "1m": .2, "3m": .3, "6m": .2, "1y": .2}
    tot = sum(w[k] for k in w if m.get(k) is not None)
    if not tot:
        return None
    return sum(m[k] * w[k] for k in w if m.get(k) is not None) / tot


def f_momentum(m: dict) -> tuple[float, str]:
    c = momentum_composite(m)
    if c is None:
        return 50, "Insufficient history"
    s = interp(c, [(-0.3, 10), (-0.1, 30), (0, 50), (0.1, 65), (0.3, 85), (0.6, 95)])
    return s, f"1W {pct(m.get('1w'))} · 1M {pct(m.get('1m'))} · 3M {pct(m.get('3m'))} · 6M {pct(m.get('6m'))} · 1Y {pct(m.get('1y'))}"


def f_technical(t: dict) -> tuple[float, str]:
    if not t:
        return 50, "No technical data"
    s = 20.0
    s += 10 if t.get("above_sma20") else 0
    s += 15 if t.get("above_sma50") else 0
    s += 20 if t.get("above_sma200") else 0
    r = t.get("rsi14")
    if r is not None:
        s += 25 if 40 <= r <= 65 else 12 if 65 < r <= 75 else -5 if r > 75 else 10 if 30 <= r < 40 else 5
    dh = t.get("dist_high52")
    if dh is not None:
        s += 5 if dh > -0.03 else 10 if dh > -0.10 else 5 if dh > -0.25 else 0
    ma = "/".join(k.upper() for k in ("sma20", "sma50", "sma200") if t.get(f"above_{k}"))
    rsi_txt = f"RSI {r:.0f}" if r is not None else "RSI n/a"
    return clamp(s), f"Above {ma or 'no MAs'} · {rsi_txt} · {pct(dh)} from 52W high"


def f_analyst(f: dict, price: float | None) -> tuple[float, str, bool]:
    b, h, se = f.get("analyst_buy"), f.get("analyst_hold"), f.get("analyst_sell")
    tp = f.get("target_price")
    parts, txt = [], []
    if b is not None and (b + (h or 0) + (se or 0)) > 0:
        share = b / (b + (h or 0) + (se or 0))
        parts.append(interp(share, [(0.3, 20), (0.5, 45), (0.7, 70), (0.9, 90)]))
        txt.append(f"{b} Buy / {h} Hold / {se} Sell")
    if tp and price:
        up = tp / price - 1
        parts.append(interp(up, [(-0.1, 10), (0, 35), (0.1, 60), (0.25, 85), (0.4, 95)]))
        txt.append(f"avg target ${tp:,.2f} ({pct(up)})")
    if not parts:
        return 50, "Analyst data unavailable (neutral)", False
    return sum(parts) / len(parts), " · ".join(txt), True


def f_earnings(next_earnings: date | None, today: date) -> tuple[float, str, str]:
    if not next_earnings:
        return 60, "Earnings date unknown", "unknown"
    d = (next_earnings - today).days
    if d <= 3:
        return 25, f"Earnings in {d} days — event risk HIGH", "high"
    if d <= 10:
        return 45, f"Earnings in {d} days — event risk ELEVATED", "elevated"
    if d <= 21:
        return 65, f"Earnings in {d} days — moderate", "moderate"
    return 85, f"Earnings in {d} days — low near-term event risk", "low"


def f_sector(sector_3m: float | None, spy_3m: float | None, etf: str | None) -> tuple[float, str]:
    if sector_3m is None or spy_3m is None:
        return 50, "Sector data unavailable"
    rel = sector_3m - spy_3m
    return interp(rel, [(-0.1, 15), (-0.03, 35), (0, 50), (0.03, 65), (0.1, 90)]), \
        f"{etf} 3M {pct(sector_3m)} vs SPY {pct(spy_3m)} (rel {pct(rel)})"


def f_market(stock_3m: float | None, spy_3m: float | None, qqq_3m: float | None) -> tuple[float, str]:
    if stock_3m is None or spy_3m is None or qqq_3m is None:
        return 50, "Benchmark data unavailable"
    rel = stock_3m - (spy_3m + qqq_3m) / 2
    return interp(rel, [(-0.2, 10), (-0.05, 35), (0, 50), (0.05, 65), (0.2, 90)]), \
        f"3M: stock {pct(stock_3m)} · SPY {pct(spy_3m)} · QQQ {pct(qqq_3m)}"


def instrument_structure(asset_type: str, strike: float | None, expiration: date | None,
                         tx_date: date, spot: float | None, today: date) -> dict:
    at = asset_type.lower()
    if at in ("stock", "etf", "other") or not expiration:
        return {"score": 55, "kind": "equity", "nature": "Direct equity — no embedded leverage",
                "detail": "Shares: no strike / expiry. Leverage not inferable."}
    days_at_trade = (expiration - tx_date).days
    days_left = (expiration - today).days
    is_call = "call" in at
    nature = "Long-term / conviction (LEAPS-like)" if days_at_trade >= 365 else \
        "Medium-term" if days_at_trade >= 120 else "Short-dated / speculative"
    s = 70 if days_at_trade >= 365 else 55 if days_at_trade >= 120 else 40
    money, m = None, None
    if strike and spot:
        m = spot / strike if is_call else strike / spot
        money = "Deep ITM" if m > 1.2 else "ITM" if m > 1.0 else "ATM" if m > 0.95 else "OTM"
        s += 10 if m > 1.2 else 5 if m > 1.0 else 0 if m > 0.95 else -10
    if days_left <= 0:
        s = 20
        nature += " — EXPIRED (historical only)"
    elif days_left < 60:
        s -= 15
    return {"score": clamp(s), "kind": "option", "nature": nature, "moneyness": money,
            "moneyness_ratio": m, "days_to_expiry": days_left, "days_at_trade": days_at_trade,
            "detail": f"{'Call' if is_call else 'Put'} strike ${strike:,.2f}, exp {expiration.isoformat()} "
                      f"({days_left} d left) · {money or 'moneyness n/a'} · {nature}"}


def age_discount(days_since_disclosure: int) -> float:
    return 1.0 if days_since_disclosure <= 180 else 0.9 if days_since_disclosure <= 365 else 0.8


def compute_score(*, tx_type: str, delay_days: int, fav_drift: float | None, fundamentals: dict,
                  tech: dict, price: float | None, today: date, next_earnings: date | None,
                  sector_3m: float | None, spy_3m: float | None, qqq_3m: float | None, etf: str | None,
                  instrument: dict, decay: dict, days_since_disclosure: int, data_type: str) -> dict:
    d = direction(tx_type)
    comps: dict[str, dict] = {}

    def add(k, score, detail, dt=data_type, avail=True):
        comps[k] = {"key": k, "label": LABELS[k], "raw": round(score, 1), "weight": WEIGHTS[k],
                    "detail": detail, "data_type": dt, "available": avail}

    add("A_delay", *f_delay(delay_days), dt="official" if data_type != "mock" else "mock")
    add("B_drift", *f_drift(fav_drift), dt="calculated")
    v, vt, va = f_valuation(fundamentals); add("C_valuation", v, vt, fundamentals.get("source", "n/a"), va)
    add("D_momentum", *f_momentum(tech.get("momentum", {})), dt="calculated")
    add("E_technical", *f_technical(tech), dt="calculated")
    a, at, aa = f_analyst(fundamentals, price); add("F_analyst", a, at, fundamentals.get("source", "n/a"), aa)
    es, et, _risk = f_earnings(next_earnings, today); add("G_earnings", es, et, fundamentals.get("source", "n/a"))
    add("H_sector", *f_sector(sector_3m, spy_3m, etf), dt="calculated")
    add("I_market", *f_market(tech.get("momentum", {}).get("3m"), spy_3m, qqq_3m), dt="calculated")
    add("J_instrument", instrument["score"], instrument["detail"], dt="official" if data_type != "mock" else "mock")
    add("K_decay", decay.get("score") if decay.get("available") else 50, decay.get("label", ""), dt="calculated")

    for k, c in comps.items():
        c["score"] = round(100 - c["raw"], 1) if (d < 0 and k in DIRECTIONAL) else c["raw"]
        c["mirrored"] = d < 0 and k in DIRECTIONAL
    base = sum(c["score"] * c["weight"] for c in comps.values()) / sum(WEIGHTS.values())
    disc = age_discount(days_since_disclosure)
    total = round(clamp(base * disc), 1)
    lab, tone = classify(total)
    return {"score": total, "base_score": round(base, 1), "age_discount": disc, "classification": lab,
            "tone": tone, "components": list(comps.values()), "earnings_risk": _risk,
            "disclaimer": "Relevance score for research. Not investment advice; never a buy/sell instruction."}
