import type { TooltipProps } from "recharts";

export const C = {
  s1: "#3987e5", s2: "#d95926", s3: "#199e70", s4: "#9085e9",
  grid: "#1c222b", axis: "#6b7380", good: "#22c55e", bad: "#ef4444", warn: "#fab219", ink: "#e6e8eb",
};

export const axisProps = {
  stroke: C.axis, tick: { fill: C.axis, fontSize: 10, fontFamily: "JetBrains Mono, monospace" },
  tickLine: false, axisLine: { stroke: "#2a323e" },
};

type Fmt = (v: number, name: string) => string;

export function DarkTooltip({ active, payload, label, fmt, labelFmt }: TooltipProps<number, string> & { fmt?: Fmt; labelFmt?: (l: string) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-line2 bg-panel/95 px-3 py-2 text-[11px] shadow-xl backdrop-blur">
      <div className="mb-1 num text-mute">{labelFmt ? labelFmt(String(label)) : label}</div>
      {payload.filter((p) => p.value !== null && p.value !== undefined).map((p) => (
        <div key={String(p.dataKey)} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-ink2">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
            {p.name}
          </span>
          <span className="num text-white">{fmt ? fmt(Number(p.value), String(p.name)) : String(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string; dashed?: boolean }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink2">
      {items.map((i) => (
        <span key={i.label} className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4" style={{ background: i.dashed ? `repeating-linear-gradient(90deg, ${i.color} 0 3px, transparent 3px 5px)` : i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
