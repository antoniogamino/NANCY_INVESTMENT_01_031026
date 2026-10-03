"""Trade ingestion: provider -> normalised RawTrade -> SQLite (deduplicated)."""
from __future__ import annotations

import csv
import io
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import IngestionLog, Trade
from .congressional_trades import CongressionalTradesProvider, RawTrade
from .reference import sector_of

VALID_TX = {"BUY", "SELL", "EXERCISE"}
VALID_ASSET = {"stock", "etf", "call", "put", "leaps_call", "leaps_put", "other"}


def _key(t) -> tuple:
    return (t.ticker, t.transaction_type, t.transaction_date, t.disclosure_date, t.asset_type, t.strike,
            t.amount_min)


def upsert_trades(db: Session, raws: list[RawTrade]) -> int:
    existing = {_key(t) for t in db.scalars(select(Trade))}
    added = 0
    for r in raws:
        if _key(r) in existing:
            continue
        status = "analyzed"
        if r.disclosure_date < r.transaction_date:
            status = "data_error"
        elif (r.disclosure_date - r.transaction_date).days > 45:
            status = "late_filing"
        db.add(Trade(
            source=r.source, source_url=r.source_url, filing_id=r.filing_id, owner=r.owner,
            owner_name=r.owner_name, asset=r.asset, ticker=r.ticker.upper(), sector=sector_of(r.ticker.upper()),
            asset_type=r.asset_type, transaction_type=r.transaction_type, transaction_date=r.transaction_date,
            disclosure_date=r.disclosure_date, amount_min=r.amount_min, amount_max=r.amount_max,
            strike=r.strike, expiration=r.expiration, contracts=r.contracts, notes=r.notes,
            confidence_level=r.confidence_level, analysis_status=status,
        ))
        existing.add(_key(r))
        added += 1
    db.commit()
    return added


def ingest(db: Session, provider: CongressionalTradesProvider) -> int:
    log = IngestionLog(provider=provider.name)
    try:
        n = upsert_trades(db, provider.fetch())
        log.records, log.status = n, "ok"
    except Exception as e:
        n, log.status, log.message = 0, "error", str(e)[:500]
    db.add(log)
    db.commit()
    return n


CSV_COLUMNS = ["owner", "owner_name", "asset", "ticker", "asset_type", "transaction_type",
               "transaction_date", "disclosure_date", "amount_min", "amount_max", "strike",
               "expiration", "contracts", "notes", "source_url", "confidence_level"]


def parse_csv(text: str, source: str = "csv_import") -> tuple[list[RawTrade], list[str]]:
    """Parse a manually transcribed CSV (one row per transaction). Returns (trades, errors)."""
    rows, errors = [], []
    reader = csv.DictReader(io.StringIO(text))

    def f(v):
        return float(str(v).replace(",", "").replace("$", "")) if v not in (None, "") else None

    def d(v):
        return date.fromisoformat(v) if v else None

    for i, row in enumerate(reader, start=2):
        try:
            tx = row["transaction_type"].strip().upper()
            at = row.get("asset_type", "stock").strip().lower() or "stock"
            if tx not in VALID_TX:
                raise ValueError(f"transaction_type must be one of {VALID_TX}")
            if at not in VALID_ASSET:
                raise ValueError(f"asset_type must be one of {VALID_ASSET}")
            conf = (row.get("confidence_level") or "official").strip().lower()
            if conf not in {"official", "estimated"}:
                raise ValueError("confidence_level must be official or estimated")
            rows.append(RawTrade(
                source=source, owner=row.get("owner") or "Spouse", owner_name=row.get("owner_name") or "Paul Pelosi",
                asset=row.get("asset") or row["ticker"], ticker=row["ticker"].strip().upper(), asset_type=at,
                transaction_type=tx, transaction_date=d(row["transaction_date"]),
                disclosure_date=d(row["disclosure_date"]), amount_min=f(row.get("amount_min")),
                amount_max=f(row.get("amount_max")), strike=f(row.get("strike")), expiration=d(row.get("expiration")),
                contracts=int(f(row.get("contracts"))) if row.get("contracts") else None, notes=row.get("notes"),
                source_url=row.get("source_url"), confidence_level=conf,
            ))
        except Exception as e:
            errors.append(f"line {i}: {e}")
    return rows, errors
