import { useEffect, useState } from "react";
import { Chip } from "./common";
import { setNote, useApi, useNotes, when } from "./lib";

const firstSentence = (s: string) => {
  const m = (s || "").match(/^.*?[.!?](\s|$)/);
  const x = (m ? m[0] : s || "").trim();
  return x.length > 180 ? x.slice(0, 177) + "…" : x;
};

/** Company description in the user's own words (saved in this browser). Falls back to one Yahoo sentence. */
export function About({ d }: any) {
  const notes = useNotes();
  const mine = notes[d.ticker];
  const [edit, setEdit] = useState(false);
  const [txt, setTxt] = useState(mine || "");
  useEffect(() => setTxt(mine || ""), [mine, d.ticker]);
  return (
    <div className="card" data-testid="about">
      <div className="row"><h3 className="sp" style={{ margin: 0 }}>About</h3>
        {!edit && <button className="btn" onClick={() => setEdit(true)} data-testid="about-edit">{mine ? "Edit" : "Write my own"}</button>}</div>
      {!edit && <p className="small" style={{ margin: "8px 0 0" }}>{mine || <span className="mute">{firstSentence(d.summary)}</span>}</p>}
      {edit && <>
        <textarea id={"note-" + d.ticker} value={txt} onChange={(e) => setTxt(e.target.value)} rows={3} placeholder="In my words, this company…"
          style={{ width: "100%", marginTop: 8, font: "inherit", padding: 10, borderRadius: 8, border: "1px solid var(--line)", background: "var(--surface)", color: "var(--ink)" }} data-testid="about-text" />
        <div className="row" style={{ marginTop: 6 }}>
          <button className="btn primary" onClick={() => { setNote(d.ticker, txt); setEdit(false); }} data-testid="about-save">Save</button>
          <button className="btn" onClick={() => { setTxt(mine || ""); setEdit(false); }}>Cancel</button>
        </div></>}
    </div>
  );
}

export function CeoLink({ d, onOpen }: any) {
  const c = d.ceo;
  if (!c?.listed) return <span className="small mute">CEO not listed by Yahoo</span>;
  const name = c.profile?.name || c.officers.map((o: any) => o.name).join(" & ");
  return <button className="ceo-link" onClick={onOpen} data-testid="ceo-link">CEO <b>{name}</b> ›</button>;
}

export function CeoPanel({ ticker, onClose }: any) {
  const { data } = useApi<any>(`/api/ceo/${ticker}`);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);
  const p = data?.profile;
  const news = (data?.news?.items || []).filter((n: any) => n.title);
  return (
    <div className="sheet-bg" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" data-testid="ceo-panel">
        <div className="row"><div className="sp"><div className="eyebrow">Chief executive</div>
          <h2 style={{ margin: "2px 0 0" }}>{p?.name || data?.officers?.map((o: any) => o.name).join(" & ") || "…"}</h2></div>
          <button className="btn" onClick={onClose} aria-label="Close">Close</button></div>
        {data?.officers?.map((o: any) => (
          <div key={o.name} className="small mute">{o.title}{o.age ? ` · age ${o.age}` : ""}{o.pay ? ` · pay $${(o.pay / 1e6).toFixed(1)}M` : ""}</div>
        ))}
        {p && <div className="small mute">CEO since {p.since}</div>}

        {p?.quotes?.length > 0 && <><h3 className="sh">In their words</h3>
          {p.quotes.map((q: any, i: number) => <blockquote key={i} className="quote">“{q.text}”<a href={q.url} target="_blank" rel="noreferrer">{q.source}</a></blockquote>)}</>}
        {p && <><h3 className="sh">Approach</h3><ul className="tight small">{p.approach.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
          <h3 className="sh">How they run the company</h3><ul className="tight small">{p.how.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul></>}
        {data && !p && <p className="small mute">No researched profile yet. Headlines below are from Yahoo Finance.</p>}

        <h3 className="sh">Latest on Yahoo Finance</h3>
        {!data && <span className="mute small">Loading…</span>}
        {data && news.length === 0 && <span className="mute small">{data.news?.error || "No recent headlines."}</span>}
        <ul className="tight small">{news.slice(0, 8).map((n: any, i: number) => <li key={i}><a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> <span className="tiny mute">{n.publisher}{n.published ? " · " + when(new Date(n.published * 1000).toISOString()) : ""}</span>{n.mentions_ceo && <> <Chip>quotes CEO</Chip></>}</li>)}</ul>

        {p?.sources?.length > 0 && <><h3 className="sh">Sources</h3><ul className="tight tiny">{p.sources.map((s: any) => <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.label}</a></li>)}</ul></>}
      </div>
    </div>
  );
}
