import { Link } from "react-router-dom";
import { Badge, Card, ErrorBox, Loading, PageHeader, scoreTone } from "../components/ui";
import { useApi } from "../lib/api";
import { fmtMoney } from "../lib/format";
import type { TickerSignals } from "../lib/types";

const cellCls = (v: number) => {
  const t = scoreTone(v);
  return t === "positive" ? "bg-good/15 text-good" : t === "negative" ? "bg-bad/15 text-bad" : t === "warning" ? "bg-warn/10 text-warn" : "bg-panel2 text-ink";
};

export default function Signals() {
  const { data, error, loading, reload } = useApi<TickerSignals[]>("/api/signals");
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading || !data) return <Loading label="Running signal engine" />;
  const labels = data[0]?.components.map((c) => c.label) ?? [];
  return (
    <div className="space-y-4">
      <PageHeader title="Signal Engine" subtitle="Per-ticker component scores (0–100). Higher = more favourable / relevant. Risk: higher = lower risk." />
      <Card bodyClass="p-0">
        <div className="overflow-x-auto scroll-thin">
          <table className="w-full border-separate border-spacing-0">
            <thead className="bg-panel2/50">
              <tr>
                <th className="th border-b border-line">Ticker</th>
                <th className="th border-b border-line text-right">Price</th>
                {labels.map((l) => <th key={l} className="th border-b border-line text-center">{l.replace(" (higher = lower risk)", "")}</th>)}
                <th className="th border-b border-line text-center">Overall</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.ticker} className="hover:bg-panel2/40">
                  <td className="td border-b border-line/60"><Link to={`/stock/${s.ticker}`} className="font-semibold text-white hover:text-accent">{s.ticker}</Link><div className="text-[10px] text-mute">{s.sector}</div></td>
                  <td className="td border-b border-line/60 text-right num">{fmtMoney(s.price)}</td>
                  {s.components.map((c) => (
                    <td key={c.key} className="border-b border-line/60 p-1 text-center" title={c.detail}>
                      <div className={`num rounded px-2 py-1.5 text-xs font-semibold ${cellCls(c.score)}`}>{c.score.toFixed(0)}</div>
                    </td>
                  ))}
                  <td className="td border-b border-line/60 text-center">
                    <div className="num text-sm font-bold text-white">{s.overall.toFixed(0)}</div>
                    <Badge tone={s.tone}>{s.classification}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <p className="text-[10px] text-mute">Hover a cell for the underlying detail. Signals describe context; they are not trading instructions.</p>
    </div>
  );
}
