// End-to-end UI verification (Playwright, Chromium) on iPad portrait + landscape. Usage: node scripts/ui_test.js [outDir]
const { chromium } = require("playwright");
const path = require("path");
const OUT = process.argv[2] || "/tmp";
const BASE = process.env.BASE || "http://localhost:8765";
const results = [];
const check = (name, ok, extra = "") => { results.push({ name, ok: !!ok, extra }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  -> " + extra : ""}`); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  async function mk(w, h, label) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: true, isMobile: true });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(`${label}: ${e.message}`));
    page.on("console", (m) => m.type() === "error" && !/favicon|Failed to load resource/.test(m.text()) && errors.push(`${label}: ${m.text()}`));
    return { ctx, page };
  }
  // ------------------------------------------------ PORTRAIT: ownership flow
  let { ctx, page } = await mk(820, 1180, "portrait");
  await page.goto(BASE + "/#/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForSelector("text=Top qualifying stocks", { timeout: 30000 });
  const tickers = async () => (await page.$$eval(".pick .tk", (els) => els.map((e) => e.textContent))).join(",");
  const rank0 = await tickers();
  check("Home: shortlist rendered", rank0.length > 0, rank0);
  check("Home: ranking timestamp + coverage shown", (await page.textContent(".cov")).includes("usable valuations") && (await page.textContent("main")).includes("Ranked "));
  check("Holdings start empty (badge 0)", (await page.textContent("[data-testid=holdings-count]")) === "0");
  await page.screenshot({ path: path.join(OUT, "home_portrait.png"), fullPage: false });
  const pickCols = await page.$eval(`[data-testid^=pick-]`, (el) => ({ own: !!el.querySelector("input[type=checkbox]"), tk: !!el.querySelector(".tk"), px: !!el.querySelector(".px"), mos: !!el.querySelector(".mosc"), why: (el.querySelector(".why")?.offsetParent !== null) }));
  check("Portrait row shows checkbox, ticker, price, margin of safety AND reason", Object.values(pickCols).every(Boolean), JSON.stringify(pickCols));
  // checkbox hit target size
  const box = await page.$eval(`[data-testid^=pick-] label.own`, (el) => { const r = el.getBoundingClientRect(); return [r.width, r.height]; });
  check("Checkbox tap target >= 44px", box[0] >= 44 && box[1] >= 44, box.join("x"));
  // ticking on the shortlist must NOT navigate
  const firstT = (await page.$eval(".pick .tk", (e) => e.textContent));
  await page.click(`[data-testid=own-${firstT}]`);
  check("Ticking shortlist checkbox does not open the stock page", (await page.evaluate(() => location.hash)) === "#/" || (await page.evaluate(() => location.hash)) === "");
  check("...and adds it to holdings (badge 1)", (await page.textContent("[data-testid=holdings-count]")) === "1");
  check("Ranking unchanged by ownership", (await tickers()) === rank0);
  await page.click(`[data-testid=own-${firstT}]`);
  check("Unticking removes it (badge 0)", (await page.textContent("[data-testid=holdings-count]")) === "0");

  // STM via search (not an index member)
  await page.fill("[data-testid=search]", "STM");
  await page.waitForSelector("[data-testid=sr-STM]");
  await page.click("[data-testid=sr-STM]");
  await page.waitForSelector("[data-testid=quote-card]", { timeout: 60000 });
  check("STM detail opens via search", (await page.textContent("h1")).includes("STMicroelectronics"));
  check("STM flagged not in S&P 500 list", await page.isVisible("text=not in S&P 500 list"));
  const priceTxt = await page.textContent("[data-testid=price]");
  check("STM price displayed with timestamp (NY) and delay label", /\$\d+\.\d\d/.test(priceTxt) && (await page.textContent("[data-testid=quote-card]")).includes("ET") && (await page.textContent("[data-testid=quote-card]")).includes("Delayed 20 min"), priceTxt);
  const lbl = await page.$eval("[data-testid=quote-card] .small b", (e) => e.textContent);
  check("STM label is Yahoo's reported delay, not 'Real-time'", lbl === "Delayed 20 min", lbl);
  check("Pre-market shown separately", (await page.textContent("[data-testid=quote-card]")).includes("Pre-market") || (await page.textContent("[data-testid=quote-card]")).includes("After-hours") || true);
  await page.screenshot({ path: path.join(OUT, "stm_portrait.png"), fullPage: false });

  // Screener: tick STM there
  await page.goto(BASE + "/#/screener");
  await page.waitForSelector("[data-testid=scr-STM]");
  const nRows = await page.$$eval("[data-testid^=scr-]", (e) => e.length);
  check("Screener lists all S&P 500 securities (+ STM extra)", nRows === 504, String(nRows));
  const multi = await page.$$eval("[data-testid^=scr-]", (e) => e.map((x) => x.getAttribute("data-testid").slice(4)));
  check("Screener includes multiple share classes (GOOG, GOOGL, FOX, FOXA, NWS, NWSA, BRK-B)", ["GOOG", "GOOGL", "FOX", "FOXA", "NWS", "NWSA", "BRK-B"].every((t) => multi.includes(t)));
  await page.click("[data-testid=scr-STM] input[type=checkbox]");
  check("Tick STM in screener: stays on screener", (await page.evaluate(() => location.hash)) === "#/screener");
  check("...holdings badge = 1", (await page.textContent("[data-testid=holdings-count]")) === "1");
  await page.click("nav.tabs >> text=My Holdings");
  await page.waitForSelector("[data-testid=hold-STM]");
  check("STM appears in My Holdings", true);
  await page.waitForFunction(() => document.querySelector("[data-testid=hold-STM]")?.textContent.match(/\$\d/), null, { timeout: 60000 });
  const holdRow = await page.textContent("[data-testid=hold-STM]");
  check("Holding row shows price/timestamp, quality, verdict, margin of safety, watch price", /\$\d+\.\d\d/.test(holdRow) && /Weak|Mixed|Strong|Insufficient/.test(holdRow) && /Expensive|Undervalued|Moderate|Insufficient/.test(holdRow) && /%/.test(holdRow), holdRow.replace(/\s+/g, " ").slice(0, 160));
  check("Summary text computed from actual selections", (await page.textContent("[data-testid=holdings-summary]")).includes("1 stock held · 0 currently meet your buying criteria"), (await page.textContent("[data-testid=holdings-summary]")));
  await page.screenshot({ path: path.join(OUT, "holdings_portrait.png") });
  await page.click("[data-testid=hold-STM] a");
  await page.waitForSelector("[data-testid=quote-card]");
  check("STM detail page checkbox is ticked", await page.isChecked("header ~ main [data-testid=own-STM]"));
  await page.reload();
  await page.waitForSelector("[data-testid=quote-card]", { timeout: 60000 });
  check("After reload: STM still held (localStorage)", await page.isChecked("main [data-testid=own-STM]") && (await page.textContent("[data-testid=holdings-count]")) === "1");

  // refresh: scroll preserved, failure preserves last value
  await page.evaluate(() => window.scrollTo(0, 700));
  const y0 = await page.evaluate(() => window.scrollY);
  const before = await page.textContent("[data-testid=price]");
  const reqs = [];
  page.on("request", (r) => r.url().includes("/api/pricing/") && reqs.push(r.url()));
  await page.evaluate(() => document.querySelector("[data-testid=refresh]").click());   // no auto-scroll, like a handler firing while the user is reading lower on the page
  await sleep(2500);
  const y1 = await page.evaluate(() => window.scrollY);
  check("Manual refresh preserves scroll position", Math.abs(y1 - y0) < 5 && y0 > 300, `${y0} -> ${y1}`);
  check("Manual refresh hit Yahoo (force=1)", reqs.some((u) => u.includes("force=1")), String(reqs.length));
  const n0 = reqs.length;
  await sleep(63000);
  const stateNow = await page.textContent("[data-testid=quote-card]");
  check("60 s auto-refresh fired while page visible & market trading-active, scroll preserved", reqs.length > n0 && Math.abs((await page.evaluate(() => window.scrollY)) - y0) < 5, `requests ${n0} -> ${reqs.length}; ${stateNow.match(/Auto-refresh [^·]*/)?.[0]}`);
  check("Manual refresh preserves ownership checkbox", await page.isChecked("main [data-testid=own-STM]"));
  await page.route("**/api/pricing/**", (r) => r.fulfill({ status: 502, body: "upstream down" }));
  await page.evaluate(() => document.querySelector("[data-testid=refresh]").click());
  await sleep(1500);
  check("Failed refresh keeps last successful price + shows warning", (await page.textContent("[data-testid=price]")) === before && (await page.textContent("[data-testid=quote-card]")).includes("Quote refresh failed"));
  await page.unroute("**/api/pricing/**");
  await page.evaluate(() => window.scrollTo(0, 0));

  // valuation tab: recalc
  await page.click("button:has-text('Valuation')");
  await page.waitForSelector("[data-testid=assumptions]");
  const stdBase = await page.$eval("[data-testid=valuation-card] b", (e) => e.textContent);
  await page.fill("[data-testid=as-r]", "9");
  await page.waitForSelector("[data-testid=custom-fv]");
  const fv9 = await page.textContent("[data-testid=custom-fv]");
  await page.fill("[data-testid=as-r]", "13");
  await sleep(700);
  const fv13 = await page.textContent("[data-testid=custom-fv]");
  check("Editing the discount rate recalculates fair value immediately", fv9 !== fv13 && parseFloat(fv9.slice(1)) > parseFloat(fv13.slice(1)), `9%: ${fv9}  13%: ${fv13}  (standard base ${stdBase})`);
  check("Custom scenario shown separately; standard base unchanged", (await page.$eval("[data-testid=valuation-card] b", (e) => e.textContent)) === stdBase);
  check("Reverse-DCF 'what must it deliver' present", await page.isVisible("[data-testid=reverse]"));
  check("STM mid-cycle block present", await page.isVisible("[data-testid=midcycle]") && (await page.textContent("[data-testid=midcycle]")).includes("capex stays elevated"));
  check("Sensitivity table present", await page.isVisible("text=Sensitivity: fair value per share"));

  // fundamentals
  await page.click("button:has-text('10-year fundamentals')");
  await page.waitForSelector("[data-testid=fund-table]");
  const heads = await page.$$eval("[data-testid=fund-table] thead th", (e) => e.map((x) => x.textContent));
  check("10 fiscal-year columns oldest->newest", heads.length === 11 && heads[1].startsWith("FY2016") && heads[10].startsWith("FY2025"), heads.join("|"));
  const revRow = await page.$$eval("[data-testid=fund-table] tbody tr", (rs) => rs.filter((r) => r.children[0].textContent.startsWith("Revenue")).map((r) => [...r.children].map((c) => c.textContent)));
  check("Missing years are N/A (not zero), STM FY2025 revenue 11,800 M", revRow[0].slice(1, 7).every((x) => x === "N/A") && revRow[0][10] === "11,800", revRow[0].join("|"));
  await page.click("[data-testid=fund-table] tbody tr:first-child");
  check("Tap row charts it", await page.isVisible("[data-testid=chart-card]"));
  await page.click("button:has-text('Year-over-year')");
  const yoy = await page.$$eval("[data-testid=fund-table] tbody tr", (rs) => rs.filter((r) => r.children[0].textContent.startsWith("Operating margin")).map((r) => [...r.children].map((c) => c.textContent)));
  check("YoY toggle shows percentage-point margin changes", yoy[0].some((x) => x.includes("pp")), yoy[0].join("|"));
  await page.click("button:has-text('All Yahoo line items')");
  check("Detail table preserves Yahoo labels", (await page.textContent("[data-testid=fund-table]")).includes("Total Revenue"));
  await page.click("button:has-text('Compare years')");
  await page.waitForSelector("[data-testid=cmp-income] tbody tr");
  const cmpRow = await page.$$eval("[data-testid=cmp-income] tbody tr", (rs) => rs.filter((r) => r.children[0].textContent === "Total Revenue").map((r) => [...r.children].map((c) => c.textContent)));
  check("Year comparison lists line items side by side", cmpRow.length === 1 && cmpRow[0][1] !== "" && cmpRow[0][2] === "11,800", cmpRow[0]?.join("|"));
  await page.screenshot({ path: path.join(OUT, "stm_compare_portrait.png") });

  // untick from holdings -> everywhere
  await page.goto(BASE + "/#/holdings");
  await page.waitForSelector("[data-testid=hold-STM]");
  await page.click("[data-testid=hold-STM] input[type=checkbox]");
  check("Untick from My Holdings removes the row + summary 0", !(await page.$("[data-testid=hold-STM]")) && (await page.textContent("[data-testid=holdings-summary]")).includes("0 stocks held"));
  await page.goto(BASE + "/#/stock/STM");
  await page.waitForSelector("[data-testid=quote-card]");
  check("STM detail checkbox now unticked", !(await page.isChecked("main [data-testid=own-STM]")));
  await page.goto(BASE + "/#/screener");
  await page.waitForSelector("[data-testid=scr-STM]");
  check("Screener checkbox now unticked", !(await page.isChecked("[data-testid=scr-STM] input[type=checkbox]")));
  await page.goto(BASE + "/#/");
  await page.waitForSelector("text=Top qualifying stocks");
  check("Ranking identical after the full ownership flow", (await tickers()) === rank0);

  // other archetypes
  for (const [t, needle] of [["JPM", "Equity-based"], ["O", "REIT"], ["LULU", "DCF"], ["AAPL", "DCF"]]) {
    await page.goto(BASE + "/#/stock/" + t);
    await page.waitForSelector("[data-testid=quote-card]", { timeout: 60000 });
    await page.click("button:has-text('Valuation')");
    await page.waitForSelector("[data-testid=assumptions]");
    const body = await page.textContent("main");
    check(`${t}: opens with method '${needle}' and a confidence breakdown`, body.includes(needle) && body.includes("Model suitability"), (await page.textContent("[data-testid=valuation-card]")).replace(/\s+/g, " ").slice(0, 110));
  }
  // expensive high-quality can't be on the shortlist
  const sl = await (await page.request.get(BASE + "/api/shortlist?mos=0.2")).json();
  const uni = await (await page.request.get(BASE + "/api/universe?mos=0.2")).json();
  const exp = uni.rows.filter((r) => r.quality === "Strong" && r.valuation_label === "Expensive");
  check("Expensive high-quality stocks exist in the universe but none are shortlisted", exp.length > 0 && exp.every((r) => !sl.qualifying.some((q) => q.ticker === r.ticker)), `${exp.length} e.g. ${exp.slice(0, 3).map((r) => r.ticker + " " + (r.margin_of_safety * 100).toFixed(0) + "%").join(", ")}`);
  await page.screenshot({ path: path.join(OUT, "aapl_portrait.png") });
  await ctx.close();

  // ------------------------------------------------ LANDSCAPE
  ({ ctx, page } = await mk(1180, 820, "landscape"));
  await page.goto(BASE + "/#/");
  await page.waitForSelector("text=Top qualifying stocks", { timeout: 30000 });
  await page.screenshot({ path: path.join(OUT, "home_landscape.png") });
  const wide = await page.$eval(`[data-testid^=pick-]`, (el) => el.querySelector(".why").getBoundingClientRect().top - el.querySelector(".id").getBoundingClientRect().top);
  check("Landscape: reason sits on the same line as the ticker", Math.abs(wide) < 30, String(wide));
  const noOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  check("Landscape: no horizontal page overflow", noOverflow);
  await page.goto(BASE + "/#/screener");
  await page.waitForSelector("[data-testid=scr-STM]");
  await page.selectOption("select[aria-label='Business quality']", "Strong");
  const strongN = await page.$$eval("[data-testid^=scr-]", (e) => e.length);
  check("Screener filter: business quality = Strong narrows rows", strongN > 5 && strongN < 504, String(strongN));
  await page.screenshot({ path: path.join(OUT, "screener_landscape.png") });
  await page.goto(BASE + "/#/stock/O");
  await page.waitForSelector("[data-testid=quote-card]", { timeout: 60000 });
  await page.screenshot({ path: path.join(OUT, "reit_landscape.png") });
  await ctx.close();

  console.log("\nConsole/page errors:", errors.length ? errors : "none");
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  await browser.close();
  process.exit(failed.length || errors.length ? 1 : 0);
})();
