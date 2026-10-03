from __future__ import annotations

import logging

from ...config import get_settings
from .base import Bar, MarketDataProvider
from .fmp_provider import FMPMarketDataProvider
from .mock_provider import MockMarketDataProvider, last_business_day

log = logging.getLogger(__name__)


def get_market_provider() -> MarketDataProvider:
    """Return the configured provider, falling back to mock if it is not configured."""
    choice = get_settings().market_data_provider.lower()
    if choice == "fmp":
        p = FMPMarketDataProvider()
        if p.is_configured():
            return p
        log.warning("market_data_provider=fmp but FMP_API_KEY missing; using mock")
    return MockMarketDataProvider()


__all__ = ["Bar", "MarketDataProvider", "get_market_provider", "last_business_day"]
