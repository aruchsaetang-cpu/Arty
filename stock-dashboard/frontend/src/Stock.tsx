import { useEffect, useMemo, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Banner, Chip, ConfChip, MosText, OwnedBox, QualityChip, QuoteChip, RuleList, ValChip } from "./common";
import { Compare, Extras, Fundamentals, ImportPanel, Perspectives, Sources } from "./StockData";
import { N, cell, num, pct, price, spct, useApi, useDebounced, usePrefs } from "./lib";
import { STATIC, getJson, postValuation } from "./api";

const fmtVal = (v: any, unit: string, ccy = "USD") =>
  unit === "pct" ? pct(v, 1) : unit === "pct2" ? `${pct(v[0], 1)} → ${pct(v[1], 1)}` : unit === "years" ? `${v} yrs` : unit === "money" ? price(v, ccy) : unit === "x" ? `${num(v, 2)}x` : String(v);

export default function Stock({ ticker }: { ticker: string }) {
  const { mos } = usePrefs();
  const base = useApi<any>(`/api/stock/${ticker}?mos=${mos}`, { keep: false });
  const [tab, setTab] = useState("overview");
  const d = base.data;
  const active = (m?: string) => ["REGULAR", "PRE", "POST"].includes(m || "");
  const pricing = useApi<any>(`/api/pricing/${ticker}?mos=${mos}`, { every: 60000, enabled: !!d, keep: true });
  const [manual, setManual] = useState<{ busy: boolean; err: string | null }>({ busy: false, err: null });
  const [auto, setAuto] = useState(true);
  // 60 s auto-refresh while visible and trading is active (pricing hook polls; this adds the FORCE flag for a real Yahoo hit)
  const forceRef = useRef(0);
  useEffect(() => {
    if (!d || !auto || STATIC) return;
    const id = setInterval(() => {
      const st = (pricing.data?.quote || d.quote)?.market_state;
      if (document.visibilityState === "visible" && active(st)) refreshNow(false);
    }, 60000);
    return () => clearInterval(id);
  }, [d, auto, ticker, mos, pricing.data]);
  async function refreshNow(manualClick = true) {
    if (manualClick) setManual({ busy: true, err: null });
    try {
      if (STATIC) throw new Error("This is a published snapshot; live quote refresh runs in the local app (scripts/run.sh).");
      pricing.setData(await getJson(`/api/pricing/${ticker}?mos=${mos}&force=1`));
      forceRef.current = Date.now();
      setManual({ busy: false, err: null });
    } catch (e: any) {
      setManual({ busy: false, err: String(e.message || e) }); // last good quote stays on screen
    }
  }
  if (!d) return <div className="card">{base.error ? <Banner kind="bad">{base.error}</Banner> : `Analysing ${ticker}… (first-time fetch of Yahoo statements can take ~10 s)`}</div>;
  const q = pricing.data?.quote || d.quote;
  const pv = pricing.data?.price_view || d.price_view;
  const rev = pricing.data?.reverse ?? d.reverse;
  const narr = pricing.data?.narrative || d.narrative;
  const v = d.valuation;
  const ccy = d.basis.quote_currency || "USD";
  const tabs = [["overview", "Overview"], ["valuation", "Valuation"], ["quality", "Quality"], ["fund", "10-year fundamentals"], ["compare", "Compare years"], ["persp", "Graham & Lynch"], ["sources", "Sources & import"]];
  return (
    <>
      <div className="row" style={{ marginTop: 10 }}>
        <div className="sp"><div className="eyebrow">{d.ticker} · {d.exchange}</div><h1>{d.name}</h1>
          <div className="small mute">{d.sector} · {d.industry} · {d.in_sp500_list ? <Chip cls="good">in S&amp;P 500 list</Chip> : <Chip>not in S&amp;P 500 list</Chip>} · {d.kind === "financial" ? "bank / insurer model" : d.kind === "reit" ? "REIT model" : "operating-company model"}</div></div>
        <OwnedBox ticker={d.ticker} label="I own this stock" />
      </div>

      <div className="card" data-testid="quote-card">
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div>
            <div className="big-price" data-testid="price">{price(q.price, ccy)}</div>
            <div className={q.change >= 0 ? "up b" : "down b"}>{N(q.change) ? "" : `${q.change >= 0 ? "+" : "−"}$${Math.abs(q.change).toFixed(2)} (${spct(q.change_pct / 100, 2)})`} <span className="mute small">today vs previous close</span></div>
          </div>
          <div className="sp small">
            <div><b>{q.price_label}</b> · market {q.market_state || q.session?.phase} · Yahoo regular-session quote time <b>{q.regular_time_et}</b></div>
            <div className="mute">{q.session?.phase?.replaceAll("_", " ").toLowerCase()}{q.session?.closed_reason ? ` (${q.session.closed_reason})` : ""} · last completed session {q.session?.last_completed_session}{q.session?.early_close ? " · early close today" : ""}</div>
            {q.pre_market && <div>Pre-market <b>{price(q.pre_market.price, ccy)}</b> ({q.pre_market.change_vs_regular_close >= 0 ? "+" : ""}{q.pre_market.change_vs_regular_close.toFixed(2)}, {spct(q.pre_market.pct_vs_regular_close / 100, 2)} vs regular close) <span className="mute">{q.pre_market.time_et}</span></div>}
            {q.post_market && <div>After-hours <b>{price(q.post_market.price, ccy)}</b> ({q.post_market.change_vs_regular_close >= 0 ? "+" : ""}{q.post_market.change_vs_regular_close.toFixed(2)}, {spct(q.post_market.pct_vs_regular_close / 100, 2)} vs regular close) <span className="mute">{q.post_market.time_et}</span></div>}
          </div>
          <div style={{ textAlign: "right", minWidth: 220 }}>
            <div className="row" style={{ justifyContent: "flex-end", gap: 6 }}><QuoteChip status={q.freshness?.status} reason={q.freshness?.reason} /><span className="tiny mute">{q.freshness?.reason}</span></div>
            {STATIC ? <div className="tiny mute" style={{ marginTop: 6 }}>Snapshot quote stored {q.stored_at_et}. Live refresh runs in the local app.</div> : <>
            <div className="row" style={{ justifyContent: "flex-end", marginTop: 6 }}>
              <label className="own"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /><span>Auto 60 s</span></label>
              <button className="btn" onClick={() => refreshNow(true)} disabled={manual.busy} data-testid="refresh">{manual.busy ? "Refreshing…" : "Refresh"}</button>
            </div>
            <div className="tiny mute">Auto-refresh {auto && active(q.market_state) ? "on while the market trades" : auto ? "paused: market not trading" : "off"} · stored {q.stored_at_et}</div></>}
          </div>
        </div>
        {(manual.err || pricing.error || q.refresh_error) && <Banner>Quote refresh failed - showing the last successful quote ({q.stored_at_et}). {q.refresh_error || ""}</Banner>}
        <div className="tiny mute">Source: Yahoo Finance. “Real-time” is shown only when Yahoo reports zero exchange delay; otherwise the reported delay or “Latest available”. Times are New York.</div>
      </div>

      {d.limits.map((l: string) => <Banner key={l} kind="info">{l}</Banner>)}
      {!v.usable && <Banner kind="bad"><b>Insufficient evidence for a credible valuation.</b> {(v.blockers || []).join("; ")}</Banner>}

      <div className="grid2">
        <div className="card">
          <h3>Business quality <span className="mute small">(Buffett-inspired model assessment)</span></h3>
          <div className="row"><QualityChip q={d.quality.label} />{d.quality.score != null && <span className="b">{d.quality.score}/100</span>}</div>
          <div className="small mute">{d.quality.reason || d.quality.pillars.map((p: any) => p.name + ": " + p.status).join(" · ")}</div>
        </div>
        <div className="card" data-testid="valuation-card">
          <h3>Valuation <span className="mute small">(independent of quality)</span></h3>
          <div className="row"><ValChip v={pv.valuation_label} /><ConfChip c={pv.confidence} /><span className="small mute">confidence</span></div>
          <div className="kv" style={{ marginTop: 8 }}>
            <div><small>Base fair value</small><b>{price(pv.fv_base, ccy)}</b></div>
            <div><small>Margin of safety</small><MosText m={pv.margin_of_safety} /></div>
            <div><small>Upside to fair value</small><b>{spct(pv.upside)}</b></div>
            <div><small>Watch price ({pct(mos, 0)} MoS)</small><b>{price(pv.watch_price, ccy)}</b>{pv.decline_to_watch ? <span className="small mute"> needs −{pct(pv.decline_to_watch, 1)}</span> : pv.watch_price ? <span className="small up"> at/below</span> : null}</div>
          </div>
          <div className="tiny mute" style={{ marginTop: 6 }}>Margin of safety = (fair value − price) / fair value · Upside = (fair value − price) / price · Watch price = fair value × (1 − required margin of safety). Price {price(pv.price, ccy)} at {q.regular_time_et}; valuation date {d.valuation_date}.</div>
        </div>
      </div>

      <div className="card">
        <h3>Shortlist rules <Chip>{pv.qualifies ? "all four met" : "does not qualify"}</Chip> <span className="small mute">(financial rules; index eligibility is separate: {d.in_sp500_list ? "in the S&P 500 list" : "not in the S&P 500 list"})</span></h3>
        <RuleList rules={pv.rules} />
      </div>

      <div className="tabbar" role="tablist">{tabs.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === "overview" && <Overview d={d} pv={pv} q={q} ccy={ccy} mos={mos} />}
      {tab === "valuation" && <Valuation d={d} pv={pv} rev={rev} ccy={ccy} mos={mos} price_={pv.price} />}
      {tab === "quality" && <Quality d={d} />}
      {tab === "fund" && <><Fundamentals d={d} /><Extras ticker={d.ticker} ccy={d.basis.reporting_currency} /></>}
      {tab === "compare" && <Compare d={d} />}
      {tab === "persp" && <Perspectives d={d} />}
      {tab === "sources" && <><Sources d={d} />{!STATIC && <ImportPanel d={d} onDone={() => base.reload()} />}</>}

      <div className="card thesis" data-testid="thesis">
        <h2 style={{ marginTop: 0 }}>Long-term thesis</h2>
        <p>{narr.thesis}</p>
        <p><b>Biggest risk.</b> {narr.risk}</p>
        <p><b>One measurable development that would change the verdict.</b> {narr.watch}</p>
        <div className="tiny mute">Buffett-inspired model assessment - not an opinion attributed to Warren Buffett. Not investment advice.</div>
      </div>
    </>
  );
}

function Overview({ d, pv, q, ccy, mos }: any) {
  const v = d.valuation;
  const news = useApi<any>(`/api/extra/${d.ticker}`);
  const pos = (m: number) => Math.max(0, Math.min(100, ((m + 0.4) / 0.9) * 100));
  const cur = pv.margin_of_safety;
  return (
    <>
      {v.usable && (
        <div className="card">
          <h3>Where the price sits against the valuation labels</h3>
          <div style={{ position: "relative", height: 34, margin: "10px 0 6px" }}>
            <div style={{ display: "flex", height: 18, borderRadius: 9, overflow: "hidden" }}>
              <div style={{ width: `${pos(-0.15)}%`, background: "var(--bad-bg)" }} />
              <div style={{ width: `${pos(0.10) - pos(-0.15)}%`, background: "var(--warn-bg)" }} />
              <div style={{ width: `${pos(mos) - pos(0.10)}%`, background: "var(--info-bg)" }} />
              <div style={{ flex: 1, background: "var(--good-bg)" }} />
            </div>
            {cur != null && <div style={{ position: "absolute", left: `calc(${pos(cur)}% - 8px)`, top: 0, fontSize: 22 }} title={`Margin of safety ${pct(cur, 1)}`}>▼</div>}
          </div>
          <div className="row small">
            <span><span className="legend-dot" style={{ background: "var(--bad)" }} />Expensive: MoS &lt; −15%</span>
            <span><span className="legend-dot" style={{ background: "var(--warn)" }} />Moderate / Fair: −15% to +10%</span>
            <span><span className="legend-dot" style={{ background: "var(--accent)" }} />Undervalued: ≥ +10% but below your buy threshold</span>
            <span><span className="legend-dot" style={{ background: "var(--good)" }} />Buy zone: MoS ≥ {pct(mos, 0)} <Chip>dashboard assumption</Chip></span>
          </div>
          <div className="small mute" style={{ marginTop: 6 }}>A company can be Undervalued (≥10%) and still fall short of your {pct(mos, 0)} required margin of safety - the labels describe value, the threshold decides whether it is on the buy list.</div>
        </div>
      )}
      {v.usable && (
        <div className="card">
          <h3>Fair value per share ({ccy}) - bear / base / bull</h3>
          <div className="kv">
            {["bear", "base", "bull"].map((s) => (
              <div key={s}><small>{s}</small><b style={{ fontSize: "1.3rem" }}>{v.scenarios[s].fair_value <= 0 ? "≤ 0 (n/m)" : price(v.scenarios[s].fair_value, ccy)}</b>
                <span className="small mute">{v.scenarios[s].fair_value > 0 && pv.price ? `price is ${spct(pv.price / v.scenarios[s].fair_value - 1)} vs this value` : "negative model value"}</span></div>
            ))}
          </div>
          <div className="small mute" style={{ marginTop: 6 }}>Method: {v.method}. Cross-check: {v.cross_method} = {v.cross_value ? price(v.cross_value, ccy) : "n/a"}.</div>
        </div>
      )}
      <div className="card">
        <h3>Company-specific news (Yahoo Finance)</h3>
        {!news.data && <span className="mute">Loading…</span>}
        {news.data?.news?.error && <div className="small mute">{news.data.news.error}</div>}
        <ul className="tight">{(news.data?.news?.items || []).map((n: any, i: number) => <li key={i}><a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> <span className="mute small">{n.publisher} · {n.published?.toString().slice(0, 10)}</span></li>)}</ul>
        <div className="tiny mute">Fetched {news.data?.news?.fetched_at}. News is context only and does not enter the valuation.</div>
      </div>
      <div className="card"><h3>About</h3><div className="small">{d.summary}{d.summary?.length >= 700 ? "…" : ""}</div>
        <div className="tiny mute" style={{ marginTop: 6 }}>Basis: quote currency {d.basis.quote_currency}; reporting currency {d.basis.reporting_currency}; {d.basis.adr_note} {d.basis.share_class_note}.</div></div>
    </>
  );
}

function Valuation({ d, pv, rev, ccy, mos, price_ }: any) {
  const v = d.valuation;
  const [ov, setOv] = useState<Record<string, number>>({});
  const dv = useDebounced(ov, 150);
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const has = Object.keys(dv).length > 0;
  useEffect(() => {
    if (!has || !v.usable) { setRes(null); setErr(null); return; }
    let live = true;
    postValuation(d.ticker, dv, mos).then((j) => { if (live) { setRes(j); setErr(null); } }).catch((e) => live && setErr(String(e.message || e)));
    return () => { live = false; };
  }, [dv, mos, d.ticker]);
  if (!v.usable) return <div className="card">No standard valuation available: {(v.blockers || []).join("; ")}</div>;
  const spec = v.assumption_spec;
  const bp = v.base_params;
  const val = (k: string) => (k in ov ? ov[k] : bp[k]);
  return (
    <>
      <div className="card">
        <h3>Standard scenarios (these drive the ranking)</h3>
        <div className="scroll"><table className="t">
          <thead><tr><th>Assumption</th><th>Bear</th><th>Base</th><th>Bull</th></tr></thead>
          <tbody>
            <tr><td><b>Fair value per share</b></td>{["bear", "base", "bull"].map((s) => <td key={s}><b>{v.scenarios[s].fair_value <= 0 ? "≤ 0 (n/m)" : price(v.scenarios[s].fair_value, ccy)}</b></td>)}</tr>
            <tr><td>Margin of safety vs price</td>{["bear", "base", "bull"].map((s) => <td key={s}><MosText m={v.scenarios[s].fair_value > 0 ? (v.scenarios[s].fair_value - pv.price) / v.scenarios[s].fair_value : null} /></td>)}</tr>
            {v.scenarios.base.params.map((p: any, i: number) => (
              <tr key={i}><td>{p.label}</td>{["bear", "base", "bull"].map((s) => <td key={s}>{fmtVal(v.scenarios[s].params[i].value, v.scenarios[s].params[i].unit, ccy)}</td>)}</tr>
            ))}
          </tbody>
        </table></div>
        <div className="small" style={{ marginTop: 8 }}><b>Method:</b> {v.method}. <b>Cross-check:</b> {v.cross_method} → {v.cross_value ? price(v.cross_value, ccy) : "n/a"} {v.agree ? <Chip cls="good">agrees within 35%</Chip> : <Chip cls="warn">material disagreement</Chip>}</div>
        {v.disagreement && <Banner>{v.disagreement}</Banner>}
        <div className="small mute">Discount rate {pct(v.r, 2)} = 10y Treasury {pct(v.rf, 2)} (Yahoo ^TNX) + clipped beta {v.beta ?? "n/a"} × 5% ERP (floor 8%, cap 12%). Shares used: {v.share_basis}. {(v.notes || []).join(" ")}</div>
        <div className="small mute">{v.owner_earnings_note}</div>
      </div>

      <div className="card">
        <h3>Confidence: <ConfChip c={v.confidence.level} /> ({v.confidence.points}/{v.confidence.max})</h3>
        <ul className="tight">{v.confidence.breakdown.map((b: any) => <li key={b.factor}><b>{b.factor}</b> {b.points}/{b.max} - <span className="mute">{b.detail}</span></li>)}</ul>
        <div className="small mute">{(d.confidence_rules || []).join(" ")}</div>
      </div>

      <div className="card" data-testid="assumptions">
        <div className="row"><h3 className="sp" style={{ margin: 0 }}>Edit assumptions - custom scenario (never changes the ranking)</h3><button className="btn" onClick={() => setOv({})} disabled={!has}>Reset to standard</button></div>
        {spec.map((s: any) => {
          const cur = val(s.key);
          const isPct = s.unit === "pct";
          const max = s.max ?? Math.max(1, bp[s.key] * 2);
          return (
            <div className="asm" key={s.key}>
              <label htmlFor={"a-" + s.key}>{s.label}</label>
              <input id={"a-" + s.key} type="range" min={s.min} max={max} step={s.step} value={cur} onChange={(e) => setOv((o) => ({ ...o, [s.key]: Number(e.target.value) }))} />
              <input className="num" type="number" step={isPct ? 0.1 : s.step} style={{ width: 92 }} value={isPct ? +(cur * 100).toFixed(2) : +cur.toFixed(2)}
                onChange={(e) => setOv((o) => ({ ...o, [s.key]: isPct ? Number(e.target.value) / 100 : Number(e.target.value) }))} data-testid={`as-${s.key}`} />
            </div>
          );
        })}
        {err && <Banner kind="bad">{err}</Banner>}
        {res && (
          <div className="kv" style={{ marginTop: 10 }} data-testid="custom-result">
            <div><small>Custom fair value (standard base {price(res.standard_base_fair_value, ccy)})</small><b data-testid="custom-fv">{price(res.fair_value, ccy)}</b></div>
            <div><small>Margin of safety</small><MosText m={res.metrics.margin_of_safety} /></div>
            <div><small>Upside to fair value</small><b>{spct(res.metrics.upside)}</b></div>
            <div><small>Watch price</small><b data-testid="custom-watch">{price(res.metrics.watch_price, ccy)}</b></div>
            <div><small>Label</small><ValChip v={res.label} /> {res.metrics.meets_required_mos ? <Chip cls="good">meets {pct(mos, 0)}</Chip> : <Chip cls="bad">short of {pct(mos, 0)}</Chip>}</div>
          </div>
        )}
        {!has && <div className="small mute" style={{ marginTop: 6 }}>Move a slider or type a value: fair value, margin of safety and watch price recalculate immediately.</div>}
      </div>

      <div className="card">
        <h3>Sensitivity: fair value per share</h3>
        <Sens s={res?.sensitivity || v.sensitivity} price_={price_} mos={mos} ccy={ccy} kind={v.kind} title={res ? "Custom scenario" : "Base scenario"} />
      </div>

      {rev && (
        <div className="card" data-testid="reverse">
          <h3>What must this company deliver to justify today’s price?</h3>
          <p>{rev.text}</p>
        </div>
      )}
      {v.midcycle && <MidCycle m={v.midcycle} ccy={ccy} />}
    </>
  );
}

function Sens({ s, price_, mos, ccy, kind, title }: any) {
  const colLabel = (x: number) => (kind === "financial" ? `ROE ${pct(x, 1)}` : kind === "reit" ? `g ${pct(x, 1)}` : `Yr-1 growth ${pct(x, 1)}`);
  return (
    <div className="scroll"><table className="t">
      <thead><tr><th>{title}: discount rate ↓ / {kind === "financial" ? "ROE" : kind === "reit" ? "growth" : "year-1 growth"} →</th>{s.cols.map((c: number, i: number) => <th key={i}>{colLabel(c)}</th>)}</tr></thead>
      <tbody>{s.rows.map((r: number, i: number) => (
        <tr key={i}><td><b>{pct(r, 1)}</b>{i === 2 ? " (base)" : ""}</td>
          {s.values[i].map((x: number | null, j: number) => {
            const m = x && x > 0 && price_ ? (x - price_) / x : null;
            return <td key={j} style={{ background: m == null ? undefined : m >= mos ? "var(--good-bg)" : m >= 0 ? "var(--warn-bg)" : "var(--bad-bg)", fontWeight: i === 2 && j === 2 ? 700 : 400 }}>{x == null ? "N/A" : x <= 0 ? "≤0" : price(x, ccy)}</td>;
          })}</tr>))}</tbody>
    </table><div className="tiny mute" style={{ padding: 8 }}>Green = meets your required margin of safety at the current price; amber = below fair value but short of it; red = price above this fair value.</div></div>
  );
}

function MidCycle({ m, ccy }: any) {
  const lab: any = { "recover_base|capex_base": "Margins recover in 3 yrs · capex converges to base", "recover_base|capex_elevated": "Margins recover in 3 yrs · capex stays elevated", "recover_slow|capex_base": "Margins recover slowly (6 yrs) · capex converges", "recover_slow|capex_elevated": "Margins recover slowly (6 yrs) · capex stays elevated" };
  return (
    <div className="card" data-testid="midcycle">
      <h3>Cyclical earnings: reported vs mid-cycle</h3>
      <div className="kv">
        <div><small>Reported EPS (latest FY)</small><b>{num(m.reported_eps_latest)}</b></div>
        <div><small>Approx. mid-cycle EPS</small><b>{num(m.midcycle_eps_estimate)}</b></div>
        <div><small>Latest operating margin</small><b>{pct(m.reported_op_margin_latest)}</b></div>
        <div><small>Normalized (mid-cycle) margin</small><b>{pct(m.normalized_op_margin)}</b></div>
      </div>
      <div className="scroll" style={{ marginTop: 8 }}><table className="t"><thead><tr><th>Fiscal year supporting normalization</th><th>Revenue (M)</th><th>Operating margin</th><th>EPS</th><th>Position</th></tr></thead>
        <tbody>{m.years.map((y: any) => <tr key={y.fy}><td>{y.fy} ({y.end})</td><td>{cell(y.revenue, "money")}</td><td>{pct(y.op_margin)}</td><td>{num(y.eps)}</td><td><Chip cls={y.position === "peak" ? "warn" : y.position === "trough" ? "bad" : "good"}>{y.position}</Chip></td></tr>)}</tbody></table></div>
      <div className="small mute">{m.window_note}</div>
      <h3>How fair value changes ({ccy} per share)</h3>
      <div className="scroll"><table className="t"><tbody>{Object.entries(m.grid).map(([k, x]: any) => <tr key={k}><td>{lab[k]}</td><td><b>{price(x, ccy)}</b></td></tr>)}</tbody></table></div>
      <div className="tiny mute">{m.grid_note}</div>
    </div>
  );
}

function Quality({ d }: any) {
  const q = d.quality;
  return (
    <>
      <div className="card"><h3>Published rules</h3>
        <div className="small">{q.rule_text}</div>
        <ul className="tight small">{q.pillar_rules.map((p: any) => <li key={p.key}><b>{p.name}.</b> {p.rule}</li>)}</ul></div>
      {q.reason && <Banner kind="bad">Insufficient evidence: {q.reason}.</Banner>}
      {q.pillars.map((p: any) => (
        <div className="card" key={p.key}>
          <div className="row"><b className="sp">{p.name}</b><Chip cls={p.status === "pass" ? "good" : p.status === "partial" ? "warn" : "bad"}>{p.status} · {p.points}/20</Chip></div>
          <div className="small">{p.summary}</div>
          {p.figures.map((f: any) => (
            <div key={f.name} style={{ marginTop: 8 }}>
              <div className="small b">{f.name}</div>
              <div style={{ width: "100%", height: 130 }}>
                <ResponsiveContainer><BarChart data={f.points.map((x: any) => ({ fy: x.fy, v: x.value }))}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="fy" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} width={54} tickFormatter={(x) => (f.kind === "pct" ? pct(x, 0) : f.kind === "money" || f.kind === "shares" ? (x / 1e6).toFixed(0) + "M" : x.toFixed(1))} />
                  <Tooltip formatter={(x: any) => (f.kind === "pct" ? pct(x) : f.kind === "money" || f.kind === "shares" ? cell(x, f.kind) : Number(x).toFixed(2))} /><Bar dataKey="v" fill="var(--accent)" /></BarChart></ResponsiveContainer>
              </div>
              <div className="tiny mute">{f.points.map((x: any) => `${x.fy} (${x.end}): ${f.kind === "pct" ? pct(x.value) : f.kind === "money" || f.kind === "shares" ? cell(x.value, f.kind) : Number(x.value).toFixed(2)}`).join(" · ")}</div>
            </div>
          ))}
        </div>
      ))}
      <div className="card"><h3>Competitive-advantage inference</h3>
        <b className="small">What supports a possible advantage</b><ul className="tight small">{q.moat.supports.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
        <b className="small">What evidence would weaken it</b><ul className="tight small">{q.moat.weakens.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
        <div className="tiny mute">{q.moat.caveat}</div></div>
    </>
  );
}
