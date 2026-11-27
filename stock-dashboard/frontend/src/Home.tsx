import { useState } from "react";
import { Banner, Chip, OwnedBox, PickRow, QuoteChip, RuleList, ValChip, QualityChip, MosText } from "./common";
import { pct, price, usePrefs, setMos, useApi } from "./lib";

export default function Home() {
  const { mos } = usePrefs();
  const { data, error, okAt } = useApi<any>(`/api/shortlist?mos=${mos}`, { every: 60000, keep: true });
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const tog = (t: string) => setOpen((o) => ({ ...o, [t]: !o[t] }));
  if (!data) return <div className="card">{error ? <Banner kind="bad">Could not load the ranking: {error}</Banner> : "Loading ranking…"}</div>;
  const c = data.coverage;
  const j = data.jobs?.fundamentals || {};
  const stm = data.stm;
  return (
    <>
      <div className="row" style={{ marginTop: 10 }}>
        <h1 className="sp">Good businesses at attractive prices</h1>
        <label className="row small"><span className="mute">Required margin of safety</span>
          <input className="num" type="number" min={0} max={90} step={1} style={{ width: 76 }} value={Math.round(mos * 100)}
            onChange={(e) => setMos(Number(e.target.value) / 100)} aria-label="Required margin of safety percent" />%
          <Chip title="Not a Buffett quote: a user preference of this dashboard">dashboard assumption</Chip></label>
      </div>
      <div className="small mute">Buffett-inspired model assessment · S&amp;P 500 securities · quality Strong, margin of safety ≥ {pct(mos, 0)}, confidence Medium/High, quote current</div>
      {error && <Banner>Refresh failed ({error.slice(0, 80)}). Showing the last successful ranking from {new Date(okAt || 0).toLocaleTimeString()}.</Banner>}
      {!data.membership.verified && <Banner kind="bad"><b>Index membership is NOT verified against S&amp;P Dow Jones Indices.</b> {data.membership.label}. As of {data.membership.as_of}. Upload the official constituents file on the Method tab to verify.</Banner>}

      <div className="card">
        <div className="row"><b>Ranking timestamp</b> <span>{data.as_of}</span><span className="sp" /><span className="mute small">Market: {data.session.phase.replaceAll("_", " ").toLowerCase()}{data.session.closed_reason ? ` (${data.session.closed_reason})` : ""} · last completed session {data.session.last_completed_session}{data.session.early_close ? " · early close today" : ""}</span></div>
        <div className="cov" style={{ marginTop: 8 }}>
          <div><b>{c.universe}</b>securities in the universe</div>
          <div><b>{c.assessed}</b>assessed</div>
          <div><b>{c.usable_valuation}</b>usable valuations</div>
          <div><b className="up">{c.qualifying}</b>qualify</div>
        </div>
        <div className="small mute" style={{ marginTop: 8 }}>
          Of the {c.universe - c.assessed} not yet assessed: <b>{c.awaiting}</b> awaiting analysis, <b>{c.failed_fetch}</b> data fetch failed.
          Of the {c.assessed} assessed: <b>{c.failed_rule}</b> failed at least one rule, <b>{c.no_valuation}</b> have insufficient evidence for a valuation, <b>{c.stale_quotes}</b> have a stale quote.
          {j.running && <> Analysis running: {j.done + j.failed}/{j.total} this pass.</>}
        </div>
        {c.assessed < c.universe && <div className="bar" style={{ marginTop: 8 }}><i style={{ width: `${(c.assessed / c.universe) * 100}%` }} /></div>}
      </div>

      <div className="card" data-testid="stm-card">
        <div className="row"><b>Pinned: STMicroelectronics (NYSE: STM)</b>{!stm.in_index && <Chip title="STM is not an S&P 500 constituent; rules below are separate from index eligibility">not in S&amp;P 500 list</Chip>}<span className="sp" /><OwnedBox ticker="STM" label="I own STM" /></div>
        <div className="row" style={{ marginTop: 4 }}>
          <span className="b" style={{ fontSize: "1.3rem" }}>{price(stm.price, stm.currency)}</span>
          <span className="mute small">{stm.price_time}</span><QuoteChip status={stm.quote_status} reason={stm.quote_reason} />
          <ValChip v={stm.valuation_label} /><QualityChip q={stm.quality} /><span>Margin of safety <MosText m={stm.margin_of_safety} /></span>
          <span className="sp" /><a className="btn primary" href="#/stock/STM">Open STM analysis →</a>
        </div>
        {stm.rules && <details><summary>Does STM pass the four financial rules? {stm.qualifies ? "Yes" : "No"} (separate from index membership)</summary><RuleList rules={stm.rules} /></details>}
      </div>

      <h2>Top qualifying stocks ({data.qualifying_total ? `showing ${data.qualifying.length} of ${data.qualifying_total}` : "none today"})</h2>
      <div className="card" style={{ padding: "4px 16px" }}>
        {data.qualifying.length === 0 && <div style={{ padding: 12 }}>
          <b>No S&amp;P 500 stock meets all four rules right now.</b> {c.assessed < c.universe ? `${c.universe - c.assessed} securities are still awaiting analysis, so this can change as the analysis completes.` : "Every security has been assessed."} The closest assessed candidates are listed separately below.</div>}
        {data.qualifying.map((r: any, i: number) => <PickRow key={r.ticker} r={r} rank={i + 1} open={!!open[r.ticker]} onToggle={() => tog(r.ticker)} />)}
      </div>
      <div className="small mute"><b>Order:</b> {data.ranking_explanation}</div>

      {data.qualifying_total < 10 && (
        <details style={{ marginTop: 12 }} open={data.qualifying_total === 0}>
          <summary>Closest assessed candidates (did not qualify) - {data.closest.length}</summary>
          <div className="card" style={{ padding: "4px 16px" }}>
            {data.closest.length === 0 && <div style={{ padding: 12 }} className="mute">No assessed stock has a usable valuation yet.</div>}
            {data.closest.map((r: any) => <PickRow key={r.ticker} r={r} closest open={!!open["c" + r.ticker]} onToggle={() => tog("c" + r.ticker)} />)}
          </div>
        </details>
      )}
    </>
  );
}
