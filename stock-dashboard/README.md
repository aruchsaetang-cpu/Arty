# Stock research dashboard (5-10 year investor)

iPad-friendly dashboard answering three questions on open:
1. Which S&P 500 stocks look like strong businesses at attractive prices today? (Home)
2. Which of those do I own? (Owned checkboxes everywhere, My Holdings tab)
3. Is STMicroelectronics (NYSE: STM) undervalued, moderately valued or expensive, and why? (pinned card + detail page)

**Stack:** React + TypeScript + Recharts (Vite) front end; Python (FastAPI, SQLite cache) back end; all market data from Yahoo Finance via
[`yfinance`](https://github.com/ranaroussi/yfinance) (implemented with the `yfinance-data` skill from himself65/finance-skills, installed for Claude Code at `.claude/skills/yfinance-data`).

## Launch

```bash
scripts/setup.sh        # once: pip deps + npm install + build the UI
scripts/run.sh          # serves UI + API + background refresher on http://localhost:8765   (PORT=... to change)
```

The server refreshes by itself: universe quotes every 10 min while NYSE is open (3 h otherwise), annual statements weekly, in rate-limited
batches of 20 with 4 workers. A cold start analysed all 503 securities in ~4 minutes. No browser or Claude session is needed:
`python3 scripts/refresh.py [--quotes|--force]` does the same headlessly for cron/systemd. A failed refresh never overwrites the last good value or timestamp.

## What is verified vs. not (read this)

* **Yahoo supplies only 4 (sometimes 5) annual periods, not 10.** All ten columns are kept; missing years are `N/A` (never 0) and charts have gaps. Because of this
  **no valuation can reach "High" confidence until older annual CSVs are imported** (Stock page -> Sources & import). Max is Medium.
* **Yahoo quotes are delayed 20 minutes** (`exchangeDataDelayedBy`), so nothing is labelled "Real-time"; the UI shows "Delayed 20 min".
* **S&P 500 membership is NOT verified against the official S&P DJI list in this build:** spglobal.com blocks automated access (Akamai 403, even from a real browser).
  The default is Wikipedia's list (503 securities, incl. all share classes), loudly labelled *unofficial*. Download the official constituents spreadsheet from S&P DJI and
  upload it on the **Method** tab (or drop it at `backend/data/sp500_official.xlsx`) and the app switches to it and drops the warning.
* Berkshire-letter and Graham/Lynch links are cited by year/chapter; the letter pages were not machine-fetched in the build sandbox.

## Model (all rules are published in the UI -> Method tab)

* **Margin of safety** = (base FV - price) / base FV · **Upside** = (base FV - price) / price · **Watch price** = base FV x (1 - required MoS). Default required MoS 20%, editable (dashboard assumption).
* **Shortlist = all four:** quality *Strong* · MoS >= required · confidence Medium/High · quote current (weekends, holidays and early closes recognised via the NYSE calendar; a missing newer completed session excludes the stock).
* **Ranking:** confidence, then discount to *bear*-case FV, then quality score. Ownership never affects anything on the server.
* **Quality** (0-100, five pillars: earning power, returns on capital, reinvestment needs, balance sheet, per-share value) with sector-specific rules for operating companies, banks/insurers, REITs.
  *Strong* additionally requires earning power and returns on capital to pass outright.
* **Valuation:** operating = 10-year FCFF DCF + earnings-power cross-check; banks/insurers = justified P/B (residual income) + sustainable-payout model; REITs = AFFO-proxy capitalisation + DDM.
  Standard bear/base/bull drive the ranking; user edits create a separate custom scenario. Labels: Undervalued MoS >= 10%, Fair -15%..10%, Expensive < -15%.
* Graham and Lynch pages are secondary perspectives only.

## Tests

```bash
cd backend && python3 -m pytest -q tests          # 32 tests: formulas, calendar/staleness, fundamentals maths, import validation, shortlist rules, import API
node scripts/ui_test.js /tmp/shots                # iPad portrait+landscape end-to-end (needs the server running)
python3 scripts/verify_independent.py STM LULU    # checks STM vs fresh Yahoo data; re-derives a fair value with separate code
```
