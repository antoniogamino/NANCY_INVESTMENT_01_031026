from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.analysis import all_trades, analyze_trade, ticker_context
from ..engines.signals import ticker_signals
from ..models import WatchlistItem
from ..services.prices import get_series

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    notes: str | None = None


@router.get("")
def get_watchlist(db: Session = Depends(get_db)):
    trades = all_trades(db)
    rows = []
    for w in db.scalars(select(WatchlistItem).order_by(WatchlistItem.added_at)):
        s = get_series(db, w.ticker)
        if not len(s):
            rows.append({"ticker": w.ticker, "error": "no price data", "id": w.id})
            continue
        ctx = ticker_context(db, w.ticker)
        latest = next((t for t in trades if t.ticker == w.ticker), None)
        a = analyze_trade(db, latest) if latest else None
        ne = ctx["fundamentals"].get("next_earnings")
        rows.append({
            "id": w.id, "ticker": w.ticker, "name": ctx["name"], "notes": w.notes, "price": ctx["price"],
            "change_1d": ctx["tech"].get("change_1d"), "rsi14": ctx["tech"].get("rsi14"),
            "target_price": ctx["fundamentals"].get("target_price"),
            "pelosi_score": a["score"]["score"] if a else None,
            "classification": a["score"]["classification"] if a else None,
            "signal_overall": ticker_signals(db, w.ticker, trades)["overall"] if latest else None,
            "since_disclosure": a["change_since_disclosure"] if a else None,
            "last_disclosure": a["disclosure_date"] if a else None,
            "next_earnings": ne, "days_to_earnings": (date.fromisoformat(ne) - date.today()).days if ne else None,
            "data_type": ctx["price_data_type"],
        })
    return rows


@router.post("")
def add(item: WatchIn, db: Session = Depends(get_db)):
    tk = item.ticker.strip().upper()
    if db.scalar(select(WatchlistItem).where(WatchlistItem.ticker == tk)):
        raise HTTPException(409, f"{tk} already in watchlist")
    if not len(get_series(db, tk)):
        raise HTTPException(404, f"No price data for {tk}")
    w = WatchlistItem(ticker=tk, notes=item.notes)
    db.add(w)
    db.commit()
    return {"id": w.id, "ticker": tk}


@router.delete("/{ticker}")
def remove(ticker: str, db: Session = Depends(get_db)):
    w = db.scalar(select(WatchlistItem).where(WatchlistItem.ticker == ticker.upper()))
    if not w:
        raise HTTPException(404, "Not in watchlist")
    db.delete(w)
    db.commit()
    return {"deleted": ticker.upper()}
