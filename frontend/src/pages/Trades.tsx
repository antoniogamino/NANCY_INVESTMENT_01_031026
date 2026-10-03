import TradesTable from "../components/TradesTable";
import { Card, ErrorBox, Loading, PageHeader } from "../components/ui";
import { useApi } from "../lib/api";
import type { TradeAnalysis } from "../lib/types";

export default function Trades() {
  const { data, error, loading, reload } = useApi<TradeAnalysis[]>("/api/trades");
  return (
    <div>
      <PageHeader title="Disclosed Trades" subtitle="Every reported transaction with price context, decay and relevance score. Click a row for full analysis." />
      {error && <ErrorBox error={error} onRetry={reload} />}
      {loading && <Loading />}
      {data && (
        <Card bodyClass="p-0">
          <TradesTable trades={data} />
        </Card>
      )}
      <p className="mt-3 text-[10px] text-mute">
        Prices at trade/disclosure are the close on (or after) that date — the filing does not report execution price.
        For options, prices refer to the underlying. Score = relevance today (0–100), not a buy/sell signal.
      </p>
    </div>
  );
}
