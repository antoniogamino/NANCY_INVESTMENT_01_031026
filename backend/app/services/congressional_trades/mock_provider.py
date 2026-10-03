"""Realistic-looking but FICTITIOUS trades for development.

These records are NOT real disclosures. They are flagged confidence_level="mock" and
source="mock" so the UI can label them clearly. Replace with the house_clerk adapter
(or another vetted source) for real research.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..reference import company_name
from .base import AMOUNT_BANDS, CongressionalTradesProvider, RawTrade

B = AMOUNT_BANDS

# (ticker, type, asset_type, tx_date, delay_days, band_idx, strike, expiration, contracts, notes)
_MOCK = [
    ("NVDA", "BUY", "leaps_call", date(2023, 11, 22), 27, 5, 12.0, date(2025, 1, 17), 50, "Exercised later (mock)"),
    ("MSFT", "BUY", "leaps_call", date(2023, 6, 16), 25, 4, 300.0, date(2025, 6, 20), 20, None),
    ("AAPL", "BUY", "call", date(2023, 3, 17), 20, 4, 140.0, date(2024, 6, 21), 50, None),
    ("AAPL", "SELL", "stock", date(2024, 7, 11), 30, 7, None, None, None, "Partial sale (mock)"),
    ("GOOGL", "BUY", "leaps_call", date(2024, 1, 12), 21, 4, 100.0, date(2025, 1, 17), 50, None),
    ("CRM", "SELL", "stock", date(2023, 12, 20), 29, 5, None, None, None, None),
    ("PANW", "BUY", "leaps_call", date(2024, 2, 21), 33, 4, 200.0, date(2025, 1, 17), 70, None),
    ("AMZN", "BUY", "call", date(2024, 1, 19), 18, 3, 150.0, date(2025, 1, 17), 30, None),
    ("NVDA", "EXERCISE", "leaps_call", date(2024, 6, 21), 12, 6, 12.0, date(2025, 1, 17), 100, "Option exercise (mock)"),
    ("TSLA", "SELL", "stock", date(2023, 12, 22), 11, 5, None, None, None, None),
    ("AVGO", "BUY", "leaps_call", date(2024, 6, 24), 16, 5, 80.0, date(2025, 6, 20), 20, None),
    ("TEM", "BUY", "leaps_call", date(2025, 1, 14), 23, 2, 20.0, date(2026, 1, 16), 50, "Speculative small cap (mock)"),
    ("VST", "BUY", "leaps_call", date(2025, 1, 14), 23, 3, 50.0, date(2026, 1, 16), 50, None),
    ("V", "SELL", "stock", date(2024, 12, 20), 26, 4, None, None, None, None),
    ("NFLX", "SELL", "stock", date(2024, 12, 31), 20, 4, None, None, None, None),
    ("DIS", "SELL", "stock", date(2024, 12, 31), 20, 3, None, None, None, None),
    ("RBLX", "BUY", "stock", date(2025, 3, 3), 41, 1, None, None, None, "Late filing flag (mock)"),
    ("NVDA", "SELL", "stock", date(2024, 12, 31), 20, 6, None, None, None, "Sold shares at a gain (mock)"),
    ("GOOGL", "BUY", "call", date(2025, 6, 20), 19, 4, 150.0, date(2026, 6, 18), 50, None),
    ("AMZN", "BUY", "call", date(2025, 6, 20), 19, 4, 150.0, date(2026, 6, 18), 50, None),
    ("AAPL", "SELL", "stock", date(2025, 6, 20), 24, 6, None, None, None, None),
    ("MSFT", "BUY", "leaps_call", date(2025, 9, 15), 28, 4, 500.0, date(2027, 1, 15), 25, None),
    ("PANW", "SELL", "stock", date(2025, 11, 4), 24, 4, None, None, None, None),
    ("AVGO", "BUY", "call", date(2026, 1, 16), 30, 4, 300.0, date(2027, 1, 15), 30, None),
    ("TSLA", "BUY", "call", date(2026, 3, 20), 22, 3, 400.0, date(2026, 12, 18), 15, "Short-dated (mock)"),
    ("CRM", "BUY", "leaps_call", date(2026, 5, 15), 25, 3, 200.0, date(2027, 6, 17), 25, None),
    # The user's reference case: buy @ ~$120, disclosed @ ~$138, today ~$145
    ("NVDA", "BUY", "stock", date(2026, 7, 14), 29, 6, None, None, None,
     "Reference case: trade ~$120, disclosure ~$138, today ~$145 (mock)"),
    ("VST", "BUY", "stock", date(2026, 8, 20), 15, 4, None, None, None, None),
    ("GOOGL", "BUY", "leaps_call", date(2026, 9, 2), 18, 4, 280.0, date(2028, 1, 21), 40, "Very recent disclosure (mock)"),
]


class MockTradesProvider(CongressionalTradesProvider):
    name = "mock"

    def fetch(self, since: date | None = None) -> list[RawTrade]:
        out: list[RawTrade] = []
        today = date.today()
        for i, (t, tx, at, d, delay, band, strike, exp, n, notes) in enumerate(_MOCK, start=1):
            disc = d + timedelta(days=delay)
            if disc > today or (since and disc < since):
                continue
            lo, hi = B[band]
            out.append(RawTrade(
                source="mock", owner="Spouse", owner_name="Paul Pelosi (mock)",
                asset=company_name(t) + ("" if at == "stock" else " - Call Options"),
                ticker=t, asset_type=at, transaction_type=tx, transaction_date=d,
                disclosure_date=disc, amount_min=lo, amount_max=hi, strike=strike,
                expiration=exp, contracts=n, notes=notes, source_url=None,
                filing_id=f"MOCK-{i:04d}", confidence_level="mock",
            ))
        return out
