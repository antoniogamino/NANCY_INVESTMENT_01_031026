from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .. import ai
from ..database import get_db
from ..engines import analysis
from ..engines.analysis import all_trades, analyze_trade, position_status, ticker_context
from ..models import Trade
from ..services import prices
from ..services.ingestion import CSV_COLUMNS, parse_csv, upsert_trades

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("")
def list_trades(db: Session = Depends(get_db)):
    trades = all_trades(db)
    status = position_status(trades)
    out = []
    for t in trades:
        a = analyze_trade(db, t)
        a["position_status"] = status.get(t.id)
        out.append(a)
    return out


@router.get("/template.csv", response_class=PlainTextResponse)
def template():
    example = ("Spouse,Paul Pelosi,NVIDIA Corporation,NVDA,stock,BUY,2026-07-14,2026-08-12,1000001,5000000,,,,"
               "Transcribed from PTR,https://disclosures-clerk.house.gov/...,official")
    return ",".join(CSV_COLUMNS) + "\n" + example + "\n"


@router.post("/import")
def import_csv(csv_text: str = Body(..., media_type="text/plain"), db: Session = Depends(get_db)):
    rows, errors = parse_csv(csv_text)
    added = upsert_trades(db, rows) if rows else 0
    tickers = {r.ticker for r in rows}
    for tk in tickers:
        prices.get_series(db, tk)
    analysis.clear_cache()
    return {"parsed": len(rows), "added": added, "errors": errors}


@router.get("/{trade_id}")
def trade_detail(trade_id: int, db: Session = Depends(get_db)):
    t = db.get(Trade, trade_id)
    if not t:
        raise HTTPException(404, "Trade not found")
    a = analyze_trade(db, t)
    return {**a, "ai": ai.analyze(a, ticker_context(db, t.ticker))}


@router.delete("/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    t = db.get(Trade, trade_id)
    if not t:
        raise HTTPException(404, "Trade not found")
    db.delete(t)
    db.commit()
    analysis.clear_cache()
    return {"deleted": trade_id}
