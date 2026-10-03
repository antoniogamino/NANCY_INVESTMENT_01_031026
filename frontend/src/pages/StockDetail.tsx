import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  CartesianGrid, ComposedChart, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { DecayPanel, ScoreBreakdown } from "../components/Analysis";
import { C, DarkTooltip, Legend, axisProps } from "../components/chart";
import { Badge, Card, DataTag, ErrorBox, Loading, ScoreBar, ScoreGauge, Segmented, TxBadge } from "../components/ui";
import { api, useApi } from "../lib/api";
import { fmtCompact, fmtMoney, fmtNum, fmtPct, fmtRange, instrumentLabel, shortDate, toneOfNumber } from "../lib/format";
import type { AIAnalysis, TickerSignals, TradeAnalysis } from "../lib/types";

interface Ctx {
  ticker: string; name: string; price: number; as_of: string; sector_etf: string | null; sector_3m: number | null;
  price_data_type: string;
  tech: {
    price: number; sma20: number | null; sma50: number | null; sma200: number | null; rsi14: number | null;
    high52: number; low52: number; dist_high52: number; dist_low52: number; vol_3m: number | null; change_1d: number | null;
    momentum: Record<string, number | null>;
  };
  fundamentals: Record<string, number | string | null>;
  sector_momentum: Record<string, number | null> | null;
  spy_momentum: Record<string, number | null>;
  qqq_momentum: Record<string, number | null>;
}
interface StockData {
  ticker: string; context: Ctx;
  history: { date: string; close: number; sma50: number | null; sma200: number | null }[];
  markers: { date: string; kind: "BUY" | "SELL" | "DISCLOSURE"; trade_id: number; price: number | null; label: string }[];
  relative_1y: { date: string; stock: number; spy: number; sector?: number }[];
  trades: TradeAnalysis[]; focus: TradeAnalysis | null; ai: AIAnalysis | null; signals: TickerSignals;
  news: { date: string; headline: string; source: string; sentiment: string }[];
}

const RANGES = [{ value: 126, label: "6M" }, { value: 252, label: "1Y" }, { value: 756, label: "3Y" }, { value: 99999, label: "ALL" }];

function KV({ k, v, tone, tag }: { k: string; v: React.ReactNode; tone?: string; tag?: string }) {
  return (
    <div className="flex items-center justify-between py-1 text-xs">
      <span className="text-mute">{k}</span>
      <span className={`num flex items-center gap-1.5 ${tone ?? "text-ink"}`}>{v}{tag && <DataTag kind={tag} />}</span>
    </div>
  );
}

export default function StockDetail() {
  const { ticker = "" } = useParams();
  const [sp] = useSearchParams();
  const tradeId = sp.get("trade");
  const nav = useNavigate();
  const path = `/api/stocks/${ticker.toUpperCase()}${tradeId ? `?trade_id=${tradeId}` : ""}`;
  const { data, error, loading, reload } = useApi<StockData>(path);
  const [range, setRange] = useState(756);
  const [wlMsg, setWlMsg] = useState<string | null>(null);

  const hist = useMemo(() => (data ? data.history.slice(-range) : []), [data, range]);
  const firstDate = hist[0]?.date;

  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading || !data) return <Loading label={`Analyzing ${ticker.toUpperCase()}`} />;

  const { context: ctx, focus: f, ai, signals } = data;
  const t = ctx.tech, fu = ctx.fundamentals;
  const markers = data.markers.filter((m) => firstDate && m.date >= firstDate);
  const focusMarkers = markers.filter((m) => !f || m.trade_id === f.id);
  const otherMarkers = markers.filter((m) => f && m.trade_id !== f.id && m.kind !== "DISCLOSURE");
  const tgt = fu.target_price as number | null;
  const upside = tgt ? tgt / ctx.price - 1 : null;
  const nb = (fu.analyst_buy as number) ?? 0, nh = (fu.analyst_hold as number) ?? 0, ns = (fu.analyst_sell as number) ?? 0;
  const ntot = nb + nh + ns || 1;
  const dte = fu.next_earnings ? Math.round((new Date(fu.next_earnings + "T00:00:00").getTime() - Date.now()) / 86400000) : null;

  const addWatch = async () => {
    try {
      await api("/api/watchlist", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker: ctx.ticker }) });
      setWlMsg("Added to watchlist");
    } catch (e) {
      setWlMsg((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      {/* header */}
      <div className="card flex flex-wrap items-center gap-x-8 gap-y-3 px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white">{ctx.ticker}</h1>
            <Badge>{(f?.sector ?? signals.sector) || "—"}</Badge>
            <DataTag kind={ctx.price_data_type} />
          </div>
          <div className="text-xs text-mute">{ctx.name}</div>
        </div>
        <div>
          <div className="label">Current</div>
          <div className="num text-2xl font-semibold text-white">{fmtMoney(ctx.price)}</div>
          <div className={`num text-[11px] ${toneOfNumber(t.change_1d)}`}>{fmtPct(t.change_1d, 2)} 1D</div>
        </div>
        {f && (
          <>
            <div><div className="label">@ Trade</div><div className="num text-lg text-ink">{fmtMoney(f.price_at_transaction)}</div><div className="text-[10px] text-mute">{shortDate(f.transaction_date)}</div></div>
            <div><div className="label">@ Disclosure</div><div className="num text-lg text-ink">{fmtMoney(f.price_at_disclosure)}</div><div className="text-[10px] text-mute">{shortDate(f.disclosure_date)}</div></div>
            <div><div className="label">Since disclosure</div><div className={`num text-lg font-semibold ${toneOfNumber(f.change_since_disclosure)}`}>{fmtPct(f.change_since_disclosure)}</div><div className="text-[10px] text-mute">follower result</div></div>
          </>
        )}
        <div className="ml-auto flex items-center gap-4">
          {f && <ScoreGauge score={f.score.score} label={f.score.classification} size={110} />}
          <div className="flex flex-col gap-1">
            <button className="btn" onClick={addWatch}>+ Watchlist</button>
            {wlMsg && <span className="text-[10px] text-mute">{wlMsg}</span>}
          </div>
        </div>
      </div>

      {/* chart + trade card */}
      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <Card title="Price history" right={<Segmented value={range} options={RANGES} onChange={setRange} />}>
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <Legend items={[{ label: ctx.ticker, color: C.s1 }, { label: "SMA 50", color: C.s3, dashed: true }, { label: "SMA 200", color: C.s4, dashed: true }]} />
            <div className="flex items-center gap-3 text-[11px] text-ink2">
              <span className="flex items-center gap-1"><span className="text-good">▲</span>BUY</span>
              <span className="flex items-center gap-1"><span className="text-bad">▼</span>SELL</span>
              <span className="flex items-center gap-1"><span className="inline-block h-3 w-0 border-l border-dashed border-warn" />DISCLOSURE</span>
            </div>
          </div>
          <div className="h-[360px]">
            <ResponsiveContainer>
              <ComposedChart data={hist} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="date" {...axisProps} minTickGap={48} tickFormatter={(d: string) => d.slice(0, 7)} />
                <YAxis {...axisProps} domain={["auto", "auto"]} width={56} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                <Tooltip content={<DarkTooltip fmt={(v) => fmtMoney(v)} />} cursor={{ stroke: "#2a323e" }} />
                <Line dataKey="close" name={ctx.ticker} stroke={C.s1} strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line dataKey="sma50" name="SMA 50" stroke={C.s3} strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
                <Line dataKey="sma200" name="SMA 200" stroke={C.s4} strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
                {focusMarkers.filter((m) => m.kind === "DISCLOSURE").map((m) => (
                  <ReferenceLine key={`d${m.trade_id}`} x={m.date} stroke={C.warn} strokeDasharray="3 3"
                    label={{ value: "DISCLOSURE", fill: C.warn, fontSize: 9, position: "insideTopRight" }} />
                ))}
                {otherMarkers.map((m) => (
                  <ReferenceDot key={`o${m.trade_id}`} x={m.date} y={m.price ?? undefined} r={4}
                    fill={m.kind === "SELL" ? C.bad : C.good} fillOpacity={0.35} stroke="#0e1217" strokeWidth={2} />
                ))}
                {focusMarkers.filter((m) => m.kind !== "DISCLOSURE").map((m) => (
                  <ReferenceDot key={`f${m.trade_id}`} x={m.date} y={m.price ?? undefined} r={7}
                    fill={m.kind === "SELL" ? C.bad : C.good} stroke="#0e1217" strokeWidth={2}
                    label={{ value: m.kind, fill: m.kind === "SELL" ? C.bad : C.good, fontSize: 10, position: m.kind === "SELL" ? "top" : "bottom", fontWeight: 700 }} />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[10px] text-mute">Large markers = selected trade; faded markers = other disclosed trades in {ctx.ticker}.</p>
        </Card>

        {f ? (
          <Card title="Pelosi trade" right={<TxBadge type={f.transaction_type} />}>
            <KV k="Transaction date" v={f.transaction_date} tag={f.confidence_level} />
            <KV k="Disclosure date" v={f.disclosure_date} tag={f.confidence_level} />
            <KV k="Reporting delay" v={`${f.delay_days} days`} tone={f.delay_days > 45 ? "text-bad" : f.delay_days > 30 ? "text-warn" : "text-ink"} />
            <KV k="Type" v={f.transaction_type} />
            <KV k="Amount (band)" v={fmtRange(f.amount_min, f.amount_max)} tag={f.confidence_level} />
            <KV k="Instrument" v={instrumentLabel(f.asset_type)} />
            <KV k="Strike" v={f.strike ? fmtMoney(f.strike) : "—"} />
            <KV k="Expiration" v={f.expiration ?? "—"} />
            {f.contracts && <KV k="Contracts" v={f.contracts} />}
            <KV k="Est. price @ trade" v={fmtMoney(f.price_at_transaction)} tag="estimated" />
            {f.est_shares && <KV k="Est. shares" v={f.est_shares.toLocaleString()} tag="estimated" />}
            <KV k="Owner" v={f.owner_name} />
            <div className="mt-2 rounded border border-line bg-bg p-2 text-[11px] text-ink2">{f.instrument.detail}</div>
            {f.notes && <div className="mt-2 text-[11px] text-mute">Note: {f.notes}</div>}
            {data.trades.length > 1 && (
              <div className="mt-3">
                <div className="label mb-1">Other {ctx.ticker} trades</div>
                <div className="flex flex-wrap gap-1">
                  {data.trades.map((x) => (
                    <button key={x.id} onClick={() => nav(`/stock/${ctx.ticker}?trade=${x.id}`)}
                      className={`rounded border px-1.5 py-0.5 text-[10px] num ${x.id === f.id ? "border-accent text-white" : "border-line2 text-mute hover:text-ink"}`}>
                      {x.transaction_type === "SELL" ? "▼" : "▲"} {x.transaction_date}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </Card>
        ) : (
          <Card title="Pelosi trade"><p className="text-xs text-mute">No disclosed trades for this ticker. Market analysis only.</p></Card>
        )}
      </div>

      {f && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Opportunity decay"><DecayPanel decay={f.decay} /></Card>
          <Card title="Trade intelligence score" right={<span className="num text-[10px] normal-case tracking-normal text-mute">base {f.score.base_score} × age {f.score.age_discount}</span>}>
            <ScoreBreakdown components={f.score.components} />
          </Card>
        </div>
      )}

      {/* market analysis */}
      <h2 className="pt-2 text-xs font-semibold uppercase tracking-[0.14em] text-ink2">Market analysis</h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Technical">
          <KV k="SMA 20" v={fmtMoney(t.sma20)} tone={t.price > (t.sma20 ?? 0) ? "text-good" : "text-bad"} />
          <KV k="SMA 50" v={fmtMoney(t.sma50)} tone={t.price > (t.sma50 ?? 0) ? "text-good" : "text-bad"} />
          <KV k="SMA 200" v={fmtMoney(t.sma200)} tone={t.price > (t.sma200 ?? 0) ? "text-good" : "text-bad"} />
          <KV k="RSI 14" v={fmtNum(t.rsi14, 0)} tone={t.rsi14 && t.rsi14 > 70 ? "text-warn" : t.rsi14 && t.rsi14 < 30 ? "text-warn" : "text-ink"} />
          <KV k="52W high" v={`${fmtMoney(t.high52)} (${fmtPct(t.dist_high52)})`} />
          <KV k="52W low" v={`${fmtMoney(t.low52)} (${fmtPct(t.dist_low52)})`} />
          <KV k="Volatility 3M" v={t.vol_3m ? `${(t.vol_3m * 100).toFixed(0)}%` : "—"} tag="calculated" />
        </Card>
        <Card title="Valuation" right={<DataTag kind={String(fu.source)} />}>
          <KV k="P/E" v={fmtNum(fu.pe as number)} />
          <KV k="Forward P/E" v={fmtNum(fu.forward_pe as number)} />
          <KV k="PEG" v={fmtNum(fu.peg as number, 2)} />
          <KV k="Price / Sales" v={fmtNum(fu.price_to_sales as number)} />
          <KV k="EV / EBITDA" v={fmtNum(fu.ev_ebitda as number)} />
          <KV k="Market cap" v={fu.market_cap_b ? fmtCompact((fu.market_cap_b as number) * 1e9) : "—"} />
        </Card>
        <Card title="Fundamentals" right={<DataTag kind={String(fu.source)} />}>
          <KV k="Gross margin" v={fmtPct(fu.gross_margin as number, 0)} />
          <KV k="Operating margin" v={fmtPct(fu.operating_margin as number, 0)} tone={toneOfNumber(fu.operating_margin as number)} />
          <KV k="ROE" v={fmtPct(fu.roe as number, 0)} tone={toneOfNumber(fu.roe as number)} />
          <KV k="Revenue growth" v={fmtPct(fu.revenue_growth as number, 0)} tone={toneOfNumber(fu.revenue_growth as number)} />
          <KV k="Beta" v={fmtNum(fu.beta as number, 2)} />
        </Card>
        <Card title="Earnings & analysts" right={<DataTag kind={String(fu.source)} />}>
          <KV k="Next earnings" v={(fu.next_earnings as string) ?? "—"} />
          <KV k="Days remaining" v={dte ?? "—"} tone={dte !== null && dte <= 10 ? "text-warn" : "text-ink"} />
          <KV k="Event risk" v={f?.score.earnings_risk ?? "—"} tone={f?.score.earnings_risk === "high" ? "text-bad" : f?.score.earnings_risk === "elevated" ? "text-warn" : "text-ink"} />
          <div className="mt-2">
            <div className="flex h-2 overflow-hidden rounded-full bg-line">
              <div className="bg-good" style={{ width: `${(nb / ntot) * 100}%` }} />
              <div className="bg-ink2/50" style={{ width: `${(nh / ntot) * 100}%`, marginLeft: 2 }} />
              <div className="bg-bad" style={{ width: `${(ns / ntot) * 100}%`, marginLeft: 2 }} />
            </div>
            <div className="mt-1 flex justify-between text-[10px] num"><span className="text-good">Buy {nb}</span><span className="text-ink2">Hold {nh}</span><span className="text-bad">Sell {ns}</span></div>
          </div>
          <KV k="Avg. target" v={fmtMoney(tgt)} />
          <KV k="Upside / downside" v={fmtPct(upside)} tone={toneOfNumber(upside)} />
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Momentum vs benchmarks" bodyClass="p-0">
          <table className="w-full">
            <thead className="border-b border-line"><tr><th className="th"> </th>{["1w", "1m", "3m", "6m", "1y"].map((h) => <th key={h} className="th text-right">{h.toUpperCase()}</th>)}</tr></thead>
            <tbody>
              {[
                [ctx.ticker, t.momentum], ["SPY", ctx.spy_momentum], ["QQQ", ctx.qqq_momentum],
                ...(ctx.sector_momentum ? [[`${ctx.sector_etf} (sector)`, ctx.sector_momentum]] : []),
              ].map(([name, m]) => (
                <tr key={name as string} className="border-b border-line/60">
                  <td className="td font-medium text-ink">{name as string}</td>
                  {["1w", "1m", "3m", "6m", "1y"].map((h) => {
                    const v = (m as Record<string, number | null>)[h];
                    return <td key={h} className={`td text-right num ${toneOfNumber(v)}`}>{fmtPct(v)}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Sector performance · 1Y relative">
          <Legend items={[{ label: ctx.ticker, color: C.s1 }, { label: ctx.sector_etf ?? "Sector", color: C.s2 }, { label: "SPY", color: C.s3 }]} />
          <div className="mt-2 h-[200px]">
            <ResponsiveContainer>
              <LineChart data={data.relative_1y} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="date" {...axisProps} minTickGap={48} tickFormatter={(d: string) => d.slice(0, 7)} />
                <YAxis {...axisProps} width={48} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                <ReferenceLine y={0} stroke="#2a323e" />
                <Tooltip content={<DarkTooltip fmt={(v) => fmtPct(v)} />} cursor={{ stroke: "#2a323e" }} />
                <Line dataKey="stock" name={ctx.ticker} stroke={C.s1} strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line dataKey="sector" name={ctx.sector_etf ?? "Sector"} stroke={C.s2} strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line dataKey="spy" name="SPY" stroke={C.s3} strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* AI analysis */}
      {ai && (
        <Card title={<span>AI analysis <span className="ml-2 normal-case tracking-normal text-mute">engine: {ai.engine}</span></span>}>
          <div className="grid gap-x-8 gap-y-5 md:grid-cols-2">
            {Object.keys(ai.titles).map((k) => (
              <div key={k}>
                <h3 className={`mb-1.5 text-[10px] font-bold tracking-[0.14em] ${k === "bull_case" ? "text-good" : k === "bear_case" || k === "key_risks" ? "text-bad" : k === "invalidation" ? "text-warn" : "text-ink2"}`}>
                  {ai.titles[k]}
                </h3>
                <ul className="space-y-1">
                  {(ai.sections[k] ?? []).map((s, i) => <li key={i} className="flex gap-2 text-xs leading-relaxed text-ink"><span className="text-mute">›</span><span>{s}</span></li>)}
                </ul>
              </div>
            ))}
          </div>
          <p className="mt-4 border-t border-line pt-2 text-[10px] text-mute">{ai.disclaimer}</p>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card title="Signal engine" right={<span className="num text-[11px] normal-case tracking-normal text-white">{signals.overall.toFixed(0)} · {signals.classification}</span>}>
          <div className="space-y-2.5">
            {signals.components.map((c) => (
              <div key={c.key}>
                <div className="flex justify-between text-[11px]"><span className="text-ink">{c.label}</span><span className="num text-white">{c.score.toFixed(0)}</span></div>
                <ScoreBar value={c.score} className="mt-1" />
                <div className="mt-0.5 truncate text-[10px] text-mute" title={c.detail}>{c.detail}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="News" bodyClass="p-0">
          <ul className="divide-y divide-line/60">
            {data.news.map((n, i) => (
              <li key={i} className="flex items-start gap-3 px-4 py-2.5 text-xs">
                <span className="num w-20 shrink-0 text-mute">{n.date}</span>
                <span className="flex-1 text-ink">{n.headline}</span>
                <Badge tone={n.sentiment === "positive" ? "positive" : n.sentiment === "negative" ? "negative" : "neutral"}>{n.sentiment}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <div className="text-[10px] text-mute"><Link to="/trades" className="text-accent">← back to trades</Link></div>
    </div>
  );
}
