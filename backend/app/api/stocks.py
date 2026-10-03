from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ai
from ..database import get_db
from ..engines.analysis import all_trades, analyze_trade, ticker_context
from ..engines.signals import ticker_signals
from ..models import Trade
from ..services.news import get_news_provider
from ..services.prices import get_series

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/{ticker}")
def stock_detail(ticker: str, trade_id: int | None = Query(None), db: Session = Depends(get_db)):
    ticker = ticker.upper()
    s = get_series(db, ticker)
    if not len(s):
        raise HTTPException(404, f"No price data for {ticker}")
    ctx = ticker_context(db, ticker)
    trades = list(db.scalars(select(Trade).where(Trade.ticker == ticker).order_by(Trade.disclosure_date.desc())))
    analyzed = [analyze_trade(db, t) for t in trades]
    focus = next((a for a in analyzed if a["id"] == trade_id), analyzed[0] if analyzed else None)

    # price history with SMA overlays + event markers
    closes = s.closes
    csum = [0.0]
    for c in closes:
        csum.append(csum[-1] + c)
    hist = []
    for i, (d, c) in enumerate(zip(s.dates, closes)):
        hist.append({"date": d, "close": c,
                     "sma50": round((csum[i + 1] - csum[i - 49]) / 50, 2) if i >= 49 else None,
                     "sma200": round((csum[i + 1] - csum[i - 199]) / 200, 2) if i >= 199 else None})
    markers = []
    for a in analyzed:
        ti = s.index_on_or_after(a["transaction_date"])
        markers.append({"date": s.dates[ti] if ti is not None else a["transaction_date"],
                        "kind": "SELL" if a["transaction_type"] == "SELL" else "BUY", "trade_id": a["id"],
                        "price": a["price_at_transaction"], "label": f"{a['transaction_type']} {a['asset_type']}"})
        di = s.index_on_or_after(a["disclosure_date"])
        markers.append({"date": s.dates[di] if di is not None else a["disclosure_date"], "kind": "DISCLOSURE",
                        "trade_id": a["id"], "price": a["price_at_disclosure"], "label": "Disclosure"})

    sec = get_series(db, ctx["sector_etf"]) if ctx["sector_etf"] else None
    spy = get_series(db, "SPY")
    start = date.today() - timedelta(days=365)
    rel = []
    base_s, base_spy = s.price_on(start), spy.price_on(start)
    base_sec = sec.price_on(start) if sec else None
    for d, c in s.window(start, date.today()):
        row = {"date": d, "stock": c / base_s - 1, "spy": (spy.price_on(d) or 0) / base_spy - 1}
        if sec and base_sec:
            row["sector"] = (sec.price_on(d) or 0) / base_sec - 1
        rel.append(row)

    return {
        "ticker": ticker, "context": ctx, "history": hist, "markers": markers, "relative_1y": rel,
        "trades": analyzed, "focus": focus,
        "ai": ai.analyze(focus, ctx) if focus else None,
        "signals": ticker_signals(db, ticker, all_trades(db)),
        "news": [n.__dict__ for n in get_news_provider().get(ticker)],
    }
