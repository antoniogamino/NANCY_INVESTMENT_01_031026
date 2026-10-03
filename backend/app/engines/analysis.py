"""Orchestrates per-trade and per-ticker analysis from the raw services + engines."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Trade
from ..services.fundamentals import get_fundamentals_provider
from ..services.market_data import get_market_provider
from ..services.prices import get_series
from ..services.reference import company_name, sector_etf
from . import technicals
from .decay import opportunity_decay
from .scoring import compute_score, instrument_structure
from .util import direction

_TICKER_CACHE: dict[tuple, dict] = {}
_TRADE_CACHE: dict[tuple, dict] = {}


def clear_cache() -> None:
    _TICKER_CACHE.clear()
    _TRADE_CACHE.clear()


def price_data_type() -> str:
    return "mock" if get_market_provider().name == "mock" else "market"


def ticker_context(db: Session, ticker: str) -> dict:
    """Market analysis for a ticker, independent of any trade."""
    s = get_series(db, ticker)
    key = (ticker, s.last_date)
    if key in _TICKER_CACHE:
        return _TICKER_CACHE[key]
    tech = technicals.snapshot(s)
    fund = get_fundamentals_provider().get(ticker, s.last).to_dict()
    etf = sector_etf(ticker)
    spy, qqq = get_series(db, "SPY"), get_series(db, "QQQ")
    sec = get_series(db, etf) if etf else None
    ctx = {
        "ticker": ticker, "name": company_name(ticker), "price": s.last, "as_of": s.last_date,
        "tech": tech, "fundamentals": fund, "sector_etf": etf,
        "sector_3m": technicals.ret(sec.closes, 63) if sec else None,
        "sector_momentum": technicals.snapshot(sec)["momentum"] if sec and len(sec) else None,
        "spy_3m": technicals.ret(spy.closes, 63), "qqq_3m": technicals.ret(qqq.closes, 63),
        "spy_momentum": technicals.snapshot(spy)["momentum"], "qqq_momentum": technicals.snapshot(qqq)["momentum"],
        "price_data_type": price_data_type(),
    }
    _TICKER_CACHE[key] = ctx
    return ctx


def analyze_trade(db: Session, t: Trade, today: date | None = None) -> dict:
    today = today or date.today()
    s = get_series(db, t.ticker)
    key = (t.id, s.last_date)
    if key in _TRADE_CACHE:
        return _TRADE_CACHE[key]
    ctx = ticker_context(db, t.ticker)
    p_tx, p_disc, p_now = s.price_on(t.transaction_date), s.price_on(t.disclosure_date), s.last
    delay = (t.disclosure_date - t.transaction_date).days
    since_disc = (today - t.disclosure_date).days
    decay = opportunity_decay(p_tx, p_disc, p_now, since_disc, t.transaction_type)
    inst = instrument_structure(t.asset_type, t.strike, t.expiration, t.transaction_date, p_now, today)
    fav_drift = (p_now / p_tx - 1) * direction(t.transaction_type) if p_tx and p_now else None
    ne = ctx["fundamentals"].get("next_earnings")
    score = compute_score(
        tx_type=t.transaction_type, delay_days=delay, fav_drift=fav_drift, fundamentals=ctx["fundamentals"],
        tech=ctx["tech"], price=p_now, today=today, next_earnings=date.fromisoformat(ne) if ne else None,
        sector_3m=ctx["sector_3m"], spy_3m=ctx["spy_3m"], qqq_3m=ctx["qqq_3m"], etf=ctx["sector_etf"],
        instrument=inst, decay=decay, days_since_disclosure=since_disc, data_type=t.confidence_level,
    )
    mid = (t.amount_min + t.amount_max) / 2 if t.amount_min and t.amount_max else None
    out = {
        "id": t.id, "ticker": t.ticker, "company": company_name(t.ticker), "asset": t.asset,
        "sector": t.sector, "transaction_type": t.transaction_type, "asset_type": t.asset_type,
        "transaction_date": t.transaction_date, "disclosure_date": t.disclosure_date,
        "delay_days": delay, "days_since_disclosure": since_disc,
        "amount_min": t.amount_min, "amount_max": t.amount_max, "amount_mid_estimated": mid,
        "strike": t.strike, "expiration": t.expiration, "contracts": t.contracts,
        "price_at_transaction": p_tx, "price_at_disclosure": p_disc, "price_now": p_now,
        "change_since_transaction": (p_now / p_tx - 1) if p_tx and p_now else None,
        "change_since_disclosure": (p_now / p_disc - 1) if p_disc and p_now else None,
        "est_shares": round(mid / p_tx) if mid and p_tx and t.asset_type in ("stock", "etf") else None,
        "source": t.source, "source_url": t.source_url, "filing_id": t.filing_id,
        "owner": t.owner, "owner_name": t.owner_name, "notes": t.notes,
        "confidence_level": t.confidence_level, "analysis_status": t.analysis_status,
        "price_data_type": ctx["price_data_type"],
        "instrument": inst, "decay": decay, "score": score,
    }
    _TRADE_CACHE[key] = out
    return out


def all_trades(db: Session) -> list[Trade]:
    return list(db.scalars(select(Trade).order_by(Trade.disclosure_date.desc(), Trade.id.desc())))


def analyze_all(db: Session) -> list[dict]:
    return [analyze_trade(db, t) for t in all_trades(db)]


def position_status(trades: list[Trade], today: date | None = None) -> dict[int, str]:
    """Heuristic OPEN/CLOSED per trade (ESTIMATED — disclosures don't report positions)."""
    today = today or date.today()
    out: dict[int, str] = {}
    for t in trades:
        if t.transaction_type == "SELL":
            out[t.id] = "closed"
            continue
        if t.expiration and t.expiration < today and t.transaction_type != "EXERCISE":
            out[t.id] = "closed"
            continue
        later_sell = any(o.ticker == t.ticker and o.transaction_type == "SELL"
                         and o.transaction_date > t.transaction_date for o in trades)
        out[t.id] = "closed" if later_sell else "open"
    return out
