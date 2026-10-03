import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fmtMoney, fmtPct, fmtRange, instrumentLabel, shortDate, toneOfNumber } from "../lib/format";
import type { TradeAnalysis } from "../lib/types";
import { Badge, DataTag, ScorePill, TxBadge } from "./ui";

type Col = {
  key: string;
  label: string;
  get: (t: TradeAnalysis) => string | number | null;
  render: (t: TradeAnalysis) => React.ReactNode;
  align?: "right";
  compact?: boolean;
};

const COLS: Col[] = [
  { key: "ticker", label: "Company", compact: true, get: (t) => t.ticker,
    render: (t) => (<div className="leading-tight"><div className="font-semibold text-white">{t.ticker}</div><div className="max-w-[160px] truncate text-[10px] text-mute">{t.company}</div></div>) },
  { key: "type", label: "Type", compact: true, get: (t) => t.transaction_type, render: (t) => <TxBadge type={t.transaction_type} /> },
  { key: "tx", label: "Trade date", compact: true, get: (t) => t.transaction_date, render: (t) => <span className="num text-ink2">{shortDate(t.transaction_date)}</span> },
  { key: "disc", label: "Disclosed", compact: true, get: (t) => t.disclosure_date, render: (t) => <span className="num text-ink2">{shortDate(t.disclosure_date)}</span> },
  { key: "delay", label: "Delay", align: "right", compact: true, get: (t) => t.delay_days,
    render: (t) => <span className={`num ${t.delay_days > 45 ? "text-bad" : t.delay_days > 30 ? "text-warn" : "text-ink2"}`}>{t.delay_days}d</span> },
  { key: "amount", label: "Amount (reported)", get: (t) => t.amount_min, compact: true, render: (t) => <span className="num text-ink2">{fmtRange(t.amount_min, t.amount_max)}</span> },
  { key: "ptx", label: "Px @ trade", align: "right", get: (t) => t.price_at_transaction, render: (t) => <span className="num">{fmtMoney(t.price_at_transaction)}</span> },
  { key: "pnow", label: "Px now", align: "right", compact: true, get: (t) => t.price_now, render: (t) => <span className="num">{fmtMoney(t.price_now)}</span> },
  { key: "chg", label: "Δ since trade", align: "right", compact: true, get: (t) => t.change_since_transaction,
    render: (t) => <span className={`num font-medium ${toneOfNumber(t.change_since_transaction)}`}>{fmtPct(t.change_since_transaction)}</span> },
  { key: "chgd", label: "Δ since discl.", align: "right", get: (t) => t.change_since_disclosure,
    render: (t) => <span className={`num ${toneOfNumber(t.change_since_disclosure)}`}>{fmtPct(t.change_since_disclosure)}</span> },
  { key: "inst", label: "Instrument", compact: true, get: (t) => t.asset_type, render: (t) => <span className="text-ink2">{instrumentLabel(t.asset_type)}</span> },
  { key: "strike", label: "Strike", align: "right", get: (t) => t.strike, render: (t) => <span className="num text-ink2">{t.strike ? fmtMoney(t.strike) : "—"}</span> },
  { key: "exp", label: "Expiration", get: (t) => t.expiration,
    render: (t) => t.expiration ? <span className={`num ${t.instrument.days_to_expiry !== undefined && t.instrument.days_to_expiry <= 0 ? "text-mute line-through" : "text-ink2"}`}>{shortDate(t.expiration)}</span> : <span className="text-mute">—</span> },
  { key: "sector", label: "Sector", get: (t) => t.sector, render: (t) => <span className="text-ink2">{t.sector ?? "—"}</span> },
  { key: "decay", label: "Decay", align: "right", get: (t) => t.decay.score, render: (t) => t.decay.score !== null ? <span className="num text-ink2" title={t.decay.label}>{t.decay.score.toFixed(0)}</span> : <span>—</span> },
  { key: "score", label: "Score", compact: true, get: (t) => t.score.score, render: (t) => <ScorePill score={t.score.score} label={t.score.classification} /> },
  { key: "src", label: "Source", get: (t) => t.source,
    render: (t) => (<span className="flex items-center gap-1">{t.source_url ? <a className="text-accent hover:underline" href={t.source_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>{t.source}</a> : <span className="text-ink2">{t.source}</span>}<DataTag kind={t.confidence_level} /></span>) },
  { key: "status", label: "Analysis", get: (t) => t.analysis_status,
    render: (t) => <Badge tone={t.analysis_status === "analyzed" ? "neutral" : "warning"}>{t.analysis_status.replace("_", " ")}</Badge> },
];

export default function TradesTable({ trades, compact = false, filters = true }: { trades: TradeAnalysis[]; compact?: boolean; filters?: boolean }) {
  const nav = useNavigate();
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 }>({ key: "disc", dir: -1 });
  const [q, setQ] = useState("");
  const [type, setType] = useState("ALL");
  const [inst, setInst] = useState("ALL");
  const [sector, setSector] = useState("ALL");
  const [cls, setCls] = useState("ALL");

  const sectors = useMemo(() => Array.from(new Set(trades.map((t) => t.sector ?? "Unknown"))).sort(), [trades]);
  const classes = useMemo(() => Array.from(new Set(trades.map((t) => t.score.classification))), [trades]);
  const cols = compact ? COLS.filter((c) => c.compact) : COLS;

  const rows = useMemo(() => {
    const f = trades.filter((t) => {
      if (q && !`${t.ticker} ${t.company}`.toLowerCase().includes(q.toLowerCase())) return false;
      if (type !== "ALL" && (type === "BUY" ? t.transaction_type === "SELL" : t.transaction_type !== "SELL")) return false;
      if (inst === "STOCK" && t.instrument.kind !== "equity") return false;
      if (inst === "OPTION" && t.instrument.kind !== "option") return false;
      if (sector !== "ALL" && (t.sector ?? "Unknown") !== sector) return false;
      if (cls !== "ALL" && t.score.classification !== cls) return false;
      return true;
    });
    const col = COLS.find((c) => c.key === sort.key)!;
    return [...f].sort((a, b) => {
      const va = col.get(a), vb = col.get(b);
      if (va === null) return 1;
      if (vb === null) return -1;
      return (va < vb ? -1 : va > vb ? 1 : 0) * sort.dir;
    });
  }, [trades, q, type, inst, sector, cls, sort]);

  return (
    <div>
      {filters && (
        <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5">
          <input className="input w-40" placeholder="Search ticker / company" value={q} onChange={(e) => setQ(e.target.value)} />
          <select className="input" value={type} onChange={(e) => setType(e.target.value)} aria-label="Type">
            <option value="ALL">All types</option><option value="BUY">Buy / Exercise</option><option value="SELL">Sell</option>
          </select>
          <select className="input" value={inst} onChange={(e) => setInst(e.target.value)} aria-label="Instrument">
            <option value="ALL">All instruments</option><option value="STOCK">Stocks</option><option value="OPTION">Options</option>
          </select>
          <select className="input" value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Sector">
            <option value="ALL">All sectors</option>{sectors.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select className="input" value={cls} onChange={(e) => setCls(e.target.value)} aria-label="Classification">
            <option value="ALL">All scores</option>{classes.map((s) => <option key={s}>{s}</option>)}
          </select>
          <span className="ml-auto text-[11px] text-mute num">{rows.length} / {trades.length}</span>
        </div>
      )}
      <div className="overflow-x-auto scroll-thin">
        <table className="w-full border-collapse">
          <thead className="border-b border-line bg-panel2/50">
            <tr>
              {cols.map((c) => (
                <th key={c.key} className={`th cursor-pointer hover:text-ink ${c.align === "right" ? "text-right" : ""}`}
                  onClick={() => setSort((s) => ({ key: c.key, dir: s.key === c.key ? ((-s.dir) as 1 | -1) : -1 }))}>
                  {c.label}{sort.key === c.key ? (sort.dir === 1 ? " ↑" : " ↓") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id} className="cursor-pointer border-b border-line/60 hover:bg-panel2/70" onClick={() => nav(`/stock/${t.ticker}?trade=${t.id}`)}>
                {cols.map((c) => <td key={c.key} className={`td ${c.align === "right" ? "text-right" : ""}`}>{c.render(t)}</td>)}
              </tr>
            ))}
            {rows.length === 0 && <tr><td className="td text-mute" colSpan={cols.length}>No trades match the filters.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
