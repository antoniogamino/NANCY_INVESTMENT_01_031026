import type { ReactNode } from "react";
import type { Tone } from "../lib/types";

export function Card({ title, right, children, className = "", bodyClass = "p-4" }: {
  title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; bodyClass?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {title && (
        <header className="card-h">
          <span>{title}</span>
          {right}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

const toneCls: Record<Tone, string> = {
  positive: "text-good border-good/40 bg-good/10",
  negative: "text-bad border-bad/40 bg-bad/10",
  warning: "text-warn border-warn/40 bg-warn/10",
  neutral: "text-ink2 border-line2 bg-panel2",
};

export function Badge({ tone = "neutral", children, className = "" }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${toneCls[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function TxBadge({ type }: { type: string }) {
  const tone: Tone = type === "SELL" ? "negative" : "positive";
  const icon = type === "SELL" ? "▼" : "▲";
  return (
    <Badge tone={tone}>
      <span aria-hidden>{icon}</span>
      {type}
    </Badge>
  );
}

/** Provenance tag: OFFICIAL / ESTIMATED / CALCULATED / MOCK / MARKET */
export function DataTag({ kind }: { kind: string }) {
  const k = kind.toLowerCase();
  const map: Record<string, string> = {
    official: "text-accent border-accent/40",
    market: "text-accent border-accent/40",
    estimated: "text-warn border-warn/40",
    calculated: "text-ink2 border-line2",
    mock: "text-[#c084fc] border-[#c084fc]/40",
  };
  return (
    <span
      title={`Data type: ${k.toUpperCase()}`}
      className={`inline-block rounded-sm border px-1 text-[9px] font-semibold uppercase leading-[14px] tracking-wider ${map[k] ?? "text-mute border-line2"}`}
    >
      {k === "calculated" ? "calc" : k === "estimated" ? "est" : k}
    </span>
  );
}

export function Stat({ label, value, sub, tag, tone }: {
  label: string; value: ReactNode; sub?: ReactNode; tag?: string; tone?: string;
}) {
  return (
    <div className="card px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <span className="label">{label}</span>
        {tag && <DataTag kind={tag} />}
      </div>
      <div className={`mt-1 text-2xl font-semibold num ${tone ?? "text-ink"}`}>{value}</div>
      {sub && <div className="mt-0.5 text-[11px] text-mute">{sub}</div>}
    </div>
  );
}

export function scoreTone(score: number): Tone {
  if (score >= 65) return "positive";
  if (score >= 50) return "neutral";
  if (score >= 35) return "warning";
  return "negative";
}

const barColor: Record<Tone, string> = {
  positive: "bg-good", negative: "bg-bad", warning: "bg-warn", neutral: "bg-ink2/60",
};

export function ScoreBar({ value, className = "" }: { value: number; className?: string }) {
  const t = scoreTone(value);
  return (
    <div className={`h-1.5 w-full rounded-full bg-line ${className}`}>
      <div className={`h-1.5 rounded-full ${barColor[t]}`} style={{ width: `${Math.max(2, Math.min(100, value))}%` }} />
    </div>
  );
}

export function ScorePill({ score, label }: { score: number; label?: string }) {
  const t = scoreTone(score);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`num text-xs font-semibold ${t === "positive" ? "text-good" : t === "negative" ? "text-bad" : t === "warning" ? "text-warn" : "text-ink"}`}>
        {score.toFixed(0)}
      </span>
      {label && <Badge tone={t}>{label}</Badge>}
    </span>
  );
}

export function ScoreGauge({ score, label, size = 120 }: { score: number; label: string; size?: number }) {
  const r = size / 2 - 8;
  const c = Math.PI * r;
  const t = scoreTone(score);
  const col = t === "positive" ? "#22c55e" : t === "negative" ? "#ef4444" : t === "warning" ? "#fab219" : "#a3a9b3";
  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 10} viewBox={`0 0 ${size} ${size / 2 + 10}`} role="img" aria-label={`Score ${score} ${label}`}>
        <path d={`M8 ${size / 2} A ${r} ${r} 0 0 1 ${size - 8} ${size / 2}`} stroke="#1f2630" strokeWidth="8" fill="none" strokeLinecap="round" />
        <path d={`M8 ${size / 2} A ${r} ${r} 0 0 1 ${size - 8} ${size / 2}`} stroke={col} strokeWidth="8" fill="none" strokeLinecap="round"
          strokeDasharray={`${(c * score) / 100} ${c}`} />
        <text x={size / 2} y={size / 2 - 4} textAnchor="middle" className="num" fill="#e6e8eb" fontSize={size / 4.2} fontWeight={600}>
          {score.toFixed(0)}
        </text>
      </svg>
      <Badge tone={t}>{label}</Badge>
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="flex items-center gap-2 p-6 text-xs text-mute"><span className="h-2 w-2 animate-pulse rounded-full bg-accent" />{label}…</div>;
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="card border-bad/40 p-4 text-xs text-bad">
      <div className="font-semibold">Could not load data</div>
      <div className="mt-1 text-ink2">{error}</div>
      <div className="mt-1 text-mute">Is the backend running on http://127.0.0.1:8000 ?</div>
      {onRetry && <button className="btn mt-3" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-white">{title}</h1>
        {subtitle && <p className="mt-0.5 text-xs text-mute">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Segmented<T extends string | number>({ value, options, onChange }: {
  value: T; options: { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-line2 bg-bg p-0.5">
      {options.map((o) => (
        <button key={String(o.value)} onClick={() => onChange(o.value)}
          className={`rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${o.value === value ? "bg-panel2 text-white" : "text-mute hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
