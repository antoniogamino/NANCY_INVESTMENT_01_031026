import { useState, type ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useApi } from "../lib/api";
import type { Meta } from "../lib/types";

const NAV = [
  { to: "/", label: "Dashboard", icon: "M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z" },
  { to: "/trades", label: "Trades", icon: "M4 6h16M4 12h16M4 18h10" },
  { to: "/timeline", label: "Timeline", icon: "M12 8v4l3 2M12 3a9 9 0 100 18 9 9 0 000-18z" },
  { to: "/signals", label: "Signals", icon: "M3 17l6-6 4 4 8-8" },
  { to: "/performance", label: "Performance", icon: "M4 20V10m6 10V4m6 16v-7m4 7H2" },
  { to: "/backtest", label: "Backtest", icon: "M4 4v16h16M8 14l3-3 3 2 5-6" },
  { to: "/watchlist", label: "Watchlist", icon: "M12 17l-5 3 1.5-5.5L4 10.5l5.7-.4L12 5l2.3 5.1 5.7.4-4.5 4L17 20z" },
  { to: "/data", label: "Data & Sources", icon: "M4 7c0-2 16-2 16 0v10c0 2-16 2-16 0V7zm0 0c0 2 16 2 16 0M4 12c0 2 16 2 16 0" },
];

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={d} />
    </svg>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { data: meta } = useApi<Meta>("/api/meta");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const nav = useNavigate();

  return (
    <div className="flex min-h-full">
      {/* sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-30 w-56 border-r border-line bg-panel transition-transform md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex h-14 items-center gap-2 border-b border-line px-4">
          <div className="grid h-7 w-7 place-items-center rounded bg-accent/15 text-accent">
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M3 17l6-6 4 4 8-9" /></svg>
          </div>
          <div className="leading-tight">
            <div className="text-[11px] font-bold tracking-[0.18em] text-white">NANCY</div>
            <div className="text-[9px] tracking-[0.14em] text-mute">INVESTMENT INTELLIGENCE</div>
          </div>
        </div>
        <nav className="p-2">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors ${isActive ? "bg-panel2 text-white" : "text-ink2 hover:bg-panel2/60 hover:text-white"}`}>
              <Icon d={n.icon} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        {meta && (
          <div className="absolute bottom-0 w-full border-t border-line p-3 text-[10px] text-mute">
            <div className="label mb-1">Providers</div>
            {Object.entries(meta.providers).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span>{k}</span><span className={`num ${v === "mock" ? "text-[#c084fc]" : "text-ink2"}`}>{v}</span></div>
            ))}
          </div>
        )}
      </aside>
      {open && <div className="fixed inset-0 z-20 bg-black/60 md:hidden" onClick={() => setOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col md:pl-56">
        {/* top bar */}
        <header className="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-line bg-bg/90 px-4 backdrop-blur">
          <button className="btn md:hidden" onClick={() => setOpen(true)} aria-label="Menu">☰</button>
          <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) nav(`/stock/${q.trim().toUpperCase()}`); setQ(""); }} className="flex-1 max-w-xs">
            <input className="input w-full" placeholder="Ticker → detail (e.g. NVDA)" value={q} onChange={(e) => setQ(e.target.value)} />
          </form>
          <div className="ml-auto flex items-center gap-3 text-[11px] text-mute">
            {meta?.mock_mode && (
              <span className="rounded border border-[#c084fc]/40 bg-[#c084fc]/10 px-2 py-0.5 font-semibold tracking-wider text-[#c084fc]" title="Fictitious development data — not real disclosures or prices">
                MOCK DATA MODE
              </span>
            )}
            {meta && <span className="hidden sm:inline num">AS OF {meta.today}</span>}
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6">{children}</main>

        <footer className="border-t border-line px-4 py-3 text-[10px] leading-relaxed text-mute md:px-6">
          {meta?.disclaimer ??
            "Congressional financial disclosures may be reported days or weeks after a transaction. Historical political trading activity does not guarantee future returns. This platform is intended for research and educational purposes and does not constitute investment advice."}
        </footer>
      </div>
    </div>
  );
}
