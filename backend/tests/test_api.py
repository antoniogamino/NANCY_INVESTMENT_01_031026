from fastapi.testclient import TestClient

from app.main import app


def test_endpoints_smoke():
    with TestClient(app) as c:
        for p in ["/api/meta", "/api/dashboard", "/api/trades", "/api/timeline", "/api/performance",
                  "/api/backtest", "/api/signals", "/api/watchlist", "/api/data-quality", "/api/stocks/NVDA"]:
            assert c.get(p).status_code == 200, p


def test_ai_never_recommends():
    with TestClient(app) as c:
        txt = str(c.get("/api/stocks/NVDA").json()["ai"]).lower()
        assert "you should buy" not in txt and "we recommend" not in txt
