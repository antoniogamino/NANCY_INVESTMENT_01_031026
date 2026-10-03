"""News adapter layer. Mock headlines only for now (clearly labelled)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta

from ...config import get_settings
from ..reference import company_name


@dataclass
class NewsItem:
    date: date
    headline: str
    source: str
    url: str | None = None
    sentiment: str = "neutral"   # positive | negative | neutral


class NewsProvider(ABC):
    name = "base"

    @abstractmethod
    def get(self, ticker: str, limit: int = 5) -> list[NewsItem]: ...


class MockNewsProvider(NewsProvider):
    name = "mock"
    _T = [
        ("{n} scheduled to report quarterly results", "neutral"),
        ("Analysts revisit price targets on {n} after sector rally", "positive"),
        ("Regulatory scrutiny headline mentions {n}", "negative"),
        ("{n} announces product update at industry event", "positive"),
        ("Options activity elevated in {t}", "neutral"),
    ]

    def get(self, ticker: str, limit: int = 5) -> list[NewsItem]:
        n = company_name(ticker)
        today = date.today()
        return [NewsItem(today - timedelta(days=3 * i + 1), f"[MOCK] {h.format(n=n, t=ticker)}", "mock", None, s)
                for i, (h, s) in enumerate(self._T[:limit])]


def get_news_provider() -> NewsProvider:
    _ = get_settings().news_provider
    return MockNewsProvider()
