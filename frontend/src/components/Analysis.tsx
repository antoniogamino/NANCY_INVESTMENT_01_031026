import { fmtMoney, fmtPct } from "../lib/format";
import type { Decay, ScoreComponent } from "../lib/types";
import { Badge, DataTag, ScoreBar } from "./ui";

/** Before / after / total breakdown of the move around the disclosure. */
export function DecayPanel({ decay, compact = false }: { decay: Decay; compact?: boolean }) {
  if (!decay.available) return <div className="text-xs text-mute">Insufficient price data for decay analysis.</div>;
  const b = decay.move_before_disclosure!, a = decay.move_after_disclosure!, t = decay.move_total!;
  const max = Math.max(Math.abs(b), Math.abs(a), Math.abs(t), 0.01);
  const Row = ({ label, v, sub }: { label: string; v: number; sub: string }) => (
    <div className="grid grid-cols-[120px_1fr_70px] items-center gap-3">
      <div>
        <div className="text-[11px] text-ink2">{label}</div>
        <div className="text-[10px] text-mute">{sub}</div>
      </div>
      <div className="relative h-5 rounded bg-bg">
        <div className="absolute inset-y-0 left-1/2 w-px bg-line2" />
        <div className={`absolute inset-y-1 rounded-sm ${v >= 0 ? "bg-good/80" : "bg-bad/80"}`}
          style={v >= 0 ? { left: "50%", width: `${(v / max) * 50}%` } : { right: "50%", width: `${(-v / max) * 50}%` }} />
      </div>
      <div className={`num text-right text-sm font-semibold ${v >= 0 ? "text-good" : "text-bad"}`}>{fmtPct(v)}</div>
    </div>
  );
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="num text-3xl font-semibold text-white">{decay.score?.toFixed(0)}</span>
          <span className="text-[10px] text-mute">/ 100 decay score</span>
        </div>
        <Badge tone={decay.tone}>{decay.label}</Badge>
      </div>
      {!compact && (
        <div className="grid grid-cols-3 gap-2 text-center">
          {[["Trade", decay.price_transaction], ["Disclosure", decay.price_disclosure], ["Now", decay.price_now]].map(([l, v]) => (
            <div key={l as string} className="rounded border border-line bg-bg px-2 py-1.5">
              <div className="label">{l}</div>
              <div className="num text-sm text-white">{fmtMoney(v as number)}</div>
            </div>
          ))}
        </div>
      )}
      <Row label="Before disclosure" v={b} sub="not capturable by public" />
      <Row label="After disclosure" v={a} sub={`${decay.days_since_disclosure} days public`} />
      <Row label="Total move" v={t} sub="trade → now" />
      {decay.share_captured_before_disclosure !== null && decay.share_captured_before_disclosure !== undefined && (
        <p className="text-[11px] text-ink2">
          <span className="num font-semibold text-warn">{(decay.share_captured_before_disclosure * 100).toFixed(0)}%</span> of the favourable move
          happened before the public could know. <DataTag kind="calculated" />
        </p>
      )}
    </div>
  );
}

export function ScoreBreakdown({ components }: { components: ScoreComponent[] }) {
  return (
    <div className="divide-y divide-line/60">
      {components.map((c) => (
        <div key={c.key} className="grid grid-cols-[minmax(110px,150px)_1fr_36px] items-center gap-3 py-2">
          <div className="leading-tight">
            <div className="text-[11px] text-ink">{c.key.split("_")[0]}. {c.label}</div>
            <div className="text-[10px] text-mute">w{c.weight}{c.mirrored ? " · mirrored (SELL)" : ""}</div>
          </div>
          <div>
            <ScoreBar value={c.score} />
            <div className="mt-1 flex items-center gap-1.5 text-[10px] text-mute">
              <span className="truncate" title={c.detail}>{c.detail}</span>
              <DataTag kind={c.data_type} />
            </div>
          </div>
          <div className="num text-right text-xs font-semibold text-white">{c.score.toFixed(0)}</div>
        </div>
      ))}
    </div>
  );
}
