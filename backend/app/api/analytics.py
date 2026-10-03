from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.analysis import all_trades, analyze_trade
from ..engines.backtest import run_backtest
from ..engines.performance import performance_report
from ..engines.signals import ticker_signals

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/timeline")
def timeline(db: Session = Depends(get_db)):
    out = []
    for t in all_trades(db):
        a = analyze_trade(db, t)
        out.append({k: a[k] for k in ("id", "ticker", "company", "sector", "transaction_type", "asset_type",
                                      "transaction_date", "disclosure_date", "delay_days", "amount_min",
                                      "amount_max", "amount_mid_estimated", "strike", "expiration",
                                      "change_since_transaction", "confidence_level")}
                   | {"score": a["score"]["score"], "classification": a["score"]["classification"]})
    return out


@router.get("/performance")
def performance(db: Session = Depends(get_db)):
    return performance_report(db, all_trades(db))


@router.get("/backtest")
def backtest(capital: float = Query(10_000, gt=0), entry_lag: int = Query(0, ge=0, le=20),
             hold_days: int = Query(90, ge=1, le=1825), include_sells: bool = False,
             db: Session = Depends(get_db)):
    return run_backtest(db, all_trades(db), capital, entry_lag, hold_days, include_sells)


@router.get("/backtest/grid")
def backtest_grid(capital: float = 10_000, include_sells: bool = False, db: Session = Depends(get_db)):
    trades = all_trades(db)
    rows = []
    for lag in (0, 1, 3, 5):
        for hold in (30, 90, 180, 365):
            r = run_backtest(db, trades, capital, lag, hold, include_sells)
            if "metrics" in r:
                m = r["metrics"]
                rows.append({"entry_lag": lag, "hold_days": hold,
                             "total_return": m["strategy"]["total_return"], "cagr": m["strategy"]["cagr"],
                             "max_drawdown": m["strategy"]["max_drawdown"], "sharpe": m["strategy"]["sharpe"],
                             "win_rate": m["strategy"]["win_rate"], "spy_return": m["spy"]["total_return"],
                             "qqq_return": m["qqq"]["total_return"]})
    return rows


@router.get("/signals")
def signals(db: Session = Depends(get_db)):
    trades = all_trades(db)
    tickers = sorted({t.ticker for t in trades})
    return sorted((ticker_signals(db, tk, trades) for tk in tickers), key=lambda x: x["overall"], reverse=True)
