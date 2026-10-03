"""Deterministic, offline mock price generator.

Prices follow a correlated factor model (market + sector + idiosyncratic noise) seeded per
ticker, so results are reproducible. Optional *anchors* pin a ticker to exact prices on
specific dates (used for the NVDA 120 -> 138 -> 145 demo case). ALL OUTPUT IS MOCK DATA.
"""
from __future__ import annotations

import math
import random
import zlib
from datetime import date, timedelta
from functools import lru_cache

from ..reference import COMPANIES, SECTOR_ETF
from .base import Bar, MarketDataProvider

MOCK_START = date(2023, 1, 3)

# ticker: (start_price, annual_drift, annual_idio_vol, beta)
PARAMS: dict[str, tuple[float, float, float, float]] = {
    "SPY": (384.0, 0.13, 0.00, 1.00),
    "QQQ": (268.0, 0.20, 0.05, 1.20),
    "XLK": (125.0, 0.20, 0.06, 1.15),
    "XLC": (49.0, 0.18, 0.07, 1.05),
    "XLY": (142.0, 0.10, 0.07, 1.10),
    "XLU": (70.0, 0.08, 0.10, 0.50),
    "XLV": (135.0, 0.03, 0.08, 0.65),
    "XLF": (34.0, 0.12, 0.08, 1.00),
    "NVDA": (14.6, 0.55, 0.38, 1.70),
    "AAPL": (125.0, 0.16, 0.18, 1.10),
    "MSFT": (240.0, 0.20, 0.17, 1.00),
    "AVGO": (55.0, 0.45, 0.30, 1.30),
    "CRM": (133.0, 0.18, 0.28, 1.15),
    "PANW": (140.0, 0.22, 0.30, 1.20),
    "GOOGL": (89.0, 0.28, 0.24, 1.05),
    "NFLX": (295.0, 0.38, 0.28, 1.15),
    "DIS": (88.0, 0.02, 0.22, 1.00),
    "RBLX": (30.0, 0.35, 0.45, 1.50),
    "AMZN": (85.0, 0.30, 0.25, 1.20),
    "TSLA": (108.0, 0.30, 0.50, 1.80),
    "VST": (23.0, 0.70, 0.40, 0.90),
    "TEM": (40.0, 0.25, 0.60, 1.60),
    "V": (210.0, 0.14, 0.14, 0.90),
}

# Pinned prices: ticker -> {date | "LAST": price}. "LAST" = most recent trading day.
ANCHORS: dict[str, dict] = {
    # The user's reference case: Paul Pelosi buys NVDA at ~$120, disclosed at ~$138, today ~$145
    "NVDA": {date(2025, 12, 31): 132.0, date(2026, 4, 15): 112.0, date(2026, 7, 14): 120.0,
             date(2026, 8, 12): 138.0, "LAST": 145.0},
    "TEM": {date(2024, 6, 14): 38.0, "LAST": 61.0},
    "VST": {"LAST": 168.0},
}

MARKET_VOL = 0.15


def business_days(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def last_business_day(d: date | None = None) -> date:
    d = d or date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _rng(key: str) -> random.Random:
    return random.Random(zlib.crc32(key.encode()))


def _factor(key: str, n: int, vol: float) -> list[float]:
    r = _rng(key)
    s = vol / math.sqrt(252)
    return [r.gauss(0, s) for _ in range(n)]


@lru_cache(maxsize=64)
def _series(ticker: str, end: date) -> tuple[tuple[date, float], ...]:
    days = business_days(MOCK_START, end)
    n = len(days)
    if ticker not in PARAMS:
        # unknown ticker: generic mid-cap profile
        p0, mu, vol, beta = 50.0, 0.10, 0.30, 1.0
    else:
        p0, mu, vol, beta = PARAMS[ticker]
    mkt = _factor("MARKET", n, MARKET_VOL)
    sector = COMPANIES.get(ticker, {}).get("sector")
    etf_sector = next((s for s, e in SECTOR_ETF.items() if e == ticker), None)
    sector_key = sector or etf_sector
    sec = _factor(f"SECTOR:{sector_key}", n, 0.10) if sector_key else [0.0] * n
    idio = _factor(f"IDIO:{ticker}", n, vol)
    drift = (mu - 0.5 * (vol ** 2 + (beta * MARKET_VOL) ** 2)) / 252

    logp = [math.log(p0)]
    for i in range(1, n):
        logp.append(logp[-1] + drift + beta * mkt[i] + 0.6 * sec[i] + idio[i])

    anchors = ANCHORS.get(ticker, {})
    if anchors:
        idx = {d: i for i, d in enumerate(days)}
        pts: list[tuple[int, float]] = []
        for k, price in anchors.items():
            i = n - 1 if k == "LAST" else idx.get(k if k.weekday() < 5 else last_business_day(k))
            if i is None or i >= n:
                continue
            pts.append((i, math.log(price) - logp[i]))
        pts.sort()
        if pts:
            adj = [0.0] * n
            for i in range(n):
                if i <= pts[0][0]:
                    # fade in from 0 at the start so early history stays natural
                    adj[i] = pts[0][1] * (i / pts[0][0] if pts[0][0] else 1)
                elif i >= pts[-1][0]:
                    adj[i] = pts[-1][1]
                else:
                    for (a, da), (b, db) in zip(pts, pts[1:]):
                        if a <= i <= b:
                            adj[i] = da + (db - da) * (i - a) / (b - a)
                            break
            logp = [lp + a for lp, a in zip(logp, adj)]

    return tuple((d, round(math.exp(lp), 2)) for d, lp in zip(days, logp))


class MockMarketDataProvider(MarketDataProvider):
    name = "mock"

    def get_history(self, ticker: str, start: date, end: date) -> list[Bar]:
        end = min(end, last_business_day())
        series = _series(ticker.upper(), last_business_day())
        vr = _rng(f"VOL:{ticker}")
        return [Bar(d, p, round(vr.uniform(5e6, 6e7))) for d, p in series if start <= d <= end]
