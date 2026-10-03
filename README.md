# NANCY INVESTMENT INTELLIGENCE

Plataforma **local** de análisis de las operaciones bursátiles reportadas en los *disclosures* del Congreso de EE. UU. (Nancy / Paul Pelosi).
No copia trades: mide **si una operación reportada sigue siendo relevante hoy**. Para eso evalúa cuánto se movió el precio antes de que la operación se hiciera pública, el contexto técnico, fundamental y de mercado, y qué tan útil habría sido seguirla *después* del disclosure.

> Congressional financial disclosures may be reported days or weeks after a transaction. Historical political trading activity does not guarantee future returns. This platform is intended for research and educational purposes and does not constitute investment advice.

---

## 1. Inicio rápido

### Windows (un clic)
```
start.bat
```
La primera vez crea `backend\.venv`, instala dependencias (pip + npm), levanta ambos servidores y abre `http://localhost:5173`.

### Manual
**Backend** (Python 3.11+):
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    ·    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://127.0.0.1:8000  ·  docs: /docs
```
**Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173 (proxy /api → :8000)
```
**Tests**:
```bash
cd backend && python -m pytest -q
```

Al primer arranque se crea `backend/data/nii.db` (SQLite) con **MOCK DATA**. Para reiniciarla: `python -m app.seed --reset`, o el botón *Reset & reseed* en **Data & Sources**.

---

## 2. ⚠ Mock data

Mientras `TRADES_PROVIDER=mock` / `MARKET_DATA_PROVIDER=mock`, **todas las operaciones, precios, fundamentales y noticias son ficticios**. Son realistas en estructura, pero **no son disclosures reales**. La interfaz lo indica con la etiqueta morada `MOCK` y el banner **MOCK DATA MODE**.

Caso de referencia incluido en la mock data (NVDA, compra de acciones):

| Momento | Precio |
|---|---|
| Operación (2026‑07‑14) | $120 |
| Disclosure (2026‑08‑12) | $138 |
| Hoy | $145 |

Resultado → antes del disclosure **+15.0%**, después **+5.1%**, total **+20.8%**. El 72% del movimiento favorable ocurrió antes de que el público pudiera saberlo. Opportunity Decay **57 · PARTIALLY DECAYED**.

---

## 3. Arquitectura

```
nancy-investment-intelligence/
├─ start.bat · .env.example · README.md
├─ backend/                      FastAPI + SQLAlchemy + SQLite
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ main.py                 app + CORS + init DB
│  │  ├─ config.py               settings desde .env
│  │  ├─ database.py · models.py Trade, PriceBar, WatchlistItem, IngestionLog
│  │  ├─ seed.py                 crea tablas + carga mock data
│  │  ├─ api/                    dashboard · trades · stocks · analytics · watchlist · system
│  │  ├─ services/               ── adaptadores intercambiables ──
│  │  │  ├─ congressional_trades/  mock_provider · house_clerk (oficial, experimental)
│  │  │  ├─ market_data/           mock_provider · fmp_provider
│  │  │  ├─ fundamentals/          mock · fmp
│  │  │  ├─ news/                  mock
│  │  │  ├─ prices.py              caché SQLite delante del proveedor
│  │  │  └─ ingestion.py           normalización, deduplicación, import CSV
│  │  ├─ engines/                ── lógica analítica pura ──
│  │  │  ├─ technicals.py          SMA, RSI(14, Wilder), momentum, volatilidad, 52W
│  │  │  ├─ decay.py               Opportunity Decay
│  │  │  ├─ scoring.py             Trade Intelligence Score (A–K)
│  │  │  ├─ analysis.py            orquestación por trade / ticker
│  │  │  ├─ signals.py             Signal Engine por ticker
│  │  │  ├─ performance.py         retornos desde la operación vs desde el disclosure, alpha
│  │  │  └─ backtest.py            "If I followed Pelosi"
│  │  └─ ai/                     reglas determinísticas → Anthropic / OpenAI opcional
│  └─ tests/
└─ frontend/                     React 18 + TS + Vite + Tailwind + Recharts
   └─ src/
      ├─ components/  Layout · TradesTable · Analysis (Decay/Score) · chart · ui
      ├─ pages/       Dashboard · Trades · StockDetail · Timeline · Signals ·
      │               Performance · Backtest · Watchlist · DataSources
      └─ lib/         api · types · format
```

El sistema **funciona aunque una API no esté configurada**: cada adaptador cae a `mock` (con un aviso en el log) y la IA cae al motor de reglas.

---

## 4. Procedencia de datos

Cada operación guarda `source, transaction_date, disclosure_date, owner, asset, ticker, asset_type, transaction_type, amount_min, amount_max, strike, expiration, notes, source_url, confidence_level`.

| Etiqueta | Significado | Ejemplos |
|---|---|---|
| `OFFICIAL` | leído del filing | fechas, banda de monto, instrumento, strike |
| `MARKET` | proveedor de precios | precio de cierre |
| `EST` | estimación (nunca se presenta como hecho) | precio de ejecución ≈ cierre del día, acciones estimadas, capital (punto medio), abierta/cerrada |
| `CALC` | cálculo propio | retornos, scores, decay, técnicos, alpha |
| `MOCK` | dato ficticio de desarrollo | todo en modo mock |

El precio "al momento de la operación" es el **cierre de ese día** (o del siguiente día hábil). El filing no reporta precio de ejecución. En opciones se usa el **subyacente**, porque la prima no se reporta.

---

## 5. Metodologías

### Trade Intelligence Score (0–100) — relevancia, no recomendación
| Factor | Peso | Lógica (resumen) |
|---|---|---|
| A Disclosure Delay | 8 | ≤7 d = 100 → 45 d = 35; >45 d (fuera de plazo STOCK Act) = 15 |
| B Price Drift | 12 | movimiento favorable desde la operación; mucho recorrido = menos relevancia |
| C Valuation | 10 | PEG, Forward P/E, P/S, EV/EBITDA (P/E se muestra) |
| D Momentum | 12 | 1S·1M·3M·6M·1A ponderados .1/.2/.3/.2/.2 |
| E Technical | 12 | sobre SMA20/50/200, RSI 40–65 ideal, >75 sobrecompra, distancia a máximo 52S |
| F Analyst | 8 | % Buy + upside vs precio objetivo |
| G Earnings Risk | 6 | ≤3 d alto · ≤10 d elevado · ≤21 d moderado |
| H Sector Momentum | 8 | ETF sectorial 3M vs SPY |
| I Market Context | 8 | acción 3M vs promedio SPY/QQQ |
| J Instrument | 8 | LEAPS/ITM = convicción; corto plazo/OTM = especulativo; expirado = 20 |
| K Opportunity Decay | 8 | ver abajo |

* Para **SELL**, los factores direccionales (B, C, D, E, F, H, I) se espejan (100 − x): debilidad hace más relevante una venta.
* **Descuento por antigüedad**: ×0.9 si el disclosure tiene >180 días, ×0.8 si tiene >365.
* Clasificación: 80–100 STRONG WATCH · 65–79 INTERESTING · 50–64 NEUTRAL · 35–49 WEAK · 0–34 AVOID / LOW RELEVANCE.

### Opportunity Decay
```
antes   = P_disclosure / P_operación − 1   (no capturable por el público)
después = P_hoy        / P_disclosure  − 1
total   = P_hoy        / P_operación   − 1
score = 100 − 1.6·antes% − 1.2·después% − min(25, 0.25·días desde disclosure) (+ hasta 10 si antes < 0)
```
≥70 OPPORTUNITY LIKELY INTACT · 45–69 PARTIALLY DECAYED · 25–44 MOSTLY PRICED IN · <25 LIKELY TOO LATE. Es una heurística, no un pronóstico.

### Performance
Retornos a 1S/1M/3M/6M/1A desde la **fecha de operación** ("¿fue buena la operación?") y desde la **fecha de disclosure** ("¿hubiera sido buena estrategia seguirla públicamente?"), con alpha vs SPY y vs QQQ. *Lag cost* = la diferencia entre ambos.

### Backtest
Entra al cierre del día k (0/1/3/5) después del disclosure y mantiene 30/90/180/365 días. Equal‑weight entre posiciones abiertas, con rebalanceo diario; el efectivo sin uso rinde 0%. Se compara contra SPY, QQQ y Buy & Hold con las mismas entradas. Métricas: capital final, retorno, CAGR, max drawdown, win rate, número de trades y Sharpe aproximado. No incluye costos, impuestos ni slippage.

---

## 6. IA

* Por defecto, `AI_PROVIDER=rules`: análisis determinístico sin API.
* Opcional: `AI_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`, o `AI_PROVIDER=openai` + `OPENAI_API_KEY`.
* El LLM solo recibe hechos calculados y debe devolver las 8 secciones en JSON. Una respuesta que contenga recomendaciones ("you should buy", "we recommend"…) se **rechaza** y se usa el motor de reglas. Nunca afirma conocer el motivo de la operación.

---

## 7. Fase 5 — fuentes reales

1. **Disclosures oficiales (House Clerk)**: `TRADES_PROVIDER=house_clerk`. *Data & Sources → Fetch index* descarga el índice anual público (`{AÑO}FD.zip`, una petición por año, con caché) y lista los PTR de Pelosi con su PDF oficial. Las transacciones dentro del PDF se transcriben e importan por **CSV** (*Load template* → *Import*) con `confidence_level=official`. No hay scraping agresivo.
2. **Precios y fundamentales**: `MARKET_DATA_PROVIDER=fmp`, `FUNDAMENTALS_PROVIDER=fmp`, `FMP_API_KEY=...` (verifica los endpoints de tu plan FMP). Para agregar otro proveedor, implementa `MarketDataProvider.get_history()` o `FundamentalsProvider.get()` y regístralo en el `__init__.py` del servicio.
3. Después de cambiar de proveedor, borra `backend/data/nii.db` o usa *Reset & reseed*.

---

## 8. API (resumen)

`GET /api/meta` · `/api/dashboard` · `/api/trades` · `/api/trades/{id}` · `POST /api/trades/import` · `/api/trades/template.csv` · `/api/stocks/{ticker}?trade_id=` · `/api/timeline` · `/api/performance` · `/api/backtest?capital&entry_lag&hold_days&include_sells` · `/api/backtest/grid` · `/api/signals` · `GET/POST/DELETE /api/watchlist` · `/api/data-quality` · `/api/sources/house-filings?years=` · `POST /api/admin/reseed`. Documentación interactiva en `http://127.0.0.1:8000/docs`.

## 9. Roadmap
- [x] Fase 1 — arquitectura, backend, SQLite, dashboard con mock data
- [x] Fase 2 — modelo de datos, ingestión, detalle de acción, gráficas
- [x] Fase 3 — scoring engine, opportunity decay, signals, performance
- [x] Fase 4 — backtesting
- [ ] Fase 5 — conectar y validar fuentes reales (adaptadores listos: House Clerk index, FMP, import CSV)
