import { Link } from "react-router-dom";
import { DecayPanel } from "../components/Analysis";
import TradesTable from "../components/TradesTable";
import { Card, ErrorBox, Loading, PageHeader, ScoreGauge, Stat, TxBadge } from "../components/ui";
import { useApi } from "../lib/api";
import { fmtCompact, fmtPct, instrumentLabel, shortDate, toneOfNumber } from "../lib/format";
import type { TradeAnalysis } from "../lib/types";

interface DashboardData {
  overview: {
    total_trades: number; buys: number; sells: number; capital_min: number; capital_max: number; capital_mid: number;
    open_positions: number; closed_positions: number; est_return_since_trade: number | null;
    est_return_since_disclosure: number | null; unique_tickers: number; options_share: number; avg_delay_days: number;
  };
  sectors: { sector: string; count: number; capital_mid: number }[];
  latest: TradeAnalysis[];
  top_scores: TradeAnalysis[];
}

export default function Dashboard() {
  const { data, error, loading, reload } = useApi<DashboardData>("/api/dashboard");
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading || !data) return <Loading label="Building dashboard" />;
  const o = data.overview;
  const maxCap = Math.max(...data.sectors.map((s) => s.capital_mid), 1);
  const featured = data.latest.find((t) => t.transaction_type !== "SELL") ?? data.latest[0];

  return (
    <div className="space-y-4">
      <PageHeader title="Portfolio Overview" subtitle="Disclosed congressional trades — Pelosi household · relevance analytics, not recommendations" />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        <Stat label="Trades detected" value={o.total_trades} sub={`${o.unique_tickers} tickers`} />
        <Stat label="Buys" value={o.buys} tone="text-good" sub="incl. exercises" />
        <Stat label="Sells" value={o.sells} tone="text-bad" />
        <Stat label="Capital (est.)" value={fmtCompact(o.capital_mid)} sub={`${fmtCompact(o.capital_min)} – ${fmtCompact(o.capital_max)}`} tag="estimated" />
        <Stat label="Return since trade" value={fmtPct(o.est_return_since_trade)} tone={toneOfNumber(o.est_return_since_trade)} sub="buy-side, amount-weighted" tag="estimated" />
        <Stat label="Return since disclosure" value={fmtPct(o.est_return_since_disclosure)} tone={toneOfNumber(o.est_return_since_disclosure)} sub="what a follower got" tag="estimated" />
        <Stat label="Open / closed" value={<span>{o.open_positions}<span className="text-mute"> / </span>{o.closed_positions}</span>} sub="heuristic" tag="estimated" />
        <Stat label="Avg. disclosure lag" value={`${o.avg_delay_days.toFixed(0)}d`} sub={`${(o.options_share * 100).toFixed(0)}% options`} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Main sectors" right={<span className="text-[10px] normal-case tracking-normal text-mute">by est. capital (midpoint)</span>}>
          <div className="space-y-2.5">
            {data.sectors.map((s) => (
              <div key={s.sector}>
                <div className="flex justify-between text-[11px]">
                  <span className="text-ink">{s.sector}</span>
                  <span className="num text-ink2">{fmtCompact(s.capital_mid)} · {s.count}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-line">
                  <div className="h-1.5 rounded-full bg-accent" style={{ width: `${(s.capital_mid / maxCap) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {featured && (
          <Card title={<span>Opportunity decay · latest buy-side · <Link className="text-accent" to={`/stock/${featured.ticker}?trade=${featured.id}`}>{featured.ticker}</Link></span>}>
            <DecayPanel decay={featured.decay} />
          </Card>
        )}

        <Card title="Highest relevance scores" bodyClass="p-0">
          <ul className="divide-y divide-line/60">
            {data.top_scores.map((t) => (
              <li key={t.id}>
                <Link to={`/stock/${t.ticker}?trade=${t.id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-panel2/60">
                  <div className="w-14 font-semibold text-white">{t.ticker}</div>
                  <TxBadge type={t.transaction_type} />
                  <div className="flex-1 text-[10px] text-mute">{instrumentLabel(t.asset_type)} · disclosed {shortDate(t.disclosure_date)}</div>
                  <ScoreGauge score={t.score.score} label={t.score.classification} size={70} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Latest disclosed trades" right={<Link to="/trades" className="text-[10px] normal-case tracking-normal text-accent">All trades →</Link>} bodyClass="p-0">
        <TradesTable trades={data.latest} compact filters={false} />
      </Card>
    </div>
  );
}
