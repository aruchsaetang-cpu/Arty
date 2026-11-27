import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getJson } from "./api";
import { pct } from "./lib";

const KEYS = ["gross_margin", "op_margin", "net_margin", "roa", "roe", "debt_equity", "eps"];
const fmt = (u: string, v: any) => (v == null ? "N/A" : u === "pct" ? pct(v, 1) : u === "x" ? Number(v).toFixed(2) : Number(v).toFixed(2));

/** Small-multiple charts: each Buffett ratio over fiscal years, its target line, and an optional second company. */
export default function RatioCharts({ d }: any) {
  const [peer, setPeer] = useState<string>("");
  const [input, setInput] = useState("");
  const [peerData, setPeerData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [suggest, setSuggest] = useState<string[]>([]);
  useEffect(() => {
    getJson("/api/universe?mos=0.2").then((u) => {
      const same = u.rows.filter((r: any) => r.industry && r.industry === d.industry && r.ticker !== d.ticker).map((r: any) => r.ticker);
      const sect = u.rows.filter((r: any) => r.sector === d.sector && r.ticker !== d.ticker && r.quality === "Strong").map((r: any) => r.ticker);
      setSuggest([...new Set([...same, ...sect])].slice(0, 5));
    }).catch(() => {});
  }, [d.ticker]);
  useEffect(() => {
    if (!peer) { setPeerData(null); return; }
    setErr(null);
    getJson(`/api/stock/${peer}?mos=0.2`).then(setPeerData).catch((e) => { setErr(String(e.message || e).slice(0, 120)); setPeer(""); });
  }, [peer]);
  const rows = useMemo(() => KEYS.map((k) => d.ratios?.find((r: any) => r.key === k)).filter((r: any) => r && r.series?.length), [d]);
  const peerRow = (k: string) => peerData?.ratios?.find((r: any) => r.key === k);
  return (
    <div className="card" data-testid="ratio-charts">
      <div className="row">
        <h3 className="sp" style={{ margin: 0 }}>Ratios over time</h3>
        <form className="row" style={{ gap: 6 }} onSubmit={(e) => { e.preventDefault(); input.trim() && setPeer(input.trim().toUpperCase()); }}>
          <input id="peer-input" className="num" style={{ width: 110 }} placeholder="Compare…" value={input} onChange={(e) => setInput(e.target.value)} aria-label="Compare with ticker" data-testid="peer-input" />
          {peer && <button type="button" className="btn" onClick={() => { setPeer(""); setInput(""); }}>Clear</button>}
        </form>
      </div>
      {suggest.length > 0 && !peer && <div className="row small" style={{ gap: 6, marginTop: 8 }}><span className="mute">Peers</span>
        {suggest.map((t) => <button key={t} className="chip" style={{ border: 0, cursor: "pointer", minHeight: 28 }} onClick={() => { setInput(t); setPeer(t); }}>{t}</button>)}</div>}
      {err && <div className="small down" style={{ marginTop: 6 }}>{err}</div>}
      <div className="charts-grid">
        {rows.map((r: any) => {
          const p = peerRow(r.key);
          const fys = [...new Set([...r.series.map((x: any) => x.fy), ...(p?.series || []).map((x: any) => x.fy)])].sort();
          const data = fys.map((fy) => ({ fy, a: r.series.find((x: any) => x.fy === fy)?.v ?? null, b: p?.series?.find((x: any) => x.fy === fy)?.v ?? null }));
          return (
            <div key={r.key} className="mini">
              <div className="row" style={{ gap: 6 }}><b className="small sp">{r.name}</b><span className="tiny mute">{r.target}</span></div>
              <div style={{ height: 150 }}>
                <ResponsiveContainer>
                  <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                    <CartesianGrid stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="fy" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(x) => String(x).replace("FY", "")} />
                    <YAxis tick={{ fontSize: 10 }} width={42} axisLine={false} tickLine={false} tickFormatter={(v) => (r.unit === "pct" ? pct(v, 0) : Number(v).toFixed(1))} domain={["auto", "auto"]} />
                    <Tooltip formatter={(v: any, n: any) => [fmt(r.unit, v), n]} />
                    {r.target_value != null && <ReferenceLine y={r.target_value} stroke="var(--good)" strokeDasharray="4 4" />}
                    <Line type="monotone" dataKey="a" name={d.ticker} stroke="var(--accent)" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />
                    {p && <Line type="monotone" dataKey="b" name={peer} stroke="var(--warn)" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} />}
                    {p && <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          );
        })}
      </div>
      <div className="tiny mute" style={{ marginTop: 6 }}>Dashed line = Buffett target.</div>
    </div>
  );
}
