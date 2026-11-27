import { useState } from "react";
import { Banner, Chip } from "./common";
import { pct, usePrefs, useApi } from "./lib";

export default function Method() {
  const { mos } = usePrefs();
  const { data } = useApi<any>("/api/meta");
  const [msg, setMsg] = useState<string | null>(null);
  if (!data) return <div className="card">Loading…</div>;
  async function upload(f: File) {
    const fd = new FormData(); fd.append("file", f);
    const r = await fetch("/api/membership/import", { method: "POST", body: fd });
    const j = await r.json();
    setMsg(r.ok ? `Official list loaded: ${j.count} securities (${j.label}). Reload the page.` : `Rejected: ${JSON.stringify(j.detail)}`);
  }
  const m = data.membership;
  return (
    <>
      <h1>Method, rules and sources</h1>
      <div className="card"><h3>S&amp;P 500 membership</h3>
        <div className="row"><Chip cls={m.verified ? "good" : "bad"}>{m.verified ? "Verified against S&P DJI file" : "NOT verified against S&P DJI"}</Chip><span>{m.label}</span><span className="mute small">as of {m.as_of} · {m.count} securities</span></div>
        <div className="small mute">{m.note} S&amp;P DJI blocks automated downloads, so verification needs the official constituents spreadsheet (download from <a href={m.url ?? data.sources.spdji.url} target="_blank" rel="noreferrer">spglobal.com/spdji</a>, “Constituents”). Upload it (.xlsx or .csv) and the app will use it instead of the secondary source.</div>
        <input type="file" accept=".xlsx,.csv" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} aria-label="Official S&P constituents file" />
        {msg && <Banner kind="info">{msg}</Banner>}</div>
      <div className="card"><h3>Formulas</h3>
        <ul className="tight"><li><b>Margin of safety</b> = {data.formulas.margin_of_safety}</li><li><b>Upside to fair value</b> = {data.formulas.upside}</li><li><b>Watch price</b> = {data.formulas.watch_price}</li></ul>
        <div className="small mute">Example: price $80, fair value $100 → margin of safety 20.0%, upside 25.0%, watch price at your {pct(mos, 0)} requirement = ${(100 * (1 - mos)).toFixed(2)}.</div></div>
      <div className="card"><h3>Shortlist: all four must hold</h3>
        <ol className="tight"><li>Business quality is <b>Strong</b> under the published rules below.</li><li>Latest regular-session price is at least <b>{pct(mos, 0)}</b> below base-case fair value <Chip>dashboard assumption, editable on Home</Chip>.</li><li>Valuation confidence is <b>Medium or High</b>.</li><li>The quote is <b>current</b> for the trading session (weekends/holidays recognised; an intraday quote is flagged delayed; a missing newer completed session excludes the stock).</li></ol>
        <div className="small">{data.ranking_explanation}</div></div>
      <div className="card"><h3>Valuation labels (boundaries on margin of safety)</h3>
        <ul className="tight">{data.label_boundaries.map((b: any) => <li key={b.label}><b>{b.label}</b>: {b.rule}</li>)}<li><b>Buy threshold</b>: margin of safety ≥ {pct(mos, 0)} (your assumption) - sits above the Undervalued boundary.</li></ul></div>
      <div className="card"><h3>Business-quality rules (“Buffett-inspired model assessment”)</h3>
        <div className="small">{data.quality_label_rule}</div>
        {Object.entries(data.quality_rules).map(([k, rs]: any) => <div key={k}><h3>{k === "operating" ? "Operating companies" : k === "financial" ? "Banks and insurers (equity-based)" : "REITs"}</h3><ul className="tight small">{rs.map((r: any) => <li key={r.key}><b>{r.name}.</b> {r.rule}</li>)}</ul></div>)}</div>
      <div className="card"><h3>Valuation confidence</h3><ul className="tight small">{data.confidence_rules.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul><div className="small mute">{data.discount_rule} Current 10-year Treasury (Yahoo ^TNX): {pct(data.rf.rate, 2)} as of {data.rf.as_of}.</div></div>
      <div className="card"><h3>Primary sources for the investing principles</h3>
        <ul className="tight small">{data.principles.map((p: any) => <li key={p.id}><b>{p.title}</b> - {p.source}, dated {p.date}. <a href={p.url} target="_blank" rel="noreferrer">link</a> · <span className="mute">{p.used_for}</span></li>)}</ul></div>
    </>
  );
}
