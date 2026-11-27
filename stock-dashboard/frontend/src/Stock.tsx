import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Banner, Chip, ConfChip, MosText, OwnedBox, QualityChip, QuoteChip, RuleList, ValChip } from "./common";
import { Compare, Extras, Fundamentals, ImportPanel, Perspectives, Sources } from "./StockData";
import { N, cell, num, pct, price, spct, useApi, useDebounced, usePrefs, when } from "./lib";
import { STATIC, getJson, postValuation } from "./api";
import { About, CeoLink, CeoPanel } from "./Ceo";
import RatioCharts from "./RatioCharts";

const fmtVal = (v: any, unit: string, ccy = "USD") =>
  unit === "pct" ? pct(v, 1) : unit === "pct2" ? `${pct(v[0], 1)} → ${pct(v[1], 1)}` : unit === "years" ? `${v} yrs` : unit === "money" ? price(v, ccy) : unit === "x" ? `${num(v, 2)}x` : String(v);
const fvTxt = (x: number, ccy: string) => (x <= 0 ? "≤ 0" : price(x, ccy));

export default function Stock({ ticker }: { ticker: string }) {
  const { mos } = usePrefs();
  const base = useApi<any>(`/api/stock/${ticker}?mos=${mos}`, { keep: false });
  const [tab, setTab] = useState("overview");
  const d = base.data;
  const active = (m?: string) => ["REGULAR", "PRE", "POST"].includes(m || "");
  const pricing = useApi<any>(`/api/pricing/${ticker}?mos=${mos}`, { every: 60000, enabled: !!d, keep: true });
  const [manual, setManual] = useState<{ busy: boolean; err: string | null }>({ busy: false, err: null });
  const [auto, setAuto] = useState(true);
  const [ceoOpen, setCeoOpen] = useState(false);
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
      pricing.setData(await getJson(`/api/pricing/${ticker}?mos=${mos}&force=1`));
      setManual({ busy: false, err: null });
    } catch (e: any) {
      setManual({ busy: false, err: String(e.message || e) });
    }
  }
  if (!d) return <div className="card">{base.error ? <Banner kind="bad">{base.error}</Banner> : `Loading ${ticker}…`}</div>;
  const q = pricing.data?.quote || d.quote;
  const pv = pricing.data?.price_view || d.price_view;
  const rev = pricing.data?.reverse ?? d.reverse;
  const narr = pricing.data?.narrative || d.narrative;
  const v = d.valuation;
  const ccy = d.basis.quote_currency || "USD";
  const ext = q.pre_market ? ["Pre-market", q.pre_market] : q.post_market ? ["After hours", q.post_market] : null;
  const tabs = [["overview", "Overview"], ["valuation", "Valuation"], ["quality", "Quality"], ["fund", "Financials"], ["compare", "Compare"], ["persp", "Graham & Lynch"], ["sources", "Sources"]];
  return (
    <>
      <div className="page-head">
        <div className="sp"><div className="eyebrow">{d.ticker} · {d.exchange}</div><h1>{d.name}</h1>
          <div className="row small mute" style={{ marginTop: 4, gap: 8 }}>{d.industry}{!d.in_sp500_list && <Chip>not in S&amp;P 500 list</Chip>}<CeoLink d={d} onOpen={() => setCeoOpen(true)} /></div></div>
        <OwnedBox ticker={d.ticker} label="I own this stock" />
      </div>

      <div className="card" data-testid="quote-card">
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div className="big-price" data-testid="price">{price(q.price, ccy)}</div>
          <div className={`b ${q.change >= 0 ? "up" : "down"}`} style={{ paddingBottom: 3 }}>{N(q.change) ? "" : `${q.change >= 0 ? "+" : "−"}${Math.abs(q.change).toFixed(2)} (${spct(q.change_pct / 100, 2)})`}</div>
          <span className="sp" />
          {!STATIC && <><label className="own"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /><span>Auto</span></label>
            <button className="btn" onClick={() => refreshNow(true)} disabled={manual.busy} data-testid="refresh">{manual.busy ? "…" : "Refresh"}</button></>}
        </div>
        <div className="small mute row" style={{ gap: 8, marginTop: 6 }}>
          <span><b>{q.price_label}</b> · {when(q.regular_time_et)} ET</span>
          <QuoteChip status={q.freshness?.status} reason={q.freshness?.reason} />
          {ext && <span>{ext[0]} {price(ext[1].price, ccy)} ({spct(ext[1].pct_vs_regular_close / 100, 2)})</span>}
          {(() => { const pe = d.ratios?.find((r: any) => r.key === "pe")?.latest; return pe ? <span data-testid="pe">P/E <b>{pe.toFixed(1)}</b></span> : null; })()}
        </div>
        {(manual.err || pricing.error || q.refresh_error) && <Banner>{STATIC ? "Snapshot: live refresh runs in the local app." : `Quote refresh failed. Showing ${when(q.stored_at_et)}.`}</Banner>}
      </div>

      {!v.usable && <Banner kind="bad">No credible valuation: {(v.blockers || []).join("; ")}</Banner>}

      <div className="grid2">
        <div className="card">
          <h3>Quality</h3>
          <div className="row"><QualityChip q={d.quality.label} />{d.quality.score != null && <span className="b">{d.quality.score}/100</span>}</div>
        </div>
        <div className="card" data-testid="valuation-card">
          <div className="row"><h3 className="sp" style={{ margin: 0 }}>Valuation</h3><ValChip v={pv.valuation_label} /><ConfChip c={pv.confidence} /></div>
          <div className="kv" style={{ marginTop: 10 }}>
            <div><small>Fair value</small><b>{price(pv.fv_base, ccy)}</b></div>
            <div><small>Margin of safety</small><MosText m={pv.margin_of_safety} /></div>
            <div><small>Upside</small><b>{spct(pv.upside)}</b></div>
            <div><small>Watch price</small><b>{price(pv.watch_price, ccy)}</b></div>
          </div>
          {d.analyst && <div className="small mute" style={{ marginTop: 8 }} data-testid="analyst">
            Analyst target <b style={{ color: "var(--ink)" }}>{price(d.analyst.median ?? d.analyst.mean, ccy)}</b> · {price(d.analyst.low, ccy)}–{price(d.analyst.high, ccy)} · {d.analyst.n} analysts <Chip>estimate, not used</Chip>
          </div>}
        </div>
      </div>

      <div className="card">
        <div className="row"><h3 className="sp" style={{ margin: 0 }}>Buy rules</h3><Chip cls={pv.qualifies ? "good" : ""}>{pv.rules.filter((r: any) => r.passed).length}/4 met</Chip></div>
        <RuleList rules={pv.rules} />
      </div>

      <div className="tabbar" role="tablist">{tabs.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>

      {tab === "overview" && <Overview d={d} pv={pv} ccy={ccy} mos={mos} />}
      {tab === "valuation" && <Valuation d={d} pv={pv} rev={rev} ccy={ccy} mos={mos} price_={pv.price} />}
      {tab === "quality" && <Quality d={d} />}
      {tab === "fund" && <><Fundamentals d={d} /><Extras ticker={d.ticker} ccy={d.basis.reporting_currency} /></>}
      {tab === "compare" && <Compare d={d} />}
      {tab === "persp" && <Perspectives d={d} />}
      {tab === "sources" && <><Sources d={d} />{!STATIC && <ImportPanel d={d} onDone={() => base.reload()} />}</>}

      {ceoOpen && <CeoPanel ticker={d.ticker} onClose={() => setCeoOpen(false)} />}
      <div className="card thesis" data-testid="thesis">
        <h2>Thesis</h2>
        <p>{narr.thesis}</p>
        <p><b>Risk.</b> {narr.risk}</p>
        <p style={{ marginBottom: 0 }}><b>Watch for.</b> {narr.watch}</p>
      </div>
    </>
  );
}

function Overview({ d, pv, ccy, mos }: any) {
  const v = d.valuation;
  const news = useApi<any>(`/api/extra/${d.ticker}`);
  const pos = (m: number) => Math.max(0, Math.min(100, ((m + 0.4) / 0.9) * 100));
  const cur = pv.margin_of_safety;
  const items = news.data?.news?.items || [];
  return (
    <>
      <About d={d} />
      <Ratios rows={d.ratios || []} ccy={ccy} />
      <RatioCharts d={d} />
      {v.usable && (
        <div className="card">
          <div className="kv">
            {["bear", "base", "bull"].map((s) => <div key={s}><small>{s[0].toUpperCase() + s.slice(1)}</small><b style={{ fontSize: "1.2rem" }}>{fvTxt(v.scenarios[s].fair_value, ccy)}</b></div>)}
          </div>
          <div style={{ position: "relative", height: 26, margin: "16px 0 6px" }}>
            <div style={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden", marginTop: 12 }}>
              <div style={{ width: `${pos(-0.15)}%`, background: "var(--bad)" }} />
              <div style={{ width: `${pos(0.10) - pos(-0.15)}%`, background: "var(--warn)" }} />
              <div style={{ width: `${pos(mos) - pos(0.10)}%`, background: "var(--accent)" }} />
              <div style={{ flex: 1, background: "var(--good)" }} />
            </div>
            {cur != null && <div style={{ position: "absolute", left: `calc(${pos(cur)}% - 6px)`, top: 0, fontSize: 12, lineHeight: 1 }}>▼</div>}
          </div>
          <div className="row tiny mute" style={{ justifyContent: "space-between" }}><span>Expensive</span><span>Fair</span><span>Undervalued</span><span>Buy ≥ {pct(mos, 0)}</span></div>
        </div>
      )}
      {items.length > 0 && (
        <div className="card">
          <h3>News</h3>
          <ul className="tight small">{items.map((n: any, i: number) => <li key={i}><a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> <span className="mute tiny">{when(n.published)}</span></li>)}</ul>
        </div>
      )}
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
  if (!v.usable) return <div className="card mute">No valuation available.</div>;
  const spec = v.assumption_spec;
  const bp = v.base_params;
  const val = (k: string) => (k in ov ? ov[k] : bp[k]);
  return (
    <>
      <div className="card">
        <div className="row"><h3 className="sp" style={{ margin: 0 }}>Scenarios</h3><span className="tiny mute">{v.method.split(" (")[0].split(":")[0]}</span></div>
        <div className="scroll" style={{ marginTop: 10 }}><table className="t">
          <thead><tr><th></th><th>Bear</th><th>Base</th><th>Bull</th></tr></thead>
          <tbody>
            <tr><td><b>Fair value</b></td>{["bear", "base", "bull"].map((s) => <td key={s}><b>{fvTxt(v.scenarios[s].fair_value, ccy)}</b></td>)}</tr>
            {v.scenarios.base.params.map((p: any, i: number) => (
              <tr key={i}><td>{p.label.split(" (")[0]}</td>{["bear", "base", "bull"].map((s) => <td key={s}>{fmtVal(v.scenarios[s].params[i].value, v.scenarios[s].params[i].unit, ccy)}</td>)}</tr>
            ))}
          </tbody>
        </table></div>
        <div className="small" style={{ marginTop: 10 }}>Cross-check {v.cross_value ? price(v.cross_value, ccy) : "n/a"} {v.agree ? <Chip cls="good">agrees</Chip> : <Chip cls="warn">differs</Chip>}</div>
      </div>

      <div className="card">
        <div className="row"><h3 className="sp" style={{ margin: 0 }}>Confidence</h3><ConfChip c={v.confidence.level} /><span className="small mute">{v.confidence.points}/{v.confidence.max}</span></div>
        <div className="kv" style={{ marginTop: 10 }}>{v.confidence.breakdown.map((b: any) => <div key={b.factor} title={b.detail}><small>{b.factor === "Model suitability" ? "Model suitability" : b.factor}</small>{b.points}/{b.max}</div>)}</div>
      </div>

      <div className="card" data-testid="assumptions">
        <div className="row"><h3 className="sp" style={{ margin: 0 }}>Your assumptions</h3><button className="btn" onClick={() => setOv({})} disabled={!has}>Reset</button></div>
        {spec.map((s: any) => {
          const cur = val(s.key);
          const isPct = s.unit === "pct";
          const max = s.max ?? Math.max(1, bp[s.key] * 2);
          return (
            <div className="asm" key={s.key}>
              <label htmlFor={"a-" + s.key} className="small">{s.label}</label>
              <input id={"a-" + s.key} type="range" min={s.min} max={max} step={s.step} value={cur} onChange={(e) => setOv((o) => ({ ...o, [s.key]: Number(e.target.value) }))} />
              <input className="num" type="number" step={isPct ? 0.1 : s.step} style={{ width: 92 }} value={isPct ? +(cur * 100).toFixed(2) : +cur.toFixed(2)}
                onChange={(e) => setOv((o) => ({ ...o, [s.key]: isPct ? Number(e.target.value) / 100 : Number(e.target.value) }))} data-testid={`as-${s.key}`} />
            </div>
          );
        })}
        {err && <Banner kind="bad">{err}</Banner>}
        {res && (
          <div className="kv" style={{ marginTop: 10 }} data-testid="custom-result">
            <div><small>Fair value</small><b data-testid="custom-fv">{price(res.fair_value, ccy)}</b></div>
            <div><small>Margin of safety</small><MosText m={res.metrics.margin_of_safety} /></div>
            <div><small>Watch price</small><b data-testid="custom-watch">{price(res.metrics.watch_price, ccy)}</b></div>
            <div><small>Verdict</small><ValChip v={res.label} /></div>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Sensitivity</h3>
        <Sens s={res?.sensitivity || v.sensitivity} price_={price_} mos={mos} ccy={ccy} kind={v.kind} />
      </div>

      {rev && <div className="card" data-testid="reverse"><h3>Priced in</h3><p className="small" style={{ margin: 0 }}>{rev.text}</p>
        {d.analyst?.implied && <p className="small" style={{ margin: "8px 0 0" }}>Analyst target {price(d.analyst.median ?? d.analyst.mean, ccy)}: {d.analyst.implied.replace("Price implies", "needs")}</p>}</div>}
      {v.midcycle && <MidCycle m={v.midcycle} ccy={ccy} />}
    </>
  );
}

function Sens({ s, price_, mos, ccy, kind }: any) {
  const x = kind === "financial" ? "ROE" : kind === "reit" ? "Growth" : "Growth";
  return (
    <div className="scroll"><table className="t">
      <thead><tr><th>Rate ↓ · {x} →</th>{s.cols.map((c: number, i: number) => <th key={i}>{pct(c, 1)}</th>)}</tr></thead>
      <tbody>{s.rows.map((r: number, i: number) => (
        <tr key={i}><td><b>{pct(r, 1)}</b></td>
          {s.values[i].map((x: number | null, j: number) => {
            const m = x && x > 0 && price_ ? (x - price_) / x : null;
            return <td key={j} style={{ color: m == null ? undefined : m >= mos ? "var(--good)" : m >= 0 ? "var(--warn)" : "var(--bad)", fontWeight: i === 2 && j === 2 ? 700 : 400 }}>{x == null ? "N/A" : x <= 0 ? "≤0" : price(x, ccy)}</td>;
          })}</tr>))}</tbody>
    </table></div>
  );
}

function MidCycle({ m, ccy }: any) {
  const lab: any = { "recover_base|capex_base": "Recovery 3 yrs · capex normal", "recover_base|capex_elevated": "Recovery 3 yrs · capex stays elevated", "recover_slow|capex_base": "Recovery 6 yrs · capex normal", "recover_slow|capex_elevated": "Recovery 6 yrs · capex stays elevated" };
  return (
    <div className="card" data-testid="midcycle">
      <h3>Mid-cycle</h3>
      <div className="kv">
        <div><small>Reported EPS</small><b>{num(m.reported_eps_latest)}</b></div>
        <div><small>Mid-cycle EPS</small><b>{num(m.midcycle_eps_estimate)}</b></div>
        <div><small>Margin now</small><b>{pct(m.reported_op_margin_latest)}</b></div>
        <div><small>Mid-cycle margin</small><b>{pct(m.normalized_op_margin)}</b></div>
      </div>
      <div className="scroll" style={{ marginTop: 10 }}><table className="t"><thead><tr><th>Year</th><th>Revenue (M)</th><th>Op. margin</th><th>EPS</th><th></th></tr></thead>
        <tbody>{m.years.map((y: any) => <tr key={y.fy}><td>{y.fy}</td><td>{cell(y.revenue, "money")}</td><td>{pct(y.op_margin)}</td><td>{num(y.eps)}</td><td><Chip cls={y.position === "peak" ? "warn" : y.position === "trough" ? "bad" : "good"}>{y.position === "near mid-cycle" ? "mid" : y.position}</Chip></td></tr>)}</tbody></table></div>
      <div className="scroll" style={{ marginTop: 10 }}><table className="t"><tbody>{Object.entries(m.grid).map(([k, x]: any) => <tr key={k}><td>{lab[k]}</td><td><b>{price(x, ccy)}</b></td></tr>)}</tbody></table></div>
    </div>
  );
}

function Quality({ d }: any) {
  const q = d.quality;
  return (
    <>
      {q.reason && <Banner kind="bad">{q.reason}</Banner>}
      {q.pillars.map((p: any) => {
        const f = p.figures[0];
        return (
          <div className="card" key={p.key}>
            <div className="row"><b className="sp">{p.name}</b><Chip cls={p.status === "pass" ? "good" : p.status === "partial" ? "warn" : "bad"}>{p.points}/20</Chip></div>
            <div className="small mute">{p.summary}</div>
            {f && f.points.length > 0 && (
              <div style={{ width: "100%", height: 110, marginTop: 8 }}>
                <ResponsiveContainer><BarChart data={f.points.map((x: any) => ({ fy: x.fy, v: x.value }))}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} /><XAxis dataKey="fy" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 11 }} width={48} axisLine={false} tickLine={false} tickFormatter={(x) => (f.kind === "pct" ? pct(x, 0) : f.kind === "money" || f.kind === "shares" ? (x / 1e6).toFixed(0) + "M" : x.toFixed(1))} />
                  <Tooltip formatter={(x: any) => (f.kind === "pct" ? pct(x) : f.kind === "money" || f.kind === "shares" ? cell(x, f.kind) : Number(x).toFixed(2))} /><Bar dataKey="v" name={f.name} fill="var(--accent)" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer>
              </div>
            )}
          </div>
        );
      })}
      {q.moat.supports.length > 0 && <div className="card"><h3>Moat signals</h3>
        <ul className="tight small">{q.moat.supports.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
        <h3 style={{ marginTop: 10 }}>Would weaken it</h3><ul className="tight small">{q.moat.weakens.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul></div>}
    </>
  );
}

function Ratios({ rows, ccy }: any) {
  const f = (r: any, v: any) => (v == null ? "N/A" : r.unit === "pct" ? pct(v, 1) : r.unit === "x" ? v.toFixed(2) : price(v, ccy));
  const mark = (s: string) => (s === "pass" ? <b className="pill-pass">✓</b> : s === "fail" ? <b className="pill-fail">✗</b> : <span className="mute">–</span>);
  return (
    <div className="card" data-testid="ratios">
      <div className="row"><h3 className="sp" style={{ margin: 0 }}>Buffett checklist</h3><span className="small mute">{rows.filter((r: any) => r.status === "pass").length}/{rows.filter((r: any) => r.status === "pass" || r.status === "fail").length} pass</span></div>
      <div className="scroll" style={{ marginTop: 10 }}><table className="t">
        <thead><tr><th>Ratio</th><th>Latest</th><th className="hide-p">Avg</th><th>Target</th><th></th></tr></thead>
        <tbody>{rows.map((r: any) => (
          <tr key={r.key}>
            <td title={r.formula}>{r.name}<div className="tiny mute">{r.formula}</div></td>
            <td>{f(r, r.latest)}<div className="tiny mute">{r.latest_fy || ""}{r.yahoo_trailing_pe ? ` · TTM ${r.yahoo_trailing_pe.toFixed(1)}` : ""}</div></td>
            <td className="hide-p">{r.avg == null ? "" : f(r, r.avg)}</td>
            <td style={{ whiteSpace: "normal", minWidth: 120 }}><a href={r.url} target="_blank" rel="noreferrer" title={r.basis} style={{ color: "inherit" }}>{r.target}</a></td>
            <td>{mark(r.status)}</td>
          </tr>))}</tbody>
      </table></div>
    </div>
  );
}
