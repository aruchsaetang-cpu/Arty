import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

/* ---------------- formatting ---------------- */
export const N = (x: any) => x === null || x === undefined || (typeof x === "number" && !isFinite(x));
export const pct = (x: any, d = 1) => (N(x) ? "N/A" : `${(x * 100).toFixed(d)}%`);
export const spct = (x: any, d = 1) => (N(x) ? "N/A" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`);
export const pp = (x: any, d = 1) => (N(x) ? "N/A" : `${x >= 0 ? "+" : ""}${x.toFixed(d)} pp`);
export const num = (x: any, d = 2) => (N(x) ? "N/A" : x.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const price = (x: any, ccy = "USD") => (N(x) ? "N/A" : (ccy === "USD" ? "$" : "") + x.toFixed(2) + (ccy === "USD" ? "" : " " + ccy));
export const mm = (x: any, d = 0) => (N(x) ? "N/A" : (x / 1e6).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const big = (x: any) => {
  if (N(x)) return "N/A";
  const a = Math.abs(x);
  const s = a >= 1e12 ? (a / 1e12).toFixed(2) + "T" : a >= 1e9 ? (a / 1e9).toFixed(2) + "B" : a >= 1e6 ? (a / 1e6).toFixed(1) + "M" : a.toFixed(0);
  return (x < 0 ? "-" : "") + s;
};
export function cell(v: any, kind: string) {
  if (N(v)) return "N/A";
  if (kind === "pct") return pct(v);
  if (kind === "ratio") return v.toFixed(2);
  if (kind === "pershare") return v.toFixed(2);
  if (kind === "shares") return (v / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 }) + "M";
  return mm(v);
}
export const fyShort = (end: string) => end?.slice(0, 7);

/* ---------------- tiny external store ---------------- */
function makeStore<T>(key: string, initial: T, version = 1) {
  let value: T = initial;
  try {
    const raw = localStorage.getItem(key);
    if (raw) value = JSON.parse(raw);
  } catch {}
  const subs = new Set<() => void>();
  const emit = () => subs.forEach((f) => f());
  const set = (v: T) => {
    value = v;
    try {
      localStorage.setItem(key, JSON.stringify(v));
    } catch {}
    emit();
  };
  window.addEventListener("storage", (e) => {
    if (e.key === key) {
      try {
        value = e.newValue ? JSON.parse(e.newValue) : initial;
      } catch {}
      emit();
    }
  });
  return {
    get: () => value,
    set,
    use: () => useSyncExternalStore((cb) => (subs.add(cb), () => subs.delete(cb)), () => value),
  };
}

/* Holdings: ticker -> {added}. Starts EMPTY. Never touched by quotes, ranking or index changes. */
const holdingsStore = makeStore<Record<string, { added: string }>>("holdings.v1", {});
export const useHoldings = () => holdingsStore.use();
export const toggleHolding = (t: string) => {
  const cur = { ...holdingsStore.get() };
  if (cur[t]) delete cur[t];
  else cur[t] = { added: new Date().toISOString() };
  holdingsStore.set(cur);
};
export const holdingTickers = () => Object.keys(holdingsStore.get());

/* Preferences. The required margin of safety is a DASHBOARD ASSUMPTION, editable. */
const prefsStore = makeStore<{ mos: number }>("prefs.v1", { mos: 0.2 });
export const usePrefs = () => prefsStore.use();
export const setMos = (m: number) => prefsStore.set({ ...prefsStore.get(), mos: Math.min(0.9, Math.max(0, m)) });

/* ---------------- hash router ---------------- */
export function useRoute() {
  const [h, setH] = useState(location.hash || "#/");
  useEffect(() => {
    const f = () => setH(location.hash || "#/");
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  const parts = h.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { parts, go: (p: string) => (location.hash = p) };
}
export const href = (p: string) => "#/" + p;

/* ---------------- data hooks: keep last good data, never blank the screen ---------------- */
export function useApi<T = any>(url: string | null, opts: { every?: number; enabled?: boolean; keep?: boolean } = {}) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [okAt, setOkAt] = useState<number | null>(null);
  const urlRef = useRef(url);
  urlRef.current = url;
  const load = useCallback(async () => {
    const u = urlRef.current;
    if (!u) return;
    setLoading(true);
    try {
      const r = await fetch(u);
      if (!r.ok) throw new Error((await r.text()).slice(0, 200) || r.statusText);
      const j = await r.json();
      if (urlRef.current === u) {
        setData(j);
        setError(null);
        setOkAt(Date.now());
      }
    } catch (e: any) {
      setError(String(e.message || e)); // keep previous data
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (opts.enabled === false) return;
    if (!opts.keep) setData(null);
    setError(null);
    load();
  }, [url, opts.enabled]);
  useEffect(() => {
    if (!opts.every || opts.enabled === false) return;
    const id = setInterval(() => document.visibilityState === "visible" && load(), opts.every);
    return () => clearInterval(id);
  }, [opts.every, opts.enabled, load]);
  return { data, error, loading, reload: load, okAt, setData };
}

export function useDebounced<T>(v: T, ms: number) {
  const [d, setD] = useState(v);
  useEffect(() => {
    const id = setTimeout(() => setD(v), ms);
    return () => clearTimeout(id);
  }, [v, ms]);
  return d;
}
