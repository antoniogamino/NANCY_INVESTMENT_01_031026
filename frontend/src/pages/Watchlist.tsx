import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, DataTag, ErrorBox, Loading, PageHeader, ScorePill } from "../components/ui";
import { api, useApi } from "../lib/api";
import { fmtMoney, fmtNum, fmtPct, toneOfNumber } from "../lib/format";

interface Row {
  id: number; ticker: string; name: string; notes: string | null; price: number; change_1d: number | null; rsi14: number | null;
  target_price: number | null; pelosi_score: number | null; classification: string | null; signal_overall: number | null;
  since_disclosure: number | null; last_disclosure: string | null; next_earnings: string | null; days_to_earnings: number | null;
  data_type: string; error?: string;
}

export default function Watchlist() {
  const { data, error, loading, reload } = useApi<Row[]>("/api/watchlist");
  const [tk, setTk] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tk.trim()) return;
    try {
      await api("/api/watchlist", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker: tk.trim() }) });
      setTk(""); setMsg(null); reload();
    } catch (er) { setMsg((er as Error).message); }
  };
  const remove = async (t: string) => { await api(`/api/watchlist/${t}`, { method: "DELETE" }); reload(); };

  return (
    <div className="space-y-4">
      <PageHeader title="Watchlist" subtitle="Saved locally in SQLite"
        right={<form onSubmit={add} className="flex items-center gap-2">
          <input className="input w-28 uppercase" placeholder="Ticker" value={tk} onChange={(e) => setTk(e.target.value)} />
          <button className="btn btn-primary" type="submit">Add</button>
          {msg && <span className="text-[11px] text-bad">{msg}</span>}
        </form>} />
      {error && <ErrorBox error={error} onRetry={reload} />}
      {loading && !data && <Loading />}
      {data && (
        <Card bodyClass="p-0">
          <div className="overflow-x-auto scroll-thin">
            <table className="w-full">
              <thead className="border-b border-line bg-panel2/50">
                <tr>{["Ticker", "Price", "1D", "Pelosi score", "Signal", "Avg target", "Since disclosure", "RSI 14", "Next earnings", ""].map((x, i) =>
                  <th key={x + i} className={`th ${i > 0 && i < 9 ? "text-right" : ""}`}>{x}</th>)}</tr>
              </thead>
              <tbody>
                {data.map((r) => r.error ? (
                  <tr key={r.ticker} className="border-b border-line/60"><td className="td text-white">{r.ticker}</td><td className="td text-bad" colSpan={8}>{r.error}</td>
                    <td className="td text-right"><button className="btn" onClick={() => remove(r.ticker)}>Remove</button></td></tr>
                ) : (
                  <tr key={r.ticker} className="border-b border-line/60 hover:bg-panel2/60">
                    <td className="td"><Link to={`/stock/${r.ticker}`} className="font-semibold text-white hover:text-accent">{r.ticker}</Link><div className="text-[10px] text-mute">{r.name}</div></td>
                    <td className="td text-right"><span className="num">{fmtMoney(r.price)}</span> <DataTag kind={r.data_type} /></td>
                    <td className={`td text-right num ${toneOfNumber(r.change_1d)}`}>{fmtPct(r.change_1d, 2)}</td>
                    <td className="td text-right">{r.pelosi_score !== null ? <ScorePill score={r.pelosi_score} label={r.classification ?? undefined} /> : <span className="text-mute">no trades</span>}</td>
                    <td className="td text-right num">{fmtNum(r.signal_overall, 0)}</td>
                    <td className="td text-right num">{fmtMoney(r.target_price)}{r.target_price && <span className={`ml-1 text-[10px] ${toneOfNumber(r.target_price / r.price - 1)}`}>{fmtPct(r.target_price / r.price - 1, 0)}</span>}</td>
                    <td className={`td text-right num ${toneOfNumber(r.since_disclosure)}`}>{fmtPct(r.since_disclosure)}{r.last_disclosure && <div className="text-[10px] text-mute">{r.last_disclosure}</div>}</td>
                    <td className={`td text-right num ${r.rsi14 && (r.rsi14 > 70 || r.rsi14 < 30) ? "text-warn" : ""}`}>{fmtNum(r.rsi14, 0)}</td>
                    <td className={`td text-right num ${r.days_to_earnings !== null && r.days_to_earnings <= 10 ? "text-warn" : "text-ink2"}`}>{r.next_earnings ?? "—"}{r.days_to_earnings !== null && <div className="text-[10px] text-mute">{r.days_to_earnings}d</div>}</td>
                    <td className="td text-right"><button className="btn" onClick={() => remove(r.ticker)} aria-label={`Remove ${r.ticker}`}>✕</button></td>
                  </tr>
                ))}
                {data.length === 0 && <tr><td className="td text-mute" colSpan={10}>Watchlist is empty. Add a ticker above or from any stock page.</td></tr>}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
