"""IF I FOLLOWED PELOSI — event-driven backtest on public disclosure dates.

Rules
* Universe: BUY / EXERCISE disclosures (optionally SELL as a short, off by default).
* Entry: close of the k-th trading day after the disclosure date (k = 0, 1, 3, 5).
* Exit: after `hold_days` calendar days (converted to trading days ≈ x 252/365), or today.
* Portfolio: equal-weight across currently open positions, rebalanced daily; idle cash earns 0%.
* Benchmarks: SPY & QQQ bought on the first entry date; "Buy & Hold" = same entries, never sold.
Shares / underlying only. No costs, taxes or slippage. Historical simulation, not advice.
"""
from __future__ import annotations

import math
from datetime import date

from sqlalchemy.orm import Session

from ..models import Trade
from ..services.prices import get_series


def _metrics(curve: list[tuple[date, float]], capital: float) -> dict:
    if len(curve) < 2:
        return {"final_capital": capital, "total_return": 0, "cagr": 0, "max_drawdown": 0, "sharpe": None}
    vals = [v for _, v in curve]
    peak, mdd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals))]
    mu = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1))
    years = max((curve[-1][0] - curve[0][0]).days / 365.25, 1 / 365)
    total = vals[-1] / capital - 1
    return {
        "final_capital": round(vals[-1], 2), "total_return": total,
        "cagr": (vals[-1] / capital) ** (1 / years) - 1 if vals[-1] > 0 else -1,
        "max_drawdown": mdd, "sharpe": (mu / sd * math.sqrt(252)) if sd > 0 else None,
    }


def run_backtest(db: Session, trades: list[Trade], capital: float = 10_000, entry_lag: int = 0,
                 hold_days: int = 90, include_sells: bool = False) -> dict:
    hold_td = max(1, round(hold_days * 252 / 365))
    spy = get_series(db, "SPY")
    cal = spy.dates  # master trading calendar
    if not cal:
        return {"error": "No price data"}

    positions = []  # (ticker, dir, entry_idx, exit_idx_hold)
    for t in trades:
        if t.transaction_type == "SELL" and not include_sells:
            continue
        s = get_series(db, t.ticker)
        i0 = s.index_on_or_after(t.disclosure_date)
        if i0 is None:
            continue
        ei = i0 + entry_lag
        if ei >= len(s):
            continue
        entry_date = s.dates[ei]
        xi = min(ei + hold_td, len(s) - 1)
        positions.append({
            "trade_id": t.id, "ticker": t.ticker, "dir": -1 if t.transaction_type == "SELL" else 1,
            "entry_date": entry_date, "exit_date": s.dates[xi], "entry_price": s.closes[ei],
            "exit_price": s.closes[xi], "open": xi == len(s) - 1 and ei + hold_td > len(s) - 1,
        })
    if not positions:
        return {"error": "No trades eligible for this configuration"}

    for p in positions:
        p["return"] = (p["exit_price"] / p["entry_price"] - 1) * p["dir"]

    start = min(p["entry_date"] for p in positions)
    idx0 = spy.index_on_or_after(start)
    days = cal[idx0:]

    def curve_for(hold_forever: bool) -> list[tuple[date, float]]:
        eq, out = capital, [(days[0], capital)]
        for k in range(1, len(days)):
            d_prev, d = days[k - 1], days[k]
            rets = []
            for p in positions:
                end = d if hold_forever else p["exit_date"]
                if p["entry_date"] <= d_prev and d <= end:
                    s = get_series(db, p["ticker"])
                    a, b = s.price_on(d_prev), s.price_on(d)
                    if a and b:
                        rets.append((b / a - 1) * p["dir"])
            if rets:
                eq *= 1 + sum(rets) / len(rets)
            out.append((d, eq))
        return out

    def bench(tk: str) -> list[tuple[date, float]]:
        s = get_series(db, tk)
        p0 = s.price_on(days[0])
        return [(d, capital * s.price_on(d) / p0) for d in days if s.price_on(d)]

    strat, bh = curve_for(False), curve_for(True)
    curves = {"strategy": strat, "buy_hold": bh, "spy": bench("SPY"), "qqq": bench("QQQ")}
    closed = [p for p in positions if not p["open"]]
    m = {k: _metrics(v, capital) for k, v in curves.items()}
    m["strategy"].update({
        "trades": len(positions), "closed_trades": len(closed),
        "win_rate": sum(1 for p in positions if p["return"] > 0) / len(positions),
        "avg_trade_return": sum(p["return"] for p in positions) / len(positions),
    })
    # downsample curve for transport (weekly)
    merged = []
    for i, (d, v) in enumerate(strat):
        if i % 5 == 0 or i == len(strat) - 1:
            merged.append({"date": d, "strategy": round(v, 2), "buy_hold": round(bh[i][1], 2),
                           "spy": round(curves["spy"][i][1], 2) if i < len(curves["spy"]) else None,
                           "qqq": round(curves["qqq"][i][1], 2) if i < len(curves["qqq"]) else None})
    return {
        "params": {"capital": capital, "entry_lag": entry_lag, "hold_days": hold_days,
                   "hold_trading_days": hold_td, "include_sells": include_sells},
        "metrics": m, "curve": merged,
        "positions": sorted(positions, key=lambda p: p["entry_date"]),
        "assumptions": [ln.strip()[2:] for ln in __doc__.splitlines() if ln.strip().startswith("* ")],
    }
