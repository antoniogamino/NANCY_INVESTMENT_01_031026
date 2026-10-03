"""Financial Modeling Prep adapter (Phase 5). Requires FMP_API_KEY in .env.

Uses the documented REST API only (no scraping). Endpoint paths may change between FMP
plan versions — verify against https://site.financialmodelingprep.com/developer/docs.
"""
from __future__ import annotations

from datetime import date

import httpx

from ...config import get_settings
from .base import Bar, MarketDataProvider

BASE = "https://financialmodelingprep.com/api/v3"


class FMPMarketDataProvider(MarketDataProvider):
    name = "fmp"

    def __init__(self) -> None:
        self.s = get_settings()

    def is_configured(self) -> bool:
        return bool(self.s.fmp_api_key)

    def get_history(self, ticker: str, start: date, end: date) -> list[Bar]:
        if not self.is_configured():
            raise RuntimeError("FMP_API_KEY not configured")
        r = httpx.get(
            f"{BASE}/historical-price-full/{ticker}",
            params={"from": start.isoformat(), "to": end.isoformat(), "apikey": self.s.fmp_api_key},
            timeout=self.s.http_timeout_s,
            headers={"User-Agent": self.s.http_user_agent},
        )
        r.raise_for_status()
        rows = r.json().get("historical", [])
        bars = [Bar(date.fromisoformat(x["date"]), float(x.get("adjClose") or x["close"]), x.get("volume"))
                for x in rows]
        return sorted(bars, key=lambda b: b.date)
