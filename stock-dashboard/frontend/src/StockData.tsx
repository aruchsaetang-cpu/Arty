import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Banner, Chip } from "./common";
import { N, cell, mm, num, pct, pp, spct, useApi } from "./lib";

const STM_NAMES: any = { income: "Income statement", balance: "Balance sheet", cashflow: "Cash flow" };

export function Fundamentals({ d }: any) {
  const [st, setSt] = useState("income");
  const [view, setView] = useState("values");
  const [sel, setSel] = useState<any>(null);
  const cols = d.columns;
  const t = d.tables[st];
  const ccy = d.basis.reporting_currency || "reporting currency";
  const rows = view === "detail" ? t.detail : t.spec;
  const yoyCell = (r: any, i: number) => {
    if (r.kind === "pct") return N(r.pp?.[i]) ? "N/A" : pp(r.pp[i]);
    const y = r.yoy?.[i];
    if (!y) return "N/A";
    if (y.pct !== null) return spct(y.pct) + (y.transition ? ` (${y.transition})` : "");
    return `Δ ${cell(y.abs, r.kind)} (${y.transition})`;
  };
  const rawCell = (v: any) => (N(v) ? "N/A" : Math.abs(v) < 1000 ? v.toFixed(2) : mm(v));
  const chartData = sel ? cols.map((c: any, i: number) => ({ fy: c.label, v: sel.values[i] ?? null })) : [];
  return (
    <>
      <div className="card">
        <div className="tabbar" style={{ margin: 0 }}>
          {Object.keys(STM_NAMES).map((k) => <button key={k} className={st === k ? "on" : ""} onClick={() => { setSt(k); setSel(null); }}>{STM_NAMES[k]}</button>)}
          <span className="sp" />
          {[["values", "Values"], ["yoy", "Year-over-year"], ["detail", "All Yahoo line items"]].map(([k, l]) => <button key={k} className={view === k ? "on" : ""} onClick={() => setView(k)}>{l}</button>)}
        </div>
        <div className="small mute">
          Annual fiscal years, oldest → newest (FY label = calendar year in which the fiscal year ends; the month is shown under it) · {ccy} · {view === "detail" ? "millions unless the value is per-share or a ratio" : "money in millions; EPS per share; shares in millions"} ·
          Yahoo supplied <b>{t.coverage.years_with_data}</b> of {t.coverage.slots} years ({t.coverage.first ? `${t.coverage.first}–${t.coverage.last}` : "none"}); missing years are <b>N/A</b>, never zero. Source: <a href={d.sources[st].url} target="_blank" rel="noreferrer">Yahoo Finance</a> (fetched {d.sources[st].fetched}).
          {view === "yoy" && " YoY uses consecutive fiscal years only; margins show percentage-point change; profit↔loss transitions are flagged and no % is shown on a zero or negative base."}
        </div>
      </div>
      <div className="scroll tall"><table className="t stick" data-testid="fund-table">
        <thead><tr><th>{view === "detail" ? "Yahoo line item" : "Metric"}</th>{cols.map((c: any) => <th key={c.slot}>{c.label}<div className="tiny">{c.end ? c.end.slice(0, 7) : "—"}</div></th>)}</tr></thead>
        <tbody>
          {rows.map((r: any) => (
            <tr key={r.key || r.label} className="click" onClick={() => setSel(r)}>
              <td>{r.label}{r.cagr?.value != null && view === "values" && <div className="tiny mute">CAGR {pct(r.cagr.value)} over {r.cagr.years} yrs ({r.cagr.from.slice(0, 4)}–{r.cagr.to.slice(0, 4)})</div>}
                {r.cagr && r.cagr.value == null && view === "values" && <div className="tiny mute">CAGR n/m: {r.cagr.reason}</div>}</td>
              {r.values.map((v: any, i: number) => {
                const txt = view === "yoy" && r.kind ? yoyCell(r, i) : view === "detail" ? rawCell(v) : cell(v, r.kind);
                return <td key={i} className={txt === "N/A" ? "na" : v < 0 ? "neg" : ""}>{txt}{view === "detail" && r.imported?.[i] ? <sup title="imported from CSV"> ⤓</sup> : null}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table></div>
      <div className="tiny mute" style={{ margin: "6px 2px" }}>Tap any row to chart it. Capital expenditure is shown as positive spend and deducted once to reach free cash flow. If Yahoo omits “Capital Expenditure” for a year, PP&amp;E + intangibles purchases are used (matching Yahoo’s own free-cash-flow definition). {d.valuation.owner_earnings_note}</div>
      {sel && (
        <div className="card" data-testid="chart-card">
          <div className="row"><b className="sp">{sel.label}</b><button className="btn" onClick={() => setSel(null)}>Close</button></div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer>
              {sel.kind === "pct" || sel.kind === "ratio" ? (
                <LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="fy" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} width={50} tickFormatter={(x) => (sel.kind === "pct" ? pct(x, 0) : x.toFixed(1))} />
                  <Tooltip formatter={(x: any) => (sel.kind === "pct" ? pct(x) : Number(x).toFixed(2))} /><Line type="monotone" dataKey="v" stroke="var(--accent)" strokeWidth={2} connectNulls={false} dot /></LineChart>
              ) : (
                <BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="var(--line)" /><XAxis dataKey="fy" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} width={56} tickFormatter={(x) => (sel.kind === "pershare" ? x.toFixed(1) : (x / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 }))} />
                  <Tooltip formatter={(x: any) => cell(x, sel.kind)} /><Bar dataKey="v" fill="var(--accent)" /></BarChart>
              )}
            </ResponsiveContainer>
          </div>
          <div className="tiny mute">Gaps are years Yahoo did not supply (N/A) - not zeros.</div>
        </div>
      )}
    </>
  );
}

export function Extras({ ticker, ccy }: any) {
  const x = useApi<any>(`/api/extra/${ticker}`);
  const te = x.data?.trailing_and_estimates;
  const pick = (o: any, keys: string[]) => keys.map((k) => [k, o?.[k]]).filter(([, v]) => v);
  const ttmRows = [...pick(te?.ttm_income || {}, ["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"]), ...pick(te?.ttm_cashflow || {}, ["Operating Cash Flow", "Free Cash Flow"])];
  const firstVal = (o: any) => { const ks = Object.keys(o).sort(); return o[ks[ks.length - 1]]; };
  return (
    <div className="card" data-testid="extras">
      <h3>Trailing twelve months and forward analyst estimates <span className="mute small">(kept separate from the annual table)</span></h3>
      {!te && <span className="mute">Loading…</span>}
      {te?.stale_error && <Banner>{te.stale_error}</Banner>}
      {ttmRows.length > 0 && <div className="scroll"><table className="t"><thead><tr><th>Trailing 12 months (reported, {ccy})</th><th>Value</th></tr></thead><tbody>{ttmRows.map(([k, v]: any) => { const val = firstVal(v); return <tr key={k}><td>{k}</td><td>{k.includes("EPS") ? num(val) : mm(val)}</td></tr>; })}</tbody></table></div>}
      {te && Object.keys(te.earnings_estimate || {}).length > 0 && (
        <div className="scroll" style={{ marginTop: 8 }}><table className="t"><thead><tr><th>Analyst EPS estimate (consensus)</th><th>Avg</th><th>Low</th><th>High</th><th>Analysts</th><th>Growth</th></tr></thead>
          <tbody>{Object.entries(te.earnings_estimate).map(([p, r]: any) => <tr key={p}><td>{p}</td><td>{num(r.avg)}</td><td>{num(r.low)}</td><td>{num(r.high)}</td><td>{r.numberOfAnalysts ?? "N/A"}</td><td>{N(r.growth) ? "N/A" : spct(r.growth)}</td></tr>)}</tbody></table></div>
      )}
      {te && Object.keys(te.revenue_estimate || {}).length > 0 && (
        <div className="scroll" style={{ marginTop: 8 }}><table className="t"><thead><tr><th>Analyst revenue estimate (consensus)</th><th>Avg (M)</th><th>Low (M)</th><th>High (M)</th><th>Analysts</th><th>Growth</th></tr></thead>
          <tbody>{Object.entries(te.revenue_estimate).map(([p, r]: any) => <tr key={p}><td>{p}</td><td>{mm(r.avg)}</td><td>{mm(r.low)}</td><td>{mm(r.high)}</td><td>{r.numberOfAnalysts ?? "N/A"}</td><td>{N(r.growth) ? "N/A" : spct(r.growth)}</td></tr>)}</tbody></table></div>
      )}
      <div className="tiny mute">Trailing figures are reported (Yahoo). Estimates are analyst opinions from Yahoo and are never used in the valuation or the ranking. Fetched {te?.fetched_at ? new Date(te.fetched_at * 1000).toLocaleString() : "…"}.</div>
    </div>
  );
}

export function Compare({ d }: any) {
  const ends = d.columns.filter((c: any) => c.end);
  const [a, setA] = useState(ends.length > 1 ? ends[ends.length - 2].end : ends[0]?.end);
  const [b, setB] = useState(ends.length ? ends[ends.length - 1].end : "");
  const { data, error } = useApi<any>(a && b ? `/api/compare/${d.ticker}?a=${a}&b=${b}` : null, { keep: true });
  const lab = (e: string) => ends.find((c: any) => c.end === e)?.label + " (" + e + ")";
  return (
    <>
      <div className="card row">
        <label>Year A <select className="num" value={a} onChange={(e) => setA(e.target.value)} aria-label="Year A">{ends.map((c: any) => <option key={c.end} value={c.end}>{c.label} · {c.end}</option>)}</select></label>
        <label>Year B <select className="num" value={b} onChange={(e) => setB(e.target.value)} aria-label="Year B">{ends.map((c: any) => <option key={c.end} value={c.end}>{c.label} · {c.end}</option>)}</select></label>
        <span className="small mute">Every reported line item, side by side. N/A = Yahoo did not report it. % change is blank when the baseline is zero or negative; an absolute change and any profit↔loss transition are shown instead.</span>
      </div>
      {error && <Banner kind="bad">{error}</Banner>}
      {data && Object.entries(data.rows).map(([st, rows]: any) => (
        <div key={st}>
          <h3>{STM_NAMES[st]}: {lab(a)} vs {lab(b)}</h3>
          <div className="scroll tall"><table className="t stick" data-testid={`cmp-${st}`}>
            <thead><tr><th>Yahoo line item</th><th>{a.slice(0, 4)}</th><th>{b.slice(0, 4)}</th><th>Change</th><th>% change</th><th>Note</th></tr></thead>
            <tbody>{rows.map((r: any) => {
              const f = (v: any) => (N(v) ? "N/A" : Math.abs(v) < 1000 ? v.toFixed(2) : mm(v));
              return <tr key={r.label}><td>{r.label}</td><td className={N(r.a) ? "na" : ""}>{f(r.a)}</td><td className={N(r.b) ? "na" : ""}>{f(r.b)}</td><td>{N(r.abs) ? "N/A" : Math.abs(r.abs) < 1000 ? r.abs.toFixed(2) : mm(r.abs)}</td><td>{N(r.pct) ? "—" : spct(r.pct)}</td><td className="small">{r.note || ""}</td></tr>;
            })}</tbody>
          </table></div>
        </div>
      ))}
    </>
  );
}

const resClass = (r: string) => (r === "pass" ? "good" : r === "fail" ? "bad" : r === "neutral" ? "warn" : "");
export function Perspectives({ d }: any) {
  const g = d.graham, l = d.lynch;
  return (
    <>
      <div className="banner info">Secondary perspectives. The main ranking uses the Buffett-inspired framework only.</div>
      <div className="card" data-testid="graham"><h3>Graham: defensive-investor criteria</h3>
        <div className="row"><Chip cls={g.passed / Math.max(g.applicable, 1) >= .75 ? "good" : "warn"}>{g.verdict}</Chip><span className="small mute">{g.passed} of {g.applicable} applicable tests passed</span></div>
        <ul className="tight">{g.tests.map((t: any, i: number) => <li key={i}><Chip cls={resClass(t.result)}>{t.result}</Chip> {t.test} <span className="mute small">- {t.detail}</span></li>)}</ul>
        <div className="small">Graham number (√(22.5 × avg EPS × book value/share)): <b>{g.graham_number ? g.graham_number.toFixed(2) : "n/a"}</b>{g.graham_mos != null && <> · margin of safety vs Graham number <b>{pct(g.graham_mos, 0)}</b></>}</div>
        <div className="tiny mute">{g.note} Source: Benjamin Graham, <i>The Intelligent Investor</i> (rev. ed. 1973), chs. 14 and 20.</div></div>
      <div className="card" data-testid="lynch"><h3>Lynch: business type and per-share growth</h3>
        <div className="row"><Chip>{l.category}</Chip><span className="small mute">{l.category_reason}</span></div>
        <ul className="tight">{l.checks.map((t: any, i: number) => <li key={i}><Chip cls={resClass(t.result)}>{t.result}</Chip> {t.test} <span className="mute small">- {t.detail}</span></li>)}</ul>
        <div className="tiny mute">{l.note} Source: Peter Lynch, <i>One Up on Wall Street</i> (1989).</div></div>
    </>
  );
}

export function Sources({ d }: any) {
  return (
    <>
      <div className="card"><h3>Data sources and what kind of figure each is</h3>
        <div className="small mute">{d.data_kinds}</div>
        <ul className="tight">{Object.values(d.sources).map((s: any) => <li key={s.label}>{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.label}</a> : s.label} <Chip>{s.type}</Chip> <span className="small mute">{s.fetched ? `fetched ${s.fetched}` : s.version ? `model ${s.version}` : ""}</span></li>)}
          <li><a href={d.membership.url} target="_blank" rel="noreferrer">{d.membership.label}</a> <Chip>{d.membership.verified ? "official" : "unverified secondary"}</Chip> <span className="small mute">as of {d.membership.as_of}</span></li></ul></div>
      <div className="card"><h3>Investing principles behind the model (primary sources)</h3>
        <ul className="tight small">{d.principles.map((p: any) => <li key={p.id}><b>{p.title}</b> - {p.source}, dated {p.date}. <a href={p.url} target="_blank" rel="noreferrer">link</a> <span className="mute">Used for: {p.used_for}.</span></li>)}</ul>
        <div className="tiny mute">Results are labelled “Buffett-inspired model assessment”. No stock-specific opinion is attributed to Warren Buffett: none is used, because no dated primary source for such an opinion is part of this model. Letter links were not machine-verified in this environment (host not reachable from the build sandbox) - confirm wording at the link.</div></div>
    </>
  );
}

export function ImportPanel({ d, onDone }: any) {
  const [file, setFile] = useState<File | null>(null);
  const [ccy, setCcy] = useState(d.basis.reporting_currency || "USD");
  const [units, setUnits] = useState("units");
  const [stmt, setStmt] = useState("");
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  async function send(commit: boolean, resolve = "") {
    if (!file) return;
    setBusy(true); setMsg(null);
    const fd = new FormData();
    fd.append("file", file); fd.append("currency", ccy); fd.append("units", units); fd.append("statement", stmt); fd.append("commit", String(commit)); fd.append("resolve", resolve);
    try {
      const r = await fetch(`/api/import/${d.ticker}`, { method: "POST", body: fd });
      const j = await r.json();
      if (r.status === 409) { setRes({ ...res, conflicts: j.detail.conflicts, need_resolution: true }); setMsg(j.detail.message); }
      else if (!r.ok) setMsg(JSON.stringify(j.detail?.errors || j.detail));
      else { setRes(j); if (j.committed) { setMsg(`Imported. Fiscal years now ${j.years_now}; confidence ${j.confidence}.`); onDone?.(); } }
    } catch (e: any) { setMsg(String(e)); } finally { setBusy(false); }
  }
  return (
    <div className="card" data-testid="import">
      <h3>Import older Yahoo Finance annual CSV data</h3>
      <div className="small mute">Export the annual Income Statement / Balance Sheet / Cash Flow table from Yahoo Finance (Download). Ticker, periods, currency, units, duplicates and conflicts are validated before anything is merged. Imported cells fill gaps only; Yahoo values win unless you choose otherwise.</div>
      <div className="filters" style={{ margin: "8px 0" }}>
        <input type="file" accept=".csv,text/csv" onChange={(e) => { setFile(e.target.files?.[0] || null); setRes(null); }} aria-label="CSV file" />
        <label>Currency <input className="num" style={{ width: 80 }} value={ccy} onChange={(e) => setCcy(e.target.value.toUpperCase())} /></label>
        <select value={units} onChange={(e) => setUnits(e.target.value)} aria-label="Units"><option value="units">Units (full amounts)</option><option value="thousands">Thousands (Yahoo UI)</option><option value="millions">Millions</option></select>
        <select value={stmt} onChange={(e) => setStmt(e.target.value)} aria-label="Statement"><option value="">Statement: auto-detect by row</option><option value="income">Income statement</option><option value="balance">Balance sheet</option><option value="cashflow">Cash flow</option></select>
        <button className="btn" disabled={!file || busy} onClick={() => send(false)}>Validate</button>
      </div>
      {res && (
        <div>
          {res.errors?.length > 0 && <Banner kind="bad"><b>Rejected:</b><ul className="tight">{res.errors.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul></Banner>}
          {res.warnings?.length > 0 && <Banner><ul className="tight">{res.warnings.map((e: string, i: number) => <li key={i}>{e}</li>)}</ul></Banner>}
          {res.ok && <div className="small">Valid: periods {res.summary.periods.join(", ")} · rows {JSON.stringify(res.summary.rows)} · {res.conflicts.length} conflict(s) with existing figures.</div>}
          {res.conflicts?.length > 0 && <div className="scroll tall" style={{ marginTop: 6 }}><table className="t"><thead><tr><th>Line</th><th>Period</th><th>Yahoo / existing</th><th>Imported</th></tr></thead><tbody>{res.conflicts.slice(0, 40).map((c: any, i: number) => <tr key={i}><td>{c.label}</td><td>{c.period}</td><td>{Math.abs(c.yahoo) < 1000 ? c.yahoo : mm(c.yahoo)}</td><td>{Math.abs(c.imported) < 1000 ? c.imported : mm(c.imported)}</td></tr>)}</tbody></table></div>}
          {res.ok && !res.committed && (
            <div className="row" style={{ marginTop: 8 }}>
              {res.conflicts.length === 0 ? <button className="btn primary" disabled={busy} onClick={() => send(true)}>Merge into {d.ticker}</button> : <>
                <button className="btn primary" disabled={busy} onClick={() => send(true, "keep_yahoo")}>Merge, keep existing values on conflict</button>
                <button className="btn" disabled={busy} onClick={() => send(true, "prefer_import")}>Merge, prefer imported values</button></>}
            </div>
          )}
        </div>
      )}
      {msg && <div className="banner info">{msg}</div>}
      {d.imports?.length > 0 && <><h3>Imported files</h3><ul className="tight small">{d.imports.map((f: any, i: number) => <li key={i}>{f.name} - {f.uploaded_at} · periods {f.periods.join(", ")}</li>)}</ul>
        <button className="btn" onClick={async () => { await fetch(`/api/import/${d.ticker}`, { method: "DELETE" }); onDone?.(); }}>Remove imported data</button></>}
    </div>
  );
}
