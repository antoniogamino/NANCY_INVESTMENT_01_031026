export const fmtPct = (x: number | null | undefined, d = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`;

export const fmtMoney = (x: number | null | undefined, d = 2) =>
  x === null || x === undefined ? "—" : `$${x.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;

export const fmtCompact = (x: number | null | undefined) => {
  if (x === null || x === undefined) return "—";
  const a = Math.abs(x);
  if (a >= 1e12) return `$${(x / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `$${(x / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(x / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(x / 1e3).toFixed(0)}K`;
  return `$${x.toFixed(0)}`;
};

export const fmtRange = (a: number | null, b: number | null) =>
  a === null || b === null ? "—" : `${fmtCompact(a)} – ${fmtCompact(b)}`;

export const fmtNum = (x: number | null | undefined, d = 1) =>
  x === null || x === undefined ? "—" : x.toFixed(d);

export const toneOfNumber = (x: number | null | undefined) =>
  x === null || x === undefined ? "text-ink2" : x > 0 ? "text-good" : x < 0 ? "text-bad" : "text-ink2";

export const shortDate = (s: string) => {
  const d = new Date(s + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
};

export const instrumentLabel = (t: string) =>
  ({ stock: "Stock", etf: "ETF", call: "Call", put: "Put", leaps_call: "LEAPS Call", leaps_put: "LEAPS Put", other: "Other" })[
    t
  ] ?? t;
