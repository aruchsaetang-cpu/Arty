// Motion review without a Blender render: screenshots the Three.js preview of a clip at N evenly spaced times from a
// fixed side camera and tiles them (ffmpeg) -> preview/sheet_<clip>.png.   node tests/preview_sheet.js <clip> [n] [camx,camy,camz]
const http = require("http"), fs = require("fs"), path = require("path"), { execSync } = require("child_process");
const { chromium } = require("playwright");
const DIR = path.resolve(__dirname, "..", "preview"); const CLIP = process.argv[2] || "combat_test"; const N = +(process.argv[3] || 12);
const CAM = (process.argv[4] || "0.6,1.2,4.4").split(",").map(Number);
const CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split("?")[0]); const p = path.join(DIR, u === "/" ? "index.html" : u);
  if (!fs.existsSync(p)) { r.writeHead(404); return r.end(); } r.writeHead(200); fs.createReadStream(p).pipe(r); });
(async () => {
  await new Promise(ok => srv.listen(0, ok)); const port = srv.address().port; const tmp = fs.mkdtempSync("/tmp/sheet-");
  const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader"] });
  const pg = await b.newPage({ viewport: { width: 360, height: 560 } });
  await pg.route(CDN, r => r.fulfill({ path: path.join(DIR, "vendor", "three.min.js"), contentType: "text/javascript" }));
  await pg.goto(`http://127.0.0.1:${port}/index.html`); await pg.waitForFunction(() => window.__preview && window.__preview.ready, null, { timeout: 120000 });
  const dur = await pg.evaluate(([c, cam]) => { const P = window.__preview; P.setClip(c); P.cam.position.set(cam[0], cam[1], cam[2]); P.ctl.update();
    document.getElementById("bar").style.display = "none"; return P.manifest.clips.find(x => x.id === c).duration; }, [CLIP, CAM]);
  for (let i = 0; i < N; i++) { const t = dur * i / (N - 1) * 0.999; await pg.evaluate(t => window.__preview.setTime(t), t); await pg.waitForTimeout(250);
    await pg.screenshot({ path: path.join(tmp, `s${String(i).padStart(2, "0")}.png`) }); }
  await b.close(); srv.close();
  const out = path.join(DIR, `sheet_${CLIP}.png`); const cols = Math.min(N, 6);
  execSync(`ffmpeg -v error -y -pattern_type glob -i '${tmp}/s*.png' -vf tile=${cols}x${Math.ceil(N / cols)} -frames:v 1 ${out}`); console.log(out);
})();
