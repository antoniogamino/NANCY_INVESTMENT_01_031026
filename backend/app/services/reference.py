"""Static reference data: company names, sectors and sector ETFs."""
from __future__ import annotations

COMPANIES: dict[str, dict] = {
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology"},
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology"},
    "AVGO": {"name": "Broadcom Inc.", "sector": "Technology"},
    "CRM": {"name": "Salesforce, Inc.", "sector": "Technology"},
    "PANW": {"name": "Palo Alto Networks, Inc.", "sector": "Technology"},
    "GOOGL": {"name": "Alphabet Inc. Class A", "sector": "Communication Services"},
    "NFLX": {"name": "Netflix, Inc.", "sector": "Communication Services"},
    "DIS": {"name": "The Walt Disney Company", "sector": "Communication Services"},
    "RBLX": {"name": "Roblox Corporation", "sector": "Communication Services"},
    "AMZN": {"name": "Amazon.com, Inc.", "sector": "Consumer Discretionary"},
    "TSLA": {"name": "Tesla, Inc.", "sector": "Consumer Discretionary"},
    "VST": {"name": "Vistra Corp.", "sector": "Utilities"},
    "TEM": {"name": "Tempus AI, Inc.", "sector": "Health Care"},
    "V": {"name": "Visa Inc.", "sector": "Financials"},
}

SECTOR_ETF: dict[str, str] = {
    "Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Utilities": "XLU",
    "Health Care": "XLV",
    "Financials": "XLF",
}

BENCHMARKS = ["SPY", "QQQ"]


def company_name(ticker: str) -> str:
    return COMPANIES.get(ticker, {}).get("name", ticker)


def sector_of(ticker: str) -> str | None:
    return COMPANIES.get(ticker, {}).get("sector")


def sector_etf(ticker: str) -> str | None:
    s = sector_of(ticker)
    return SECTOR_ETF.get(s) if s else None


def all_series_tickers() -> list[str]:
    return list(COMPANIES) + BENCHMARKS + sorted(set(SECTOR_ETF.values()))
