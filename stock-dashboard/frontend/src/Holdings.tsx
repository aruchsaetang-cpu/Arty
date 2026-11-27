import { useState } from "react";
import { Banner, Chip, MosText, OwnedBox, QualityChip, QuoteChip, ValChip } from "./common";
import { holdingTickers, pct, price, useApi, useHoldings, usePrefs } from "./lib";

export default function Holdings() {
  const held = useHoldings();
  const { mos } = usePrefs();
  const tickers = Object.keys(held).sort();
  const url = tickers.length ? `/api/summaries?tickers=${tickers.join(",")}&mos=${mos}` : null;
  const { data, error, okAt } = useApi<any>(url, { every: 60000, keep: true });
  const [onlyQ, setOnlyQ] = useState(false);
  // rows for CURRENT holdings only (an un-ticked stock disappears at once, before any refetch)
  const byT: Record<string, any> = {};
  (data?.rows || []).forEach((r: any) => (byT[r.ticker] = r));
  const rows = tickers.map((t) => byT[t] || { ticker: t, name: t, status: "awaiting", pending: true });
  const nq = rows.filter((r) => r.qualifies).length;
  const shown = onlyQ ? rows.filter((r) => r.qualifies) : rows;
  return (
    <>
      <h1>My Holdings</h1>
      <div className="card row" data-testid="holdings-summary">
        <b style={{ fontSize: "1.1rem" }}>{tickers.length} stock{tickers.length === 1 ? "" : "s"} held · {nq} currently meet your buying criteria</b>
        <span className="sp" />
        <label className="own"><input type="checkbox" checked={onlyQ} onChange={(e) => setOnlyQ(e.target.checked)} /><span>Qualifying only</span></label>
      </div>
      <div className="small mute">Buying criteria = the four shortlist rules at your {pct(mos, 0)} required margin of safety. Owning a stock has no effect on its valuation or rank. Holdings are saved in this browser only.</div>
      {error && <Banner>Refresh failed ({error.slice(0, 80)}). Showing last successful data{okAt ? ` from ${new Date(okAt).toLocaleTimeString()}` : ""}.</Banner>}
      {tickers.length === 0 && <div className="card">No holdings yet. Tick “Owned” beside any ticker on the Home, Screener, or a stock page.</div>}
      {tickers.length > 0 && (
        <div className="scroll">
          <table className="t">
            <thead><tr><th>Stock</th><th>Owned</th><th>Latest price</th><th>Quality</th><th>Valuation</th><th>Margin of safety</th><th>Watch price</th></tr></thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.ticker} className="click" onClick={() => (location.hash = "#/stock/" + r.ticker)} data-testid={`hold-${r.ticker}`}>
                  <td><a href={"#/stock/" + r.ticker} onClick={(e) => e.stopPropagation()} className="b">{r.ticker}</a><div className="tiny mute" style={{ whiteSpace: "normal" }}>{r.name}{r.in_index === false && <> · <Chip>not in S&amp;P 500 list</Chip></>}</div></td>
                  <td style={{ textAlign: "center" }}><OwnedBox ticker={r.ticker} compact /></td>
                  <td>{r.pending || r.price == null ? <span className="mute">{r.status === "failed_fetch" ? "data fetch failed" : "awaiting data"}</span> : <>{price(r.price, r.currency)}<div className="tiny mute">{r.price_time}</div><QuoteChip status={r.quote_status} reason={r.quote_reason} /></>}</td>
                  <td><QualityChip q={r.quality} /></td>
                  <td><ValChip v={r.valuation_label} /></td>
                  <td><MosText m={r.margin_of_safety} /></td>
                  <td>{r.watch_price != null ? <>{price(r.watch_price, r.currency)}{r.decline_to_watch ? <div className="tiny mute">needs −{pct(r.decline_to_watch, 0)}</div> : <div className="tiny up">at/below watch</div>}</> : <span className="mute">N/A</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
