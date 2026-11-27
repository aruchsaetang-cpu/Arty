import { useState } from "react";
import { Banner, Chip, MosText, OwnedBox, QualityChip, QuoteChip, ValChip } from "./common";
import { holdingTickers, pct, price, useApi, useHoldings, usePrefs , stockHref, openStock, when} from "./lib";

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
      {error && <Banner>Refresh failed. Showing last data.</Banner>}
      {tickers.length === 0 && <div className="card mute">No holdings. Tick “Owned” on any stock.</div>}
      {tickers.length > 0 && (
        <div className="scroll">
          <table className="t">
            <thead><tr><th>Stock</th><th>Owned</th><th>Price</th><th>Quality</th><th>Valuation</th><th>Margin</th><th>Watch</th></tr></thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.ticker} className="click" onClick={() => openStock(r.ticker)} data-testid={`hold-${r.ticker}`}>
                  <td><a href={stockHref(r.ticker)} onClick={(e) => e.stopPropagation()} className="b">{r.ticker}</a><div className="tiny mute" style={{ whiteSpace: "normal" }}>{r.name}{r.in_index === false && <> · <Chip>not in S&amp;P 500 list</Chip></>}</div></td>
                  <td style={{ textAlign: "center" }}><OwnedBox ticker={r.ticker} compact /></td>
                  <td>{r.pending || r.price == null ? <span className="mute">{r.status === "failed_fetch" ? "no data" : "loading"}</span> : <>{price(r.price, r.currency)}<div className="tiny mute">{when(r.price_time)}</div></>}</td>
                  <td><QualityChip q={r.quality} /></td>
                  <td><ValChip v={r.valuation_label} /></td>
                  <td><MosText m={r.margin_of_safety} /></td>
                  <td>{r.watch_price != null ? <>{price(r.watch_price, r.currency)}{r.decline_to_watch ? <div className="tiny mute">needs −{pct(r.decline_to_watch, 0)}</div> : null}</> : <span className="mute">N/A</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
