"""Create tables and load development data.  Run:  python -m app.seed [--reset]"""
from __future__ import annotations

import sys

from .database import Base, SessionLocal, engine
from .models import PriceBar, Trade, WatchlistItem
from .services import prices
from .services.congressional_trades import get_trades_provider
from .services.ingestion import ingest
from .services.reference import all_series_tickers


def init_db(reset: bool = False) -> dict:
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    prices.clear_cache()
    db = SessionLocal()
    try:
        out = {"trades_added": 0, "bars_added": 0}
        if db.query(Trade).count() == 0:
            out["trades_added"] = ingest(db, get_trades_provider())
        tickers = set(all_series_tickers()) | {t for (t,) in db.query(Trade.ticker).distinct()}
        for t in sorted(tickers):
            if db.query(PriceBar).filter(PriceBar.ticker == t).count() == 0:
                out["bars_added"] += prices.load_into_db(db, t)
        if db.query(WatchlistItem).count() == 0:
            db.add_all([WatchlistItem(ticker=t) for t in ("NVDA", "GOOGL", "VST", "AVGO")])
            db.commit()
        return out
    finally:
        db.close()


if __name__ == "__main__":
    print(init_db(reset="--reset" in sys.argv))
