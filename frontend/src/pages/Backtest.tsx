import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { C, DarkTooltip, Legend, axisProps } from "../components/chart";
import { Card, ErrorBox, Loading, PageHeader } from "../components/ui";
import { useApi } from "../lib/api";
import { fmtMoney, fmtNum, fmtPct, toneOfNumber } from "../lib/format";

type M = { final_capital: number; total_return: number; cagr: number; max_drawdown: number; sharpe: number | null;
  trades?: number; win_rate?: number; avg_trade_return?: number; closed_trades?: number };
interface BT {
  error?: string;
  params: { capital: number; entry_lag: number; hold_days: number; hold_trading_days: number };
  metrics: { strategy: M; buy_hold: M; spy: M; qqq: M };
  curve: { date: string; strategy: number; buy_hold: number; spy: number; qqq: number }[];
  positions: { trade_id: number; ticker: string; entry_date: string; exit_date: string; entry_price: number; exit_price: number; return: number; open: boolean }[];
  assumptions: string[];
}
type GridRow = { entry_lag: number; hold_days: number; total_return: number; cagr: number; max_drawdown: number; sharpe: number | null; win_rate: number; spy_return: number; qqq_return: number };

const LAGS = [{ v: 0, l: "Immediately after disclosure" }, { v: 1, l: "1 day after" }, { v: 3, l: "3 days after" }, { v: 5, l: "5 days after" }];
const HOLDS = [30, 90, 180, 365];
const SERIES = [
  { key: "strategy", label: "Follow Pelosi", color: C.s1 },
  { key: "spy", label: "SPY", color: C.s2 },
  { key: "qqq", label: "QQQ", color: C.s3 },
  { key: "buy_hold", label: "Buy & Hold (same entries)", color: C.s4 },
] as const;

export default function Backtest() {
  const [capital, setCapital] = useState(10000);
  const [lag, setLag] = useState(1);
  const [hold, setHold] = useState(90);
  const [sells, setSells] = useState(false);
  const [q, setQ] = useState({ capital: 10000, lag: 1, hold: 90, sells: false });
  const { data, error, loading, reload } = useApi<BT>(`/api/backtest?capital=${q.capital}&entry_lag=${q.lag}&hold_days=${q.hold}&include_sells=${q.sells}`);
  const grid = useApi<GridRow[]>(`/api/backtest/grid?capital=${q.capital}&include_sells=${q.sells}`);

  return (
    <div className="space-y-4">
      <PageHeader title="If I Followed Pelosi" subtitle="Event-driven backtest entering only after trades became public" />

      <Card title="Configuration">
        <form className="flex flex-wrap items-end gap-4" onSubmit={(e) => { e.preventDefault(); setQ({ capital, lag, hold, sells }); }}>
          <label className="flex flex-col gap-1"><span className="label">Initial capital</span>
            <input className="input w-32 num" type="number" min={100} step={100} value={capital} onChange={(e) => setCapital(Number(e.target.value))} /></label>
          <label className="flex flex-col gap-1"><span className="label">Entry</span>
            <select className="input" value={lag} onChange={(e) => setLag(Number(e.target.value))}>{LAGS.map((l) => <option key={l.v} value={l.v}>{l.l}</option>)}</select></label>
          <label className="flex flex-col gap-1"><span className="label">Holding period</span>
            <select className="input" value={hold} onChange={(e) => setHold(Number(e.target.value))}>{HOLDS.map((h) => <option key={h} value={h}>{h} days</option>)}</select></label>
          <label className="flex items-center gap-2 pb-1.5 text-xs text-ink2"><input type="checkbox" checked={sells} onChange={(e) => setSells(e.target.checked)} />Treat SELL disclosures as shorts</label>
          <button className="btn btn-primary" type="submit">Run backtest</button>
        </form>
      </Card>

      {error && <ErrorBox error={error} onRetry={reload} />}
      {loading && <Loading label="Simulating" />}
      {data?.error && <div className="card p-4 text-xs text-warn">{data.error}</div>}
      {data && !data.error && (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {SERIES.map((s) => {
              const m = data.metrics[s.key];
              return (
                <div key={s.key} className="card p-4" style={{ borderTop: `2px solid ${s.color}` }}>
                  <div className="label">{s.label}</div>
                  <div className="mt-1 num text-2xl font-semibold text-white">{fmtMoney(m.final_capital, 0)}</div>
                  <div className={`num text-sm ${toneOfNumber(m.total_return)}`}>{fmtPct(m.total_return)}</div>
                  <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                    <span className="text-mute">CAGR</span><span className={`num text-right ${toneOfNumber(m.cagr)}`}>{fmtPct(m.cagr)}</span>
                    <span className="text-mute">Max DD</span><span className="num text-right text-bad">{fmtPct(m.max_drawdown)}</span>
                    <span className="text-mute">Sharpe≈</span><span className="num text-right text-ink">{fmtNum(m.sharpe, 2)}</span>
                    {m.trades !== undefined && (<>
                      <span className="text-mute">Trades</span><span className="num text-right text-ink">{m.trades}</span>
                      <span className="text-mute">Win rate</span><span className="num text-right text-ink">{((m.win_rate ?? 0) * 100).toFixed(0)}%</span>
                      <span className="text-mute">Avg trade</span><span className={`num text-right ${toneOfNumber(m.avg_trade_return)}`}>{fmtPct(m.avg_trade_return)}</span>
                    </>)}
                  </div>
                </div>
              );
            })}
          </div>

          <Card title="Equity curve">
            <Legend items={SERIES.map((s) => ({ label: s.label, color: s.color }))} />
            <div className="mt-2 h-[320px]">
              <ResponsiveContainer>
                <LineChart data={data.curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={C.grid} vertical={false} />
                  <XAxis dataKey="date" {...axisProps} minTickGap={48} tickFormatter={(d: string) => d.slice(0, 7)} />
                  <YAxis {...axisProps} width={64} tickFormatter={(v: number) => fmtMoney(v, 0)} />
                  <Tooltip content={<DarkTooltip fmt={(v) => fmtMoney(v, 0)} />} cursor={{ stroke: "#2a323e" }} />
                  {SERIES.map((s) => <Line key={s.key} dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2} dot={false} isAnimationActive={false} />)}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}

      {grid.data && (
        <Card title="Strategy grid · total return by entry lag × holding period" bodyClass="p-0">
          <div className="overflow-x-auto scroll-thin">
            <table className="w-full">
              <thead className="border-b border-line bg-panel2/50"><tr><th className="th">Entry</th>{HOLDS.map((h) => <th key={h} className="th text-right">{h}d hold</th>)}</tr></thead>
              <tbody>
                {LAGS.map((l) => (
                  <tr key={l.v} className="border-b border-line/60">
                    <td className="td text-ink2">{l.l}</td>
                    {HOLDS.map((h) => {
                      const r = grid.data!.find((x) => x.entry_lag === l.v && x.hold_days === h);
                      const sel = q.lag === l.v && q.hold === h;
                      return (
                        <td key={h} className={`td text-right ${sel ? "bg-accent/10" : ""}`}>
                          {r ? (<div className="leading-tight"><div className={`num font-semibold ${toneOfNumber(r.total_return)}`}>{fmtPct(r.total_return)}</div>
                            <div className="num text-[10px] text-mute">DD {fmtPct(r.max_drawdown, 0)} · SR {fmtNum(r.sharpe, 2)}</div></div>) : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {data && !data.error && (
        <Card title={`Positions (${data.positions.length})`} bodyClass="p-0">
          <div className="max-h-[360px] overflow-auto scroll-thin">
            <table className="w-full">
              <thead className="sticky top-0 border-b border-line bg-panel2"><tr>{["Ticker", "Entry", "Exit", "Entry px", "Exit px", "Return", "Status"].map((x, i) => <th key={x} className={`th ${i > 2 ? "text-right" : ""}`}>{x}</th>)}</tr></thead>
              <tbody>
                {data.positions.map((p) => (
                  <tr key={p.trade_id} className="border-b border-line/60">
                    <td className="td font-semibold text-white">{p.ticker}</td>
                    <td className="td num text-ink2">{p.entry_date}</td>
                    <td className="td num text-ink2">{p.exit_date}</td>
                    <td className="td text-right num">{fmtMoney(p.entry_price)}</td>
                    <td className="td text-right num">{fmtMoney(p.exit_price)}</td>
                    <td className={`td text-right num ${toneOfNumber(p.return)}`}>{fmtPct(p.return)}</td>
                    <td className="td text-right text-[10px] text-mute">{p.open ? "OPEN" : "closed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="list-disc space-y-0.5 border-t border-line py-3 pl-8 pr-4 text-[10px] text-mute">{data.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
        </Card>
      )}
    </div>
  );
}
