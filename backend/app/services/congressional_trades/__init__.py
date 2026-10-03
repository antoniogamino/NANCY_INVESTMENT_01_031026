from __future__ import annotations

from ...config import get_settings
from .base import AMOUNT_BANDS, CongressionalTradesProvider, RawTrade
from .house_clerk import HouseClerkProvider
from .mock_provider import MockTradesProvider


def get_trades_provider() -> CongressionalTradesProvider:
    if get_settings().trades_provider.lower() == "house_clerk":
        return HouseClerkProvider()
    return MockTradesProvider()


__all__ = ["AMOUNT_BANDS", "CongressionalTradesProvider", "RawTrade", "get_trades_provider",
           "HouseClerkProvider", "MockTradesProvider"]
