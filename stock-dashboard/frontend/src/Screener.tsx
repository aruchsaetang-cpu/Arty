import { useMemo, useState } from "react";
import { Banner, Chip, ConfChip, MosText, OwnedBox, QualityChip, QuoteChip, StatusLabel, ValChip } from "./common";
import { price, useApi, useHoldings, usePrefs , stockHref, openStock} from "./lib";

const sel = (v: string, set: any, opts: string[], label: string) => (
  <select value={v} onChange={(e) => set(e.target.value)} aria-label={label}>
    <option value="">{label}: all</option>{opts.map((o) => <option key={o}>{o}</option>)}
  </select>
);

export default function Screener() {
  const { mos } = usePrefs();
  const held = useHoldings();
  const extra = Object.keys(held).sort().join(",");
  const { data, error } = useApi<any>(`/api/universe?mos=${mos}&extra=${extra}`, { every: 120000, keep: true });
  const [f, setF] = useState({ q: "", sector: "", quality: "", valuation: "", conf: "", cov: "", status: "", owned: false });
  const [sort, setSort] = useState<{ k: string; d: number }>({ k: "ticker", d: 1 });
  const set = (k: string) => (v: any) => setF((o) => ({ ...o, [k]: v }));
  const idxRows: any[] = data?.rows || [];
  const rows: any[] = useMemo(() => [...idxRows, ...(data?.extra_rows || [])], [data]);
  const sectors = useMemo(() => [...new Set(rows.map((r) => r.sector).filter(Boolean))].sort() as string[], [rows]);
  const shown = useMemo(() => {
    let out = rows.filter((r) => {
      if (f.owned && !held[r.ticker]) return false;
      if (f.q && !(r.ticker.toLowerCase().includes(f.q.toLowerCase()) || (r.name || "").toLowerCase().includes(f.q.toLowerCase()))) return false;
      if (f.sector && r.sector !== f.sector) return false;
      if (f.quality && (r.quality || "Awaiting analysis") !== f.quality) return false;
      if (f.valuation && (r.valuation_label || "Not assessed") !== f.valuation) return false;
      if (f.conf && (r.confidence || "awaiting") !== f.conf) return false;
      if (f.status && r.status !== f.status) return false;
      if (f.cov === "8+" && !(r.years >= 8)) return false;
      if (f.cov === "4-7" && !(r.years >= 4 && r.years < 8)) return false;
      if (f.cov === "<4" && !(r.years !== undefined && r.years < 4)) return false;
      if (f.cov === "awaiting" && r.status !== "awaiting" && r.status !== "failed_fetch") return false;
      if (f.cov === "stale" && r.quote_status !== "stale") return false;
      return true;
    });
    const g = (r: any) => (sort.k === "quote" ? r.quote_status : r[sort.k]);
    out = [...out].sort((a, b) => {
      const x = g(a), y = g(b);
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x > y ? 1 : x < y ? -1 : 0) * sort.d;
    });
    return out;
  }, [rows, f, sort, held]);
  const th = (k: string, l: string, cls = "") => (
    <th className={cls} onClick={() => setSort((s) => ({ k, d: s.k === k ? -s.d : 1 }))}>{l}{sort.k === k ? (sort.d > 0 ? " ▲" : " ▼") : ""}</th>
  );
  if (!data) return <div className="card">{error ? <Banner kind="bad">{error}</Banner> : "Loading screener…"}</div>;
  return (
    <>
      <h1>Screener · all {idxRows.length} S&amp;P 500 securities</h1>
      <div className="small mute">Includes every listed share class (e.g. GOOG/GOOGL, FOX/FOXA, NWS/NWSA, BRK-B). Membership source: {data.membership.label} (as of {data.membership.as_of}). Below the index list, non-index securities you hold or pinned (e.g. STM) appear flagged “not in S&amp;P 500 list”; they are never part of the index ranking or coverage.</div>
      <div className="card filters">
        <input type="text" placeholder="Search ticker or name" value={f.q} onChange={(e) => set("q")(e.target.value)} aria-label="Search" />
        {sel(f.sector, set("sector"), sectors, "Sector")}
        {sel(f.quality, set("quality"), ["Strong", "Mixed", "Weak", "Insufficient evidence", "Awaiting analysis"], "Business quality")}
        {sel(f.valuation, set("valuation"), ["Undervalued", "Moderate / Fairly valued", "Expensive", "Insufficient evidence", "Not assessed"], "Valuation")}
        {sel(f.conf, set("conf"), ["high", "medium", "low", "insufficient", "awaiting"], "Confidence")}
        {sel(f.cov, set("cov"), ["8+", "4-7", "<4", "awaiting", "stale"], "Data coverage")}
        {sel(f.status, set("status"), Object.keys(StatusLabel), "Status")}
        <label className="own"><input type="checkbox" checked={f.owned} onChange={(e) => set("owned")(e.target.checked)} /><span>Owned only</span></label>
        <span className="mute small">{shown.length} shown</span>
      </div>
      <div className="small mute" style={{ marginBottom: 6 }}>Data coverage: 8+ = ≥8 fiscal years (high-confidence eligible); 4-7 = Yahoo's usual 4-5 years; stale = quote older than the last completed session.</div>
      <div className="scroll tall">
        <table className="t">
          <thead><tr>{th("ticker", "Ticker")}<th>Owned</th>{th("name", "Name", "hide-p")}{th("sector", "Sector", "hide-p")}{th("price", "Price")}{th("margin_of_safety", "Margin of safety")}{th("quality", "Quality")}{th("valuation_label", "Valuation", "hide-p")}{th("confidence", "Confidence", "hide-p")}{th("years", "Yrs", "hide-p")}{th("quote_status", "Quote", "hide-p")}{th("status", "Status")}</tr></thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.ticker} className="click" onClick={() => openStock(r.ticker)} data-testid={`scr-${r.ticker}`}>
                <td><a href={stockHref(r.ticker)} onClick={(e) => e.stopPropagation()} className="b">{r.ticker}</a>{r.extra && <div><Chip title="Analysable and holdable, but not part of the S&P 500 ranking">not in S&amp;P 500 list</Chip></div>}</td>
                <td style={{ textAlign: "center" }}><OwnedBox ticker={r.ticker} compact /></td>
                <td className="hide-p" style={{ textAlign: "left", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{r.name}</td>
                <td className="hide-p" style={{ textAlign: "left" }}>{r.sector}</td>
                <td>{price(r.price, r.currency)}</td>
                <td><MosText m={r.margin_of_safety} /></td>
                <td><QualityChip q={r.quality} /></td>
                <td className="hide-p"><ValChip v={r.valuation_label} /></td>
                <td className="hide-p"><ConfChip c={r.confidence} /></td>
                <td className="hide-p">{r.years ?? "–"}</td>
                <td className="hide-p"><QuoteChip status={r.quote_status} reason={r.quote_reason} /></td>
                <td style={{ textAlign: "left" }}><Chip cls={r.qualifies ? "good" : r.status === "awaiting" ? "" : r.status === "failed_fetch" ? "bad" : "warn"} title={r.status_detail}>{StatusLabel[r.status]}</Chip></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
