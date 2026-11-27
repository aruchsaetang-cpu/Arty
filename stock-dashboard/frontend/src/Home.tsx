import { useState } from "react";
import { Banner, Chip, MosText, OwnedBox, PickRow, QualityChip, QuoteChip, RuleList, ValChip } from "./common";
import { pct, price, setMos, stockHref, useApi, usePrefs } from "./lib";

export default function Home() {
  const { mos } = usePrefs();
  const { data, error, okAt } = useApi<any>(`/api/shortlist?mos=${mos}`, { every: 60000, keep: true });
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const tog = (t: string) => setOpen((o) => ({ ...o, [t]: !o[t] }));
  if (!data) return <div className="card">{error ? <Banner kind="bad">Could not load the ranking: {error}</Banner> : "Loading ranking…"}</div>;
  const c = data.coverage;
  const j = data.jobs?.fundamentals || {};
  const stm = data.stm;
  const s = data.session;
  return (
    <>
      <div className="page-head">
        <div className="sp">
          <div className="eyebrow">Buffett-inspired model assessment · S&amp;P 500</div>
          <h1>Good businesses at attractive prices</h1>
          <div className="sub">Strong quality · price ≥ {pct(mos, 0)} below fair value · Medium/High confidence · current quote</div>
        </div>
        <label className="row small" htmlFor="mos-input">
          <span className="mute">Required margin of safety</span>
          <span className="row" style={{ gap: 4 }}>
            <input id="mos-input" className="num" type="number" min={0} max={90} step={1} style={{ width: 64, textAlign: "right" }} value={Math.round(mos * 100)}
              onChange={(e) => setMos(Number(e.target.value) / 100)} aria-label="Required margin of safety percent" />%
          </span>
          <Chip title="A preference of this dashboard, not a Buffett quote">assumption</Chip>
        </label>
      </div>

      {error && <Banner>Refresh failed. Showing the ranking from {new Date(okAt || 0).toLocaleTimeString()}.</Banner>}
      {!data.membership.verified && <Banner kind="bad"><b>Index membership is unverified.</b> The list comes from Wikipedia (as of {data.membership.as_of}), not S&amp;P Dow Jones Indices. Upload the official constituents file on the Method tab to verify it.</Banner>}

      <div className="cov">
        <div><b>{c.universe}</b>securities</div>
        <div><b>{c.assessed}</b>assessed</div>
        <div><b>{c.usable_valuation}</b>usable valuations</div>
        <div><b className="up">{c.qualifying}</b>qualify</div>
      </div>
      <div className="tiny mute">
        Ranked {data.as_of} · NYSE {s.phase.replaceAll("_", " ").toLowerCase()}{s.closed_reason ? ` (${s.closed_reason})` : ""}, last completed session {s.last_completed_session}{s.early_close ? ", early close today" : ""}.{" "}
        Not yet assessed: {c.awaiting} awaiting, {c.failed_fetch} fetch failed. Assessed: {c.failed_rule} missed a rule, {c.no_valuation} lack evidence for a valuation, {c.stale_quotes} stale quotes.
        {j.running && <> Analysis running: {j.done + j.failed}/{j.total}.</>}
      </div>

      <h2>Top qualifying stocks <span className="mute" style={{ fontWeight: 400 }}>{data.qualifying_total ? `${data.qualifying.length} of ${data.qualifying_total}` : "none today"}</span></h2>
      <div className="list">
        {data.qualifying.length === 0 && <div style={{ padding: "14px 0" }}>
          No S&amp;P 500 stock meets all four rules right now. {c.assessed < c.universe ? `${c.universe - c.assessed} securities are still awaiting analysis.` : ""} The closest candidates are listed below.</div>}
        {data.qualifying.map((r: any, i: number) => <PickRow key={r.ticker} r={r} rank={i + 1} open={!!open[r.ticker]} onToggle={() => tog(r.ticker)} />)}
      </div>
      <div className="tiny mute" style={{ marginTop: 8 }}>{data.ranking_explanation}</div>

      <h2>STMicroelectronics <span className="mute" style={{ fontWeight: 400 }}>pinned</span></h2>
      <div className="card" data-testid="stm-card" style={{ marginTop: 0 }}>
        <div className="row">
          <a className="tk" href={stockHref("STM")}>STM</a>
          {!stm.in_index && <Chip title="STM is not an S&P 500 constituent; its financial rules are judged separately">not in S&amp;P 500 list</Chip>}
          <span className="sp" />
          <OwnedBox ticker="STM" label="I own STM" />
        </div>
        <div className="row" style={{ marginTop: 6 }}>
          <span className="mos" style={{ fontSize: "1.4rem" }}>{price(stm.price, stm.currency)}</span>
          <span className="tiny mute">{stm.price_time}</span>
          <QuoteChip status={stm.quote_status} reason={stm.quote_reason} />
          <ValChip v={stm.valuation_label} /><QualityChip q={stm.quality} />
          <span className="small mute">margin of safety <MosText m={stm.margin_of_safety} /></span>
          <span className="sp" />
          <a className="btn primary" href={stockHref("STM")}>Open STM analysis</a>
        </div>
        {stm.rules && <details style={{ marginTop: 6 }}><summary>Passes the four financial rules? {stm.qualifies ? "Yes" : "No"} <span className="mute small" style={{ marginLeft: 6 }}>(index eligibility is separate)</span></summary><RuleList rules={stm.rules} /></details>}
      </div>

      {data.qualifying_total < 10 && (
        <details style={{ marginTop: 18 }} open={data.qualifying_total === 0}>
          <summary>Closest candidates that did not qualify ({data.closest.length})</summary>
          <div className="list" style={{ marginTop: 8 }}>
            {data.closest.length === 0 && <div style={{ padding: 12 }} className="mute">No assessed stock has a usable valuation yet.</div>}
            {data.closest.map((r: any) => <PickRow key={r.ticker} r={r} closest open={!!open["c" + r.ticker]} onToggle={() => tog("c" + r.ticker)} />)}
          </div>
        </details>
      )}
    </>
  );
}
