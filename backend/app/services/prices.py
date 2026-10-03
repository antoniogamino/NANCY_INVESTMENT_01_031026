"""Price access layer with a SQLite cache in front of the configured market-data provider."""
from __future__ import annotations

import bisect
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import PriceBar
from .market_data import get_market_provider, last_business_day
from .market_data.mock_provider import MOCK_START

log = logging.getLogger(__name__)


class Series:
    """Ascending daily close series with fast date lookups."""

    def __init__(self, ticker: str, rows: list[tuple[date, float]]):
        self.ticker = ticker
        self.dates = [d for d, _ in rows]
        self.closes = [c for _, c in rows]

    def __len__(self) -> int:
        return len(self.dates)

    @property
    def last(self) -> float | None:
        return self.closes[-1] if self.closes else None

    @property
    def last_date(self) -> date | None:
        return self.dates[-1] if self.dates else None

    def index_on_or_after(self, d: date) -> int | None:
        i = bisect.bisect_left(self.dates, d)
        return i if i < len(self.dates) else None

    def index_on_or_before(self, d: date) -> int | None:
        i = bisect.bisect_right(self.dates, d) - 1
        return i if i >= 0 else None

    def price_on(self, d: date) -> float | None:
        """Close on d, or the next trading day if d is not a trading day."""
        i = self.index_on_or_after(d)
        return self.closes[i] if i is not None else None

    def window(self, start: date, end: date) -> list[tuple[date, float]]:
        a = bisect.bisect_left(self.dates, start)
        b = bisect.bisect_right(self.dates, end)
        return list(zip(self.dates[a:b], self.closes[a:b]))


_CACHE: dict[str, Series] = {}


def clear_cache() -> None:
    _CACHE.clear()


def load_into_db(db: Session, ticker: str, start: date = MOCK_START) -> int:
    provider = get_market_provider()
    bars = provider.get_history(ticker, start, last_business_day())
    existing = set(db.scalars(select(PriceBar.date).where(PriceBar.ticker == ticker)))
    new = [PriceBar(ticker=ticker, date=b.date, close=b.close, volume=b.volume, source=provider.name)
           for b in bars if b.date not in existing]
    db.add_all(new)
    db.commit()
    return len(new)


def get_series(db: Session, ticker: str) -> Series:
    ticker = ticker.upper()
    if ticker in _CACHE:
        return _CACHE[ticker]
    rows = db.execute(
        select(PriceBar.date, PriceBar.close).where(PriceBar.ticker == ticker).order_by(PriceBar.date)
    ).all()
    stale = not rows or rows[-1][0] < last_business_day() - timedelta(days=3)
    if stale:
        try:
            load_into_db(db, ticker)
            rows = db.execute(
                select(PriceBar.date, PriceBar.close).where(PriceBar.ticker == ticker).order_by(PriceBar.date)
            ).all()
        except Exception as e:  # provider down -> use whatever is cached
            log.warning("Price refresh failed for %s: %s", ticker, e)
    s = Series(ticker, [(d, c) for d, c in rows])
    _CACHE[ticker] = s
    return s
