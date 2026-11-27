/* Data layer. Live mode -> the FastAPI server. Snapshot mode (the published artifact) -> JSON files exported by
   scripts/export_snapshot.py, with price-dependent maths (margin of safety, rules, custom scenarios) recomputed here. */
export const STATIC: boolean = (import.meta as any).env?.VITE_STATIC === "1";

let snap: any = null;
const chunks: Record<string, Promise<any>> = {};
async function loadSnap() {
  if (!snap) snap = await (await fetch("data/snapshot.json")).json();
  return snap;
}
async function detailOf(t: string) {
  const s = await loadSnap();
  const f = s.detail_index[t];
  if (!f) throw new Error(`${t} is not in this snapshot. The snapshot covers the ${s.meta.membership.count} index securities plus STM; run the live app to analyse other tickers.`);
  chunks[f] = chunks[f] || fetch("data/" + f).then((r) => r.json());
  const d = (await chunks[f])[t];
  return { ...d, principles: s.shared.principles, confidence_rules: s.shared.confidence_rules, label_boundaries: s.shared.label_boundaries };
}

/* ---------- formulas (same as backend/dashboard/valuation.py) ---------- */
const mosOf = (fv: number | null, p: number | null) => (fv == null || fv <= 0 || p == null ? null : (fv - p) / fv);
export function priceMetrics(fv: number | null, p: number | null, req: number) {
  const m = mosOf(fv, p);
  const w = fv == null || fv <= 0 ? null : fv * (1 - req);
  return { margin_of_safety: m, upside: fv == null || p == null || p <= 0 ? null : (fv - p) / p, watch_price: w,
    decline_to_watch: p == null || w == null || p <= w ? null : (p - w) / p, meets_required_mos: m != null && m >= req };
}
export function valLabel(fv: number | null, p: number | null, conf: string) {
  if (fv == null || fv <= 0 || p == null || conf === "insufficient") return "Insufficient evidence";
  const m = (fv - p) / fv;
  return m >= 0.1 ? "Undervalued" : m < -0.15 ? "Expensive" : "Moderate / Fairly valued";
}
function rules(quality: string, qscore: any, qreason: any, m: number | null, req: number, conf: string, fresh: any) {
  const rs = [
    { key: "quality", rule: "Business quality is Strong", passed: quality === "Strong", detail: `Quality: ${quality}` + (qscore != null ? ` (${qscore}/100)` : qreason ? ` - ${qreason}` : "") },
    { key: "margin", rule: `Price at least ${Math.round(req * 100)}% below base fair value (dashboard assumption)`, passed: m != null && m >= req,
      detail: m == null ? "No usable valuation" : `Margin of safety ${(m * 100).toFixed(1)}%; needs ${Math.round(req * 100)}%` },
    { key: "confidence", rule: "Valuation confidence is Medium or High", passed: conf === "medium" || conf === "high", detail: `Confidence: ${conf}` },
    { key: "quote", rule: "Quote is current for the trading session", passed: ["current", "delayed"].includes(fresh?.status), detail: `${fresh?.status}: ${fresh?.reason || ""}` },
  ];
  return { rules: rs, missed: rs.filter((r) => !r.passed).map((r) => r.rule) };
}
const CONF: any = { high: 3, medium: 2, low: 1, insufficient: 0 };
const rankKey = (r: any) => [-CONF[r.confidence || "insufficient"], -(r.bear_discount ?? -9), -(r.quality_score || 0)];
const cmpKey = (a: any[], b: any[]) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; };

function rowAt(r: any, req: number) {
  if (!r.quality) return { ...r };
  const pm = r.usable && r.price != null ? priceMetrics(r.fv_base, r.price, req) : { margin_of_safety: null, upside: null, watch_price: null, decline_to_watch: null, meets_required_mos: false };
  const { rules: rs, missed } = rules(r.quality, r.quality_score, null, pm.margin_of_safety, req, r.confidence, { status: r.quote_status, reason: r.quote_reason });
  const q = missed.length === 0;
  return { ...r, ...pm, bear_discount: mosOf(r.fv_bear, r.price), rules: rs, missed, qualifies: q,
    status: q ? "qualified" : r.usable ? "assessed_failed_rule" : "assessed_no_valuation", reason: r.reason || r.weakest };
}
function priceView(d: any, req: number) {
  const pv = d.price_view;
  const pm = pv.fv_base != null && pv.price != null ? priceMetrics(pv.fv_base, pv.price, req) : {};
  const q = d.quality;
  const { rules: rs, missed } = rules(q.label, q.score, q.reason, (pm as any).margin_of_safety ?? null, req, pv.confidence, pv.freshness);
  return { ...pv, ...pm, rules: rs, missed, qualifies: missed.length === 0 };
}

/* ---------- custom valuation (port of dcf_operating / pb_financial / affo_reit) ---------- */
function dcf(p: any) {
  let prev = p.revenue0, pv = 0, last = 0;
  const lerp = (a: number, b: number, t: number, ramp: number) => (ramp <= 0 ? b : a + ((b - a) * Math.min(t, ramp)) / ramp);
  for (let t = 1; t <= 10; t++) {
    const g = p.g1 + ((p.g_term - p.g1) * (t - 1)) / 9;
    const rev = prev * (1 + g);
    const m = lerp(p.margin_start, p.margin_target, t, p.ramp_years);
    let cx = lerp(p.capex_start, p.capex_target, t, p.capex_ramp_years);
    if (t === 10) cx = Math.max(cx, p.da_pct);
    const f = rev * m * (1 - p.tax) + rev * p.da_pct - rev * cx - p.nwc_pct * (rev - prev);
    pv += f / (1 + p.r) ** t; prev = rev; last = f;
  }
  const tv = (last * (1 + p.g_term)) / (p.r - p.g_term) / (1 + p.r) ** 10;
  return (pv + tv - p.net_debt) / p.shares;
}
const FN: any = { operating: dcf, financial: (p: any) => (p.bvps * (p.roe - p.g)) / (p.r - p.g), reit: (p: any) => (p.affo_ps * (1 + p.g)) / (p.r - p.g) };
function customValuation(d: any, overrides: any, req: number) {
  const v = d.valuation, kind = v.kind;
  const p: any = { ...v.base_params };
  for (const k of Object.keys(overrides)) if (k in p && overrides[k] != null) p[k] = Number(overrides[k]);
  if (kind === "operating" && "ramp_years" in overrides) p.capex_ramp_years = p.ramp_years;
  if (p.r <= (kind === "operating" ? p.g_term : p.g)) throw new Error("Discount rate must exceed growth");
  const fn = FN[kind], fv = fn(p);
  const xkey = kind === "operating" ? "g1" : kind === "financial" ? "roe" : "g", step = kind === "reit" ? 0.01 : 0.02;
  const rs = [-0.02, -0.01, 0, 0.01, 0.02].map((x) => p.r + x), xs = [-2, -1, 0, 1, 2].map((k) => p[xkey] + step * k);
  const values = rs.map((r) => xs.map((x) => { try { return fn({ ...p, r, [xkey]: x }); } catch { return null; } }));
  const price = d.price_view.price;
  return { fair_value: fv, params: p, is_custom: true, metrics: priceMetrics(fv, price, req), label: valLabel(fv, price, "ok"),
    standard_base_fair_value: v.scenarios.base.fair_value, sensitivity: { rows: rs, cols: xs, col_key: xkey, values, base_r: p.r } };
}
function compare(d: any, a: string, b: string) {
  const ia = d.columns.findIndex((c: any) => c.end === a), ib = d.columns.findIndex((c: any) => c.end === b);
  const rows: any = {};
  for (const st of ["income", "balance", "cashflow"]) {
    rows[st] = d.tables[st].detail.map((r: any) => {
      const x = r.values[ia], y = r.values[ib];
      const o: any = { label: r.label, a: x, b: y, abs: null, pct: null, note: null };
      if (x != null && y != null) {
        o.abs = y - x;
        if (x > 0) o.pct = (y - x) / x; else if (x === 0) o.note = "zero baseline"; else o.note = y > 0 ? "loss->profit" : "negative baseline";
        if (x > 0 && y < 0) o.note = "profit->loss";
      } else if (x != null || y != null) o.note = "missing in one year (N/A)";
      return o;
    }).filter((o: any) => o.a != null || o.b != null);
  }
  return { a, b, rows };
}

/* ---------- router for snapshot mode ---------- */
async function staticGet(url: string): Promise<any> {
  const u = new URL(url, "http://x");
  const p = u.pathname, q = u.searchParams, req = Number(q.get("mos") ?? 0.2);
  const s = await loadSnap();
  const allRows = () => [...s.universe.rows, ...s.universe.extra_rows];
  if (p === "/api/meta") return { ...s.meta, snapshot: s.generated_at_et };
  if (p === "/api/universe") {
    const held = (q.get("extra") || "").split(",").filter(Boolean);
    const extra = s.universe.extra_rows.filter((r: any) => r.ticker === "STM" || held.includes(r.ticker));
    return { ...s.universe, rows: s.universe.rows.map((r: any) => rowAt(r, req)), extra_rows: extra.map((r: any) => rowAt(r, req)) };
  }
  if (p === "/api/shortlist") {
    const rows = s.universe.rows.map((r: any) => rowAt(r, req));
    const qual = rows.filter((r: any) => r.qualifies).sort((a: any, b: any) => cmpKey(rankKey(a), rankKey(b)));
    const closest = rows.filter((r: any) => r.usable && !r.qualifies).sort((a: any, b: any) => a.missed.length - b.missed.length || (b.margin_of_safety ?? -9) - (a.margin_of_safety ?? -9));
    const cov = { ...s.universe.coverage, qualifying: qual.length, failed_rule: rows.filter((r: any) => r.status === "assessed_failed_rule").length };
    const stm = rowAt(s.universe.extra_rows.find((r: any) => r.ticker === "STM"), req);
    return { ...s.shortlist_static, coverage: cov, required_mos: req, qualifying: qual.slice(0, 10), qualifying_total: qual.length, closest: closest.slice(0, 10), stm };
  }
  if (p === "/api/summaries") {
    const by: any = {}; allRows().forEach((r: any) => (by[r.ticker] = r));
    return { rows: (q.get("tickers") || "").split(",").filter(Boolean).map((t) => (by[t] ? rowAt(by[t], req) : { ticker: t, name: t, status: "failed_fetch", status_detail: "not in this snapshot" })) };
  }
  if (p === "/api/search") {
    const ql = (q.get("q") || "").trim().toLowerCase(); if (!ql) return { results: [] };
    const res = allRows().map((r: any) => ({ r, s: r.ticker.toLowerCase() === ql ? 0 : r.ticker.toLowerCase().startsWith(ql) ? 1 : (r.name || "").toLowerCase().includes(ql) ? 2 : 9 }))
      .filter((x: any) => x.s < 9).sort((a: any, b: any) => a.s - b.s || a.r.ticker.localeCompare(b.r.ticker)).slice(0, 20);
    return { results: res.map(({ r }: any) => ({ ticker: r.ticker, name: r.name, in_index: !r.extra })) };
  }
  const m = p.match(/^\/api\/(stock|pricing|extra|compare)\/(.+)$/);
  if (m) {
    const d = await detailOf(decodeURIComponent(m[2]));
    if (m[1] === "stock") return { ...d, price_view: priceView(d, req), required_mos: req };
    if (m[1] === "pricing") return { quote: d.quote, price_view: priceView(d, req), reverse: d.reverse, narrative: d.narrative };
    if (m[1] === "extra") return s.extras[d.ticker] || { trailing_and_estimates: { note: "Not captured in this snapshot" }, news: { items: [], error: "News is captured only for the shortlisted stocks and STM in this snapshot." } };
    return compare(d, q.get("a")!, q.get("b")!);
  }
  throw new Error("Not available in the published snapshot - run the live app for this.");
}

export async function getJson(url: string): Promise<any> {
  if (STATIC) return staticGet(url);
  const r = await fetch(url);
  if (!r.ok) throw new Error((await r.text()).slice(0, 200) || r.statusText);
  return r.json();
}
export async function postValuation(ticker: string, overrides: any, mos: number): Promise<any> {
  if (STATIC) return customValuation(await detailOf(ticker), overrides, mos);
  const r = await fetch(`/api/valuation/${ticker}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ overrides, mos }) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || "error");
  return j;
}
