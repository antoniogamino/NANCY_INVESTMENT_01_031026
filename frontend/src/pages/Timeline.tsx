import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { C, axisProps } from "../components/chart";
import { Card, DataTag, ErrorBox, Loading, PageHeader, ScorePill, TxBadge } from "../components/ui";
import { useApi } from "../lib/api";
import { fmtCompact, fmtPct, fmtRange, instrumentLabel, toneOfNumber } from "../lib/format";

interface Item {
  id: number; ticker: string; company: string; sector: string | null; transaction_type: string; asset_type: string;
  transaction_date: string; disclosure_date: string; delay_days: number; amount_min: number | null; amount_max: number | null;
  amount_mid_estimated: number | null; strike: number | null; expiration: string | null; change_since_transaction: number | null;
  confidence_level: string; score: number; classification: string;
}

export default function Timeline() {
  const { data, error, loading, reload } = useApi<Item[]>("/api/timeline");
  const [year, setYear] = useState("ALL");
  const [ticker, setTicker] = useState("ALL");
  const [sector, setSector] = useState("ALL");
  const [type, setType] = useState("ALL");
  const [inst, setInst] = useState("ALL");
  const [minAmt, setMinAmt] = useState(0);

  const opts = useMemo(() => {
    const d = data ?? [];
    return {
      years: Array.from(new Set(d.map((x) => x.transaction_date.slice(0, 4)))).sort().reverse(),
      tickers: Array.from(new Set(d.map((x) => x.ticker))).sort(),
      sectors: Array.from(new Set(d.map((x) => x.sector ?? "Unknown"))).sort(),
    };
  }, [data]);

  const rows = useMemo(() => (data ?? []).filter((x) =>
    (year === "ALL" || x.transaction_date.startsWith(year)) &&
    (ticker === "ALL" || x.ticker === ticker) &&
    (sector === "ALL" || (x.sector ?? "Unknown") === sector) &&
    (type === "ALL" || (type === "SELL" ? x.transaction_type === "SELL" : x.transaction_type !== "SELL")) &&
    (inst === "ALL" || (inst === "STOCK" ? ["stock", "etf"].includes(x.asset_type) : !["stock", "etf"].includes(x.asset_type))) &&
    (x.amount_max ?? 0) >= minAmt
  ).sort((a, b) => b.transaction_date.localeCompare(a.transaction_date)), [data, year, ticker, sector, type, inst, minAmt]);

  const pts = (side: "buy" | "sell") => rows.filter((r) => (side === "sell") === (r.transaction_type === "SELL"))
    .map((r) => ({ x: new Date(r.transaction_date + "T00:00:00").getTime(), y: r.amount_mid_estimated ?? 1000, ...r }));

  const grouped = useMemo(() => {
    const g: Record<string, Item[]> = {};
    rows.forEach((r) => { (g[r.transaction_date.slice(0, 4)] ??= []).push(r); });
    return Object.entries(g).sort((a, b) => b[0].localeCompare(a[0]));
  }, [rows]);

  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  return (
    <div className="space-y-4">
      <PageHeader title="Trade Timeline" subtitle="Historical sequence of disclosed transactions" />
      <div className="card flex flex-wrap items-center gap-2 px-4 py-2.5">
        <select className="input" value={year} onChange={(e) => setYear(e.target.value)} aria-label="Year"><option value="ALL">All years</option>{opts.years.map((y) => <option key={y}>{y}</option>)}</select>
        <select className="input" value={ticker} onChange={(e) => setTicker(e.target.value)} aria-label="Ticker"><option value="ALL">All tickers</option>{opts.tickers.map((y) => <option key={y}>{y}</option>)}</select>
        <select className="input" value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Sector"><option value="ALL">All sectors</option>{opts.sectors.map((y) => <option key={y}>{y}</option>)}</select>
        <select className="input" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type"><option value="ALL">Buy & sell</option><option value="BUY">Buy-side</option><option value="SELL">Sell</option></select>
        <select className="input" value={inst} onChange={(e) => setInst(e.target.value)} aria-label="Instrument"><option value="ALL">Stocks & options</option><option value="STOCK">Stocks</option><option value="OPTION">Options</option></select>
        <select className="input" value={minAmt} onChange={(e) => setMinAmt(Number(e.target.value))} aria-label="Minimum amount">
          <option value={0}>Any amount</option><option value={100000}>≥ $100K</option><option value={500000}>≥ $500K</option><option value={1000000}>≥ $1M</option><option value={5000000}>≥ $5M</option>
        </select>
        <span className="ml-auto text-[11px] text-mute num">{rows.length} trades</span>
      </div>

      <Card title="Trades over time · size = reported band midpoint (log scale)">
        <div className="mb-1 flex gap-4 text-[11px] text-ink2">
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-good" />Buy / exercise</span>
          <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-bad" />Sell</span>
        </div>
        <div className="h-[240px]">
          <ResponsiveContainer>
            <ScatterChart margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis type="number" dataKey="x" domain={["dataMin - 2592000000", "dataMax + 2592000000"]} {...axisProps}
                tickFormatter={(v: number) => new Date(v).toISOString().slice(0, 7)} />
              <YAxis type="number" dataKey="y" scale="log" domain={[5000, 50000000]} {...axisProps} width={56} tickFormatter={(v: number) => fmtCompact(v)} />
              <ZAxis range={[80, 80]} />
              <Tooltip cursor={false} content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0].payload as Item;
                return (
                  <div className="rounded-md border border-line2 bg-panel/95 px-3 py-2 text-[11px]">
                    <div className="font-semibold text-white">{p.ticker} · {p.transaction_type}</div>
                    <div className="text-mute num">{p.transaction_date} · {instrumentLabel(p.asset_type)}</div>
                    <div className="num text-ink2">{fmtRange(p.amount_min, p.amount_max)}</div>
                  </div>
                );
              }} />
              <Scatter name="Buy" data={pts("buy")} fill={C.good} stroke="#0e1217" strokeWidth={2} />
              <Scatter name="Sell" data={pts("sell")} fill={C.bad} stroke="#0e1217" strokeWidth={2} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="space-y-4">
        {grouped.map(([y, items]) => (
          <div key={y}>
            <div className="mb-2 flex items-center gap-3"><span className="num text-sm font-semibold text-white">{y}</span><span className="h-px flex-1 bg-line" /><span className="text-[10px] text-mute">{items.length} trades</span></div>
            <ol className="relative ml-2 border-l border-line2">
              {items.map((x) => (
                <li key={x.id} className="relative mb-2 pl-5">
                  <span className={`absolute -left-[5px] top-3 h-2.5 w-2.5 rounded-full ring-2 ring-bg ${x.transaction_type === "SELL" ? "bg-bad" : "bg-good"}`} />
                  <Link to={`/stock/${x.ticker}?trade=${x.id}`} className="card flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-2 hover:border-line2">
                    <span className="num w-20 text-[11px] text-mute">{x.transaction_date}</span>
                    <span className="w-14 font-semibold text-white">{x.ticker}</span>
                    <TxBadge type={x.transaction_type} />
                    <span className="text-[11px] text-ink2">{instrumentLabel(x.asset_type)}{x.strike ? ` · $${x.strike} ${x.expiration}` : ""}</span>
                    <span className="num text-[11px] text-ink2">{fmtRange(x.amount_min, x.amount_max)}</span>
                    <span className="text-[10px] text-mute">disclosed +{x.delay_days}d</span>
                    <span className={`num text-[11px] ${toneOfNumber(x.change_since_transaction)}`}>{fmtPct(x.change_since_transaction)} since</span>
                    <span className="ml-auto flex items-center gap-2"><DataTag kind={x.confidence_level} /><ScorePill score={x.score} /></span>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </div>
  );
}
