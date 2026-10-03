import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { C, DarkTooltip, axisProps } from "../components/chart";
import { Card, ErrorBox, Loading, PageHeader, Segmented, TxBadge } from "../components/ui";
import { useApi } from "../lib/api";
import { fmtPct, toneOfNumber } from "../lib/format";

type Agg = { n: number; avg_return: number | null; median_return: number | null; win_rate: number | null; avg_alpha_spy: number | null; avg_alpha_qqq: number | null };
type Block = { from_transaction: Agg; from_disclosure: Agg; disclosure_cost: number | null };
type Cell = { return: number; raw_return: number; spy: number | null; qqq: number | null; alpha_spy: number | null; alpha_qqq: number | null } | null;
interface Perf {
  trades: { id: number; ticker: string; transaction_type: string; asset_type: string; transaction_date: string; disclosure_date: string;
    from_transaction: Record<string, Cell>; from_disclosure: Record<string, Cell> }[];
  aggregate_all: Record<string, Block>; aggregate_buys: Record<string, Block>; notes: string[];
}
const H = ["1w", "1m", "3m", "6m", "1y"];

export default function Performance() {
  const { data, error, loading, reload } = useApi<Perf>("/api/performance");
  const [scope, setScope] = useState<"buys" | "all">("buys");
  const [h, setH] = useState("3m");
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;
  const agg = scope === "buys" ? data.aggregate_buys : data.aggregate_all;
  const chart = H.map((k) => ({
    h: k.toUpperCase(), tx: agg[k].from_transaction.avg_return, disc: agg[k].from_disclosure.avg_return,
    aspy: agg[k].from_disclosure.avg_alpha_spy, aqqq: agg[k].from_disclosure.avg_alpha_qqq,
  }));

  return (
    <div className="space-y-4">
      <PageHeader title="Performance Analysis"
        subtitle={<>Separates <b className="text-ink">“the trade was good”</b> (from transaction date) from <b className="text-ink">“following it publicly was good”</b> (from disclosure date).</>}
        right={<Segmented value={scope} onChange={setScope} options={[{ value: "buys", label: "Buy-side only" }, { value: "all", label: "All (sells as short)" }]} />} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Avg. return · transaction vs disclosure entry">
          <div className="mb-1 flex gap-4 text-[11px] text-ink2">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: C.s1 }} />From transaction (filer)</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: C.s2 }} />From disclosure (public follower)</span>
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer>
              <BarChart data={chart} margin={{ top: 10, right: 8, left: 0, bottom: 0 }} barGap={2}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="h" {...axisProps} />
                <YAxis {...axisProps} width={48} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                <ReferenceLine y={0} stroke="#2a323e" />
                <Tooltip content={<DarkTooltip fmt={(v) => fmtPct(v)} />} cursor={{ fill: "#ffffff08" }} />
                <Bar dataKey="tx" name="From transaction" fill={C.s1} radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar dataKey="disc" name="From disclosure" fill={C.s2} radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Follower alpha · entry at disclosure">
          <div className="mb-1 flex gap-4 text-[11px] text-ink2">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: C.s3 }} />Alpha vs SPY</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: C.s4 }} />Alpha vs QQQ</span>
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer>
              <BarChart data={chart} margin={{ top: 10, right: 8, left: 0, bottom: 0 }} barGap={2}>
                <CartesianGrid stroke={C.grid} vertical={false} />
                <XAxis dataKey="h" {...axisProps} />
                <YAxis {...axisProps} width={48} tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
                <ReferenceLine y={0} stroke="#2a323e" />
                <Tooltip content={<DarkTooltip fmt={(v) => fmtPct(v)} />} cursor={{ fill: "#ffffff08" }} />
                <Bar dataKey="aspy" name="Alpha vs SPY" fill={C.s3} radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar dataKey="aqqq" name="Alpha vs QQQ" fill={C.s4} radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Summary by horizon" bodyClass="p-0">
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full">
            <thead className="border-b border-line bg-panel2/50">
              <tr>
                <th className="th">Horizon</th><th className="th">Entry</th><th className="th text-right">N</th><th className="th text-right">Avg</th>
                <th className="th text-right">Median</th><th className="th text-right">Win rate</th><th className="th text-right">Alpha SPY</th><th className="th text-right">Alpha QQQ</th>
                <th className="th text-right" title="Avg return from transaction minus avg return from disclosure">Lag cost</th>
              </tr>
            </thead>
            <tbody>
              {H.map((k) => (["from_transaction", "from_disclosure"] as const).map((e, i) => {
                const a = agg[k][e];
                return (
                  <tr key={k + e} className={`border-b ${i ? "border-line" : "border-line/40"}`}>
                    {i === 0 && <td className="td font-semibold text-white" rowSpan={2}>{k.toUpperCase()}</td>}
                    <td className="td text-ink2">{e === "from_transaction" ? "Transaction" : "Disclosure"}</td>
                    <td className="td text-right num text-mute">{a.n}</td>
                    <td className={`td text-right num ${toneOfNumber(a.avg_return)}`}>{fmtPct(a.avg_return)}</td>
                    <td className={`td text-right num ${toneOfNumber(a.median_return)}`}>{fmtPct(a.median_return)}</td>
                    <td className="td text-right num">{a.win_rate === null ? "—" : `${(a.win_rate * 100).toFixed(0)}%`}</td>
                    <td className={`td text-right num ${toneOfNumber(a.avg_alpha_spy)}`}>{fmtPct(a.avg_alpha_spy)}</td>
                    <td className={`td text-right num ${toneOfNumber(a.avg_alpha_qqq)}`}>{fmtPct(a.avg_alpha_qqq)}</td>
                    {i === 0 && <td className={`td text-right num ${agg[k].disclosure_cost !== null && agg[k].disclosure_cost! > 0 ? "text-warn" : "text-ink2"}`} rowSpan={2}>{fmtPct(agg[k].disclosure_cost)}</td>}
                  </tr>
                );
              }))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Per-trade returns" right={<Segmented value={h} onChange={setH} options={H.map((x) => ({ value: x, label: x.toUpperCase() }))} />} bodyClass="p-0">
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full">
            <thead className="border-b border-line bg-panel2/50">
              <tr>{["Ticker", "Type", "Trade date", "From trade", "From disclosure", "SPY (discl.)", "QQQ (discl.)", "Alpha SPY", "Alpha QQQ"].map((x, i) =>
                <th key={x} className={`th ${i > 2 ? "text-right" : ""}`}>{x}</th>)}</tr>
            </thead>
            <tbody>
              {data.trades.filter((t) => scope === "all" || t.transaction_type !== "SELL").map((t) => {
                const a = t.from_transaction[h], b = t.from_disclosure[h];
                return (
                  <tr key={t.id} className="border-b border-line/60 hover:bg-panel2/60">
                    <td className="td font-semibold"><Link className="text-white hover:text-accent" to={`/stock/${t.ticker}?trade=${t.id}`}>{t.ticker}</Link></td>
                    <td className="td"><TxBadge type={t.transaction_type} /></td>
                    <td className="td num text-ink2">{t.transaction_date}</td>
                    <td className={`td text-right num ${toneOfNumber(a?.return)}`}>{a ? fmtPct(a.return) : <span className="text-mute">pending</span>}</td>
                    <td className={`td text-right num ${toneOfNumber(b?.return)}`}>{b ? fmtPct(b.return) : <span className="text-mute">pending</span>}</td>
                    <td className="td text-right num text-ink2">{fmtPct(b?.spy)}</td>
                    <td className="td text-right num text-ink2">{fmtPct(b?.qqq)}</td>
                    <td className={`td text-right num ${toneOfNumber(b?.alpha_spy)}`}>{fmtPct(b?.alpha_spy)}</td>
                    <td className={`td text-right num ${toneOfNumber(b?.alpha_qqq)}`}>{fmtPct(b?.alpha_qqq)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
      <ul className="list-disc space-y-0.5 pl-5 text-[10px] text-mute">{data.notes.map((n) => <li key={n}>{n}</li>)}</ul>
    </div>
  );
}
