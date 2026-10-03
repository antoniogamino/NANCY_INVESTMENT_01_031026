"""Pure technical-analysis helpers operating on a price Series."""
from __future__ import annotations

import math
from datetime import date

from ..services.prices import Series

HORIZONS = {"1w": 5, "1m": 21, "3m": 63, "6m": 126, "1y": 252}


def sma(closes: list[float], n: int) -> float | None:
    return sum(closes[-n:]) / n if len(closes) >= n else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    """Wilder's RSI."""
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        ch = closes[i] - closes[i - 1]
        gains += max(ch, 0)
        losses += max(-ch, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(ch, 0)) / n
        al = (al * (n - 1) + max(-ch, 0)) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def ret(closes: list[float], n: int) -> float | None:
    if len(closes) <= n or closes[-n - 1] == 0:
        return None
    return closes[-1] / closes[-n - 1] - 1


def volatility(closes: list[float], n: int = 63) -> float | None:
    if len(closes) <= n:
        return None
    r = [math.log(closes[i] / closes[i - 1]) for i in range(len(closes) - n, len(closes))]
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(252)


def snapshot(s: Series, as_of: date | None = None) -> dict:
    """Full technical snapshot of a series (optionally as of a past date)."""
    if as_of:
        i = s.index_on_or_before(as_of)
        closes = s.closes[: (i + 1) if i is not None else 0]
    else:
        closes = s.closes
    if not closes:
        return {}
    last = closes[-1]
    w52 = closes[-252:]
    hi, lo = max(w52), min(w52)
    out = {
        "price": last,
        "sma20": sma(closes, 20), "sma50": sma(closes, 50), "sma200": sma(closes, 200),
        "rsi14": rsi(closes[-300:], 14),
        "high52": hi, "low52": lo,
        "dist_high52": last / hi - 1, "dist_low52": last / lo - 1,
        "vol_3m": volatility(closes, 63),
        "change_1d": ret(closes, 1),
        "momentum": {k: ret(closes, n) for k, n in HORIZONS.items()},
    }
    for k in ("sma20", "sma50", "sma200"):
        out[f"above_{k}"] = (last > out[k]) if out[k] else None
    return out


def forward_return(s: Series, start: date, trading_days: int, lag: int = 0) -> tuple[float | None, date | None]:
    """Return from close on/after `start` (+lag trading days) over `trading_days`. None if not enough data."""
    i = s.index_on_or_after(start)
    if i is None:
        return None, None
    i += lag
    j = i + trading_days
    if j >= len(s):
        return None, None
    return s.closes[j] / s.closes[i] - 1, s.dates[j]
