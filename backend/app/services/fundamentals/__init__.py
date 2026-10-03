"""Fundamentals, analyst consensus and earnings calendar adapters."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import httpx

from ...config import get_settings

log = logging.getLogger(__name__)


@dataclass
class Fundamentals:
    ticker: str
    pe: float | None = None
    forward_pe: float | None = None
    peg: float | None = None
    price_to_sales: float | None = None
    ev_ebitda: float | None = None
    gross_margin: float | None = None      # fraction
    operating_margin: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None    # YoY fraction
    beta: float | None = None
    market_cap_b: float | None = None
    analyst_buy: int | None = None
    analyst_hold: int | None = None
    analyst_sell: int | None = None
    target_price: float | None = None
    next_earnings: date | None = None
    source: str = "mock"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["next_earnings"] = self.next_earnings.isoformat() if self.next_earnings else None
        return d


class FundamentalsProvider(ABC):
    name = "base"

    @abstractmethod
    def get(self, ticker: str, current_price: float | None = None) -> Fundamentals: ...


# ticker: pe, fpe, peg, ps, ev/ebitda, gm, om, roe, growth, beta, mcap_b, buy, hold, sell, target_mult, earnings_anchor
_MOCK = {
    "NVDA": (48, 31, 1.1, 24, 40, .75, .62, 1.05, .55, 1.7, 3550, 52, 6, 1, 1.18, date(2025, 11, 19)),
    "AAPL": (33, 30, 2.8, 9.5, 25, .46, .31, 1.45, .06, 1.1, 3300, 24, 15, 3, 1.06, date(2025, 10, 30)),
    "MSFT": (36, 32, 2.2, 13, 25, .69, .45, .33, .15, 1.0, 5000, 55, 5, 0, 1.15, date(2025, 10, 29)),
    "AVGO": (60, 36, 1.6, 22, 38, .77, .40, .25, .40, 1.3, 3100, 36, 5, 0, 1.12, date(2025, 12, 11)),
    "CRM": (40, 24, 1.9, 6.5, 20, .77, .20, .10, .09, 1.15, 160, 34, 14, 2, 1.25, date(2025, 12, 3)),
    "PANW": (110, 55, 3.5, 13, 70, .74, .12, .20, .15, 1.2, 160, 30, 12, 2, 1.15, date(2025, 11, 18)),
    "GOOGL": (27, 23, 1.3, 7.5, 18, .59, .32, .32, .13, 1.05, 3650, 50, 10, 0, 1.10, date(2025, 10, 28)),
    "NFLX": (45, 34, 1.7, 9.0, 32, .47, .29, .40, .16, 1.15, 340, 30, 12, 2, 1.08, date(2025, 10, 21)),
    "DIS": (22, 18, 1.4, 1.8, 13, .37, .14, .08, .04, 1.0, 165, 20, 10, 1, 1.20, date(2025, 11, 13)),
    "RBLX": (None, 95, None, 9.5, 80, .78, -.05, -.4, .30, 1.5, 45, 22, 8, 2, 1.12, date(2025, 10, 30)),
    "AMZN": (34, 28, 1.6, 2.9, 15, .50, .11, .22, .11, 1.2, 1400, 60, 3, 0, 1.22, date(2025, 10, 30)),
    "TSLA": (190, 150, 6.0, 18, 110, .17, .06, .09, -.02, 1.8, 2300, 15, 18, 10, 0.72, date(2025, 10, 22)),
    "VST": (28, 22, 1.2, 4.2, 14, .38, .20, .30, .25, 0.9, 57, 14, 2, 0, 1.15, date(2025, 11, 6)),
    "TEM": (None, None, None, 9.0, None, .55, -.20, -.5, .80, 1.6, 10, 7, 4, 0, 1.25, date(2025, 11, 4)),
    "V": (31, 27, 2.1, 17, 24, .80, .67, .50, .10, 0.9, 800, 30, 6, 0, 1.12, date(2025, 10, 28)),
}


def _next_earnings(anchor: date, today: date | None = None) -> date:
    today = today or date.today()
    d = anchor
    while d < today:
        d += timedelta(days=91)
    return d


class MockFundamentalsProvider(FundamentalsProvider):
    name = "mock"

    def get(self, ticker: str, current_price: float | None = None) -> Fundamentals:
        row = _MOCK.get(ticker.upper())
        if not row:
            return Fundamentals(ticker=ticker, source="unavailable")
        pe, fpe, peg, ps, ev, gm, om, roe, g, beta, mcap, b, h, s, tm, anchor = row
        return Fundamentals(
            ticker=ticker, pe=pe, forward_pe=fpe, peg=peg, price_to_sales=ps, ev_ebitda=ev,
            gross_margin=gm, operating_margin=om, roe=roe, revenue_growth=g, beta=beta,
            market_cap_b=mcap, analyst_buy=b, analyst_hold=h, analyst_sell=s,
            target_price=round(current_price * tm, 2) if current_price else None,
            next_earnings=_next_earnings(anchor), source="mock",
        )


class FMPFundamentalsProvider(FundamentalsProvider):
    """Phase 5 adapter using documented FMP endpoints. Falls back to mock on any error."""
    name = "fmp"
    BASE = "https://financialmodelingprep.com/api/v3"

    def get(self, ticker: str, current_price: float | None = None) -> Fundamentals:
        s = get_settings()
        fb = MockFundamentalsProvider().get(ticker, current_price)
        if not s.fmp_api_key:
            return fb
        try:
            p = {"apikey": s.fmp_api_key}
            r = httpx.get(f"{self.BASE}/ratios-ttm/{ticker}", params=p, timeout=s.http_timeout_s).json()
            k = r[0] if r else {}
            pt = httpx.get(f"{self.BASE}/price-target-consensus", params={**p, "symbol": ticker},
                           timeout=s.http_timeout_s).json()
            return Fundamentals(
                ticker=ticker, pe=k.get("peRatioTTM"), peg=k.get("pegRatioTTM"),
                price_to_sales=k.get("priceToSalesRatioTTM"),
                ev_ebitda=k.get("enterpriseValueMultipleTTM"),
                gross_margin=k.get("grossProfitMarginTTM"), operating_margin=k.get("operatingProfitMarginTTM"),
                roe=k.get("returnOnEquityTTM"),
                target_price=(pt[0].get("targetConsensus") if pt else None) or fb.target_price,
                forward_pe=fb.forward_pe, revenue_growth=fb.revenue_growth, beta=fb.beta,
                next_earnings=fb.next_earnings, source="fmp",
            )
        except Exception as e:
            log.warning("FMP fundamentals failed for %s: %s", ticker, e)
            return fb


def get_fundamentals_provider() -> FundamentalsProvider:
    if get_settings().fundamentals_provider.lower() == "fmp":
        return FMPFundamentalsProvider()
    return MockFundamentalsProvider()
