from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import analytics, dashboard, stocks, system, trades, watchlist
from .config import get_settings
from .seed import init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.getLogger("nii").info("DB init: %s", init_db())
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["*"], allow_headers=["*"])

for r in (system.router, dashboard.router, trades.router, stocks.router, analytics.router, watchlist.router):
    app.include_router(r)
