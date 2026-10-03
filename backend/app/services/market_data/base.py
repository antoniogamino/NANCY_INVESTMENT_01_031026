from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class Bar:
    date: date
    close: float
    volume: float | None = None


class MarketDataProvider(ABC):
    """Adapter contract for historical daily prices."""

    name: str = "base"

    @abstractmethod
    def get_history(self, ticker: str, start: date, end: date) -> list[Bar]:
        """Return daily bars (ascending) between start and end inclusive."""

    def is_configured(self) -> bool:
        return True
