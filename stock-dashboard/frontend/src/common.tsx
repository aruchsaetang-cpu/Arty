import React from "react";
import { pct, price, spct, toggleHolding, useHoldings } from "./lib";

/** Ownership checkbox: its own 48px tap target; never bubbles to the row, so it cannot open the stock page. */
export function OwnedBox({ ticker, label = "Owned", compact = false }: { ticker: string; label?: string; compact?: boolean }) {
  const held = useHoldings();
  const on = !!held[ticker];
  return (
    <label className="own" onClick={(e) => e.stopPropagation()} aria-label={`${label}: ${ticker}`}>
      <input type="checkbox" checked={on} onChange={() => toggleHolding(ticker)} onClick={(e) => e.stopPropagation()} data-testid={`own-${ticker}`} />
      {!compact && <span>{label}</span>}
    </label>
  );
}

export const qualityClass = (q: string | null) => (q === "Strong" ? "good" : q === "Mixed" ? "warn" : q === "Weak" ? "bad" : "");
export const valClass = (v: string | null) => (v === "Undervalued" ? "good" : v === "Expensive" ? "bad" : v?.startsWith("Moderate") ? "warn" : "");
export const confClass = (c: string | null) => (c === "high" ? "good" : c === "medium" ? "warn" : c === "low" ? "bad" : "");

export const Chip = ({ cls = "", children, title }: { cls?: string; children: React.ReactNode; title?: string }) => (
  <span className={`chip ${cls}`} title={title}>{children}</span>
);
export const QualityChip = ({ q }: { q: string | null }) => (q ? <Chip cls={qualityClass(q)}>{q}</Chip> : <Chip>Awaiting analysis</Chip>);
export const ValChip = ({ v }: { v: string | null }) => (v ? <Chip cls={valClass(v)}>{v}</Chip> : <Chip>Not assessed</Chip>);
export const ConfChip = ({ c }: { c: string | null }) => (c ? <Chip cls={confClass(c)}>{c[0].toUpperCase() + c.slice(1)}</Chip> : <Chip>–</Chip>);

export function QuoteChip({ status, reason }: { status?: string | null; reason?: string }) {
  if (!status) return <Chip title="No quote cached yet">No quote</Chip>;
  const cls = status === "current" ? "good" : status === "delayed" ? "warn" : "bad";
  const txt = status === "current" ? "Current" : status === "delayed" ? "Delayed / intraday" : "Stale";
  return <Chip cls={cls} title={reason}>{txt}</Chip>;
}

export const MosText = ({ m }: { m: number | null | undefined }) =>
  m === null || m === undefined ? <span className="mute">N/A</span> : <span className={`mos ${m >= 0 ? "up" : "down"}`}>{pct(m, 0)}</span>;

export function Banner({ kind = "", children }: { kind?: string; children: React.ReactNode }) {
  return <div className={`banner ${kind}`}>{children}</div>;
}

export const StatusLabel: Record<string, string> = {
  qualified: "Qualifies",
  assessed_failed_rule: "Assessed - failed a rule",
  assessed_no_valuation: "Assessed - no usable valuation",
  awaiting: "Awaiting analysis",
  failed_fetch: "Data fetch failed",
};

export function Missed({ missed }: { missed: string[] }) {
  if (!missed?.length) return <Chip cls="good">Meets all four rules</Chip>;
  return <>{missed.map((m) => <Chip key={m} cls="bad">Missed: {m}</Chip>)}</>;
}

export function RuleList({ rules }: { rules: any[] }) {
  return (
    <ul className="tight">
      {rules.map((r) => (
        <li key={r.key}>
          <b className={r.passed ? "pill-pass" : "pill-fail"}>{r.passed ? "✓" : "✗"}</b> {r.rule} <span className="mute small">- {r.detail}</span>
        </li>
      ))}
    </ul>
  );
}

export function PickRow({ r, rank, open, onToggle, go, closest }: any) {
  const ccy = r.currency || "USD";
  return (
    <div className="pick">
      <div className="pick-main" onClick={onToggle} role="button" aria-expanded={open} data-testid={`pick-${r.ticker}`}>
        <OwnedBox ticker={r.ticker} />
        <div className="id">
          <div className="row" style={{ gap: 6 }}>
            {rank && <span className="rank">{rank}</span>}
            <a className="tk" href={"#/stock/" + r.ticker} onClick={(e) => e.stopPropagation()}>{r.ticker}</a>
          </div>
          <div className="nm">{r.name}</div>
        </div>
        <div className="px">
          <div className="b">{price(r.price, ccy)}</div>
          <div className="tiny mute">{r.price_time || ""}</div>
        </div>
        <div className="mosc">
          <MosText m={r.margin_of_safety} />
          <div className="tiny mute">margin of safety</div>
        </div>
        <div className="why">
          {closest ? <span><Missed missed={r.missed} /></span> : <span>{r.reason || r.weakest}</span>}
        </div>
      </div>
      {open && (
        <div className="pick-more">
          <div className="kv">
            <div><small>Fair value bear / base / bull</small>{[r.fv_bear, r.fv_base, r.fv_bull].map((x) => (x === null || x === undefined ? "N/A" : x <= 0 ? "≤0" : x.toFixed(2))).join(" / ")}</div>
            <div><small>Base fair value</small><b>{price(r.fv_base, ccy)}</b></div>
            <div><small>Upside to fair value</small>{spct(r.upside)}</div>
            <div><small>Watch price (buy below)</small>{price(r.watch_price, ccy)}{r.decline_to_watch ? <span className="mute small"> (needs −{pct(r.decline_to_watch, 0)})</span> : null}</div>
            <div><small>Confidence</small><ConfChip c={r.confidence} /></div>
            <div><small>Business quality</small><QualityChip q={r.quality} /> <span className="small mute">{r.quality_score ?? ""}{r.quality_score != null ? "/100" : ""}</span></div>
            <div><small>Valuation</small><ValChip v={r.valuation_label} /></div>
            <div><small>Quote</small><QuoteChip status={r.quote_status} reason={r.quote_reason} /></div>
          </div>
          {!closest && r.risk && <div><b>Biggest risk:</b> {r.risk}</div>}
          {closest && <div className="small mute">Closest candidates are assessed stocks that did NOT qualify; the rules each one missed are shown above.</div>}
          <div className="row">
            <a className="btn primary" href={"#/stock/" + r.ticker}>Open full analysis →</a>
          </div>
        </div>
      )}
    </div>
  );
}
