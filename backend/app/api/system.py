from __future__ import annotations

from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..engines import analysis
from ..models import IngestionLog, Trade
from ..services.congressional_trades import HouseClerkProvider
from ..services.market_data import get_market_provider
from ..services.fundamentals import get_fundamentals_provider
from ..services.news import get_news_provider

router = APIRouter(prefix="/api", tags=["system"])

DISCLAIMER = ("Congressional financial disclosures may be reported days or weeks after a transaction. "
              "Historical political trading activity does not guarantee future returns. This platform is "
              "intended for research and educational purposes and does not constitute investment advice.")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/meta")
def meta():
    s = get_settings()
    mp = get_market_provider()
    ai_ready = (s.ai_provider == "anthropic" and bool(s.anthropic_api_key)) or \
               (s.ai_provider == "openai" and bool(s.openai_api_key))
    return {
        "app": s.app_name, "disclaimer": DISCLAIMER, "today": date.today(),
        "providers": {
            "trades": s.trades_provider, "market_data": mp.name,
            "fundamentals": get_fundamentals_provider().name, "news": get_news_provider().name,
            "ai": s.ai_provider if ai_ready else "rules",
        },
        "mock_mode": mp.name == "mock" or s.trades_provider == "mock",
    }


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)):
    trades = list(db.scalars(select(Trade)))
    issues = []
    for t in trades:
        if t.disclosure_date < t.transaction_date:
            issues.append({"id": t.id, "ticker": t.ticker, "issue": "Disclosure date before transaction date"})
        if (t.disclosure_date - t.transaction_date).days > 45:
            issues.append({"id": t.id, "ticker": t.ticker, "issue": "Disclosure later than 45 days"})
        if t.asset_type not in ("stock", "etf") and (t.strike is None or t.expiration is None):
            issues.append({"id": t.id, "ticker": t.ticker, "issue": "Option without strike/expiration"})
        if not t.source_url and t.confidence_level != "mock":
            issues.append({"id": t.id, "ticker": t.ticker, "issue": "Missing source_url"})
    logs = db.scalars(select(IngestionLog).order_by(IngestionLog.started_at.desc()).limit(20))
    return {
        "by_confidence": Counter(t.confidence_level for t in trades),
        "by_source": Counter(t.source for t in trades),
        "by_status": Counter(t.analysis_status for t in trades),
        "issues": issues,
        "ingestion_log": [{"provider": l.provider, "at": l.started_at, "records": l.records,
                           "status": l.status, "message": l.message} for l in logs],
        "field_types": {
            "transaction_date, disclosure_date, amount band, asset, owner, strike, expiration": "OFFICIAL (from filing) or MOCK",
            "price at transaction / disclosure / now": "MARKET DATA (mock when provider=mock)",
            "estimated shares, capital midpoint, open/closed status": "ESTIMATED",
            "returns, scores, decay, technicals, alpha": "CALCULATED",
        },
    }


@router.post("/admin/reseed")
def reseed():
    from ..seed import init_db
    out = init_db(reset=True)
    analysis.clear_cache()
    return out


@router.get("/sources/house-filings")
def house_filings(years: str = Query(None, description="comma separated, e.g. 2025,2026"),
                  last_name: str = "Pelosi"):
    ys = [int(y) for y in years.split(",")] if years else [date.today().year]
    try:
        fl = HouseClerkProvider(last_name).list_filings(ys)
        return {"ok": True, "filings": [f.__dict__ for f in fl]}
    except Exception as e:
        return {"ok": False, "error": str(e), "filings": []}
