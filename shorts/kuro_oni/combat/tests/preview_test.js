// Headless check of the Three.js combat preview: serves combat/preview, loads it in Chromium at 960x540, picks the
// low-kick clip, scrubs to its hit, screenshots, and fails on console errors or missing clips.
//   node shorts/kuro_oni/combat/tests/preview_test.js [seq]
// cdnjs is blocked in this container, so the cdnjs URL is answered with the identical vendored r128 file (run 1);
// run 2 lets the CDN fail and checks the page's own fallback to vendor/three.min.js.
const http = require("http"), fs = require("fs"), path = require("path");
const { chromium } = require("playwright");
const DIR = path.resolve(__dirname, "..", "preview"); const SEQ = process.argv[2] || "combat_test";
const CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".glb": "model/gltf-binary", ".png": "image/png" };
const srv = http.createServer((q, r) => {
  const p = path.join(DIR, decodeURIComponent(q.url.split("?")[0]) === "/" ? "index.html" : decodeURIComponent(q.url.split("?")[0]));
  if (!p.startsWith(DIR) || !fs.existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { "Content-Type": TYPES[path.extname(p)] || "application/octet-stream" }); fs.createReadStream(p).pipe(r);
});
(async () => {
  await new Promise(ok => srv.listen(0, ok)); const port = srv.address().port; const out = {};
  const browser = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  for (const mode of ["cdn-routed", "cdn-blocked"]) {
    const page = await browser.newPage({ viewport: { width: 960, height: 540 } }); const errs = [];
    page.on("console", m => { if (m.type() === "error" && !(mode === "cdn-blocked" && /ERR_FAILED/.test(m.text()))) errs.push(m.text()); }); page.on("pageerror", e => errs.push(String(e)));
    if (mode === "cdn-routed") await page.route(CDN, r => r.fulfill({ path: path.join(DIR, "vendor", "three.min.js"), contentType: "text/javascript" }));
    else await page.route(CDN, r => r.abort());
    const t0 = Date.now();
    await page.goto(`http://127.0.0.1:${port}/index.html?seq=${SEQ}`);
    await page.waitForFunction(() => window.__preview && (window.__preview.ready || window.__preview.errors.length), null, { timeout: 120000 });
    const st = await page.evaluate(() => ({ ready: window.__preview.ready, errors: window.__preview.errors, clips: window.__preview.clips,
      animations: window.__preview.animations, three: window.__preview.threeSource, rev: window.THREE && THREE.REVISION }));
    let shot = null;
    if (st.ready) {
      const kick = st.clips.find(c => /kick/.test(c)) || st.clips[0];
      const hitT = await page.evaluate(id => { window.__preview.setClip(id); const c = window.__preview.manifest.clips.find(x => x.id === id); return c.hits.length ? c.hits[0].time : 0.5; }, kick);
      await page.evaluate(t => window.__preview.setTime(t), hitT); await page.waitForTimeout(1500);
      shot = path.join(DIR, mode === "cdn-routed" ? "screenshot.png" : "screenshot_fallback.png"); await page.screenshot({ path: shot });
      const fps = await page.evaluate(() => new Promise(ok => { let n = 0; const t = performance.now(); (function f() { n++; if (performance.now() - t < 2000) requestAnimationFrame(f); else ok(n / 2); })(); }));
      st.fps = Math.round(fps); st.kick_clip = kick; st.hit_time = hitT;
    }
    out[mode] = Object.assign(st, { console_errors: errs, load_ms: Date.now() - t0, screenshot: shot });
    await page.close();
  }
  await browser.close(); srv.close();
  console.log(JSON.stringify(out, null, 1));
  const ok = Object.values(out).every(o => o.ready && !o.console_errors.length && o.clips && o.clips.length >= 3);
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
