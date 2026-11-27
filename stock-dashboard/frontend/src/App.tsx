import { useEffect, useRef, useState } from "react";
import Holdings from "./Holdings";
import Home from "./Home";
import Method from "./Method";
import Screener from "./Screener";
import Stock from "./Stock";
import { Chip } from "./common";
import { useApi, useHoldings, useRoute } from "./lib";

function Search() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const t = useRef<any>(null);
  useEffect(() => {
    clearTimeout(t.current);
    if (!q.trim()) { setRes([]); return; }
    t.current = setTimeout(async () => {
      try { const r = await fetch("/api/search?q=" + encodeURIComponent(q)); setRes((await r.json()).results || []); } catch { setRes([]); }
    }, 200);
  }, [q]);
  const pick = (tk: string) => { location.hash = "#/stock/" + tk; setQ(""); setOpen(false); };
  return (
    <div className="search">
      <input placeholder="Search any ticker or company (e.g. STM, JPM, O)…" value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
        onKeyDown={(e) => e.key === "Enter" && (res[0] ? pick(res[0].ticker) : q.trim() && pick(q.trim().toUpperCase()))} aria-label="Search ticker" data-testid="search" />
      {open && res.length > 0 && (
        <div className="dd">{res.map((r) => (
          <button key={r.ticker} onClick={() => pick(r.ticker)} data-testid={`sr-${r.ticker}`}>
            <b>{r.ticker}</b><span className="mute small sp">{r.name || (r.external ? "Analyse this ticker" : "")}</span>
            {r.in_index ? <Chip cls="good">S&amp;P 500</Chip> : <Chip>not in index list</Chip>}
          </button>))}</div>
      )}
    </div>
  );
}

export default function App() {
  const { parts } = useRoute();
  const held = useHoldings();
  const { data: meta } = useApi<any>("/api/meta", { every: 300000, keep: true });
  const page = parts[0] || "home";
  const tab = (k: string, l: string, extra?: any) => <a href={"#/" + (k === "home" ? "" : k)} className={page === k ? "on" : ""}>{l}{extra}</a>;
  useEffect(() => { document.getElementById("root")?.setAttribute("data-page", page); }, [page]);
  return (
    <>
      <header className="top"><div className="top-in">
        <span className="brand">📈 Research</span>
        <nav className="tabs">{tab("home", "Home")}{tab("screener", "Screener")}{tab("holdings", "My Holdings", <span className="badge-n" data-testid="holdings-count">{Object.keys(held).length}</span>)}{tab("method", "Method")}</nav>
        <Search />
        {meta && <Chip cls={meta.session.phase === "OPEN" ? "good" : ""} title={`Now ${meta.session.now_et}`}>NYSE {meta.session.phase === "OPEN" ? "open" : meta.session.closed_reason ? `closed (${meta.session.closed_reason})` : meta.session.phase.replaceAll("_", " ").toLowerCase()}</Chip>}
      </div></header>
      <main className="wrap">
        {page === "home" && <Home />}
        {page === "screener" && <Screener />}
        {page === "holdings" && <Holdings />}
        {page === "method" && <Method />}
        {page === "stock" && parts[1] && <Stock key={parts[1]} ticker={decodeURIComponent(parts[1]).toUpperCase()} />}
      </main>
    </>
  );
}
