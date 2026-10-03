"""PERFORMANCE ANALYSIS — "was the trade good?" vs "was following it publicly good?".

For each trade we compute forward returns of the *underlying* from the transaction date
(what the filer experienced) and from the disclosure date (what a public follower could get),
plus the same windows for SPY and QQQ. Returns are signed by direction (SELL = short view).
Options are evaluated on the underlying because premiums are not disclosed.
"""
from __future__ import annotations

import statistics

from sqlalchemy.orm import Session

from ..models import Trade
from ..services.prices import get_series
from .technicals import HORIZONS, forward_return
from .util import direction


def trade_performance(db: Session, t: Trade) -> dict:
    s, spy, qqq = get_series(db, t.ticker), get_series(db, "SPY"), get_series(db, "QQQ")
    d = direction(t.transaction_type)
    out = {"id": t.id, "ticker": t.ticker, "transaction_type": t.transaction_type,
           "asset_type": t.asset_type, "transaction_date": t.transaction_date,
           "disclosure_date": t.disclosure_date, "from_transaction": {}, "from_disclosure": {}}
    for anchor_name, anchor in (("from_transaction", t.transaction_date), ("from_disclosure", t.disclosure_date)):
        for h, n in HORIZONS.items():
            r, _ = forward_return(s, anchor, n)
            rs, _ = forward_return(spy, anchor, n)
            rq, _ = forward_return(qqq, anchor, n)
            if r is None:
                out[anchor_name][h] = None
                continue
            sr = r * d
            out[anchor_name][h] = {
                "return": sr, "raw_return": r, "spy": rs, "qqq": rq,
                "alpha_spy": (sr - rs * d) if rs is not None else None,
                "alpha_qqq": (sr - rq * d) if rq is not None else None,
            }
    return out


def _agg(vals: list[dict], key: str) -> float | None:
    xs = [v[key] for v in vals if v and v.get(key) is not None]
    return statistics.mean(xs) if xs else None


def aggregate(perfs: list[dict], only_buys: bool = False) -> dict:
    rows = [p for p in perfs if not only_buys or p["transaction_type"] != "SELL"]
    out = {}
    for h in HORIZONS:
        block = {}
        for anchor in ("from_transaction", "from_disclosure"):
            vals = [p[anchor][h] for p in rows if p[anchor].get(h)]
            rets = [v["return"] for v in vals]
            block[anchor] = {
                "n": len(vals),
                "avg_return": statistics.mean(rets) if rets else None,
                "median_return": statistics.median(rets) if rets else None,
                "win_rate": sum(1 for r in rets if r > 0) / len(rets) if rets else None,
                "avg_alpha_spy": _agg(vals, "alpha_spy"),
                "avg_alpha_qqq": _agg(vals, "alpha_qqq"),
            }
        ft, fd = block["from_transaction"]["avg_return"], block["from_disclosure"]["avg_return"]
        block["disclosure_cost"] = (ft - fd) if ft is not None and fd is not None else None
        out[h] = block
    return out


def performance_report(db: Session, trades: list[Trade]) -> dict:
    perfs = [trade_performance(db, t) for t in trades]
    return {
        "trades": perfs,
        "aggregate_all": aggregate(perfs),
        "aggregate_buys": aggregate(perfs, only_buys=True),
        "notes": [
            "Returns measured on the underlying share price (option premiums are not disclosed).",
            "SELL disclosures are scored as a short/avoid view: a price decline counts as a positive return.",
            "disclosure_cost = avg return from transaction − avg return from disclosure (edge lost to reporting lag).",
        ],
    }
