import { useState } from "react";
import { Banner, Chip, MosText, OwnedBox, PickRow, QualityChip, QuoteChip, RuleList, ValChip } from "./common";
import { pct, price, setMos, stockHref, useApi, usePrefs, when } from "./lib";

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
          <div className="eyebrow">S&amp;P 500 · Buffett-inspired</div>
          <h1>Good businesses at attractive prices</h1>
        </div>
        <label className="row small" htmlFor="mos-input">
          <span className="mute">Margin of safety ≥</span>
          <span className="row" style={{ gap: 4 }}>
            <input id="mos-input" className="num" type="number" min={0} max={90} step={1} style={{ width: 64, textAlign: "right" }} value={Math.round(mos * 100)}
              onChange={(e) => setMos(Number(e.target.value) / 100)} aria-label="Required margin of safety percent" />%
          </span>
        </label>
      </div>

      {error && <Banner>Refresh failed. Showing {new Date(okAt || 0).toLocaleTimeString()}.</Banner>}
      {!data.membership.verified && <Banner kind="bad">Index list unverified (Wikipedia). <a href="#method">Verify</a></Banner>}

      <div className="cov">
        <div><b>{c.universe}</b>securities</div>
        <div><b>{c.assessed}</b>assessed</div>
        <div><b>{c.usable_valuation}</b>usable valuations</div>
        <div><b className="up">{c.qualifying}</b>qualify</div>
      </div>
      <div className="tiny mute" title={`${c.awaiting} awaiting, ${c.failed_fetch} fetch failed, ${c.failed_rule} missed a rule, ${c.no_valuation} no valuation, ${c.stale_quotes} stale quotes`}>
        Ranked {when(data.as_of)} ET{c.awaiting ? ` · ${c.awaiting} awaiting analysis` : ""}{j.running ? ` · analysing ${j.done + j.failed}/${j.total}` : ""}
      </div>

      <h2>Top qualifying stocks</h2>
      <div className="list">
        {data.qualifying.length === 0 && <div style={{ padding: "14px 0" }}>
          None today. See closest candidates below.</div>}
        {data.qualifying.map((r: any, i: number) => <PickRow key={r.ticker} r={r} rank={i + 1} open={!!open[r.ticker]} onToggle={() => tog(r.ticker)} />)}
      </div>
      <div className="tiny mute" style={{ marginTop: 8 }} title={data.ranking_explanation}>Ordered by confidence, bear-case discount, quality.</div>

      <h2>STMicroelectronics</h2>
      <div className="card" data-testid="stm-card" style={{ marginTop: 0 }}>
        <div className="row">
          <a className="tk" href={stockHref("STM")}>STM</a>
          {!stm.in_index && <Chip>not in S&amp;P 500 list</Chip>}
          <span className="sp" />
          <OwnedBox ticker="STM" label="I own STM" />
        </div>
        <div className="row" style={{ marginTop: 6 }}>
          <span className="mos" style={{ fontSize: "1.4rem" }}>{price(stm.price, stm.currency)}</span>
          <ValChip v={stm.valuation_label} /><QualityChip q={stm.quality} />
          <MosText m={stm.margin_of_safety} />
          <span className="sp" />
          <a className="btn primary" href={stockHref("STM")}>Open</a>
        </div>
        {stm.rules && <details style={{ marginTop: 6 }}><summary>Buy rules: {stm.rules.filter((r: any) => r.passed).length}/4 met</summary><RuleList rules={stm.rules} /></details>}
      </div>

      {data.qualifying_total < 10 && (
        <details style={{ marginTop: 18 }} open={data.qualifying_total === 0}>
          <summary>Closest candidates</summary>
          <div className="list" style={{ marginTop: 8 }}>
            {data.closest.length === 0 && <div style={{ padding: 12 }} className="mute">No assessed stock has a usable valuation yet.</div>}
            {data.closest.map((r: any) => <PickRow key={r.ticker} r={r} closest open={!!open["c" + r.ticker]} onToggle={() => tog("c" + r.ticker)} />)}
          </div>
        </details>
      )}
    </>
  );
}
