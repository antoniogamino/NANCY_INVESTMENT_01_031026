"""SQLite data model.

Every trade stores provenance (source, source_url, confidence_level) so the UI can
distinguish OFFICIAL vs ESTIMATED vs CALCULATED vs MOCK values.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64))                 # mock | house_clerk | ...
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    filing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner: Mapped[str] = mapped_column(String(64))                  # Self | Spouse | Joint
    owner_name: Mapped[str] = mapped_column(String(128))
    asset: Mapped[str] = mapped_column(String(256))
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(32))             # stock | call | put | leaps_call | ...
    transaction_type: Mapped[str] = mapped_column(String(16))       # BUY | SELL | EXERCISE
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    disclosure_date: Mapped[date] = mapped_column(Date, index=True)
    amount_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    strike: Mapped[float | None] = mapped_column(Float, nullable=True)
    expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    contracts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # official = read from filing; estimated = inferred; mock = development data
    confidence_level: Mapped[str] = mapped_column(String(16), default="official")
    analysis_status: Mapped[str] = mapped_column(String(32), default="analyzed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_ticker_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="mock")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    records: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
