"""SIGNAL ENGINE — per-ticker component scores (0-100, higher = more favourable/relevant).

Pelosi Activity · Disclosure Freshness · Price Opportunity · Momentum · Fundamental Quality ·
Valuation · Risk (higher = lower risk) · Overall.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..models import Trade
from ..services.reference import sector_of
from .analysis import analyze_trade, ticker_context
from .scoring import classify, f_momentum, f_valuation
from .util import interp

WEIGHTS = {"activity": 15, "freshness": 15, "opportunity": 15, "momentum": 15,
           "quality": 15, "valuation": 10, "risk": 15}


def _quality(f: dict) -> tuple[float, str]:
    parts = []
    if f.get("gross_margin") is not None:
        parts.append(interp(f["gross_margin"], [(0.2, 25), (0.4, 50), (0.6, 75), (0.8, 95)]))
    if f.get("operating_margin") is not None:
        parts.append(interp(f["operating_margin"], [(-0.2, 5), (0, 30), (0.15, 60), (0.3, 85), (0.5, 98)]))
    if f.get("roe") is not None:
        parts.append(interp(f["roe"], [(-0.3, 5), (0, 25), (0.15, 60), (0.3, 85), (0.6, 95)]))
    if f.get("revenue_growth") is not None:
        parts.append(interp(f["revenue_growth"], [(-0.1, 15), (0, 35), (0.1, 60), (0.25, 80), (0.5, 95)]))
    if not parts:
        return 50, "Fundamentals unavailable"
    return sum(parts) / len(parts), "Margins, ROE and revenue growth"


def ticker_signals(db: Session, ticker: str, trades: list[Trade], today: date | None = None) -> dict:
    today = today or date.today()
    ctx = ticker_context(db, ticker)
    tt = sorted([t for t in trades if t.ticker == ticker], key=lambda t: t.disclosure_date)
    comps: dict[str, dict] = {}

    def add(k, label, score, detail):
        comps[k] = {"key": k, "label": label, "score": round(score, 1), "weight": WEIGHTS[k], "detail": detail}

    # Activity: recent count, net buys, size
    recent = [t for t in tt if (today - t.disclosure_date).days <= 730]
    buys = sum(1 for t in recent if t.transaction_type != "SELL")
    sells = len(recent) - buys
    size = sum(((t.amount_min or 0) + (t.amount_max or 0)) / 2 for t in recent if t.transaction_type != "SELL")
    act = 30 + 10 * min(buys, 4) - 12 * min(sells, 3) + interp(size, [(0, 0), (250_000, 5), (1_000_000, 15), (5_000_000, 25)])
    add("activity", "Pelosi Activity", max(0, min(100, act)),
        f"{buys} buy-side / {sells} sell disclosures in 24M · est. ${size:,.0f} buy-side (midpoints)")

    latest = tt[-1] if tt else None
    days = (today - latest.disclosure_date).days if latest else 9999
    add("freshness", "Disclosure Freshness", interp(days, [(0, 100), (30, 80), (90, 55), (180, 35), (365, 15), (730, 5)]),
        f"Latest disclosure {days} days ago" if latest else "No disclosures")

    latest_buy = next((t for t in reversed(tt) if t.transaction_type != "SELL"), None)
    if latest_buy:
        a = analyze_trade(db, latest_buy, today)
        add("opportunity", "Price Opportunity", a["decay"].get("score") or 50, a["decay"].get("label", ""))
    else:
        add("opportunity", "Price Opportunity", 30, "No buy-side disclosure to follow")

    ms, mt = f_momentum(ctx["tech"].get("momentum", {}))
    add("momentum", "Momentum", ms, mt)
    qs, qt = _quality(ctx["fundamentals"])
    add("quality", "Fundamental Quality", qs, qt)
    vs, vt, _ = f_valuation(ctx["fundamentals"])
    add("valuation", "Valuation", vs, vt)

    vol = ctx["tech"].get("vol_3m")
    beta = ctx["fundamentals"].get("beta")
    ne = ctx["fundamentals"].get("next_earnings")
    dte = (date.fromisoformat(ne) - today).days if ne else None
    risk = interp(vol or 0.35, [(0.15, 90), (0.3, 65), (0.5, 40), (0.8, 15)])
    if beta:
        risk -= max(0, (beta - 1.2) * 15)
    if dte is not None and dte <= 7:
        risk -= 10
    vol_txt = f"{vol * 100:.0f}%" if vol else "n/a"
    add("risk", "Risk (higher = lower risk)", max(0, min(100, risk)),
        f"3M vol {vol_txt} · beta {beta or 'n/a'} · earnings in {dte if dte is not None else 'n/a'} d")

    overall = sum(c["score"] * c["weight"] for c in comps.values()) / sum(WEIGHTS.values())
    lab, tone = classify(overall)
    return {"ticker": ticker, "name": ctx["name"], "price": ctx["price"], "sector": sector_of(ticker),
            "components": list(comps.values()), "overall": round(overall, 1), "classification": lab, "tone": tone}
