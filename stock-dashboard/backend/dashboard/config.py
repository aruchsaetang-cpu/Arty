"""Published constants and rule thresholds. Everything the UI shows as a 'rule' is read from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "cache.db"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

TZ_NY = "America/New_York"
MODEL_VERSION = "2026.11-r3"

# ---- user-editable default (dashboard assumption, NOT a Buffett quote) -----------------------
DEFAULT_REQUIRED_MOS = 0.20

# ---- valuation label boundaries (margin of safety = (FV - P) / FV) ---------------------------
LABEL_UNDERVALUED_MIN_MOS = 0.10     # MoS >= 10%  -> Undervalued
LABEL_EXPENSIVE_MAX_MOS = -0.15      # MoS <  -15% -> Expensive  (price > 1.176x fair value)
# in between -> Moderate / Fairly valued.  The buy threshold (default 20%) sits ABOVE the
# Undervalued boundary on purpose: a stock can be modestly undervalued and still not be buyable.

# ---- discount-rate construction ---------------------------------------------------------------
EQUITY_RISK_PREMIUM = 0.05
BETA_CLIP = (0.8, 1.4)
DISCOUNT_FLOOR, DISCOUNT_CAP = 0.08, 0.12
TERMINAL_GROWTH = {"bear": 0.02, "base": 0.025, "bull": 0.03}
PROJECTION_YEARS = 10

# ---- data sufficiency -----------------------------------------------------------------------
MIN_YEARS_FOR_ASSESSMENT = 4         # fewer annual periods -> "Insufficient evidence"
YEARS_FOR_HIGH_COVERAGE = 8

# ---- freshness --------------------------------------------------------------------------------
QUOTE_GRACE_MIN_AFTER_CLOSE = 10     # regularMarketTime may precede the close print by a few minutes
OPEN_SESSION_STALE_EXTRA_MIN = 15    # beyond Yahoo's stated delay before an open-session quote is 'stale'

# ---- background refresh ---------------------------------------------------------------------
FUNDAMENTALS_TTL_HOURS = 24 * 7
UNIVERSE_QUOTE_TTL_MIN_OPEN = 10
UNIVERSE_QUOTE_TTL_MIN_CLOSED = 180
BATCH_SIZE = 20
BATCH_PAUSE_SEC = 1.5
WORKERS = 4

# ---- sources shown in the UI -------------------------------------------------------------------
SOURCES = {
    "yahoo": {"label": "Yahoo Finance (via yfinance)", "url": "https://finance.yahoo.com/"},
    "spdji": {"label": "S&P Dow Jones Indices - S&P 500 constituents",
              "url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/"},
    "wikipedia": {"label": "Wikipedia - List of S&P 500 companies (unofficial secondary source)",
                  "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"},
}

PRINCIPLES = [
    {"id": "owner-earnings", "title": "Owner earnings and reinvestment needs",
     "source": "Berkshire Hathaway shareholder letter for 1986 (appendix on goodwill: 'owner earnings' = reported earnings + D&A - average annual capex needed to maintain position)",
     "date": "1987-03-04", "url": "https://www.berkshirehathaway.com/letters/1986.html",
     "used_for": "Cash required for reinvestment pillar; owner-earnings proxy"},
    {"id": "roe", "title": "Judge a business by return on equity without leverage",
     "source": "Berkshire Hathaway shareholder letter for 1979 (return on equity capital, earned without undue leverage)",
     "date": "1980-03-03", "url": "https://www.berkshirehathaway.com/letters/1979.html",
     "used_for": "Returns on capital pillar"},
    {"id": "intrinsic", "title": "Intrinsic value = discounted cash that can be taken out of a business; growth and value are joined",
     "source": "Berkshire Hathaway shareholder letter for 1992 (intrinsic value; margin of safety credited to Graham)",
     "date": "1993-03-01", "url": "https://www.berkshirehathaway.com/letters/1992.html",
     "used_for": "Fair-value method and margin-of-safety framing"},
    {"id": "wonderful", "title": "A wonderful company at a fair price beats a fair company at a wonderful price",
     "source": "Berkshire Hathaway shareholder letter for 1989", "date": "1990-03-02",
     "url": "https://www.berkshirehathaway.com/letters/1989.html", "used_for": "Quality-first ranking order"},
    {"id": "mr-market", "title": "Mr. Market: use price swings, do not be guided by them",
     "source": "Berkshire Hathaway shareholder letter for 1987", "date": "1988-03-14",
     "url": "https://www.berkshirehathaway.com/letters/1987.html", "used_for": "Why the buy threshold is price-vs-value"},
    {"id": "owners-manual", "title": "An Owner's Manual: tenets on per-share value, debt aversion and retained earnings",
     "source": "Berkshire Hathaway, 'An Owner's Manual' (first issued 1996)", "date": "1996-06-01",
     "url": "https://www.berkshirehathaway.com/owners.html",
     "used_for": "Balance-sheet and value-per-share pillars"},
    {"id": "graham", "title": "Defensive-investor criteria, normalized earnings, margin of safety",
     "source": "Benjamin Graham, The Intelligent Investor (rev. 4th ed., 1973), chs. 14 and 20", "date": "1973-01-01",
     "url": "https://en.wikipedia.org/wiki/The_Intelligent_Investor", "used_for": "Secondary Graham perspective"},
    {"id": "lynch", "title": "Six stock categories; PEG; per-share growth",
     "source": "Peter Lynch, One Up on Wall Street (1989), chs. 7 and 13", "date": "1989-01-01",
     "url": "https://en.wikipedia.org/wiki/One_Up_on_Wall_Street", "used_for": "Secondary Lynch perspective"},
]
