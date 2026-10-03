import { useState } from "react";
import { Card, ErrorBox, Loading, PageHeader } from "../components/ui";
import { api, useApi } from "../lib/api";

interface DQ {
  by_confidence: Record<string, number>; by_source: Record<string, number>; by_status: Record<string, number>;
  issues: { id: number; ticker: string; issue: string }[];
  ingestion_log: { provider: string; at: string; records: number; status: string; message: string | null }[];
  field_types: Record<string, string>;
}
interface Filing { name: string; filing_type: string; filing_date: string; doc_id: string; pdf_url: string }

function Counts({ title, data }: { title: string; data: Record<string, number> }) {
  return (
    <Card title={title}>
      {Object.entries(data).map(([k, v]) => (
        <div key={k} className="flex justify-between py-0.5 text-xs"><span className="text-ink2">{k}</span><span className="num text-white">{v}</span></div>
      ))}
    </Card>
  );
}

export default function DataSources() {
  const { data, error, loading, reload } = useApi<DQ>("/api/data-quality");
  const [csv, setCsv] = useState("");
  const [importMsg, setImportMsg] = useState<string | null>(null);
  const [years, setYears] = useState(String(new Date().getFullYear()));
  const [filings, setFilings] = useState<{ ok: boolean; error?: string; filings: Filing[] } | null>(null);
  const [busy, setBusy] = useState(false);

  const doImport = async () => {
    setBusy(true);
    try {
      const r = await api<{ parsed: number; added: number; errors: string[] }>("/api/trades/import", { method: "POST", headers: { "Content-Type": "text/plain" }, body: csv });
      setImportMsg(`Parsed ${r.parsed}, added ${r.added}.${r.errors.length ? " Errors: " + r.errors.join("; ") : ""}`);
      reload();
    } catch (e) { setImportMsg((e as Error).message); }
    setBusy(false);
  };
  const loadTemplate = async () => setCsv(await (await fetch("/api/trades/template.csv")).text());
  const fetchFilings = async () => {
    setBusy(true);
    try { setFilings(await api(`/api/sources/house-filings?years=${encodeURIComponent(years)}`)); } catch (e) { setFilings({ ok: false, error: (e as Error).message, filings: [] }); }
    setBusy(false);
  };
  const reseed = async () => {
    if (!window.confirm("Reset the database and reload mock data? Imported trades and watchlist will be deleted.")) return;
    setBusy(true); await api("/api/admin/reseed", { method: "POST" }); setBusy(false); reload();
  };

  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (loading || !data) return <Loading />;

  return (
    <div className="space-y-4">
      <PageHeader title="Data Quality & Sources" subtitle="Provenance of every field: OFFICIAL · ESTIMATED · CALCULATED · MOCK" />
      <div className="grid gap-4 md:grid-cols-3">
        <Counts title="By confidence" data={data.by_confidence} />
        <Counts title="By source" data={data.by_source} />
        <Counts title="By analysis status" data={data.by_status} />
      </div>

      <Card title="Field provenance">
        <div className="space-y-1.5">
          {Object.entries(data.field_types).map(([k, v]) => (
            <div key={k} className="grid gap-2 text-xs md:grid-cols-[1fr_280px]"><span className="text-ink2">{k}</span><span className="num text-white">{v}</span></div>
          ))}
        </div>
      </Card>

      <Card title={`Data issues (${data.issues.length})`}>
        {data.issues.length === 0 ? <p className="text-xs text-mute">No issues detected.</p> : (
          <ul className="space-y-1 text-xs">{data.issues.map((i, k) => <li key={k} className="flex gap-3"><span className="w-14 font-semibold text-white">{i.ticker}</span><span className="text-warn">{i.issue}</span><span className="num text-mute">#{i.id}</span></li>)}</ul>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Import transcribed trades (CSV)">
          <p className="mb-2 text-[11px] text-mute">Transcribe transactions from official Periodic Transaction Reports. Rows are stored with confidence <b>official</b> or <b>estimated</b>.</p>
          <textarea className="input h-40 w-full font-mono text-[11px]" value={csv} onChange={(e) => setCsv(e.target.value)} placeholder="owner,owner_name,asset,ticker,..." />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <button className="btn" onClick={loadTemplate}>Load template</button>
            <button className="btn btn-primary" onClick={doImport} disabled={busy || !csv.trim()}>Import</button>
            {importMsg && <span className="text-[11px] text-ink2">{importMsg}</span>}
          </div>
        </Card>
        <Card title="Official House Clerk filings (experimental)">
          <p className="mb-2 text-[11px] text-mute">Downloads the yearly public index from disclosures-clerk.house.gov (one request per year, cached) and lists Pelosi filings with links to the official PDFs. Transactions are not parsed automatically.</p>
          <div className="flex items-center gap-2">
            <input className="input w-40 num" value={years} onChange={(e) => setYears(e.target.value)} aria-label="Years" />
            <button className="btn btn-primary" onClick={fetchFilings} disabled={busy}>Fetch index</button>
          </div>
          {filings && (
            <div className="mt-3 max-h-48 overflow-auto scroll-thin text-xs">
              {!filings.ok && <p className="text-bad">{filings.error}</p>}
              {filings.ok && filings.filings.length === 0 && <p className="text-mute">No filings found (or index unavailable offline).</p>}
              {filings.filings.map((f) => (
                <div key={f.doc_id} className="flex gap-3 py-0.5">
                  <span className="num text-mute">{f.filing_date}</span><span className="text-ink2">{f.filing_type === "P" ? "PTR" : f.filing_type}</span>
                  {f.pdf_url ? <a className="text-accent hover:underline" href={f.pdf_url} target="_blank" rel="noreferrer">{f.doc_id}</a> : <span>{f.doc_id}</span>}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card title="Ingestion log" right={<button className="btn" onClick={reseed} disabled={busy}>Reset & reseed mock data</button>}>
        <ul className="space-y-1 text-xs">
          {data.ingestion_log.map((l, i) => (
            <li key={i} className="flex gap-3"><span className="num text-mute">{l.at.slice(0, 19).replace("T", " ")}</span><span className="text-white">{l.provider}</span>
              <span className={l.status === "ok" ? "text-good" : "text-bad"}>{l.status}</span><span className="num text-ink2">{l.records} records</span>{l.message && <span className="text-mute">{l.message}</span>}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
