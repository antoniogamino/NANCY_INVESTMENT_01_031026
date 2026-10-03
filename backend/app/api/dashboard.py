from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..engines.analysis import all_trades, analyze_trade, position_status

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    trades = all_trades(db)
    analyzed = [analyze_trade(db, t) for t in trades]
    status = position_status(trades)
    buys = [a for a in analyzed if a["transaction_type"] != "SELL"]
    sells = [a for a in analyzed if a["transaction_type"] == "SELL"]
    cap_min = sum(a["amount_min"] or 0 for a in analyzed)
    cap_max = sum(a["amount_max"] or 0 for a in analyzed)
    sectors = Counter(a["sector"] or "Unknown" for a in analyzed)
    sector_cap = defaultdict(float)
    for a in analyzed:
        sector_cap[a["sector"] or "Unknown"] += a["amount_mid_estimated"] or 0

    # amount-weighted (midpoint) return since transaction for buy-side trades — ESTIMATED
    w = [(a["amount_mid_estimated"] or 0, a["change_since_transaction"]) for a in buys
         if a["change_since_transaction"] is not None]
    wsum = sum(x for x, _ in w)
    est_return = sum(x * r for x, r in w) / wsum if wsum else None
    w2 = [(a["amount_mid_estimated"] or 0, a["change_since_disclosure"]) for a in buys
          if a["change_since_disclosure"] is not None]
    w2sum = sum(x for x, _ in w2)
    est_return_follow = sum(x * r for x, r in w2) / w2sum if w2sum else None

    for a in analyzed:
        a["position_status"] = status.get(a["id"])

    top = sorted(analyzed, key=lambda a: a["score"]["score"], reverse=True)
    return {
        "overview": {
            "total_trades": len(analyzed), "buys": len(buys), "sells": len(sells),
            "capital_min": cap_min, "capital_max": cap_max, "capital_mid": (cap_min + cap_max) / 2,
            "open_positions": sum(1 for v in status.values() if v == "open"),
            "closed_positions": sum(1 for v in status.values() if v == "closed"),
            "est_return_since_trade": est_return, "est_return_since_disclosure": est_return_follow,
            "unique_tickers": len({a["ticker"] for a in analyzed}),
            "options_share": sum(1 for a in analyzed if a["instrument"]["kind"] == "option") / max(1, len(analyzed)),
            "avg_delay_days": sum(a["delay_days"] for a in analyzed) / max(1, len(analyzed)),
        },
        "sectors": [{"sector": s, "count": c, "capital_mid": sector_cap[s]} for s, c in sectors.most_common()],
        "latest": analyzed[:12],
        "top_scores": top[:6],
        "data_types": {
            "overview.capital": "estimated (sum of reported band min/max)",
            "overview.est_return": "estimated (amount-midpoint weighted, underlying price)",
            "overview.open_closed": "estimated (heuristic from later sells / option expiry)",
        },
    }
