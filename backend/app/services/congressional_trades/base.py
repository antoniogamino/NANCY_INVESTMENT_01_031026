from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawTrade:
    """Normalised trade record produced by every congressional-trades adapter."""

    source: str
    owner: str                      # Self | Spouse | Joint | Dependent
    owner_name: str
    asset: str
    ticker: str
    asset_type: str                 # stock | call | put | leaps_call | leaps_put | etf | other
    transaction_type: str           # BUY | SELL | EXERCISE
    transaction_date: date
    disclosure_date: date
    amount_min: float | None = None
    amount_max: float | None = None
    strike: float | None = None
    expiration: date | None = None
    contracts: int | None = None
    notes: str | None = None
    source_url: str | None = None
    filing_id: str | None = None
    confidence_level: str = "official"   # official | estimated | mock
    extra: dict = field(default_factory=dict)


class CongressionalTradesProvider(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, since: date | None = None) -> list[RawTrade]:
        ...

    def is_configured(self) -> bool:
        return True


# Standard value bands used on House Periodic Transaction Reports
AMOUNT_BANDS: list[tuple[float, float]] = [
    (1_001, 15_000), (15_001, 50_000), (50_001, 100_000), (100_001, 250_000),
    (250_001, 500_000), (500_001, 1_000_000), (1_000_001, 5_000_000),
    (5_000_001, 25_000_000), (25_000_001, 50_000_000),
]
